"""
Every badge, and the rule for earning it.

A rule takes a ProfileStats and returns when the badge was achieved (a date or datetime), or None if it hasn't been.
Changing a rule doesn't take badges away from anyone; run `award_badges --reset` to recompute from scratch.

The exception is Headliner, which has no rule: it's worked out across everyone on each run (see awarding.py), and
moves when someone else takes the top spot.
"""

import datetime
import re
from collections import Counter
from dataclasses import dataclass
from typing import Callable

from django.utils import timezone

from assets.models import Asset
from RIGS.models import Event, EventChecklist, PowerTestRecord, RiskAssessment, Venue
from training.models import TrainingItemQualification, TrainingLevel

from badges.stats import MAX_SHIFT, academic_year, add_years, nth, postcode_area, risk_assessment


@dataclass(frozen=True)
class Category:
    slug: str
    name: str
    colour: str  # Medal colour; dark enough for a white icon on top


@dataclass(frozen=True)
class Badge:
    slug: str
    name: str
    category: Category
    icon: str  # Font Awesome (solid) icon name
    blurb: str
    rule: Callable | None


MILESTONES = Category("milestones", "Milestones", "#3853a4")
LEADERSHIP = Category("leadership", "Leadership", "#c2410c")
EXPLORER = Category("explorer", "Explorer", "#15803d")
ROAD = Category("road", "Road", "#475569")
TRAINING = Category("training", "Training", "#0e7490")
DEPARTMENTS = Category("departments", "Departments", "#6d28d9")
TEACHING = Category("teaching", "Teaching", "#1e3a8a")
SAFETY = Category("safety", "Safety", "#b91c1c")
CREW = Category("crew", "Crew", "#be185d")
CLIENTS = Category("clients", "Clients", "#047857")
ADMIN = Category("admin", "Admin", "#57534e")
STORE = Category("store", "Store", "#a16207")
MOMENTS = Category("moments", "Moments", "#0369a1")
SEASONS = Category("seasons", "Seasons", "#4d7c0f")
POWER = Category("power", "Power", "#854d0e")
PRODUCTION = Category("production", "Production", "#4338ca")
TRADITIONS = Category("traditions", "Traditions", "#9f1239")
COMMUNITY = Category("community", "Community", "#0f766e")
NOVELTY = Category("novelty", "Novelty", "#111827")

CATEGORIES = [
    MILESTONES, LEADERSHIP, EXPLORER, ROAD, TRAINING, DEPARTMENTS, TEACHING,
    SAFETY, POWER, PRODUCTION, CREW, CLIENTS, COMMUNITY, ADMIN, STORE, MOMENTS, SEASONS, TRADITIONS, NOVELTY,
]  # fmt: skip

# Anything bigger is a placeholder or a typo, not a real job
BIG_TICKET = (2000, 100_000)

HEADLINER = "headliner"

FULL_HOUSE_DEPARTMENTS = (TrainingLevel.SOUND, TrainingLevel.LIGHTING, TrainingLevel.POWER, TrainingLevel.RIGGING)


def first(values):
    return next(iter(values), None)


def nth_of(attr, n):
    """The nth entry of one of ProfileStats' sorted date lists."""
    return lambda s: nth(getattr(s, attr), n)


def authored(n, *models):
    return lambda s: nth(s.authored(*models), n)


def anniversary(years):
    def rule(s):
        date = add_years(s.first_rig.start_date, years) if s.first_rig else None
        return date if date and date <= s.today else None

    return rule


def level(minimum, department=None, exclude=()):
    """
    A confirmed level of at least `minimum` in an actual department (or in `department`, if given).

    The "common competencies" levels have no department; they're prerequisites, not the level itself.
    """
    return lambda s: first(
        q.confirmed_on
        for q in s.level_quals
        if q.level.level >= minimum
        and q.level.department is not None
        and q.level.department not in exclude
        and department in (None, q.level.department)
    )


def full_house(s):
    dates = [level(TrainingLevel.TECHNICIAN, department)(s) for department in FULL_HOUSE_DEPARTMENTS]
    return None if None in dates else max(dates)


