import React, { useState } from "react";
import { Alert, Link } from "@mui/material";

export const REPO_URL = process.env.REACT_APP_REPO_URL || "https://github.com/isingh7/taxi-project";

// localStorage so the notice stays dismissed across visits.
const STORAGE_KEY = "demo-notice-dismissed";

const wasDismissed = () => {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === "1";
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
      window.localStorage.setItem(STORAGE_KEY, "1");
    } catch {
      // Storage can be blocked; the notice just reappears on the next visit.
    }
  };

  return (
    <Alert
      severity="info"
      variant="outlined"
      onClose={dismiss}
      sx={{ mb: 3, py: 0, bgcolor: "background.paper", "& .MuiAlert-message": { py: 1 } }}
    >
      Demo with synthetic sample data (about 20,000 trips per dataset, including deliberate data defects).{" "}
      <Link href={REPO_URL} target="_blank" rel="noreferrer">Source code</Link>
    </Alert>
  );
}
