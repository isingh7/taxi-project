import React from "react";
import { Box } from "@mui/material";
import { Line } from "react-chartjs-2";
import { categoryAxis, valueAxis } from "./setup";
import { chartColors } from "../../theme";
import { shortDate } from "../../format";

export default function DrawdownChart({ daily = [], height = 200 }) {
  const data = {
    labels: daily.map((d) => shortDate(d.date)),
    datasets: [
      {
        label: "Drawdown",
        data: daily.map((d) => d.drawdown_pct),
        borderColor: chartColors.series[0],
        backgroundColor: "rgba(42,120,214,0.12)",
        fill: "origin",
        borderWidth: 2,
        cubicInterpolationMode: "monotone",
        pointRadius: 0,
        pointHoverRadius: 4,
      },
    ],
  };
  const options = {
    interaction: { mode: "index", intersect: false },
    scales: {
      x: categoryAxis({ ticks: { maxTicksLimit: 8 } }),
      y: valueAxis({ beginAtZero: false, max: 0, ticks: { callback: (v) => `${v}%` } }),
    },
    plugins: {
      tooltip: {
        callbacks: {
          label: (ctx) =>
            ctx.parsed.y == null ? " Building 7-day window" : ` ${ctx.parsed.y.toFixed(1)}% below peak`,
        },
      },
    },
  };
  return (
    <Box sx={{ position: "relative", height, width: "100%" }} role="img" aria-label="Area chart of revenue drawdown from its running peak">
      <Line data={data} options={options} />
    </Box>
  );
}
