import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
} from "chart.js";
import { chartColors } from "../../theme";

ChartJS.register(BarElement, CategoryScale, Filler, Legend, LinearScale, LineElement, PointElement, Tooltip);

ChartJS.defaults.font.family = '"Inter", -apple-system, "Segoe UI", Roboto, sans-serif';
ChartJS.defaults.font.size = 12;
ChartJS.defaults.color = chartColors.axis;
ChartJS.defaults.maintainAspectRatio = false;
ChartJS.defaults.plugins.legend.display = false; // legends are rendered in HTML next to the title
ChartJS.defaults.plugins.tooltip.backgroundColor = "#ffffff";
ChartJS.defaults.plugins.tooltip.titleColor = chartColors.ink;
ChartJS.defaults.plugins.tooltip.bodyColor = chartColors.inkSecondary;
ChartJS.defaults.plugins.tooltip.borderColor = "#d9dce1";
ChartJS.defaults.plugins.tooltip.borderWidth = 1;
ChartJS.defaults.plugins.tooltip.padding = 10;
ChartJS.defaults.plugins.tooltip.boxPadding = 4;
ChartJS.defaults.plugins.tooltip.usePointStyle = true;

/** Shared axis styling: recessive grid, no axis border clutter. */
export const valueAxis = (extra = {}) => ({
  beginAtZero: true,
  border: { display: false },
  grid: { color: chartColors.grid, drawTicks: false },
  ...extra,
  ticks: { padding: 8, maxTicksLimit: 6, ...(extra.ticks || {}) },
});

export const categoryAxis = (extra = {}) => ({
  border: { color: "#c3c2b7" },
  grid: { display: false },
  ...extra,
  ticks: { padding: 6, autoSkip: true, maxRotation: 0, ...(extra.ticks || {}) },
});
