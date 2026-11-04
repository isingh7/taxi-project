import pandas as pd
import pytest

from taxi_api.models import IngestionRun, PaymentType, Trip, Zone
from taxi_api.services import sql_reports
from taxi_api.services.etl import load_reference_data, run_pipeline
from taxi_api.services.sources import SyntheticSource

from .conftest import TABLE


@pytest.mark.django_db
def test_reference_data_load_is_idempotent():
    assert load_reference_data() == (9, 6)
    load_reference_data()
    assert Zone.objects.count() == 9 and PaymentType.objects.count() == 6


@pytest.mark.django_db
def test_pipeline_records_audit_trail(loaded_table):
    run = IngestionRun.objects.get()
    assert run.status == IngestionRun.Status.SUCCESS
    assert run.rows_loaded == Trip.objects.count() > 0
    assert run.rows_extracted >= run.rows_loaded + run.rows_rejected
    assert run.quality_report["rows_clean"] == run.rows_loaded
    assert run.finished_at is not None


@pytest.mark.django_db
def test_reload_replaces_instead_of_duplicating(loaded_table):
    first = Trip.objects.count()
    run_pipeline(SyntheticSource(table=TABLE, rows=1_500, seed=7))
    assert Trip.objects.count() == first
    assert IngestionRun.objects.count() == 2


@pytest.mark.django_db
def test_failed_extract_is_recorded():
    class Broken:
        name, table = "bigquery", TABLE

        def extract(self):
            raise ConnectionError("quota exceeded")

    with pytest.raises(ConnectionError):
        run_pipeline(Broken())
    run = IngestionRun.objects.get()
    assert run.status == IngestionRun.Status.FAILED
    assert "quota exceeded" in run.error_message


@pytest.mark.django_db
def test_trips_dataframe_joins_reference_data(loaded_table):
    df = sql_reports.trips_dataframe(loaded_table)
    assert len(df) == Trip.objects.count()
    assert set(df["payment_label"]) <= set(PaymentType.objects.values_list("payment_label", flat=True))
    assert pd.api.types.is_datetime64_any_dtype(df["pickup_datetime"])
    assert "Manhattan" in set(df["pickup_borough"])


@pytest.mark.django_db
def test_borough_league_table_reconciles_with_orm(loaded_table):
    rows = sql_reports.borough_league_table(loaded_table)
    assert [r["revenue_rank"] for r in rows] == sorted(r["revenue_rank"] for r in rows)
    assert sum(r["trips"] for r in rows) == Trip.objects.count()
    assert sum(float(r["revenue_share_pct"]) for r in rows) == pytest.approx(100, abs=0.1)
    orm_total = sum(float(t) for t in Trip.objects.values_list("total_amount", flat=True))
    assert sum(float(r["revenue"]) for r in rows) == pytest.approx(orm_total, abs=1)


@pytest.mark.django_db
def test_top_routes_limit_and_order(loaded_table):
    routes = sql_reports.top_routes(loaded_table, limit=3)
    assert len(routes) == 3
    assert routes[0]["trips"] >= routes[1]["trips"] >= routes[2]["trips"]


@pytest.mark.django_db
def test_popular_location_rejects_unknown_column(loaded_table):
    assert sql_reports.most_popular_location(loaded_table, "pickup")["count"] > 0
    with pytest.raises(ValueError):
        sql_reports.most_popular_location(loaded_table, "pickup_latitude; --")
