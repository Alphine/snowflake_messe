# SDD — MESSE Bandarmologi Copilot on Snowflake
**Snowflake CoCo CLI Hackathon 2026 — Problem Statement #4 (Domain-Specific AI Copilot)**
**Deadline: prototype submission closes 6 August 2026. Time is the binding constraint.**

---

## 0. Read this first (context for Claude Code)

This SDD hands off a **partially built** pipeline. SQL logic has already been
written and validated on synthetic data in DuckDB (window-function semantics
verified to match Snowflake, including two bugs already fixed: nested window
functions, and `RANGE BETWEEN INTERVAL` framing replaced with a self-join).
Do not redesign the schema or scoring logic from scratch — extend and wire it.

Files already exist at:
```
sql/01_schema.sql          -- database, schemas, tables, stage  [DONE, untested on real Snowflake]
sql/02_load.sql             -- COPY INTO + data quality gate     [DONE, needs real CSVs]
sql/03_transforms.sql       -- full signal pipeline               [DONE, logic-validated]
semantic/messe_semantic_model.yaml  -- Cortex Analyst semantic layer [DONE]
agent/copilot_spec.md       -- system prompt + agent workflow     [DONE]
seed/dim_broker.csv         -- partial broker master, VERIFY      [PARTIAL]
seed/dim_emiten.csv         -- 5 sample tickers only               [PARTIAL, expand]
test_logic.py                -- DuckDB validation harness          [DONE, keep using it]
```

**Your job is what's below — the parts that were not yet possible without
real data access and a real Snowflake account.**

---

## 1. Objective

Ship a working, demoable prototype: MESSE's IDX price + broker-flow data lands
in Snowflake, gets transformed into bandarmologi signals, exposed through a
Cortex Analyst semantic layer, and answered by an agentic copilot via CoCo CLI.

**Not the objective:** porting all of MESSE. Scope is capped at what's needed
for a 4-minute demo that survives judge questions.

---

## 2. Current state of the data model

```
RAW.DAILY_PRICE       (ticker, trade_date, OHLCV, value, frequency, foreign buy/sell)
RAW.BROKER_SUMMARY    (ticker, trade_date, broker_code, buy/sell lot+value+avg)
RAW.INDEX_DAILY       (index_code, trade_date, close, volume, value)  -- IHSG context
DIM.BROKER            (broker_code, name, is_foreign, tier)
DIM.EMITEN            (ticker, name, sector, sub_sector, shares, free_float, is_lq45)

MART.FACT_BROKER_NET       -- net flow per broker/ticker/day
MART.DAILY_BROKER_AGG      -- HHI concentration, top net buyer, foreign net
MART.TOP_BUYER_PERSIST     -- 28-day rolling: has one broker kept leading?
MART.DAILY_PRICE_FEAT      -- returns, 20d vol, 20d avg value, forward returns
MART.SIG_ACCUMULATION      -- accumulation intensity normalised by turnover
MART.BANDAR_SCORE          -- composite 0-100 score + SIGNAL_LABEL
MART.SIGNAL_EDGE           -- MEASURED win rate / payoff per signal bucket
MART.VW_POSITION_SIZING    -- quarter-Kelly weight, capped, with SIZING_CAVEAT
MART.VW_WATCHLIST          -- serving view, latest signal per ticker
```

The scoring weights (`0.40 accum + 0.25 concentration + 0.20 persistence + 0.15
quiet`) and the liquidity floor (`AVG_VALUE_20D >= 1e9`) are judgement calls
from prior discussion with the founder, not fitted parameters. Leave them as
configurable constants — do not silently retune them.

---

## 3. Tasks — in priority order

### Task A — Data export and load (BLOCKING, do first)

1. Inspect the actual MESSE SQLite schema:
   ```
   sqlite3 <path-to-messe.db> ".schema daily_price"
   sqlite3 <path-to-messe.db> ".schema broker_summary"
   ```
2. Reconcile column names/types against `RAW.DAILY_PRICE` and
   `RAW.BROKER_SUMMARY` in `sql/01_schema.sql`. **If they don't match, fix the
   export query — do not silently rename Snowflake columns**, since the
   semantic model and transforms reference these names by contract.
3. Export CSVs (query templates are in the header comment of `sql/02_load.sql`).
   Scope: last 12–18 months, prioritize LQ45 + top 100 by liquidity if the full
   universe is large. State the actual cutoff used in the demo notes.
4. Expand `seed/dim_emiten.csv` to cover every ticker in the export — a ticker
   present in `RAW.DAILY_PRICE` but missing from `DIM.EMITEN` will show `NULL`
   company name/sector in `VW_WATCHLIST` and looks broken on stage.
5. Verify `seed/dim_broker.csv` against the current IDX exchange member list.
   Any broker code present in `RAW.BROKER_SUMMARY` but absent from
   `DIM.BROKER` silently defaults to `IS_FOREIGN = FALSE` — this directly
   biases the foreign-flow signal. Run the "unmapped broker" query in
   `sql/02_load.sql` and close every gap it reports before moving on.
6. Run `sql/01_schema.sql` → stage the 4 CSVs → `sql/02_load.sql`. Confirm the
   data quality gate output (row counts, date range, unmapped brokers, buy/sell
   imbalance) before proceeding to Task B. If imbalance > 2% on more than a
   handful of ticker-days, stop and investigate the export query — do not
   proceed on bad broker data, since every downstream signal depends on it.

