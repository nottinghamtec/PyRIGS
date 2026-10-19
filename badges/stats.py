"""
Everything we know about someone's history in TEC, worked out from data RIGS already records.

Used both for deciding which badges someone has earned and for building their Tech Rider.
"""

import datetime
from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import cached_property

from django.db.models import Count, Q
from django.utils import timezone
from reversion.models import Revision, Version

from assets.models import Asset

from RIGS.models import Event, EventChecklist, EventCheckIn, PowerTestRecord, Profile, RiskAssessment, Venue
from training.models import TrainingItemQualification, TrainingLevelQualification

# A check-in longer than this was almost certainly a forgotten check-out
MAX_SHIFT = datetime.timedelta(hours=24)

HS_MODELS = (RiskAssessment, EventChecklist, PowerTestRecord)
# Models whose creators we credit, from the first saved version of each object
CREATED_MODELS = (*HS_MODELS, Event, Venue, Asset)

# Some imported revisions are dated 1970; nothing real in RIGS predates this
HISTORY_START = timezone.make_aware(datetime.datetime(2000, 1, 1))

# A "rig" is a real, crewed event that went ahead
RIG_FILTER = Q(is_rig=True, dry_hire=False) & ~Q(status=Event.CANCELLED)


def to_datetime(value):
    if value is None or isinstance(value, datetime.datetime):
        return value
    return timezone.make_aware(datetime.datetime.combine(value, datetime.time.min))


def nth(values, n):
    """The nth (1-based) value of an already sorted list, or None if there aren't that many."""
    return values[n - 1] if len(values) >= n else None


def add_years(date, years):
    try:
        return date.replace(year=date.year + years)
    except ValueError:  # 29th February
        return date.replace(year=date.year + years, day=28)


def academic_year(date):
    """TEC's year runs from September, e.g. 2025/26."""
    start = date.year if date.month >= 9 else date.year - 1
    return f"{start}/{str(start + 1)[-2:]}"


@dataclass
class History:
    """What people have done in RIGS, from the version history."""

    created: dict  # {model: {user_id: [sorted datetimes]}}: objects each person created
    asset_edits: dict  # {user_id: [sorted datetimes]}: changes saved to the assets database
    cable_edits: dict  # {user_id: [sorted datetimes]}: as above, for cables only
    revisions: dict  # {user_id: [sorted datetimes]}: every change saved anywhere in RIGS


def _by_user(rows):
    by_user = defaultdict(list)
    for user_id, date in rows:
        by_user[user_id].append(date)
    for dates in by_user.values():
        dates.sort()
    return by_user


def build_history(user_id=None):
    """
    Work out History for everyone (once per award run, shared between profiles), or for just one person.

    One person is much cheaper, as only the records they've touched need looking at; that's what single pages use.
    """
    mine = {} if user_id is None else {"revision__user_id": user_id}

    created = {}
    for model in CREATED_MODELS:
        versions = Version.objects.get_for_model(model)
        if mine:  # Only objects they've touched; we still need everyone's versions of those to find who was first
            versions = versions.filter(object_id__in=versions.filter(**mine).values("object_id"))
        first_versions = {}
        rows = versions.order_by("revision__date_created", "pk").values_list(
            "object_id", "revision__user_id", "revision__date_created"
        )
        for object_id, author_id, date in rows:
            first_versions.setdefault(object_id, (author_id, date))
        existing = {str(pk) for pk in model.objects.values_list("pk", flat=True)}
        created[model] = _by_user(
            (author_id, date)
            for object_id, (author_id, date) in first_versions.items()
            if author_id is not None and object_id in existing and date >= HISTORY_START
        )

    # One edit per revision, however many assets it touched
    cables = {str(pk) for pk in Asset.objects.filter(is_cable=True).values_list("pk", flat=True)}
    asset_revisions, cable_revisions = {}, {}
    versions = (
        Version.objects.get_for_model(Asset)
        .filter(revision__user__isnull=False, revision__date_created__gte=HISTORY_START, **mine)
        .values_list("revision_id", "object_id", "revision__user_id", "revision__date_created")
    )
    for revision_id, object_id, author_id, date in versions:
        asset_revisions[revision_id] = (author_id, date)
        if object_id in cables:
            cable_revisions[revision_id] = (author_id, date)

    revisions = Revision.objects.filter(
        user__isnull=False, date_created__gte=HISTORY_START, **({"user_id": user_id} if mine else {})
    ).values_list("user_id", "date_created")
    return History(
        created=created,
        asset_edits=_by_user(asset_revisions.values()),
        cable_edits=_by_user(cable_revisions.values()),
        revisions=_by_user(revisions),
    )


