import numpy as np
import pandas as pd
import pytest

from taxi_api.services.enrichment import assign_zone, enrich, load_zones
from taxi_api.services.sources import (
    CANONICAL_COLUMNS,
    CsvSource,
    SyntheticSource,
    UnknownTableError,
    get_source,
    validate_table_name,
)


def test_synthetic_source_is_reproducible_and_canonical():
    a = SyntheticSource(rows=500, seed=1).extract()
    b = SyntheticSource(rows=500, seed=1).extract()
    pd.testing.assert_frame_equal(a, b)
    assert list(a.columns) == CANONICAL_COLUMNS


def test_synthetic_source_injects_defects():
    df = SyntheticSource(rows=1_000, seed=1, defect_rate=0.05).extract()
    assert (df["fare_amount"] < 0).any()
    assert (df["pickup_latitude"] == 0).any()
    assert df.duplicated().any()


@pytest.mark.parametrize(
    "bad", ["users", "tlc_yellow_trips_2015`; DROP TABLE x; --", "../etc/passwd", ""]
)
def test_table_whitelist_blocks_injection(bad):
    with pytest.raises(UnknownTableError):
        validate_table_name(bad)
    with pytest.raises(UnknownTableError):
        get_source("synthetic", bad)


def test_csv_source_validates_columns(tmp_path):
    good = tmp_path / "good.csv"
    SyntheticSource(rows=10).extract().to_csv(good, index=False)
    assert len(CsvSource(good).extract()) >= 10

    bad = tmp_path / "bad.csv"
    pd.DataFrame({"fare_amount": [1]}).to_csv(bad, index=False)
    with pytest.raises(ValueError, match="missing required columns"):
        CsvSource(bad).extract()


def test_assign_zone_uses_priority_for_overlaps():
    zones = load_zones()
    points = pd.DataFrame(
        {
            "lat": [40.6413, 40.7549, 40.6782, 0.0, np.nan],
            "lon": [-73.7781, -73.9840, -73.9442, 0.0, np.nan],
        }
    )
    ids = assign_zone(points["lat"], points["lon"], zones)
    names = zones.set_index("zone_id")["zone_name"]
    # JFK sits inside the Queens box too; the higher-priority airport zone wins.
    assert names[ids[0]] == "JFK Airport"
    assert names[ids[1]] == "Midtown Manhattan"
    assert names[ids[2]] == "Brooklyn"
    assert ids[3] is pd.NA and ids[4] is pd.NA


def test_enrich_adds_borough_and_time_parts():
    df = pd.DataFrame(
        {
            "pickup_datetime": pd.to_datetime(["2015-01-01 17:30"]),
            "pickup_latitude": [40.7549], "pickup_longitude": [-73.9840],
            "dropoff_latitude": [np.nan], "dropoff_longitude": [np.nan],
        }
    )
    out = enrich(df)
    assert out.loc[0, "pickup_borough"] == "Manhattan"
    assert out.loc[0, "pickup_hour"] == 17
    assert out["dropoff_zone_id"].isna().all()
