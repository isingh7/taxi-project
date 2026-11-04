import React from "react";
import {
  Box, Grid, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography,
} from "@mui/material";
import Panel from "../components/Panel";
import PageHeader from "../components/PageHeader";
import KpiCard from "../components/KpiCard";
import HourlyChart from "../components/charts/HourlyChart";
import FareHistogram from "../components/charts/FareHistogram";
import DemandHeatmap from "../components/charts/DemandHeatmap";
import ChartLegend from "../components/charts/Legend";
import LocationMap from "../components/LocationMap";
import { chartColors } from "../theme";
import { hourRange, minutes, money, num } from "../format";

export default function OperationsView({ headline, analytics }) {
  const k = analytics?.kpis || {};
  const pickup = headline?.most_popular_pickup_location;
  const dropoff = headline?.most_popular_dropoff_location;
  const peak = headline?.most_popular_time_of_day;

  return (
    <>
      <PageHeader
        title="Demand & locations"
        description="When and where trips happen, how long they take and what they cost."
      />

      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={6} lg={3}>
          <KpiCard label="Busiest hour" value={hourRange(peak?.hour)} caption={peak ? `${num(peak.count)} trips` : undefined} />
        </Grid>
        <Grid item xs={6} lg={3}>
          <KpiCard label="Median trip" value={minutes(k.median_duration_min)} caption={`90th percentile ${minutes(k.p90_duration_min)}`} />
        </Grid>
        <Grid item xs={6} lg={3}>
          <KpiCard label="Average distance" value={`${num(k.avg_distance_miles, 1)} mi`} caption={`Avg journey ${minutes(headline?.avg_journey_time)}`} />
        </Grid>
        <Grid item xs={6} lg={3}>
          <KpiCard label="Average tip" value={money(headline?.avg_tip_amount)} caption="Where a tip was recorded" />
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid item xs={12}>
          <Panel
            title="Demand by weekday and hour"
            subtitle="Trips by pickup time. Darker cells are busier; hover a cell for the count."
          >
            <DemandHeatmap grid={analytics?.weekday_hour} />
          </Panel>
        </Grid>
        <Grid item xs={12} lg={6}>
          <Panel title="Trips by pickup hour">
            <HourlyChart hourly={analytics?.hourly} height={280} />
          </Panel>
        </Grid>
        <Grid item xs={12} lg={6}>
          <Panel
            title="Fare distribution"
            subtitle={`Unflagged trips; the top 1% above ${money(analytics?.fare_distribution?.clipped_above, 0)} is not shown`}
          >
            <FareHistogram dist={analytics?.fare_distribution} height={280} />
          </Panel>
        </Grid>

        <Grid item xs={12} lg={7}>
          <Panel
            title="Top pickup & drop-off spots"
            contentSx={{ display: "flex", flexDirection: "column" }}
            actions={
              <ChartLegend
                items={[
                  { label: `Pickup · ${num(pickup?.count)} trips`, color: chartColors.series[0], shape: "dot" },
                  { label: `Drop-off · ${num(dropoff?.count)} trips`, color: chartColors.series[1], shape: "dot" },
                ]}
              />
            }
          >
            <LocationMap pickup={pickup} dropoff={dropoff} />
          </Panel>
        </Grid>

        <Grid item xs={12} lg={5}>
          <Panel title="Busiest routes" subtitle="Zone to zone, by number of trips" contentSx={{ px: 0 }}>
            <TableContainer>
              <Table size="small" aria-label="Busiest routes">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ pl: 2.5 }}>Route</TableCell>
                    <TableCell align="right">Trips</TableCell>
                    <TableCell align="right">Avg fare</TableCell>
                    <TableCell align="right" sx={{ pr: 2.5 }}>Avg time</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {(analytics?.top_routes || []).slice(0, 8).map((r) => (
                    <TableRow key={`${r.pickup_zone}-${r.dropoff_zone}`} hover>
                      <TableCell sx={{ pl: 2.5 }}>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>{r.pickup_zone}</Typography>
                        <Box component="span" sx={{ color: "text.secondary", fontSize: "0.8rem" }}>→ {r.dropoff_zone}</Box>
                      </TableCell>
                      <TableCell align="right">{num(r.trips)}</TableCell>
                      <TableCell align="right">{money(r.avg_total)}</TableCell>
                      <TableCell align="right" sx={{ pr: 2.5 }}>{minutes(r.avg_minutes, 0)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Panel>
        </Grid>
      </Grid>
    </>
  );
}
