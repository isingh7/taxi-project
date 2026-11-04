from unittest import mock

import pandas as pd
import pytest
from rest_framework.test import APIClient

from taxi_api.services import bigquery_live

from .conftest import TABLE


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
def test_health(client):
    assert client.get("/api/health/").json()["status"] == "ok"


@pytest.mark.django_db
def test_tables_lists_load_status(client, loaded_table):
    tables = {t["table"]: t for t in client.get("/api/tables/").json()}
    assert len(tables) == 12
    assert tables[TABLE]["loaded"] and tables[TABLE]["trips"] > 0
    assert not tables["tlc_green_trips_2013"]["loaded"]


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["data", "analytics", "data-quality"])
def test_unknown_table_is_404_not_500(client, path):
    resp = client.get(f"/api/{path}/users;DROP TABLE x/")
    assert resp.status_code == 404
    assert "allowed_tables" in resp.json()


@pytest.mark.django_db
def test_get_data_falls_back_to_local_store(client, loaded_table, settings):
    settings.BIGQUERY_ENABLED = False
    body = client.get(f"/api/data/{TABLE}/").json()
    assert body["data_source"] == "local"
    assert body["min_journey_time"] <= body["avg_journey_time"] <= body["max_journey_time"]
    assert 0 <= body["most_popular_time_of_day"]["hour"] <= 23
    assert body["most_popular_pickup_location"]["count"] > 0


@pytest.mark.django_db
def test_get_data_auto_falls_back_when_bigquery_errors(client, loaded_table, settings):
    settings.BIGQUERY_ENABLED = True
    with mock.patch.object(bigquery_live, "fetch_headline_stats", side_effect=RuntimeError("no creds")):
        assert client.get(f"/api/data/{TABLE}/").json()["data_source"] == "local"
        assert client.get(f"/api/data/{TABLE}/?source=bigquery").status_code == 503


@pytest.mark.django_db
def test_get_data_not_loaded_gives_actionable_hint(client, settings):
    settings.BIGQUERY_ENABLED = False
    resp = client.get("/api/data/tlc_green_trips_2014/")
    assert resp.status_code == 404
    assert "ingest_trips" in resp.json()["hint"]


@pytest.mark.django_db
def test_get_data_uses_bigquery_when_available(client, settings):
    settings.BIGQUERY_ENABLED = True
    fake = {
        "avg_journey_time": 12.5, "min_journey_time": 1.0, "max_journey_time": 200.0,
        "avg_total_cost": 15.2, "min_total_cost": 2.5, "max_total_cost": 300.0, "avg_tip_amount": 2.1,
        "most_popular_time_of_day": {"hour": 19, "count": 10},
        "most_popular_pickup_location": {"latitude": 40.75, "longitude": -73.99, "count": 5},
        "most_popular_dropoff_location": {"latitude": 40.76, "longitude": -73.98, "count": 4},
    }
    with mock.patch.object(bigquery_live, "fetch_headline_stats", return_value=fake):
        body = client.get(f"/api/data/{TABLE}/").json()
    assert body["data_source"] == "bigquery" and body["avg_journey_time"] == 12.5


@pytest.mark.django_db
def test_analytics_payload(client, loaded_table):
    body = client.get(f"/api/analytics/{TABLE}/").json()
    assert set(body) >= {"kpis", "hourly", "daily", "payment_mix", "boroughs", "top_routes"}
    assert len(body["hourly"]) == 24
    assert body["kpis"]["trips"] == sum(b["trips"] for b in body["boroughs"])


@pytest.mark.django_db
def test_daily_csv_export(client, loaded_table):
    resp = client.get(f"/api/analytics/{TABLE}/daily.csv")
    assert resp["Content-Type"] == "text/csv"
    lines = resp.content.decode().strip().splitlines()
    assert lines[0].startswith("date,revenue,trips,rolling_mean")
    assert len(lines) > 30


@pytest.mark.django_db
def test_data_quality_and_runs(client, loaded_table):
    dq = client.get(f"/api/data-quality/{TABLE}/").json()
    assert dq["status"] == "success"
    assert any(r["action"] == "reject" for r in dq["quality_report"]["rules"])
    assert len(client.get("/api/ingestion-runs/").json()) == 1


class FakeJob:
    def __init__(self, df):
        self._df = df

    def result(self):
        return self

    def to_dataframe(self):
        return self._df


class FakeBigQuery:
    def __init__(self):
        self.calls = []

    def query(self, sql):
        self.calls.append(sql)
        if "avg_journey_time" in sql:
            return FakeJob(pd.DataFrame([{
                "avg_journey_time": 12.0, "min_journey_time": -3.0, "max_journey_time": 90.0,
                "avg_total_cost": 15.0, "min_total_cost": 2.5, "max_total_cost": 99.0,
                "avg_tip_amount": float("nan"),
            }]))
        if "EXTRACT(HOUR" in sql:
            return FakeJob(pd.DataFrame([{"hour": 19, "count": 100}]))
        return FakeJob(pd.DataFrame([{"latitude": 40.75, "longitude": -73.99, "count": 7}]))


def test_bigquery_uses_four_queries_and_caches():
    fake = FakeBigQuery()
    data = bigquery_live.fetch_headline_stats(TABLE, client=fake)
    assert len(fake.calls) == 4
    assert all(f"bigquery-public-data.new_york.{TABLE}" in sql for sql in fake.calls)
    assert data["min_journey_time"] == 0  # negative clamp
    assert data["avg_tip_amount"] is None  # NaN -> None
    bigquery_live.fetch_headline_stats(TABLE, client=fake)
    assert len(fake.calls) == 4  # second call served from cache


def test_bigquery_rejects_unknown_table():
    with pytest.raises(ValueError):
        bigquery_live.build_queries("x` UNION SELECT 1 --")
