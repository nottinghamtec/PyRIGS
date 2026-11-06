from django.core.management.base import BaseCommand

from assets import models, pat
from assets.sss import SSSParseError


class Command(BaseCommand):
    help = "Re-reads each uploaded PAT file and brings its recorded results up to date with what the parser now decodes"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report what would change without changing anything")

    def handle(self, *args, **options):
        total = 0
        counted = set()  # a dry run writes nothing, so records in overlapping files would be counted twice
        for batch in models.PATTestBatch.objects.order_by("id"):
            try:
                if options["dry_run"]:
                    plan = pat.plan_reprocess(batch, refresh=True)
                    pks = {current.pk for current, _ in plan.replacements} - counted
                    counted |= pks
                    updated, added = len(pks), len(plan.new)
                else:
                    summary = pat.reprocess(batch, None, refresh=True)
                    updated, added = len(summary.replaced), len(summary.imported)
            except (OSError, ValueError, SSSParseError) as error:
                self.stderr.write(f"{batch.original_filename}: skipped, couldn't read the stored file ({error})")
                continue
            total += updated + added
            self.stdout.write(f"{batch.original_filename}: {updated} updated, {added} added")
        verb = "would be changed" if options["dry_run"] else "changed"
        self.stdout.write(f"{total} results {verb}")
