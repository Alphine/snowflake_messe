-- ============================================================
-- 02_load.sql — stage upload + COPY INTO
--
-- STEP 1 (shell, from MESSE's real MySQL db `u808021404_messe`):
-- Run these against the production MySQL (phpMyAdmin / mysql CLI /
-- mysqldump --where). NOT sqlite3 — the SDD's original assumption
-- of a SQLite export was wrong; MESSE runs on MySQL (Hostinger).
--
--   mysql -h <host> -u <user> -p u808021404_messe -e "
--     SELECT ticker, date, open, high, low, close, volume,
--            (COALESCE(close,0) * COALESCE(volume,0)) AS value_idr
--     FROM market_data
--     WHERE date >= '2024-02-01'
--   " --batch > market_data.csv
--
--   mysql -h <host> -u <user> -p u808021404_messe -e "
--     SELECT ticker, date, accumulation_score, distribution_score,
--            volume_score, liquidity_score, volatility_score
--     FROM expert_scores
--     WHERE date >= '2024-02-01'
--   " --batch > expert_scores.csv
--
--   mysql -h <host> -u <user> -p u808021404_messe -e "
--     SELECT ticker, date, final_score, signal,
--            bandar_score, bandar_signal, smart_money_label
--     FROM stock_scores
--     WHERE date >= '2024-02-01'
--   " --batch > stock_scores.csv
--
--   mysql -h <host> -u <user> -p u808021404_messe -e "
--     SELECT ticker, name, sector, industry, is_active
--     FROM stocks WHERE is_active = 1
--   " --batch > stocks_export.csv
--   -- then hand-merge stocks_export.csv into dim_emiten.csv (adds
--   -- LISTED_SHARES / FREE_FLOAT_PCT / IS_LQ45 manually for LQ45 names,
--   -- NULL otherwise) — do NOT load stocks_export.csv directly, column
--   -- order doesn't match DIM.EMITEN.
--
-- `--batch` output is tab-separated with a header row and literal
-- "NULL" for nulls; convert to comma-CSV (e.g. `column -s$'\t' -o,`
-- or a one-line python/csv script) before staging — the stage's
-- FILE_FORMAT below expects comma-delimited CSV with a header.
--
-- STEP 2 (shell): upload to stage
--   snow stage copy market_data.csv     @MESSE.RAW.MESSE_STAGE --overwrite
--   snow stage copy expert_scores.csv   @MESSE.RAW.MESSE_STAGE --overwrite
--   snow stage copy stock_scores.csv    @MESSE.RAW.MESSE_STAGE --overwrite
--   snow stage copy dim_emiten.csv      @MESSE.RAW.MESSE_STAGE --overwrite
--
-- STEP 3: run this file
--   snow sql -f 02_load.sql
-- ============================================================

USE DATABASE MESSE;
USE WAREHOUSE MESSE_WH;

COPY INTO RAW.MARKET_DATA
FROM @RAW.MESSE_STAGE/market_data.csv
ON_ERROR = 'CONTINUE';

COPY INTO RAW.EXPERT_SCORES
FROM @RAW.MESSE_STAGE/expert_scores.csv
ON_ERROR = 'CONTINUE';

COPY INTO RAW.STOCK_SCORES
FROM @RAW.MESSE_STAGE/stock_scores.csv
ON_ERROR = 'CONTINUE';

COPY INTO DIM.EMITEN
FROM @RAW.MESSE_STAGE/dim_emiten.csv
ON_ERROR = 'CONTINUE';

-- ------------------------------------------------------------
-- Data quality gate — run BEFORE transforms. If any of these
-- look wrong, the signals downstream will be silently garbage.
-- ------------------------------------------------------------
SELECT 'market_data'    AS TBL, COUNT(*) AS ROWS_,
       COUNT(DISTINCT TICKER) AS TICKERS,
       MIN(TRADE_DATE) AS FROM_DT, MAX(TRADE_DATE) AS TO_DT
FROM RAW.MARKET_DATA
UNION ALL
SELECT 'expert_scores', COUNT(*), COUNT(DISTINCT TICKER),
       MIN(TRADE_DATE), MAX(TRADE_DATE)
FROM RAW.EXPERT_SCORES
UNION ALL
SELECT 'stock_scores', COUNT(*), COUNT(DISTINCT TICKER),
       MIN(TRADE_DATE), MAX(TRADE_DATE)
FROM RAW.STOCK_SCORES;

-- tickers present in market_data but missing from DIM.EMITEN
-- (these show NULL company name/sector in VW_WATCHLIST)
SELECT DISTINCT md.TICKER
FROM RAW.MARKET_DATA md
LEFT JOIN DIM.EMITEN e ON e.TICKER = md.TICKER
WHERE e.TICKER IS NULL;

-- coverage check: how many ticker/days have expert_scores data at
-- all vs just market_data — expert_scores is the bandar-proxy input,
-- if this is thin the whole signal layer is thin. Report honestly,
-- don't force it (SDD Task B step 2).
SELECT
    COUNT(DISTINCT md.TICKER || '|' || md.TRADE_DATE)  AS PRICE_TICKER_DAYS,
    COUNT(DISTINCT es.TICKER || '|' || es.TRADE_DATE)  AS EXPERT_SCORE_TICKER_DAYS
FROM RAW.MARKET_DATA md
LEFT JOIN RAW.EXPERT_SCORES es
       ON es.TICKER = md.TICKER AND es.TRADE_DATE = md.TRADE_DATE;

-- days where OHLC looks broken (high < low, close outside [low,high])
-- — replaces the old buy/sell imbalance gate, which doesn't apply
-- since there's no broker_summary anymore.
SELECT TICKER, TRADE_DATE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, CLOSE_PRICE
FROM RAW.MARKET_DATA
WHERE HIGH_PRICE < LOW_PRICE
   OR CLOSE_PRICE > HIGH_PRICE
   OR CLOSE_PRICE < LOW_PRICE
LIMIT 20;
