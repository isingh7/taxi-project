"""Live headline stats straight from BigQuery (the original feature, reworked).

Changes from the first version:
    * The table name is whitelisted. It used to be put into the SQL unchecked,
      which allowed SQL injection.
    * Nine full-table scans became four. The seven scalar metrics are computed
      in one pass with conditional aggregation. BigQuery bills per column
      scanned, so reading ``total_amount`` once instead of three times (and
      the timestamps once instead of four times) lowers the cost.
    * The BigQuery client is created lazily, so Django starts (and tests run)
      without GCP credentials.
    * Results are cached. The TLC tables are historical and never change.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

from django.core.cache import cache

from taxi_api.constants import BIGQUERY_DATASET, MAX_TRIP_SECONDS, MIN_TRIP_SECONDS
from taxi_api.services.sources import validate_table_name

CACHE_TTL_SECONDS = 24 * 60 * 60

_VALID_TRIP = (
    f"TIMESTAMP_DIFF(dropoff_datetime, pickup_datetime, SECOND) BETWEEN {MIN_TRIP_SECONDS} "
    f"AND {MAX_TRIP_SECONDS}"
)


def build_queries(table: str) -> dict[str, str]:
    table = validate_table_name(table)
    src = f"`{BIGQUERY_DATASET}.{table}`"
    duration_min = "TIMESTAMP_DIFF(dropoff_datetime, pickup_datetime, SECOND) / 60"
    return {
        "scalars": f"""
            SELECT
              ROUND(AVG(IF({_VALID_TRIP}, {duration_min}, NULL)), 2) AS avg_journey_time,
              ROUND(MIN(IF({_VALID_TRIP}, {duration_min}, NULL)), 2) AS min_journey_time,
              ROUND(MAX(IF({_VALID_TRIP}, {duration_min}, NULL)), 2) AS max_journey_time,
              ROUND(AVG(IF(total_amount > 1, total_amount, NULL)), 2) AS avg_total_cost,
              ROUND(MIN(IF(total_amount > 1, total_amount, NULL)), 2) AS min_total_cost,
              ROUND(MAX(IF(total_amount > 1, total_amount, NULL)), 2) AS max_total_cost,
              ROUND(AVG(IF(tip_amount > 0, tip_amount, NULL)), 2)     AS avg_tip_amount
            FROM {src}
        """,
        "most_popular_time_of_day": f"""
            SELECT EXTRACT(HOUR FROM pickup_datetime) AS hour, COUNT(*) AS count
            FROM {src} WHERE {_VALID_TRIP}
            GROUP BY hour ORDER BY count DESC LIMIT 1
        """,
        "most_popular_pickup_location": f"""
            SELECT ROUND(pickup_latitude, 4) AS latitude, ROUND(pickup_longitude, 4) AS longitude,
                   COUNT(*) AS count
            FROM {src}
            WHERE pickup_latitude IS NOT NULL AND pickup_latitude != 0 AND pickup_longitude != 0
            GROUP BY latitude, longitude ORDER BY count DESC LIMIT 1
        """,
        "most_popular_dropoff_location": f"""
            SELECT ROUND(dropoff_latitude, 4) AS latitude, ROUND(dropoff_longitude, 4) AS longitude,
                   COUNT(*) AS count
            FROM {src}
            WHERE dropoff_latitude IS NOT NULL AND dropoff_latitude != 0 AND dropoff_longitude != 0
            GROUP BY latitude, longitude ORDER BY count DESC LIMIT 1
        """,
    }


@lru_cache(maxsize=1)
def _default_client():
    from google.cloud import bigquery

    return bigquery.Client()


def _first_row(client, sql: str) -> dict:
    df = client.query(sql).result().to_dataframe()
    if df.empty:
        return {}
    return {k: (None if v != v else v) for k, v in df.iloc[0].to_dict().items()}  # NaN -> None


def fetch_headline_stats(table: str, client=None) -> dict:
    cache_key = f"bq-headline:{table}"
    if (cached := cache.get(cache_key)) is not None:
        return cached

    client = client or _default_client()
    queries = build_queries(table)
    with ThreadPoolExecutor(max_workers=len(queries)) as pool:
        futures = {key: pool.submit(_first_row, client, sql) for key, sql in queries.items()}
        results = {key: f.result() for key, f in futures.items()}

    scalars = results["scalars"]
    data = {
        **scalars,
        "min_journey_time": max(scalars.get("min_journey_time") or 0, 0),
        "min_total_cost": max(scalars.get("min_total_cost") or 0, 0),
        "most_popular_time_of_day": results["most_popular_time_of_day"],
        "most_popular_pickup_location": results["most_popular_pickup_location"],
        "most_popular_dropoff_location": results["most_popular_dropoff_location"],
    }
    cache.set(cache_key, data, CACHE_TTL_SECONDS)
    return data
