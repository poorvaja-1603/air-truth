# flow.md

STATUS: PLANNED FLOW. No code exists yet. Every file, entry point, and module below is a plan, not a description of working code. Each section is replaced with real content, including real function names, as its milestone lands.

Last updated: 31 October 2026.

## 1. Overall system flow (planned)

Two phases share one domain and one set of rules.

Phase 1 (CA1): OpenAQ and Open-Meteo APIs -> Python extraction -> raw JSON in GCS -> Pandas cleaning -> validation -> partitioned Parquet in GCS.

Phase 2 (Microproject): OpenAQ and Open-Meteo -> Airbyte -> BigQuery raw -> dbt staging -> dbt intermediate -> dbt marts -> conversational BI. Airflow runs and monitors the whole chain.

## 2. Architecture and pipeline flow diagrams

See `plan.md` sections 14 and 15 for the full diagrams. They are kept there to avoid two copies drifting apart.

## 3. Execution entry points (planned)

| Phase | Entry point | What it does |
|---|---|---|
| CA1 | `ca1/run_pipeline.py` | Runs extract, transform, validate, load in order and exits non-zero on any failure |
| Microproject | Airflow DAG `airtruth_daily` | Triggers Airbyte syncs, then dbt build and test, then a freshness check |
| Microproject | `microproject/bi_app/app.py` | Streamlit chat interface |

## 4. Order of execution (planned)

### CA1

1. `config` loads environment variables and the station list.
2. `extract` fetches OpenAQ stations and readings, Open-Meteo weather and model air quality; writes raw JSON.
3. `transform` reads raw JSON, applies the rule table from `plan.md` section 17.
4. `validate` checks schema, dtypes, ranges, and row counts.
5. `load` writes Parquet to GCS partitions and verifies the object exists.
6. `run_pipeline` logs a summary with counts per stage.

### Microproject DAG `airtruth_daily` (planned task order)

1. `sync_openaq` (Airbyte connection)
2. `sync_weather` (Airbyte connection, Builder connector)
3. `sync_model_air_quality` (Airbyte connection, Builder connector)
4. `dbt_build_staging`
5. `dbt_test_staging`
6. `dbt_build_marts`
7. `dbt_test_marts`
8. `freshness_check`

Any failure stops downstream tasks, so marts are never refreshed from failed or untested data.

## 5. Planned responsibility of each file

| Planned file | Responsibility | Depends on |
|---|---|---|
| `ca1/discover_stations.py` | Query OpenAQ for live Mumbai stations, sensors, and recency | OpenAQ API, `.env` |
| `ca1/inspect_csv.py` | Profile external CSV files (schemas, nulls, date ranges) | CSV files in `data/external/` |
| `ca1/config.py` | Read environment variables, hold constants | `.env` |
| `ca1/extract.py` | HTTP calls, retry, status handling, rate limiting, raw JSON writing | config |
| `ca1/transform.py` | Cleaning and derivation rules | raw JSON, `reference/pollutant_thresholds.csv` |
| `ca1/validate.py` | Pre-upload checks | transform output |
| `ca1/load.py` | Upload Parquet to GCS, verify | validated frames, GCS credentials |
| `ca1/run_pipeline.py` | Orchestrate the four stages and log counts | all of the above |
| `reference/pollutant_thresholds.csv` | Single source of thresholds | read by `transform.py` and loaded as a dbt seed |
| `microproject/airbyte/` | Connector and connection notes, Builder export | Airbyte workspace |
| `microproject/airflow/dags/airtruth_daily.py` | The DAG | Airbyte connection ids, dbt project |
| `microproject/dbt/models/staging/` | `stg_*` models | `airtruth_raw` tables |
| `microproject/dbt/models/intermediate/` | `int_*` models | staging |
| `microproject/dbt/models/marts/` | `mart_*` models | intermediate |
| `microproject/bi_app/` | UI, LLM client, SQL guard, query log | marts, read-only credentials |

## 6. Important functions and their responsibilities

To be filled in when code exists. Functions are not listed here until they are written.

## 7. Data passed between components (planned)

| From | To | Data |
|---|---|---|
| OpenAQ and Open-Meteo | `extract` | JSON responses |
| `extract` | `transform` | Raw JSON files under `raw/` |
| `transform` | `validate` | Pandas DataFrames with canonical columns from `plan.md` section 10 |
| `validate` | `load` | Same frames, only if all checks pass |
| Airbyte | BigQuery `airtruth_raw` | Raw tables with Airbyte metadata columns |
| dbt | BigQuery staging, intermediate, marts | Views and tables |
| BI app | BigQuery marts | Validated SELECT statements only |

## 8. Where intermediate data is stored (planned)

- CA1 raw: `gs://<bucket>/raw/...` and a local gitignored `data/raw/` copy
- CA1 cleaned frames: in memory, then written as Parquet
- Microproject raw: `airtruth_raw` dataset
- dbt intermediate: `airtruth_intermediate` views

## 9. Where final outputs appear (planned)

- CA1: `gs://<bucket>/processed/<table>/year=YYYY/month=MM/*.parquet`, plus the run log
- Microproject: `airtruth_marts` tables, Airflow run history, Streamlit answers, BI query log in `airtruth_ops`

## 10. How Airflow coordinates the microproject (planned)

Airflow triggers each Airbyte connection and waits on job completion with the Airbyte operator and sensor. It then runs dbt through shell commands, treating `dbt test` as a pass or fail gate between building staging and marts. Retries are configured per task; a task that exhausts retries fails the run visibly.

## 11. dbt model dependencies (planned)

```
airtruth_raw.openaq_locations  ----> stg_openaq_locations  -----------+
airtruth_raw.openaq_measurements -> stg_openaq_measurements --> int_station_hourly --+
airtruth_raw.weather_hourly ------> stg_weather_hourly ---------------+              |
airtruth_raw.model_aq_hourly -----> stg_model_air_quality_hourly -----+              v
                                                              int_station_weather_model_joined
                                                                      |
          +-----------------------------+-----------------------------+------------------+
          v                             v                             v                  v
mart_station_daily_air_quality  mart_model_vs_ground_daily  mart_pollution_weather_drivers  mart_station_data_quality
```

## 12. How the BI interface reaches warehouse data (planned)

1. User types a question in Streamlit.
2. The app sends the question plus a curated description of the mart tables to the configured LLM.
3. The generated SQL goes through the guard: single SELECT statement, allow-listed tables only, LIMIT enforced.
4. A BigQuery dry run estimates bytes; the job runs with `maximum_bytes_billed` set, under a read-only service account.
5. Rows come back, are shown as a table, and a short summary is generated from the returned rows only.
6. Question, SQL, bytes billed, and outcome are written to the query log.

## 13. Changes log

| Date | Change |
|---|---|
| 31 Oct 2026 | Initial planned flow created |
| 31 Oct 2026 | Added `ca1/discover_stations.py` and `ca1/inspect_csv.py` to CA1 file responsibilities |
