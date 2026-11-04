import React, { useEffect, useRef, useState } from "react";
import { Alert, Box, Card, CircularProgress, Grid } from "@mui/material";
import { API_URL } from "../api";

// Same plotly.js version the Python Plotly package (5.22) bundles, so the charts
// render exactly as they do in the Dash server.
const PLOTLY_SRC = "https://cdnjs.cloudflare.com/ajax/libs/plotly.js/2.32.0/plotly.min.js";

// Mirrors GRAPH_HEIGHTS in dashboard/app.py. Fixed heights keep charts from resizing in a loop.
export const FIGURE_LAYOUT = [
  { id: "daily", height: 340, full: true },
  { id: "drawdown", height: 240, full: true },
  { id: "hourly", height: 320 },
  { id: "fares", height: 320 },
  { id: "boroughs", height: 300 },
  { id: "payments", height: 300 },
];

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
        reject(new Error("Could not load the charting library."));
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
      });
    });
    return () => {
      cancelled = true;
      if (window.Plotly && el) window.Plotly.purge(el);
    };
  }, [figure]);

  return <Box ref={ref} sx={{ height, width: "100%" }} />;
}

/**
 * The Dash dashboard's charts for one dataset, built in Python by the same figure
 * code as the Dash server and drawn here with plotly.js. Used on static hosting.
 */
export default function DashFigures({ table }) {
  const [state, setState] = useState({ loading: true });

  useEffect(() => {
    let cancelled = false;
    setState({ loading: true });
    Promise.all([fetch(dashFiguresUrl(table)).then((r) => {
      if (!r.ok) throw new Error("These charts are not included in the demo snapshot.");
      return r.json();
    }), loadPlotly()])
      .then(([figures]) => !cancelled && setState({ figures }))
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
      {FIGURE_LAYOUT.map(({ id, height, full }) => (
        <Grid item xs={12} lg={full ? 12 : 6} key={id}>
          <Card sx={{ overflow: "hidden", bgcolor: "#fcfcfb" }}>
            <PlotlyFigure figure={state.figures[id]} height={height} />
          </Card>
        </Grid>
      ))}
    </Grid>
  );
}
