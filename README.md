# MESSE × Snowflake CoCo CLI Hackathon 2026

**Problem statement #4 — Domain-Specific AI Copilot (capital markets, Indonesia)**

An AI copilot that reads accumulation/distribution patterns on the Indonesia
Stock Exchange using *bandarmologi*-style signals, and sizes risk with
Fractional Kelly against an edge it measures rather than assumes.

> **Data reality, stated up front**: MESSE does not collect IDX broker
> transaction data (verified against its production MySQL schema and source
> code — there is no broker feed anywhere in the product). Classic
> bandarmologi reads broker order flow; this prototype instead re-ranks
> MESSE's own precomputed price/volume accumulation & distribution factor
> scores cross-sectionally in Snowflake. It is a proxy, not order flow — see
> "Known gaps" below and `copilot_spec.md`, which requires the agent to say
> this explicitly rather than let the name imply more than the data supports.

---

## Run order

```bash
snow sql -f 01_schema.sql        # database, schemas, tables, stage
# export CSVs from MESSE's real MySQL db (see header of 02_load.sql —
# NOT sqlite3, MESSE runs on MySQL/Hostinger)
snow stage copy market_data.csv    @MESSE.RAW.MESSE_STAGE --overwrite
snow stage copy expert_scores.csv  @MESSE.RAW.MESSE_STAGE --overwrite
snow stage copy stock_scores.csv   @MESSE.RAW.MESSE_STAGE --overwrite
snow stage copy dim_emiten.csv     @MESSE.RAW.MESSE_STAGE --overwrite
snow sql -f 02_load.sql          # COPY INTO + data quality gate
snow sql -f 03_transforms.sql    # signal layer
```

Then register `messe_semantic_model.yaml` for Cortex Analyst /
Snowflake Intelligence, and wire the agent per `copilot_spec.md`.

## Layers

| Object | What it does |
|---|---|
| `RAW.MARKET_DATA` | OHLCV landing, as exported from MESSE `market_data` |
| `RAW.EXPERT_SCORES` | MESSE's own accumulation/distribution/volume factor scores |
| `RAW.STOCK_SCORES` | MESSE's own final score + labels, kept for cross-reference only |
| `MART.DAILY_PRICE_FEAT` | Returns, liquidity, volatility, forward returns |
| `MART.SIG_ACCUMULATION` | Rolling accumulation/distribution factor scores + signal persistence |
| `MART.BANDAR_SCORE` | Composite 0–100, cross-sectional percentile ranks |
| `MART.SIGNAL_EDGE` | **Measured** win rate and payoff per signal bucket |
| `MART.VW_POSITION_SIZING` | Quarter-Kelly weight + caveat |
| `MART.VW_WATCHLIST` | Serving view for the copilot |

## The design decision worth defending

`SIGNAL_EDGE` sits between the score and the sizing on purpose. Kelly needs a win
rate and a payoff ratio; most implementations hardcode plausible-looking numbers.
Here both are computed from realised 20-day forward returns per bucket, and the
sizing view returns **zero** when the measured Kelly fraction is non-positive.

The pipeline was validated on synthetic random-walk data before touching real
data. On data with no genuine edge, it correctly sized nothing. That negative
test is worth showing to judges — it demonstrates the system fails closed.

## Known gaps to state honestly in the submission

- **No broker-level data exists in MESSE.** `BANDAR_SCORE` is a price/volume
  factor-score proxy (MESSE's own `accumulation_score` / `distribution_score` /
  `volume_score`, re-ranked cross-sectionally), not measured broker order flow.
  This is the single biggest deviation from the original design and from what
  "bandarmologi" classically means — say so before a judge has to ask.
- MESSE's own `bandar_score`/`bandar_signal`/`smart_money_label` fields
  (`RAW.STOCK_SCORES`) are inconsistently populated — many rows are NULL or
  left at default (score never computed for that ticker/day). Carried through
  `VW_WATCHLIST` for cross-reference only, not used to compute `BANDAR_SCORE`.
- MESSE's stored `market_data.value` column is always 0 in production;
  `VALUE_IDR` is recomputed on export as `close * volume`, which is an
  approximation (ignores intraday VWAP).
- Forward returns overlap across dates, so bucket win rates are correlated
  observations. A proper walk-forward split with purged embargo is the next step.
- The liquidity floor (IDR 1bn/day) is a judgement call, not a fitted parameter.
- `LISTED_SHARES` / `FREE_FLOAT_PCT` are not tracked by MESSE — NULL for most
  tickers in `DIM.EMITEN` unless hand-backfilled for known LQ45 names.

Stating these earns more credit than hiding them. "Solution completeness" in the
rubric rewards knowing where your system ends.

## Scope discipline

Submission closes **6 August 2026**. If time runs short, cut the number of
emiten and the number of signals — never cut a layer. A thin pipeline that runs
end-to-end scores far better than a wide one that stops at the mart.

## Regulatory framing

Positioned as decision support and risk sizing, not investment recommendation.
The copilot is prompted to refuse buy/sell calls and to surface every sizing
caveat. See `agent/copilot_spec.md`.
