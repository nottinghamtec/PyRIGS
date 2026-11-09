from django.core.management.base import BaseCommand

from notifications import scheduled
from notifications.dispatch import deliver_pending


class Command(BaseCommand):
    help = (
        "Queues time-based notifications and delivers everything waiting. Run every minute through cron in production."
    )

    def add_arguments(self, parser):
        parser.add_argument("--quiet", action="store_true", help="Say nothing unless something was queued or sent")

    def handle(self, *args, **options):
        queued = scheduled.queue_all()
        delivered = deliver_pending()
        if not options["quiet"] or delivered or any(queued.values()):
            summary = ", ".join(f"{name.removeprefix('queue_')}: {count}" for name, count in queued.items())
            self.stdout.write(f"Queued {summary}. Delivered {delivered}.")
