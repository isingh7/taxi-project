"""ETL orchestration: extract -> validate/clean -> enrich -> load, with an audit trail."""

from __future__ import annotations

import logging
from decimal import Decimal

import pandas as pd
from django.db import transaction
from django.utils import timezone

from taxi_api.models import IngestionRun, PaymentType, Trip, Zone
from taxi_api.services.enrichment import enrich, load_payment_types, load_zones
from taxi_api.services.quality import run_quality_checks

logger = logging.getLogger(__name__)

BATCH_SIZE = 5_000


def load_reference_data() -> tuple[int, int]:
    """Upsert the zone and payment-type dimensions from CSV. Safe to run repeatedly."""
    zones = load_zones()
    for row in zones.to_dict("records"):
        Zone.objects.update_or_create(zone_id=row.pop("zone_id"), defaults=row)
    payments = load_payment_types()
    for row in payments.to_dict("records"):
        PaymentType.objects.update_or_create(
            payment_code=row["payment_code"],
            defaults={"payment_label": row["payment_label"], "is_electronic": bool(row["is_electronic"])},
        )
    return len(zones), len(payments)


def _money(value) -> Decimal:
    return Decimal(str(round(float(value), 2)))


def _none_if_na(value):
    return None if pd.isna(value) else value


def _to_models(df: pd.DataFrame, run: IngestionRun, table: str) -> list[Trip]:
    tz = timezone.get_current_timezone()
    trips = []
    for r in df.itertuples(index=False):
        trips.append(
            Trip(
                ingestion_run=run,
                source_table=table,
                pickup_datetime=timezone.make_aware(r.pickup_datetime.to_pydatetime(), tz),
                dropoff_datetime=timezone.make_aware(r.dropoff_datetime.to_pydatetime(), tz),
                passenger_count=None if pd.isna(r.passenger_count) else int(r.passenger_count),
                trip_distance=float(r.trip_distance),
                duration_minutes=float(r.duration_minutes),
                fare_amount=_money(r.fare_amount),
                tip_amount=_money(0 if pd.isna(r.tip_amount) else r.tip_amount),
                total_amount=_money(r.total_amount),
                payment_type_id=int(r.payment_type),
                pickup_zone_id=_none_if_na(r.pickup_zone_id),
                dropoff_zone_id=_none_if_na(r.dropoff_zone_id),
                pickup_latitude=_none_if_na(r.pickup_latitude),
                pickup_longitude=_none_if_na(r.pickup_longitude),
                dropoff_latitude=_none_if_na(r.dropoff_latitude),
                dropoff_longitude=_none_if_na(r.dropoff_longitude),
                is_outlier=bool(r.is_outlier),
            )
        )
    return trips


def run_pipeline(source, replace: bool = True) -> IngestionRun:
    """Run one ingestion. ``replace=True`` makes reloads of the same table idempotent."""
    load_reference_data()
    run = IngestionRun.objects.create(source=source.name, source_table=source.table)
    try:
        raw = source.extract()
        run.rows_extracted = len(raw)
        logger.info("Extracted %s rows from %s:%s", len(raw), source.name, source.table)

        result = run_quality_checks(raw)
        enriched = enrich(result.clean)

        with transaction.atomic():
            if replace:
                Trip.objects.filter(source_table=source.table).exclude(ingestion_run=run).delete()
            Trip.objects.bulk_create(_to_models(enriched, run, source.table), batch_size=BATCH_SIZE)

        run.rows_loaded = len(enriched)
        run.rows_rejected = len(result.rejected)
        run.quality_report = result.report
        run.status = IngestionRun.Status.SUCCESS
    except Exception as exc:
        logger.exception("Ingestion failed")
        run.status = IngestionRun.Status.FAILED
        run.error_message = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        run.finished_at = timezone.now()
        run.save()
    return run
