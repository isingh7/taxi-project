import React from "react";
import { Box, Card, CardContent, Skeleton, Typography } from "@mui/material";

/** A single headline number. The number is the visual, so no chart and no colour. */
export default function KpiCard({ label, value, caption, icon: Icon, loading = false }) {
  return (
    <Card sx={{ height: "100%" }}>
      <CardContent sx={{ p: 2.5, "&:last-child": { pb: 2.5 } }}>
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 1 }}>
          <Typography variant="overline" color="text.secondary" component="h3">
            {label}
          </Typography>
          {Icon && (
            <Box
              sx={{
                width: 32, height: 32, borderRadius: 2, display: "grid", placeItems: "center",
                bgcolor: "primary.light", color: "primary.main",
              }}
              aria-hidden
            >
              <Icon fontSize="small" />
            </Box>
          )}
        </Box>
        {loading ? (
          <Skeleton width="60%" height={40} />
        ) : (
          <Typography variant="h4" component="p" sx={{ fontSize: { xs: "1.6rem", md: "1.85rem" } }}>
            {value}
          </Typography>
        )}
        {caption && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {loading ? <Skeleton width="80%" /> : caption}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}
