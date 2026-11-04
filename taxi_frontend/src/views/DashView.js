import React, { useEffect, useState } from "react";
import { Alert, AlertTitle, Box, Button, Card, CircularProgress } from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import PageHeader from "../components/PageHeader";
import { DASHBOARD_URL } from "../api";
import { tableLabel } from "../format";

export const dashEmbedUrl = (table) =>
  `${DASHBOARD_URL.replace(/\/$/, "")}/?table=${encodeURIComponent(table)}&embed=1`;

/**
 * The Plotly Dash dashboard, embedded in the page. It follows the dataset picked
 * in the top bar; Dash hides its own header and picker in embed mode.
 */
export default function DashView({ table }) {
  const [status, setStatus] = useState("checking"); // checking | up | down
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setStatus("checking");
    // no-cors: we only need to know whether the server answers at all.
    fetch(DASHBOARD_URL, { mode: "no-cors", cache: "no-store" })
      .then(() => !cancelled && setStatus("up"))
      .catch(() => !cancelled && setStatus("down"));
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  return (
    <>
      <PageHeader
        title="Dash dashboard"
        description={`The Python (Plotly Dash) version of the dashboard for ${tableLabel(table)} trips, embedded here.`}
      />
      {status === "down" ? (
        <Alert
          severity="warning"
          variant="outlined"
          action={
            <Button color="inherit" size="small" startIcon={<RefreshIcon />} onClick={() => setAttempt((n) => n + 1)}>
              Retry
            </Button>
          }
        >
          <AlertTitle>The Dash dashboard is not running</AlertTitle>
          Start it from the project folder with <code>python -m dashboard.app</code>, then press Retry.
        </Alert>
      ) : (
        <Card sx={{ overflow: "hidden", position: "relative", height: "calc(100vh - 220px)", minHeight: 560 }}>
          {status === "checking" && (
            <Box sx={{ position: "absolute", inset: 0, display: "grid", placeItems: "center" }}>
              <CircularProgress aria-label="Loading dashboard" />
            </Box>
          )}
          {status === "up" && (
            <Box
              component="iframe"
              key={table}
              title="Plotly Dash dashboard"
              src={dashEmbedUrl(table)}
              sx={{ border: 0, width: "100%", height: "100%", display: "block", bgcolor: "#f9f9f7" }}
            />
          )}
        </Card>
      )}
    </>
  );
}
