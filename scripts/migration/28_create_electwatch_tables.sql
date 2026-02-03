-- =============================================================================
-- ElectWatch BigQuery Tables
-- Dataset: justdata-ncrc.electwatch
-- 
-- This script creates all tables needed for the ElectWatch application.
-- Run with: bq query --use_legacy_sql=false < 28_create_electwatch_tables.sql
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. OFFICIALS - Congress members with summary statistics
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE `justdata-ncrc.electwatch.officials` (
  -- Primary key
  bioguide_id STRING NOT NULL OPTIONS(description="Congress.gov Bioguide ID"),
  
  -- Basic info
  name STRING,
  party STRING,
  state STRING,
  district STRING,
  chamber STRING,  -- 'house' or 'senate'
  photo_url STRING,
  website_url STRING,
  years_in_congress INT64,
  first_elected INT64,
  
  -- External identifiers
  fec_candidate_id STRING,
  fec_committee_id STRING,
  opensecrets_id STRING,
  govtrack_id INT64,
  
  -- Trading summary (aggregated from official_trades)
  total_trades INT64,
  purchase_count INT64,
  sale_count INT64,
  stock_trades_min FLOAT64,
  stock_trades_max FLOAT64,
  stock_trades_display STRING,
  purchases_display STRING,
  sales_display STRING,
  trade_score FLOAT64,
  symbols_traded ARRAY<STRING>,
  
  -- PAC contribution summary
  contributions FLOAT64,
  pac_contributions FLOAT64,
  financial_sector_pac FLOAT64,
  financial_pac_pct FLOAT64,
  
  -- Individual contribution summary
  individual_contributions_total FLOAT64,
  individual_financial_total FLOAT64,
  individual_financial_pct FLOAT64,
  
  -- Scoring
  involvement_score FLOAT64,
  financial_sector_score FLOAT64,
  
  -- Committee assignments
  committees ARRAY<STRING>,
  is_finance_committee BOOL,
  
  -- Top donors/PACs (denormalized for dashboard)
  top_financial_pacs ARRAY<STRUCT<name STRING, amount FLOAT64, sector STRING>>,
  top_individual_financial ARRAY<STRUCT<
    name STRING,
    employer STRING,
    occupation STRING,
    amount FLOAT64,
    date STRING,
    city STRING,
    state STRING
  >>,
  top_industries ARRAY<STRUCT<name STRING, amount FLOAT64>>,
  
  -- Wealth info
  net_worth STRUCT<
    min FLOAT64,
    max FLOAT64,
    source STRING,
    year INT64
  >,
  wealth_tier STRING,
  
  -- Activity flags
  has_financial_activity BOOL,
  
  -- Metadata
  updated_at TIMESTAMP
)
CLUSTER BY bioguide_id, state, party
OPTIONS(
  description="Congress members tracked by ElectWatch with aggregated financial activity"
);

-- -----------------------------------------------------------------------------
-- 2. OFFICIAL_TRADES - Individual stock trades (STOCK Act disclosures)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE `justdata-ncrc.electwatch.official_trades` (
  -- Composite key
  id STRING NOT NULL OPTIONS(description="Unique trade ID"),
  bioguide_id STRING NOT NULL,
  
  -- Trade details
  ticker STRING,
  company STRING,
  trade_type STRING,  -- 'purchase', 'sale'
  amount_min FLOAT64,
  amount_max FLOAT64,
  amount_display STRING,
  
  -- Dates
  transaction_date DATE,
  disclosure_date DATE,
  
  -- Additional info
  owner STRING,  -- 'Self', 'Spouse', 'Dependent'
  asset_type STRING,
  capital_gains BOOL,
  filing_url STRING,
  source STRING,  -- 'fmp', 'quiver', etc.
  
  -- Metadata
  updated_at TIMESTAMP
)
PARTITION BY transaction_date
CLUSTER BY bioguide_id, ticker
OPTIONS(
  description="Individual stock trades from STOCK Act disclosures"
);

-- -----------------------------------------------------------------------------
-- 3. OFFICIAL_PAC_CONTRIBUTIONS - PAC contributions to officials
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE `justdata-ncrc.electwatch.official_pac_contributions` (
  id STRING NOT NULL,
  bioguide_id STRING NOT NULL,
  
  -- PAC info
  committee_id STRING,
  committee_name STRING,
  
  -- Contribution details
  amount FLOAT64,
  contribution_date DATE,
  
  -- Classification
  sector STRING,
  sub_sector STRING,
  is_financial BOOL,
  
  -- Metadata
  updated_at TIMESTAMP
)
CLUSTER BY bioguide_id, committee_name
OPTIONS(
  description="PAC contributions to congressional officials"
);

