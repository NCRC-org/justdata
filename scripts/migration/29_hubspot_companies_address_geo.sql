-- Migration: Add street address + geocoded coordinates to hubspot.companies
-- Run in BigQuery console if the table was created before address columns existed.

ALTER TABLE `justdata-ncrc.hubspot.companies`
ADD COLUMN IF NOT EXISTS street_address STRING;

ALTER TABLE `justdata-ncrc.hubspot.companies`
ADD COLUMN IF NOT EXISTS street_address_2 STRING;

ALTER TABLE `justdata-ncrc.hubspot.companies`
ADD COLUMN IF NOT EXISTS postal_code STRING;

ALTER TABLE `justdata-ncrc.hubspot.companies`
ADD COLUMN IF NOT EXISTS latitude FLOAT64;

ALTER TABLE `justdata-ncrc.hubspot.companies`
ADD COLUMN IF NOT EXISTS longitude FLOAT64;

-- If an old table had `city` without postal_code, postal_code is new; `city`/`state` unchanged.
