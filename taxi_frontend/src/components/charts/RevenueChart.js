import React from "react";
import { Box } from "@mui/material";
import { Line } from "react-chartjs-2";
import { categoryAxis, valueAxis } from "./setup";
import { chartColors } from "../../theme";
import { money, moneyCompact, shortDate } from "../../format";

/** Daily revenue with its 7-day average; anomalous days marked in the reserved critical colour. */
export default function RevenueChart({ daily = [], height = 300 }) {
  const [blue, orange] = chartColors.series;
  const data = {
    labels: daily.map((d) => shortDate(d.date)),
    datasets: [
      {
        label: "Daily revenue",
        data: daily.map((d) => d.revenue),
        borderColor: blue,
        backgroundColor: blue,
        borderWidth: 2,
        cubicInterpolationMode: "monotone", // smooth but never overshoots real values
        pointRadius: daily.map((d) => (d.is_anomaly ? 5 : 0)),
        pointHoverRadius: 5,
        pointBackgroundColor: daily.map((d) => (d.is_anomaly ? chartColors.critical : blue)),
        pointBorderColor: "#fff",
        pointBorderWidth: 2,
      },
      {
        label: "7-day average",
        data: daily.map((d) => d.rolling_mean),
        borderColor: orange,
        backgroundColor: orange,
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
      y: valueAxis({ ticks: { callback: (v) => moneyCompact(v) } }),
    },
    plugins: {
      tooltip: {
        callbacks: {
          label: (ctx) => ` ${ctx.dataset.label}: ${money(ctx.parsed.y, 0)}`,
          afterBody: (items) =>
            daily[items[0].dataIndex]?.is_anomaly ? "▲ Anomaly: more than 3σ from the previous week" : "",
        },
      },
    },
  };
  return (
    <Box sx={{ position: "relative", height, width: "100%" }} role="img" aria-label="Line chart of daily revenue and its 7-day average">
      <Line data={data} options={options} />
    </Box>
  );
}
