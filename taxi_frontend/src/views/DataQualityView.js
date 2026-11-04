import React from "react";
import {
  Box, Chip, Grid, LinearProgress, Stack, Table, TableBody, TableCell, TableContainer, TableHead,
  TableRow, Tooltip, Typography,
} from "@mui/material";
import BlockOutlinedIcon from "@mui/icons-material/BlockOutlined";
import BuildOutlinedIcon from "@mui/icons-material/BuildOutlined";
import FlagOutlinedIcon from "@mui/icons-material/FlagOutlined";
import Panel from "../components/Panel";
import PageHeader from "../components/PageHeader";
import KpiCard from "../components/KpiCard";
import { dateTime, num, pct } from "../format";

// Action is shown as icon + word, never colour alone.
const ACTIONS = {
  reject: { label: "Reject", icon: <BlockOutlinedIcon />, color: "error", help: "Row removed: cannot be used for financial figures" },
  fix: { label: "Fix", icon: <BuildOutlinedIcon />, color: "default", help: "Value repaired in a documented way; row kept" },
  flag: { label: "Flag", icon: <FlagOutlinedIcon />, color: "warning", help: "Row kept but marked for review" },
};

const humanise = (rule) =>
  rule.replace(/_/g, " ").replace(/\bnyc\b/g, "NYC").replace(/^\w/, (c) => c.toUpperCase());

export default function DataQualityView({ quality, runs = [] }) {
  const report = quality?.quality_report || {};
  const rules = report.rules || [];
  const total = (action) => rules.filter((r) => r.action === action).reduce((s, r) => s + r.rows_affected, 0);
  const completeness = Object.entries(report.completeness_pct || {}).sort((a, b) => a[1] - b[1]);

  return (
    <>
      <PageHeader
        title="Data quality"
        description="Every load is checked against documented business rules. Rows are rejected, fixed or flagged, never silently dropped, and every count reconciles."
      />

      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={6} lg={3}>
          <KpiCard label="Pass rate" value={pct(report.pass_rate_pct)} caption={`${num(report.rows_clean)} of ${num(report.rows_in)} rows loaded`} />
        </Grid>
        <Grid item xs={6} lg={3}>
          <KpiCard label="Rejected" value={num(report.rows_rejected)} caption="Unusable for financial reporting" />
        </Grid>
        <Grid item xs={6} lg={3}>
          <KpiCard label="Fixed" value={num(total("fix"))} caption="Repaired, row kept" />
        </Grid>
        <Grid item xs={6} lg={3}>
          <KpiCard label="Flagged" value={num(total("flag"))} caption="Kept, marked as outliers" />
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid item xs={12}>
          <Panel
            title="Rule results"
            subtitle={quality ? `Load #${quality.id} · ${quality.source} · ${dateTime(quality.finished_at)}` : undefined}
            contentSx={{ px: 0 }}
          >
            <TableContainer>
              <Table size="small" aria-label="Data quality rules">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ pl: 2.5 }}>Rule</TableCell>
                    <TableCell>Action</TableCell>
                    <TableCell align="right">Rows</TableCell>
                    <TableCell align="right">% of input</TableCell>
                    <TableCell sx={{ pr: 2.5, display: { xs: "none", md: "table-cell" } }}>Description</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {rules.map((r) => {
                    const a = ACTIONS[r.action] || ACTIONS.fix;
                    return (
                      <TableRow key={r.rule} hover sx={{ opacity: r.rows_affected ? 1 : 0.55 }}>
                        <TableCell sx={{ pl: 2.5, fontWeight: 600 }}>{humanise(r.rule)}</TableCell>
                        <TableCell>
                          <Tooltip title={a.help}>
                            <Chip size="small" variant="outlined" color={a.color} icon={a.icon} label={a.label} />
                          </Tooltip>
                        </TableCell>
                        <TableCell align="right">{num(r.rows_affected)}</TableCell>
                        <TableCell align="right">{pct(r.pct_of_input, 2)}</TableCell>
                        <TableCell sx={{ pr: 2.5, color: "text.secondary", display: { xs: "none", md: "table-cell" } }}>
                          {r.description}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </TableContainer>
          </Panel>
        </Grid>

        <Grid item xs={12} lg={5}>
          <Panel title="Field completeness" subtitle="Share of raw rows with a value, before cleaning">
            <Stack spacing={1.5}>
              {completeness.map(([field, value]) => (
                <Box key={field}>
                  <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
                    <Typography variant="body2">{humanise(field)}</Typography>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>{pct(value)}</Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={value}
                    aria-label={`${field} completeness`}
                    sx={{ height: 6, borderRadius: 3, bgcolor: "#eef0f3" }}
                  />
                </Box>
              ))}
            </Stack>
          </Panel>
        </Grid>

        <Grid item xs={12} lg={7}>
          <Panel title="Load history" subtitle="Audit trail of ingestion runs for this dataset" contentSx={{ px: 0 }}>
            <TableContainer>
              <Table size="small" aria-label="Ingestion runs">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ pl: 2.5 }}>Run</TableCell>
                    <TableCell>Finished</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell align="right">Loaded</TableCell>
                    <TableCell align="right" sx={{ pr: 2.5 }}>Rejected</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {runs.slice(0, 8).map((run) => (
                    <TableRow key={run.id} hover>
                      <TableCell sx={{ pl: 2.5 }}>#{run.id} · {run.source}</TableCell>
                      <TableCell>{dateTime(run.finished_at)}</TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          variant="outlined"
                          color={run.status === "success" ? "success" : run.status === "failed" ? "error" : "default"}
                          label={run.status === "success" ? "✓ Success" : run.status === "failed" ? "✕ Failed" : "Running"}
                        />
                      </TableCell>
                      <TableCell align="right">{num(run.rows_loaded)}</TableCell>
                      <TableCell align="right" sx={{ pr: 2.5 }}>{num(run.rows_rejected)}</TableCell>
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