-- -----------------------------------------------------------------------------
-- 4. OFFICIAL_INDIVIDUAL_CONTRIBUTIONS - Individual contributions
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE `justdata-ncrc.electwatch.official_individual_contributions` (
  id STRING NOT NULL,
  bioguide_id STRING NOT NULL,
  
  -- Contributor info
  contributor_name STRING,
  employer STRING,
  occupation STRING,
  city STRING,
  state STRING,
  
  -- Contribution details
  amount FLOAT64,
  contribution_date DATE,
  
  -- Classification
  sector STRING,
  is_financial BOOL,
  match_reason STRING,  -- 'employer', 'occupation', etc.
  
  -- Metadata
  updated_at TIMESTAMP
)
CLUSTER BY bioguide_id, employer
OPTIONS(
  description="Individual contributions to congressional officials"
);

-- -----------------------------------------------------------------------------
-- 5. FIRMS - Companies/stocks tracked
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE `justdata-ncrc.electwatch.firms` (
  ticker STRING NOT NULL,
  name STRING,
  sector STRING,
  industry STRING,
  
  -- Aggregated stats
  officials_count INT64,
  trade_count INT64,
  total_value_min FLOAT64,
  total_value_max FLOAT64,
  purchase_count INT64,
  sale_count INT64,
  
  -- Market data (from Finnhub)
  quote STRUCT<
    current_price FLOAT64,
    change FLOAT64,
    change_percent FLOAT64,
    high FLOAT64,
    low FLOAT64,
    open FLOAT64,
    previous_close FLOAT64,
    timestamp INT64
  >,
  
  -- Officials who traded (denormalized for queries)
  officials ARRAY<STRUCT<
    bioguide_id STRING,
    name STRING,
    party STRING,
    state STRING,
    chamber STRING,
    photo_url STRING
  >>,
  
  -- Metadata
  updated_at TIMESTAMP
)
CLUSTER BY ticker, sector
OPTIONS(
  description="Companies/stocks tracked in ElectWatch"
);

-- -----------------------------------------------------------------------------
-- 6. INDUSTRIES - Sector aggregations
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE `justdata-ncrc.electwatch.industries` (
  sector STRING NOT NULL,
  name STRING,
  description STRING,
  color STRING,
  
  -- Aggregated stats
  firms_count INT64,
  officials_count INT64,
  total_trades INT64,
  total_value_min FLOAT64,
  total_value_max FLOAT64,
  
  -- Top firms in this industry
  top_firms ARRAY<STRUCT<
    ticker STRING,
    name STRING,
    total FLOAT64,
    officials_count INT64,
    trade_count INT64
  >>,
  
  -- Metadata
  updated_at TIMESTAMP
)
CLUSTER BY sector
OPTIONS(
  description="Financial industry/sector aggregations"
);

-- -----------------------------------------------------------------------------
-- 7. COMMITTEES - Congressional committees
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE `justdata-ncrc.electwatch.committees` (
  id STRING NOT NULL,
  name STRING,
  full_name STRING,
  chamber STRING,
  chair STRING,
  ranking_member STRING,
  members_count INT64,
  jurisdiction STRING,
  
  -- Metadata
  updated_at TIMESTAMP
)
CLUSTER BY chamber
OPTIONS(
  description="Congressional committees relevant to financial oversight"
);

-- -----------------------------------------------------------------------------
-- 8. NEWS - News articles
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE `justdata-ncrc.electwatch.news` (
  id STRING NOT NULL,
  title STRING,
  url STRING,
  source STRING,
  published_date DATE,
  summary STRING,
  
  -- Related entities
  tickers ARRAY<STRING>,
  officials ARRAY<STRING>,
  
  -- Metadata
  fetched_at TIMESTAMP
)
PARTITION BY published_date
CLUSTER BY source
OPTIONS(
  description="News articles related to congressional financial activity"
);

-- -----------------------------------------------------------------------------
-- 9. INSIGHTS - AI-generated pattern insights
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE `justdata-ncrc.electwatch.insights` (
  id STRING NOT NULL,
  title STRING,
  summary STRING,
  detailed_summary STRING,
  evidence STRING,
  category STRING,  -- 'concentration', 'party_balance', 'committee', 'timing'
  severity STRING,  -- 'high', 'medium', 'low'
  
  -- Related entities (denormalized)
  officials ARRAY<STRUCT<
    id STRING,
    name STRING,
    party STRING,
    state STRING,
    amount FLOAT64,
    detail STRING
  >>,
  
  industries ARRAY<STRUCT<
    code STRING,
    name STRING,
    amount FLOAT64,
    detail STRING
  >>,
  
  firms ARRAY<STRUCT<
    ticker STRING,
    name STRING,
    amount FLOAT64,
    detail STRING
  >>,
  
  committees ARRAY<STRUCT<
    id STRING,
    name STRING,
    detail STRING
  >>,
  
  sources ARRAY<STRUCT<
    title STRING,
    url STRING,
    source STRING,
    date STRING
  >>,
  
  -- Metadata
  generated_at TIMESTAMP
)
CLUSTER BY category, severity
OPTIONS(
  description="AI-generated insights about financial patterns"
);

