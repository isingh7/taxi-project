import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ThemeProvider } from "@mui/material";
import App from "./App";
import theme from "./theme";
import { getAnalytics, getDataQuality, getHeadlineStats, getIngestionRuns, getTables } from "./api";

jest.mock("./api", () => ({
  getHeadlineStats: jest.fn(),
  getAnalytics: jest.fn(),
  getDataQuality: jest.fn(),
  getIngestionRuns: jest.fn(),
  getTables: jest.fn(),
  describeError: (e) => e.message,
  dailyCsvUrl: (t) => `/api/analytics/${t}/daily.csv`,
  DASHBOARD_URL: "http://localhost:8050",
}));
// jsdom has no canvas; chart rendering is not what these tests cover.
jest.mock("react-chartjs-2", () => {
  const Stub = () => <div data-testid="chart" />;
  return { Line: Stub, Bar: Stub };
});

const TABLE = "tlc_yellow_trips_2015";
const headline = {
  avg_journey_time: 16.36, min_journey_time: 1.58, max_journey_time: 217.43,
  avg_total_cost: 25.88, min_total_cost: 4.03, max_total_cost: 977.8,
  avg_tip_amount: 2.11, data_source: "local",
  most_popular_time_of_day: { hour: 18, count: 933 },
  most_popular_pickup_location: { latitude: 40.75, longitude: -73.98, count: 16 },
  most_popular_dropoff_location: { latitude: 40.73, longitude: -73.97, count: 7 },
};
const analytics = {
  kpis: {
    trips: 14073, gross_revenue: 364154.82, gross_revenue_ex_outliers: 189814.69, median_fare: 9.84,
    p95_fare: 34.23, avg_card_tip_pct: 17.2, card_share_pct: 60.9, median_duration_min: 12.2,
    p90_duration_min: 30.9, avg_distance_miles: 2.41,
  },
  daily: [
    { date: "2015-01-01", revenue: 4000, rolling_mean: 4000, pct_change: null, volatility: null, drawdown_pct: null, is_anomaly: false },
    { date: "2015-01-02", revenue: 9000, rolling_mean: 6500, pct_change: 125, volatility: 10, drawdown_pct: 0, is_anomaly: true },
  ],
  hourly: [{ hour: 18, trips: 933, share_pct: 6.6, avg_fare: 12 }],
  payment_mix: [{ payment_type: "Credit card", trips: 8614 }],
  fare_distribution: { edges: [0, 10, 20], counts: [5, 3], clipped_above: 41 },
  boroughs: [{ borough: "Manhattan", trips: 9264, revenue: 243531.14, avg_fare: 24.2, revenue_share_pct: 66.88, revenue_rank: 1 }],
  top_routes: [{ pickup_zone: "Brooklyn", dropoff_zone: "Midtown Manhattan", trips: 1702, avg_total: 25.24, avg_minutes: 13.9 }],
};
const quality = {
  id: 7, source: "synthetic", finished_at: "2026-11-04T14:41:54Z", rows_loaded: 14073,
  quality_report: {
    pass_rate_pct: 92.89, rows_in: 15150, rows_clean: 14073, rows_rejected: 927,
    completeness_pct: { fare_amount: 100, payment_type: 99.2 },
    rules: [
      { rule: "fare_out_of_range", action: "reject", rows_affected: 470, pct_of_input: 3.1, description: "Fare below $2.50" },
      { rule: "pickup_outside_nyc", action: "fix", rows_affected: 450, pct_of_input: 2.97, description: "Bad GPS" },
    ],
  },
};

const renderApp = () => render(<ThemeProvider theme={theme}><App /></ThemeProvider>);

beforeEach(() => {
  window.location.hash = "";
  getTables.mockResolvedValue([
    { table: "tlc_green_trips_2013", loaded: false, trips: 0 },
    { table: TABLE, loaded: true, trips: 14073 },
  ]);
  getHeadlineStats.mockResolvedValue(headline);
  getAnalytics.mockResolvedValue(analytics);
  getDataQuality.mockResolvedValue(quality);
  getIngestionRuns.mockResolvedValue([{ id: 7, source: "synthetic", source_table: TABLE, status: "success", finished_at: quality.finished_at, rows_loaded: 14073, rows_rejected: 927 }]);
});

