import pandas as pd
import pytest
from django.core.cache import cache

from taxi_api.services.etl import run_pipeline
from taxi_api.services.sources import SyntheticSource

TABLE = "tlc_yellow_trips_2015"


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def loaded_table(db):
    """A small synthetic load in the test database."""
    run_pipeline(SyntheticSource(table=TABLE, rows=1_500, seed=7))
    return TABLE


def make_trip(**overrides):
    """One valid raw trip in canonical columns; override fields to create defects."""
    row = {
        "pickup_datetime": pd.Timestamp("2015-01-05 08:00:00"),
        "dropoff_datetime": pd.Timestamp("2015-01-05 08:15:00"),
        "passenger_count": 1,
        "trip_distance": 3.0,
        "fare_amount": 14.0,
        "tip_amount": 2.8,
        "total_amount": 17.6,
        "payment_type": "1",
        "pickup_latitude": 40.7549,
        "pickup_longitude": -73.9840,
        "dropoff_latitude": 40.7128,
        "dropoff_longitude": -74.0060,
    }
    row.update(overrides)
    return row


def frame(*rows):
    return pd.DataFrame(list(rows))
