from django.core.management.base import BaseCommand

from assets import models, pat
from assets.sss import SSSParseError


class Command(BaseCommand):
    help = "Re-reads each uploaded PAT file and brings its recorded results up to date with what the parser now decodes"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report what would change without changing anything")

    def handle(self, *args, **options):
        total = 0
        total_kept = 0
        counted_unmatched = set()
        counted = set()  # a dry run writes nothing, so records in overlapping files would be counted twice
        for batch in models.PATTestBatch.objects.order_by("id"):
            try:
                if options["dry_run"]:
                    plan = pat.plan_reprocess(batch, refresh=True)
                    pks = {current.pk for current, _ in plan.replacements} - counted
                    counted |= pks
                    updated, added = len(pks), len(plan.new)
                    keys = {(result.asset_id, result.tested_at) for result in plan.new_unmatched} - counted_unmatched
                    counted_unmatched |= keys
                    kept = len(keys)
                else:
                    summary = pat.reprocess(batch, None, refresh=True)
                    updated, added = len(summary.replaced), len(summary.imported)
                    kept = len(summary.kept)
            except (OSError, ValueError, SSSParseError) as error:
                self.stderr.write(f"{batch.original_filename}: skipped, couldn't read the stored file ({error})")
                continue
            total += updated + added
            total_kept += kept
            self.stdout.write(f"{batch.original_filename}: {updated} updated, {added} added, {kept} unmatched kept")
        verb = "would be changed" if options["dry_run"] else "changed"
        self.stdout.write(f"{total} results {verb}")
        verb = "would be kept" if options["dry_run"] else "kept"
        self.stdout.write(f"{total_kept} results for assets not in RIGS {verb}")
