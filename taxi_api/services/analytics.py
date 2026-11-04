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


WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def weekday_hour(df: pd.DataFrame) -> dict:
    """Trips by weekday x pickup hour (a 7 x 24 matrix), for the demand heatmap."""
    if df.empty:
        return {"weekdays": WEEKDAYS, "hours": list(range(24)), "trips": [[0] * 24 for _ in WEEKDAYS]}
    ts = df["pickup_datetime"]
    matrix = (
        pd.crosstab(ts.dt.dayofweek, ts.dt.hour)
        .reindex(index=range(7), columns=range(24), fill_value=0)
    )
    return {
        "weekdays": WEEKDAYS,
        "hours": list(range(24)),
        "trips": matrix.to_numpy(dtype=int).tolist(),
    }


def _money(v: float) -> str:
    return f"${v:,.0f}"


def _hour_range(h: int) -> str:
    return f"{h:02d}:00–{(h + 1) % 24:02d}:00"


def key_findings(payload: dict) -> list[dict]:
    """Plain-English findings for business users, generated from the analytics payload.

    Each finding has a short ``title``, a ``detail`` sentence and a ``tone``:
    ``warning`` for something to act on before using the numbers, ``insight`` otherwise.
    """
    findings: list[dict] = []
    kpis = payload.get("kpis", {})
    if not kpis.get("trips"):
        return findings

    gross, clean = kpis.get("gross_revenue") or 0, kpis.get("gross_revenue_ex_outliers") or 0
    if gross:
        flagged_share = 100 * (gross - clean) / gross
        findings.append({
            "id": "flagged_revenue",
            "tone": "warning" if flagged_share >= 10 else "insight",
            "title": f"Flagged trips are {kpis.get('outlier_rate_pct', 0):.1f}% of trips "
                     f"but {flagged_share:.0f}% of revenue",
            "detail": "Their fares are far above normal for the distance travelled. Review them before "
                      f"quoting totals: excluding them, revenue is {_money(clean)} instead of {_money(gross)}.",
        })

    daily = payload.get("daily", [])
    anomalies = [d for d in daily if d.get("is_anomaly")]
    if anomalies:
        worst = max(anomalies, key=lambda d: abs(d["revenue"] - (d["rolling_mean"] or d["revenue"])))
        day = pd.Timestamp(worst["date"])
        vs_avg = 100 * (worst["revenue"] / worst["rolling_mean"] - 1) if worst["rolling_mean"] else 0
        findings.append({
            "id": "anomalies",
            "tone": "warning",
            "title": f"{len(anomalies)} unusual revenue day{'s' if len(anomalies) != 1 else ''}",
            "detail": f"The largest is {day:%b} {day.day}: {_money(worst['revenue'])}, "
                      f"{abs(vs_avg):.0f}% {'above' if vs_avg >= 0 else 'below'} the 7-day average. "
                      "Check for data issues or one-off events before using these days in forecasts.",
        })

    boroughs = [b for b in payload.get("boroughs", []) if b.get("borough") != "Unknown"]
    if boroughs:
        top = boroughs[0]
        runner_up = f" {boroughs[1]['borough']} is next at {float(boroughs[1]['revenue_share_pct']):.0f}%." \
            if len(boroughs) > 1 else ""
        findings.append({
            "id": "borough_concentration",
            "tone": "insight",
            "title": f"{top['borough']} generates {float(top['revenue_share_pct']):.0f}% of revenue",
            "detail": f"{top['trips']:,} trips at an average fare of ${float(top['avg_fare']):.2f}.{runner_up}",
        })

    hourly = payload.get("hourly", [])
    if hourly and max(h["trips"] for h in hourly):
        peak = max(hourly, key=lambda h: h["trips"])
        trough = min(hourly, key=lambda h: h["trips"])
        ratio = peak["trips"] / max(trough["trips"], 1)
        findings.append({
            "id": "peak_demand",
            "tone": "insight",
            "title": f"Demand peaks at {_hour_range(peak['hour'])}",
            "detail": f"That hour carries {peak['share_pct']:.1f}% of daily trips, {ratio:.0f}x the quietest hour "
                      f"({_hour_range(trough['hour'])}). Driver supply should follow this curve.",
        })

    grid = payload.get("weekday_hour", {}).get("trips")
    if grid:
        totals = [sum(row) for row in grid]
        busiest, quietest = int(np.argmax(totals)), int(np.argmin(totals))
        if totals[quietest]:
            lift = 100 * (totals[busiest] / totals[quietest] - 1)
            findings.append({
                "id": "weekly_pattern",
                "tone": "insight",
                "title": f"{WEEKDAYS[busiest]} is the busiest day",
                "detail": f"It has {lift:.0f}% more trips than {WEEKDAYS[quietest]}, the quietest day.",
            })

    if kpis.get("avg_card_tip_pct") is not None:
        findings.append({
            "id": "tipping",
            "tone": "insight",
            "title": f"Card riders tip {kpis['avg_card_tip_pct']:.1f}% on average",
            "detail": f"{kpis.get('card_share_pct', 0):.0f}% of trips are paid by card. Cash tips are not "
                      "recorded, so tip figures across all trips would understate tipping.",
        })
    return findings


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
