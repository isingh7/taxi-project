from django.core.management.base import BaseCommand, CommandError

from taxi_api.constants import ALLOWED_TABLES
from taxi_api.services.etl import run_pipeline
from taxi_api.services.sources import get_source


class Command(BaseCommand):
    help = "Extract, validate, enrich and load taxi trips into the local analytics store."

    def add_arguments(self, parser):
        parser.add_argument("--source", choices=["synthetic", "bigquery", "csv"], default="synthetic")
        parser.add_argument("--table", default="tlc_yellow_trips_2015",
                            help="TLC table name (use --all for every table)")
        parser.add_argument("--all", action="store_true", help="Load every allowed table")
        parser.add_argument("--rows", type=int, default=20_000)
        parser.add_argument("--path", help="CSV file path (csv source only)")
        parser.add_argument("--seed", type=int, default=42)

    def handle(self, *args, **opts):
        tables = ALLOWED_TABLES if opts["all"] else [opts["table"]]
        for table in tables:
            try:
                source = get_source(opts["source"], table, rows=opts["rows"],
                                    path=opts["path"], seed=opts["seed"])
                run = run_pipeline(source)
            except Exception as exc:
                raise CommandError(f"{table}: {exc}") from exc

            report = run.quality_report
            self.stdout.write(self.style.SUCCESS(
                f"{table}: extracted {run.rows_extracted:,}, loaded {run.rows_loaded:,}, "
                f"rejected {run.rows_rejected:,} (pass rate {report['pass_rate_pct']}%)"
            ))
            for rule in report["rules"]:
                if rule["rows_affected"]:
                    self.stdout.write(
                        f"    [{rule['action']:<6}] {rule['rule']:<26} {rule['rows_affected']:>6,}"
                        f"  ({rule['pct_of_input']}%)"
                    )
