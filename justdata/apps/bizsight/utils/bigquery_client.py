#!/usr/bin/env python3
"""
BigQuery Client for BizSight.

Provides the BigQueryClient wrapper class with bizsight-specific query
helpers. Client initialization delegates to the shared client at
justdata.shared.utils.bigquery_client (passing app_name='bizsight' so
BIZSIGHT_CREDENTIALS_JSON / BIZSIGHT_BIGQUERY_CREDENTIALS_JSON are
honored via the shared client's VALID_APP_NAMES list).
"""

import os
import logging
from typing import List

from justdata.shared.utils.bigquery_client import (
    get_bigquery_client as shared_get_bigquery_client,
)

logger = logging.getLogger(__name__)


class BigQueryClient:
    """Wrapper class for BigQuery operations."""

    def __init__(self, project_id: str = None, credentials_path: str = None):
        """Initialize the BigQuery client via the shared utility.

        Args:
            project_id: GCP project ID (defaults to JUSTDATA_PROJECT_ID env var
                or 'justdata-ncrc')
            credentials_path: Ignored — the shared client picks credentials from
                env vars. Argument kept for backward compatibility with
                callers that still pass it.
        """
        resolved_project = project_id or os.getenv('JUSTDATA_PROJECT_ID', 'justdata-ncrc')
        # Shared client raises on unrecoverable init errors — let them surface
        # rather than fall back to a local re-implementation.
        self.client = shared_get_bigquery_client(
            project_id=resolved_project,
            app_name='bizsight',
        )
        self.project_id = resolved_project
        self.summary_project_id = resolved_project
        self.use_summary_tables = os.getenv('USE_SUMMARY_TABLES', 'false').lower() == 'true'
    
    def query(self, sql: str, **kwargs):
        """Execute a BigQuery SQL query and return QueryJob."""
        return self.client.query(sql, **kwargs)
    
    def get_sb_county_summary(self, geoid5: str, years: list = None):
        """
        Get pre-aggregated SB county summary for ~99% cost reduction.
        Falls back to regular disclosure query if summary tables are not available.
        
        Args:
            geoid5: Single GEOID5 code (5-digit FIPS) for one county
            years: Optional list of years to filter
            
        Returns:
            Query job result with county-level aggregated data
        """
        if not self.use_summary_tables:
            logger.info("Summary tables disabled, using original disclosure query")
            return self.get_disclosure_data(geoid5, years)
        
        try:
            geoid5_padded = str(geoid5).zfill(5)
            
            year_filter = ""
            if years:
                year_list = ", ".join(str(y) for y in years)
                year_filter = f"AND year IN ({year_list})"
            
            sql = f"""
            SELECT
                geoid5,
                year,
                lender_name,
                num_under_100k,
                num_100k_250k,
                num_250k_1m,
                total_loans,
                amt_under_100k,
                amt_100k_250k,
                amt_250k_1m,
                lmi_tract_loans,
                low_income_loans,
                moderate_income_loans,
                midu_income_loans,
                lmi_tract_amount,
                low_income_amount,
                moderate_income_amount,
                midu_income_amount
            FROM `{self.summary_project_id}.bizsight.sb_county_summary`
            WHERE geoid5 = '{geoid5_padded}'
                {year_filter}
            ORDER BY year, lender_name
            """
            
            logger.info(f"Using SB county summary table for geoid5={geoid5_padded}")
            return self.query(sql)
            
        except Exception as e:
            logger.warning(f"SB county summary query failed, falling back to disclosure: {e}")
            return self.get_disclosure_data(geoid5, years)
    
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
        
        # Note: bizsight.sb_county_summary has pre-computed income columns per row:
        # low_income_loans, moderate_income_loans, midu_income_loans (mid+upper combined)
        # Each row = one lender in one county for one year, with all income breakdowns as columns
        sql = f"""
        SELECT
            a.*,
            g.county_state,
            g.county as county_name,
            g.state as state_name,
            g.geoid5 as geo_geoid5,
            -- Unique identifier for grouping
            CONCAT(CAST(a.geoid5 AS STRING), '_', CAST(a.year AS STRING), '_', COALESCE(a.respondent_id, '0')) as census_tract_geoid,
            -- Calculate loan_count and loan_amount from num_* and amt_* fields
            COALESCE(a.num_under_100k, 0) + COALESCE(a.num_100k_250k, 0) + COALESCE(a.num_250k_1m, 0) as loan_count,
            COALESCE(a.amt_under_100k, 0) + COALESCE(a.amt_100k_250k, 0) + COALESCE(a.amt_250k_1m, 0) as loan_amount,
            -- Census tract-level demographics not available at county level
            NULL as tract_to_msa_income_percentage,
            NULL as tract_median_income,
            NULL as tract_population,
            NULL as tract_white_percent,
            NULL as tract_black_percent,
            NULL as tract_hispanic_percent,
            NULL as tract_asian_percent,
            NULL as tract_other_race_percent,
            NULL as tract_minority_population_percent,
            -- Income category label for display
            'County Aggregate' as income_category,
            -- LMI flag: use low_income_loans + moderate_income_loans (lmi_tract_loans contains zeros)
            CASE WHEN (COALESCE(a.low_income_loans, 0) + COALESCE(a.moderate_income_loans, 0)) > 0 THEN 1 ELSE 0 END as is_lmi_tract
        FROM `{self.project_id}.bizsight.sb_county_summary` a
        JOIN `{self.project_id}.shared.cbsa_to_county` g
            ON LPAD(CAST(a.geoid5 AS STRING), 5, '0') = LPAD(CAST(g.geoid5 AS STRING), 5, '0')
        WHERE LPAD(CAST(g.geoid5 AS STRING), 5, '0') = '{geoid5_padded}'
            {year_filter}
        ORDER BY a.geoid5, a.year
        """
        
        return self.query(sql)
    
    def get_disclosure_data(self, geoid5: str, years: list = None, is_planning_region: bool = False):
        """
        Get disclosure (lender-level, county-level) small business lending data.

        Args:
            geoid5: Single GEOID5 code (5-digit FIPS) for one county
            years: Optional list of years to filter
            is_planning_region: Whether this is a CT planning region (for future use)

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
            d.* EXCEPT(lender_name),
            l.sb_lender as lender_name,
            g.county_state,
            g.county as county_name,
            g.state as state_name
        FROM `{self.project_id}.bizsight.sb_county_summary` d
        JOIN (
            SELECT sb_resid, sb_lender,
            ROW_NUMBER() OVER (PARTITION BY sb_resid ORDER BY sb_year DESC) as rn
            FROM `{self.project_id}.bizsight.sb_lenders`
        ) l ON d.respondent_id = l.sb_resid AND l.rn = 1
        JOIN `{self.project_id}.shared.cbsa_to_county` g
            ON LPAD(CAST(d.geoid5 AS STRING), 5, '0') = LPAD(CAST(g.geoid5 AS STRING), 5, '0')
        WHERE LPAD(CAST(g.geoid5 AS STRING), 5, '0') = '{geoid5_padded}'
            {year_filter}
        ORDER BY d.year, l.sb_lender
        """
        
        return self.query(sql)
    
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

        # Derive income breakdowns from income_group_total column
        sql = f"""
        SELECT
            COUNT(DISTINCT CAST(a.geoid5 AS STRING)) as total_tracts,
            SUM(COALESCE(a.num_under_100k, 0) + COALESCE(a.num_100k_250k, 0) + COALESCE(a.num_250k_1m, 0)) as total_loans,
            SUM(COALESCE(a.amt_under_100k, 0) + COALESCE(a.amt_100k_250k, 0) + COALESCE(a.amt_250k_1m, 0)) as total_loan_amount,
            -- LMI tract loans: sum low_income_loans + moderate_income_loans
            SUM(COALESCE(a.low_income_loans, 0) + COALESCE(a.moderate_income_loans, 0)) as lmi_tract_loans,
            SUM(COALESCE(a.lmi_tract_amount, 0)) as lmi_tract_amount,
            -- LMI borrower metrics (not available - small business data doesn't have borrower income)
            0 as lmi_borrower_loans,
            0 as lmi_borrower_amount,
            -- Calculate percentages
            SAFE_DIVIDE(
                SUM(COALESCE(a.low_income_loans, 0) + COALESCE(a.moderate_income_loans, 0)),
                SUM(COALESCE(a.num_under_100k, 0) + COALESCE(a.num_100k_250k, 0) + COALESCE(a.num_250k_1m, 0))
            ) * 100 as pct_loans_to_lmi_tracts,
            SAFE_DIVIDE(
                SUM(COALESCE(a.lmi_tract_amount, 0)),
                SUM(COALESCE(a.amt_under_100k, 0) + COALESCE(a.amt_100k_250k, 0) + COALESCE(a.amt_250k_1m, 0))
            ) * 100 as pct_dollars_to_lmi_tracts,
            0 as pct_loans_to_lmi_borrowers,
            -- Income category breakdowns - counts
            SUM(COALESCE(a.low_income_loans, 0)) as low_income_loans,
            SUM(COALESCE(a.moderate_income_loans, 0)) as moderate_income_loans,
            0 as middle_income_loans,
            SUM(COALESCE(a.midu_income_loans, 0)) as upper_income_loans,
            -- Income category breakdowns - amounts
            SUM(COALESCE(a.low_income_amount, 0)) as low_income_amount,
            SUM(COALESCE(a.moderate_income_amount, 0)) as moderate_income_amount,
            0 as middle_income_amount,
            SUM(COALESCE(a.midu_income_amount, 0)) as upper_income_amount
        FROM `{self.project_id}.bizsight.sb_county_summary` a
        JOIN `{self.project_id}.shared.cbsa_to_county` g
            ON LPAD(CAST(a.geoid5 AS STRING), 5, '0') = LPAD(CAST(g.geoid5 AS STRING), 5, '0')
        WHERE LPAD(CAST(g.geoid5 AS STRING), 5, '0') = '{geoid5_padded}'
            {year_filter}
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
        FROM `{self.project_id}.shared.census` c
        JOIN `{self.project_id}.shared.cbsa_to_county` g 
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
        FROM `{self.project_id}.shared.cbsa_to_county`
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
        # Query directly from shared.cbsa_to_county (like LendSight does for counties)
        sql = f"""
        SELECT DISTINCT
            SUBSTR(LPAD(CAST(geoid5 AS STRING), 5, '0'), 1, 2) as state_fips,
            state as state_name
        FROM `{self.project_id}.shared.cbsa_to_county`
        WHERE geoid5 IS NOT NULL
            AND state IS NOT NULL
        ORDER BY state
        """
        
        return self.query(sql)
    
    def get_last_5_years_sb(self) -> List[int]:
        """
        Get the last 5 years dynamically from SB disclosure data (bizsight.sb_county_summary).
        
        Returns:
            List of the 5 most recent years available, sorted descending (e.g., [2024, 2023, 2022, 2021, 2020])
        """
        try:
            query = f"""
            SELECT DISTINCT year
            FROM `{self.project_id}.bizsight.sb_county_summary`
            WHERE year IS NOT NULL
            ORDER BY year DESC
            LIMIT 5
            """
            query_job = self.query(query)
            results = query_job.result()
            years = [int(row.year) for row in results]
            if years:
                print(f"[OK] Fetched last 5 SB disclosure years: {years}")
                return years
            else:
                # Fallback to recent years
                print("[WARN]  No SB disclosure years found, using fallback")
                return list(range(2020, 2025))  # 2020-2024
        except Exception as e:
            print(f"Error fetching SB disclosure years: {e}")
            # Fallback to recent years
            return list(range(2020, 2025))  # 2020-2024
    
    def get_available_years(self):
        """Get list of available years from disclosure data."""
        sql = f"""
        SELECT DISTINCT year
        FROM `{self.project_id}.bizsight.sb_county_summary`
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

        # Use pre-computed columns directly instead of deriving from income_group_total
        sql = f"""
        SELECT
            SUM(COALESCE(a.num_under_100k, 0) + COALESCE(a.num_100k_250k, 0) + COALESCE(a.num_250k_1m, 0)) as total_loans,
            SUM(COALESCE(a.amt_under_100k, 0) + COALESCE(a.amt_100k_250k, 0) + COALESCE(a.amt_250k_1m, 0)) as total_amount,
            -- LMI tract loans/amounts
            SUM(COALESCE(a.low_income_loans, 0) + COALESCE(a.moderate_income_loans, 0)) as lmi_tract_loans,
            SUM(COALESCE(a.lmi_tract_amount, 0)) as lmi_tract_amount,
            -- Income category breakdowns - counts
            SUM(COALESCE(a.low_income_loans, 0)) as low_income_loans,
            SUM(COALESCE(a.moderate_income_loans, 0)) as moderate_income_loans,
            0 as middle_income_loans,
            SUM(COALESCE(a.midu_income_loans, 0)) as upper_income_loans,
            -- Income category breakdowns - amounts
            SUM(COALESCE(a.low_income_amount, 0)) as low_income_amount,
            SUM(COALESCE(a.moderate_income_amount, 0)) as moderate_income_amount,
            0 as middle_income_amount,
            SUM(COALESCE(a.midu_income_amount, 0)) as upper_income_amount,
            SUM(COALESCE(a.num_under_100k, 0)) as num_under_100k,
            SUM(COALESCE(a.num_100k_250k, 0)) as num_100k_250k,
            SUM(COALESCE(a.num_250k_1m, 0)) as num_250k_1m,
            SUM(COALESCE(a.amt_under_100k, 0)) as amt_under_100k,
            SUM(COALESCE(a.amt_250k_1m, 0)) as amt_250k_1m,
            SUM(COALESCE(a.numsbrev_under_1m, 0)) as numsb_under_1m,
            SUM(COALESCE(a.amtsbrev_under_1m, 0)) as amtsb_under_1m,
            SUM(COALESCE(a.unknown_income_loans, 0)) as unknown_income_loans,
            SUM(COALESCE(a.unknown_income_amount, 0)) as unknown_income_amount
        FROM `{self.project_id}.bizsight.sb_county_summary` a
        JOIN `{self.project_id}.shared.cbsa_to_county` g
            ON LPAD(CAST(a.geoid5 AS STRING), 5, '0') = LPAD(CAST(g.geoid5 AS STRING), 5, '0')
        WHERE SUBSTR(LPAD(CAST(g.geoid5 AS STRING), 5, '0'), 1, 2) = '{state_fips_padded}'
            AND CAST(a.year AS INT64) = {year}
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
        SELECT
            SUM(COALESCE(a.num_under_100k, 0) + COALESCE(a.num_100k_250k, 0) + COALESCE(a.num_250k_1m, 0)) as total_loans,
            SUM(COALESCE(a.amt_under_100k, 0) + COALESCE(a.amt_100k_250k, 0) + COALESCE(a.amt_250k_1m, 0)) as total_amount,
            -- LMI tract loans/amounts
            SUM(COALESCE(a.low_income_loans, 0) + COALESCE(a.moderate_income_loans, 0)) as lmi_tract_loans,
            SUM(COALESCE(a.lmi_tract_amount, 0)) as lmi_tract_amount,
            -- Income category breakdowns - counts
            SUM(COALESCE(a.low_income_loans, 0)) as low_income_loans,
            SUM(COALESCE(a.moderate_income_loans, 0)) as moderate_income_loans,
            0 as middle_income_loans,
            SUM(COALESCE(a.midu_income_loans, 0)) as upper_income_loans,
            -- Income category breakdowns - amounts
            SUM(COALESCE(a.low_income_amount, 0)) as low_income_amount,
            SUM(COALESCE(a.moderate_income_amount, 0)) as moderate_income_amount,
            0 as middle_income_amount,
            SUM(COALESCE(a.midu_income_amount, 0)) as upper_income_amount,
            SUM(COALESCE(a.num_under_100k, 0)) as num_under_100k,
            SUM(COALESCE(a.num_100k_250k, 0)) as num_100k_250k,
            SUM(COALESCE(a.num_250k_1m, 0)) as num_250k_1m,
            SUM(COALESCE(a.amt_under_100k, 0)) as amt_under_100k,
            SUM(COALESCE(a.amt_250k_1m, 0)) as amt_250k_1m,
            SUM(COALESCE(a.numsbrev_under_1m, 0)) as numsb_under_1m,
            SUM(COALESCE(a.amtsbrev_under_1m, 0)) as amtsb_under_1m,
            SUM(COALESCE(a.unknown_income_loans, 0)) as unknown_income_loans,
            SUM(COALESCE(a.unknown_income_amount, 0)) as unknown_income_amount
        FROM `{self.project_id}.bizsight.sb_county_summary` a
        WHERE CAST(a.year AS INT64) = {year}
        """

        return self.query(sql)