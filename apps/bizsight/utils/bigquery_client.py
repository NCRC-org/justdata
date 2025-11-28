#!/usr/bin/env python3
"""
BigQuery Client for BizSight
Self-contained BigQuery client for small business lending data.
"""

from google.cloud import bigquery
from google.oauth2 import service_account
from pathlib import Path
import os
import logging

logger = logging.getLogger(__name__)


def get_bigquery_client(project_id: str = None, credentials_path: str = None):
    """
    Get a BigQuery client instance.
    
    Args:
        project_id: GCP project ID (defaults to env var)
        credentials_path: Path to service account JSON (defaults to env var)
    
    Returns:
        BigQuery client instance
    """
    if not project_id:
        project_id = os.getenv('GCP_PROJECT_ID', 'hdma1-242116')
    
    # Try to find credentials file (like shared BigQuery client does)
    cred_path = None
    base_dir = Path(__file__).parent.parent
    possible_paths = [
        # Actual workspace location (primary)
        Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\DREAM Analysis\config\credentials\hdma1-242116-74024e2eb88f.json"),
        # C:\DREAM locations (common workspace location)
        Path('C:/DREAM/config/credentials/hdma1-242116-74024e2eb88f.json'),
        Path('C:/DREAM/hdma1-242116-74024e2eb88f.json'),
        # Local credentials directory
        base_dir / 'credentials' / 'bigquery_service_account.json',
        base_dir / 'credentials' / 'hdma1-242116-74024e2eb88f.json',
        # Relative paths
        Path('config/credentials/hdma1-242116-74024e2eb88f.json'),
        Path('hdma1-242116-74024e2eb88f.json'),
        # Root workspace locations
        Path(__file__).parent.parent.parent.parent / 'config' / 'credentials' / 'hdma1-242116-74024e2eb88f.json',
        Path(__file__).parent.parent.parent.parent / 'credentials' / 'hdma1-242116-74024e2eb88f.json',
    ]
    
    # Also check if C:\DREAM\config\credentials exists and search for any hdma1-*.json files
    cred_dir = Path('C:/DREAM/config/credentials')
    if cred_dir.exists():
        for json_file in cred_dir.glob('hdma1-*.json'):
            if json_file not in possible_paths:
                possible_paths.append(json_file)
    
    # First, check if credentials_path is provided and exists
    if credentials_path and os.path.exists(credentials_path):
        cred_path = Path(credentials_path)
        logger.info(f"Using provided credentials: {cred_path}")
    # Check environment variable
    elif os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        env_cred_path = Path(os.getenv('GOOGLE_APPLICATION_CREDENTIALS'))
        if env_cred_path.exists():
            cred_path = env_cred_path
            logger.info(f"Using credentials from environment: {cred_path}")
        else:
            logger.warning(f"GOOGLE_APPLICATION_CREDENTIALS points to non-existent file: {env_cred_path}")
    
    # If not found yet, search common locations (like shared client)
    if not cred_path or not cred_path.exists():
        for path in possible_paths:
            if path.exists():
                cred_path = path
                logger.info(f"Found credentials at: {cred_path}")
                break
    
    # Initialize client with credentials if found
    try:
        if cred_path and cred_path.exists():
            # Use explicit credentials loading (like shared client)
            credentials = service_account.Credentials.from_service_account_file(str(cred_path))
            client = bigquery.Client(credentials=credentials, project=project_id)
            logger.info(f"BigQuery client initialized for project: {project_id} using credentials: {cred_path}")
            return client
        else:
            # Fallback: try default service account (for cloud deployments)
            logger.warning("No credentials file found, trying default service account...")
            logger.warning("Tried locations:")
            for path in possible_paths:
                logger.warning(f"  - {path}")
            client = bigquery.Client(project=project_id)
            logger.info(f"BigQuery client initialized for project: {project_id} using default credentials")
            return client
    except Exception as e:
        logger.error(f"Failed to initialize BigQuery client: {e}")
        # Try one more time with default credentials
        try:
            logger.info("Attempting to use default application credentials...")
            client = bigquery.Client(project=project_id)
            return client
        except Exception as e2:
            logger.error(f"Error with default credentials: {e2}")
            return None


