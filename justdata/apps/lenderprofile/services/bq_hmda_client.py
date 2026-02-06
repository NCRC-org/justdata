#!/usr/bin/env python3
"""
BigQuery-based HMDA data client for lending footprint analysis.
Queries HMDA data to determine where lenders concentrate their lending activity.

This is especially important for mortgage companies that don't have branches,
allowing us to determine their geographic footprint based on lending patterns.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from justdata.shared.utils.bigquery_client import get_bigquery_client, escape_sql_string

logger = logging.getLogger(__name__)


class BigQueryHMDAClient:
    """Client for fetching HMDA lending data from BigQuery."""

    # Class-level cache for national data (shared across all instances)
    _national_cache = {}
    _national_cache_timestamp = None

    def __init__(self, project_id: str = None):
        """
        Initialize BigQuery HMDA client.

        Args:
            project_id: GCP project ID (defaults to environment variable)
        """
        self.project_id = project_id or os.getenv('JUSTDATA_PROJECT_ID', 'justdata-ncrc')
        self.client = None

    def _get_client(self):
        """Get BigQuery client (lazy initialization)."""
        if self.client is None:
            self.client = get_bigquery_client(self.project_id)
        return self.client

    def get_top_metros(
        self,
        lei: str,
        year: int = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get top metros where a lender concentrates their lending activity.

        Uses HMDA data to find MSA/MD codes with highest application counts.
        Joins with shared.cbsa_to_county to get proper metro names.

        Args:
            lei: Legal Entity Identifier for the lender
            year: Year to analyze (defaults to most recent available)
            limit: Number of top metros to return (default 10)

        Returns:
            List of metro dictionaries with:
            - msa_code: MSA/MD code
            - msa_name: Metro area name
            - application_count: Number of applications
            - loan_count: Number of originations
            - total_amount: Total loan amount in thousands
            - pct_of_total: Percentage of lender's total applications
        """
        try:
            client = self._get_client()
            lei_escaped = escape_sql_string(lei.upper())

            # If no year specified, find the most recent year with data
            if year is None:
                year = self._get_most_recent_year(lei_escaped)
                if year is None:
                    logger.warning(f"No HMDA data found for LEI: {lei}")
                    return []

            # Query for top metros by application count
            # Join with shared.cbsa_to_county to get proper CBSA names
            query = f"""
            WITH lender_activity AS (
                SELECT
                    CAST(derived_msa_md AS STRING) as msa_code,
                    state_code,
                    COUNT(*) as application_count,
                    SUM(CASE WHEN action_taken = '1' THEN 1 ELSE 0 END) as loan_count,
                    SUM(CASE WHEN action_taken = '1' THEN loan_amount ELSE 0 END) as total_amount
                FROM `{self.project_id}.hmda.hmda`
                WHERE lei = '{lei_escaped}'
                  AND activity_year = '{year}'
                  AND derived_msa_md IS NOT NULL
                  AND CAST(derived_msa_md AS STRING) != ''
                  AND CAST(derived_msa_md AS STRING) != 'NA'
                GROUP BY msa_code, state_code
            ),
            total_apps AS (
                SELECT SUM(application_count) as total
                FROM lender_activity
            ),
            cbsa_names AS (
                SELECT DISTINCT
                    CAST(cbsa_code AS STRING) as cbsa_code,
                    CBSA as cbsa_name
                FROM `justdata-ncrc.shared.cbsa_to_county`
                WHERE cbsa_code IS NOT NULL
            )
            SELECT
                la.msa_code,
                COALESCE(cn.cbsa_name, CONCAT('MSA ', la.msa_code)) as msa_name,
                la.state_code,
                la.application_count,
                la.loan_count,
                la.total_amount,
                ROUND(100.0 * la.application_count / NULLIF(ta.total, 0), 1) as pct_of_total
            FROM lender_activity la
            CROSS JOIN total_apps ta
            LEFT JOIN cbsa_names cn ON la.msa_code = cn.cbsa_code
            ORDER BY la.application_count DESC
            LIMIT {limit}
            """

            logger.info(f"Querying top {limit} metros for LEI {lei} in year {year}")

            query_job = client.query(query)
            results = list(query_job.result())

            metros = []
            for row in results:
                metros.append({
                    'msa_code': row.msa_code,
                    'msa_name': row.msa_name or f"MSA {row.msa_code}",
                    'state_code': row.state_code,
                    'application_count': row.application_count,
                    'loan_count': row.loan_count,
                    'total_amount': row.total_amount,
                    'pct_of_total': row.pct_of_total
                })

            logger.info(f"Found {len(metros)} metros for LEI {lei} in year {year}")
            return metros

        except Exception as e:
            logger.error(f"Error getting top metros for LEI {lei}: {e}", exc_info=True)
            return []

    def get_lending_summary(
        self,
        lei: str,
        years: List[int] = None
    ) -> Dict[str, Any]:
        """
        Get lending activity summary for a lender.

        Args:
            lei: Legal Entity Identifier
            years: List of years to analyze (defaults to last 3 years)

        Returns:
            Dictionary with:
            - total_applications: Total application count
            - total_originations: Total loan originations
            - total_volume: Total loan volume in thousands
            - approval_rate: Loan origination rate
            - top_loan_purposes: Breakdown by loan purpose
            - year_over_year: YoY comparison
        """
        try:
            client = self._get_client()
            lei_escaped = escape_sql_string(lei.upper())

            # Default to last 3 years
            if years is None:
                years = [2023, 2022, 2021]

            years_str = ', '.join(f"'{y}'" for y in years)

            query = f"""
            SELECT
                activity_year,
                loan_purpose,
                COUNT(*) as applications,
                SUM(CASE WHEN action_taken = '1' THEN 1 ELSE 0 END) as originations,
                SUM(CASE WHEN action_taken = '1' THEN loan_amount ELSE 0 END) as volume
            FROM `{self.project_id}.hmda.hmda`
            WHERE lei = '{lei_escaped}'
              AND activity_year IN ({years_str})
            GROUP BY activity_year, loan_purpose
            ORDER BY activity_year DESC, applications DESC
            """

            query_job = client.query(query)
            results = list(query_job.result())

            # Aggregate results
            by_year = {}
            by_purpose = {}

            for row in results:
                year = row.activity_year
                purpose = self._get_purpose_name(row.loan_purpose)

                if year not in by_year:
                    by_year[year] = {
                        'applications': 0,
                        'originations': 0,
                        'volume': 0
                    }

                by_year[year]['applications'] += row.applications
                by_year[year]['originations'] += row.originations
                by_year[year]['volume'] += row.volume or 0

                if purpose not in by_purpose:
                    by_purpose[purpose] = {
                        'applications': 0,
                        'originations': 0
                    }

                by_purpose[purpose]['applications'] += row.applications
                by_purpose[purpose]['originations'] += row.originations

            # Calculate totals
            total_apps = sum(y['applications'] for y in by_year.values())
            total_origs = sum(y['originations'] for y in by_year.values())
            total_vol = sum(y['volume'] for y in by_year.values())

            # Calculate YoY change
            yoy_change = None
            sorted_years = sorted(by_year.keys(), reverse=True)
            if len(sorted_years) >= 2:
                current = by_year[sorted_years[0]]['applications']
                previous = by_year[sorted_years[1]]['applications']
                if previous > 0:
                    yoy_change = round(100.0 * (current - previous) / previous, 1)

            return {
                'total_applications': total_apps,
                'total_originations': total_origs,
                'total_volume': total_vol,
                'approval_rate': round(100.0 * total_origs / max(total_apps, 1), 1),
                'by_year': by_year,
                'by_purpose': by_purpose,
                'yoy_change': yoy_change,
                'years_analyzed': sorted_years
            }

        except Exception as e:
            logger.error(f"Error getting lending summary for LEI {lei}: {e}", exc_info=True)
            return {}

    def get_lending_footprint(
        self,
        lei: str,
        year: int = None,
        include_states: bool = True,
        include_metros: bool = True,
        metro_limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get comprehensive lending footprint for a lender.

        Combines top metros and state breakdown to show where the lender operates.

        Args:
            lei: Legal Entity Identifier
            year: Year to analyze
            include_states: Include state-level breakdown
            include_metros: Include metro-level breakdown
            metro_limit: Number of top metros to return

        Returns:
            Dictionary with:
            - top_metros: List of top metro areas
            - states: State-level breakdown
            - total_states: Number of states with activity
            - concentration: Geographic concentration metrics
        """
        result = {
            'top_metros': [],
            'states': [],
            'total_states': 0,
            'total_metros': 0,
            'concentration': {}
        }

        try:
            client = self._get_client()
            lei_escaped = escape_sql_string(lei.upper())

            # Get most recent year if not specified
            if year is None:
                year = self._get_most_recent_year(lei_escaped)
                if year is None:
                    return result

            result['year'] = year

            # Get top metros
            if include_metros:
                result['top_metros'] = self.get_top_metros(lei, year, metro_limit)
                result['total_metros'] = len(result['top_metros'])

            # Get state breakdown (action_taken 1-5 are applications)
            if include_states:
                state_query = f"""
                SELECT
                    state_code,
                    COUNT(*) as application_count,
                    SUM(CASE WHEN action_taken = '1' THEN 1 ELSE 0 END) as loan_count,
                    SUM(CASE WHEN action_taken = '1' THEN loan_amount ELSE 0 END) as total_amount
                FROM `{self.project_id}.hmda.hmda`
                WHERE lei = '{lei_escaped}'
                  AND activity_year = '{year}'
                  AND action_taken IN ('1', '2', '3', '4', '5')
                  AND state_code IS NOT NULL
                  AND state_code != ''
                GROUP BY state_code
                ORDER BY application_count DESC
                """

                query_job = client.query(state_query)
                state_results = list(query_job.result())

                total_apps = sum(r.application_count for r in state_results)

                for row in state_results:
                    result['states'].append({
                        'state_code': row.state_code,
                        'application_count': row.application_count,
                        'loan_count': row.loan_count,
                        'total_amount': row.total_amount,
                        'pct_of_total': round(100.0 * row.application_count / max(total_apps, 1), 1)
                    })

                result['total_states'] = len(result['states'])

            # Calculate concentration metrics
            if result['top_metros']:
                top_5_pct = sum(m.get('pct_of_total', 0) for m in result['top_metros'][:5])
                result['concentration'] = {
                    'top_5_metros_pct': round(top_5_pct, 1),
                    'is_concentrated': top_5_pct > 70,  # >70% in top 5 metros = concentrated
                    'is_national': result['total_states'] >= 40  # Active in 40+ states = national
                }

            return result

        except Exception as e:
            logger.error(f"Error getting lending footprint for LEI {lei}: {e}", exc_info=True)
            return result

    def get_lending_footprint_history(
        self,
        lei: str,
        years: int = 5
    ) -> Dict[str, Any]:
        """
        Get multi-year lending footprint for trend comparison.

        Args:
            lei: Legal Entity Identifier
            years: Number of years of history to fetch

        Returns:
            Dictionary with:
            - by_year: Total applications by year for lender
            - states_by_year: Top states by year
            - national_by_year: National total applications by year
        """
        result = {
            'by_year': {},
            'states_by_year': {},
            'national_by_year': {}
        }

        try:
            client = self._get_client()
            lei_escaped = escape_sql_string(lei.upper())

            # Get lender totals by year (action_taken 1-5 are applications)
            lender_query = f"""
            SELECT
                activity_year,
                COUNT(*) as application_count
            FROM `{self.project_id}.hmda.hmda`
            WHERE lei = '{lei_escaped}'
              AND action_taken IN ('1', '2', '3', '4', '5')
            GROUP BY activity_year
            ORDER BY activity_year DESC
            LIMIT {years}
            """

            query_job = client.query(lender_query)
            for row in query_job.result():
                result['by_year'][str(row.activity_year)] = row.application_count

            # Get lender states by year (action_taken 1-5 are applications)
            states_query = f"""
            SELECT
                activity_year,
                state_code,
                COUNT(*) as application_count
            FROM `{self.project_id}.hmda.hmda`
            WHERE lei = '{lei_escaped}'
              AND action_taken IN ('1', '2', '3', '4', '5')
              AND state_code IS NOT NULL
              AND state_code != ''
            GROUP BY activity_year, state_code
            ORDER BY activity_year, application_count DESC
            """

            query_job = client.query(states_query)
            year_states = {}
            for row in query_job.result():
                year = str(row.activity_year)
                if year not in year_states:
                    year_states[year] = {}
                year_states[year][row.state_code] = row.application_count

            # Keep all states per year, sorted by count descending
            for year, states in year_states.items():
                sorted_states = dict(sorted(states.items(), key=lambda x: x[1], reverse=True))
                result['states_by_year'][year] = sorted_states

            # Get national totals by year (action_taken 1-5 are applications)
            national_query = f"""
            SELECT
                activity_year,
                COUNT(*) as application_count
            FROM `{self.project_id}.hmda.hmda`
            WHERE CAST(activity_year AS INT64) >= (SELECT CAST(MAX(activity_year) AS INT64) - {years} FROM `{self.project_id}.hmda.hmda`)
              AND action_taken IN ('1', '2', '3', '4', '5')
            GROUP BY activity_year
            ORDER BY activity_year
            """

            query_job = client.query(national_query)
            for row in query_job.result():
                result['national_by_year'][str(row.activity_year)] = row.application_count

            logger.info(f"Got lending footprint history for LEI {lei}: {len(result['by_year'])} years")
            return result

        except Exception as e:
            logger.error(f"Error getting lending footprint history for LEI {lei}: {e}", exc_info=True)
            return result

    def _get_most_recent_year(self, lei_escaped: str) -> Optional[int]:
        """Get the most recent year with HMDA data for this lender."""
        try:
            client = self._get_client()

            query = f"""
            SELECT MAX(activity_year) as max_year
            FROM `{self.project_id}.hmda.hmda`
            WHERE lei = '{lei_escaped}'
            """

            query_job = client.query(query)
            result = list(query_job.result())

            if result and result[0].max_year:
                return result[0].max_year
            return None

        except Exception as e:
            logger.error(f"Error getting most recent year: {e}")
            return None

    def find_lei_by_name(self, institution_name: str) -> Optional[str]:
        """
        Find LEI by searching the HMDA lenders table by institution name.

        Useful when the GLEIF LEI doesn't match the HMDA LEI (e.g., holding company vs bank).

        Args:
            institution_name: Name of the institution to search for

        Returns:
            LEI if found, None otherwise
        """
        try:
            client = self._get_client()
            name_escaped = escape_sql_string(institution_name.lower())

            # Search for matching lender in lenders18 table
            query = f"""
            SELECT lei, respondent_name
            FROM `justdata-ncrc.lendsight.lenders18`
            WHERE LOWER(respondent_name) LIKE '%{name_escaped}%'
            ORDER BY respondent_name
            LIMIT 5
            """

            query_job = client.query(query)
            results = list(query_job.result())

            if results:
                # Return the first match (usually the main bank)
                logger.info(f"Found HMDA LEI for '{institution_name}': {results[0].lei} ({results[0].respondent_name})")
                return results[0].lei

            logger.debug(f"No HMDA lender found for name: {institution_name}")
            return None

        except Exception as e:
            logger.error(f"Error searching for LEI by name '{institution_name}': {e}")
            return None

    def get_hierarchy_leis(self, lei: str) -> List[Dict[str, Any]]:
        """
        Get all LEIs in the corporate hierarchy from GLEIF.

        Args:
            lei: Starting LEI

        Returns:
            List of dicts with lei and name for all entities in hierarchy
        """
        try:
            client = self._get_client()
            lei_escaped = escape_sql_string(lei.upper())

            # Get the entity and find its ultimate parent
            query = f"""
            WITH RECURSIVE
            -- First get the starting entity
            start_entity AS (
                SELECT lei, gleif_legal_name, ultimate_parent_lei
                FROM `{self.project_id}.justdata.gleif_names`
                WHERE lei = '{lei_escaped}'
            ),
            -- Get the ultimate parent LEI
            parent_lei AS (
                SELECT COALESCE(ultimate_parent_lei, lei) as root_lei
                FROM start_entity
            ),
            -- Get all entities that share this ultimate parent
            all_entities AS (
                SELECT lei, gleif_legal_name
                FROM `{self.project_id}.justdata.gleif_names`
                WHERE ultimate_parent_lei = (SELECT root_lei FROM parent_lei)
                   OR lei = (SELECT root_lei FROM parent_lei)
            )
            SELECT lei, gleif_legal_name as name
            FROM all_entities
            ORDER BY gleif_legal_name
            """

            query_job = client.query(query)
            results = []
            for row in query_job.result():
                results.append({'lei': row.lei, 'name': row.name})

            if not results:
                # Fallback: just return the input LEI
                logger.warning(f"No hierarchy found for LEI {lei}, using single LEI")
                return [{'lei': lei, 'name': None}]

            logger.info(f"Found {len(results)} entities in hierarchy for LEI {lei}")
            return results

        except Exception as e:
            logger.error(f"Error getting hierarchy for LEI {lei}: {e}")
            return [{'lei': lei, 'name': None}]

    def get_hmda_by_purpose(self, leis: List[str], years: int = 5) -> Dict[str, Any]:
        """
        Get HMDA applications by loan purpose for stacked column chart.

        Queries HMDA for all LEIs and returns data broken down by loan purpose and year.

        Args:
            leis: List of LEIs to query
            years: Number of years of history

        Returns:
            Dictionary with:
            - by_purpose_year: Dict of {purpose: {year: count}}
            - by_year: Total applications by year
            - states_by_year: Aggregated states by year
            - national_by_year: National totals by year
        """
        result = {
            'by_purpose_year': {},
            'by_year': {},
            'states_by_year': {},
            'national_by_year': {},
            'national_by_purpose_year': {}
        }

        if not leis:
            return result

        try:
            client = self._get_client()

            # Escape all LEIs
            lei_list = [f"'{escape_sql_string(lei.upper())}'" for lei in leis]
            lei_in_clause = ', '.join(lei_list)

            # Get applications by loan purpose and year
            purpose_query = f"""
            SELECT
                activity_year,
                CASE
                    WHEN loan_purpose = '1' THEN 'Purchase'
                    WHEN loan_purpose IN ('31', '32') THEN 'Refinance'
                    WHEN loan_purpose IN ('2', '4') THEN 'Home Equity'
                    ELSE 'Other'
                END as purpose,
                COUNT(*) as application_count
            FROM `{self.project_id}.hmda.hmda`
            WHERE lei IN ({lei_in_clause})
              AND action_taken IN ('1', '2', '3', '4', '5')
            GROUP BY activity_year, purpose
            ORDER BY activity_year DESC, application_count DESC
            """

            query_job = client.query(purpose_query)
            for row in query_job.result():
                purpose = row.purpose
                year = str(row.activity_year)

                if purpose not in result['by_purpose_year']:
                    result['by_purpose_year'][purpose] = {}
                result['by_purpose_year'][purpose][year] = row.application_count

                # Also track total by year
                if year not in result['by_year']:
                    result['by_year'][year] = 0
                result['by_year'][year] += row.application_count

            # Get states by year (aggregated across all entities)
            states_query = f"""
            SELECT
                activity_year,
                state_code,
                COUNT(*) as application_count
            FROM `{self.project_id}.hmda.hmda`
            WHERE lei IN ({lei_in_clause})
              AND action_taken IN ('1', '2', '3', '4', '5')
              AND state_code IS NOT NULL
              AND state_code != ''
            GROUP BY activity_year, state_code
            ORDER BY activity_year, application_count DESC
            """

            query_job = client.query(states_query)
            year_states = {}
            for row in query_job.result():
                year = str(row.activity_year)
                if year not in year_states:
                    year_states[year] = {}
                year_states[year][row.state_code] = row.application_count

            for year, states in year_states.items():
                sorted_states = dict(sorted(states.items(), key=lambda x: x[1], reverse=True))
                result['states_by_year'][year] = sorted_states

            # Get national totals from cache or query
            import time
            cache_key = f'national_{years}'
            cache_max_age = 86400  # 24 hours

            # Check if we have valid cached data
            if (cache_key in BigQueryHMDAClient._national_cache and
                BigQueryHMDAClient._national_cache_timestamp and
                time.time() - BigQueryHMDAClient._national_cache_timestamp < cache_max_age):
                cached = BigQueryHMDAClient._national_cache[cache_key]
                result['national_by_year'] = cached.get('national_by_year', {})
                result['national_by_purpose_year'] = cached.get('national_by_purpose_year', {})
                logger.info("Using cached national HMDA data")
            else:
                # Query national data
                national_query = f"""
                SELECT
                    activity_year,
                    CASE
                        WHEN loan_purpose = '1' THEN 'Purchase'
                        WHEN loan_purpose IN ('31', '32') THEN 'Refinance'
                        WHEN loan_purpose IN ('2', '4') THEN 'Home Equity'
                        ELSE 'Other'
                    END as purpose,
                    COUNT(*) as application_count
                FROM `{self.project_id}.hmda.hmda`
                WHERE CAST(activity_year AS INT64) >= (SELECT MAX(CAST(activity_year AS INT64)) - {years} FROM `{self.project_id}.hmda.hmda`)
                  AND action_taken IN ('1', '2', '3', '4', '5')
                GROUP BY activity_year, purpose
                ORDER BY activity_year
                """

                query_job = client.query(national_query)
                for row in query_job.result():
                    year = str(row.activity_year)
                    purpose = row.purpose

                    if year not in result['national_by_year']:
                        result['national_by_year'][year] = 0
                    result['national_by_year'][year] += row.application_count

                    if purpose not in result['national_by_purpose_year']:
                        result['national_by_purpose_year'][purpose] = {}
                    result['national_by_purpose_year'][purpose][year] = row.application_count

                # Cache the national data
                BigQueryHMDAClient._national_cache[cache_key] = {
                    'national_by_year': result['national_by_year'],
                    'national_by_purpose_year': result['national_by_purpose_year']
                }
                BigQueryHMDAClient._national_cache_timestamp = time.time()
                logger.info("Cached national HMDA data for future requests")

            logger.info(f"Got HMDA data by purpose across {len(result['by_year'])} years")
            return result

        except Exception as e:
            logger.error(f"Error getting HMDA by purpose: {e}", exc_info=True)
            return result

    def _get_purpose_name(self, purpose_code) -> str:
        """Convert loan purpose code to name."""
        purpose_map = {
            1: 'Home Purchase',
            2: 'Home Improvement',
            31: 'Refinancing',
            32: 'Cash-out Refinancing',
            4: 'Other Purpose',
            5: 'Not Applicable'
        }
        return purpose_map.get(purpose_code, f'Purpose {purpose_code}')


def test_hmda_client():
    """Test the HMDA client with a sample lender."""
    from justdata.shared.utils.unified_env import ensure_unified_env_loaded
    ensure_unified_env_loaded(verbose=True)

    client = BigQueryHMDAClient()

    # Test with Fifth Third Bank's LEI
    test_lei = "QFROUN1UWUYU0DVIWD51"  # Fifth Third Bank

    print(f"\nTesting HMDA client with LEI: {test_lei}")
    print("=" * 60)

    # Get lending footprint
    footprint = client.get_lending_footprint(test_lei)

    print(f"\nLending Footprint for {footprint.get('year', 'N/A')}:")
    print(f"  Total States: {footprint.get('total_states', 0)}")
    print(f"  Total Metros: {footprint.get('total_metros', 0)}")

    if footprint.get('concentration'):
        conc = footprint['concentration']
        print(f"  Top 5 Metros: {conc.get('top_5_metros_pct', 0)}% of volume")
        print(f"  Is Concentrated: {conc.get('is_concentrated', False)}")
        print(f"  Is National: {conc.get('is_national', False)}")

    print("\nTop 10 Metros:")
    for i, metro in enumerate(footprint.get('top_metros', [])[:10], 1):
        print(f"  {i}. {metro['msa_name']} ({metro['msa_code']})")
        print(f"     Applications: {metro['application_count']:,} ({metro['pct_of_total']}%)")

    print("\nTop 5 States:")
    for i, state in enumerate(footprint.get('states', [])[:5], 1):
        print(f"  {i}. {state['state_code']}: {state['application_count']:,} apps ({state['pct_of_total']}%)")


if __name__ == '__main__':
    test_hmda_client()
