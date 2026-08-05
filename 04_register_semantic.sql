-- ============================================================
-- 04_register_semantic.sql — prep for Cortex Analyst
-- Run: snow sql -f 04_register_semantic.sql --connection messe
--
-- Cortex Analyst can read a semantic model YAML directly off a stage
-- (no separate "registration" object needed for this path — the
-- newer SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML / native Semantic View
-- flow is recommended for production but the stage-YAML path is
-- still fully supported and is the fastest path for a demo).
-- Source: https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst
-- ============================================================

USE DATABASE MESSE;
USE WAREHOUSE MESSE_WH;

-- MESSE_STAGE already exists (from 01_schema.sql) but wasn't created
-- with DIRECTORY enabled, which Snowsight's file picker needs to list
-- files on the stage. Add it.
ALTER STAGE RAW.MESSE_STAGE SET DIRECTORY = (ENABLE = TRUE);

-- Cortex Analyst requires this role (or CORTEX_USER) on whichever
-- role will query it. ACCOUNTADMIN should already have broad grants,
-- but this makes it explicit.
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_ANALYST_USER TO ROLE ACCOUNTADMIN;

-- Refresh the stage's file listing after upload.
ALTER STAGE RAW.MESSE_STAGE REFRESH;

SELECT * FROM DIRECTORY(@RAW.MESSE_STAGE) WHERE RELATIVE_PATH ILIKE '%.yaml';
