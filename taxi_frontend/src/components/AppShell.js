import React, { useState } from "react";
import {
  AppBar,
  Box,
  Button,
  Chip,
  Divider,
  Drawer,
  FormControl,
  IconButton,
  InputLabel,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  ListSubheader,
  MenuItem,
  Select,
  Toolbar,
  Tooltip,
  Typography,
  useMediaQuery,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import MenuIcon from "@mui/icons-material/Menu";
import LocalTaxiIcon from "@mui/icons-material/LocalTaxi";
import FileDownloadOutlinedIcon from "@mui/icons-material/FileDownloadOutlined";
import { tableLabel, num } from "../format";

export const DRAWER_WIDTH = 248;

function Brand() {
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1.25, px: 2.5, height: 64 }}>
      <Box sx={{ width: 34, height: 34, borderRadius: 2, bgcolor: "secondary.main", color: "#f5c518", display: "grid", placeItems: "center" }}>
        <LocalTaxiIcon fontSize="small" />
      </Box>
      <Box>
        <Typography sx={{ fontWeight: 700, lineHeight: 1.1 }}>NYC Taxi</Typography>
        <Typography variant="caption" color="text.secondary">Revenue analytics</Typography>
      </Box>
    </Box>
  );
}

function Navigation({ views, current, onSelect, quality }) {
  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <Brand />
      <Divider />
      <List component="nav" aria-label="Sections" sx={{ py: 1.5 }}>
        {views.map(({ id, label, icon: Icon }) => (
          <ListItemButton key={id} selected={current === id} onClick={() => onSelect(id)}>
            <ListItemIcon sx={{ minWidth: 36 }}><Icon fontSize="small" /></ListItemIcon>
            <ListItemText primary={label} primaryTypographyProps={{ fontWeight: 600, fontSize: "0.9rem" }} />
          </ListItemButton>
        ))}
      </List>
      <Box sx={{ mt: "auto", p: 2.5 }}>
        {quality && (
          <Box sx={{ p: 1.5, borderRadius: 2, bgcolor: "background.default", border: 1, borderColor: "divider" }}>
            <Typography variant="caption" color="text.secondary">Last load</Typography>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>
              {num(quality.rows_loaded)} trips · {quality.quality_report?.pass_rate_pct}% passed
            </Typography>
          </Box>
        )}
      </Box>
    </Box>
  );
}

function DatasetSelect({ tables, value, onChange }) {
  const loaded = tables.length ? tables : [{ table: value, loaded: true, trips: 0 }];
  const group = (color) => loaded.filter((t) => t.table?.includes(`_${color}_`));
  const option = (t) => (
    <MenuItem key={t.table} value={t.table} disabled={!t.loaded}>
      <Box sx={{ display: "flex", justifyContent: "space-between", width: "100%", gap: 2 }}>
        <span>{tableLabel(t.table)}</span>
        <Typography variant="caption" color="text.secondary">
          {t.loaded ? `${num(t.trips)} trips` : "not loaded"}
        </Typography>
      </Box>
    </MenuItem>
  );
  return (
    <FormControl size="small" sx={{ minWidth: { xs: 0, sm: 230 }, flex: { xs: 1, sm: "none" } }}>
      <InputLabel id="dataset-label">Dataset</InputLabel>
      <Select
        labelId="dataset-label"
        id="dataset"
        label="Dataset"
        value={value || ""}
        onChange={(e) => onChange(e.target.value)}
        renderValue={(v) => tableLabel(v)}
      >
        <ListSubheader>Yellow cabs</ListSubheader>
        {group("yellow").map(option)}
        <ListSubheader>Green cabs</ListSubheader>
        {group("green").map(option)}
      </Select>
    </FormControl>
  );
}

export default function AppShell({
  views, currentView, onViewChange, tables, table, onTableChange,
  dataSource, quality, csvUrl, children,
}) {
  const theme = useTheme();
  const desktop = useMediaQuery(theme.breakpoints.up("md"));
  const [mobileOpen, setMobileOpen] = useState(false);

  const select = (id) => {
    onViewChange(id);
    setMobileOpen(false);
  };
  const nav = <Navigation views={views} current={currentView} onSelect={select} quality={quality} />;

  return (
    <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "background.default" }}>
      <Box component="aside" sx={{ width: { md: DRAWER_WIDTH }, flexShrink: { md: 0 } }}>
        {desktop ? (
          <Drawer variant="permanent" open PaperProps={{ sx: { width: DRAWER_WIDTH, borderRight: 1, borderColor: "divider" } }}>
            {nav}
          </Drawer>
        ) : (
          <Drawer variant="temporary" open={mobileOpen} onClose={() => setMobileOpen(false)} ModalProps={{ keepMounted: true }} PaperProps={{ sx: { width: DRAWER_WIDTH } }}>
            {nav}
          </Drawer>
        )}
      </Box>

      <Box sx={{ flex: 1, minWidth: 0 }}>
        <AppBar position="sticky" sx={{ bgcolor: "rgba(255,255,255,0.92)", backdropFilter: "blur(8px)" }}>
          <Toolbar sx={{ gap: 1.5, minHeight: 64, px: { xs: 2, md: 3 } }}>
            {!desktop && (
              <IconButton edge="start" aria-label="Open navigation" onClick={() => setMobileOpen(true)}>
                <MenuIcon />
              </IconButton>
            )}
            <DatasetSelect tables={tables} value={table} onChange={onTableChange} />
            {dataSource && (
              <Tooltip
                title={dataSource === "bigquery"
                  ? "Headline figures queried live from the full BigQuery table"
                  : "Headline figures computed from the validated sample in the local store"}
              >
                <Chip
                  size="small"
                  variant="outlined"
                  label={dataSource === "bigquery" ? "Live · BigQuery" : "Local store"}
                  sx={{ display: { xs: "none", sm: "inline-flex" } }}
                />
              </Tooltip>
            )}
            <Box sx={{ flex: 1, display: { xs: "none", sm: "block" } }} />
            <Button
              variant="outlined"
              color="secondary"
              size="small"
              href={csvUrl}
              startIcon={<FileDownloadOutlinedIcon />}
              sx={{ display: { xs: "none", sm: "inline-flex" } }}
            >
              Export CSV
            </Button>
          </Toolbar>
        </AppBar>
        <Box component="main" sx={{ px: { xs: 2, md: 4 }, py: { xs: 3, md: 4 }, maxWidth: 1400, mx: "auto" }}>
          {children}
        </Box>
      </Box>
    </Box>
  );
}
