"""Analytics layer: pure pandas/NumPy functions over a trips DataFrame.

The functions do no I/O, so they are fast to unit-test and the Django API and
the Dash dashboard can share them.

Revenue is treated like a P&L series. Daily revenue gets day-over-day
returns, rolling volatility, drawdown from peak and anomaly flags, the same
measures a trading desk uses to monitor a book.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _safe(value, ndigits=2):
    """Convert NumPy scalars / NaN to JSON-friendly Python values."""
    if value is None or (isinstance(value, float) and np.isnan(value)) or value is pd.NA:
        return None
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating | float):
        return round(float(value), ndigits)
    return value


def summary_kpis(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"trips": 0}
    fare = df["fare_amount"]
    duration = df["duration_minutes"]
    q_fare = np.percentile(fare, [50, 90, 95, 99])
    q_dur = np.percentile(duration, [50, 90, 95])
    card = df["payment_label"].eq("Credit card")
    return {
        "trips": int(len(df)),
        "gross_revenue": _safe(df["total_amount"].sum()),
        # Finance asked for the figure both ways: flagged rows are kept but can be excluded.
        "gross_revenue_ex_outliers": _safe(df.loc[~df["is_outlier"], "total_amount"].sum()),
        "avg_fare": _safe(fare.mean()),
        "median_fare": _safe(q_fare[0]),
        "p90_fare": _safe(q_fare[1]),
        "p95_fare": _safe(q_fare[2]),
        "p99_fare": _safe(q_fare[3]),
        "avg_duration_min": _safe(duration.mean()),
        "median_duration_min": _safe(q_dur[0]),
        "p90_duration_min": _safe(q_dur[1]),
        "p95_duration_min": _safe(q_dur[2]),
        "avg_distance_miles": _safe(df["trip_distance"].mean()),
        # Tips are only reliably recorded on card payments; cash tips are not captured.
        "avg_card_tip_pct": _safe(100 * df.loc[card, "tip_pct"].mean()),
        "card_share_pct": _safe(100 * card.mean()),
        "outlier_rate_pct": _safe(100 * df["is_outlier"].mean(), 3),
    }


def hourly_demand(df: pd.DataFrame) -> list[dict]:
    hours = df["pickup_datetime"].dt.hour
    grouped = (
        df.assign(hour=hours)
        .groupby("hour")
        .agg(trips=("fare_amount", "size"), avg_fare=("fare_amount", "mean"),
             revenue=("total_amount", "sum"))
        .reindex(range(24), fill_value=0)
    )
    grouped["share_pct"] = 100 * grouped["trips"] / max(grouped["trips"].sum(), 1)
    # itertuples keeps per-column dtypes (iterrows would upcast trip counts to float).
    return [
        {"hour": int(r.Index), "trips": int(r.trips), "avg_fare": _safe(r.avg_fare),
         "revenue": _safe(r.revenue), "share_pct": _safe(r.share_pct)}
        for r in grouped.itertuples()
    ]


def peak_hour(df: pd.DataFrame) -> dict:
    rows = hourly_demand(df)
    best = max(rows, key=lambda r: r["trips"])
    return {"hour": best["hour"], "count": best["trips"]}


def daily_revenue(df: pd.DataFrame, window: int = 7, anomaly_z: float = 3.0) -> list[dict]:
    """Daily revenue time series with trading-style risk metrics.

    * ``rolling_mean``  - trailing ``window``-day average (smooths weekday seasonality)
    * ``pct_change``    - day-over-day return
    * ``volatility``    - trailing std dev of daily returns (in %)
    * ``drawdown_pct``  - % below the running peak of the rolling mean
    * ``is_anomaly``    - |z| of revenue vs the previous ``window`` days exceeds ``anomaly_z``
    """
    if df.empty:
        return []
    daily = (
        df.set_index("pickup_datetime")["total_amount"]
        .resample("D")
        .agg(["sum", "size"])
        .rename(columns={"sum": "revenue", "size": "trips"})
    )
    daily["rolling_mean"] = daily["revenue"].rolling(window, min_periods=1).mean()
    returns = daily["revenue"].pct_change().replace([np.inf, -np.inf], np.nan)
    daily["pct_change"] = 100 * returns
    daily["volatility"] = 100 * returns.rolling(window, min_periods=min(2, window)).std()
    # Drawdown is measured on the smoothed series (like an equity curve); on raw daily
    # values every quiet weekday after a busy day would read as a large drawdown.
    # Only full windows count, so a single busy first day cannot set an unreachable peak.
    smoothed = daily["revenue"].rolling(window, min_periods=window).mean()
    peak = smoothed.cummax()
    daily["drawdown_pct"] = 100 * (smoothed - peak) / peak.replace(0, np.nan)
    # Baseline uses the *previous* days only. If today's value were in its own
    # mean/std, a spike would inflate the baseline and hide itself. A full window
    # is required because std estimates from 2-3 days are too noisy to alert on.
    prior = daily["revenue"].shift(1).rolling(window, min_periods=window)
    z = (daily["revenue"] - prior.mean()) / prior.std().replace(0, np.nan)
    daily["is_anomaly"] = z.abs().gt(anomaly_z).fillna(False)
    return [
        {
            "date": idx.date().isoformat(),
            "revenue": _safe(r["revenue"]),
            "trips": int(r["trips"]),
            "rolling_mean": _safe(r["rolling_mean"]),
            "pct_change": _safe(r["pct_change"]),
            "volatility": _safe(r["volatility"]),
            "drawdown_pct": _safe(r["drawdown_pct"]),
            "is_anomaly": bool(r["is_anomaly"]),
        }
        for idx, r in daily.iterrows()
    ]


def payment_mix(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []
    g = df.groupby("payment_label").agg(
        trips=("fare_amount", "size"),
        revenue=("total_amount", "sum"),
        avg_tip_pct=("tip_pct", "mean"),
    )
    g["share_pct"] = 100 * g["trips"] / g["trips"].sum()
    g["avg_tip_pct"] = 100 * g["avg_tip_pct"]
    g = g.sort_values("trips", ascending=False)
    return [
        {"payment_type": label, **{k: _safe(v) for k, v in row.items()}}
        for label, row in g.iterrows()
    ]


def fare_distribution(df: pd.DataFrame, bins: int = 30, clip_pct: float = 99) -> dict:
    """Histogram of fares for unflagged trips, clipped at a percentile so the tail does not flatten it."""
    if df.empty:
        return {"edges": [], "counts": []}
    fares = df.loc[~df["is_outlier"], "fare_amount"].to_numpy(dtype=float)
    upper = np.percentile(fares, clip_pct)
    counts, edges = np.histogram(fares[fares <= upper], bins=bins)
    return {"edges": [round(float(e), 2) for e in edges], "counts": counts.tolist(),
            "clipped_above": round(float(upper), 2)}