### Task B — Run and validate transforms

1. Run `sql/03_transforms.sql` on the real warehouse.
2. Sanity-check `MART.SIGNAL_EDGE`: each `SIGNAL_LABEL` bucket should have
   `N_OBS` reported. If `STEALTH_ACCUMULATION` or `DISTRIBUTION` have fewer
   than ~30 observations, that's expected on a short history — surface it via
   `SIZING_CAVEAT = 'INSUFFICIENT_SAMPLE'`, don't try to force more data to
   make the bucket look robust.
3. Query `MART.VW_POSITION_SIZING` and confirm at least one row exists with
   `SIZING_CAVEAT = 'OK'` and `SUGGESTED_WEIGHT > 0`. If every bucket comes
   back `NO_EDGE`, that is a legitimate and demoable finding (see Section 5 —
   "honesty beat") — do not adjust the scoring weights just to manufacture a
   positive edge. Flag it to the founder instead if it happens.

### Task C — Register the semantic layer

1. Register `semantic/messe_semantic_model.yaml` with Cortex Analyst /
   Snowflake Intelligence per current Snowflake docs (verify the registration
   command/UI path — it may have changed; don't guess from training data).
2. Run the four `verified_queries` in the YAML manually against
   `MART.VW_WATCHLIST` / `MART.VW_POSITION_SIZING` to confirm they return rows
   with real data, not just against the synthetic set.
3. If any verified query returns empty because a threshold doesn't fit the
   real data's scale (e.g. the `AVG_VALUE_20D >= 5000000000` liquidity filter
   in `stealth_accumulation_screen`), adjust the threshold in the YAML to a
   percentile that actually returns 10–20 tickers, and note the change.

### Task D — Wire the CoCo CLI agent

1. Implement the agent workflow described in `agent/copilot_spec.md` section
   "Agent workflow (CoCo CLI orchestration)" using Snowflake CoCo CLI.
2. Use the system prompt in `agent/copilot_spec.md` verbatim as the base —
   it encodes compliance constraints (no buy/sell calls, caveats must be
   surfaced) that are load-bearing for the submission, not just style.
3. Confirm the agent actually queries Snowflake for every ticker/price/broker
   claim rather than answering from context — this is explicit in the system
   prompt's rule 1. Test this by asking about a ticker NOT in the watchlist
   and confirming the agent says so rather than fabricating a plausible answer.
4. Test the two demo questions from `agent/copilot_spec.md`:
   - "Saham apa yang lagi diakumulasi diam-diam?"
   - "Berapa besar posisi yang wajar?"
   Confirm the second answer surfaces `SIZING_CAVEAT` in the response text,
   not just in a data table the user has to interpret themselves.

### Task E — Demo prep

1. Follow the demo script table in `agent/copilot_spec.md` (target 4 minutes).
2. Prepare the "honesty beat" (Task B, step 3) as an actual screen you can
   show — a query against `MART.VW_POSITION_SIZING WHERE SIZING_CAVEAT !=
   'OK'` returning real rows. This is the differentiator; don't skip it under
   time pressure even if everything else is running late.
3. Write up the "Known gaps" section from `README.md` into the submission
   text substantively — overlapping forward-return windows, partial broker
   mapping, judgement-call thresholds. Judges score "solution completeness"
   partly on whether a team knows its own edges.

---

## 4. Explicit non-goals (do not do these, even if there's time left)

- Do not port MESSE's Orchestra Intelligence multi-expert consensus system in
  full — reference it in the pitch narrative as a future direction, not as a
  built feature, unless it is already fully working and tested.
- Do not add options/derivatives data, only IHSG cash equities.
- Do not build a custom frontend. CoCo CLI + Snowflake Intelligence /
  Snowsight is the interface for this submission.
- Do not present `SUGGESTED_WEIGHT` anywhere as a buy/sell recommendation.
  Every surface (semantic layer descriptions, agent responses, demo slides)
  must frame it as risk-sizing decision support. This is a regulatory
  guardrail from the original design discussion, not a style preference.

---

## 5. Acceptance criteria

- [ ] `snow sql -f sql/01_schema.sql` runs clean on the real account
- [ ] Real MESSE data loaded; data quality gate shows zero unmapped brokers
      and <2% buy/sell imbalance on the vast majority of ticker-days
- [ ] `sql/03_transforms.sql` runs clean end-to-end on real data
- [ ] `MART.SIGNAL_EDGE` has non-trivial `N_OBS` per bucket; results reported
      honestly even if some buckets show `NO_EDGE`
- [ ] Semantic model registered; all 4 verified queries return real rows
- [ ] CoCo CLI agent answers both demo questions, correctly surfaces
      `SIZING_CAVEAT`, and refuses to answer about tickers not in the data
- [ ] Demo run-through completed at least once end-to-end before submission,
      including the "honesty beat" (a `NO_EDGE` or `INSUFFICIENT_SAMPLE` result
      shown on screen, not just described)

---

## 6. If you get stuck

Report back rather than silently working around these:
- Export CSV columns don't reconcile with the DDL after inspection
- Buy/sell imbalance gate fails broadly (>2% on most ticker-days)
- Every signal bucket comes back `NO_EDGE` after a full data load (real
  finding worth surfacing, but the founder should decide how to frame it)
- Snowflake CoCo CLI registration/auth steps differ from what's assumed here
  (the product surface may have changed since this SDD was written)
