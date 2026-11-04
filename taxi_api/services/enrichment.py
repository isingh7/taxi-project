"""Enrich layer: join trips to the reference data (zones, payment types)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from taxi_api.constants import REFERENCE_DATA_DIR


def load_zones() -> pd.DataFrame:
    return pd.read_csv(REFERENCE_DATA_DIR / "zones.csv").sort_values("priority")


def load_payment_types() -> pd.DataFrame:
    return pd.read_csv(REFERENCE_DATA_DIR / "payment_types.csv")


def assign_zone(lat: pd.Series, lon: pd.Series, zones: pd.DataFrame) -> pd.Series:
    """Return the zone_id for each point (nullable Int64; NA if no zone matches).

    Vectorised: builds an (n_points x n_zones) boolean matrix in NumPy rather than
    looping over rows, so 1M points take about a second instead of minutes.
    Overlapping boxes are resolved by ``priority`` (zones are pre-sorted by it, so
    the first True column wins).
    """
    zones = zones.sort_values("priority")
    la = lat.to_numpy(dtype=float)[:, None]
    lo = lon.to_numpy(dtype=float)[:, None]
    inside = (
        (la >= zones["min_lat"].to_numpy())
        & (la <= zones["max_lat"].to_numpy())
        & (lo >= zones["min_lon"].to_numpy())
        & (lo <= zones["max_lon"].to_numpy())
    )
    has_match = inside.any(axis=1)
    first_match = inside.argmax(axis=1)
    ids = np.where(has_match, zones["zone_id"].to_numpy()[first_match], -1)
    return pd.Series(ids, index=lat.index).replace(-1, pd.NA).astype("Int64")


def enrich(df: pd.DataFrame, zones: pd.DataFrame | None = None) -> pd.DataFrame:
    zones = load_zones() if zones is None else zones
    out = df.copy()
    out["pickup_zone_id"] = assign_zone(out["pickup_latitude"], out["pickup_longitude"], zones)
    out["dropoff_zone_id"] = assign_zone(out["dropoff_latitude"], out["dropoff_longitude"], zones)
    borough = zones.set_index("zone_id")["borough"]
    out["pickup_borough"] = out["pickup_zone_id"].map(borough).fillna("Unknown")
    out["pickup_hour"] = out["pickup_datetime"].dt.hour
    out["pickup_date"] = out["pickup_datetime"].dt.date
    return out
