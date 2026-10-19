from collections import defaultdict

from django.contrib.auth.models import Permission
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views import generic

from RIGS.models import EventChecklist, PowerTestRecord, Profile, RiskAssessment

from badges.models import BadgeAward, BadgeSettings
from badges.registry import BADGES, HEADLINER, badges_by_category
from badges.stats import ProfileStats


def granted(user, codename):
    """
    Whether someone has actually been given a badges permission, directly or through a group.

    has_perm() is always true for superusers, but superusers only get early access if the settings allow it, or if
    they're given the permission like anyone else.
    """
    if not user.is_superuser:
        return user.has_perm(f"badges.{codename}")
    return (
        Permission.objects.filter(content_type__app_label="badges", codename=codename)
        .filter(Q(user=user) | Q(group__user=user))
        .exists()
    )


def badges_visible(user, settings=None):
    """Everyone once badges are live; before that, anyone given View Badges, and superusers if the settings allow."""
    settings = settings or BadgeSettings.load()
    return settings.badges_live or (user.is_superuser and settings.badges_superusers) or granted(user, "view_badges")


def tech_rider_visible(user, settings=None):
    """Everyone once Tech Rider is live; before that, anyone given View Tech Rider, and superusers if allowed."""
    settings = settings or BadgeSettings.load()
    return (
        settings.tech_rider_live
        or (user.is_superuser and settings.tech_rider_superusers)
        or granted(user, "view_tech_rider")
    )


class BadgesVisibleMixin:
    def dispatch(self, request, *args, **kwargs):
        self.settings = BadgeSettings.load()
        if not badges_visible(request.user, self.settings):
            raise Http404
        return super().dispatch(request, *args, **kwargs)


class BadgeList(BadgesVisibleMixin, generic.TemplateView):
    template_name = "badges/badge_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        holders = defaultdict(list)
        for award in BadgeAward.objects.select_related("profile").order_by("awarded_at"):
            holders[award.slug].append(award)
        mine = {award.slug: award for award in BadgeAward.objects.filter(profile=self.request.user)}
        context["categories"] = [
            (
                category,
                [(badge, holders[badge.slug], mine.get(badge.slug)) for badge in badges],
                sum(1 for badge in badges if badge.slug in mine),
            )
            for category, badges in badges_by_category()
        ]
        context["earned_count"] = len(mine)
        context["badge_count"] = len(BADGES)
        context["preview"] = not self.settings.badges_live
        context["page_title"] = "Badges"
        return context


class Leaderboard(BadgesVisibleMixin, generic.TemplateView):
    template_name = "badges/leaderboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        counts = (
            BadgeAward.objects.filter(profile__is_active=True)
            .exclude(slug=HEADLINER)  # Doesn't count towards itself
            .values("profile")
            .annotate(badges=Count("id"))
            .order_by("-badges", "profile__first_name", "profile__last_name")
        )
        people = Profile.objects.in_bulk([row["profile"] for row in counts])
        headliners = set(BadgeAward.objects.filter(slug=HEADLINER).values_list("profile", flat=True))
        top = counts[0]["badges"] if counts else 0
        rows, previous = [], None
        for position, row in enumerate(counts, start=1):
            if row["badges"] != previous:
                rank, previous = position, row["badges"]
            rows.append(
                {
                    "rank": rank,
                    "tied": sum(1 for other in counts if other["badges"] == row["badges"]) > 1,
                    "profile": people[row["profile"]],
                    "badges": row["badges"],
                    "width": round(100 * row["badges"] / top),
                    "headliner": row["profile"] in headliners,
                }
            )
        context.update(
            {
                "rows": rows,
                "preview": not self.settings.badges_live,
                "headliner": BADGES[HEADLINER],
                "page_title": "Badge Leaderboard",
            }
        )
        return context


