import React from "react";
import { Box, Button, Card, CardContent, Chip, Grid, Stack, Typography } from "@mui/material";
import GitHubIcon from "@mui/icons-material/GitHub";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import PageHeader from "../components/PageHeader";
import Panel from "../components/Panel";
import { REPO_URL } from "../components/DemoNotice";

const doc = (path) => `${REPO_URL}/blob/main/${path}`;

const FACTS = [
  { value: "12", label: "TLC datasets, 2009–2016" },
  { value: "12", label: "documented data-quality rules" },
  { value: "100+", label: "automated tests, about 90% coverage" },
  { value: "2", label: "databases tested in CI: SQLite and PostgreSQL" },
];

// A real sequence: each step feeds the next.
const PIPELINE = [
  { step: "Extract", detail: "Google BigQuery, CSV extracts or a reproducible NumPy generator, behind one interface." },
  { step: "Validate", detail: "pandas and NumPy rules reject, fix or flag every row, with a recorded reason." },
  { step: "Enrich", detail: "Trips are joined to zone and payment reference data, with codes from different source systems harmonised." },
  { step: "Store & report", detail: "A relational model in PostgreSQL or SQLite, with SQL reports using CTEs and window functions." },
  { step: "Serve", detail: "A Django REST API feeds this React app and a Plotly Dash dashboard." },
];

const STACK = [
  { group: "Data", items: ["Python", "pandas", "NumPy", "Google BigQuery"] },
  { group: "SQL & storage", items: ["PostgreSQL", "SQLite", "Django ORM", "Window functions"] },
  { group: "Back end", items: ["Django REST Framework", "gunicorn", "Caching"] },
  { group: "Front end", items: ["React", "Material UI", "Chart.js"] },
  { group: "Dashboards", items: ["Plotly Dash", "Plotly"] },
  { group: "Delivery", items: ["pytest", "Jest", "ruff", "GitHub Actions", "Docker", "AWS ECS Fargate"] },
];

const DECISIONS = [
  {
    asked: "Show the minimum and maximum fare and journey time.",
    found: "Minimums and maximums came from data errors, such as a 23-hour trip with the meter left running.",
    did: "The headline figures are the median and 95th percentile, which one bad row cannot move.",
  },
  {
    asked: "Show the average tip.",
    found: "Cash tips are never recorded, so an average over all trips understates tipping.",
    did: "Report the tip rate on card trips only, and say why next to the number.",
  },
  {
    asked: "Delete the bad rows.",
    found: "Deleting hides problems. On the sample, flagged trips are about 4% of trips but nearly half of revenue.",
    did: "Every row is rejected, fixed or flagged with a reason, and revenue is shown with and without flagged trips.",
  },
];

const QUALITY = [
  "Closed an SQL injection hole in the original API by whitelisting table names.",
  "Cut the live BigQuery query from 9 full-table scans to 4, and cached the results.",
  "Moved secrets out of the code into environment variables and GitHub secrets.",
  "Every push runs the tests on SQLite and PostgreSQL, builds the Docker images and redeploys this site.",
];

