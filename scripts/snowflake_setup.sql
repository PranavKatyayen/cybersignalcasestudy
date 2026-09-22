-- CyberSignal: Snowflake setup (safe to re-run)

CREATE WAREHOUSE IF NOT EXISTS CYBERSIGNAL_WH
  WITH WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60          -- suspend after 60s idle
  AUTO_RESUME = TRUE
  INITIALLY_SUSPENDED = TRUE;

CREATE DATABASE IF NOT EXISTS CYBERSIGNAL;

USE DATABASE CYBERSIGNAL;

CREATE SCHEMA IF NOT EXISTS RAW;
CREATE SCHEMA IF NOT EXISTS STAGING;   -- dbt staging models land here
CREATE SCHEMA IF NOT EXISTS ANALYTICS; -- dbt marts (gold layer) land here

USE SCHEMA RAW;

-- Raw table for curated scored entities coming out of the local Python ETL
CREATE TABLE IF NOT EXISTS RAW.SCORED_ENTITIES (
    entity_key              STRING,
    attribution_confidence  STRING,
    provider_roles          VARIANT,   -- array, stored as semi-structured
    attribution_reasons     VARIANT,
    total_score              NUMBER,
    asset_count               NUMBER,
    orgs                      VARIANT,
    countries                 VARIANT,
    sample_ips                VARIANT,
    top_findings              VARIANT,
    loaded_at                 TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- One row per individual scored asset (the evidence detail behind each entity's top_findings)
CREATE TABLE IF NOT EXISTS RAW.SCORED_ASSETS (
    entity_key              STRING,
    attribution_confidence  STRING,
    provider_role           STRING,
    attribution_reason      STRING,
    org                      STRING,
    domain                   STRING,
    ip                       STRING,
    port                     NUMBER,
    product                  STRING,
    country                  STRING,
    raw_score                NUMBER,
    adjusted_score           NUMBER,
    findings                 VARIANT,
    tags                     VARIANT,
    loaded_at                TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- One row per entity's pre-generated risk narrative (see scripts/generate_narratives.py)
CREATE TABLE IF NOT EXISTS RAW.ENTITY_NARRATIVES (
    entity_key                STRING,
    summary                    STRING,
    outreach_angle              STRING,
    cited_evidence_indices       VARIANT,
    narrative_source              STRING,
    loaded_at                     TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Which model wrote each narrative, and with which prompt version
ALTER TABLE RAW.ENTITY_NARRATIVES ADD COLUMN IF NOT EXISTS provider STRING;
ALTER TABLE RAW.ENTITY_NARRATIVES ADD COLUMN IF NOT EXISTS model STRING;
ALTER TABLE RAW.ENTITY_NARRATIVES ADD COLUMN IF NOT EXISTS prompt_version STRING;

-- File format + internal stage for loading the curated JSON output of the local pipeline
CREATE FILE FORMAT IF NOT EXISTS RAW.JSON_FORMAT
  TYPE = 'JSON'
  STRIP_OUTER_ARRAY = FALSE;

CREATE STAGE IF NOT EXISTS RAW.CURATED_STAGE
  FILE_FORMAT = RAW.JSON_FORMAT;

-- Sanity check
SHOW WAREHOUSES LIKE 'CYBERSIGNAL_WH';
SHOW DATABASES LIKE 'CYBERSIGNAL';
