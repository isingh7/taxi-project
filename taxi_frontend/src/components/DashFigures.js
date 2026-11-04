import React, { useEffect, useRef, useState } from "react";
import { Alert, Box, CircularProgress, Grid } from "@mui/material";
import Panel from "./Panel";
import FindingsList from "./FindingsList";
import { API_URL } from "../api";

// Same plotly.js version the Python Plotly package (5.22) bundles, so the charts
// render exactly as they do in the Dash server.
const PLOTLY_SRC = "https://cdnjs.cloudflare.com/ajax/libs/plotly.js/2.32.0/plotly.min.js";

export const dashFiguresUrl = (table) => `${API_URL}/dash/${table}.json`;

let plotlyPromise = null;
function loadPlotly() {
  if (window.Plotly) return Promise.resolve(window.Plotly);
  if (!plotlyPromise) {
    plotlyPromise = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = PLOTLY_SRC;
      script.async = true;
      script.onload = () => resolve(window.Plotly);
      script.onerror = () => {
        plotlyPromise = null;
        reject(new Error("Could not load the charting library. Check your connection and reload."));
      };
      document.head.appendChild(script);
    });
  }
  return plotlyPromise;
}

function PlotlyFigure({ figure, height }) {
  const ref = useRef(null);

  useEffect(() => {
    const el = ref.current;
    let cancelled = false;
    loadPlotly().then((Plotly) => {
      if (cancelled || !el) return;
      Plotly.react(el, figure.data, { ...figure.layout, autosize: true }, {
        responsive: true,
        displaylogo: false,
        modeBarButtonsToRemove: ["lasso2d", "select2d"],
      });
    });
    return () => {
      cancelled = true;
      if (window.Plotly && el) window.Plotly.purge(el);
    };
  }, [figure]);

  // Fixed height: the container sets the size, so a resize can never grow the chart.
  return <Box ref={ref} sx={{ height, width: "100%" }} />;
}

/**
 * The Dash dashboard for one dataset: findings plus the charts, built at deploy time by
 * the Dash app's own Python figure code (dashboard/figures.py) and drawn with plotly.js.
 */
export default function DashFigures({ table }) {
  const [state, setState] = useState({ loading: true });

  useEffect(() => {
    let cancelled = false;
    setState({ loading: true });
    Promise.all([
      fetch(dashFiguresUrl(table)).then((r) => {
        if (!r.ok) throw new Error("These charts are not included in the demo snapshot.");
        return r.json();
      }),
      loadPlotly(),
    ])
      .then(([dash]) => !cancelled && setState({ dash }))
      .catch((error) => !cancelled && setState({ error: error.message }));
    return () => {
      cancelled = true;
    };
  }, [table]);

  if (state.error) return <Alert severity="warning" variant="outlined">{state.error}</Alert>;
  if (state.loading) {
    return (
      <Box sx={{ display: "grid", placeItems: "center", py: 10 }}>
        <CircularProgress aria-label="Loading charts" />
      </Box>
    );
  }
  return (
    <Grid container spacing={2}>
      <Grid item xs={12}>
        <Panel title="Key findings" subtitle="Written from the data for this dataset.">
          <FindingsList findings={state.dash.findings} />
        </Panel>
      </Grid>
      {state.dash.charts.map((chart) => (
        <Grid item xs={12} lg={chart.full_width ? 12 : 6} key={chart.id}>
          <Panel title={chart.title} subtitle={chart.subtitle} contentSx={{ px: 1, pb: "8px !important" }}>
            <PlotlyFigure figure={chart.figure} height={chart.height} />
          </Panel>
        </Grid>
      ))}
    </Grid>
  );
}