class BigQueryClient:
    """Wrapper class for BigQuery operations."""
    
    def __init__(self, project_id: str = None, credentials_path: str = None):
        """Initialize BigQuery client."""
        self.client = get_bigquery_client(project_id, credentials_path)
        self.project_id = project_id or os.getenv('GCP_PROJECT_ID', 'hdma1-242116')
        
        if self.client is None:
            raise RuntimeError("BigQuery client could not be initialized. Check credentials.")
    
    def query(self, sql: str, **kwargs):
        """Execute a BigQuery SQL query and return QueryJob."""
        return self.client.query(sql, **kwargs)
    
    def get_aggregate_data_with_census(self, geoid5: str, years: list = None):
        """
        Get aggregate (tract-level) small business lending data with census demographics.
        
        Args:
            geoid5: Single GEOID5 code (5-digit FIPS) for one county
            years: Optional list of years to filter
        
        Returns:
            Query job result with tract-level data and census demographics
        """
        geoid5_padded = str(geoid5).zfill(5)
        
        year_filter = ""
        if years:
            year_list = ", ".join(str(y) for y in years)
            year_filter = f"AND CAST(a.year AS INT64) IN ({year_list})"
        
        # Query without census table (table doesn't exist in BigQuery)
        # Use aggregate table fields directly if they exist, otherwise set defaults
        sql = f"""
        SELECT 
            a.*,
            g.county_state,
            g.county as county_name,
            g.state as state_name,
            g.geoid5,
            -- Use geoid10 from aggregate table as the census tract identifier
            CAST(a.geoid10 AS STRING) as census_tract_geoid,
            -- Calculate loan_count and loan_amount from num_* and amt_* fields (like disclosure table)
            COALESCE(a.num_under_100k, 0) + COALESCE(a.num_100k_250k, 0) + COALESCE(a.num_250k_1m, 0) as loan_count,
            COALESCE(a.amt_under_100k, 0) + COALESCE(a.amt_100k_250k, 0) + COALESCE(a.amt_250k_1m, 0) as loan_amount,
            -- Get census tract data from geo.census table (2025 FFIEC Census file)
            -- Join on geoid = geoid10
            -- Use income_level field from census (1=low ≤50%, 2=moderate ≤80%, 3=middle ≤120%, 4=upper >120%)
            -- Map to tract_to_msa_income_percentage using midpoints for each range
            CASE 
                WHEN c.income_level = 1 THEN 40.0  -- Low (≤50% AMI, use midpoint ~40%)
                WHEN c.income_level = 2 THEN 65.0   -- Moderate (≤80% AMI, use midpoint ~65%)
                WHEN c.income_level = 3 THEN 100.0 -- Middle (≤120% AMI, use midpoint ~100%)
                WHEN c.income_level = 4 THEN 150.0 -- Upper (>120% AMI, use midpoint ~150%)
                ELSE NULL
            END as tract_to_msa_income_percentage,
            -- Store the MSA median family income as tract median income
            COALESCE(c.msa_median_family_income, 0) as tract_median_income,
            -- Total population
            COALESCE(c.total_persons, 0) as tract_population,
            -- Calculate race percentages as share of total population
            SAFE_DIVIDE(COALESCE(c.total_white, 0), 
                       NULLIF(COALESCE(c.total_persons, 0), 0)) * 100 as tract_white_percent,
            SAFE_DIVIDE(COALESCE(c.total_black, 0), 
                       NULLIF(COALESCE(c.total_persons, 0), 0)) * 100 as tract_black_percent,
            SAFE_DIVIDE(COALESCE(c.total_hispanic, 0), 
                       NULLIF(COALESCE(c.total_persons, 0), 0)) * 100 as tract_hispanic_percent,
            SAFE_DIVIDE(COALESCE(c.total_asian, 0), 
                       NULLIF(COALESCE(c.total_persons, 0), 0)) * 100 as tract_asian_percent,
            SAFE_DIVIDE(COALESCE(c.total_ai_an, 0) + COALESCE(c.total_nh_opi, 0), 
                       NULLIF(COALESCE(c.total_persons, 0), 0)) * 100 as tract_other_race_percent,
            -- Calculate minority population percent: (total - white) / total * 100
            SAFE_DIVIDE(
                COALESCE(c.total_persons, 0) - COALESCE(c.total_white, 0),
                NULLIF(COALESCE(c.total_persons, 0), 0)
            ) * 100 as tract_minority_population_percent,
            -- Income classification using income_level field from census (2025 FFIEC Census)
            -- 1=low (≤50%), 2=moderate (≤80%), 3=middle (≤120%), 4=upper (>120%), else=unknown
            CASE 
                WHEN c.income_level = 1 THEN 'Low Income (≤50% AMI)'
                WHEN c.income_level = 2 THEN 'Moderate Income (≤80% AMI)'
                WHEN c.income_level = 3 THEN 'Middle Income (≤120% AMI)'
                WHEN c.income_level = 4 THEN 'Upper Income (>120% AMI)'
                ELSE 'Unknown Income'
            END as income_category,
            -- LMI flag (≤80% AMI) - income_level 1 or 2
            CASE WHEN c.income_level IN (1, 2) THEN 1 ELSE 0 END as is_lmi_tract,
            -- Include income_level field directly for easier filtering
            c.income_level as income_level
        FROM `{self.project_id}.sb.aggregate` a
        JOIN `{self.project_id}.geo.cbsa_to_county` g 
            ON LPAD(CAST(a.geoid5 AS STRING), 5, '0') = LPAD(CAST(g.geoid5 AS STRING), 5, '0')
        LEFT JOIN `{self.project_id}.geo.census` c
            ON CAST(a.geoid10 AS STRING) = CAST(c.geoid AS STRING)
        WHERE LPAD(CAST(g.geoid5 AS STRING), 5, '0') = '{geoid5_padded}'
            {year_filter}
        ORDER BY census_tract_geoid, a.year
        """
        
        return self.query(sql)
    
    def get_disclosure_data(self, geoid5: str, years: list = None):
        """
        Get disclosure (lender-level, county-level) small business lending data.
        
        Args:
            geoid5: Single GEOID5 code (5-digit FIPS) for one county
            years: Optional list of years to filter
        
        Returns:
            Query job result
        """
        geoid5_padded = str(geoid5).zfill(5)
        
        year_filter = ""
        if years:
            year_list = ", ".join(str(y) for y in years)
            year_filter = f"AND CAST(d.year AS INT64) IN ({year_list})"
        
        sql = f"""
        SELECT 
            d.*,
            l.sb_lender as lender_name,
            g.county_state,
            g.county as county_name,
            g.state as state_name,
            g.geoid5
        FROM `{self.project_id}.sb.disclosure` d
        JOIN `{self.project_id}.sb.lenders` l 
            ON d.respondent_id = l.sb_resid
        JOIN `{self.project_id}.geo.cbsa_to_county` g 
            ON LPAD(CAST(d.geoid5 AS STRING), 5, '0') = LPAD(CAST(g.geoid5 AS STRING), 5, '0')
        WHERE LPAD(CAST(g.geoid5 AS STRING), 5, '0') = '{geoid5_padded}'
            {year_filter}
        ORDER BY d.year, l.sb_lender
        """
        
        return self.query(sql)
    
    def get_lender_disclosure_data(self, 
                                   respondent_id: str = None, 
                                   lender_name: str = None,
                                   geoid5: str = None,
                                   years: list = None):
        """
        Get disclosure (lender-level) small business lending data with flexible filtering.
        
        Args:
            respondent_id: Optional respondent ID (sb_resid) to filter by specific lender
            lender_name: Optional lender name (partial match supported) to filter by lender
            geoid5: Optional GEOID5 code (5-digit FIPS) to filter by county
            years: Optional list of years to filter
        
        Returns:
            Query job result with lender-level disclosure data
        
        Examples:
            # Get all data for a specific lender by respondent_id
            bq_client.get_lender_disclosure_data(respondent_id='12345')
            
            # Get data for lenders matching a name pattern
            bq_client.get_lender_disclosure_data(lender_name='Chase')
            
            # Get data for a specific lender in a specific county
            bq_client.get_lender_disclosure_data(respondent_id='12345', geoid5='24031')
            
            # Get data for all lenders in a county for specific years
            bq_client.get_lender_disclosure_data(geoid5='24031', years=[2023, 2024])
        """
        where_conditions = []
        
        # Filter by respondent_id
        if respondent_id:
            where_conditions.append(f"d.respondent_id = '{respondent_id}'")
        
        # Filter by lender_name (case-insensitive partial match)
        if lender_name:
            where_conditions.append(f"UPPER(l.sb_lender) LIKE UPPER('%{lender_name}%')")
        
        # Filter by geoid5 (county)
        if geoid5:
            geoid5_padded = str(geoid5).zfill(5)
            where_conditions.append(f"LPAD(CAST(d.geoid5 AS STRING), 5, '0') = '{geoid5_padded}'")
        
        # Filter by years
        year_filter = ""
        if years:
            year_list = ", ".join(str(y) for y in years)
            year_filter = f"AND CAST(d.year AS INT64) IN ({year_list})"
        
        # Build WHERE clause
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        sql = f"""
        SELECT 
            d.*,
            l.sb_lender as lender_name,
            g.county_state,
            g.county as county_name,
            g.state as state_name,
            g.geoid5
        FROM `{self.project_id}.sb.disclosure` d
        JOIN `{self.project_id}.sb.lenders` l 
            ON d.respondent_id = l.sb_resid
        LEFT JOIN `{self.project_id}.geo.cbsa_to_county` g 
            ON LPAD(CAST(d.geoid5 AS STRING), 5, '0') = LPAD(CAST(g.geoid5 AS STRING), 5, '0')
        WHERE {where_clause}
            {year_filter}
        ORDER BY d.year, l.sb_lender, g.county_state
        """
        
        return self.query(sql)
    
    def get_lender_qualification_data(self, min_loans: int = 1000, years: list = None, max_rows: int = None, 
                                      exclude_credit_card: bool = True, min_avg_loan_amount: float = 10000):
        """
        Get lender disclosure data with qualification status.
        
        A lender "qualifies" if they have >= min_loans in consecutive years.
        This identifies lenders that consistently maintain high loan volumes.
        
        Args:
            min_loans: Minimum number of loans required for qualification (default: 1000)
            years: Optional list of years to filter (e.g., [2022, 2023, 2024])
            max_rows: Optional maximum number of rows to return (for testing/limiting)
            exclude_credit_card: If True, exclude lenders with average loan amount < min_avg_loan_amount (default: True)
            min_avg_loan_amount: Minimum average loan amount to include lender (default: 10000)
        
        Returns:
            Query job result with all disclosure records and qualification_status field
        
        Example:
            # Get all disclosure data with qualification status
            query_result = bq_client.get_lender_qualification_data(min_loans=1000)
            df = query_result.to_dataframe()
            
            # Get data for specific years only
            query_result = bq_client.get_lender_qualification_data(min_loans=1000, years=[2023, 2024])
        """
        # Build year filter
        year_filter = ""
        if years:
            year_list = ", ".join(str(y) for y in years)
            year_filter = f"AND CAST(d.year AS INT64) IN ({year_list})"
        
        # Build limit clause
        limit_clause = ""
        if max_rows:
            limit_clause = f"LIMIT {max_rows}"
        
        # Build credit card lender exclusion
        # Note: amounts are in thousands (000s), so $10,000 = 10
        credit_card_filter = ""
        if exclude_credit_card:
            # Convert min_avg_loan_amount from dollars to thousands
            min_avg_thousands = min_avg_loan_amount / 1000
            credit_card_filter = f"""
-- Exclude credit card lenders (average loan amount < ${min_avg_loan_amount:,.0f})
-- Note: amounts in disclosure table are in thousands (000s)
lender_avg_loan_amount AS (
  SELECT 
    d.respondent_id,
    -- Calculate average loan amount per lender across all years
    -- Amounts are in thousands, so result is also in thousands
    SAFE_DIVIDE(
      SUM(COALESCE(d.amt_under_100k, 0) + 
          COALESCE(d.amt_100k_250k, 0) + 
          COALESCE(d.amt_250k_1m, 0)),
      NULLIF(SUM(COALESCE(d.num_under_100k, 0) + 
                 COALESCE(d.num_100k_250k, 0) + 
                 COALESCE(d.num_250k_1m, 0)), 0)
    ) AS avg_loan_amount_thousands
  FROM `{self.project_id}.sb.disclosure` d
  WHERE d.year IS NOT NULL
    AND d.respondent_id IS NOT NULL
    {year_filter}
  GROUP BY d.respondent_id
  HAVING avg_loan_amount_thousands >= {min_avg_thousands}
),
"""
            # Add filter to main query
            credit_card_join = """
INNER JOIN lender_avg_loan_amount lavg
  ON d.respondent_id = lavg.respondent_id
"""
        else:
            credit_card_join = ""
        
        sql = f"""
WITH 
{credit_card_filter}
loan_counts AS (
  SELECT 
    d.respondent_id,
    CAST(d.year AS INT64) AS year,
    -- Sum loan counts across all size categories
    SUM(COALESCE(d.num_under_100k, 0) + 
        COALESCE(d.num_100k_250k, 0) + 
        COALESCE(d.num_250k_1m, 0)) AS loans_in_year
  FROM `{self.project_id}.sb.disclosure` d
  {credit_card_join if exclude_credit_card else ""}
  WHERE d.year IS NOT NULL
    AND d.respondent_id IS NOT NULL
    {year_filter}
  GROUP BY d.respondent_id, CAST(d.year AS INT64)
),
qualified AS (
  SELECT 
    curr.respondent_id,
    curr.year
  FROM loan_counts curr
  INNER JOIN loan_counts prev
    ON curr.respondent_id = prev.respondent_id 
    AND curr.year = prev.year + 1
  WHERE curr.loans_in_year >= {min_loans} 
    AND prev.loans_in_year >= {min_loans}
)
SELECT 
  d.*,
  l.sb_lender as lender_name,
  g.county_state,
  g.county as county_name,
  g.state as state_name,
  CASE 
    WHEN q.respondent_id IS NOT NULL THEN 'Qualifies'
    ELSE 'Does Not Qualify'
  END AS qualification_status
FROM `{self.project_id}.sb.disclosure` d
LEFT JOIN `{self.project_id}.sb.lenders` l 
  ON d.respondent_id = l.sb_resid
LEFT JOIN `{self.project_id}.geo.cbsa_to_county` g 
  ON LPAD(CAST(d.geoid5 AS STRING), 5, '0') = LPAD(CAST(g.geoid5 AS STRING), 5, '0')
LEFT JOIN qualified q
  ON d.respondent_id = q.respondent_id 
  AND CAST(d.year AS INT64) = q.year
{credit_card_join if exclude_credit_card else ""}
WHERE d.year IS NOT NULL
  AND d.respondent_id IS NOT NULL
  {year_filter}
ORDER BY d.respondent_id, d.year, g.county_state
{limit_clause}
"""
        
        return self.query(sql)
    
    def create_lender_qualification_table(self, min_loans: int = 1000, years: list = None, 
                                          exclude_credit_card: bool = True, 
                                          min_avg_loan_amount: float = 10000,
                                          table_name: str = None,
                                          dataset: str = 'misc'):
        """
        Create a BigQuery table with lender qualification data instead of returning results.
        This is much faster for large datasets than fetching to Python.
        
        For each year, includes:
        - All lenders in that year
        - Only lenders with average loan amount >= $10k for that year (if exclude_credit_card=True)
        - Qualification status: lenders with >= 1000 loans in that year AND previous year
        
        Args:
            min_loans: Minimum number of loans required for qualification (default: 1000)
            years: Optional list of years to filter (default: 2018-2024)
            exclude_credit_card: If True, exclude lenders with average loan amount < min_avg_loan_amount for that year
            min_avg_loan_amount: Minimum average loan amount to include lender (default: 10000)
            table_name: Name for the output table (default: auto-generated with timestamp)
            dataset: Dataset to create table in (default: 'misc')
        
        Returns:
            Tuple of (table_id, query_job) where table_id is the full table path
        """
        from datetime import datetime
        
        # Default to 2018-2024 if no years specified
        if years is None:
            years = [2018, 2019, 2020, 2021, 2022, 2023, 2024]
        
        # Generate table name if not provided
        if not table_name:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            table_name = f'lender_qualification_data_{timestamp}'
        
        # Build year filter
        year_filter = ""
        if years:
            year_list = ", ".join(str(y) for y in years)
            year_filter = f"AND CAST(d.year AS INT64) IN ({year_list})"
        
        # Build credit card lender exclusion
        # Note: amounts are in thousands (000s), so $10,000 = 10
        # Calculate average loan amount PER YEAR (not across all years)
        credit_card_filter = ""
        if exclude_credit_card:
            # Convert min_avg_loan_amount from dollars to thousands
            min_avg_thousands = min_avg_loan_amount / 1000
            credit_card_filter = f"""
-- Exclude credit card lenders (average loan amount < ${min_avg_loan_amount:,.0f} for that year)
-- Note: amounts in disclosure table are in thousands (000s)
-- Calculate average loan amount PER YEAR per lender
lender_avg_loan_amount_by_year AS (
  SELECT 
    d.respondent_id,
    CAST(d.year AS INT64) AS year,
    -- Calculate average loan amount per lender for THIS YEAR
    -- Amounts are in thousands, so result is also in thousands
    SAFE_DIVIDE(
      SUM(COALESCE(d.amt_under_100k, 0) + 
          COALESCE(d.amt_100k_250k, 0) + 
          COALESCE(d.amt_250k_1m, 0)),
      NULLIF(SUM(COALESCE(d.num_under_100k, 0) + 
                 COALESCE(d.num_100k_250k, 0) + 
                 COALESCE(d.num_250k_1m, 0)), 0)
    ) AS avg_loan_amount_thousands
  FROM `{self.project_id}.sb.disclosure` d
  WHERE d.year IS NOT NULL
    AND d.respondent_id IS NOT NULL
    {year_filter}
  GROUP BY d.respondent_id, CAST(d.year AS INT64)
  HAVING avg_loan_amount_thousands >= {min_avg_thousands}
),
"""
            # Add filter to main query - join on both respondent_id AND year
            credit_card_join = """
INNER JOIN lender_avg_loan_amount_by_year lavg
  ON d.respondent_id = lavg.respondent_id
  AND CAST(d.year AS INT64) = lavg.year
"""
        else:
            credit_card_join = ""
        
        # Check if dataset exists, create if needed
        try:
            dataset_ref = self.client.dataset(dataset)
            try:
                self.client.get_dataset(dataset_ref)
            except Exception:
                # Dataset doesn't exist, create it
                print(f"   Creating dataset '{dataset}' if it doesn't exist...")
                dataset_obj = bigquery.Dataset(dataset_ref)
                dataset_obj.location = "US"
                self.client.create_dataset(dataset_obj, exists_ok=True)
        except Exception as e:
            print(f"   Warning: Could not verify/create dataset: {e}")
        
        # Full table path
        table_id = f"{self.project_id}.{dataset}.{table_name}"
        
        sql = f"""
CREATE OR REPLACE TABLE `{table_id}` AS
WITH 
{credit_card_filter}
loan_counts AS (
  SELECT 
    d.respondent_id,
    CAST(d.year AS INT64) AS year,
    -- Sum loan counts across all size categories
    SUM(COALESCE(d.num_under_100k, 0) + 
        COALESCE(d.num_100k_250k, 0) + 
        COALESCE(d.num_250k_1m, 0)) AS loans_in_year
  FROM `{self.project_id}.sb.disclosure` d
  {credit_card_join if exclude_credit_card else ""}
  WHERE d.year IS NOT NULL
    AND d.respondent_id IS NOT NULL
    {year_filter}
  GROUP BY d.respondent_id, CAST(d.year AS INT64)
),
qualified AS (
  SELECT 
    curr.respondent_id,
    curr.year
  FROM loan_counts curr
  INNER JOIN loan_counts prev
    ON curr.respondent_id = prev.respondent_id 
    AND curr.year = prev.year + 1
  WHERE curr.loans_in_year >= {min_loans} 
    AND prev.loans_in_year >= {min_loans}
)
SELECT 
  d.*,
  l.sb_lender as lender_name,
  g.county_state,
  g.county as county_name,
  g.state as state_name,
  CASE 
    WHEN q.respondent_id IS NOT NULL THEN 'Qualifies'
    ELSE 'Does Not Qualify'
  END AS qualification_status
FROM `{self.project_id}.sb.disclosure` d
LEFT JOIN `{self.project_id}.sb.lenders` l 
  ON d.respondent_id = l.sb_resid
LEFT JOIN `{self.project_id}.geo.cbsa_to_county` g 
  ON LPAD(CAST(d.geoid5 AS STRING), 5, '0') = LPAD(CAST(g.geoid5 AS STRING), 5, '0')
LEFT JOIN qualified q
  ON d.respondent_id = q.respondent_id 
  AND CAST(d.year AS INT64) = q.year
{credit_card_join if exclude_credit_card else ""}
WHERE d.year IS NOT NULL
  AND d.respondent_id IS NOT NULL
  {year_filter}
ORDER BY d.respondent_id, d.year, g.county_state
"""
        
        query_job = self.query(sql)
        return table_id, query_job
    
    def get_county_summary_stats(self, geoid5: str, years: list = None):
        """
        Get summary statistics for a county including LMI metrics.
        
        Args:
            geoid5: Single GEOID5 code (5-digit FIPS) for one county
            years: Optional list of years to filter
        
        Returns:
            Query job result with summary statistics
        """
        geoid5_padded = str(geoid5).zfill(5)
        
        year_filter = ""
        if years:
            year_list = ", ".join(str(y) for y in years)
            year_filter = f"AND CAST(a.year AS INT64) IN ({year_list})"
        
        sql = f"""
        WITH tract_data AS (
            SELECT 
                a.*,
                -- Get census tract data from geo.census table (2025 FFIEC Census file)
                -- Join on geoid = geoid10
                -- Use income_level field from census (1=low ≤50%, 2=moderate ≤80%, 3=middle ≤120%, 4=upper >120%)
                -- Map to tract_to_msa_income_percentage using midpoints for each range
                CASE 
                    WHEN c.income_level = 1 THEN 40.0  -- Low (≤50% AMI, use midpoint ~40%)
                    WHEN c.income_level = 2 THEN 65.0   -- Moderate (≤80% AMI, use midpoint ~65%)
                    WHEN c.income_level = 3 THEN 100.0 -- Middle (≤120% AMI, use midpoint ~100%)
                    WHEN c.income_level = 4 THEN 150.0 -- Upper (>120% AMI, use midpoint ~150%)
                    ELSE NULL
                END as tract_to_msa_income_percentage,
                -- Calculate minority population percent: (total - white) / total * 100
                SAFE_DIVIDE(
                    COALESCE(c.total_persons, 0) - COALESCE(c.total_white, 0),
                    NULLIF(COALESCE(c.total_persons, 0), 0)
                ) * 100 as tract_minority_population_percent,
                -- LMI flag (≤80% AMI) - income_level 1 or 2
                CASE WHEN c.income_level IN (1, 2) THEN 1 ELSE 0 END as is_lmi_tract,
                -- Use geoid10 from aggregate table as the tract identifier
                CAST(a.geoid10 AS STRING) as tract_geoid,
                -- Calculate loan_count and loan_amount from num_* and amt_* fields (like disclosure table)
                COALESCE(a.num_under_100k, 0) + COALESCE(a.num_100k_250k, 0) + COALESCE(a.num_250k_1m, 0) as loan_count,
                COALESCE(a.amt_under_100k, 0) + COALESCE(a.amt_100k_250k, 0) + COALESCE(a.amt_250k_1m, 0) as loan_amount
            FROM `{self.project_id}.sb.aggregate` a
            JOIN `{self.project_id}.geo.cbsa_to_county` g 
                ON LPAD(CAST(a.geoid5 AS STRING), 5, '0') = LPAD(CAST(g.geoid5 AS STRING), 5, '0')
            LEFT JOIN `{self.project_id}.geo.census` c
                ON CAST(a.geoid10 AS STRING) = CAST(c.geoid AS STRING)
            WHERE LPAD(CAST(g.geoid5 AS STRING), 5, '0') = '{geoid5_padded}'
                {year_filter}
        )
        SELECT 
            COUNT(DISTINCT tract_geoid) as total_tracts,
            SUM(loan_count) as total_loans,
            SUM(loan_amount) as total_loan_amount,
            -- LMI tract metrics
            SUM(CASE WHEN is_lmi_tract = 1 THEN loan_count ELSE 0 END) as lmi_tract_loans,
            SUM(CASE WHEN is_lmi_tract = 1 THEN loan_amount ELSE 0 END) as lmi_tract_amount,
            -- LMI borrower metrics (using income field from aggregate table, in $000s)
            -- Income is in $000s, so <= 80 means <= 80% of AMI
            SUM(CASE WHEN COALESCE(income, 999) <= 80 THEN loan_count ELSE 0 END) as lmi_borrower_loans,
            SUM(CASE WHEN COALESCE(income, 999) <= 80 THEN loan_amount ELSE 0 END) as lmi_borrower_amount,
            -- Percentages
            SAFE_DIVIDE(
                SUM(CASE WHEN is_lmi_tract = 1 THEN loan_count ELSE 0 END),
                SUM(loan_count)
            ) * 100 as pct_loans_to_lmi_tracts,
            SAFE_DIVIDE(
                SUM(CASE WHEN is_lmi_tract = 1 THEN loan_amount ELSE 0 END),
                SUM(loan_amount)
            ) * 100 as pct_dollars_to_lmi_tracts,
            SAFE_DIVIDE(
                SUM(CASE WHEN COALESCE(income, 999) <= 80 THEN loan_count ELSE 0 END),
                SUM(loan_count)
            ) * 100 as pct_loans_to_lmi_borrowers
        FROM tract_data
        """
        
        return self.query(sql)
    
    def get_county_minority_threshold(self, geoid5: str):
        """
        Get the overall minority percentage for a county to use as threshold for race layers.
        
        Args:
            geoid5: Single GEOID5 code (5-digit FIPS) for one county
        
        Returns:
            Query job result with county-level minority percentage
        """
        geoid5_padded = str(geoid5).zfill(5)
        
        sql = f"""
        SELECT 
            AVG(SAFE_DIVIDE(
                COALESCE(c.total_persons, 0) - COALESCE(c.total_white, 0),
                NULLIF(COALESCE(c.total_persons, 0), 0)
            ) * 100) as county_avg_minority_pct,
            PERCENTILE_CONT(SAFE_DIVIDE(
                COALESCE(c.total_persons, 0) - COALESCE(c.total_white, 0),
                NULLIF(COALESCE(c.total_persons, 0), 0)
            ) * 100, 0.5) OVER() as county_median_minority_pct
        FROM `{self.project_id}.geo.census` c
        JOIN `{self.project_id}.geo.cbsa_to_county` g 
            ON SUBSTR(c.geoid, 1, 5) = LPAD(CAST(g.geoid5 AS STRING), 5, '0')
        WHERE LPAD(CAST(g.geoid5 AS STRING), 5, '0') = '{geoid5_padded}'
        LIMIT 1
        """
        
        return self.query(sql)
    
    def get_available_counties(self, state_code: str = None):
        """
        Get list of available counties from disclosure data.
        
        Args:
            state_code: Optional 2-digit state FIPS code to filter by state
        
        Returns:
            Query job result with county information
        """
        state_filter = ""
        if state_code:
            # State code is first 2 digits of GEOID5
            state_code_padded = str(state_code).zfill(2)
            state_filter = f"AND SUBSTR(LPAD(CAST(geoid5 AS STRING), 5, '0'), 1, 2) = '{state_code_padded}'"
        
        sql = f"""
        SELECT DISTINCT
            county_state,
            geoid5,
            SUBSTR(LPAD(CAST(geoid5 AS STRING), 5, '0'), 1, 2) as state_fips,
            SUBSTR(LPAD(CAST(geoid5 AS STRING), 5, '0'), 3, 3) as county_fips
        FROM `{self.project_id}.geo.cbsa_to_county`
        WHERE geoid5 IS NOT NULL
            AND county_state IS NOT NULL
            AND TRIM(county_state) != ''
            {state_filter}
        ORDER BY county_state
        """
        
        print(f"DEBUG: get_available_counties SQL query:\n{sql}")
        query_job = self.query(sql)
        print(f"DEBUG: Query job created, job_id: {query_job.job_id}")
        return query_job
    
    def get_available_states(self):
        """Get list of available states.
        
        Note: This method is kept for backward compatibility, but get_available_states()
        in data_utils.py now uses a hardcoded list of all US states (like LendSight)
        for better reliability and performance.
        """
        # Query directly from geo.cbsa_to_county (like LendSight does for counties)
        sql = f"""
        SELECT DISTINCT
            SUBSTR(LPAD(CAST(geoid5 AS STRING), 5, '0'), 1, 2) as state_fips,
            state as state_name
        FROM `{self.project_id}.geo.cbsa_to_county`
        WHERE geoid5 IS NOT NULL
            AND state IS NOT NULL
        ORDER BY state
        """
        
        return self.query(sql)
    
    def get_available_years(self):
        """Get list of available years from disclosure data."""
        sql = f"""
        SELECT DISTINCT year
        FROM `{self.project_id}.sb.disclosure`
        WHERE year IS NOT NULL
        ORDER BY year
        """
        
        result = self.query(sql)
        return [row.year for row in result]
    
    def get_state_benchmarks(self, state_fips: str, year: int = 2024):
        """
        Get state-level benchmark statistics for comparison.
        
        Args:
            state_fips: 2-digit state FIPS code
            year: Year to get benchmarks for (default 2024)
        
        Returns:
            Query job result with state-level statistics
        """
        state_fips_padded = str(state_fips).zfill(2)
        
        sql = f"""
        WITH tract_data AS (
            SELECT 
                a.*,
                c.income_level,
                CASE WHEN c.income_level IN (1, 2) THEN 1 ELSE 0 END as is_lmi_tract,
                COALESCE(a.num_under_100k, 0) + COALESCE(a.num_100k_250k, 0) + COALESCE(a.num_250k_1m, 0) as loan_count,
                COALESCE(a.amt_under_100k, 0) + COALESCE(a.amt_100k_250k, 0) + COALESCE(a.amt_250k_1m, 0) as loan_amount
            FROM `{self.project_id}.sb.aggregate` a
            JOIN `{self.project_id}.geo.cbsa_to_county` g 
                ON LPAD(CAST(a.geoid5 AS STRING), 5, '0') = LPAD(CAST(g.geoid5 AS STRING), 5, '0')
            LEFT JOIN `{self.project_id}.geo.census` c
                ON CAST(a.geoid10 AS STRING) = CAST(c.geoid AS STRING)
            WHERE SUBSTR(LPAD(CAST(g.geoid5 AS STRING), 5, '0'), 1, 2) = '{state_fips_padded}'
                AND CAST(a.year AS INT64) = {year}
        )
        SELECT 
            SUM(loan_count) as total_loans,
            SUM(loan_amount) as total_amount,
            SUM(CASE WHEN is_lmi_tract = 1 THEN loan_count ELSE 0 END) as lmi_tract_loans,
            SUM(CASE WHEN is_lmi_tract = 1 THEN loan_amount ELSE 0 END) as lmi_tract_amount,
            -- Income category breakdowns (by loan count)
            SUM(CASE WHEN income_level = 1 THEN loan_count ELSE 0 END) as low_income_loans,
            SUM(CASE WHEN income_level = 2 THEN loan_count ELSE 0 END) as moderate_income_loans,
            SUM(CASE WHEN income_level = 3 THEN loan_count ELSE 0 END) as middle_income_loans,
            SUM(CASE WHEN income_level = 4 THEN loan_count ELSE 0 END) as upper_income_loans,
            -- Income category breakdowns (by loan amount)
            SUM(CASE WHEN income_level = 1 THEN loan_amount ELSE 0 END) as low_income_amount,
            SUM(CASE WHEN income_level = 2 THEN loan_amount ELSE 0 END) as moderate_income_amount,
            SUM(CASE WHEN income_level = 3 THEN loan_amount ELSE 0 END) as middle_income_amount,
            SUM(CASE WHEN income_level = 4 THEN loan_amount ELSE 0 END) as upper_income_amount,
            SUM(COALESCE(num_under_100k, 0)) as num_under_100k,
            SUM(COALESCE(num_100k_250k, 0)) as num_100k_250k,
            SUM(COALESCE(num_250k_1m, 0)) as num_250k_1m,
            SUM(COALESCE(amt_under_100k, 0)) as amt_under_100k,
            SUM(COALESCE(amt_250k_1m, 0)) as amt_250k_1m,
            SUM(COALESCE(numsb_under_1m, 0)) as numsb_under_1m,
            SUM(COALESCE(amtsb_under_1m, 0)) as amtsb_under_1m
        FROM tract_data
        """
        
        return self.query(sql)
    
    def get_national_benchmarks(self, year: int = 2024):
        """
        Get national-level benchmark statistics for comparison.
        
        Args:
            year: Year to get benchmarks for (default 2024)
        
        Returns:
            Query job result with national-level statistics
        """
        sql = f"""
        WITH tract_data AS (
            SELECT 
                a.*,
                c.income_level,
                CASE WHEN c.income_level IN (1, 2) THEN 1 ELSE 0 END as is_lmi_tract,
                COALESCE(a.num_under_100k, 0) + COALESCE(a.num_100k_250k, 0) + COALESCE(a.num_250k_1m, 0) as loan_count,
                COALESCE(a.amt_under_100k, 0) + COALESCE(a.amt_100k_250k, 0) + COALESCE(a.amt_250k_1m, 0) as loan_amount
            FROM `{self.project_id}.sb.aggregate` a
            LEFT JOIN `{self.project_id}.geo.census` c
                ON CAST(a.geoid10 AS STRING) = CAST(c.geoid AS STRING)
            WHERE CAST(a.year AS INT64) = {year}
        )
        SELECT 
            SUM(loan_count) as total_loans,
            SUM(loan_amount) as total_amount,
            SUM(CASE WHEN is_lmi_tract = 1 THEN loan_count ELSE 0 END) as lmi_tract_loans,
            SUM(CASE WHEN is_lmi_tract = 1 THEN loan_amount ELSE 0 END) as lmi_tract_amount,
            -- Income category breakdowns (by loan count)
            SUM(CASE WHEN income_level = 1 THEN loan_count ELSE 0 END) as low_income_loans,
            SUM(CASE WHEN income_level = 2 THEN loan_count ELSE 0 END) as moderate_income_loans,
            SUM(CASE WHEN income_level = 3 THEN loan_count ELSE 0 END) as middle_income_loans,
            SUM(CASE WHEN income_level = 4 THEN loan_count ELSE 0 END) as upper_income_loans,
            -- Income category breakdowns (by loan amount)
            SUM(CASE WHEN income_level = 1 THEN loan_amount ELSE 0 END) as low_income_amount,
            SUM(CASE WHEN income_level = 2 THEN loan_amount ELSE 0 END) as moderate_income_amount,
            SUM(CASE WHEN income_level = 3 THEN loan_amount ELSE 0 END) as middle_income_amount,
            SUM(CASE WHEN income_level = 4 THEN loan_amount ELSE 0 END) as upper_income_amount,
            SUM(COALESCE(num_under_100k, 0)) as num_under_100k,
            SUM(COALESCE(num_100k_250k, 0)) as num_100k_250k,
            SUM(COALESCE(num_250k_1m, 0)) as num_250k_1m,
            SUM(COALESCE(amt_under_100k, 0)) as amt_under_100k,
            SUM(COALESCE(amt_250k_1m, 0)) as amt_250k_1m,
            SUM(COALESCE(numsb_under_1m, 0)) as numsb_under_1m,
            SUM(COALESCE(amtsb_under_1m, 0)) as amtsb_under_1m
        FROM tract_data
        """
        
        return self.query(sql)