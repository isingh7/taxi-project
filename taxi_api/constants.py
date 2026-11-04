"""Shared constants for the taxi analytics service.

Table names cannot be passed to BigQuery as query parameters, so every table
name that reaches SQL must first be checked against ``ALLOWED_TABLES``. The old
view put the URL segment straight into an f-string, which allowed SQL
injection.
"""

from pathlib import Path

BIGQUERY_DATASET = "bigquery-public-data.new_york"

ALLOWED_TABLES = (
    "tlc_green_trips_2013",
    "tlc_green_trips_2014",
    "tlc_green_trips_2015",
    "tlc_green_trips_2016",
    "tlc_yellow_trips_2009",
    "tlc_yellow_trips_2010",
    "tlc_yellow_trips_2011",
    "tlc_yellow_trips_2012",
    "tlc_yellow_trips_2013",
    "tlc_yellow_trips_2014",
    "tlc_yellow_trips_2015",
    "tlc_yellow_trips_2016",
)

REFERENCE_DATA_DIR = Path(__file__).resolve().parent / "reference_data"

# Source systems encode payment type inconsistently: 2009-2014 yellow trips use
# text codes, later years use the TLC integer codes. Both are mapped to the
# integer code.
PAYMENT_CODE_ALIASES = {
    "1": 1, "CRD": 1, "CRE": 1, "CREDIT": 1, "CREDIT CARD": 1,
    "2": 2, "CSH": 2, "CAS": 2, "CASH": 2,
    "3": 3, "NOC": 3, "NO CHARGE": 3,
    "4": 4, "DIS": 4, "DISPUTE": 4,
    "5": 5, "UNK": 5, "UNKNOWN": 5,
    "6": 6, "VOIDED": 6,
}
UNKNOWN_PAYMENT_CODE = 5

# Business rules agreed with operations. See docs/REQUIREMENTS.md, section R3.
MIN_TRIP_SECONDS = 60
MAX_TRIP_SECONDS = 4 * 60 * 60
MAX_TRIP_MILES = 100
MAX_PLAUSIBLE_MPH = 80
MIN_FARE = 2.50  # NYC flag-drop fare
MAX_FARE = 1_000
NYC_BOUNDS = {"min_lat": 40.45, "max_lat": 40.95, "min_lon": -74.30, "max_lon": -73.65}
