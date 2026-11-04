"""SQL reporting layer: hand-written SQL against the relational store.

The ORM covers the CRUD. These reports use joins, CTEs and window functions,
which are clearer in plain SQL. Values are cast to NUMERIC before ROUND because
PostgreSQL has no ROUND(double precision, int). Every query is parameterised (``%s``) and
written in the subset of SQL that SQLite (local dev) and PostgreSQL (AWS RDS)
both support.
"""

from __future__ import annotations

import pandas as pd
from django.db import connection

TRIPS_SQL = """
    SELECT
        t.pickup_datetime,
        t.dropoff_datetime,
        t.passenger_count,
        t.trip_distance,
        t.duration_minutes,
        CAST(t.fare_amount AS NUMERIC)  AS fare_amount,
        CAST(t.tip_amount AS NUMERIC)   AS tip_amount,
        CAST(t.total_amount AS NUMERIC) AS total_amount,
        t.is_outlier,
        pt.payment_label,
        COALESCE(pz.borough, 'Unknown') AS pickup_borough,
        COALESCE(dz.borough, 'Unknown') AS dropoff_borough,
        pz.zone_name AS pickup_zone
    FROM taxi_api_trip t
    JOIN taxi_api_paymenttype pt ON pt.payment_code = t.payment_type_id
    LEFT JOIN taxi_api_zone pz   ON pz.zone_id = t.pickup_zone_id
    LEFT JOIN taxi_api_zone dz   ON dz.zone_id = t.dropoff_zone_id
    WHERE t.source_table = %s
"""

BOROUGH_LEAGUE_SQL = """
    WITH borough_totals AS (
        SELECT
            COALESCE(z.borough, 'Unknown')     AS borough,
            COUNT(*)                           AS trips,
            SUM(CAST(t.total_amount AS NUMERIC))  AS revenue,
            AVG(CAST(t.fare_amount AS NUMERIC))   AS avg_fare,
            AVG(CASE WHEN pt.is_electronic AND t.fare_amount > 0
                     THEN 1.0 * CAST(t.tip_amount AS NUMERIC) / CAST(t.fare_amount AS NUMERIC) END) AS avg_card_tip_ratio
        FROM taxi_api_trip t
        JOIN taxi_api_paymenttype pt ON pt.payment_code = t.payment_type_id
        LEFT JOIN taxi_api_zone z ON z.zone_id = t.pickup_zone_id
        WHERE t.source_table = %s
        GROUP BY COALESCE(z.borough, 'Unknown')
    )
    SELECT
        borough,
        trips,
        ROUND(revenue, 2)                                         AS revenue,
        ROUND(avg_fare, 2)                                        AS avg_fare,
        ROUND(100.0 * avg_card_tip_ratio, 2)                      AS avg_card_tip_pct,
        ROUND(100.0 * revenue / SUM(revenue) OVER (), 2)          AS revenue_share_pct,
        RANK() OVER (ORDER BY revenue DESC)                       AS revenue_rank
    FROM borough_totals
    ORDER BY revenue_rank
"""

TOP_ROUTES_SQL = """
    WITH routes AS (
        SELECT
            COALESCE(pz.zone_name, 'Unknown') AS pickup_zone,
            COALESCE(dz.zone_name, 'Unknown') AS dropoff_zone,
            COUNT(*)                          AS trips,
            AVG(CAST(t.total_amount AS NUMERIC)) AS avg_total,
            AVG(CAST(t.duration_minutes AS NUMERIC)) AS avg_minutes
        FROM taxi_api_trip t
        LEFT JOIN taxi_api_zone pz ON pz.zone_id = t.pickup_zone_id
        LEFT JOIN taxi_api_zone dz ON dz.zone_id = t.dropoff_zone_id
        WHERE t.source_table = %s
          AND t.pickup_zone_id IS NOT NULL
          AND t.dropoff_zone_id IS NOT NULL
        GROUP BY pz.zone_name, dz.zone_name
    )
    SELECT pickup_zone, dropoff_zone, trips,
           ROUND(avg_total, 2) AS avg_total, ROUND(avg_minutes, 1) AS avg_minutes,
           ROW_NUMBER() OVER (ORDER BY trips DESC) AS route_rank
    FROM routes
    ORDER BY trips DESC
    LIMIT %s
"""

POPULAR_LOCATION_SQL = """
    SELECT ROUND(CAST({col}_latitude AS NUMERIC), 3) AS latitude,
           ROUND(CAST({col}_longitude AS NUMERIC), 3) AS longitude, COUNT(*) AS count
    FROM taxi_api_trip
    WHERE source_table = %s AND {col}_latitude IS NOT NULL
    GROUP BY 1, 2
    ORDER BY count DESC
    LIMIT 1
"""


def _query(sql: str, params: list) -> pd.DataFrame:
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        columns = [col[0] for col in cursor.description]
        return pd.DataFrame(cursor.fetchall(), columns=columns)


def _records(df: pd.DataFrame) -> list[dict]:
    return df.astype(object).where(df.notna(), None).to_dict("records")


def trips_dataframe(table: str) -> pd.DataFrame:
    df = _query(TRIPS_SQL, [table])
    if df.empty:
        return df
    for col in ("pickup_datetime", "dropoff_datetime"):
        df[col] = pd.to_datetime(df[col], utc=True).dt.tz_localize(None)
    numeric = ["trip_distance", "duration_minutes", "fare_amount", "tip_amount", "total_amount"]
    df[numeric] = df[numeric].astype(float)
    df["is_outlier"] = df["is_outlier"].astype(bool)
    df["tip_pct"] = (df["tip_amount"] / df["fare_amount"]).where(df["fare_amount"] > 0)
    return df


def borough_league_table(table: str) -> list[dict]:
    return _records(_query(BOROUGH_LEAGUE_SQL, [table]))


def top_routes(table: str, limit: int = 10) -> list[dict]:
    return _records(_query(TOP_ROUTES_SQL, [table, int(limit)]))


def most_popular_location(table: str, end: str) -> dict:
    if end not in ("pickup", "dropoff"):  # column names cannot be parameterised; whitelist instead
        raise ValueError(end)
    df = _query(POPULAR_LOCATION_SQL.format(col=end), [table])
    return _records(df)[0] if not df.empty else {"latitude": None, "longitude": None, "count": 0}
