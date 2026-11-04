import React from "react";
import { Box } from "@mui/material";
import { Bar } from "react-chartjs-2";
import { chartColors } from "../../theme";

/** Draws each bar's value just past its end, so the x-axis can be hidden. */
const endLabels = {
  id: "endLabels",
  afterDatasetsDraw(chart, _args, opts) {
    const { ctx } = chart;
    ctx.save();
    ctx.font = '500 12px "Inter", -apple-system, "Segoe UI", Roboto, sans-serif';
    ctx.fillStyle = chartColors.inkSecondary;
    ctx.textBaseline = "middle";
    chart.getDatasetMeta(0).data.forEach((bar, i) => {
      ctx.fillText(opts.format(chart.data.datasets[0].data[i]), bar.x + 6, bar.y);
    });
    ctx.restore();
  },
};

/** Horizontal bars, largest first. Used instead of pie charts for part-to-whole. */
export default function RankedBarChart({ rows = [], label, value, format = String, ariaLabel }) {
  const sorted = [...rows].sort((a, b) => (b[value] || 0) - (a[value] || 0));
  const values = sorted.map((r) => Number(r[value] || 0));
  const max = Math.max(...values, 1);
  const data = {
    labels: sorted.map((r) => r[label]),
    datasets: [
      {
        data: values,
        backgroundColor: chartColors.series[0],
        hoverBackgroundColor: "#1c5cab",
        borderRadius: { topRight: 4, bottomRight: 4 },
        borderSkipped: "left",
        barThickness: 18,
      },
    ],
  };
  const options = {
    indexAxis: "y",
    layout: { padding: { right: 8 } },
    scales: {
      x: { display: false, beginAtZero: true, max: max * 1.25 },
      y: {
        border: { display: false },
        grid: { display: false },
        ticks: { color: chartColors.inkSecondary, font: { weight: 500 } },
      },
    },
    plugins: {
      endLabels: { format },
      tooltip: { callbacks: { label: (ctx) => ` ${format(ctx.parsed.x)}` } },
    },
  };
  return (
    <Box sx={{ position: "relative", width: "100%", height: Math.max(160, sorted.length * 36 + 20) }} role="img" aria-label={ariaLabel}>
      <Bar data={data} options={options} plugins={[endLabels]} />
    </Box>
  );
}
