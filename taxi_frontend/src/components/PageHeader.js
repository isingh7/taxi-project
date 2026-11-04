import React from "react";
import { Box, Typography } from "@mui/material";

export default function PageHeader({ title, description, actions }) {
  return (
    <Box sx={{ display: "flex", gap: 2, alignItems: { sm: "flex-end" }, justifyContent: "space-between", flexDirection: { xs: "column", sm: "row" }, mb: 3 }}>
      <Box>
        <Typography variant="h5" component="h1">{title}</Typography>
        {description && (
          <Typography color="text.secondary" sx={{ mt: 0.5, maxWidth: 720 }}>{description}</Typography>
        )}
      </Box>
      {actions}
    </Box>
  );
}