export default function AboutView() {
  return (
    <>
      <PageHeader
        title="About this project"
        description="A revenue and data-quality analytics platform for New York City taxi trips, built end to end: data pipeline, SQL, API, web app and dashboards."
        actions={
          <Button variant="contained" href={REPO_URL} target="_blank" rel="noreferrer" startIcon={<GitHubIcon />}>
            Source code
          </Button>
        }
      />

      <Grid container spacing={2} sx={{ mb: 2 }}>
        {FACTS.map((f) => (
          <Grid item xs={6} lg={3} key={f.label}>
            <Card sx={{ height: "100%" }}>
              <CardContent>
                <Typography variant="h4" component="p">{f.value}</Typography>
                <Typography variant="body2" color="text.secondary">{f.label}</Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Grid container spacing={2}>
        <Grid item xs={12}>
          <Panel title="How the data flows" subtitle="Each step feeds the next. The same code runs locally, in CI and when this site is built.">
            <Box
              component="ol"
              sx={{
                listStyle: "none", m: 0, p: 0, display: "grid", gap: 1.5,
                gridTemplateColumns: { xs: "1fr", md: "repeat(5, 1fr)" },
              }}
            >
              {PIPELINE.map((p, i) => (
                <Box component="li" key={p.step} sx={{ position: "relative", p: 2, borderRadius: 2, bgcolor: "background.default", border: 1, borderColor: "divider" }}>
                  <Typography variant="overline" color="primary.main">Step {i + 1}</Typography>
                  <Typography sx={{ fontWeight: 650 }}>{p.step}</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>{p.detail}</Typography>
                  {i < PIPELINE.length - 1 && (
                    <ArrowForwardIcon
                      fontSize="small"
                      aria-hidden
                      sx={{ display: { xs: "none", md: "block" }, position: "absolute", right: -18, top: "50%", transform: "translateY(-50%)", color: "text.disabled", bgcolor: "background.paper", borderRadius: "50%", zIndex: 1 }}
                    />
                  )}
                </Box>
              ))}
            </Box>
          </Panel>
        </Grid>

        <Grid item xs={12}>
          <Panel title="Requirements I challenged" subtitle="Taken literally, each of these would have produced misleading numbers.">
            <Grid container spacing={2}>
              {DECISIONS.map((d) => (
                <Grid item xs={12} md={4} key={d.asked}>
                  <Stack spacing={1.25} sx={{ height: "100%", p: 2, borderRadius: 2, border: 1, borderColor: "divider" }}>
                    <Box>
                      <Typography variant="overline" color="text.secondary">Asked for</Typography>
                      <Typography sx={{ fontWeight: 600 }}>“{d.asked}”</Typography>
                    </Box>
                    <Box>
                      <Typography variant="overline" color="text.secondary">What the data showed</Typography>
                      <Typography variant="body2">{d.found}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="overline" color="text.secondary">What I did</Typography>
                      <Typography variant="body2">{d.did}</Typography>
                    </Box>
                  </Stack>
                </Grid>
              ))}
            </Grid>
          </Panel>
        </Grid>

        <Grid item xs={12} lg={7}>
          <Panel title="Built with">
            <Stack spacing={1.5}>
              {STACK.map((s) => (
                <Box key={s.group} sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "130px 1fr" }, gap: 1, alignItems: "center" }}>
                  <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 600 }}>{s.group}</Typography>
                  <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75 }}>
                    {s.items.map((item) => <Chip key={item} label={item} size="small" variant="outlined" />)}
                  </Box>
                </Box>
              ))}
            </Stack>
          </Panel>
        </Grid>

        <Grid item xs={12} lg={5}>
          <Panel title="Engineering quality">
            <Stack spacing={1.25} component="ul" sx={{ m: 0, p: 0, listStyle: "none" }}>
              {QUALITY.map((q) => (
                <Box component="li" key={q} sx={{ display: "flex", gap: 1 }}>
                  <CheckCircleOutlineIcon fontSize="small" color="success" sx={{ mt: 0.25 }} aria-hidden />
                  <Typography variant="body2">{q}</Typography>
                </Box>
              ))}
            </Stack>
          </Panel>
        </Grid>

        <Grid item xs={12}>
          <Panel title="Read more">
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
              <Button variant="outlined" color="secondary" href={doc("docs/REQUIREMENTS.md")} target="_blank" rel="noreferrer">Requirements log</Button>
              <Button variant="outlined" color="secondary" href={doc("docs/DATA_DICTIONARY.md")} target="_blank" rel="noreferrer">Data dictionary and quality rules</Button>
              <Button variant="outlined" color="secondary" href={doc("docs/AWS_DEPLOYMENT.md")} target="_blank" rel="noreferrer">AWS deployment runbook</Button>
              <Button variant="outlined" color="secondary" href={doc("README.md")} target="_blank" rel="noreferrer">README</Button>
            </Box>
          </Panel>
        </Grid>
      </Grid>
    </>
  );
}
