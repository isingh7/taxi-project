import numpy as np
import pandas as pd
import pytest

from taxi_api.services.quality import robust_zscore, run_quality_checks

from .conftest import frame, make_trip


def rule(report, name):
    return next(r for r in report["rules"] if r["rule"] == name)


def test_valid_trip_passes_and_gets_derived_measures():
    result = run_quality_checks(frame(make_trip()))
    assert len(result.clean) == 1 and result.rejected.empty
    row = result.clean.iloc[0]
    assert row["duration_minutes"] == 15
    assert row["speed_mph"] == pytest.approx(12.0)
    assert row["fare_per_mile"] == pytest.approx(14 / 3)
    assert row["tip_pct"] == pytest.approx(0.2)


@pytest.mark.parametrize(
    "overrides, expected_reason",
    [
        ({"dropoff_datetime": pd.Timestamp("2015-01-05 07:55:00")}, "dropoff_before_pickup"),
        ({"dropoff_datetime": pd.Timestamp("2015-01-05 08:00:30")}, "duration_out_of_range"),
        ({"dropoff_datetime": pd.Timestamp("2015-01-05 13:00:00")}, "duration_out_of_range"),
        ({"pickup_datetime": "not a date"}, "missing_timestamp"),
        ({"trip_distance": 0}, "distance_out_of_range"),
        ({"trip_distance": 250}, "distance_out_of_range"),
        ({"fare_amount": -14.0}, "fare_out_of_range"),
        ({"fare_amount": 1.0, "total_amount": 2.0}, "fare_out_of_range"),
        ({"total_amount": 10.0}, "total_less_than_fare"),
        ({"trip_distance": 60}, "implausible_speed"),  # 60 miles in 15 minutes
    ],
)
def test_reject_rules(overrides, expected_reason):
    result = run_quality_checks(frame(make_trip(), make_trip(**overrides)))
    assert len(result.clean) == 1
    assert result.rejected["reject_reason"].tolist() == [expected_reason]
    assert rule(result.report, expected_reason)["rows_affected"] == 1


def test_duplicates_are_removed_not_rejected():
    result = run_quality_checks(frame(make_trip(), make_trip()))
    assert len(result.clean) == 1
    assert result.rejected.empty
    assert rule(result.report, "duplicate_rows")["rows_affected"] == 1


@pytest.mark.parametrize(
    "raw, code", [("CSH", 2), ("crd", 1), (" Cash ", 2), ("1.0", 1), (2, 2), ("???", 5), (None, 5)]
)
def test_payment_codes_from_different_source_systems_are_harmonised(raw, code):
    result = run_quality_checks(frame(make_trip(payment_type=raw)))
    assert result.clean["payment_type"].iloc[0] == code


def test_bad_coordinates_are_nulled_but_trip_kept():
    result = run_quality_checks(frame(make_trip(pickup_latitude=0.0, pickup_longitude=0.0)))
    assert len(result.clean) == 1
    assert np.isnan(result.clean["pickup_latitude"].iloc[0])
    assert rule(result.report, "pickup_outside_nyc")["rows_affected"] == 1


def test_zero_passengers_becomes_null():
    result = run_quality_checks(frame(make_trip(passenger_count=0)))
    assert pd.isna(result.clean["passenger_count"].iloc[0])


def test_outlier_flagged_not_removed():
    rows = [make_trip(fare_amount=14.0 + i * 0.1, total_amount=18 + i * 0.1) for i in range(50)]
    rows.append(make_trip(fare_amount=600.0, total_amount=605.0))
    result = run_quality_checks(frame(*rows))
    assert len(result.clean) == 51
    assert result.clean["is_outlier"].sum() == 1
    assert result.clean.loc[result.clean["is_outlier"], "fare_amount"].iloc[0] == 600


def test_report_totals_reconcile():
    rows = [make_trip(), make_trip(fare_amount=-1), make_trip(trip_distance=0), make_trip()]
    report = run_quality_checks(frame(*rows)).report
    # in = clean + rejected + duplicates removed
    assert report["rows_in"] == report["rows_clean"] + report["rows_rejected"] + 1
    assert 0 <= report["pass_rate_pct"] <= 100


def test_empty_input_does_not_crash():
    empty = frame(make_trip()).iloc[0:0]
    result = run_quality_checks(empty)
    assert result.clean.empty and result.report["rows_in"] == 0


def test_robust_zscore_ignores_the_outlier_it_is_detecting():
    values = pd.Series([10.0] * 20 + [11.0] * 20 + [1_000.0])
    z = robust_zscore(values)
    assert z.iloc[-1] > 100
    assert z.iloc[:-1].abs().max() < 1


def test_robust_zscore_constant_series_is_zero():
    assert robust_zscore(pd.Series([5.0, 5.0, 5.0])).eq(0).all()
