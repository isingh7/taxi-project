"""Builds the API payloads by combining the SQL layer and the pandas analytics layer."""

from __future__ import annotations

from django.core.cache import cache

from taxi_api.models import IngestionRun
from taxi_api.services import analytics, sql_reports


def latest_successful_run(table: str) -> IngestionRun | None:
    return (
        IngestionRun.objects.filter(source_table=table, status=IngestionRun.Status.SUCCESS)
        .order_by("-started_at")
        .first()
    )


def _cache_key(prefix: str, table: str) -> str | None:
    run = latest_successful_run(table)
    # Keyed on the run id: a new load gets a new key, so stale data is never served.
    return f"{prefix}:{table}:{run.pk}" if run else None


def analytics_payload(table: str) -> dict | None:
    key = _cache_key("analytics", table)
    if key is None:
        return None
    if (cached := cache.get(key)) is not None:
        return cached

    df = sql_reports.trips_dataframe(table)
    payload = {
        "table": table,
        "kpis": analytics.summary_kpis(df),
        "hourly": analytics.hourly_demand(df),
        "daily": analytics.daily_revenue(df),
        "payment_mix": analytics.payment_mix(df),
        "fare_distribution": analytics.fare_distribution(df),
        "boroughs": sql_reports.borough_league_table(table),
        "top_routes": sql_reports.top_routes(table, limit=10),
    }
    cache.set(key, payload, 60 * 60)
    return payload


def local_headline_stats(table: str) -> dict | None:
    """Same contract as the BigQuery headline stats, computed from the local store."""
    df = sql_reports.trips_dataframe(table)
    if df.empty:
        return None
    tips = df.loc[df["tip_amount"] > 0, "tip_amount"]
    return {
        "avg_journey_time": round(df["duration_minutes"].mean(), 2),
        "min_journey_time": round(df["duration_minutes"].min(), 2),
        "max_journey_time": round(df["duration_minutes"].max(), 2),
        "avg_total_cost": round(df["total_amount"].mean(), 2),
        "min_total_cost": round(df["total_amount"].min(), 2),
        "max_total_cost": round(df["total_amount"].max(), 2),
        "avg_tip_amount": round(tips.mean(), 2) if not tips.empty else 0.0,
        "most_popular_time_of_day": analytics.peak_hour(df),
        "most_popular_pickup_location": sql_reports.most_popular_location(table, "pickup"),
        "most_popular_dropoff_location": sql_reports.most_popular_location(table, "dropoff"),
    }
