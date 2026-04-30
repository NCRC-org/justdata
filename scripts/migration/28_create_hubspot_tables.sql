-- Migration: Create HubSpot sync tables in BigQuery
-- Dataset: justdata-ncrc.hubspot
--
-- These tables are populated daily by the hubspot-daily-sync Cloud Run Job.
-- They mirror HubSpot CRM data for fast membership lookups and analytics joins.
--
-- Usage: Run each statement in BigQuery console or via:
--   bq query --use_legacy_sql=false < scripts/migration/28_create_hubspot_tables.sql

-- ============================================================================
-- 1. Create hubspot dataset if it doesn't exist
-- ============================================================================
-- Run manually in BigQuery console:
-- CREATE SCHEMA IF NOT EXISTS `justdata-ncrc.hubspot` OPTIONS(location="US");

-- ============================================================================
-- 2. Create companies table
-- ============================================================================
CREATE TABLE IF NOT EXISTS `justdata-ncrc.hubspot.companies` (
    hubspot_company_id STRING NOT NULL,
    name STRING,
    domain STRING,
    membership_status STRING,
    current_membership_status STRING,
    street_address STRING,
    street_address_2 STRING,
    city STRING,
    state STRING,
    postal_code STRING,
    country STRING,
    industry STRING,
    phone STRING,
    latitude FLOAT64,
    longitude FLOAT64,
    synced_at TIMESTAMP NOT NULL
);

-- ============================================================================
-- 3. Create contacts table
-- ============================================================================
CREATE TABLE IF NOT EXISTS `justdata-ncrc.hubspot.contacts` (
    hubspot_contact_id STRING NOT NULL,
    email STRING,
    firstname STRING,
    lastname STRING,
    company_name STRING,
    hubspot_company_id STRING,
    membership_status STRING,
    jobtitle STRING,
    phone STRING,
    synced_at TIMESTAMP NOT NULL
);

-- ============================================================================
-- 4. Useful views for common queries
-- ============================================================================

-- View: Active members (for membership lookup at login)
CREATE OR REPLACE VIEW `justdata-ncrc.hubspot.active_members` AS
SELECT
    c.hubspot_contact_id,
    c.email,
    c.firstname,
    c.lastname,
    c.company_name,
    c.hubspot_company_id,
    c.membership_status,
    co.name AS company_name_from_company,
    co.domain AS company_domain
FROM `justdata-ncrc.hubspot.contacts` c
LEFT JOIN `justdata-ncrc.hubspot.companies` co
    ON c.hubspot_company_id = co.hubspot_company_id
WHERE UPPER(TRIM(c.membership_status)) IN (
    'CURRENT', 'GRACE PERIOD', 'LIFETIME MEMBER',
    'NATIONAL PARTNER', 'RECIPROCAL'
);

-- View: Active member companies
CREATE OR REPLACE VIEW `justdata-ncrc.hubspot.active_companies` AS
SELECT
    hubspot_company_id,
    name,
    domain,
    membership_status,
    current_membership_status,
    city,
    state,
    country,
    industry
FROM `justdata-ncrc.hubspot.companies`
WHERE UPPER(TRIM(membership_status)) IN (
    'CURRENT', 'GRACE PERIOD', 'LIFETIME MEMBER',
    'NATIONAL PARTNER', 'RECIPROCAL'
);

-- View: JustData users not in HubSpot (marketing targets)
CREATE OR REPLACE VIEW `justdata-ncrc.hubspot.justdata_users_not_in_hubspot` AS
SELECT DISTINCT
    u.user_email,
    u.user_type,
    COUNT(*) AS total_reports,
    MAX(u.timestamp) AS last_activity,
    MIN(u.timestamp) AS first_activity,
    STRING_AGG(DISTINCT u.app_name, ', ') AS tools_used
FROM `justdata-ncrc.cache.usage_log` u
LEFT JOIN `justdata-ncrc.hubspot.contacts` h
    ON LOWER(u.user_email) = LOWER(h.email)
WHERE h.email IS NULL
    AND u.user_email IS NOT NULL
    AND u.error_message IS NULL
    AND LOWER(SPLIT(u.user_email, '@')[OFFSET(1)]) NOT IN (
        'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
        'aol.com', 'icloud.com', 'me.com', 'mac.com',
        'protonmail.com', 'proton.me', 'live.com', 'msn.com',
        'comcast.net', 'verizon.net', 'att.net', 'sbcglobal.net',
        'ymail.com', 'rocketmail.com', 'mail.com', 'zoho.com',
        'fastmail.com', 'tutanota.com', 'hey.com', 'pm.me',
        'googlemail.com', 'earthlink.net', 'cox.net', 'charter.net',
        'optonline.net', 'frontier.com', 'windstream.net'
    )
GROUP BY u.user_email, u.user_type
ORDER BY total_reports DESC;

-- ============================================================================
-- 5. Verify setup
-- ============================================================================
SELECT table_name, table_type
FROM `justdata-ncrc.hubspot.INFORMATION_SCHEMA.TABLES`
ORDER BY table_name;
