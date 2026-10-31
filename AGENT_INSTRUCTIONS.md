# AGENT_INSTRUCTIONS.md

Rules for every implementation session on AirTruth Mumbai. Read this file and `plan.md` before changing anything.

## 1. Before you start any task

1. Read `plan.md`, then `decision.md`, then `flow.md`.
2. Confirm which milestone you are working on (M1 to M17 in `plan.md`, section 20).
3. Check the evidence tags in `plan.md`. Any item tagged [U] must be confirmed against the live source or official documentation before code depends on it. Record the outcome in `decision.md`.
4. If a request conflicts with this file or `plan.md`, stop and ask. Do not quietly pick a side.

## 2. Source of truth

- The two official requirement documents are the source of truth: the CA1 PDF and the DE Microproject report format.
- CA1 and the microproject are separate submissions with different required tools. Never claim that CA1 code satisfies the microproject.
- Do not replace Airflow with a Python scheduler or cron, dbt with Pandas, Airbyte with `requests`, or BigQuery with local storage in the microproject.
- Do not change the selected architecture without a documented technical reason in `decision.md`.

## 3. Phase discipline

- CA1 work: Python, `requests`, Pandas, PyArrow, Google Cloud Storage only.
- Do not build Airflow, Airbyte, dbt, BigQuery, or BI features during CA1 unless needed for architecture compatibility, and say why in `decision.md`.
- Microproject work starts only after CA1 milestones M1 to M8 are complete or explicitly parked by the user.
- The CA1 extractor stays in the repository as a documented fallback. Do not delete it.

## 4. Engineering rules

- Implement incrementally. One milestone at a time.
- The project must run after every milestone. Do not leave the main branch broken.
- Keep responsibilities separate: ingestion, transformation, validation, storage, orchestration, interface. One module, one job.
- Test each stage on its own before wiring stages together.
- Do not add a dependency unless the current task needs it. Every new dependency is justified in `decision.md`.
- Do not use Kafka, Spark, Kubernetes, or similar unless the user approves and a real requirement exists.
- No duplicate logic. Shared rules live in `reference/pollutant_thresholds.csv` and the rule table in `plan.md` section 17.
- Keep raw data separate from processed data, always.
- Keep schemas and business rules identical across phases. If one must change, change both and log it.

## 5. Failure handling

- Handle missing records, invalid values, API failures, retries, and connection errors explicitly.
- Retry only on retryable conditions (429, 500, 502, 503, 504, connection errors) with exponential backoff and a hard cap.
- On 429, honour the `x-ratelimit-reset` header when present.
- Fail fast on 401 and 403. Skip with a logged warning on 404 for a single station, and continue.
- Never silently hide a failed run. A failed stage must exit non-zero (CA1) or fail the Airflow task (microproject). Never mark a run successful when a stage failed.
- Log row counts at every stage boundary: extracted, after cleaning, after validation, uploaded.

## 6. Honesty rules

- Never fabricate source data. Never invent API responses, row counts, screenshots, logs, or timestamps.
- Never claim an execution succeeded unless it ran and you saw the output. Quote real output when reporting results.
- If something could not be run (no network, no credentials), say so plainly and describe what remains.
- Distinguish verified facts from assumptions in documentation. Keep the evidence tags from `plan.md`.

## 7. Secrets and configuration

- Never hardcode API keys, service account files, passwords, or tokens.
- Read configuration from environment variables. Maintain `.env.example` with every variable name and a dummy value.
- `.env`, service account JSON files, `data/`, and Airbyte credentials are in `.gitignore` from the first commit.
- Never print secrets in logs or error messages.
- BI database access uses a read-only service account separate from the pipeline account.

## 8. Documentation duties

- Update `decision.md` whenever a meaningful technical decision is made or changed. Keep the old row and mark it superseded with a one-line reason.
- Update `flow.md` whenever the execution flow, file responsibilities, or data hand-offs change.
- Keep documentation consistent with the code. If you cannot update it in the same change, say so.
- Do not document functions or files that do not exist. The planned sections of `flow.md` are marked PLANNED and are replaced as code lands.

## 9. Code quality (very important)

- No unnecessary comments. Do not explain obvious statements.
- Comment only genuinely non-obvious logic or important edge cases, for example why a lookback window overlaps.
- Do not generate excessive docstrings. Prefer clear names over documentation.
- Use meaningful function and variable names.
- Keep functions short and focused.
- Avoid overengineering, deep class hierarchies, and clever abstractions.
- Write code that an undergraduate student can read and explain in a viva.
- No dead code, no commented-out code, no unused imports.
- Prefer the standard library and already-approved dependencies.
- SQL in dbt: one model per concept, explicit column lists in staging, CTEs named by purpose, consistent snake_case.

## 10. Testing expectations

- Every cleaning rule in `plan.md` section 17 has a unit test (CA1) and a dbt test or model check (microproject).
- Before declaring a milestone done: run its tests, run the pipeline stage, report the real output.
- Test idempotency: running the same window twice must not change row counts.
- BI safety tests must include destructive statements, multi-statement input, unknown tables, and missing LIMIT.

## 11. Definition of done per milestone

A milestone is done only when all of these hold:

1. Code runs from a clean checkout using documented commands.
2. Tests for the milestone pass, with real output shown.
3. No secrets in the repository.
4. `decision.md` and `flow.md` reflect reality.
5. The user has been told what was verified and what was not.

## 12. Stop conditions

Stop and ask the user when:

- A [U] item turns out false and changes the architecture.
- A paid feature or billing change would be needed.
- A requirement in the two official documents appears unmet.
- The scope-cut order in `plan.md` section 20 needs to be applied.

## 13. Repository layout (planned)

```
airtruth-mumbai/
  plan.md  AGENT_INSTRUCTIONS.md  decision.md  flow.md
  .env.example  .gitignore  README.md
  reference/pollutant_thresholds.csv
  ca1/            extract, transform, validate, load, run, config, tests
  microproject/
    airbyte/      connector definitions and connection notes
    airflow/      dags and docker setup
    dbt/          staging, intermediate, marts, tests, seeds
    bi_app/       Streamlit app, SQL guard, LLM client, query log
  data/           local raw and processed copies (gitignored)
```

Create folders only when the milestone needs them.
