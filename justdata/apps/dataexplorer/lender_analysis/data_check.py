"""Pre-analysis data availability check."""
import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from justdata.apps.dataexplorer.config import PROJECT_ID
from justdata.apps.dataexplorer.data_utils import validate_years
from justdata.apps.dataexplorer.lender_analysis.filters import parse_lender_wizard_parameters
from justdata.shared.utils.bigquery_client import escape_sql_string, execute_query, get_bigquery_client

logger = logging.getLogger(__name__)


def check_lender_has_data(
    wizard_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Lightweight check to verify if a lender has any HMDA data in the selected geography.
    This should be called BEFORE starting the async job to provide early feedback.

    Args:
        wizard_data: Dictionary from wizard with lender, geography, and filters

    Returns:
        Dictionary with:
            - has_data: bool - True if lender has data, False otherwise
            - lender_name: str - Name of the lender
            - county_count: int - Number of counties in geography
            - year_range: str - Year range string (e.g., "2022-2024")
            - error: str - Error message if check failed (optional)
    """
    try:
        # Parse parameters
        lender_info, geography_scope, comparison_group, years, query_filters, counties = parse_lender_wizard_parameters(wizard_data)

        if not lender_info.get('lei'):
            return {
                'has_data': False,
                'error': 'Lender LEI is required',
                'lender_name': lender_info.get('name', 'Unknown'),
                'county_count': 0,
                'year_range': ''
            }

        # Validate years
        try:
            validated_years = validate_years(years)
        except ValueError as e:
            return {
                'has_data': False,
                'error': str(e),
                'lender_name': lender_info.get('name', 'Unknown'),
                'county_count': 0,
                'year_range': ''
            }

        # Format year range
        if validated_years:
            year_range = f"{min(validated_years)}-{max(validated_years)}" if len(validated_years) > 1 else str(validated_years[0])
        else:
            year_range = ''

        # Get BigQuery client
        client = get_bigquery_client(PROJECT_ID, app_name='dataexplorer')

        subject_lei = lender_info.get('lei')
        years_str = "', '".join(map(str, validated_years))
        years_int_str = ", ".join(map(str, validated_years))  # Unquoted for INT64 columns (de_hmda)

        # Build filter clauses from query_filters
        action_taken = query_filters.get('action_taken', ['1'])
        if len(action_taken) == 1:
            action_taken_clause = f"h.action_taken = '{action_taken[0]}'"
        else:
            action_taken_values = "', '".join(action_taken)
            action_taken_clause = f"h.action_taken IN ('{action_taken_values}')"

        occupancy = query_filters.get('occupancy', ['1'])
        if len(occupancy) == 1:
            occupancy_clause = f"h.occupancy_type = '{occupancy[0]}'"
        else:
            occupancy_values = "', '".join(occupancy)
            occupancy_clause = f"h.occupancy_type IN ('{occupancy_values}')"

        total_units = query_filters.get('total_units', ['1', '2', '3', '4'])
        if total_units == ['5+']:
            total_units_clause = "(h.total_units IS NOT NULL AND h.total_units NOT IN ('1','2','3','4'))"
        elif len(total_units) == 1:
            total_units_clause = f"h.total_units = '{total_units[0]}'"
        else:
            total_units_values = "', '".join(total_units)
            total_units_clause = f"h.total_units IN ('{total_units_values}')"

        construction = query_filters.get('construction', ['1'])
        if len(construction) == 1:
            construction_clause = f"h.construction_method = '{construction[0]}'"
        else:
            construction_values = "', '".join(construction)
            construction_clause = f"h.construction_method IN ('{construction_values}')"

        loan_type = query_filters.get('loan_type', ['1', '2', '3', '4'])
        if len(loan_type) == 1:
            loan_type_clause = f"h.loan_type = '{loan_type[0]}'"
        else:
            loan_type_values = "', '".join(loan_type)
            loan_type_clause = f"h.loan_type IN ('{loan_type_values}')"

        exclude_reverse = query_filters.get('exclude_reverse_mortgages', True)
        if exclude_reverse:
            reverse_clause = "(h.reverse_mortgage IS NULL OR h.reverse_mortgage != '1')"
        else:
            reverse_clause = "1=1"

        # Determine county count based on geography scope
        county_count = 0

        if geography_scope == 'custom':
            # Use provided counties
            county_count = len(counties) if counties else 0
            if county_count == 0:
                return {
                    'has_data': False,
                    'error': 'No counties selected for custom geography',
                    'lender_name': lender_info.get('name', 'Unknown'),
                    'county_count': 0,
                    'year_range': year_range
                }

            # Build geoids list for query
            geoids_escaped = [escape_sql_string(str(g)) for g in counties]
            geoids_str = "', '".join(geoids_escaped)

            # COUNT query for custom geography
            count_query = f"""
            SELECT COUNT(*) as loan_count
            FROM `{PROJECT_ID}.shared.de_hmda` h
            WHERE h.lei = '{escape_sql_string(subject_lei)}'
              AND h.activity_year IN ({years_int_str})
              AND CAST(h.county_code AS STRING) IN ('{geoids_str}')
              AND {action_taken_clause}
              AND {occupancy_clause}
              AND {total_units_clause}
              AND {construction_clause}
              AND {loan_type_clause}
              AND {reverse_clause}
            LIMIT 1
            """
        else:
            # For all_cbsas, loan_cbsas, branch_cbsas - count all loans for this lender
            # The geography is determined by where the lender has loans, so we just check if they have ANY loans
            count_query = f"""
            SELECT COUNT(*) as loan_count, COUNT(DISTINCT county_code) as county_count
            FROM `{PROJECT_ID}.shared.de_hmda` h
            WHERE h.lei = '{escape_sql_string(subject_lei)}'
              AND h.activity_year IN ({years_int_str})
              AND {action_taken_clause}
              AND {occupancy_clause}
              AND {total_units_clause}
              AND {construction_clause}
              AND {loan_type_clause}
              AND {reverse_clause}
              AND h.county_code IS NOT NULL
            LIMIT 1
            """

        # Execute count query
        result = execute_query(client, count_query)

        if result and len(result) > 0:
            loan_count = result[0].get('loan_count', 0)
            if geography_scope != 'custom':
                county_count = result[0].get('county_count', 0)

            has_data = loan_count > 0

            logger.info(f"Lender data check: {lender_info.get('name')} has {loan_count} loans in {county_count} counties for years {year_range}")

            return {
                'has_data': has_data,
                'lender_name': lender_info.get('name', 'Unknown'),
                'county_count': county_count,
                'year_range': year_range,
                'loan_count': loan_count
            }
        else:
            return {
                'has_data': False,
                'lender_name': lender_info.get('name', 'Unknown'),
                'county_count': county_count,
                'year_range': year_range,
                'loan_count': 0
            }

    except Exception as e:
        logger.error(f"Error checking lender data: {e}", exc_info=True)
        return {
            'has_data': None,  # Unknown - proceed with normal flow
            'error': str(e),
            'lender_name': wizard_data.get('lender', {}).get('name', 'Unknown'),
            'county_count': 0,
            'year_range': ''
        }


