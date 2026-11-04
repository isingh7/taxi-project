import React from "react";
import { Box, Card, CardContent, Typography } from "@mui/material";

/** Card with a title row (title, optional subtitle, optional actions on the right). */
export default function Panel({ title, subtitle, actions, children, sx, contentSx }) {
  return (
    <Card sx={{ height: "100%", display: "flex", flexDirection: "column", ...sx }}>
      <Box sx={{ px: 2.5, pt: 2.25, pb: 1, display: "flex", gap: 2, alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap" }}>
        <Box>
          <Typography variant="h6" component="h2">{title}</Typography>
          {subtitle && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25 }}>
              {subtitle}
            </Typography>
          )}
        </Box>
        {actions}
      </Box>
      <CardContent sx={{ px: 2.5, pt: 1, flex: 1, ...contentSx }}>{children}</CardContent>
    </Card>
  );
}
