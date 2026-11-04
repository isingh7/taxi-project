import React from "react";
import { Box } from "@mui/material";
import { Bar } from "react-chartjs-2";
import { categoryAxis, valueAxis } from "./setup";
import { chartColors } from "../../theme";
import { money, num } from "../../format";

export default function FareHistogram({ dist = {}, height = 260 }) {
  const edges = dist.edges || [];
  const counts = dist.counts || [];
  const data = {
    labels: counts.map((_, i) => `$${Math.round(edges[i])}`),
    datasets: [
      {
        label: "Trips",
        data: counts,
        backgroundColor: chartColors.series[0],
        hoverBackgroundColor: "#1c5cab",
        borderRadius: { topLeft: 3, topRight: 3 },
        borderSkipped: "bottom",
        categoryPercentage: 1,
        barPercentage: 0.94,
      },
    ],
  };
  const options = {
    scales: {
      x: categoryAxis({ ticks: { maxTicksLimit: 8 } }),
      y: valueAxis({ ticks: { callback: (v) => num(v) } }),
    },
    plugins: {
      tooltip: {
        callbacks: {
          title: (items) => {
            const i = items[0].dataIndex;
            return `${money(edges[i])} – ${money(edges[i + 1])}`;
          },
          label: (ctx) => ` ${num(ctx.parsed.y)} trips`,
        },
      },
    },
  };
  return (
    <Box sx={{ position: "relative", height, width: "100%" }} role="img" aria-label="Histogram of fares">
      <Bar data={data} options={options} />
    </Box>
  );
}