class ProfileStats:
    def __init__(self, profile, history=None):
        self.profile = profile
        self._history = history

    @cached_property
    def today(self):
        return timezone.localdate()

    # --- Rigs ---

    @cached_property
    def rig_events(self):
        """
        Rigs this person checked in to or MIC'd.

        Check-ins only started in 2021, so MIC'd events are the only record of anything before then.
        """
        return list(
            Event.objects.filter(RIG_FILTER)
            .filter(Q(crew__person=self.profile) | Q(mic=self.profile, start_date__lte=self.today))
            .distinct()
            .select_related("venue")
            .order_by("start_date", "pk")
        )

    @cached_property
    def rig_dates(self):
        return [event.start_date for event in self.rig_events]

    @cached_property
    def first_rig(self):
        return self.rig_events[0] if self.rig_events else None

    @cached_property
    def checkins(self):
        return list(
            EventCheckIn.objects.filter(person=self.profile)
            .filter(event__in=[event.pk for event in self.rig_events])
            .select_related("event")
            .order_by("time")
        )

    @cached_property
    def shifts(self):
        """(check-in, raw length) for every completed check-in that looks plausible."""
        shifts = []
        for checkin in self.checkins:
            if checkin.end_time is None or checkin.end_time <= checkin.time:
                continue
            shifts.append((checkin, checkin.end_time - checkin.time))
        return sorted(shifts, key=lambda shift: shift[0].end_time)

    @cached_property
    def total_hours(self):
        return sum(min(length, MAX_SHIFT).total_seconds() for _, length in self.shifts) / 3600

    def hours_reached(self, hours):
        total = 0
        for checkin, length in self.shifts:
            total += min(length, MAX_SHIFT).total_seconds() / 3600
            if total >= hours:
                return checkin.end_time
        return None

    @cached_property
    def longest_shift(self):
        plausible = [shift for shift in self.shifts if shift[1] <= MAX_SHIFT]
        return max(plausible, key=lambda shift: shift[1], default=None)

    @cached_property
    def longest_shift_hours(self):
        return self.longest_shift[1].total_seconds() / 3600 if self.longest_shift else None

    @cached_property
    def drive_dates(self):
        """Start date of each rig where this person checked in with a vehicle."""
        seen = set()
        dates = []
        for checkin in self.checkins:
            if checkin.vehicle.strip() and checkin.event_id not in seen:
                seen.add(checkin.event_id)
                dates.append(checkin.event.start_date)
        return sorted(dates)

    @cached_property
    def roles(self):
        return Counter((checkin.role.strip() or "Crew").title() for checkin in self.checkins).most_common()

    # --- Venues ---

    @cached_property
    def venue_counts(self):
        return Counter(event.venue for event in self.rig_events if event.venue is not None).most_common()

    @cached_property
    def new_venue_dates(self):
        seen = set()
        dates = []
        for event in self.rig_events:
            if event.venue_id is not None and event.venue_id not in seen:
                seen.add(event.venue_id)
                dates.append(event.start_date)
        return dates

    def venue_reached(self, count):
        """When any one venue first reached `count` rigs."""
        counts = Counter()
        for event in self.rig_events:
            if event.venue_id is None:
                continue
            counts[event.venue_id] += 1
            if counts[event.venue_id] == count:
                return event.start_date
        return None

    # --- MIC ---

    @cached_property
    def mic_events(self):
        return list(
            Event.objects.filter(RIG_FILTER, mic=self.profile, start_date__lte=self.today)
            .annotate(crew_count=Count("crew__person", distinct=True))
            .select_related("venue")
            .order_by("start_date", "pk")
        )

    @cached_property
    def mic_dates(self):
        return [event.start_date for event in self.mic_events]

    @cached_property
    def power_mic_dates(self):
        dates = []
        for model in (RiskAssessment, PowerTestRecord):
            dates += model.objects.filter(power_mic=self.profile, event__start_date__lte=self.today).values_list(
                "event__start_date", flat=True
            )
        return sorted(dates)

    # --- Training ---

    @cached_property
    def item_quals(self):
        return list(TrainingItemQualification.objects.filter(trainee_id=self.profile.pk).order_by("date", "pk"))

    @cached_property
    def taught_quals(self):
        return list(TrainingItemQualification.objects.filter(supervisor_id=self.profile.pk).order_by("date", "pk"))

    @cached_property
    def level_quals(self):
        return list(
            TrainingLevelQualification.objects.filter(trainee_id=self.profile.pk, confirmed_on__isnull=False)
            .select_related("level")
            .order_by("confirmed_on", "pk")
        )

    @cached_property
    def levels_confirmed_for_others(self):
        return list(
            TrainingLevelQualification.objects.filter(confirmed_by_id=self.profile.pk, confirmed_on__isnull=False)
            .exclude(trainee_id=self.profile.pk)
            .order_by("confirmed_on")
            .values_list("confirmed_on", flat=True)
        )

    # --- Things created and edited in RIGS ---

    @property
    def history(self):
        """The shared History if we were given one (award runs), otherwise just this person's (single pages)."""
        if self._history is None:
            self._history = build_history(user_id=self.profile.pk)
        return self._history

    def authored(self, *models):
        """When this person created each object of these models (H&S documents by default)."""
        return sorted(
            date for model in models or HS_MODELS for date in self.history.created[model].get(self.profile.pk, [])
        )

    @property
    def asset_edits(self):
        return self.history.asset_edits.get(self.profile.pk, [])

    @property
    def cable_edits(self):
        return self.history.cable_edits.get(self.profile.pk, [])

    @property
    def revisions(self):
        return self.history.revisions.get(self.profile.pk, [])

    # --- Clients ---

    @cached_property
    def mic_clients(self):
        """(start date, client) for each MIC'd event with a client, where a client is an organisation or person."""
        return [
            (
                event.start_date,
                ("organisation", event.organisation_id) if event.organisation_id else ("person", event.person_id),
            )
            for event in self.mic_events
            if event.organisation_id or event.person_id
        ]

    @cached_property
    def authorised_mic_dates(self):
        authorised = set(
            Event.objects.filter(
                pk__in=[event.pk for event in self.mic_events], authorisation__isnull=False
            ).values_list("pk", flat=True)
        )
        return [event.start_date for event in self.mic_events if event.pk in authorised]

    # --- Crew ---

    @cached_property
    def event_people(self):
        """{event id: other people on it} for each rig, counting crew who checked in and the MIC."""
        people = defaultdict(set)
        rows = EventCheckIn.objects.filter(event__in=[event.pk for event in self.rig_events]).values_list(
            "event_id", "person_id"
        )
        for event_id, person_id in rows:
            people[event_id].add(person_id)
        for event in self.rig_events:
            if event.mic_id:
                people[event.pk].add(event.mic_id)
            people[event.pk].discard(self.profile.pk)
        return people

    def crewmates_reached(self, distinct=None, shared=None):
        """When this person first rigged with `distinct` different people, or with one person `shared` times."""
        seen = Counter()
        for event in self.rig_events:
            for person_id in self.event_people.get(event.pk, ()):
                seen[person_id] += 1
                if shared and seen[person_id] == shared:
                    return event.start_date
            if distinct and len(seen) >= distinct:
                return event.start_date
        return None

    # --- Tech Rider extras ---

    @cached_property
    def crewmates(self):
        """The people this person has rigged with most, as [(profile, shared rigs)]."""
        counts = Counter(person_id for people in self.event_people.values() for person_id in people)
        top = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:5]
        people = Profile.objects.in_bulk([person_id for person_id, _ in top])
        return [(people[person_id], shared) for person_id, shared in top if person_id in people]

    @cached_property
    def rigs_by_year(self):
        counts = Counter(academic_year(date) for date in self.rig_dates)
        return sorted(counts.items())

    @cached_property
    def biggest_rig(self):
        if not self.rig_events:
            return None
        return (
            Event.objects.filter(pk__in=[event.pk for event in self.rig_events])
            .annotate(crew_count=Count("crew__person", distinct=True))
            .select_related("venue")
            .order_by("-crew_count", "start_date")
            .first()
        )

    @cached_property
    def this_year(self):
        label = academic_year(self.today)
        return {
            "label": label,
            "rigs": sum(1 for date in self.rig_dates if academic_year(date) == label),
            "mics": sum(1 for date in self.mic_dates if academic_year(date) == label),
            "new_venues": sum(1 for date in self.new_venue_dates if academic_year(date) == label),
            "skills": sum(1 for qual in self.item_quals if academic_year(qual.date) == label),
        }
