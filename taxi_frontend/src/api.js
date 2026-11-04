import axios from "axios";

export const API_URL = (process.env.REACT_APP_API_URL || "http://localhost:8000/api").replace(/\/$/, "");
export const DASHBOARD_URL = process.env.REACT_APP_DASHBOARD_URL || "http://localhost:8050";

const client = axios.create({ baseURL: API_URL, timeout: 60000 });

export const getHeadlineStats = (table) => client.get(`/data/${table}/`).then((r) => r.data);
export const getAnalytics = (table) => client.get(`/analytics/${table}/`).then((r) => r.data);
export const getDataQuality = (table) => client.get(`/data-quality/${table}/`).then((r) => r.data);
export const getTables = () => client.get("/tables/").then((r) => r.data);
export const getIngestionRuns = () => client.get("/ingestion-runs/").then((r) => r.data);
export const dailyCsvUrl = (table) => `${API_URL}/analytics/${table}/daily.csv`;

/** Turn an axios error into a sentence a business user can act on. */
export function describeError(error) {
  if (error?.response?.data?.hint) {
    return `${error.response.data.detail} Load it with: ${error.response.data.hint}`;
  }
  if (error?.response?.data?.detail) return error.response.data.detail;
  if (error?.request) return `Cannot reach the API at ${API_URL}. Is the Django server running?`;
  return "Something went wrong while loading data.";
}
