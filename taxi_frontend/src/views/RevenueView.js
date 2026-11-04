import React from "react";
import {
  Chip, Grid, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography,
} from "@mui/material";
import KpiCard from "../components/KpiCard";
import Panel from "../components/Panel";
import PageHeader from "../components/PageHeader";
import RevenueChart from "../components/charts/RevenueChart";
import DrawdownChart from "../components/charts/DrawdownChart";
import RankedBarChart from "../components/charts/RankedBarChart";
import ChartLegend from "../components/charts/Legend";
import { chartColors } from "../theme";
import { money, moneyCompact, num, pct, shortDate } from "../format";

const mean = (xs) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null);

export default function RevenueView({ analytics }) {
  const k = analytics?.kpis || {};
  const daily = analytics?.daily || [];
  const anomalies = daily.filter((d) => d.is_anomaly);
  const drawdowns = daily.map((d) => d.drawdown_pct).filter((v) => v != null);
  const maxDrawdown = drawdowns.length ? Math.min(...drawdowns) : null;
  const vols = daily.map((d) => d.volatility).filter((v) => v != null);

  return (
    <>
      <PageHeader
        title="Revenue"
        description="Daily revenue is monitored like a P&L: trend, day-to-day volatility, drawdown from peak and statistically unusual days."
      />

      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={6} lg={3}>
          <KpiCard label="Avg daily revenue" value={money(mean(daily.map((d) => d.revenue)), 0)} caption={`over ${num(daily.length)} days`} />
        </Grid>
        <Grid item xs={6} lg={3}>
          <KpiCard label="Excl. flagged trips" value={moneyCompact(k.gross_revenue_ex_outliers)} caption={`of ${moneyCompact(k.gross_revenue)} gross`} />
        </Grid>
        <Grid item xs={6} lg={3}>
          <KpiCard label="Daily volatility" value={pct(mean(vols))} caption="Average 7-day std dev of daily change" />
        </Grid>
        <Grid item xs={6} lg={3}>
          <KpiCard label="Max drawdown" value={pct(maxDrawdown)} caption="Deepest fall of the 7-day average" />
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid item xs={12}>
          <Panel
            title="Daily revenue"
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
            <RevenueChart daily={daily} height={320} />
          </Panel>
        </Grid>

        <Grid item xs={12}>
          <Panel title="Drawdown" subtitle="How far the 7-day average sits below its highest point so far">
            <DrawdownChart daily={daily} />
          </Panel>
        </Grid>

        <Grid item xs={12} lg={7}>
          <Panel title="Revenue by pickup borough" contentSx={{ px: 0 }}>
            <TableContainer>
              <Table size="small" aria-label="Revenue by borough">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ pl: 2.5 }}>Rank</TableCell>
                    <TableCell>Borough</TableCell>
                    <TableCell align="right">Trips</TableCell>
                    <TableCell align="right">Revenue</TableCell>
                    <TableCell align="right">Avg fare</TableCell>
                    <TableCell align="right" sx={{ pr: 2.5 }}>Share</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {(analytics?.boroughs || []).map((b) => (
                    <TableRow key={b.borough} hover>
                      <TableCell sx={{ pl: 2.5, color: "text.secondary" }}>{b.revenue_rank}</TableCell>
                      <TableCell sx={{ fontWeight: 600 }}>{b.borough}</TableCell>
                      <TableCell align="right">{num(b.trips)}</TableCell>
                      <TableCell align="right">{money(b.revenue, 0)}</TableCell>
                      <TableCell align="right">{money(b.avg_fare)}</TableCell>
                      <TableCell align="right" sx={{ pr: 2.5 }}>{pct(b.revenue_share_pct)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Panel>
        </Grid>

        <Grid item xs={12} lg={5}>
          <Panel title="Trips by payment type">
            <RankedBarChart
              rows={analytics?.payment_mix}
              label="payment_type"
              value="trips"
              format={(v) => num(v)}
              ariaLabel="Ranked bar chart of trips by payment type"
            />
          </Panel>
        </Grid>

        <Grid item xs={12}>
          <Panel
            title="Unusual revenue days"
            subtitle="Days more than 3 standard deviations from the previous 7 days. Check these before quoting period totals."
            contentSx={{ px: 0 }}
          >
            {anomalies.length === 0 ? (
              <Typography color="text.secondary" sx={{ px: 2.5 }}>No unusual days in this period.</Typography>
            ) : (
              <TableContainer>
                <Table size="small" aria-label="Anomalous revenue days">
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ pl: 2.5 }}>Date</TableCell>
                      <TableCell align="right">Revenue</TableCell>
                      <TableCell align="right">7-day average</TableCell>
                      <TableCell align="right">Change vs prior day</TableCell>
                      <TableCell sx={{ pr: 2.5 }}>Direction</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {anomalies.map((d) => (
                      <TableRow key={d.date} hover>
                        <TableCell sx={{ pl: 2.5, fontWeight: 600 }}>{shortDate(d.date)}</TableCell>
                        <TableCell align="right">{money(d.revenue, 0)}</TableCell>
                        <TableCell align="right">{money(d.rolling_mean, 0)}</TableCell>
                        <TableCell align="right">{pct(d.pct_change)}</TableCell>
                        <TableCell sx={{ pr: 2.5 }}>
                          <Chip
                            size="small"
                            variant="outlined"
                            label={d.revenue >= d.rolling_mean ? "▲ Spike" : "▼ Dip"}
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Panel>
        </Grid>
      </Grid>
    </>
  );
}
