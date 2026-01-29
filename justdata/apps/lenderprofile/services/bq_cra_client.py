#!/usr/bin/env python3
"""
BigQuery CRA Client for LenderProfile
Fetches CRA small business lending data from BigQuery.
"""

import logging
import os
from typing import Dict, Any, List, Optional
from google.cloud import bigquery
from google.oauth2 import service_account
import json

logger = logging.getLogger(__name__)


class BigQueryCRAClient:
    """
    Client for fetching CRA small business lending data from BigQuery.

    Data tables:
    - sb.disclosure: Lender-level, county-level SB lending data
    - sb.lenders: Lender crosswalk with respondent_id, LEI, name
    - sb.aggregate: Tract-level aggregate SB lending data
    """

    def __init__(self, project_id: str = None):
        """Initialize BigQuery CRA client."""
        self.project_id = project_id or os.getenv('GCP_PROJECT_ID', 'justdata-ncrc')
        self.client = self._get_client()

    def _get_client(self):
        """Get BigQuery client with credentials."""
        try:
            # Check for JSON credentials in environment
            cred_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
            if cred_json and cred_json.strip().startswith('{'):
                cred_dict = json.loads(cred_json)
                credentials = service_account.Credentials.from_service_account_info(cred_dict)
                return bigquery.Client(credentials=credentials, project=self.project_id)

            # Fall back to default credentials
            return bigquery.Client(project=self.project_id)
        except Exception as e:
            logger.error(f"Failed to initialize BigQuery client: {e}")
            return None

    def _execute_query(self, sql: str) -> List[Dict[str, Any]]:
        """Execute a BigQuery query and return results as list of dicts."""
        if not self.client:
            logger.warning("BigQuery client not available")
            return []

        try:
            query_job = self.client.query(sql)
            results = list(query_job.result())
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"BigQuery query error: {e}")
            return []

    def lookup_respondent_id(self, lei: str = None, fdic_cert: str = None,
                              institution_name: str = None) -> Optional[str]:
        """
        Look up respondent_id from LEI, FDIC cert, or institution name.

        The sb.lenders table contains the crosswalk between:
        - sb_resid (respondent_id)
        - sb_lender (lender name)
        - lei (Legal Entity Identifier)
        - fdic_cert (FDIC Certificate Number)

        Args:
            lei: Legal Entity Identifier
            fdic_cert: FDIC Certificate Number
            institution_name: Institution name for fuzzy matching

        Returns:
            respondent_id if found, None otherwise
        """
        if not self.client:
            return None

        # Try RSSD first if available (CRA uses RSSD via sb_rssd column)
        # Note: The sb.lenders table has sb_rssd, not lei or fdic_cert columns
        if fdic_cert:
            # FDIC cert might map to RSSD in some cases - try name search instead
            pass

        # Try name matching (primary method for CRA lookup)
        if institution_name:
            # Clean name for matching
            clean_name = institution_name.replace("'", "''").upper()
            # Try exact match first
            sql = f"""
            SELECT sb_resid, sb_lender, sb_rssd
            FROM `justdata-ncrc.bizsight.sb_lenders`
            WHERE UPPER(sb_lender) = '{clean_name}'
            LIMIT 1
            """
            results = self._execute_query(sql)
            if results:
                return results[0].get('sb_resid')

        # Try name matching (fuzzy) with various suffixes removed
        if institution_name:
            # Clean name for matching - remove common suffixes
            clean_name = institution_name.replace("'", "''").upper()
            # Remove common bank suffixes for better matching
            suffixes_to_remove = [
                ', NATIONAL ASSOCIATION', ', N.A.', ', NA',
                ' NATIONAL ASSOCIATION', ' N.A.', ' NA',
                ', FSB', ' FSB', ', SSB', ' SSB'
            ]
            base_name = clean_name
            for suffix in suffixes_to_remove:
                base_name = base_name.replace(suffix, '')

            sql = f"""
            SELECT sb_resid, sb_lender, sb_rssd
            FROM `justdata-ncrc.bizsight.sb_lenders`
            WHERE UPPER(sb_lender) LIKE '%{base_name}%'
               OR UPPER(sb_lender) LIKE '%{base_name.replace(" BANK", "")}%'
               OR UPPER(sb_lender) = '{base_name}'
               OR UPPER(sb_lender) = '{base_name} BANK'
            ORDER BY sb_year DESC
            LIMIT 5
            """
            results = self._execute_query(sql)
            if results:
                # Return first match (most recent year)
                logger.info(f"Found CRA lender match: {results[0].get('sb_lender')} -> respondent_id {results[0].get('sb_resid')}")
                return results[0].get('sb_resid')

        return None

    def get_lender_sb_lending_by_year(self, respondent_id: str, years: int = 5) -> Dict[str, Any]:
        """
        Get lender's small business lending volume by year.

        Args:
            respondent_id: The lender's CRA respondent ID
            years: Number of years to fetch (default 5)

        Returns:
            Dict with yearly lending data
        """
        if not self.client or not respondent_id:
            return {'years': [], 'loan_counts': [], 'loan_amounts': []}

        sql = f"""
        SELECT
            CAST(d.year AS INT64) as year,
            SUM(COALESCE(d.num_under_100k, 0) +
                COALESCE(d.num_100k_250k, 0) +
                COALESCE(d.num_250k_1m, 0)) as loan_count,
            SUM(COALESCE(d.amt_under_100k, 0) +
                COALESCE(d.amt_100k_250k, 0) +
                COALESCE(d.amt_250k_1m, 0)) as loan_amount_thousands
        FROM `{self.project_id}.sb.disclosure` d
        WHERE d.respondent_id = '{respondent_id}'
        GROUP BY year
        ORDER BY year DESC
        LIMIT {years}
        """

        results = self._execute_query(sql)

        # Sort by year ascending for chart display
        results = sorted(results, key=lambda x: x.get('year', 0))

        return {
            'years': [r.get('year') for r in results],
            'loan_counts': [r.get('loan_count', 0) for r in results],
            'loan_amounts': [r.get('loan_amount_thousands', 0) for r in results]  # In thousands
        }

    def get_national_sb_lending_by_year(self, years: int = 5) -> Dict[str, Any]:
        """
        Get national small business lending totals by year.

        Args:
            years: Number of years to fetch (default 5)

        Returns:
            Dict with yearly national totals
        """
        if not self.client:
            return {'years': [], 'loan_counts': [], 'loan_amounts': []}

        sql = f"""
        SELECT
            CAST(d.year AS INT64) as year,
            SUM(COALESCE(d.num_under_100k, 0) +
                COALESCE(d.num_100k_250k, 0) +
                COALESCE(d.num_250k_1m, 0)) as loan_count,
            SUM(COALESCE(d.amt_under_100k, 0) +
                COALESCE(d.amt_100k_250k, 0) +
                COALESCE(d.amt_250k_1m, 0)) as loan_amount_thousands
        FROM `{self.project_id}.sb.disclosure` d
        GROUP BY year
        ORDER BY year DESC
        LIMIT {years}
        """

        results = self._execute_query(sql)

        # Sort by year ascending
        results = sorted(results, key=lambda x: x.get('year', 0))

        return {
            'years': [r.get('year') for r in results],
            'loan_counts': [r.get('loan_count', 0) for r in results],
            'loan_amounts': [r.get('loan_amount_thousands', 0) for r in results]
        }

    def get_lender_sb_lending_by_state(self, respondent_id: str, top_n: int = 10) -> Dict[str, Any]:
        """
        Get lender's small business lending breakdown by state (most recent year).

        Args:
            respondent_id: The lender's CRA respondent ID
            top_n: Number of top states to return (default 10)

        Returns:
            Dict with state-level lending data and percentages
        """
        if not self.client or not respondent_id:
            return {'states': [], 'loan_counts': [], 'percentages': []}

        sql = f"""
        WITH lender_totals AS (
            SELECT
                SUBSTR(LPAD(CAST(d.geoid5 AS STRING), 5, '0'), 1, 2) as state_fips,
                SUM(COALESCE(d.num_under_100k, 0) +
                    COALESCE(d.num_100k_250k, 0) +
                    COALESCE(d.num_250k_1m, 0)) as loan_count
            FROM `{self.project_id}.sb.disclosure` d
            WHERE d.respondent_id = '{respondent_id}'
                AND d.year = (SELECT MAX(year) FROM `{self.project_id}.sb.disclosure` WHERE respondent_id = '{respondent_id}')
            GROUP BY state_fips
        ),
        total_loans AS (
            SELECT SUM(loan_count) as total FROM lender_totals
        )
        SELECT
            lt.state_fips,
            COALESCE(g.state, 'Unknown') as state_name,
            lt.loan_count,
            ROUND(100.0 * lt.loan_count / NULLIF(t.total, 0), 1) as percentage
        FROM lender_totals lt
        CROSS JOIN total_loans t
        LEFT JOIN `justdata-ncrc.shared.cbsa_to_county` g
            ON lt.state_fips = SUBSTR(LPAD(CAST(g.geoid5 AS STRING), 5, '0'), 1, 2)
        GROUP BY lt.state_fips, g.state, lt.loan_count, t.total
        ORDER BY loan_count DESC
        LIMIT {top_n}
        """

        results = self._execute_query(sql)

        return {
            'states': [r.get('state_name', 'Unknown') for r in results],
            'state_fips': [r.get('state_fips') for r in results],
            'loan_counts': [r.get('loan_count', 0) for r in results],
            'percentages': [r.get('percentage', 0) for r in results]
        }

    def get_lender_sb_lending_states_by_year(self, respondent_id: str, years: int = 5, top_n: int = 10) -> Dict[str, Dict[str, int]]:
        """
        Get lender's small business lending by state for each year.

        Returns a dict keyed by year, with state -> loan_amount values.

        Args:
            respondent_id: The lender's CRA respondent ID
            years: Number of years to fetch
            top_n: Number of top states per year

        Returns:
            Dict like {2023: {'OH': 500000, 'MI': 300000, ...}, 2022: {...}, ...}
        """
        if not self.client or not respondent_id:
            return {}

        sql = f"""
        WITH yearly_states AS (
            SELECT
                CAST(d.year AS INT64) as year,
                SUBSTR(LPAD(CAST(d.geoid5 AS STRING), 5, '0'), 1, 2) as state_fips,
                SUM(COALESCE(d.amt_under_100k, 0) +
                    COALESCE(d.amt_100k_250k, 0) +
                    COALESCE(d.amt_250k_1m, 0)) as loan_amount
            FROM `{self.project_id}.sb.disclosure` d
            WHERE d.respondent_id = '{respondent_id}'
            GROUP BY year, state_fips
        ),
        state_names AS (
            SELECT DISTINCT
                SUBSTR(LPAD(CAST(geoid5 AS STRING), 5, '0'), 1, 2) as state_fips,
                state as state_abbr
            FROM `justdata-ncrc.shared.cbsa_to_county`
            WHERE state IS NOT NULL
        )
        SELECT
            ys.year,
            COALESCE(sn.state_abbr, ys.state_fips) as state,
            ys.loan_amount
        FROM yearly_states ys
        LEFT JOIN state_names sn ON ys.state_fips = sn.state_fips
        ORDER BY year DESC, loan_amount DESC
        """

        results = self._execute_query(sql)

        # Organize by year
        states_by_year = {}
        for row in results:
            year = row.get('year')
            state = row.get('state', 'Unknown')
            amount = row.get('loan_amount', 0)

            if year not in states_by_year:
                states_by_year[year] = {}

            # Only keep top N states per year
            if len(states_by_year[year]) < top_n:
                states_by_year[year][state] = amount

        return states_by_year

    def get_lender_info(self, respondent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get lender information from the lenders table.

        Args:
            respondent_id: The lender's CRA respondent ID

        Returns:
            Dict with lender info or None
        """
        if not self.client or not respondent_id:
            return None

        sql = f"""
        SELECT *
        FROM `justdata-ncrc.bizsight.sb_lenders`
        WHERE sb_resid = '{respondent_id}'
        LIMIT 1
        """

        results = self._execute_query(sql)
        return results[0] if results else None

    def get_sb_lending_summary(self, lei: str = None, fdic_cert: str = None,
                                institution_name: str = None) -> Dict[str, Any]:
        """
        Get complete small business lending summary for a lender.

        This is the main method called by data_collector.py

        Args:
            lei: Legal Entity Identifier
            fdic_cert: FDIC Certificate Number
            institution_name: Institution name

        Returns:
            Complete SB lending summary dict
        """
        # Look up respondent_id
        respondent_id = self.lookup_respondent_id(lei, fdic_cert, institution_name)

        if not respondent_id:
            logger.warning(f"Could not find CRA respondent_id for institution: {institution_name}")
            return {
                'has_data': False,
                'error': 'Institution not found in CRA data'
            }

        # Get lender info
        lender_info = self.get_lender_info(respondent_id)

        # Get yearly lending data
        yearly_data = self.get_lender_sb_lending_by_year(respondent_id, years=5)

        # Get national totals for comparison
        national_data = self.get_national_sb_lending_by_year(years=5)

        # Get top states
        state_data = self.get_lender_sb_lending_by_state(respondent_id, top_n=10)

        # Get states by year for interactive chart
        states_by_year = self.get_lender_sb_lending_states_by_year(respondent_id, years=5, top_n=10)

        # Calculate market share if we have data
        market_share = []
        if yearly_data['years'] and national_data['years']:
            for i, year in enumerate(yearly_data['years']):
                if year in national_data['years']:
                    nat_idx = national_data['years'].index(year)
                    nat_total = national_data['loan_counts'][nat_idx]
                    lender_total = yearly_data['loan_counts'][i]
                    share = round(100.0 * lender_total / nat_total, 3) if nat_total > 0 else 0
                    market_share.append({
                        'year': year,
                        'share': share
                    })

        return {
            'has_data': True,
            'respondent_id': respondent_id,
            'lender_name': lender_info.get('sb_lender') if lender_info else institution_name,
            'yearly_lending': yearly_data,
            'national_lending': national_data,
            'top_states': state_data,
            'states_by_year': states_by_year,
            'market_share': market_share,
            'data_source': 'CRA Small Business Lending Data'
        }


# Test function
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    client = BigQueryCRAClient()

    # Test with Fifth Third Bank
    print("Testing CRA Client...")
    print("=" * 50)

    # Try to look up respondent_id
    respondent_id = client.lookup_respondent_id(institution_name="Fifth Third Bank")
    print(f"Respondent ID for Fifth Third Bank: {respondent_id}")

    if respondent_id:
        # Get summary
        summary = client.get_sb_lending_summary(institution_name="Fifth Third Bank")
        print(f"\nSB Lending Summary:")
        print(f"  Has Data: {summary.get('has_data')}")
        print(f"  Lender Name: {summary.get('lender_name')}")
        print(f"  Years: {summary.get('yearly_lending', {}).get('years')}")
        print(f"  Loan Counts: {summary.get('yearly_lending', {}).get('loan_counts')}")
        print(f"\n  Top States: {summary.get('top_states', {}).get('states')}")
        print(f"  State Percentages: {summary.get('top_states', {}).get('percentages')}")
