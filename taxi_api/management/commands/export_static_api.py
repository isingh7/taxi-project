"""Export API responses as static JSON so the React app can run without a server.

Used to publish a read-only demo (e.g. GitHub Pages). The responses come from the
real endpoints via Django's test client, so the demo matches the live API exactly.

    python manage.py export_static_api --out taxi_frontend/public/demo-data
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.test import Client, override_settings

from taxi_api.constants import ALLOWED_TABLES


class Command(BaseCommand):
    help = "Write the API's JSON responses to static files for a server-less demo."

    def add_arguments(self, parser):
        parser.add_argument("--out", required=True, help="Output directory")

    @override_settings(BIGQUERY_ENABLED=False, ALLOWED_HOSTS=["testserver"])
    def handle(self, *args, **opts):
        out = Path(opts["out"])
        client = Client()

        def save(api_path: str, file_path: str, as_json: bool = True) -> None:
            resp = client.get(f"/api/{api_path}")
            if resp.status_code != 200:
                raise CommandError(f"/api/{api_path} returned {resp.status_code}")
            target = out / file_path
            target.parent.mkdir(parents=True, exist_ok=True)
            if as_json:
                target.write_text(json.dumps(resp.json(), separators=(",", ":")), encoding="utf-8")
            else:
                target.write_bytes(resp.content)

        tables = client.get("/api/tables/").json()
        save("tables/", "tables.json")
        save("ingestion-runs/", "ingestion-runs.json")

        loaded = [t["table"] for t in tables if t["loaded"]]
        if not loaded:
            raise CommandError("No tables loaded. Run `manage.py ingest_trips --all` first.")
        for table in loaded:
            if table not in ALLOWED_TABLES:
                continue
            save(f"data/{table}/", f"data/{table}.json")
            save(f"analytics/{table}/", f"analytics/{table}.json")
            save(f"analytics/{table}/daily.csv", f"analytics/{table}/daily.csv", as_json=False)
            save(f"data-quality/{table}/", f"data-quality/{table}.json")

        size_kb = sum(p.stat().st_size for p in out.rglob("*") if p.is_file()) / 1024
        self.stdout.write(self.style.SUCCESS(
            f"Exported {len(loaded)} tables to {out} ({size_kb:,.0f} KB)"
        ))
