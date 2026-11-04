import React, { useEffect, useState } from "react";
import { Alert, AlertTitle, Box, CircularProgress, Collapse, Stack } from "@mui/material";
import SpaceDashboardOutlinedIcon from "@mui/icons-material/SpaceDashboardOutlined";
import PaidOutlinedIcon from "@mui/icons-material/PaidOutlined";
import PlaceOutlinedIcon from "@mui/icons-material/PlaceOutlined";
import FactCheckOutlinedIcon from "@mui/icons-material/FactCheckOutlined";
import InsightsOutlinedIcon from "@mui/icons-material/InsightsOutlined";
import "./components/charts/setup";
import AppShell from "./components/AppShell";
import OverviewView from "./views/OverviewView";
import RevenueView from "./views/RevenueView";
import OperationsView from "./views/OperationsView";
import DataQualityView from "./views/DataQualityView";
import DashView from "./views/DashView";
import useDashboardData from "./hooks/useDashboardData";
import { dailyCsvUrl, getTables } from "./api";

export const VIEWS = [
  { id: "overview", label: "Overview", icon: SpaceDashboardOutlinedIcon, component: OverviewView },
  { id: "revenue", label: "Revenue", icon: PaidOutlinedIcon, component: RevenueView },
  { id: "operations", label: "Demand & locations", icon: PlaceOutlinedIcon, component: OperationsView },
  { id: "quality", label: "Data quality", icon: FactCheckOutlinedIcon, component: DataQualityView },
  { id: "dash", label: "Dash dashboard", icon: InsightsOutlinedIcon, component: DashView, standalone: true },
];

const DEFAULT_TABLE = "tlc_yellow_trips_2015";

const viewFromHash = () => {
  const id = window.location.hash.replace("#", "");
  return VIEWS.some((v) => v.id === id) ? id : "overview";
};

export default function App() {
  // The view lives in the URL hash, so views can be bookmarked and the back button works.
  const [view, setViewState] = useState(viewFromHash);
  const setView = (id) => {
    window.location.hash = id;
    setViewState(id);
  };

  useEffect(() => {
    const onHashChange = () => setViewState(viewFromHash());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);
  const [tables, setTables] = useState([]);
  const [table, setTable] = useState(DEFAULT_TABLE);
  const data = useDashboardData(table);

  // Start on a table that actually has data in the local store.
  useEffect(() => {
    getTables()
      .then((list) => {
        setTables(list);
        const loaded = list.filter((t) => t.loaded).map((t) => t.table);
        setTable((current) => (loaded.length && !loaded.includes(current) ? loaded[0] : current));
      })
      .catch(() => {}); // connection problems are reported by the data hook
  }, []);

  useEffect(() => {
    window.scrollTo?.({ top: 0 });
  }, [view]);

  const current = VIEWS.find((v) => v.id === view);
  const View = current.component;
  const firstLoad = data.loading && !data.analytics && !data.error;

  return (
    <AppShell
      views={VIEWS}
      currentView={view}
      onViewChange={setView}
      tables={tables}
      table={table}
      onTableChange={setTable}
      dataSource={data.headline?.data_source}
      quality={data.quality}
      csvUrl={dailyCsvUrl(table)}
    >
      {current.standalone ? (
        // The Dash view loads its own data, so API errors on this page do not block it.
        <View table={table} />
      ) : data.error ? (
        <Alert severity="error" variant="outlined" role="alert">
          <AlertTitle>Could not load data</AlertTitle>
          {data.error}
        </Alert>
      ) : firstLoad ? (
        <Box sx={{ display: "grid", placeItems: "center", py: 12 }}>
          <CircularProgress aria-label="Loading data" />
        </Box>
      ) : (
        <Box sx={{ opacity: data.loading ? 0.55 : 1, transition: "opacity 150ms" }} aria-busy={data.loading}>
          <Collapse in={Boolean(data.warnings?.length)}>
            <Stack spacing={1} sx={{ mb: 2 }}>
              {(data.warnings || []).map((w) => (
                <Alert key={w} severity="warning" variant="outlined">{w}</Alert>
              ))}
            </Stack>
          </Collapse>
          <View table={table} {...data} />
        </Box>
      )}
    </AppShell>
  );
}