class TechRider(generic.TemplateView):
    template_name = "badges/tech_rider.html"

    def dispatch(self, request, *args, **kwargs):
        self.settings = BadgeSettings.load()
        if not tech_rider_visible(request.user, self.settings):
            raise Http404
        pk = kwargs.get("pk", request.user.pk)
        # Members can only see their own; superusers can look at anyone's to check it's right
        if pk != request.user.pk and not request.user.is_superuser:
            raise Http404
        self.profile = get_object_or_404(Profile, pk=pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stats = ProfileStats(self.profile)
        show_badges = badges_visible(self.request.user, self.settings)
        awards = [award for award in self.profile.badge_awards.all() if award.badge] if show_badges else []

        timeline = [
            (timezone.localtime(award.awarded_at).date(), award.badge.icon, award.badge.name, award.badge.blurb)
            for award in awards
        ]
        timeline += [
            (
                timezone.localtime(qual.confirmed_on).date(),
                "graduation-cap",
                str(qual.level),
                "Training level confirmed.",
            )
            for qual in stats.level_quals
        ]
        if stats.first_rig:
            timeline.append((stats.first_rig.start_date, "play", "First rig", str(stats.first_rig)))
        timeline.sort(key=lambda entry: entry[0])

        first_rig, first_mic = stats.first_rig, stats.mic_events[0] if stats.mic_events else None
        inputs = [
            ("Rigs", len(stats.rig_events), f"First: {first_rig.name}" if first_rig else None),
            ("Hours on site", round(stats.total_hours), None),
            ("Events as MIC", len(stats.mic_events), None),
            ("Venues played", len(stats.new_venue_dates), None),
            ("Rigs driven", len(stats.drive_dates), None),
            ("Training items learned", len(stats.item_quals), None),
            ("Items signed off for others", len(stats.taught_quals), None),
            ("Training levels reached", len(stats.level_quals), None),
            ("Risk assessments written", len(stats.authored(RiskAssessment)), None),
            ("Event checklists completed", len(stats.authored(EventChecklist)), None),
            ("Power tests recorded", len(stats.authored(PowerTestRecord)), None),
        ]

        notes = []
        if first_rig:
            venue = f" at {first_rig.venue}" if first_rig.venue else ""
            notes.append(
                (
                    "Debut performance",
                    f"{first_rig.name}, {first_rig.start_date:%-d %B %Y}{venue}",
                    first_rig.get_absolute_url(),
                )
            )
        if first_mic:
            notes.append(
                (
                    "First headline (MIC)",
                    f"{first_mic.name}, {first_mic.start_date:%B %Y}",
                    first_mic.get_absolute_url(),
                )
            )
        if stats.longest_shift:
            event = stats.longest_shift[0].event
            notes.append(
                ("Longest day", f"{stats.longest_shift_hours:.1f} hours on {event.name}", event.get_absolute_url())
            )
        if stats.biggest_rig and stats.biggest_rig.crew_count > 1:
            rig = stats.biggest_rig
            notes.append(("Biggest call", f"{rig.crew_count} crew on {rig.name}", rig.get_absolute_url()))
        this_year = stats.this_year
        notes.append(
            (
                f"This season ({this_year['label']})",
                f"{this_year['rigs']} rigs, {this_year['mics']} as MIC, "
                f"{this_year['new_venues']} new venues, {this_year['skills']} new skills",
                None,
            )
        )

        top_level = max(stats.level_quals, key=lambda qual: (qual.level.level, qual.confirmed_on), default=None)
        max_year = max((count for _, count in stats.rigs_by_year), default=0)
        context.update(
            {
                "subject": self.profile,
                "stats": stats,
                "awards": awards,
                "show_badges": show_badges,
                "timeline": timeline,
                "rigs_by_year": [(year, count, round(100 * count / max_year)) for year, count in stats.rigs_by_year],
                "inputs": inputs,
                "notes": notes,
                "position": str(top_level.level) if top_level else "Crew",
                "home_venue": stats.venue_counts[0] if stats.venue_counts else None,
                "preview": not self.settings.tech_rider_live,
                "page_title": f"Tech Rider: {self.profile.first_name or self.profile}",
            }
        )
        return context