test("overview shows KPIs, highlights and the data source", async () => {
  renderApp();
  expect(await screen.findByText("$364.2K")).toBeInTheDocument();
  expect(screen.getByText("14,073")).toBeInTheDocument();
  expect(screen.getByText("$9.84")).toBeInTheDocument();
  expect(screen.getByText("92.9%")).toBeInTheDocument();
  expect(screen.getByText("18:00–19:00")).toBeInTheDocument();
  expect(screen.getByText("Manhattan")).toBeInTheDocument();
  expect(screen.getByText("Local store")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Export CSV/ })).toHaveAttribute("href", `/api/analytics/${TABLE}/daily.csv`);
});

test("navigates to data quality and shows rules with action labels", async () => {
  renderApp();
  await screen.findByText("$364.2K");
  await userEvent.click(screen.getByRole("button", { name: /open navigation/i }));
  await userEvent.click(await screen.findByRole("button", { name: "Data quality" }));
  const rules = await screen.findByRole("table", { name: "Data quality rules" });
  expect(within(rules).getByText("Fare out of range")).toBeInTheDocument();
  expect(within(rules).getByText("Reject")).toBeInTheDocument();
  expect(within(rules).getByText("Fix")).toBeInTheDocument();
  expect(screen.getByRole("table", { name: "Ingestion runs" })).toHaveTextContent("✓ Success");
});

test("revenue view lists anomalous days", async () => {
  renderApp();
  await screen.findByText("$364.2K");
  await userEvent.click(screen.getByRole("button", { name: /open navigation/i }));
  await userEvent.click(await screen.findByRole("button", { name: "Revenue" }));
  const table = await screen.findByRole("table", { name: "Anomalous revenue days" });
  expect(within(table).getByText("Jan 2")).toBeInTheDocument();
  expect(within(table).getByText("▲ Spike")).toBeInTheDocument();
});

test("shows one clear error when the API is unreachable", async () => {
  const down = new Error("Cannot reach the API at http://localhost:8000/api.");
  getHeadlineStats.mockRejectedValue(down);
  getAnalytics.mockRejectedValue(down);
  getDataQuality.mockRejectedValue(down);
  renderApp();
  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("Could not load data");
  expect(alert).toHaveTextContent("Cannot reach the API");
});

test("a partial failure shows a warning but still renders analytics", async () => {
  getHeadlineStats.mockRejectedValue(new Error("BigQuery is unavailable."));
  renderApp();
  expect(await screen.findByText("$364.2K")).toBeInTheDocument();
  expect(await screen.findByText("BigQuery is unavailable.")).toBeInTheDocument();
});

describe("Dash dashboard view", () => {
  afterEach(() => {
    delete global.fetch;
  });

  const openDashView = async () => {
    renderApp();
    await screen.findByText("$364.2K");
    await userEvent.click(screen.getByRole("button", { name: /open navigation/i }));
    await userEvent.click(await screen.findByRole("button", { name: "Dash dashboard" }));
  };

  test("embeds Dash in the page, following the selected dataset", async () => {
    global.fetch = jest.fn().mockResolvedValue({});
    await openDashView();
    const frame = await screen.findByTitle("Plotly Dash dashboard");
    expect(frame).toHaveAttribute("src", `http://localhost:8050/?table=${TABLE}&embed=1`);
    expect(screen.queryByRole("link", { name: /dash dashboard/i })).not.toBeInTheDocument(); // no new-tab link
  });

  test("explains how to start Dash when it is not running", async () => {
    global.fetch = jest.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    await openDashView();
    expect(await screen.findByText("The Dash dashboard is not running")).toBeInTheDocument();
    expect(screen.getByText("python -m dashboard.app")).toBeInTheDocument();
  });
});
