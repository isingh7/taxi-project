import axios from "axios";

/**
 * Demo mode (REACT_APP_DEMO_MODE=true) reads a static snapshot of the API's responses
 * from /demo-data, so the app can be hosted on GitHub Pages without a server.
 * The snapshot is produced by `manage.py export_static_api` from the real endpoints.
 */
export const DEMO_MODE = process.env.REACT_APP_DEMO_MODE === "true";

const DEMO_BASE = `${process.env.PUBLIC_URL || ""}/demo-data`;
export const API_URL = DEMO_MODE
  ? DEMO_BASE
  : (process.env.REACT_APP_API_URL || "http://localhost:8000/api").replace(/\/$/, "");
export const DASHBOARD_URL = process.env.REACT_APP_DASHBOARD_URL || "http://localhost:8050";

const client = axios.create({ baseURL: API_URL, timeout: 60000 });

// Live API path -> static file path.
const path = (live, demo) => (DEMO_MODE ? demo : live);

export const getHeadlineStats = (table) =>
  client.get(path(`/data/${table}/`, `/data/${table}.json`)).then((r) => r.data);
export const getAnalytics = (table) =>
  client.get(path(`/analytics/${table}/`, `/analytics/${table}.json`)).then((r) => r.data);
export const getDataQuality = (table) =>
  client.get(path(`/data-quality/${table}/`, `/data-quality/${table}.json`)).then((r) => r.data);
export const getTables = () => client.get(path("/tables/", "/tables.json")).then((r) => r.data);
export const getIngestionRuns = () =>
  client.get(path("/ingestion-runs/", "/ingestion-runs.json")).then((r) => r.data);
export const dailyCsvUrl = (table) => `${API_URL}/analytics/${table}/daily.csv`;

/** Turn an axios error into a sentence a business user can act on. */
export function describeError(error) {
  if (DEMO_MODE && error?.response?.status === 404) {
    return "This dataset is not included in the demo snapshot. Pick another dataset.";
  }
  if (error?.response?.data?.hint) {
    return `${error.response.data.detail} Load it with: ${error.response.data.hint}`;
  }
  if (error?.response?.data?.detail) return error.response.data.detail;
  if (error?.request) return `Cannot reach the API at ${API_URL}. Is the Django server running?`;
  return "Something went wrong while loading data.";
}
