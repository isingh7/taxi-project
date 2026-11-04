# Requirements log

This log records what each user group needs, how each requirement was tested
against the data, and where a requirement was **challenged** because taking it
literally would have given misleading numbers.

> The stakeholders below are **personas** for the two main audiences. They are
> not records of real meetings. The challenges, though, come from what the
> data showed during development, and each one points to the code or test
> that settles it.

## Users

| Persona | Needs | Main question |
|---|---|---|
| **Finance analyst** | Revenue reporting, reconciliation, export to Excel | "What did we earn, and can I trust the number?" |
| **Operations manager** | Demand by hour and borough, busiest routes | "Where and when should drivers be?" |
| **Data owner** | Lineage, rejected-row counts, reasons | "What happened to the rows we didn't use?" |

## Requirements and acceptance criteria

| ID | Requirement | Acceptance criteria | Where |
|---|---|---|---|
| R1 | Headline stats per dataset (journey time, fare, tip, busiest hour, top locations) | Same JSON contract as v1; works without GCP credentials | `GET /api/data/<table>/`, `test_api.py` |
| R2 | Daily revenue with trend | 7-day average; days with no trips show as 0, not skipped | `analytics.daily_revenue`, `test_daily_revenue_fills_missing_days_with_zero` |
| R3 | Bad data must not distort financial figures | Each rule is *reject*, *fix* or *flag*; counts reconcile (in = clean + rejected + duplicates) | `services/quality.py`, `test_report_totals_reconcile` |
| R4 | Revenue by borough, ranked, with share of total | Shares sum to 100%; totals reconcile with the ORM to within $1 | `BOROUGH_LEAGUE_SQL`, `test_borough_league_table_reconciles_with_orm` |
| R5 | Finance can take the numbers into Excel | CSV download of the daily series | `GET /api/analytics/<table>/daily.csv` |
| R6 | Alert on unusual revenue days | Day flagged when revenue is more than 3σ from the *previous* 7 days | `test_daily_revenue_flags_anomalous_day` |
| R7 | Every load is auditable | Each run stores source, row counts, DQ report, status and error | `IngestionRun`, `/api/ingestion-runs/` |
| R8 | Payment data from different source systems is comparable | `CSH`/`CRD`/`Cash`/`1`/`1.0` all map to one code set | `test_payment_codes_from_different_source_systems_are_harmonised` |

## Challenged requirements

### C1. "Show the minimum and maximum journey time and fare"
**What the data showed:** min and max come from data errors, not real trips:
dropoffs before pickups, $0.01 fares, 23-hour "trips" where the meter was
left running. One bad row moves the number, so it can't be compared month to month.
**Outcome:** kept in the v1 endpoint for backward compatibility. The
new insights panel and dashboard lead with **median and p95**, which one bad row can't move.

### C2. "A trip is valid if it lasts under 24 hours"
**Challenge:** the original filter allowed trips of up to 24 hours. A real NYC
taxi trip of more than 4 hours is almost always a meter left running.
**Outcome:** the limit is now 4 hours (`MAX_TRIP_SECONDS`), kept in one constant so the
business can change it. **To confirm with operations.**

### C3. "Show the average tip"
**Challenge:** cash tips are not recorded in TLC data, so they show as $0.
Averaging all trips mixes "no tip" with "tip not recorded" and understates tipping.
**Outcome:** the new metric is **card tip rate** (tip ÷ fare on card trips only).
The original "average tip where tip > 0" stays for v1.

### C4. "Just delete the bad rows"
**Challenge:** deleting hides the problem and can't be audited. Some defects can be
repaired (a 0,0 GPS fix still has a valid fare). Others are real but unusual,
and finance must decide on them, not an engineer.
**Outcome:** three actions:
* **reject**: can't be used for money figures (negative fare, dropoff before pickup)
* **fix**: repaired in a documented way (bad coordinates set to null, trip kept)
* **flag**: kept but marked (`is_outlier`, robust z-score on log fare-per-mile)

Revenue is shown **both with and without flagged trips**. On the synthetic
`tlc_green_trips_2014` sample, flagged trips are about 4% of rows but about
half of gross revenue ($370.6k vs $188.8k). That is exactly the kind of gap
finance needs to see before quoting a number.

### C5. "Average fare" as the headline
**Challenge:** fares are right-skewed. On the synthetic `tlc_yellow_trips_2015` sample, mean is $23.80 and median is $9.84.
**Outcome:** median is the headline KPI; the mean is still in the API.

### C6. "Query BigQuery live every time"
**Challenge:** the v1 endpoint ran 9 full-table scans per page view. That is slow
(seconds) and billed per scan, for historical data that never changes.
**Outcome:** 4 queries instead of 9, results cached for 24h, and a local Postgres/SQLite
store loaded by a scheduled ETL. `?source=auto` falls back to the store if
BigQuery is down.

## Open questions

1. Should the 3σ anomaly threshold differ by weekday? (Weekend revenue is more volatile.)
2. Who signs off flagged outliers: finance or operations?
3. The zone boundaries are approximate bounding boxes. Is borough-level accuracy
   enough, or do we need the official TLC taxi-zone shapefile (263 zones)?
4. Retention: how many years of trip-level data should the local store keep?
