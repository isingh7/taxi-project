import csv
import logging
import time

from django.conf import settings
from django.db.models import Count, Max
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from taxi_api.constants import ALLOWED_TABLES
from taxi_api.models import IngestionRun, Trip
from taxi_api.serializers import IngestionRunSerializer, TaxiTripSerializer
from taxi_api.services import bigquery_live, reports

logger = logging.getLogger(__name__)


def _unknown_table(table):
    return Response(
        {"detail": f"Unknown table '{table}'.", "allowed_tables": list(ALLOWED_TABLES)},
        status=status.HTTP_404_NOT_FOUND,
    )


def _not_loaded(table):
    return Response(
        {
            "detail": f"No data loaded for '{table}'.",
            "hint": f"python manage.py ingest_trips --table {table} --source synthetic",
        },
        status=status.HTTP_404_NOT_FOUND,
    )


@api_view(["GET"])
def health(request):
    return Response({"status": "ok", "trips_loaded": Trip.objects.count()})


@api_view(["GET"])
def list_tables(request):
    loaded = {
        row["source_table"]: row
        for row in Trip.objects.values("source_table").annotate(
            trips=Count("id"), latest_pickup=Max("pickup_datetime")
        )
    }
    return Response(
        [
            {
                "table": t,
                "loaded": t in loaded,
                "trips": loaded.get(t, {}).get("trips", 0),
            }
            for t in ALLOWED_TABLES
        ]
    )


@api_view(["GET"])
def get_data(request, table_name):
    """Headline stats. ``?source=bigquery|local|auto`` (default ``auto``).

    ``auto`` tries BigQuery first and falls back to the local store, so the UI
    keeps working without GCP credentials or when BigQuery quota runs out.
    """
    if table_name not in ALLOWED_TABLES:
        return _unknown_table(table_name)
    source = request.query_params.get("source", "auto")
    started = time.perf_counter()

    data, data_source = None, None
    use_bigquery = source == "bigquery" or (source == "auto" and settings.BIGQUERY_ENABLED)
    if use_bigquery:
        try:
            data, data_source = bigquery_live.fetch_headline_stats(table_name), "bigquery"
        except Exception as exc:  # credentials missing, quota, network...
            logger.warning("BigQuery unavailable for %s: %s", table_name, exc)
            if source == "bigquery":
                return Response(
                    {"detail": "BigQuery is unavailable.", "error": str(exc)},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
    if data is None:
        data, data_source = reports.local_headline_stats(table_name), "local"
        if data is None:
            return _not_loaded(table_name)

    serializer = TaxiTripSerializer(data={**data, "data_source": data_source})
    serializer.is_valid(raise_exception=True)
    logger.info("get_data(%s) via %s in %.2fs", table_name, data_source, time.perf_counter() - started)
    return Response(serializer.data)


@api_view(["GET"])
def analytics_view(request, table_name):
    if table_name not in ALLOWED_TABLES:
        return _unknown_table(table_name)
    payload = reports.analytics_payload(table_name)
    if payload is None:
        return _not_loaded(table_name)
    return Response(payload)


@api_view(["GET"])
def daily_revenue_csv(request, table_name):
    """CSV download of the daily revenue series, for finance users who work in Excel."""
    if table_name not in ALLOWED_TABLES:
        return _unknown_table(table_name)
    payload = reports.analytics_payload(table_name)
    if payload is None:
        return _not_loaded(table_name)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{table_name}_daily_revenue.csv"'
    rows = payload["daily"]
    if rows:
        writer = csv.DictWriter(response, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return response


@api_view(["GET"])
def data_quality(request, table_name):
    if table_name not in ALLOWED_TABLES:
        return _unknown_table(table_name)
    run = IngestionRun.objects.filter(source_table=table_name).order_by("-started_at").first()
    if run is None:
        return _not_loaded(table_name)
    return Response(IngestionRunSerializer(run).data)


@api_view(["GET"])
def ingestion_runs(request):
    runs = IngestionRun.objects.all()[:50]
    return Response(IngestionRunSerializer(runs, many=True).data)
