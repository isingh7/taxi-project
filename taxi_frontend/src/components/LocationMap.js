import React from "react";
import GoogleMapReact from "google-map-react";
import { Box, Typography } from "@mui/material";
import MapOutlinedIcon from "@mui/icons-material/MapOutlined";
import { chartColors } from "../theme";
import { DEMO_MODE } from "../api";

const MAPS_KEY = process.env.REACT_APP_GOOGLE_MAPS_API_KEY;
const NYC_CENTER = { lat: 40.7484, lng: -73.9857 };

const hasCoords = (loc) => loc && loc.latitude != null && loc.longitude != null;

export const mapCenter = (pickup, dropoff) => {
  if (hasCoords(pickup) && hasCoords(dropoff)) {
    return {
      lat: (Number(pickup.latitude) + Number(dropoff.latitude)) / 2,
      lng: (Number(pickup.longitude) + Number(dropoff.longitude)) / 2,
    };
  }
  return NYC_CENTER;
};

// Muted base map so the two markers carry the attention.
const MAP_STYLES = [
  { elementType: "geometry", stylers: [{ color: "#f3f4f6" }] },
  { elementType: "labels.text.fill", stylers: [{ color: "#6b7280" }] },
  { featureType: "poi", stylers: [{ visibility: "off" }] },
  { featureType: "road", elementType: "geometry", stylers: [{ color: "#ffffff" }] },
  { featureType: "water", elementType: "geometry", stylers: [{ color: "#dbe7f3" }] },
  { featureType: "transit", stylers: [{ visibility: "off" }] },
];

const Pin = ({ label, color }) => (
  <Box sx={{ position: "absolute", transform: "translate(-50%, -100%)", display: "flex", flexDirection: "column", alignItems: "center" }}>
    <Box sx={{ px: 1, py: 0.25, mb: 0.5, borderRadius: 1, bgcolor: "#fff", border: 1, borderColor: "divider", boxShadow: 1, whiteSpace: "nowrap" }}>
      <Typography variant="caption" sx={{ fontWeight: 700 }}>{label}</Typography>
    </Box>
    <Box sx={{ width: 14, height: 14, borderRadius: "50%", bgcolor: color, border: "3px solid #fff", boxShadow: 2 }} />
  </Box>
);

export default function LocationMap({ pickup = {}, dropoff = {}, minHeight = 360 }) {
  if (!MAPS_KEY) {
    return (
      <Box sx={{ height: "100%", minHeight, borderRadius: 2, bgcolor: "background.default", border: 1, borderColor: "divider", display: "grid", placeItems: "center", textAlign: "center", p: 3 }}>
        <Box>
          <MapOutlinedIcon color="disabled" />
          <Typography variant="body2" color="text.secondary">
            {DEMO_MODE
              ? "The map is not available in this demo."
              : "Map disabled. Set REACT_APP_GOOGLE_MAPS_API_KEY in .env.local."}
          </Typography>
        </Box>
      </Box>
    );
  }
  return (
    <Box sx={{ height: "100%", minHeight, borderRadius: 2, overflow: "hidden", border: 1, borderColor: "divider" }}>
      <GoogleMapReact
        bootstrapURLKeys={{ key: MAPS_KEY }}
        center={mapCenter(pickup, dropoff)}
        defaultZoom={12}
        options={{ styles: MAP_STYLES, disableDefaultUI: true, zoomControl: true }}
      >
        {hasCoords(pickup) && (
          <Pin lat={Number(pickup.latitude)} lng={Number(pickup.longitude)} label="Top pickup" color={chartColors.series[0]} />
        )}
        {hasCoords(dropoff) && (
          <Pin lat={Number(dropoff.latitude)} lng={Number(dropoff.longitude)} label="Top drop-off" color={chartColors.series[1]} />
        )}
      </GoogleMapReact>
    </Box>
  );
}
