import { useEffect, useState } from "react";
import {
  describeError,
  getAnalytics,
  getDataQuality,
  getHeadlineStats,
  getIngestionRuns,
} from "../api";

const settle = (promise) => promise.then((value) => ({ value })).catch((error) => ({ error }));

/**
 * Loads everything the views need for one table in parallel.
 * Each part fails on its own: if BigQuery headline stats fail, the analytics
 * from the local store still render, and the reverse.
 */
export default function useDashboardData(table) {
  const [state, setState] = useState({ loading: true });

  useEffect(() => {
    if (!table) return undefined;
    let cancelled = false; // ignore late responses after the table changes
    setState((prev) => ({ ...prev, loading: true }));

    Promise.all([
      settle(getHeadlineStats(table)),
      settle(getAnalytics(table)),
      settle(getDataQuality(table)),
      settle(getIngestionRuns()),
    ]).then(([headline, analytics, quality, runs]) => {
      if (cancelled) return;
      const errors = [headline, analytics, quality].filter((r) => r.error).map((r) => describeError(r.error));
      setState({
        loading: false,
        headline: headline.value,
        analytics: analytics.value,
        quality: quality.value,
        runs: (runs.value || []).filter((r) => r.source_table === table),
        error: errors.length === 3 ? errors[0] : null, // nothing at all to show
        warnings: errors.length && errors.length < 3 ? [...new Set(errors)] : [],
      });
    });

    return () => {
      cancelled = true;
    };
  }, [table]);

  return state;
}
