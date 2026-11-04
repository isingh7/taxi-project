import numpy as np
import pandas as pd
import pytest

from taxi_api.services import analytics


@pytest.fixture
def trips():
    return pd.DataFrame(
        {
            "pickup_datetime": pd.to_datetime(
                ["2015-01-01 08:10", "2015-01-01 08:40", "2015-01-01 18:00", "2015-01-02 08:05"]
            ),
            "fare_amount": [10.0, 20.0, 30.0, 40.0],
            "tip_amount": [2.0, 0.0, 6.0, 0.0],
            "total_amount": [12.0, 20.0, 36.0, 40.0],
            "duration_minutes": [10.0, 20.0, 30.0, 40.0],
            "trip_distance": [1.0, 2.0, 3.0, 4.0],
            "payment_label": ["Credit card", "Cash", "Credit card", "Cash"],
            "is_outlier": [False, False, False, True],
        }
    ).assign(tip_pct=lambda d: d.tip_amount / d.fare_amount)


def test_summary_kpis(trips):
    k = analytics.summary_kpis(trips)
    assert k["trips"] == 4
    assert k["gross_revenue"] == 108.0
    assert k["gross_revenue_ex_outliers"] == 68.0
    assert k["avg_fare"] == 25.0
    assert k["median_fare"] == 25.0
    assert k["card_share_pct"] == 50.0
    assert k["avg_card_tip_pct"] == 20.0  # both card trips tipped 20%
    assert k["outlier_rate_pct"] == 25.0


def test_summary_kpis_empty():
    assert analytics.summary_kpis(pd.DataFrame()) == {"trips": 0}


def test_hourly_demand_has_all_24_hours(trips):
    rows = analytics.hourly_demand(trips)
    assert [r["hour"] for r in rows] == list(range(24))
    by_hour = {r["hour"]: r for r in rows}
    assert by_hour[8]["trips"] == 3 and isinstance(by_hour[8]["trips"], int)
    assert by_hour[3]["trips"] == 0
    assert sum(r["share_pct"] for r in rows) == pytest.approx(100)
    assert analytics.peak_hour(trips) == {"hour": 8, "count": 3}


def test_payment_mix_ranked_by_trips(trips):
    mix = analytics.payment_mix(trips)
    assert {m["payment_type"] for m in mix} == {"Credit card", "Cash"}
    card = next(m for m in mix if m["payment_type"] == "Credit card")
    assert card["revenue"] == 48.0 and card["avg_tip_pct"] == 20.0


def _series(revenues):
    days = pd.date_range("2015-01-01", periods=len(revenues), freq="D")
    return pd.DataFrame({"pickup_datetime": days + pd.Timedelta(hours=9), "total_amount": revenues})


def test_daily_revenue_returns_and_drawdown():
    out = analytics.daily_revenue(_series([100.0, 110.0, 99.0]), window=1)
    assert [d["revenue"] for d in out] == [100, 110, 99]
    assert out[0]["pct_change"] is None
    assert out[1]["pct_change"] == 10.0
    assert out[2]["pct_change"] == -10.0
    assert out[2]["drawdown_pct"] == -10.0  # 99 vs running peak of 110
    assert out[1]["drawdown_pct"] == 0.0


def test_daily_revenue_flags_anomalous_day():
    rng = np.random.default_rng(0)
    revenues = list(1_000 + rng.normal(0, 10, 20)) + [5_000.0]
    out = analytics.daily_revenue(_series(revenues), window=7)
    assert out[-1]["is_anomaly"] is True
    assert not any(d["is_anomaly"] for d in out[:-1])


def test_daily_revenue_fills_missing_days_with_zero():
    df = _series([100.0, 100.0])
    df.loc[1, "pickup_datetime"] += pd.Timedelta(days=2)
    out = analytics.daily_revenue(df)
    assert [d["trips"] for d in out] == [1, 0, 0, 1]


def test_fare_distribution_clips_tail(trips):
    dist = analytics.fare_distribution(trips, bins=3, clip_pct=50)
    assert sum(dist["counts"]) == 2  # the flagged $40 fare is excluded; 30 is above p50
    assert dist["clipped_above"] == 20.0
