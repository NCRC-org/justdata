-- Create AI usage tracking table
-- Run with: bq query --project_id=justdata-ncrc --use_legacy_sql=false < scripts/migration/12_create_ai_usage_table.sql

CREATE TABLE IF NOT EXISTS `justdata-ncrc.firebase_analytics.ai_usage` (
    timestamp STRING,
    provider STRING,
    model STRING,
    input_tokens INT64,
    output_tokens INT64,
    total_tokens INT64,
    input_cost_usd FLOAT64,
    output_cost_usd FLOAT64,
    total_cost_usd FLOAT64,
    app_name STRING,
    report_type STRING
);
