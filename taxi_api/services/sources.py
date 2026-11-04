"""Extract layer: every source returns a DataFrame with ``CANONICAL_COLUMNS``.

Three sources are interchangeable behind ``get_source``:
    * ``BigQuerySource``  - sample of a public NYC TLC table (needs GCP credentials)
    * ``CsvSource``       - a local extract, e.g. a file a business user sent over
    * ``SyntheticSource`` - reproducible NumPy-generated trips for demos and tests,
                            with realistic defects injected so the DQ checks have
                            something to catch
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from taxi_api.constants import ALLOWED_TABLES, BIGQUERY_DATASET

CANONICAL_COLUMNS = [
    "pickup_datetime",
    "dropoff_datetime",
    "passenger_count",
    "trip_distance",
    "fare_amount",
    "tip_amount",
    "total_amount",
    "payment_type",
    "pickup_latitude",
    "pickup_longitude",
    "dropoff_latitude",
    "dropoff_longitude",
]


class UnknownTableError(ValueError):
    pass


def validate_table_name(table: str) -> str:
    if table not in ALLOWED_TABLES:
        raise UnknownTableError(f"Unknown table '{table}'. Allowed: {', '.join(ALLOWED_TABLES)}")
    return table


@dataclass
class BigQuerySource:
    table: str
    rows: int = 50_000
    client: object | None = None

    name = "bigquery"

    def extract(self) -> pd.DataFrame:
        from google.cloud import bigquery

        table = validate_table_name(self.table)
        client = self.client or bigquery.Client()
        sql = f"""
            SELECT {", ".join(CANONICAL_COLUMNS)}
            FROM `{BIGQUERY_DATASET}.{table}`
            WHERE RAND() < @sample_fraction
            LIMIT @row_limit
        """
        config = bigquery.QueryJobConfig(
            query_parameters=[
                # Over-sample a little, then LIMIT trims it to size.
                bigquery.ScalarQueryParameter("sample_fraction", "FLOAT64", 0.001),
                bigquery.ScalarQueryParameter("row_limit", "INT64", int(self.rows)),
            ]
        )
        return client.query(sql, job_config=config).result().to_dataframe()


@dataclass
class CsvSource:
    path: Path
    table: str = "csv_upload"

    name = "csv"

    def extract(self) -> pd.DataFrame:
        df = pd.read_csv(self.path)
        missing = set(CANONICAL_COLUMNS) - set(df.columns)
        if missing:
            raise ValueError(f"CSV is missing required columns: {sorted(missing)}")
        return df[CANONICAL_COLUMNS]


@dataclass
class SyntheticSource:
    table: str = "tlc_yellow_trips_2015"
    rows: int = 20_000
    seed: int = 42
    defect_rate: float = 0.03

    name = "synthetic"

    # Relative demand by hour of day: overnight low, morning and evening peaks.
    _HOURLY_WEIGHTS = np.array(
        [3, 2, 1.5, 1, 1, 1.5, 3, 5, 6, 5.5, 5, 5.2,
         5.5, 5.4, 5.6, 6, 6.4, 7, 7.5, 7.2, 6.5, 6, 5.5, 4.5]
    )
    # (lat, lon, weight) hotspots: Midtown, Lower Manhattan, JFK, LGA, Brooklyn, Upper Manhattan.
    _HOTSPOTS = np.array(
        [
            [40.7549, -73.9840, 0.40],
            [40.7128, -74.0060, 0.18],
            [40.6413, -73.7781, 0.08],
            [40.7769, -73.8740, 0.07],
            [40.6782, -73.9442, 0.12],
            [40.7870, -73.9754, 0.15],
        ]
    )

    def extract(self) -> pd.DataFrame:
        rng = np.random.default_rng(self.seed)
        n = self.rows
        year = int(self.table[-4:]) if self.table[-4:].isdigit() else 2015

        day_offsets = rng.integers(0, 90, n)
        hours = rng.choice(24, n, p=self._HOURLY_WEIGHTS / self._HOURLY_WEIGHTS.sum())
        seconds = rng.integers(0, 3600, n)
        pickup = (
            pd.Timestamp(f"{year}-01-01")
            + pd.to_timedelta(day_offsets, unit="D")
            + pd.to_timedelta(hours, unit="h")
            + pd.to_timedelta(seconds, unit="s")
        )

        distance = np.round(rng.lognormal(mean=0.6, sigma=0.75, size=n), 2)
        speed_mph = np.clip(rng.normal(12, 4, n), 3, 45)
        duration_s = (distance / speed_mph * 3600 + rng.integers(60, 240, n)).astype(int)
        dropoff = pickup + pd.to_timedelta(duration_s, unit="s")

        fare = np.round(2.5 + 2.5 * distance + 0.5 * duration_s / 60 * 0.4, 2)
        payment = rng.choice(["1", "2", "3", "4"], n, p=[0.62, 0.36, 0.01, 0.01])
        tip_pct = np.where(payment == "1", np.clip(rng.normal(0.18, 0.06, n), 0, 0.5), 0.0)
        tip = np.round(fare * tip_pct, 2)
        total = np.round(fare + tip + 0.5 + 0.3, 2)  # MTA tax + improvement surcharge

        spots = rng.choice(len(self._HOTSPOTS), n, p=self._HOTSPOTS[:, 2])
        p_lat = self._HOTSPOTS[spots, 0] + rng.normal(0, 0.01, n)
        p_lon = self._HOTSPOTS[spots, 1] + rng.normal(0, 0.01, n)
        bearing = rng.uniform(0, 2 * np.pi, n)
        d_lat = p_lat + np.cos(bearing) * distance / 69
        d_lon = p_lon + np.sin(bearing) * distance / 52

        df = pd.DataFrame(
            {
                "pickup_datetime": pickup,
                "dropoff_datetime": dropoff,
                "passenger_count": rng.choice([1, 2, 3, 4, 5, 6], n, p=[0.7, 0.14, 0.05, 0.03, 0.05, 0.03]),
                "trip_distance": distance,
                "fare_amount": fare,
                "tip_amount": tip,
                "total_amount": total,
                "payment_type": payment.astype(object),
                "pickup_latitude": np.round(p_lat, 6),
                "pickup_longitude": np.round(p_lon, 6),
                "dropoff_latitude": np.round(d_lat, 6),
                "dropoff_longitude": np.round(d_lon, 6),
            }
        )
        return self._inject_defects(df, rng)

    def _inject_defects(self, df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
        """Add the kinds of defects found in the real TLC data."""
        n_bad = int(len(df) * self.defect_rate)
        if n_bad == 0:
            return df
        idx = rng.choice(df.index, size=n_bad * 6, replace=False).reshape(6, n_bad)
        df.loc[idx[0], ["pickup_latitude", "pickup_longitude"]] = 0.0           # GPS dropout
        df.loc[idx[1], "dropoff_datetime"] = df.loc[idx[1], "pickup_datetime"] - pd.Timedelta(minutes=5)
        df.loc[idx[2], "fare_amount"] = -df.loc[idx[2], "fare_amount"]           # refunds / reversals
        df.loc[idx[3], "fare_amount"] = df.loc[idx[3], "fare_amount"] * 40       # keying errors
        df.loc[idx[3], "total_amount"] = df.loc[idx[3], "fare_amount"] + 1
        df.loc[idx[4], "payment_type"] = rng.choice(["CSH", "CRD", "Cash", None], n_bad)  # legacy codes
        df.loc[idx[5], "passenger_count"] = 0
        duplicates = df.sample(n=max(1, n_bad // 3), random_state=self.seed)
        return pd.concat([df, duplicates], ignore_index=True)


def get_source(kind: str, table: str, rows: int = 20_000, path: str | None = None, seed: int = 42):
    if kind == "synthetic":
        validate_table_name(table)
        # Offset the seed per table so each dataset looks different but stays reproducible.
        return SyntheticSource(table=table, rows=rows, seed=seed + ALLOWED_TABLES.index(table))
    if kind == "bigquery":
        return BigQuerySource(table=validate_table_name(table), rows=rows)
    if kind == "csv":
        if not path:
            raise ValueError("--path is required for the csv source")
        return CsvSource(path=Path(path), table=table)
    raise ValueError(f"Unknown source '{kind}'")