def polymath(s):
    departments = set()
    for qual in s.level_quals:
        if qual.level.department is not None:
            departments.add(qual.level.department)
            if len(departments) == 3:
                return qual.confirmed_on
    return None


def weekend_warrior(s):
    """Three rigs starting in the same Friday to Sunday."""
    weekends = Counter()
    for date in s.rig_dates:
        if date.weekday() >= 4:
            weekends[date.toordinal() - (date.weekday() - 4)] += 1
            if 3 in weekends.values():
                return date
    return None


def night_owl(s):
    for checkin, length in s.shifts:
        start, end = timezone.localtime(checkin.time), timezone.localtime(checkin.end_time)
        if length <= MAX_SHIFT and end.date() > start.date() and end.hour < 6:
            return checkin.end_time
    return None


def clients(same=None, different=None):
    """MIC'd `same` events for one client, or for `different` clients."""

    def rule(s):
        counts = Counter()
        for date, client in s.mic_clients:
            counts[client] += 1
            if (same and counts[client] == same) or (different and len(counts) == different):
                return date
        return None

    return rule


def event_days(event):
    """Every day an event runs, up to a fortnight."""
    days = min(((event.end_date or event.start_date) - event.start_date).days, 14)
    return [event.start_date + datetime.timedelta(days=n) for n in range(days + 1)]


def on_day(month, day):
    return lambda s: first(d for e in s.rig_events for d in event_days(e) if (d.month, d.day) == (month, day))


def comeback(s):
    """Back on the road after a year without a rig."""
    return first(current for previous, current in zip(s.rig_dates, s.rig_dates[1:]) if (current - previous).days >= 365)


def vehicle_rigs(pattern, n):
    """The nth rig where this person checked in with a vehicle matching pattern."""

    def rule(s):
        seen, dates = set(), []
        for checkin in s.checkins:
            if re.search(pattern, checkin.vehicle, re.IGNORECASE) and checkin.event_id not in seen:
                seen.add(checkin.event_id)
                dates.append(checkin.event.start_date)
        return nth(sorted(dates), n)

    return rule


def ra_rigs(n, *fields):
    """The nth rig whose risk assessment ticks any of these boxes."""
    return lambda s: nth(s.rigs_where(lambda e: (ra := risk_assessment(e)) and any(getattr(ra, f) for f in fields)), n)


def quote_rigs(pattern, anywhere=False):
    """The first rig with something matching pattern on its quote (or, if anywhere, its name or venue notes too)."""

    def text(s, event):
        extra = f" {event.name} {event.venue.notes if event.venue else ''}".lower() if anywhere else ""
        return s.quote_text.get(event.pk, "") + extra

    return lambda s: first(s.rigs_where(lambda e: re.search(pattern, text(s, e))))


def named_rigs(pattern, n=1):
    """The nth rig with a name matching pattern."""
    return lambda s: nth(s.rigs_where(lambda e: re.search(pattern, e.name, re.IGNORECASE)), n)


def off_grid(s):
    return first(
        s.rigs_where(
            lambda e: ((ra := risk_assessment(e)) and ra.generators) or "generator" in s.quote_text.get(e.pk, "")
        )
    )


def annual_fixture(s):
    """The same event (going by its name, ignoring any year in it) in three different academic years."""
    years = {}
    for event in s.rig_events:
        name = " ".join(re.sub(r"\d+", " ", event.name.lower()).split())
        years.setdefault(name, set()).add(academic_year(event.start_date))
        if len(years[name]) == 3:
            return event.start_date
    return None


def society_darling(s):
    """Rigs for ten different Students' Union organisations (societies, sports clubs and so on)."""
    seen = set()
    for event in s.rig_events:
        if event.organisation_id and event.organisation.union_account:
            seen.add(event.organisation_id)
            if len(seen) == 10:
                return event.start_date
    return None


def away_game(s):
    """A rig at a venue whose address has a postcode outside Nottingham (most venues don't have one recorded)."""
    return first(
        s.rigs_where(lambda e: e.venue and (area := postcode_area(e.venue.address)) is not None and area != "NG")
    )


T = TrainingLevel

