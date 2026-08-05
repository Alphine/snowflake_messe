-- ============================================================
-- MESSE x Snowflake CoCo CLI Hackathon 2026
-- 01_schema.sql — database, schemas, raw + dim tables
-- Run: snow sql -f 01_schema.sql
--
-- REVISION NOTE (2026-08-05): original SDD assumed a SQLite export
-- with RAW.DAILY_PRICE / RAW.BROKER_SUMMARY (per-broker buy/sell).
-- Inspection of the real MESSE source (MySQL db `u808021404_messe`,
-- schema at scoring-saham/public_html/db/schema.sql) showed NO
-- broker-level transaction data exists anywhere in the product —
-- MESSE only stores OHLCV (`market_data`) and its own precomputed
-- multi-factor scores (`expert_scores`, `stock_scores`). There is
-- no IDX/KSEI broker summary feed. RAW.BROKER_SUMMARY and DIM.BROKER
-- are dropped; the bandar score in 03_transforms.sql is rebuilt from
-- MESSE's own accumulation/distribution/volume factor scores instead
-- of broker net-flow. This is a real scope change, not a naming fix
-- — see README "Known gaps" for the honesty framing.
-- ============================================================

CREATE DATABASE IF NOT EXISTS MESSE;
USE DATABASE MESSE;

CREATE SCHEMA IF NOT EXISTS RAW;    -- landing, as-ingested
CREATE SCHEMA IF NOT EXISTS DIM;    -- reference / master data
CREATE SCHEMA IF NOT EXISTS MART;   -- derived signals, serving layer

CREATE WAREHOUSE IF NOT EXISTS MESSE_WH
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE
  INITIALLY_SUSPENDED = TRUE;

USE WAREHOUSE MESSE_WH;

-- ------------------------------------------------------------
-- Internal stage for CSV upload from MESSE (MySQL export)
-- ------------------------------------------------------------
CREATE STAGE IF NOT EXISTS RAW.MESSE_STAGE
  FILE_FORMAT = (
    TYPE = CSV
    FIELD_DELIMITER = ','
    SKIP_HEADER = 1
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    NULL_IF = ('', 'NULL', 'null', 'NaN')
    EMPTY_FIELD_AS_NULL = TRUE
  );

-- ------------------------------------------------------------
-- RAW: daily OHLCV per emiten (from MESSE `market_data`, sourced
-- from Yahoo Finance by MESSE's own collector — see
-- data/dataCollector.php). No prev_close / frequency columns exist
-- in MESSE; prev_close is derived via LAG in 03_transforms.sql.
-- VALUE_IDR is NOT trustworthy from MESSE (`value` column is stored
-- as 0 in production) — recomputed on export as close * volume.
-- ------------------------------------------------------------
CREATE OR REPLACE TABLE RAW.MARKET_DATA (
    TICKER          VARCHAR(10)   NOT NULL,
    TRADE_DATE      DATE          NOT NULL,
    OPEN_PRICE      NUMBER(18,4),
    HIGH_PRICE      NUMBER(18,4),
    LOW_PRICE       NUMBER(18,4),
    CLOSE_PRICE     NUMBER(18,4),
    VOLUME_SHARES   NUMBER(38,0),
    VALUE_IDR       NUMBER(38,0),   -- recomputed = close * volume, see 02_load.sql
    CONSTRAINT PK_MARKET_DATA PRIMARY KEY (TICKER, TRADE_DATE)
);

-- ------------------------------------------------------------
-- RAW: MESSE's own per-factor expert scores (from `expert_scores`).
-- These are precomputed price/volume-pattern heuristics, NOT raw
-- broker order flow. Used as the bandarmologi proxy input.
-- ------------------------------------------------------------
CREATE OR REPLACE TABLE RAW.EXPERT_SCORES (
    TICKER               VARCHAR(10) NOT NULL,
    TRADE_DATE           DATE        NOT NULL,
    ACCUMULATION_SCORE    NUMBER(5,2),
    DISTRIBUTION_SCORE    NUMBER(5,2),
    VOLUME_SCORE          NUMBER(5,2),
    LIQUIDITY_SCORE       NUMBER(5,2),
    VOLATILITY_SCORE      NUMBER(5,2),
    CONSTRAINT PK_EXPERT_SCORES PRIMARY KEY (TICKER, TRADE_DATE)
);

-- ------------------------------------------------------------
-- RAW: MESSE's own final composite scores (from `stock_scores`).
-- BANDAR_SIGNAL / SMART_MONEY_LABEL are MESSE's existing labels,
-- kept for cross-reference in the demo but NOT used as the primary
-- signal — many rows have these NULL / default (score not run for
-- that ticker/day), so they are not reliable enough alone.
-- ------------------------------------------------------------
CREATE OR REPLACE TABLE RAW.STOCK_SCORES (
    TICKER              VARCHAR(10) NOT NULL,
    TRADE_DATE          DATE        NOT NULL,
    FINAL_SCORE          NUMBER(5,2),
    SIGNAL                VARCHAR(20),
    MESSE_BANDAR_SCORE    NUMBER(5,2),
    MESSE_BANDAR_SIGNAL   VARCHAR(50),
    MESSE_SMART_MONEY_LABEL VARCHAR(20),
    CONSTRAINT PK_STOCK_SCORES PRIMARY KEY (TICKER, TRADE_DATE)
);

-- ------------------------------------------------------------
-- DIM: emiten master (from MESSE `stocks`). LISTED_SHARES and
-- FREE_FLOAT_PCT are not tracked by MESSE — NULL unless backfilled
-- manually in the seed CSV for known LQ45 names.
-- ------------------------------------------------------------
CREATE OR REPLACE TABLE DIM.EMITEN (
    TICKER          VARCHAR(10) NOT NULL PRIMARY KEY,
    COMPANY_NAME    VARCHAR(300),
    SECTOR          VARCHAR(100),
    SUB_SECTOR      VARCHAR(100),
    LISTED_SHARES   NUMBER(38,0),
    FREE_FLOAT_PCT  NUMBER(9,4),
    IS_LQ45         BOOLEAN DEFAULT FALSE,
    IS_ACTIVE       BOOLEAN DEFAULT TRUE
);

-- ------------------------------------------------------------
-- DIM: IHSG / index level (context for relative strength).
-- Not populated by MESSE either — left in schema for future use,
-- not required for the acceptance criteria in this SDD.
-- ------------------------------------------------------------
CREATE OR REPLACE TABLE RAW.INDEX_DAILY (
    INDEX_CODE   VARCHAR(20) NOT NULL,
    TRADE_DATE   DATE        NOT NULL,
    CLOSE_LEVEL  NUMBER(18,4),
    VOLUME_SHARES NUMBER(38,0),
    VALUE_IDR    NUMBER(38,0),
    CONSTRAINT PK_INDEX_DAILY PRIMARY KEY (INDEX_CODE, TRADE_DATE)
);
