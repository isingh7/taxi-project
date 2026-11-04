import React from "react";
import { Box, Typography } from "@mui/material";

/** HTML legend: swatch shape matches the mark (line / dot / bar). */
export default function ChartLegend({ items }) {
  return (
    <Box component="ul" sx={{ display: "flex", flexWrap: "wrap", gap: 2, listStyle: "none", m: 0, p: 0 }}>
      {items.map(({ label, color, shape = "line" }) => (
        <Box component="li" key={label} sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
          <Box
            aria-hidden
            sx={{
              bgcolor: color,
              ...(shape === "line" && { width: 16, height: 3, borderRadius: 2 }),
              ...(shape === "dot" && { width: 9, height: 9, borderRadius: "50%" }),
              ...(shape === "bar" && { width: 10, height: 10, borderRadius: 0.5 }),
            }}
          />
          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 500 }}>
            {label}
          </Typography>
        </Box>
      ))}
    </Box>
  );
}