# fmt: off
_BADGES = [
    Badge("opening-act", "Opening Act", MILESTONES, "play", "Your first rig with TEC.", nth_of("rig_dates", 1)),
    Badge("regular", "Regular", MILESTONES, "repeat", "Ten rigs down.", nth_of("rig_dates", 10)),
    Badge("veteran", "Veteran", MILESTONES, "medal", "A quarter-century of shows.", nth_of("rig_dates", 25)),
    Badge("half-century", "Half Century", MILESTONES, "award", "Fifty rigs. Respect.", nth_of("rig_dates", 50)),
    Badge("centurion", "Centurion", MILESTONES, "crown", "One hundred rigs. Legendary.", nth_of("rig_dates", 100)),
    Badge("clocked-on", "Clocked On", MILESTONES, "clock", "100 hours on site.", lambda s: s.hours_reached(100)),
    Badge("lifer", "Lifer", MILESTONES, "hourglass-end", "500 hours on site.", lambda s: s.hours_reached(500)),
    Badge("anniversary-1", "Anniversary I", MILESTONES, "cake-candles", "A year since your first rig.", anniversary(1)),
    Badge("anniversary-2", "Anniversary II", MILESTONES, "cake-candles", "Two years since your first rig.", anniversary(2)),
    Badge("anniversary-3", "Anniversary III", MILESTONES, "cake-candles", "Three years since your first rig.", anniversary(3)),

    Badge("mic-drop", "Mic Drop", LEADERSHIP, "microphone", "Your first event as MIC.", nth_of("mic_dates", 1)),
    Badge("ringleader", "Ringleader", LEADERSHIP, "bullhorn", "MIC'd ten events.", nth_of("mic_dates", 10)),
    Badge("big-top", "Big Top", LEADERSHIP, "people-group", "MIC'd an event with 8+ crew checked in.",
          lambda s: first(e.start_date for e in s.mic_events if e.crew_count >= 8)),

    Badge("away-game", "Away Game", EXPLORER, "route", "Rigged outside Nottingham.", away_game),
    Badge("new-ground", "New Ground", EXPLORER, "map-pin", "Rigged at 5 different venues.", nth_of("new_venue_dates", 5)),
    Badge("well-travelled", "Well Travelled", EXPLORER, "map", "Rigged at 15 different venues.", nth_of("new_venue_dates", 15)),
    Badge("home-venue", "Home Venue", EXPLORER, "house", "Ten rigs at the same venue.", lambda s: s.venue_reached(10)),

    Badge("behind-the-wheel", "Behind the Wheel", ROAD, "truck", "Your first rig as a driver.", nth_of("drive_dates", 1)),
    Badge("road-warrior", "Road Warrior", ROAD, "truck-fast", "Drove for 25 rigs.", nth_of("drive_dates", 25)),
    Badge("virgils-co-pilot", "Virgil's Co-Pilot", ROAD, "van-shuttle", "Ten trips in Virgil.", vehicle_rigs("virgil", 10)),
    Badge("hitched", "Hitched", ROAD, "trailer", "Towed the trailer.", vehicle_rigs(r"erms|genny|trailer", 1)),

    Badge("first-steps", "First Steps", TRAINING, "seedling", "Your first training item recorded.",
          lambda s: first(q.date for q in s.item_quals)),
    Badge("passed-out", "Passed Out", TRAINING, "graduation-cap", "Your first item passed out.",
          lambda s: first(q.date for q in s.item_quals if q.depth == TrainingItemQualification.PASSED_OUT)),
    Badge("technician", "Technician", TRAINING, "wrench", "Reached Technician in any department.", level(T.TECHNICIAN)),
    # Haulage supervisors aren't RIGS supervisors either (see TrainingLevelQualification.clean)
    Badge("supervisor", "Supervisor", TRAINING, "user-shield", "Reached Supervisor.", level(T.SUPERVISOR, exclude=(T.HAULAGE,))),
    Badge("polymath", "Polymath", TRAINING, "shapes", "Levels in three or more departments.", polymath),

    Badge("sound-technician", "Sound Technician", DEPARTMENTS, "volume-high", "Technician level in Sound.", level(T.TECHNICIAN, T.SOUND)),
    Badge("lighting-technician", "Lighting Technician", DEPARTMENTS, "lightbulb", "Technician level in Lighting.", level(T.TECHNICIAN, T.LIGHTING)),
    Badge("power-technician", "Power Technician", DEPARTMENTS, "bolt-lightning", "Technician level in Power.", level(T.TECHNICIAN, T.POWER)),
    Badge("rigging-technician", "Rigging Technician", DEPARTMENTS, "link", "Technician level in Rigging.", level(T.TECHNICIAN, T.RIGGING)),
    Badge("full-house", "Full House", DEPARTMENTS, "layer-group", "Technician in every department.", full_house),

    Badge("passing-it-on", "Passing It On", TEACHING, "chalkboard-user", "Signed off your first training item.",
          lambda s: first(q.date for q in s.taught_quals)),
    Badge("professor", "Professor", TEACHING, "book-open", "Signed off 50 training items.",
          lambda s: nth([q.date for q in s.taught_quals], 50)),
    Badge("kingmaker", "Kingmaker", TEACHING, "chess-king", "Confirmed someone's training level.", nth_of("levels_confirmed_for_others", 1)),

    Badge("risk-aware", "Risk Aware", SAFETY, "helmet-safety", "Wrote your first risk assessment.", authored(1, RiskAssessment)),
    Badge("risk-assessor", "Risk Assessor", SAFETY, "clipboard-check", "Wrote ten risk assessments.", authored(10, RiskAssessment)),
    Badge("box-ticker", "Box Ticker", SAFETY, "list-check", "Completed your first event checklist.", authored(1, EventChecklist)),
    Badge("live-wire", "Live Wire", SAFETY, "plug-circle-check", "Recorded your first power test.", authored(1, PowerTestRecord)),
    Badge("power-player", "Power Player", SAFETY, "bolt", "Power MIC on a risk assessment or power test.", nth_of("power_mic_dates", 1)),
    Badge("paper-trail", "Paper Trail", SAFETY, "file-shield", "Wrote 50 H&S documents of any kind.", authored(50)),

    Badge("off-grid", "Off Grid", POWER, "gas-pump", "Rigged on generator power.", off_grid),
    Badge("three-phase", "Three-Phase", POWER, "charging-station", "Power MIC on a three-phase supply.", nth_of("three_phase_dates", 1)),
    Badge("big-power", "Big Power", POWER, "tower-broadcast", "Five big-power rigs.", ra_rigs(5, "big_power")),

    Badge("great-outdoors", "Great Outdoors", PRODUCTION, "tree", "Five outdoor rigs.", ra_rigs(5, "outside")),
    Badge("under-canvas", "Under Canvas", PRODUCTION, "tent", "Rigged in a marquee.", quote_rigs("marquee", anywhere=True)),
    Badge("flying-high", "Flying High", PRODUCTION, "helicopter", "Worked on a rig with special structures.",
          ra_rigs(1, "special_structures", "suspended_structures")),
    Badge("turn-it-down", "Turn It Down", PRODUCTION, "volume-xmark", "Rigged where noise was monitored.", ra_rigs(1, "noise_monitoring")),
    Badge("big-rig", "Big Rig", PRODUCTION, "volume-high", "Rigged the big PA.", quote_rigs(r"nexo|alpha")),
    Badge("goalposts", "Goalposts", PRODUCTION, "archway", "Put up truss.", quote_rigs(r"goalpost|tri-?lite|prolyte|truss (box|structure|goal)")),
    Badge("big-ticket", "Big Ticket", PRODUCTION, "sterling-sign", "MIC'd a £2,000+ job.",
          lambda s: first(e.start_date for e in s.mic_events if BIG_TICKET[0] <= s.mic_quote_totals.get(e.pk, 0) < BIG_TICKET[1])),

    Badge("social-butterfly", "Social Butterfly", CREW, "users", "Rigged with 15 different people.", lambda s: s.crewmates_reached(distinct=15)),
    Badge("dynamic-duo", "Dynamic Duo", CREW, "user-group", "Rigged with the same person 20 times.", lambda s: s.crewmates_reached(shared=20)),

    Badge("regular-customer", "Regular Customer", CLIENTS, "handshake", "MIC'd five events for the same client.", clients(same=5)),
    Badge("networker", "Networker", CLIENTS, "address-book", "MIC'd for ten different clients.", clients(different=10)),
    Badge("signed-sealed-delivered", "Signed, Sealed, Delivered", CLIENTS, "file-signature", "MIC'd an event the client authorised online.",
          nth_of("authorised_mic_dates", 1)),

    Badge("society-darling", "Society Darling", COMMUNITY, "heart", "Rigged for ten different societies.", society_darling),
    Badge("outside-booking", "Outside Booking", COMMUNITY, "building", "MIC'd for an external client.",
          lambda s: first(e.start_date for e in s.mic_events if e.organisation_id and not e.organisation.union_account)),

    Badge("quote-machine", "Quote Machine", ADMIN, "file-invoice", "Created 10 events in RIGS.", authored(10, Event)),
    Badge("archivist", "Archivist", ADMIN, "box-archive", "Made 250 changes in RIGS.", nth_of("revisions", 250)),
    Badge("venue-scout", "Venue Scout", ADMIN, "location-dot", "Added a new venue to RIGS.", authored(1, Venue)),

    Badge("asset-wrangler", "Asset Wrangler", STORE, "boxes-stacked", "Added 25 assets to the database.", authored(25, Asset)),
    Badge("curator", "Curator", STORE, "pen-to-square", "Made 50 changes to the assets database.", nth_of("asset_edits", 50)),
    Badge("coil-wrangler", "Coil Wrangler", STORE, "plug", "Made 25 changes to cables in the assets database.", nth_of("cable_edits", 25)),

    Badge("weekend-warrior", "Weekend Warrior", MOMENTS, "calendar-week", "Three rigs in one Fri–Sun.", weekend_warrior),
    Badge("night-owl", "Night Owl", MOMENTS, "moon", "Checked out after midnight.", night_owl),
    Badge("early-call", "Early Call", MOMENTS, "mug-hot", "Checked in before 7am.",
          lambda s: first(c.time for c in s.checkins if timezone.localtime(c.time).hour < 7)),
    Badge("festive-spirit", "Festive Spirit", MOMENTS, "snowflake", "Rigged in the run-up to Christmas.",
          lambda s: first(d for d in s.rig_dates if d.month == 12 and d.day <= 24)),

    Badge("fright-night", "Fright Night", SEASONS, "ghost", "Rigged on Halloween.", on_day(10, 31)),
    Badge("summer-season", "Summer Season", SEASONS, "sun", "Rigged during the summer break.",
          lambda s: first(d for d in s.rig_dates if d.month in (7, 8))),
    Badge("marathon", "Marathon", SEASONS, "person-running", "Crewed an event lasting three days or more.",
          lambda s: first(e.end_date for e in s.rig_events if e.end_date and (e.end_date - e.start_date).days >= 2)),
    Badge("comeback-tour", "Comeback Tour", SEASONS, "rotate-left", "Back on the road after a year away.", comeback),

    Badge("belle-of-the-ball", "Belle of the Ball", TRADITIONS, "champagne-glasses", "Five balls.", named_rigs(r"\bballs?\b", 5)),
    Badge("varsity", "Varsity", TRADITIONS, "flag-checkered", "Rigged a Varsity event.", named_rigs("varsity")),
    Badge("freshers-flu", "Freshers' Flu", TRADITIONS, "head-side-cough", "Rigged Freshers or Welcome Week.", named_rigs("freshers|welcome")),
    Badge("wedding-crasher", "Wedding Crasher", TRADITIONS, "ring", "Rigged a wedding.", named_rigs("wedding")),
    Badge("annual-fixture", "Annual Fixture", TRADITIONS, "calendar-check", "The same event in three different years.", annual_fixture),

    Badge(HEADLINER, "Headliner", NOVELTY, "trophy", "Top of the bill: more badges than anyone else. Yours until someone overtakes you!", None),
]
# fmt: on

BADGES = {badge.slug: badge for badge in _BADGES}
assert len(BADGES) == len(_BADGES), "Badge slugs must be unique"


def badges_by_category():
    return [(category, [b for b in _BADGES if b.category == category]) for category in CATEGORIES]