-- -----------------------------------------------------------------------------
-- 10. METADATA - Update metadata (one row per update)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE `justdata-ncrc.electwatch.metadata` (
  id STRING NOT NULL,  -- 'current' or ISO date
  status STRING,
  last_updated TIMESTAMP,
  last_updated_display STRING,
  
  -- Data windows
  data_window_start DATE,
  data_window_end DATE,
  stock_data_window_start DATE,
  stock_data_window_end DATE,
  fec_data_window_start DATE,
  fec_data_window_end DATE,
  
  -- Next update
  next_update TIMESTAMP,
  next_update_display STRING,
  
  -- Data source status
  data_sources JSON,
  
  -- Counts
  officials_count INT64,
  firms_count INT64,
  industries_count INT64,
  committees_count INT64,
  news_count INT64,
  
  -- Errors/warnings
  errors ARRAY<STRING>,
  warnings ARRAY<STRING>
)
OPTIONS(
  description="Metadata about ElectWatch data updates"
);

-- -----------------------------------------------------------------------------
-- 11. TREND_SNAPSHOTS - Historical time-series data
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE `justdata-ncrc.electwatch.trend_snapshots` (
  snapshot_date DATE NOT NULL,
  bioguide_id STRING NOT NULL,
  
  -- Official name (for reference)
  name STRING,
  
  -- Snapshot metrics
  finance_pct FLOAT64,
  total_contributions FLOAT64,
  finance_contributions FLOAT64,
  stock_buys FLOAT64,
  stock_sells FLOAT64,
  
  -- Metadata
  created_at TIMESTAMP
)
PARTITION BY snapshot_date
CLUSTER BY bioguide_id
OPTIONS(
  description="Weekly snapshots of official financial metrics for trend analysis"
);

-- -----------------------------------------------------------------------------
-- 12. AI_SUMMARIES - AI-generated text summaries
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TABLE `justdata-ncrc.electwatch.summaries` (
  id STRING NOT NULL,  -- 'current' or ISO date
  
  weekly_overview STRING,
  top_movers STRING,
  industry_highlights STRING,
  status STRING,
  
  generated_at TIMESTAMP
)
OPTIONS(
  description="AI-generated summary texts for dashboard"
);

-- =============================================================================
-- INDEXES AND VIEWS
-- =============================================================================

-- View: Active officials with financial activity
CREATE OR REPLACE VIEW `justdata-ncrc.electwatch.v_active_officials` AS
SELECT *
FROM `justdata-ncrc.electwatch.officials`
WHERE has_financial_activity = TRUE
ORDER BY involvement_score DESC;

-- View: Recent trades (last 90 days)
CREATE OR REPLACE VIEW `justdata-ncrc.electwatch.v_recent_trades` AS
SELECT 
  t.*,
  o.name AS official_name,
  o.party,
  o.state,
  o.chamber,
  o.photo_url
FROM `justdata-ncrc.electwatch.official_trades` t
JOIN `justdata-ncrc.electwatch.officials` o ON t.bioguide_id = o.bioguide_id
WHERE t.transaction_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
ORDER BY t.transaction_date DESC;

-- View: Top financial sector PAC recipients
CREATE OR REPLACE VIEW `justdata-ncrc.electwatch.v_top_pac_recipients` AS
SELECT 
  bioguide_id,
  name,
  party,
  state,
  chamber,
  financial_sector_pac,
  financial_pac_pct,
  pac_contributions
FROM `justdata-ncrc.electwatch.officials`
WHERE financial_sector_pac > 0
ORDER BY financial_sector_pac DESC
LIMIT 100;

-- =============================================================================
-- Grant access to service account
-- =============================================================================
-- Run these in Cloud Console or with bq command:
-- GRANT `roles/bigquery.dataViewer` ON DATASET `justdata-ncrc.electwatch` 
--   TO "serviceAccount:electwatch@justdata-ncrc.iam.gserviceaccount.com";
-- GRANT `roles/bigquery.dataEditor` ON DATASET `justdata-ncrc.electwatch`
--   TO "serviceAccount:electwatch@justdata-ncrc.iam.gserviceaccount.com";
