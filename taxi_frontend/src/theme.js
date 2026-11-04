import { createTheme } from "@mui/material/styles";

/** Chart colours: validated colour-blind-safe order, shared with the Dash dashboard. */
export const chartColors = {
  series: ["#2a78d6", "#eb6834", "#1baf7a"],
  critical: "#d03b3b",
  grid: "#e1e0d9",
  axis: "#898781",
  ink: "#0b0b0b",
  inkSecondary: "#52514e",
};

const ink = "#14171f";

const theme = createTheme({
  palette: {
    mode: "light",
    primary: { main: "#1f5fbf", dark: "#174a96", light: "#e8f0fb", contrastText: "#fff" },
    secondary: { main: ink },
    error: { main: "#c62f2f" },
    warning: { main: "#b7791f" },
    success: { main: "#1e7f4f" },
    background: { default: "#f6f7f9", paper: "#ffffff" },
    text: { primary: ink, secondary: "#5b6170" },
    divider: "#e3e6eb",
  },
  shape: { borderRadius: 10 },
  typography: {
    fontFamily: '"Inter", -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    h4: { fontWeight: 700, letterSpacing: "-0.02em" },
    h5: { fontWeight: 700, letterSpacing: "-0.01em" },
    h6: { fontWeight: 650, fontSize: "1rem" },
    subtitle2: { fontWeight: 600 },
    overline: { fontWeight: 600, letterSpacing: "0.06em", lineHeight: 1.6 },
    button: { textTransform: "none", fontWeight: 600 },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: { fontFeatureSettings: '"tnum" 1, "cv11" 1' },
      },
    },
    MuiPaper: {
      defaultProps: { elevation: 0 },
      styleOverrides: { root: { backgroundImage: "none" } },
    },
    MuiCard: {
      defaultProps: { variant: "outlined" },
      styleOverrides: { root: { borderColor: "#e3e6eb" } },
    },
    MuiAppBar: {
      defaultProps: { elevation: 0, color: "inherit" },
      styleOverrides: { root: { borderBottom: "1px solid #e3e6eb" } },
    },
    MuiButton: { defaultProps: { disableElevation: true } },
    MuiTableCell: {
      styleOverrides: {
        head: { fontWeight: 600, color: "#5b6170", fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.04em" },
        root: { borderColor: "#eef0f3" },
      },
    },
    MuiChip: { styleOverrides: { root: { fontWeight: 600 } } },
    MuiListItemButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          margin: "2px 8px",
          "&.Mui-selected": { backgroundColor: "#e8f0fb", color: "#1f5fbf" },
          "&.Mui-selected .MuiListItemIcon-root": { color: "#1f5fbf" },
        },
      },
    },
  },
});

export default theme;
