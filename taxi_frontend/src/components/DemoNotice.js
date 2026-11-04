import React, { useState } from "react";
import { Alert, Link } from "@mui/material";

export const REPO_URL = process.env.REACT_APP_REPO_URL || "https://github.com/isingh7/taxi-project";

const STORAGE_KEY = "demo-notice-dismissed";

const wasDismissed = () => {
  try {
    return window.sessionStorage.getItem(STORAGE_KEY) === "1";
  } catch {
    return false;
  }
};

/** Explains what the hosted demo is, so nobody mistakes the sample figures for real totals. */
export default function DemoNotice() {
  const [open, setOpen] = useState(!wasDismissed());
  if (!open) return null;

  const dismiss = () => {
    setOpen(false);
    try {
      window.sessionStorage.setItem(STORAGE_KEY, "1");
    } catch {
      // Storage can be blocked; the notice just reappears on the next visit.
    }
  };

  return (
    <Alert severity="info" variant="outlined" onClose={dismiss} sx={{ mb: 3, bgcolor: "background.paper" }}>
      <strong>Live demo.</strong> The figures come from a synthetic sample of about 20,000 NYC taxi trips per
      dataset, generated with realistic data defects so the quality checks have something to catch. The full
      version runs a Python API that loads the real trip data from Google BigQuery.{" "}
      <Link href={REPO_URL} target="_blank" rel="noreferrer">View the source code</Link>.
    </Alert>
  );
}
