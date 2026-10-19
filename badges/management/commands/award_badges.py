from collections import Counter

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from RIGS.models import Profile

from badges.awarding import award_badges, send_badge_emails
from badges.models import BadgeAward, BadgeSettings


class Command(BaseCommand):
    help = (
        "Awards any badges people have earned, then emails people about new ones. Run regularly "
        "through sys cron in production. Awards are made whether or not badges are live; the 'badges live' setting "
        "controls who can "
        "see them, and nothing is emailed until it is on."
    )

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Show what would happen without saving or sending")
        parser.add_argument(
            "--reset", action="store_true", help="Remove existing awards and recompute them all (never emailed)"
        )
        parser.add_argument("--user", help="Only consider this username")
        parser.add_argument("--no-email", action="store_true", help="Award badges but don't send any emails")
        parser.add_argument(
            "--as-if-live",
            action="store_true",
            help="With --dry-run, show what would happen if badges were live, including emails",
        )
        parser.add_argument("--quiet", action="store_true", help="Only print the summary")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        if options["as_if_live"] and not dry_run:
            raise CommandError("--as-if-live can only be used with --dry-run")
        live = True if options["as_if_live"] else BadgeSettings.load().badges_live
        profiles = Profile.objects.all()
        if options["user"]:
            profiles = profiles.filter(username=options["user"])
            if not profiles.exists():
                raise CommandError(f"No user called {options['user']}")

        awards = award_badges(profiles, dry_run=dry_run, reset=options["reset"], live=live)

        verb = "Would award" if dry_run else "Awarded"
        if not options["quiet"]:
            for profile, badge, achieved, emailed in awards:
                note = ", queued for email" if emailed else ""
                self.stdout.write(
                    f"{verb} {badge.name} to {profile} (achieved {timezone.localtime(achieved):%Y-%m-%d}{note})"
                )

        people = len({profile.pk for profile, *_ in awards})
        queued = sum(1 for *_, emailed in awards if emailed)
        self.stdout.write(f"{verb} {len(awards)} badge(s) to {people} person/people, {queued} queued for email.")
        for name, count in Counter(badge.name for _, badge, *_ in awards).most_common():
            self.stdout.write(f"  {name}: {count}")

        if not live:
            self.stdout.write(
                "Badges are not live: only people with View Badges (and superusers, if allowed) can see these awards, "
                "and no emails are sent."
            )
            return
        if options["no_email"]:
            return

        # A dry run didn't save today's awards, so preview them alongside any already waiting
        extra = [
            BadgeAward(profile=profile, slug=badge.slug, awarded_at=achieved)
            for profile, badge, achieved, emailed in awards
            if dry_run and emailed
        ]
        results = send_badge_emails(dry_run=dry_run, live=live, extra=extra)
        for profile, profile_awards, outcome in results:
            names = ", ".join(award.badge.name for award in profile_awards)
            self.stdout.write(f"Email to {profile} ({outcome}): {names}")
        outcomes = Counter(outcome for *_, outcome in results)
        self.stdout.write("Emails: " + (", ".join(f"{n} {o}" for o, n in outcomes.items()) or "none to send"))
