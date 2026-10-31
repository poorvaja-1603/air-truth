# AirTruth Mumbai: Reconciling Ground-Station Air Quality with Weather and Model Data

Status: PROPOSAL, awaiting approval. No code has been written.

## REVISION 1 (31 Oct 2026, after your answers). This block overrides anything below that conflicts.

1. **CA1 storage is AWS S3, not GCS.** You have AWS credits, and the CA1 brief allows S3. Use bucket layout `s3://<bucket>/processed_data/year=YYYY/month=MM/` (matches the brief's example) plus `raw_data/`. Use a least-privilege IAM user, never root keys, and set a budget alert. Everywhere below that says GCS in a CA1 context now means S3.
2. **CA1 is cut to the CA1 PDF only, because of the 2-day window.** In scope: one API source (OpenAQ), about 5 Mumbai stations, 30 days hourly, `requests` with retry and status checks, Pandas cleaning (imputation, explicit casting, filtering, one business rule: the 24-hour exceedance flag), Parquet to S3, terminal log, S3 console screenshot with timestamp, 3 to 5 page report, demo video. **Out of scope for CA1:** Open-Meteo, model air quality, station quality score, weather joins, anything microproject. Those return in Phase 2.
3. **CA1 two-day schedule.** Day 1: OpenAQ key, AWS bucket and IAM, extraction with retry, Pandas transform. Day 2: validation, S3 upload, full run and screenshot, report, video.
4. **Airbyte runs locally with `abctl` in normal mode** (16 GB RAM, 20 cores is enough, and normal mode keeps the Connector Builder). Airbyte Cloud trial is the fallback.
5. **LLM for the BI layer: Gemini.** Confirm the current free-tier model id in AI Studio at M15.
6. **Open item: the warehouse.** BigQuery needs a billing-enabled Google Cloud project. If that is not possible, the fallback is Snowflake (its trial terms are unverified). Decision pending your answer.
Prepared: Saturday 31 October 2026. Microproject demo and submission: 16 and 17 November 2026.

Evidence tags used throughout:

| Tag | Meaning |
|---|---|
| [V] | Verified from documentation or search results found on 31 Oct 2026. No live API call was made, because no API keys exist yet. |
| [A] | Reasonable technical assumption, not checked against a source. |
| [U] | Unverified. Must be confirmed at the named milestone before we depend on it. |
| [M] | Needs manual implementation. No ready-made connector or feature. |

---

## REVISION 2 (31 Oct 2026, professor's guidance: multiple sources, different acquisition methods). Overrides Revision 1 item 2 where they conflict.

CA1 now has two sources acquired by different methods:

| Source | Method | Grain | Role |
|---|---|---|---|
| OpenAQ v3 | Authenticated REST API (key header, pagination, rate limit, JSON) | Hourly, last 30 days, about 5 stations | Recent readings |
| Mendeley Data, "Daily Air Quality Index and Pollutant Concentrations for Mumbai" (DOI 10.17632/9dcb8jmbts.1) | File download (CSV, file format to be confirmed on download) [U] | Daily, June 2019 to January 2026, 5 MPCB stations (Kurla, Bandra, BKC, Sion, airport) | Historical baseline. Licence CC BY 4.0 [V] https://data.mendeley.com/datasets/9dcb8jmbts/1 |

Caveat to state in the report: the CSV was itself built from OpenAQ hourly data, so the sources are different in method, not fully independent in origin.

CA1 transformation additions: aggregate API hourly to daily (18 of 24 hours rule), map station names between the two sources with a small lookup table [M], conform both to one daily schema with a `source` column, then write one daily Parquet partitioned by year and month. Optional if time allows: pull a January 2026 window from the API and compare with the CSV daily values as a reconciliation check.

Optional third source (stretch only): SAFAR station list scraped as HTML. Not checked for robots or terms [U]. Skipped unless Day 1 finishes early.

---

## 1. Project title

**AirTruth Mumbai: a multi-source data pipeline that compares Mumbai's ground-station air quality with weather conditions and model-based air quality estimates.**

## 2. Abstract

Mumbai has dozens of air quality monitors, but their data is patchy: sensors go offline, flatline, or report implausible spikes. Separately, global models (CAMS, exposed through Open-Meteo) estimate air quality everywhere, and reanalysis weather explains why pollution rises or falls. Nobody combines these into one trustworthy, queryable view.

AirTruth Mumbai ingests hourly ground-station readings (OpenAQ), historical weather (Open-Meteo), and modelled air quality (Open-Meteo Air Quality API), cleans and harmonises them, and answers four questions: how reliable is each station, how far does the model drift from ground truth, which weather conditions precede PM2.5 spikes, and which stations and hours breach the national 24-hour standard most often.

It is built in two phases on one domain. **CA1** is a Python and Pandas pipeline that writes partitioned Parquet to Google Cloud Storage. **Microproject** re-implements the same logic on an enterprise-style stack: Airbyte, BigQuery, dbt, Airflow, and a conversational BI interface.

## 3. Problem statement

Raw air quality data from public sources is not decision-ready. Station feeds have gaps, duplicate timestamps, unit differences, UTC versus IST confusion, and impossible values. Model data is on a coarse grid and has no notion of station reliability. Weather lives in a separate system. A person asking "was Sion really that bad last Tuesday, and was it the weather?" has to manually fetch, clean, and join three sources.

**Problem:** there is no automated, tested pipeline that turns these three feeds into a single trustworthy dataset with data-quality scoring and a way to query it in plain English.

## 4. Motivation and real-world relevance

- Air pollution is a genuine daily concern in Mumbai, with a visible post-monsoon and winter rise. Residents, schools, and local bodies need station-level evidence, not a single city number.
- The reconciliation problem (point sensors versus grid models) is real in environmental data engineering, and the same pattern applies to any sensor-versus-model setting.
- It exercises the core data engineering skills the course targets: API extraction with rate limits, late-arriving data, schema harmonisation, timezone handling, data quality testing, orchestration, warehouse modelling, and serving data to a non-technical user.

## 5. Objectives

1. Build a CA1 pipeline: API extraction with retry, Pandas cleaning, Parquet storage in cloud object storage, verified end to end.
2. Build a microproject pipeline: Airbyte ingestion, BigQuery warehouse, dbt staging and marts with tests, Airflow orchestration, conversational BI.
3. Keep one domain, one set of schemas, and one set of business rules across both phases.
4. Produce explainable code and documentation so each member can defend every decision in a viva.

## 6. Research methodology

1. Read both requirement documents and extracted every mandatory item (summarised in Appendix A).
2. Shortlisted six candidate ideas across urban, environmental, agricultural, energy, hazard, and financial domains.
3. For each serious candidate, searched official documentation for endpoint, authentication, rate limits, history, and connector availability.
4. Separated verified facts [V] from assumptions [A], unknowns [U], and manual work [M].
5. Scored candidates on the eleven required criteria, then chose on balance rather than ease.
6. Checked free-tier and student accessibility for every cloud tool, because a demo that depends on a locked feature is a failed demo.

Limitation: research was documentation-based. Live endpoint behaviour (for example, how many Mumbai stations actually have recent data on OpenAQ) is confirmed at milestone M1.

## 7. Candidate comparison

Scores are my judgement, 1 (weak) to 5 (strong), out of 55.

| Criterion | A. AirTruth Mumbai | B. Mandi Monsoon | C. Rain x Tide Flood Risk | D. Rooftop Solar Yield | E. Quake Watch | F. Stock Dashboard |
|---|---|---|---|---|---|---|
| Problem usefulness | 4 | 4 | 4 | 3 | 3 | 2 |
| Uniqueness | 4 | 5 | 5 | 3 | 2 | 1 |
| Data source availability | 4 | 2 | 4 | 4 [U] | 4 [U] | 4 |
| Number of useful sources | 3 | 2 | 2 | 2 | 2 | 2 |
| Data quality | 3 | 3 | 2 | 3 | 4 | 3 |
| Data engineering relevance | 5 | 4 | 3 | 3 | 3 | 3 |
| Pipeline complexity (right-sized) | 4 | 3 | 2 | 3 | 3 | 2 |
| Tool compatibility | 5 | 2 | 3 | 3 | 3 | 4 |
| CA1 feasibility | 5 | 3 | 4 | 4 | 4 | 4 |
| Microproject extensibility | 5 | 3 | 3 | 3 | 3 | 3 |
| Demo potential | 5 | 3 | 3 | 3 | 4 | 3 |
| **Total** | **47** | 34 | 35 | 34 | 35 | 31 |

### Strengths and limitations

**A. AirTruth Mumbai (selected).** Strengths: OpenAQ has an Airbyte source connector [V], Open-Meteo needs no key [V], hourly data supports real incremental loading, and the reconciliation and station-reliability angle is distinctive. Limitations: station coverage and recency in OpenAQ must be confirmed [U]; no Open-Meteo connector was found in Airbyte's catalogue, so it needs the Connector Builder [M].

**B. Mandi Monsoon (crop prices versus rainfall).** Strengths: very original, genuine farmer-relevance. Limitations: data.gov.in requires a free key [V], the dataset page itself states that an API does not exist for that resource [V], the feed is "current daily" so history must be accumulated over time, and no ready Airbyte connector was found. Too fragile for a fixed demo date.

**C. Rain x Tide flood risk.** Strengths: very Mumbai, very distinctive. Limitations: the marine sea-level variable comes from a 0.5 degree ocean reanalysis grid for history and is labelled unsuitable for coastal navigation [V]. There is no flood ground truth to validate against, both feeds come from one provider, and the monsoon has ended so there is nothing live to demo.

**D. Rooftop solar yield.** Reasonable and useful, but it is a model-only pipeline with no ground truth and little data quality story. NASA POWER details were not verified [U].

**E. Quake watch.** Clean data, but generic and widely done. USGS feed details were not verified in this session [U].

**F. Stock or crypto dashboard.** The generic baseline the brief warns against. Included only to show what we are avoiding.

## 8. Final selection and justification

**Selected: A, AirTruth Mumbai.**

Why it wins:

1. **Genuine problem.** Station reliability and model-versus-ground disagreement are real questions, not toy charts.
2. **Distinctive.** The central artefact is a reconciliation and data-quality layer, not another AQI dashboard.
3. **Best tool fit.** It is the only candidate where a source connector in Airbyte's catalogue is directly verified (OpenAQ) [V], so the microproject requirement is met with a real connector rather than a workaround for every source.
4. **Right size.** Three feeds, about eight stations, 90 days of hourly data. This is roughly tens of thousands of rows, well inside every free tier, but rich enough for incremental loads, late-arriving data, and joins.
5. **Natural two-phase fit.** Cleaning rules written in Pandas translate cleanly into dbt SQL and tests.

It is not the easiest option. Candidates C and D would be easier to start. A was chosen because it scores highest on depth and verified tooling at the same time.

## 9. Data source research

### 9.1 OpenAQ API v3: ground-station measurements

| Item | Detail |
|---|---|
| Provider | OpenAQ (non-profit aggregator of government and research monitors) |
| Docs | https://docs.openaq.org/ |
| Base URL | https://api.openaq.org/v3 [V] (path seen in docs example `/v3/locations/2178`) |
| Format | JSON |
| Auth | Free API key, header `X-API-Key`, register at https://explore.openaq.org/register [V] (https://docs.openaq.org/using-the-api/api-key) |
| Rate limit | 60 requests per minute and 2,000 per hour per key [V] (https://docs.openaq.org/using-the-api/rate-limits) |
| Throttling signal | HTTP 429 when exceeded; headers `x-ratelimit-used`, `x-ratelimit-limit`, `x-ratelimit-remaining`, `x-ratelimit-reset` [V] |
| Pagination | `limit` and `page` parameters, limit up to 1000 per page [V] (OpenAQ R client docs) |
| Pollutants | PM2.5, PM10, NO2, SO2, CO, O3 and others [V] |
| Mumbai coverage | A published dataset derived from OpenAQ hourly data covers five MPCB stations (Kurla, Bandra, Bandra Kurla Complex, Sion, Chhatrapati Shivaji airport) [V] (https://data.mendeley.com/datasets/9dcb8jmbts/1). Current recency and sensor ids must be confirmed. [U] at M1 |
| Endpoints we expect to use | `/locations` (stations and coordinates), `/locations/{id}` (sensors), `/sensors/{id}/measurements` (readings) [U] confirm exact paths and parameters at M1 |
| Airbyte connector | OpenAQ source exists, support level Marketplace, streams include Locations, Sensors, Measurements [V] (https://docs.airbyte.com/integrations/sources/openaq) |
| Known risk | Stations go offline, so readings can go stale [V] |

### 9.2 Open-Meteo Historical Weather API: ERA5 reanalysis

| Item | Detail |
|---|---|
| Provider | Open-Meteo |
| Docs | https://open-meteo.com/ |
| Endpoint | `https://archive-api.open-meteo.com/v1/archive` [U] confirm at M1 |
| Auth | None for non-commercial use [V] |
| Licence | CC BY 4.0, attribution required; free for non-commercial use [V] (https://github.com/open-meteo/open-meteo) |
| Free limits | Quoted as 600 per minute, 5,000 per hour, 10,000 per day, 300,000 per month by a third-party summary of the pricing page [V, secondary]. Check https://open-meteo.com/en/pricing at M1 |
| Variables we expect to use | temperature_2m, relative_humidity_2m, precipitation, wind_speed_10m, wind_direction_10m, surface_pressure [U] |
| History | Back to 1940 per third-party sources [V, secondary] |
| Latency | Reanalysis typically lags by several days [A]. We end the analysis window at today minus 7 days to avoid half-filled recent days |
| Airbyte connector | None found for Open-Meteo in the Airbyte catalogue searches. Use Connector Builder [M] |

### 9.3 Open-Meteo Air Quality API: CAMS model estimates

| Item | Detail |
|---|---|
| Endpoint | `https://air-quality-api.open-meteo.com/v1/air-quality` [V] (seen in a public example with `hourly=pm2_5,pm10,us_aqi`) |
| Auth and limits | Same family and terms as 9.2 [V] |
| Variables | pm2_5, pm10, us_aqi confirmed [V]; nitrogen_dioxide and ozone expected [U] |
| Resolution | Global model grid, roughly tens of kilometres [A]. This is why the model cannot resolve individual stations and why the comparison is interesting |
| Date range parameters | `start_date` and `end_date` or `past_days` [U] confirm limits at M1 |

### 9.4 Reference data

- Pollutant thresholds (CPCB NAAQS 24-hour limits: PM2.5 60, PM10 100 ug/m3) [A, from general knowledge]. Confirm against the CPCB source at M2 and store as `reference/pollutant_thresholds.csv`, used by both phases.
- SAFAR Mumbai network, for cross-checking station locations: https://safar.tropmet.res.in/monitoring%20system-10-3-Details [V]. Lists stations including Chembur, Bhandup, Bandra Kurla Complex, Colaba, and Andheri.

### 9.5 Sources considered and rejected

- data.gov.in mandi prices: https://data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi [V]. Rejected for reliability, see candidate B.

## 10. Dataset schema and field descriptions

### 10.1 Canonical schemas used in both phases

**dim_station**

| Field | Type | Description |
|---|---|---|
| station_id | INT64 | OpenAQ location id |
| station_name | STRING | Human-readable station name |
| latitude, longitude | FLOAT64 | Station coordinates (also used to query Open-Meteo) |
| provider | STRING | Operator, for example MPCB |

**fct_station_reading_hourly** (ground truth, one row per sensor per hour)

| Field | Type | Description |
|---|---|---|
| station_id | INT64 | FK to dim_station |
| sensor_id | INT64 | OpenAQ sensor id |
| parameter | STRING | pm25, pm10, no2 |
| observed_at_utc | TIMESTAMP | Hour start in UTC |
| observed_at_ist | TIMESTAMP | Same instant in Asia/Kolkata |
| value_ugm3 | FLOAT64 | Concentration in ug/m3 |
| is_imputed | BOOL | True if filled by the short-gap rule |
| exceeds_24h_standard | BOOL | Set on daily aggregates, see 17 |

**fct_weather_hourly**

| Field | Type | Description |
|---|---|---|
| station_id | INT64 | Weather requested at the station's coordinates |
| observed_at_utc | TIMESTAMP | Hour |
| temperature_c, relative_humidity_pct, precipitation_mm, wind_speed_kmh, wind_direction_deg, surface_pressure_hpa | FLOAT64 | ERA5 reanalysis values |

**fct_model_air_quality_hourly**

| Field | Type | Description |
|---|---|---|
| station_id | INT64 | Model queried at the station's coordinates |
| observed_at_utc | TIMESTAMP | Hour |
| pm25_model_ugm3, pm10_model_ugm3 | FLOAT64 | CAMS estimates |

Exact raw field names depend on the live API responses and are finalised at M2 [U]. The canonical names above are the contract both phases must produce.

## 11. Data availability and access requirements

| Requirement | Detail | Cost |
|---|---|---|
| OpenAQ API key | Free registration | Free [V] |
| Open-Meteo | No key | Free, non-commercial, attribution [V] |
| Google Cloud project | Needed for GCS and BigQuery. The $300, 90-day free trial requires a card; the Free Tier includes 5 GB-months of US regional Cloud Storage and 1 TiB queries plus 10 GiB BigQuery storage per month [V] (https://cloud.google.com/free) | Free within limits |
| Airbyte | Local via `abctl` (Docker, about 4 CPU and 8 GB RAM, or 2 CPU and 8 GB in low-resource mode) [V], or Airbyte Cloud trial (reported as 30 days with 400 credits by a third-party article, confirm at signup) [V, secondary] | Free |
| Airflow, dbt Core, Streamlit | Open source | Free |
| LLM for conversational BI | Gemini API free tier or a Claude API key. Gemini free-tier numbers and model names change often, so confirm in AI Studio [V] (https://ai.google.dev/gemini-api/docs/rate-limits) | Free tier or user key |

Both Google Cloud and AWS require a payment card to sign up, so there is no card-free cloud path for CA1 either way. [V]

## 12. CA1 technology stack and justification

| Tool | What and where | Why this one | Alternative rejected | Status |
|---|---|---|---|---|
| Python 3.11+ | Runtime for the whole pipeline | Required by the CA1 brief (Pandas) and the team's language | None needed | Mandatory |
| `requests` with `urllib3.Retry` | Extraction from OpenAQ and Open-Meteo | Plain, explainable, supports retry with backoff and explicit status checks, which the report must describe | `httpx` or `aiohttp` (async adds complexity with a 60 per minute limit, no benefit) | Mandatory |
| Pandas | Cleaning and transformation | Mandated by the CA1 brief. Data is tens of thousands of rows | PySpark (overkill), Polars (not in the brief) | Mandatory |
| PyArrow | Write Parquet | Pandas' standard Parquet engine | fastparquet | Mandatory |
| Google Cloud Storage | Target store for raw JSON and processed Parquet | Same Google Cloud project later hosts BigQuery, giving one account, one set of credentials, and native Parquet loading into BigQuery | AWS S3 (equally valid for CA1, but adds a second cloud account just for CA1) | Mandatory (S3 acceptable per brief) |
| Parquet over CSV | Processed file format | Columnar, compressed (Snappy), keeps column types, supports partition pruning, loads natively into BigQuery. CSV loses types and is larger | CSV | Mandatory choice, justified in report |
| `logging` module | Run logs for evidence | Standard library, produces the terminal proof CA1 requires | Third-party log frameworks | Mandatory |
| `pytest` | Unit tests for transform rules | Lightweight, standard | unittest | Optional |

Not used in CA1: Airflow. The CA1 brief accepts terminal output as execution proof, so adding Airflow would pull microproject work forward without being required.

## 13. Microproject technology stack and justification

| Tool | What and where | Why this one | Alternative rejected | Status |
|---|---|---|---|---|
| Airbyte | Ingestion from OpenAQ and Open-Meteo into BigQuery | The OpenAQ source connector is verified in its catalogue [V]; custom APIs can be wrapped with the Connector Builder [V]; free and open source; the Airflow provider has a dedicated operator [V] | Fivetran: free plan exists (500,000 MAR, no card) [V], but no OpenAQ or Open-Meteo connector was found, and custom sources need its Connector SDK [V], which is more code | Phase-specific, mandatory |
| Google BigQuery | Warehouse: raw, staging, marts | Free tier of 1 TiB queries and 10 GiB storage [V]; shares a project with GCS; serverless, no cluster to babysit; dbt and Airbyte both support it [A] | Snowflake: trial length unverified [U], separate account, no link to GCS | Phase-specific, mandatory |
| dbt Core (dbt-bigquery) | SQL transformations, tests, docs, lineage | Free, version-controlled SQL, built-in tests, auto-generated lineage graph that is excellent for a demo | dbt Cloud (extra account, no need), plain SQL scripts (no tests or lineage) | Phase-specific, mandatory |
| Apache Airflow | Schedules and monitors: Airbyte sync, dbt run, dbt test | Required by brief. `AirbyteTriggerSyncOperator` and `AirbyteJobSensor` exist [V]; provider supports both Airbyte Cloud and open-source via client id and secret [V] | Cron or Python scheduler (explicitly not allowed by the brief) | Phase-specific, mandatory |
| Streamlit | Web UI for conversational BI | Pure Python, fast to build, easy to explain | Gradio, a React app (more code for no extra marks) | Phase-specific |
| LLM text-to-SQL layer | Converts questions to SQL | Provider-agnostic through environment variables. See section 18 for guardrails | Hardcoded answers (explicitly rejected by the brief) | Phase-specific, mandatory |
| `sqlglot` | Parses LLM SQL to enforce read-only rules | Small, well known, lets us check statement type and table names before running | Regex checks (unsafe) | Phase-specific |

Not used, on purpose: Kafka, Spark, Kubernetes, Docker Swarm. The data is small and hourly. Airbyte itself runs on a local Kubernetes cluster under `abctl`, but we do not manage that ourselves [V].

### Airbyte deployment: decision needed

| Option | Pros | Cons |
|---|---|---|
| Airbyte Cloud trial | Light on the laptop; Connector Builder always available | Trial credits and duration to be confirmed at signup; data plane outside our control |
| Local `abctl` | Free, unlimited, closer to a real self-hosted setup | Needs about 4 CPU and 8 GB RAM for good performance; low-resource mode disables the Connector Builder [V], which we need for Open-Meteo |

**Recommendation:** Airbyte Cloud trial, started no earlier than needed so that the trial window covers 16 and 17 November, with local `abctl` as fallback if the machine has 16 GB RAM or more. This depends on your laptop specifications. See open questions in the final proposal.

## 14. CA1 architecture

```
+-------------------+     +------------------+     +----------------------+
| OpenAQ API v3     |     |                  |     |  RAW (GCS)           |
| (stations,sensors,|---->|  extract.py      |---->|  raw/openaq/         |
|  hourly readings) |     |  requests+retry  |     |  ingest_date=YYYY-MM-DD/
+-------------------+     |  status checks   |     |  *.json              |
| Open-Meteo        |---->|  rate limiting   |     +----------+-----------+
| archive + AQ APIs |     +------------------+                |
+-------------------+                                         v
                          +------------------+     +----------------------+
                          | transform.py     |<----|  read raw JSON       |
                          | Pandas cleaning  |     +----------------------+
                          | type casting     |
                          | imputation       |
                          | business rules   |
                          +--------+---------+
                                   |
                                   v
                          +------------------+     +----------------------+
                          | validate.py      |---->| PROCESSED (GCS)      |
                          | schema + range   |     | processed/           |
                          | row-count checks |     |  station_readings_hourly/
                          +------------------+     |   year=2026/month=10/|
                                                   |   *.parquet          |
                                                   +----------------------+
```

CA1 elements the brief requires:

- **Raw versus processed:** raw JSON is stored untouched under `raw/`; only validated Parquet lands under `processed/`.
- **Extraction and retry:** see section 17.
- **Transformation stages:** parse, cast, clean, impute, filter, derive.
- **Storage structure and format:** see section 18.
- **Verification:** logged row counts at each stage, a post-upload check that the object exists with the expected size, and a GCS console screenshot showing the file timestamp.

## 15. Microproject architecture

```
Sources                Ingestion              Warehouse (BigQuery)                 Serving
+-----------+        +-----------+        +-------------------------+        +----------------+
| OpenAQ    |------->|           |        | airtruth_raw            |        | Streamlit chat |
+-----------+        |  Airbyte  |------->|  openaq_*  weather_*    |        |                |
| Open-Meteo|------->|  syncs    |        |  model_aq_*             |        |  question      |
| (Builder) |        +-----------+        +------------+------------+        |    |           |
+-----------+              ^                           |  dbt                |    v           |
                           |                           v                     |  LLM -> SQL    |
                           |              +-------------------------+        |    |           |
                           |              | airtruth_staging        |        |  sqlglot guard |
                           |              |  stg_* (views)          |        |    |           |
                           |              +------------+------------+        |    v           |
                           |                           |                     |  BigQuery      |
                           |                           v                     |  (read-only)   |
                           |              +-------------------------+        |    |           |
                           |              | airtruth_intermediate   |        |    v           |
                           |              |  int_* (views)          |        |  table + chart |
                           |              +------------+------------+        |  + summary     |
                           |                           |                     +-------^--------+
                           |                           v                             |
                           |              +-------------------------+                |
                           |              | airtruth_marts          |----------------+
                           |              |  mart_* (tables)        |
                           |              +-------------------------+
                           |
              +------------+---------------------------------------------+
              |  Apache Airflow DAG: airtruth_daily                        |
              |  sync_openaq >> sync_weather >> sync_model_aq              |
              |  >> dbt_build_staging >> dbt_test_sources_staging          |
              |  >> dbt_build_marts >> dbt_test_marts >> freshness_check   |
              +------------------------------------------------------------+
```

Airflow coordinates three things: ingestion (triggers the Airbyte connections and waits for completion), transformation (runs dbt in dependency order, with tests as gates), and downstream availability (marts only refresh if staging tests pass, so the chatbot never queries half-built tables).

### dbt layers

| Layer | Models | Purpose |
|---|---|---|
| Staging (views) | `stg_openaq_locations`, `stg_openaq_measurements`, `stg_weather_hourly`, `stg_model_air_quality_hourly` | Rename, cast, convert UTC to IST, drop duplicates, nothing business-specific |
| Intermediate (views) | `int_station_hourly` (pivot pm25, pm10, no2, apply short-gap rule), `int_station_weather_model_joined` | Join the three sources at station and hour grain |
| Marts (tables, partitioned by date, clustered by station_id) | `mart_station_daily_air_quality`, `mart_model_vs_ground_daily`, `mart_pollution_weather_drivers`, `mart_station_data_quality` | Answer the four business questions |

### Quality tests

- Sources: not_null and unique on (sensor_id, timestamp); freshness on raw tables.
- Staging: accepted ranges for each pollutant and weather variable; relationships from readings to stations.
- Marts: row-count sanity versus intermediate; completeness between 0 and 1; custom test that daily exceedance flags match the thresholds file.

### Logging and monitoring

Airflow task logs and retries; `dbt` `run_results.json`; Airbyte job history; a BI query log table recording question, generated SQL, bytes billed, and outcome.

## 16. End-to-end data flow

1. Station list: OpenAQ locations in a Mumbai bounding box, filtered to stations with recent PM2.5 data.
2. For each station: readings for PM2.5, PM10, NO2.
3. For each station coordinate: Open-Meteo weather and model air quality for the same window.
4. Clean and harmonise (CA1 in Pandas, microproject in dbt).
5. Build station-hour fact tables, then daily marts.
6. Serve through the Streamlit chat.

Window: the last 90 days ending 7 days before the run date, with a 3-day overlap on each daily run to catch late-arriving station data. Estimated size: about 8 stations x 3 pollutants x 24 hours x 90 days, roughly 52,000 reading rows plus similar weather and model rows. This estimate is mine [A].

Request budget for CA1 backfill: about 24 sensors x 3 pages of 1,000 rows is about 72 calls, comfortably inside 60 per minute and 2,000 per hour, with throttling at 50 per minute for headroom. [A]

## 17. Transformation and cleaning strategy

The same rules apply in both phases. CA1 implements them in Pandas, the microproject re-implements them as dbt SQL.

| # | Operation | Rule | Reason |
|---|---|---|---|
| 1 | Flatten JSON | One row per sensor reading with explicit columns | Predictable schema |
| 2 | Datetime parsing | Parse to `datetime64[ns, UTC]`, derive an Asia/Kolkata column | Avoid UTC versus IST errors in daily aggregates |
| 3 | Type casting | Ids to int64, values to float64, parameter to category, flags to bool | Explicit types are a CA1 requirement and prevent silent string maths |
| 4 | Sentinel and negative values | Negative concentrations and known sentinel codes become null | Physically impossible |
| 5 | Range filter | Remove PM2.5 above 1,000 ug/m3, PM10 above 2,000, NO2 above 2,000 [A, confirm with CPCB sensor ranges at M2] | Sensor faults, not real air |
| 6 | Duplicates | Keep one row per (sensor_id, timestamp), latest ingested wins | Late-arriving corrections |
| 7 | Short-gap imputation | Forward fill up to 3 consecutive hours, set `is_imputed` | Brief outages should not fragment the day |
| 8 | Long gaps | Never impute beyond 3 hours; leave null | Honest data; the quality mart reports it |
| 9 | Weather gaps | Linear interpolation up to 3 hours | Smooth physical variables |
| 10 | Unit harmonisation | Keep ug/m3 only; drop readings in other units, logged | Avoid silent unit mixing |
| 11 | Daily aggregation | Daily mean only if at least 18 of 24 hours are present (a data sufficiency rule) [A] | Standard practice to avoid biased daily means |
| 12 | Business flag | `exceeds_24h_standard` when daily mean exceeds the threshold from `reference/pollutant_thresholds.csv` | Single source of truth for both phases |
| 13 | Station quality score | Completeness, flatline count (same value 6 or more hours), outlier count | Powers `mart_station_data_quality` |

## 18. Storage and schema design

### CA1 bucket layout (GCS)

```
gs://<bucket>/
  raw/
    openaq/ingest_date=2026-11-03/location_id=<id>.json
    open_meteo_weather/ingest_date=2026-11-03/station_id=<id>.json
    open_meteo_aq/ingest_date=2026-11-03/station_id=<id>.json
  processed/
    station_readings_hourly/year=2026/month=10/part-<run_id>.parquet
    weather_hourly/year=2026/month=10/part-<run_id>.parquet
    model_air_quality_hourly/year=2026/month=10/part-<run_id>.parquet
```

Hive-style `year=/month=` partitions let BigQuery and other engines skip irrelevant months. Each run writes a deterministic path per partition, so re-running overwrites rather than duplicating.

### Why Parquet instead of CSV

| Point | Parquet | CSV |
|---|---|---|
| Size | Columnar plus Snappy compression, typically several times smaller | Plain text, largest |
| Types | Schema stored in the file (timestamps, floats, categories survive) | Everything is text and must be re-cast |
| Query efficiency | Reads only the columns needed; partition pruning on year and month | Must read whole files |
| Warehouse loading | BigQuery loads Parquet natively with its schema | Needs schema hints and parsing options |
| Human readability | Needs a tool | Opens anywhere |

We measure the actual compression ratio on our own data and report the numbers in the CA1 report, rather than quoting generic claims.

### Warehouse schema (BigQuery, microproject)

| Dataset | Written by | Contents |
|---|---|---|
| `airtruth_raw` | Airbyte | Raw tables as landed, with Airbyte metadata columns |
| `airtruth_staging` | dbt | `stg_*` views |
| `airtruth_intermediate` | dbt | `int_*` views |
| `airtruth_marts` | dbt | `mart_*` tables, partitioned by date, clustered by station_id |
| `airtruth_ops` | BI app | Query log table |

## 19. CA1 versus microproject reusability matrix

| Component | CA1 implementation | Microproject implementation | Reuse strategy | Classification |
|---|---|---|---|---|
| Data sources | OpenAQ and Open-Meteo through Python | Same sources through Airbyte | Same endpoints, parameters, station list, and window logic documented once | Directly reusable (research and config) |
| Extraction | `requests` with retry in Python | Airbyte connectors (OpenAQ source, Builder connector for Open-Meteo) | CA1 code proves the API behaviour and pagination, which guides connector configuration. CA1 extractor stays as a documented fallback | Reimplemented using a different tool |
| Transformation | Pandas | dbt SQL (staging, intermediate) | Rule table in section 17 is the shared specification. Each Pandas rule has a matching dbt model or test | Reimplemented using a different tool |
| Storage | Parquet in GCS | BigQuery tables | Parquet schema equals BigQuery schema, so a Parquet load is a valid emergency path | Reimplemented using a different tool |
| Orchestration | Single script, terminal logs | Airflow DAG with retries and sensors | Run order from the script becomes the DAG task order | New microproject functionality |
| Data modelling | Flat hourly tables | Staging, intermediate, marts, tests | Canonical schemas in section 10 | Directly reusable (definitions), new (marts) |
| Analytics | Basic summary statistics for the report | Four marts answering the business questions | Same questions, richer implementation | New microproject functionality |
| Interface | None required | Streamlit conversational BI | None | New microproject functionality |
| Validation | Python assertions on ranges and row counts | dbt tests plus Airflow gates | Same thresholds in `reference/pollutant_thresholds.csv` | Reimplemented using a different tool |

### What must be done for CA1

Extraction with retry, Pandas cleaning, type casting, imputation, filters, Parquet to GCS, logs and console screenshot, 3 to 5 page report, demo video.

### What can wait until the microproject

Airbyte, BigQuery, dbt, Airflow, and the BI interface. Do not build these during CA1.

### What changes later

Cleaning logic moves from Pandas to SQL. Run logs move from the terminal to Airflow. Storage targets move from GCS to BigQuery.

### Estimated extra effort for the microproject

About 55 to 70 person-hours across two people, from my own estimate [A], broken down in section 20.

### Suggested division of work (two members)

| Member 1 | Member 2 |
|---|---|
| GCP project and BigQuery setup, Airbyte connections, Airflow DAG, ingestion testing | dbt project: staging, intermediate, marts, tests, docs; BI app and guardrails |
| Joint | Architecture, report writing, demo rehearsal, reviewing each other's work |

Note: CA1 is individual. If your teammate also submits a CA1 on the same domain, confirm with the professor that overlapping work is acceptable. A safe option is for each person's CA1 to use a different station subset or city.

## 20. Phase-wise implementation roadmap

Calendar assumes approval by 1 November. CA1's own deadline is not stated in the PDF, so dates for Phase 1 are provisional.

### Phase 1: CA1

| Milestone | Work | Target |
|---|---|---|
| M1 | Register OpenAQ key, create GCP project and bucket, confirm live Mumbai stations and recent data, confirm endpoints (resolves [U] items) | 1 to 2 Nov |
| M2 | Inspect real responses, finalise schemas, set up environment, `.env.example` | 2 Nov |
| M3 | Extraction with retry, status handling, rate limiting, raw to GCS | 3 Nov |
| M4 | Pandas transform: casting, imputation, filters, flags | 3 to 4 Nov |
| M5 | Validation checks, tests | 4 Nov |
| M6 | Parquet upload, partitioned layout, post-upload verification | 4 Nov |
| M7 | Full run, logs, GCS screenshot with timestamp | 5 Nov |
| M8 | 3 to 5 page report, demo video | 5 to 6 Nov |

### Phase 2: Microproject

| Milestone | Work | Target |
|---|---|---|
| M9 | Review CA1 for reuse; freeze canonical schemas | 6 Nov |
| M10 | Airbyte deployment decision, OpenAQ connector test, Open-Meteo Builder connector prototype (the highest risk item, do it first) | 6 to 8 Nov |
| M11 | BigQuery datasets, service accounts, destination connection, first successful syncs | 8 Nov |
| M12 | dbt staging models and tests | 8 to 10 Nov |
| M13 | Intermediate models and four marts, tests | 10 to 12 Nov |
| M14 | Airflow DAG: syncs, dbt build, tests, failure behaviour | 10 to 12 Nov |
| M15 | Conversational BI: guardrails first, then LLM, then golden-question tests | 12 to 14 Nov |
| M16 | End-to-end run, **feature freeze on 13 Nov**, bug fixing | 13 to 14 Nov |
| M17 | Report, screenshots, demo rehearsal, backup recording | 14 to 15 Nov |
| Buffer | One full day kept free | 15 Nov |
| Demo | Lab sessions | 16 and 17 Nov |

The schedule is tight (about 16 days to the demo). The scope-cut order if time runs out: drop `mart_pollution_weather_drivers` first, then the chart auto-generation in the BI app, then NO2. The required stack (Airflow, Airbyte, dbt, BigQuery, conversational BI) is never cut.

## 21. Testing and validation strategy

| Level | What | How |
|---|---|---|
| Unit (CA1) | Each cleaning rule | `pytest` with small hand-made DataFrames covering negatives, duplicates, gaps, unit mismatch |
| Contract (CA1) | Output schema and dtypes | Assertions in `validate.py` before upload |
| Integration (CA1) | Extract to transform to upload | One real run, row counts logged at each stage |
| Data tests (dbt) | Not null, unique, ranges, relationships, custom threshold test | `dbt test`, gated in Airflow |
| Orchestration | Failure and retry behaviour | Deliberately break a connection and confirm the DAG fails visibly and does not refresh marts |
| Idempotency | Re-running the same window | Row counts must not change |
| BI safety | Rejects `DROP`, `DELETE`, multiple statements, unknown tables, missing LIMIT | Adversarial prompt set, all must be blocked |
| BI quality | Natural language to SQL accuracy | 10 to 15 golden questions with expected answers computed by hand-written SQL |
| Reconciliation | Warehouse versus CA1 | Spot-compare daily PM2.5 means for two stations between the Parquet output and the dbt marts |

## 22. Expected outputs and demo plan

### CA1 deliverables

- Terminal log of a clean run
- GCS console screenshot showing the Parquet object and its timestamp
- 3 to 5 page report (section mapping in Appendix A)
- Demo video

### Microproject deliverables

- Airflow UI showing a successful DAG run and one visible failure and recovery
- Airbyte sync history
- BigQuery datasets with populated marts
- dbt docs lineage graph
- Report in the DE Microproject format
- Live conversational BI demo

### Demo questions for the BI interface (examples)

1. Which station had the highest average PM2.5 last week?
2. On how many days did Sion exceed the 24-hour PM2.5 standard in the last 60 days?
3. How far off is the model from the Bandra ground station, on average?
4. What was the wind speed on the days PM2.5 was above the standard at Kurla?
5. Which station has the least reliable data?

Backup plan: a screen recording of the full flow, because live demos depend on network, APIs, and an LLM.

## 23. Risks, limitations, and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| **BigQuery sandbox does not support DML, streaming, or Data Transfer Service, and expires tables after 60 days [V]** | dbt incremental models and Airbyte typed loading may fail | Use a billing-enabled project (free trial or Free Tier), with budget alerts, `maximum_bytes_billed`, and partition filters. Do not use the sandbox |
| Card required for Google Cloud [V] | Blocks everything | Resolve before M1. Check immediately |
| OpenAQ Mumbai stations lack recent data [U] | Weak dataset | M1 check. Fallback: broaden to Mumbai Metropolitan Region |
| Airbyte OpenAQ connector is Marketplace support level, not certified [V] | May break on pagination or date filters | Test at M10. Fallback: custom Builder connector for OpenAQ as well |
| Open-Meteo has no catalogued Airbyte connector [M] | Custom work on the critical path | Prototype first at M10. Station-coordinate looping in Connector Builder is [U]. Fallback: fewer fixed reference points, or the Airbyte OpenWeather connector [V, exists in catalogue; its key and limits not checked] |
| Airbyte local needs about 4 CPU and 8 GB RAM; low-resource mode disables Builder [V] | Laptop slowness or missing Builder | Prefer Airbyte Cloud trial, confirm hardware |
| Airbyte Cloud trial limits unconfirmed [V, secondary] | Trial may expire before demo | Start the trial at M10, not earlier; verify dates at signup |
| LLM free-tier limits and model names change frequently [V] | BI breaks mid-demo | Provider-agnostic config, cached answers for rehearsed questions only as a clearly labelled fallback, backup video |
| LLM generates unsafe or wrong SQL | Incorrect or costly queries | `sqlglot` guard, allow-list of mart tables, read-only service account, dry run, byte cap, forced LIMIT |
| Open-Meteo non-commercial licence [V] | Academic use is fine; must credit | Include attribution in reports and UI footer |
| Time pressure (16 days) | Unfinished stack | Fixed scope-cut order in section 20, feature freeze on 13 Nov |
| Free-tier terms change | Surprise cost | Budget alert at a low threshold, check pricing pages at M1 |

## 24. References

1. OpenAQ API key: https://docs.openaq.org/using-the-api/api-key
2. OpenAQ rate limits: https://docs.openaq.org/using-the-api/rate-limits
3. OpenAQ platform: https://docs.openaq.org/docs/platform
4. Airbyte OpenAQ connector: https://docs.airbyte.com/integrations/sources/openaq
5. Airbyte connectors and Connector Builder: https://docs.airbyte.com/platform/move-data/sources-destinations-connectors
6. Airbyte local quickstart and resource requirements: https://docs.airbyte.com/platform/using-airbyte/getting-started/oss-quickstart
7. Airflow Airbyte operator: https://airflow.apache.org/docs/apache-airflow-providers-airbyte/5.2.3/operators/airbyte.html
8. Open-Meteo repository, licence and terms: https://github.com/open-meteo/open-meteo
9. Open-Meteo marine API (used to rule out candidate C): https://open-meteo.com/en/docs/marine-weather-api
10. BigQuery sandbox: https://cloud.google.com/bigquery/docs/sandbox
11. Google Cloud free programme: https://cloud.google.com/free
12. AWS Free Tier: https://aws.amazon.com/free
13. Fivetran free plan: https://mdscon.fivetran.com/pricing/free-plan
14. Gemini API rate limits: https://ai.google.dev/gemini-api/docs/rate-limits
15. data.gov.in mandi price resource (rejected candidate B): https://data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi
16. SAFAR Mumbai monitoring network: https://safar.tropmet.res.in/monitoring%20system-10-3-Details
17. Mumbai OpenAQ-derived dataset (evidence of station coverage): https://data.mendeley.com/datasets/9dcb8jmbts/1

---

## Appendix A: Requirement traceability

### CA1 report checklist

| Brief requirement | Where we satisfy it |
|---|---|
| Block diagram: source, extraction, Pandas, S3 or GCS | Section 14 |
| Source details: endpoint, rate limits, schema | Sections 9 and 10 |
| Error handling: retry logic and HTTP status checks | `extract.py`: retry with backoff on 429, 500, 502, 503, 504; honour `x-ratelimit-reset`; fail fast on 401 and 403; skip with warning on 404; non-zero exit on unrecoverable failure |
| Missing value imputation strategy | Section 17, rules 7 to 9 |
| Explicit type casting | Section 17, rule 3 |
| Filtering and business rules | Section 17, rules 4 to 6, 11 to 13 |
| Target bucket structure | Section 18 |
| Parquet versus CSV with justification | Section 18 |
| Terminal output showing success | Milestone M7 |
| Cloud console screenshot with timestamp | Milestone M7 |

### Microproject report checklist

| Brief requirement | Where we satisfy it |
|---|---|
| Problem statement and objective | Sections 3 and 5 |
| Architecture and tech stack | Sections 13 and 15 |
| Ingestion, Airflow DAGs, dbt models, warehouse and BI integration | Sections 15, 18, and the flow in `flow.md` |
| Summary of processed datasets | Row counts from the final run |
| Sample insights through conversational BI | Section 22 |
| Conclusion and learning outcomes | Written at M17 |

## Appendix B: Viva answer map

| Question | Short answer and where to read more |
|---|---|
| Why this project? | A genuine reconciliation and data quality problem with verified tooling. Sections 4 and 8 |
| Why these sources? | Ground truth, weather explanation, and model estimate, all free and accessible. Section 9 |
| How do we extract? | `requests` with retry in CA1, Airbyte in the microproject. Sections 12 and 13 |
| What if an API fails? | Retry with backoff, status handling, rate-limit headers, loud failure. Appendix A |
| Why Pandas? | Required by CA1 and sized for tens of thousands of rows. Section 12 |
| Why Parquet? | Types, compression, column pruning, partitioning. Section 18 |
| Why GCS and BigQuery? | One cloud account, native Parquet loading, free tier. Sections 12 and 13 |
| How does Airflow orchestrate? | Triggers syncs, runs dbt, gates on tests. Section 15 |
| Why Airbyte and not Fivetran? | Verified OpenAQ connector and Builder for the rest. Section 13 |
| What does dbt do? | Versioned SQL transformations with tests and lineage. Section 15 |
| Staging versus marts? | Staging cleans one source; marts answer business questions. Section 15 |
| How does conversational BI stay safe? | LLM output is parsed, restricted, dry-run, and executed read-only. Planned in `flow.md` |
| What was reused? | Sources, schemas, rules, thresholds. Section 19 |
| What is new in the microproject? | Orchestration, warehouse modelling, tests, BI. Section 19 |
