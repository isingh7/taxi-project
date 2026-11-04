import React from "react";
import { Box, Tooltip, Typography } from "@mui/material";
import { num } from "../../format";

// Sequential blue ramp (one hue, light to dark); the lightest step means "few trips".
const RAMP = ["#eef4fc", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"];

const colorFor = (value, max) => RAMP[Math.min(RAMP.length - 1, Math.floor((value / Math.max(max, 1)) * RAMP.length))];

/** Weekday x hour grid of trip counts, drawn with CSS grid (no chart library needed). */
export default function DemandHeatmap({ grid }) {
  if (!grid?.trips?.length) return <Typography color="text.secondary">No trips to chart.</Typography>;
  const max = Math.max(...grid.trips.flat());
  const hours = grid.hours || [...Array(24).keys()];

  return (
    <Box sx={{ overflowX: "auto" }}>
      <Box
        role="table"
        aria-label="Trips by weekday and pickup hour"
        sx={{ display: "grid", gridTemplateColumns: "44px repeat(24, minmax(18px, 1fr))", gap: "2px", minWidth: 560 }}
      >
        <Box role="row" sx={{ display: "contents" }}>
          <span />
          {hours.map((h) => (
            <Typography key={h} role="columnheader" variant="caption" color="text.secondary" sx={{ textAlign: "center", fontSize: 10.5 }}>
              {h % 3 === 0 ? String(h).padStart(2, "0") : ""}
            </Typography>
          ))}
        </Box>
        {grid.trips.map((row, d) => (
          <Box role="row" key={grid.weekdays[d]} sx={{ display: "contents" }}>
            <Typography role="rowheader" variant="caption" color="text.secondary" sx={{ alignSelf: "center", fontWeight: 600 }}>
              {grid.weekdays[d].slice(0, 3)}
            </Typography>
            {row.map((value, h) => (
              <Tooltip key={h} title={`${grid.weekdays[d]} ${String(h).padStart(2, "0")}:00 · ${num(value)} trips`} disableInteractive>
                <Box role="cell" aria-label={`${grid.weekdays[d]} ${h}:00, ${value} trips`}
                  sx={{ height: 26, borderRadius: "3px", bgcolor: colorFor(value, max) }} />
              </Tooltip>
            ))}
          </Box>
        ))}
      </Box>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mt: 1.5, justifyContent: "flex-end" }}>
        <Typography variant="caption" color="text.secondary">Fewer trips</Typography>
        <Box sx={{ display: "flex", gap: "2px" }} aria-hidden>
          {RAMP.map((c) => <Box key={c} sx={{ width: 18, height: 10, borderRadius: "2px", bgcolor: c }} />)}
        </Box>
        <Typography variant="caption" color="text.secondary">More ({num(max)} max)</Typography>
      </Box>
    </Box>
  );
}
