import React from "react";
import { Box } from "@mui/material";
import { Bar } from "react-chartjs-2";
import { categoryAxis, valueAxis } from "./setup";
import { chartColors } from "../../theme";
import { money, num, pct } from "../../format";

export default function HourlyChart({ hourly = [], height = 260 }) {
  const labels = hourly.map((h) => `${String(h.hour).padStart(2, "0")}:00`);
  const data = {
    labels,
    datasets: [
      {
        label: "Trips",
        data: hourly.map((h) => h.trips),
        backgroundColor: chartColors.series[0],
        hoverBackgroundColor: "#1c5cab",
        borderRadius: { topLeft: 4, topRight: 4 },
        borderSkipped: "bottom",
        categoryPercentage: 0.82,
        barPercentage: 0.95,
      },
    ],
  };
  const options = {
    scales: {
      x: categoryAxis({ ticks: { autoSkip: false, callback: (_, i) => (i % 3 === 0 ? labels[i] : "") } }),
      y: valueAxis({ ticks: { callback: (v) => num(v) } }),
    },
    plugins: {
      tooltip: {
        callbacks: {
          label: (ctx) => {
            const h = hourly[ctx.dataIndex];
            return [` ${num(h.trips)} trips (${pct(h.share_pct)} of day)`, ` Avg fare ${money(h.avg_fare)}`];
          },
        },
      },
    },
  };
  return (
    <Box sx={{ position: "relative", height, width: "100%" }} role="img" aria-label="Bar chart of trips by pickup hour">
      <Bar data={data} options={options} />
    </Box>
  );
}
