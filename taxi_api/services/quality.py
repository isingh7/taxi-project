"""Transform and validate layer: data-quality rules applied with pandas and NumPy.

Each rule has one of three actions:
    reject - the row cannot be trusted for financial reporting, so it is removed
    fix    - the value is repaired in a deterministic, documented way
    flag   - the row is kept but marked (e.g. statistical outliers)

``run_quality_checks`` returns the clean frame, the rejected rows (with the
reason) and a JSON-serialisable report that is stored on ``IngestionRun``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from taxi_api import constants as c


@dataclass
class QualityResult:
    clean: pd.DataFrame
    rejected: pd.DataFrame
    report: dict = field(default_factory=dict)


def robust_zscore(values: pd.Series) -> pd.Series:
    """Modified z-score (Iglewicz & Hoaglin) using the median absolute deviation.

    The MAD is used instead of the standard deviation because the outliers we
    are looking for (e.g. a $4,000 fare keyed in error) inflate the std dev and
    hide themselves.
    """
    arr = values.to_numpy(dtype=float)
    median = np.nanmedian(arr)
    mad = np.nanmedian(np.abs(arr - median))
    if mad == 0 or np.isnan(mad):
        return pd.Series(np.zeros(len(arr)), index=values.index)
    return pd.Series(0.6745 * (arr - median) / mad, index=values.index)


def _normalise_types(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ("pickup_datetime", "dropoff_datetime"):
        df[col] = pd.to_datetime(df[col], errors="coerce", utc=True).dt.tz_localize(None)
    numeric = [
        "passenger_count", "trip_distance", "fare_amount", "tip_amount", "total_amount",
        "pickup_latitude", "pickup_longitude", "dropoff_latitude", "dropoff_longitude",
    ]
    df[numeric] = df[numeric].apply(pd.to_numeric, errors="coerce")
    return df


def _normalise_payment(series: pd.Series) -> tuple[pd.Series, int]:
    keys = series.astype("string").str.strip().str.upper()
    # "1.0" -> "1" when the source sent floats.
    keys = keys.str.replace(r"\.0$", "", regex=True)
    mapped = keys.map(c.PAYMENT_CODE_ALIASES)
    unmapped = int(mapped.isna().sum())
    return mapped.fillna(c.UNKNOWN_PAYMENT_CODE).astype(int), unmapped


def _in_nyc(lat: pd.Series, lon: pd.Series) -> pd.Series:
    b = c.NYC_BOUNDS
    return lat.between(b["min_lat"], b["max_lat"]) & lon.between(b["min_lon"], b["max_lon"])


def run_quality_checks(raw: pd.DataFrame, outlier_threshold: float = 3.5) -> QualityResult:
    rows_in = len(raw)
    rules: list[dict] = []

    def record(rule, description, mask_or_count, action):
        count = int(mask_or_count.sum()) if isinstance(mask_or_count, pd.Series) else int(mask_or_count)
        rules.append(
            {
                "rule": rule,
                "description": description,
                "action": action,
                "rows_affected": count,
                "pct_of_input": round(100 * count / rows_in, 3) if rows_in else 0.0,
            }
        )

    completeness = (
        (1 - raw.isna().mean()).mul(100).round(2).to_dict() if rows_in else {}
    )

    df = _normalise_types(raw)

    # --- fixes -----------------------------------------------------------------
    dup_mask = df.duplicated(keep="first")
    record("duplicate_rows", "Exact duplicate records removed", dup_mask, "fix")
    df = df.loc[~dup_mask].copy()

    df["payment_type"], unmapped = _normalise_payment(df["payment_type"])
    record("payment_code_unmapped", "Unrecognised payment codes mapped to 'Unknown'", unmapped, "fix")

    zero_pax = df["passenger_count"].fillna(-1).le(0)
    record("passenger_count_zero", "Passenger count <= 0 set to null (driver did not key it)", zero_pax, "fix")
    df.loc[zero_pax, "passenger_count"] = np.nan

    for end in ("pickup", "dropoff"):
        lat, lon = df[f"{end}_latitude"], df[f"{end}_longitude"]
        bad_geo = lat.notna() & ~_in_nyc(lat, lon)
        record(
            f"{end}_outside_nyc",
            f"{end.title()} coordinates outside NYC (e.g. 0,0 GPS dropout) set to null",
            bad_geo,
            "fix",
        )
        df.loc[bad_geo, [f"{end}_latitude", f"{end}_longitude"]] = np.nan

    # --- derived measures ------------------------------------------------------
    duration_s = (df["dropoff_datetime"] - df["pickup_datetime"]).dt.total_seconds()
    df["duration_minutes"] = (duration_s / 60).round(2)
    hours = duration_s / 3600
    df["speed_mph"] = np.where(hours > 0, df["trip_distance"] / hours, np.nan)
    df["fare_per_mile"] = np.where(df["trip_distance"] > 0, df["fare_amount"] / df["trip_distance"], np.nan)
    df["tip_pct"] = np.where(df["fare_amount"] > 0, df["tip_amount"] / df["fare_amount"], np.nan)

    # --- rejections ------------------------------------------------------------
    reject_rules = [
        ("missing_timestamp", "Pickup or dropoff timestamp missing / unparseable",
         df["pickup_datetime"].isna() | df["dropoff_datetime"].isna()),
        ("dropoff_before_pickup", "Dropoff time is not after pickup time", duration_s <= 0),
        ("duration_out_of_range",
         f"Trip shorter than {c.MIN_TRIP_SECONDS}s or longer than {c.MAX_TRIP_SECONDS // 3600}h",
         (duration_s > 0) & ((duration_s < c.MIN_TRIP_SECONDS) | (duration_s > c.MAX_TRIP_SECONDS))),
        ("distance_out_of_range", f"Distance <= 0 or > {c.MAX_TRIP_MILES} miles",
         df["trip_distance"].isna() | (df["trip_distance"] <= 0) | (df["trip_distance"] > c.MAX_TRIP_MILES)),
        ("fare_out_of_range", f"Fare below ${c.MIN_FARE:.2f} flag-drop or above ${c.MAX_FARE:,}",
         df["fare_amount"].isna() | (df["fare_amount"] < c.MIN_FARE) | (df["fare_amount"] > c.MAX_FARE)),
        ("total_less_than_fare", "Total amount is less than the fare (components do not reconcile)",
         df["total_amount"] < df["fare_amount"]),
        ("implausible_speed", f"Average speed above {c.MAX_PLAUSIBLE_MPH} mph",
         pd.Series(df["speed_mph"] > c.MAX_PLAUSIBLE_MPH, index=df.index)),
    ]
    reasons = pd.Series(pd.NA, index=df.index, dtype="string")
    for rule, description, mask in reject_rules:
        mask = mask.fillna(False).astype(bool)
        record(rule, description, mask, "reject")
        reasons = reasons.mask(mask & reasons.isna(), rule)  # first failing rule is the reason

    rejected = df.loc[reasons.notna()].assign(reject_reason=reasons[reasons.notna()])
    clean = df.loc[reasons.isna()].copy()

    # --- flags -----------------------------------------------------------------
    # Fare per mile is right-skewed (the flag-drop dominates short trips), so score on log scale.
    clean["is_outlier"] = robust_zscore(np.log(clean["fare_per_mile"])).abs() > outlier_threshold
    record(
        "fare_per_mile_outlier",
        f"log(fare per mile) has robust z-score > {outlier_threshold} (kept, flagged for review)",
        clean["is_outlier"],
        "flag",
    )

    report = {
        "rows_in": rows_in,
        "rows_clean": len(clean),
        "rows_rejected": len(rejected),
        "pass_rate_pct": round(100 * len(clean) / rows_in, 2) if rows_in else 0.0,
        "completeness_pct": completeness,
        "rules": rules,
    }
    return QualityResult(clean=clean.reset_index(drop=True), rejected=rejected, report=report)
