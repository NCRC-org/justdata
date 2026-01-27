-- JustData Workflow Tables
-- Dataset: justdata
-- Run via: python -m justdata.apps.workflow.schema.run_migration

-- Main tasks table
CREATE TABLE IF NOT EXISTS `{PROJECT_ID}.justdata.workflow_tasks` (
  id STRING NOT NULL,
  title STRING NOT NULL,
  type STRING NOT NULL,
  priority STRING NOT NULL,
  status STRING DEFAULT 'open',
  app STRING,
  notes STRING,
  dependencies ARRAY<STRING>,
  is_collector BOOL DEFAULT FALSE,
  is_goal BOOL DEFAULT FALSE,
  collector_for STRING,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  created_by STRING,
  completed_at TIMESTAMP,
  completed_by STRING
)
OPTIONS (
  description = 'Workflow tasks for JustData project management'
);

-- Positions table (shared layout across all admin users)
CREATE TABLE IF NOT EXISTS `{PROJECT_ID}.justdata.workflow_positions` (
  task_id STRING NOT NULL,
  x FLOAT64 NOT NULL,
  y FLOAT64 NOT NULL,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_by STRING
)
OPTIONS (
  description = 'Node positions for workflow visualization'
);

-- Task ID counter for auto-generation
CREATE TABLE IF NOT EXISTS `{PROJECT_ID}.justdata.workflow_task_counter` (
  counter_name STRING NOT NULL,
  current_value INT64 NOT NULL
)
OPTIONS (
  description = 'Counter for auto-generating task IDs'
);
