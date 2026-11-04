import React from "react";
import { Box, Grid, Stack, Typography, Divider } from "@mui/material";
import PaidOutlinedIcon from "@mui/icons-material/PaidOutlined";
import LocalTaxiOutlinedIcon from "@mui/icons-material/LocalTaxiOutlined";
import ReceiptLongOutlinedIcon from "@mui/icons-material/ReceiptLongOutlined";
import VerifiedOutlinedIcon from "@mui/icons-material/VerifiedOutlined";
import KpiCard from "../components/KpiCard";
import Panel from "../components/Panel";
import PageHeader from "../components/PageHeader";
import RevenueChart from "../components/charts/RevenueChart";
import HourlyChart from "../components/charts/HourlyChart";
import ChartLegend from "../components/charts/Legend";
import { chartColors } from "../theme";
import { hourRange, minutes, money, moneyCompact, num, pct, tableLabel } from "../format";

function Highlight({ label, value, caption }) {
  return (
    <Box sx={{ py: 1.5 }}>
      <Typography variant="body2" color="text.secondary">{label}</Typography>
      <Typography variant="h6" component="p" sx={{ fontSize: "1.15rem", mt: 0.25 }}>{value}</Typography>
      {caption && <Typography variant="caption" color="text.secondary">{caption}</Typography>}
    </Box>
  );
}

export default function OverviewView({ table, headline, analytics, quality }) {
  const k = analytics?.kpis || {};
  const report = quality?.quality_report;
  const anomalies = (analytics?.daily || []).filter((d) => d.is_anomaly).length;
  const topBorough = analytics?.boroughs?.[0];
  const peak = headline?.most_popular_time_of_day;

  return (
    <>
      <PageHeader
        title="Overview"
        description={`Revenue, demand and data quality for ${tableLabel(table)} trips.`}
      />

      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={12} sm={6} lg={3}>
          <KpiCard
            label="Gross revenue"
            icon={PaidOutlinedIcon}
            value={moneyCompact(k.gross_revenue)}
            caption={`${moneyCompact(k.gross_revenue_ex_outliers)} excluding flagged trips`}
          />
        </Grid>
        <Grid item xs={12} sm={6} lg={3}>
          <KpiCard
            label="Trips"
            icon={LocalTaxiOutlinedIcon}
            value={num(k.trips)}
            caption={`Median trip ${minutes(k.median_duration_min)} · ${num(k.avg_distance_miles, 1)} mi avg`}
          />
        </Grid>
        <Grid item xs={12} sm={6} lg={3}>
          <KpiCard
            label="Median fare"
            icon={ReceiptLongOutlinedIcon}
            value={money(k.median_fare)}
            caption={`95th percentile ${money(k.p95_fare)}`}
          />
        </Grid>
        <Grid item xs={12} sm={6} lg={3}>
          <KpiCard
            label="Data quality"
            icon={VerifiedOutlinedIcon}
            value={pct(report?.pass_rate_pct)}
            caption={`${num(report?.rows_rejected)} of ${num(report?.rows_in)} rows rejected`}
          />
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid item xs={12}>
          <Panel
            title="Daily revenue"
            subtitle="Total fare revenue per day, with the trailing 7-day average"
            actions={
              <ChartLegend
                items={[
                  { label: "Daily revenue", color: chartColors.series[0] },
                  { label: "7-day average", color: chartColors.series[1] },
                  { label: "Anomaly (>3σ)", color: chartColors.critical, shape: "dot" },
                ]}
              />
            }
          >
            <RevenueChart daily={analytics?.daily} />
          </Panel>
        </Grid>

        <Grid item xs={12} lg={8}>
          <Panel title="Demand by hour" subtitle="Trips by pickup hour across the period">
            <HourlyChart hourly={analytics?.hourly} />
          </Panel>
        </Grid>

        <Grid item xs={12} lg={4}>
          <Panel title="Highlights">
            <Stack divider={<Divider flexItem />}>
              <Highlight
                label="Busiest pickup hour"
                value={hourRange(peak?.hour)}
                caption={peak ? `${num(peak.count)} trips` : undefined}
              />
              <Highlight
                label="Top borough by revenue"
                value={topBorough?.borough ?? "–"}
                caption={topBorough ? `${pct(topBorough.revenue_share_pct)} of revenue` : undefined}
              />
              <Highlight
                label="Card tip rate"
                value={pct(k.avg_card_tip_pct)}
                caption={`${pct(k.card_share_pct, 0)} of trips paid by card`}
              />
              <Highlight
                label="Unusual revenue days"
                value={num(anomalies)}
                caption="More than 3σ away from the previous week"
              />
            </Stack>
          </Panel>
        </Grid>
      </Grid>
    </>
  );
}
