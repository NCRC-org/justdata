#!/usr/bin/env python3
"""
DataExplorer Lender Analysis Core Logic
Handles lender-based analysis with peer comparison for HMDA mortgage lending data.
"""

import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime

from justdata.apps.dataexplorer.config import PROJECT_ID
from justdata.apps.dataexplorer.data_utils import validate_years, get_peer_lenders
from justdata.apps.dataexplorer.lender_report_builder import build_lender_report
from justdata.shared.utils.progress_tracker import ProgressTracker, store_analysis_result
from justdata.shared.utils.bigquery_client import get_bigquery_client, execute_query, escape_sql_string
from justdata.shared.utils.unified_env import get_unified_config
from justdata.apps.lendsight.core import load_sql_template
import logging

logger = logging.getLogger(__name__)


def _format_all_metros_for_excel(metros_df: pd.DataFrame, years: List[int], PROJECT_ID: str, client) -> List[Dict[str, Any]]:
    """
    Format all metros data for Excel export.
    Aggregates by CBSA and loan purpose, includes all CBSAs (not just top 10).
    """
    try:
        if metros_df.empty:
            return []
        
        # Get CBSA information for counties
        from justdata.apps.dataexplorer.area_report_builder import filter_df_by_loan_purpose
        
        # Get unique counties
        if 'geoid5' not in metros_df.columns and 'county_code' in metros_df.columns:
            metros_df['geoid5'] = metros_df['county_code'].astype(str)
        
        unique_counties = metros_df['geoid5'].unique().tolist() if 'geoid5' in metros_df.columns else []
        
        # Query CBSA information
        cbsa_lookup = {}
        if unique_counties:
            # Batch counties to avoid long IN clauses
            batch_size = 200
            for i in range(0, len(unique_counties), batch_size):
                batch = unique_counties[i:i + batch_size]
                counties_str = "', '".join([str(c) for c in batch if pd.notna(c)])
                
                cbsa_query = f"""
                SELECT DISTINCT
                    CAST(c.cbsa_code AS STRING) as cbsa_code,
                    c.CBSA as cbsa_name,
                    CAST(c.geoid5 AS STRING) as geoid5
                FROM `{PROJECT_ID}.shared.cbsa_to_county` c
                WHERE CAST(c.geoid5 AS STRING) IN ('{counties_str}')
                  AND c.cbsa_code IS NOT NULL
                  AND c.CBSA IS NOT NULL
                  AND c.cbsa_code != '99999'
                  AND c.CBSA NOT LIKE 'Rural%'
                """
                
                cbsa_results = execute_query(client, cbsa_query)
                if cbsa_results:
                    for row in cbsa_results:
                        geoid5 = str(row.get('geoid5', ''))
                        cbsa_code = str(row.get('cbsa_code', ''))
                        cbsa_name = str(row.get('cbsa_name', ''))
                        if geoid5 and cbsa_code:
                            if geoid5 not in cbsa_lookup:
                                cbsa_lookup[geoid5] = []
                            cbsa_lookup[geoid5].append({'code': cbsa_code, 'name': cbsa_name})
        
        # Add CBSA info to metros_df
        def get_cbsa_info(county_code):
            county_str = str(county_code) if pd.notna(county_code) else ''
            if county_str in cbsa_lookup and cbsa_lookup[county_str]:
                return cbsa_lookup[county_str][0]
            return {'code': None, 'name': None}
        
        metros_df['cbsa_code'] = metros_df['geoid5'].apply(lambda x: get_cbsa_info(x)['code'] if 'geoid5' in metros_df.columns else None)
        metros_df['cbsa_name'] = metros_df['geoid5'].apply(lambda x: get_cbsa_info(x)['name'] if 'geoid5' in metros_df.columns else None)
        
        # Aggregate by CBSA and loan purpose
        metros_list = []
        if 'cbsa_code' in metros_df.columns and metros_df['cbsa_code'].notna().any():
            cbsa_df = metros_df[metros_df['cbsa_code'].notna()].copy()
            
            # Get all CBSAs (not just top 10)
            all_cbsa_codes = cbsa_df['cbsa_code'].unique().tolist()
            
            for cbsa_code in all_cbsa_codes:
                cbsa_data = cbsa_df[cbsa_df['cbsa_code'] == cbsa_code]
                cbsa_name = cbsa_data['cbsa_name'].iloc[0] if not cbsa_data.empty else ''
                
                # Aggregate by loan purpose
                all_df = filter_df_by_loan_purpose(cbsa_data, 'all')
                purchase_df = filter_df_by_loan_purpose(cbsa_data, 'purchase')
                refinance_df = filter_df_by_loan_purpose(cbsa_data, 'refinance')
                equity_df = filter_df_by_loan_purpose(cbsa_data, 'equity')
                
                metros_list.append({
                    'CBSA Code': cbsa_code,
                    'CBSA Name': cbsa_name,
                    'All Loans': int(all_df['total_originations'].sum()) if not all_df.empty else 0,
                    'Home Purchase': int(purchase_df['total_originations'].sum()) if not purchase_df.empty else 0,
                    'Refinance': int(refinance_df['total_originations'].sum()) if not refinance_df.empty else 0,
                    'Home Equity': int(equity_df['total_originations'].sum()) if not equity_df.empty else 0
                })
            
            # Sort by total loans descending
            metros_list.sort(key=lambda x: x['All Loans'], reverse=True)
        
        return metros_list
        
    except Exception as e:
        logger.error(f"Error formatting all metros for Excel: {e}", exc_info=True)
        return []


def _generate_peer_data_sheet_for_excel(
    subject_lei: str,
    peer_leis: List[str],
    years: List[int],
    target_counties: List[str],
    query_filters: Dict[str, Any],
    PROJECT_ID: str,
    client
) -> List[Dict[str, Any]]:
    """
    Generate peer data sheet with all peers by CBSA and year.
    Returns list of dicts with: CBSA Code, CBSA Name, Year, Peer Name, LEI, Applications/Originations
    """
    try:
        if not peer_leis:
            return []
        
        years_str = "', '".join(map(str, years))
        peer_leis_str = "', '".join([escape_sql_string(lei) for lei in peer_leis])
        
        # Build filter clauses
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
        
        # Query peer data by CBSA and year
        # Use target_counties to limit to selected geography
        counties_escaped = [escape_sql_string(c) for c in target_counties]
        counties_list = "', '".join(counties_escaped)
        
        peer_query = f"""
        SELECT 
            CAST(c.cbsa_code AS STRING) as cbsa_code,
            c.CBSA as cbsa_name,
            h.activity_year as year,
            MAX(l.respondent_name) as lender_name,
            h.lei,
            COUNT(*) as applications
        FROM `{PROJECT_ID}.shared.de_hmda` h
        -- For 2022-2023 Connecticut data, join to shared.census to get planning region from tract
        LEFT JOIN `{PROJECT_ID}.shared.census` ct_tract
            ON CAST(h.county_code AS STRING) LIKE '09%'
            AND CAST(h.county_code AS STRING) NOT LIKE '091%'
            AND h.census_tract IS NOT NULL
            AND SUBSTR(LPAD(CAST(h.census_tract AS STRING), 11, '0'), 6, 6) = SUBSTR(LPAD(CAST(ct_tract.geoid AS STRING), 11, '0'), 6, 6)
        LEFT JOIN `{PROJECT_ID}.shared.cbsa_to_county` c
            ON COALESCE(
                -- For 2022-2023: Use planning region from tract
                CASE 
                    WHEN CAST(h.county_code AS STRING) LIKE '09%' 
                         AND CAST(h.county_code AS STRING) NOT LIKE '091%'
                         AND ct_tract.geoid IS NOT NULL THEN
                        SUBSTR(LPAD(CAST(ct_tract.geoid AS STRING), 11, '0'), 1, 5)
                    ELSE NULL
                END,
                -- For 2024: Use planning region code directly from county_code
                CAST(h.county_code AS STRING)
            ) = CAST(c.geoid5 AS STRING)
        LEFT JOIN `{PROJECT_ID}.lendsight.lenders18` l
            ON h.lei = l.lei
        WHERE CAST(c.geoid5 AS STRING) IN ('{counties_list}')
          AND h.lei IN ('{peer_leis_str}')
          AND h.activity_year IN ('{years_str}')
          AND {action_taken_clause}
          AND {occupancy_clause}
          AND {total_units_clause}
          AND {construction_clause}
          AND {loan_type_clause}
          AND {reverse_clause}
          AND c.cbsa_code IS NOT NULL
          AND c.CBSA IS NOT NULL
        GROUP BY cbsa_code, cbsa_name, year, h.lei
        ORDER BY cbsa_name, year, lender_name
        """
        
        peer_results = execute_query(client, peer_query)
        
        # Format results
        peer_data_sheet = []
        for row in peer_results:
            peer_data_sheet.append({
                'CBSA Code': row.get('cbsa_code', ''),
                'CBSA Name': row.get('cbsa_name', ''),
                'Year': int(row.get('year', 0)),
                'Peer Name': row.get('lender_name', ''),
                'LEI': row.get('lei', ''),
                'Applications': int(row.get('applications', 0))
            })
        
        logger.info(f"Generated peer data sheet with {len(peer_data_sheet)} rows")
        return peer_data_sheet
        
    except Exception as e:
        logger.error(f"Error generating peer data sheet: {e}", exc_info=True)
        return []


def apply_filters_to_sql_template(sql_template: str, query_filters: Dict[str, Any]) -> str:
    """
    Apply query filters to SQL template by replacing hardcoded filter values.
    
    Args:
        sql_template: SQL query template with hardcoded filters
        query_filters: Dictionary of filters from wizard (action_taken, occupancy, total_units, etc.)
        
    Returns:
        Modified SQL template with filters applied
    """
    sql = sql_template
    
    # Apply action_taken filter
    action_taken = query_filters.get('action_taken', ['1'])
    if len(action_taken) == 1:
        action_taken_clause = f"h.action_taken = '{action_taken[0]}'"
    else:
        action_taken_values = "', '".join(action_taken)
        action_taken_clause = f"h.action_taken IN ('{action_taken_values}')"
    sql = sql.replace("h.action_taken = '1'  -- Originated loans only", f"{action_taken_clause}  -- Action taken filter")
    
    # Apply occupancy filter
    occupancy = query_filters.get('occupancy', ['1'])
    if len(occupancy) == 1:
        occupancy_clause = f"h.occupancy_type = '{occupancy[0]}'"
    else:
        occupancy_values = "', '".join(occupancy)
        occupancy_clause = f"h.occupancy_type IN ('{occupancy_values}')"
    sql = sql.replace("h.occupancy_type = '1'  -- Owner-occupied", f"{occupancy_clause}  -- Occupancy filter")
    
    # Apply total_units filter
    total_units = query_filters.get('total_units', ['1', '2', '3', '4'])
    if total_units == ['5+']:
        total_units_clause = "(h.total_units IS NOT NULL AND h.total_units NOT IN ('1','2','3','4'))  -- 5+ units"
    elif len(total_units) == 1:
        total_units_clause = f"h.total_units = '{total_units[0]}'"
    else:
        total_units_values = "', '".join(total_units)
        total_units_clause = f"h.total_units IN ('{total_units_values}')"
    sql = sql.replace("h.total_units IN ('1','2','3','4')  -- 1-4 units", f"{total_units_clause}  -- Total units filter")
    
    # Apply construction filter
    construction = query_filters.get('construction', ['1'])
    if len(construction) == 1:
        construction_clause = f"h.construction_method = '{construction[0]}'"
    else:
        construction_values = "', '".join(construction)
        construction_clause = f"h.construction_method IN ('{construction_values}')"
    sql = sql.replace("h.construction_method = '1'  -- Site-built", f"{construction_clause}  -- Construction filter")
    
    # Apply loan_type filter (if specified)
    loan_type = query_filters.get('loan_type')
    if loan_type:
        if len(loan_type) == 1:
            loan_type_clause = f"h.loan_type = '{loan_type[0]}'"
        else:
            loan_type_values = "', '".join(loan_type)
            loan_type_clause = f"h.loan_type IN ('{loan_type_values}')"
        # Add loan_type filter after construction_method filter
        # Find the line after construction_method and add loan_type filter
        # For now, we'll add it as a new condition
        if "h.loan_type IN ('1','2','3','4')" not in sql:
            # Insert loan_type filter after construction_method line
            sql = sql.replace(
                f"{construction_clause}  -- Construction filter",
                f"{construction_clause}  -- Construction filter\n    AND {loan_type_clause}  -- Loan type filter"
            )
        else:
            sql = sql.replace("h.loan_type IN ('1','2','3','4')", loan_type_clause)
    
    # Apply reverse mortgage filter (exclude by default unless explicitly included)
    exclude_reverse = query_filters.get('exclude_reverse_mortgages', True)
    if exclude_reverse:
        reverse_clause = "(h.reverse_mortgage IS NULL OR h.reverse_mortgage != '1')  -- Not reverse mortgages"
    else:
        reverse_clause = "1=1  -- Include reverse mortgages"
    sql = sql.replace("(h.reverse_mortgage IS NULL OR h.reverse_mortgage != '1')  -- Not reverse mortgages", reverse_clause)
    
    return sql


def parse_lender_wizard_parameters(wizard_data: Dict[str, Any]) -> tuple:
    """
    Parse parameters from lender wizard data structure.
    
    Args:
        wizard_data: Dictionary from wizard with lender, geography, and filters
        
    Returns:
        Tuple of (lender_info, geography_scope, comparison_group, years_list, filters_dict, counties_list)
    """
    lender = wizard_data.get('lender', {})
    
    # Get years - default to last 3 years for lender analysis
    if 'years' in wizard_data and wizard_data['years']:
        years = wizard_data['years']
        if isinstance(years, str):
            years = [int(y.strip()) for y in years.split(',') if y.strip()]
        elif not isinstance(years, list):
            years = [int(years)]
    else:
        # Default to most recent 3 years (dynamic based on current year, capped at 2024 for HMDA)
        current_year = datetime.now().year
        max_year = min(current_year, 2024)  # HMDA data only available through 2024
        years = list(range(max_year - 2, max_year + 1))  # Most recent 3 years
    
    # Geography scope
    geography_scope = wizard_data.get('geography_scope', 'loan_cbsas')  # 'loan_cbsas', 'branch_cbsas', 'custom', 'all_cbsas'
    
    # For custom scope, get counties from lenderAnalysis or direct fields
    if geography_scope == 'custom':
        lender_analysis = wizard_data.get('lenderAnalysis', {})
        counties = lender_analysis.get('customCounties', []) or wizard_data.get('custom_counties', [])
    else:
        counties = []
    
    # Comparison group
    comparison_group = wizard_data.get('comparison_group', 'peers')  # 'peers', 'all', 'banks', 'mortgage', 'credit_unions'
    
    # Parse filters from wizard data (same format as area analysis)
    filters = wizard_data.get('filters', {})
    
    # Convert wizard filter format to query format
    query_filters = {}
    
    # Action taken: 'origination' -> ['1']
    if filters.get('actionTaken') == 'origination':
        query_filters['action_taken'] = ['1']
    elif filters.get('actionTaken') == 'application':
        query_filters['action_taken'] = ['1', '2', '3', '4', '5']
    
    # Occupancy
    occupancy_map = {
        'owner-occupied': '1',
        'second-home': '2',
        'investor': '3'
    }
    if filters.get('occupancy'):
        query_filters['occupancy'] = [occupancy_map.get(o, o) for o in filters.get('occupancy', [])]
    
    # Loan purpose - Convert wizard format to LendSight format
    if filters.get('loanPurpose'):
        purpose_list = []
        for p in filters.get('loanPurpose', []):
            if p == 'home-purchase':
                purpose_list.append('purchase')
            elif p == 'refinance':
                purpose_list.append('refinance')
            elif p == 'home-equity':
                purpose_list.append('equity')
        if purpose_list:
            query_filters['loan_purpose'] = purpose_list
    
    # Total units
    if filters.get('totalUnits') == '1-4':
        query_filters['total_units'] = ['1', '2', '3', '4']
    elif filters.get('totalUnits') == '5+':
        query_filters['total_units'] = ['5+']
    
    # Construction type
    construction_map = {
        'site-built': '1',
        'manufactured': '2'
    }
    if filters.get('construction'):
        query_filters['construction'] = [construction_map.get(c, c) for c in filters.get('construction', [])]
    
    # Loan type
    loan_type_map = {
        'conventional': '1',
        'fha': '2',
        'va': '3',
        'rhs': '4'
    }
    if filters.get('loanType'):
        query_filters['loan_type'] = [loan_type_map.get(lt, lt) for lt in filters.get('loanType', [])]
    
    # Reverse mortgage
    query_filters['exclude_reverse_mortgages'] = filters.get('reverseMortgage', True)
    
    # Counties are already extracted above for custom scope
    # For other scopes, counties will be determined in run_lender_analysis
    
    return lender, geography_scope, comparison_group, years, query_filters, counties


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
        config = get_unified_config(load_env=False, verbose=False)
        PROJECT_ID = config.get('GCP_PROJECT_ID')
        client = get_bigquery_client(PROJECT_ID)

        subject_lei = lender_info.get('lei')
        years_str = "', '".join(map(str, validated_years))

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
              AND h.activity_year IN ('{years_str}')
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
              AND h.activity_year IN ('{years_str}')
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


def run_lender_analysis(
    wizard_data: Dict[str, Any],
    job_id: str = None,
    progress_tracker: Optional[ProgressTracker] = None
) -> Dict[str, Any]:
    """
    Run lender analysis for web interface.

    Args:
        wizard_data: Dictionary from wizard with lender, geography, and filters
        job_id: Optional job ID for tracking
        progress_tracker: Optional progress tracker for real-time updates

    Returns:
        Dictionary with success status and results
    """
    try:
        # Initialize progress
        if progress_tracker:
            progress_tracker.update_progress('initializing', 0, 'Initializing lender analysis...')
        
        # Parse parameters
        lender_info, geography_scope, comparison_group, years, query_filters, counties = parse_lender_wizard_parameters(wizard_data)
        
        if not lender_info.get('lei'):
            return {
                'success': False,
                'error': 'Lender LEI is required'
            }
        
        if progress_tracker:
            progress_tracker.update_progress('preparing_data', 5, f'Preparing analysis for {lender_info.get("name", "lender")}...')
        
        # Validate years
        try:
            validated_years = validate_years(years)
        except ValueError as e:
            return {
                'success': False,
                'error': str(e)
            }
        
        if progress_tracker:
            progress_tracker.update_progress('connecting_db', 10, 'Connecting to database...')
        
        # Get configuration
        config = get_unified_config(load_env=False, verbose=False)
        PROJECT_ID = config.get('GCP_PROJECT_ID')
        client = get_bigquery_client(PROJECT_ID)
        sql_template_base = load_sql_template()
        
        # Apply query filters to SQL template
        sql_template = apply_filters_to_sql_template(sql_template_base, query_filters)
        
        # Determine geography based on geography_scope
        if progress_tracker:
            progress_tracker.update_progress('determining_geography', 15, f'Determining geography based on {geography_scope}...')
        
        # Get lender identifiers
        subject_lei = lender_info.get('lei')
        subject_rssd = lender_info.get('rssd')
        
        # Fetch additional lender details from lenders18 (type_name, city, state, etc.)
        if subject_lei:
            try:
                from justdata.apps.dataexplorer.data_utils import get_lender_details_by_lei, get_gleif_data_by_lei
                lender_details = get_lender_details_by_lei(subject_lei)
                if lender_details:
                    # Update lender_info with details from lenders18
                    if lender_details.get('type_name'):
                        lender_info['type_name'] = lender_details['type_name']
                        lender_info['type'] = lender_details['type_name']  # Also set as 'type' for compatibility
                    if lender_details.get('name') and not lender_info.get('name'):
                        lender_info['name'] = lender_details['name']
                    if lender_details.get('city') and not lender_info.get('city'):
                        lender_info['city'] = lender_details['city']
                    if lender_details.get('state') and not lender_info.get('state'):
                        lender_info['state'] = lender_details['state']
                    if lender_details.get('rssd') and not lender_info.get('rssd'):
                        lender_info['rssd'] = lender_details['rssd']
                    logger.info(f"Updated lender_info with details: type_name={lender_info.get('type_name')}, city={lender_info.get('city')}, state={lender_info.get('state')}")
                
                # Fetch GLEIF data (addresses and relationships)
                gleif_data = get_gleif_data_by_lei(subject_lei)
                if gleif_data:
                    lender_info['gleif_data'] = gleif_data
                    lender_info['legal_address'] = gleif_data.get('legal_address', {})
                    lender_info['headquarters_address'] = gleif_data.get('headquarters_address', {})
                    lender_info['direct_parent'] = gleif_data.get('direct_parent')
                    lender_info['ultimate_parent'] = gleif_data.get('ultimate_parent')
                    lender_info['direct_children'] = gleif_data.get('direct_children', [])
                    lender_info['ultimate_children'] = gleif_data.get('ultimate_children', [])
                    logger.info(f"Updated lender_info with GLEIF data: legal={lender_info.get('legal_address')}, hq={lender_info.get('headquarters_address')}")
            except Exception as e:
                logger.warning(f"Could not fetch additional lender details: {e}", exc_info=True)
        
        # Determine target counties based on geography_scope
        target_county_geoids = []
        
        if geography_scope == 'custom':
            # Use counties provided from wizard (custom selection)
            target_county_geoids = counties if counties else []
            if not target_county_geoids:
                if progress_tracker:
                    progress_tracker.complete(success=False, error='No counties selected for custom geography')
                return {
                    'success': False,
                    'error': 'No counties selected for custom geography. Please select at least one county.'
                }
            logger.info(f"Using {len(target_county_geoids)} custom counties for geography scope")
        
        elif geography_scope == 'all_cbsas':
            # Query all counties where the lender has loans matching the selected filters
            # Note: This queries hmda.hmda (not de_hmda), so activity_year is STRING
            years_str = "', '".join(map(str, validated_years))
            
            # Build filter clauses to match the data query
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
            
            # First, get all counties/planning regions where lender has loans
            # Normalize all Connecticut data to planning region codes (new standard)
            # For 2022-2023: Map legacy county codes to planning regions via tract
            # For 2024: Already uses planning region codes - keep as-is
            counties_query = f"""
            SELECT DISTINCT
                COALESCE(
                    -- For 2022-2023 legacy county codes, get planning region from tract
                    CASE 
                        WHEN CAST(h.county_code AS STRING) LIKE '09%' 
                             AND CAST(h.county_code AS STRING) NOT LIKE '091%'
                             AND h.census_tract IS NOT NULL
                             AND ct_tract.geoid IS NOT NULL THEN
                            SUBSTR(LPAD(CAST(ct_tract.geoid AS STRING), 11, '0'), 1, 5)
                        ELSE NULL
                    END,
                    -- For 2024 planning region codes or if tract join fails, use county_code as-is
                    CAST(h.county_code AS STRING)
                ) as geoid5
            FROM `{PROJECT_ID}.shared.de_hmda` h
            LEFT JOIN `{PROJECT_ID}.shared.census` ct_tract
                ON CAST(h.county_code AS STRING) LIKE '09%'
                AND CAST(h.county_code AS STRING) NOT LIKE '091%'
                AND h.census_tract IS NOT NULL
                AND SUBSTR(LPAD(CAST(h.census_tract AS STRING), 11, '0'), 6, 6) = SUBSTR(LPAD(CAST(ct_tract.geoid AS STRING), 11, '0'), 6, 6)
            WHERE h.lei = '{escape_sql_string(subject_lei)}'
              AND h.activity_year IN ('{years_str}')
              AND {action_taken_clause}
              AND {occupancy_clause}
              AND {total_units_clause}
              AND {construction_clause}
              AND {loan_type_clause}
              AND {reverse_clause}
              AND h.county_code IS NOT NULL
            """
            counties_result = execute_query(client, counties_query)
            target_county_geoids = [row['geoid5'] for row in counties_result if row.get('geoid5')]
            
            # Now get county_state for the counties we found (for the data query)
            if target_county_geoids:
                # Batch counties to avoid long IN clauses
                county_states = {}
                batch_size_cbsa = 200
                for i in range(0, len(target_county_geoids), batch_size_cbsa):
                    batch = target_county_geoids[i:i + batch_size_cbsa]
                    counties_str = "', '".join([escape_sql_string(c) for c in batch])
                    cbsa_query = f"""
                    SELECT DISTINCT
                        CAST(c.geoid5 AS STRING) as geoid5,
                        c.county_state
                    FROM `{PROJECT_ID}.shared.cbsa_to_county` c
                    WHERE CAST(c.geoid5 AS STRING) IN ('{counties_str}')
                      AND c.county_state IS NOT NULL
                    """
                    cbsa_result = execute_query(client, cbsa_query)
                    for row in cbsa_result:
                        geoid5 = row.get('geoid5')
                        county_state = row.get('county_state')
                        if geoid5 and county_state:
                            county_states[geoid5] = county_state
                
                # Update target_counties to use county_state where available, fallback to geoid5
                target_counties = [county_states.get(geoid5, geoid5) for geoid5 in target_county_geoids]
            else:
                target_counties = []
            
            logger.info(f"Found {len(target_county_geoids)} counties with loans matching filters for {geography_scope}")
            
        elif geography_scope == 'branch_cbsas':
            # Query CBSAs where lender has >1% of branches, then get all counties in those CBSAs
            if not subject_rssd:
                if progress_tracker:
                    progress_tracker.complete(success=False, error='RSSD is required for branch-based geography')
                return {
                    'success': False,
                    'error': 'RSSD is required for branch-based geography selection'
                }
            
            # SOD25 branch data is separate from HMDA years - get the most recent year available in SOD25
            # First, find what years are available in SOD25
            available_years_query = f"""
            SELECT DISTINCT CAST(year AS STRING) as year_str
            FROM `{PROJECT_ID}.branchsight.sod`
            ORDER BY CAST(year AS STRING) DESC
            LIMIT 1
            """
            try:
                available_years_result = execute_query(client, available_years_query)
                if available_years_result and available_years_result[0]:
                    branch_year = int(available_years_result[0].get('year_str', '2025'))
                    logger.info(f"Found available branch year in SOD25: {branch_year}")
                else:
                    branch_year = 2025  # Default to 2025 if query fails
                    logger.warning(f"Could not determine available branch year, defaulting to 2025")
            except Exception as e:
                logger.warning(f"Error finding available branch year: {e}, defaulting to 2025")
                branch_year = 2025
            
            # RSSD in SOD25 is stored as STRING - try both padded and unpadded formats
            rssd_original = str(subject_rssd).strip()
            # Try unpadded (remove leading zeros)
            try:
                rssd_unpadded = str(int(rssd_original))
            except (ValueError, TypeError):
                rssd_unpadded = rssd_original
            
            # Try padded to 10 digits
            rssd_padded = rssd_original.zfill(10) if rssd_original.isdigit() else rssd_original
            
            escaped_rssd_unpadded = escape_sql_string(rssd_unpadded)
            escaped_rssd_padded = escape_sql_string(rssd_padded)
            
            logger.info(f"=== BRANCH CBSAS DEBUG START ===")
            logger.info(f"Subject RSSD: original='{rssd_original}', unpadded='{rssd_unpadded}', padded='{rssd_padded}'")
            logger.info(f"HMDA years: {validated_years}, Branch year (SOD25): {branch_year}")
            logger.info(f"Escaped RSSD values: unpadded='{escaped_rssd_unpadded}', padded='{escaped_rssd_padded}', original='{escape_sql_string(rssd_original)}'")
            
            # Step 1: First check what RSSD formats exist in the table (sample query)
            sample_rssd_query = f"""
            SELECT DISTINCT rssd, COUNT(*) as branch_count
            FROM `{PROJECT_ID}.branchsight.sod`
            WHERE rssd LIKE '%{rssd_unpadded[-6:]}%'  -- Last 6 digits to find similar RSSDs
            GROUP BY rssd
            ORDER BY branch_count DESC
            LIMIT 10
            """
            try:
                sample_result = execute_query(client, sample_rssd_query)
                logger.info(f"Sample RSSD values in SOD25 (last 6 digits match): {sample_result}")
            except Exception as e:
                logger.warning(f"Could not run sample RSSD query: {e}")
            
            # Step 2: Try to find any branches without year filter to debug
            debug_query = f"""
            SELECT COUNT(*) as total_branches, 
                   MIN(CAST(year AS STRING)) as min_year,
                   MAX(CAST(year AS STRING)) as max_year,
                   COUNT(DISTINCT CAST(year AS STRING)) as distinct_years
            FROM `{PROJECT_ID}.branchsight.sod`
            WHERE rssd = '{escaped_rssd_unpadded}' OR rssd = '{escaped_rssd_padded}'
            """
            logger.info(f"Running debug query (unpadded/padded): {debug_query[:200]}...")
            try:
                debug_result = execute_query(client, debug_query)
                if debug_result and debug_result[0]:
                    logger.info(f"Debug query (unpadded/padded) result: {debug_result[0]}")
                    if debug_result[0].get('total_branches', 0) == 0:
                        # Try with just the original RSSD format
                        debug_query2 = f"""
                        SELECT COUNT(*) as total_branches, 
                               MIN(CAST(year AS STRING)) as min_year,
                               MAX(CAST(year AS STRING)) as max_year
                        FROM `{PROJECT_ID}.branchsight.sod`
                        WHERE rssd = '{escape_sql_string(rssd_original)}'
                        """
                        logger.info(f"Running debug query (original format): {debug_query2[:200]}...")
                        debug_result2 = execute_query(client, debug_query2)
                        if debug_result2 and debug_result2[0]:
                            logger.info(f"Debug query (original format) result: {debug_result2[0]}")
            except Exception as e:
                logger.error(f"Error in debug query: {e}", exc_info=True)
            
            # Step 1: Get all branches for the lender to calculate total
            # Use the branch_year from SOD25 (not HMDA years)
            total_branches_query = f"""
            SELECT COUNT(*) as total_branches
            FROM `{PROJECT_ID}.branchsight.sod`
            WHERE (rssd = '{escaped_rssd_unpadded}' OR rssd = '{escaped_rssd_padded}' OR rssd = '{escape_sql_string(rssd_original)}')
              AND CAST(year AS STRING) = '{branch_year}'
            """
            logger.info(f"Running total branches query for branch year {branch_year}: {total_branches_query[:300]}...")
            try:
                total_branches_result = execute_query(client, total_branches_query)
                total_branches = total_branches_result[0].get('total_branches', 0) if total_branches_result else 0
                logger.info(f"Query result: {total_branches_result}")
                logger.info(f"Found {total_branches} total branches for RSSD '{rssd_original}' in branch year {branch_year}")
            except Exception as e:
                logger.error(f"Error executing total branches query: {e}", exc_info=True)
                total_branches = 0
                
            if total_branches == 0:
                # Build detailed error message with debug info
                error_details = []
                error_details.append(f"RSSD tried: '{rssd_original}' (unpadded: '{rssd_unpadded}', padded: '{rssd_padded}')")
                error_details.append(f"Branch year checked (SOD25): {branch_year}")
                error_details.append(f"Note: SOD25 branch data is separate from HMDA years {validated_years}")
                
                # Try to get debug info from the queries we ran
                try:
                    # Check if any branches exist at all (without year filter)
                    any_branches_query = f"""
                    SELECT COUNT(*) as total
                    FROM `{PROJECT_ID}.branchsight.sod`
                    WHERE rssd = '{escaped_rssd_unpadded}' OR rssd = '{escaped_rssd_padded}' OR rssd = '{escape_sql_string(rssd_original)}'
                    """
                    any_result = execute_query(client, any_branches_query)
                    any_count = any_result[0].get('total', 0) if any_result else 0
                    if any_count > 0:
                        # Get available years
                        years_query = f"""
                        SELECT DISTINCT CAST(year AS STRING) as year_str
                        FROM `{PROJECT_ID}.branchsight.sod`
                        WHERE rssd = '{escaped_rssd_unpadded}' OR rssd = '{escaped_rssd_padded}' OR rssd = '{escape_sql_string(rssd_original)}'
                        ORDER BY year_str
                        """
                        years_result = execute_query(client, years_query)
                        available_years = [r.get('year_str') for r in years_result if r.get('year_str')]
                        error_details.append(f"Found {any_count} total branches, but in years: {available_years}")
                    else:
                        error_details.append("No branches found for this RSSD in any year")
                except Exception as e:
                    error_details.append(f"Could not check for branches: {str(e)}")
                
                error_msg = "No branch data found for lender. " + " | ".join(error_details)
                
                logger.error(f"=== NO BRANCHES FOUND ===")
                logger.error(f"RSSD tried: original='{rssd_original}', unpadded='{rssd_unpadded}', padded='{rssd_padded}'")
                logger.error(f"Years tried: {validated_years}")
                logger.error(f"Branch year checked: {branch_year}")
                logger.error(f"Error message: {error_msg}")
                
                if progress_tracker:
                    progress_tracker.complete(success=False, error=error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }
            
            # Step 2: Get branches by CBSA
            branches_by_cbsa_query = f"""
            SELECT 
                CAST(c.cbsa_code AS STRING) as cbsa_code,
                COUNT(*) as branch_count
            FROM `{PROJECT_ID}.branchsight.sod` b
            LEFT JOIN `{PROJECT_ID}.shared.cbsa_to_county` c
                ON CAST(b.geoid5 AS STRING) = CAST(c.geoid5 AS STRING)
            WHERE (b.rssd = '{escaped_rssd_unpadded}' OR b.rssd = '{escaped_rssd_padded}' OR b.rssd = '{escape_sql_string(rssd_original)}')
              AND CAST(b.year AS STRING) = '{branch_year}'
              AND c.cbsa_code IS NOT NULL
            GROUP BY cbsa_code
            HAVING (COUNT(*) / {total_branches}) > 0.01
            """
            branches_by_cbsa_result = execute_query(client, branches_by_cbsa_query)
            target_cbsa_codes = [row['cbsa_code'] for row in branches_by_cbsa_result if row.get('cbsa_code')]
            
            if not target_cbsa_codes:
                if progress_tracker:
                    progress_tracker.complete(success=False, error='No CBSAs found with >1% of lender branches')
                return {
                    'success': False,
                    'error': 'No CBSAs found with >1% of lender branches'
                }
            
            # Step 3: Get all counties in those CBSAs
            cbsa_codes_str = "', '".join([escape_sql_string(c) for c in target_cbsa_codes])
            counties_in_cbsas_query = f"""
            SELECT DISTINCT
                CAST(geoid5 AS STRING) as geoid5
            FROM `{PROJECT_ID}.shared.cbsa_to_county`
            WHERE CAST(cbsa_code AS STRING) IN ('{cbsa_codes_str}')
              AND geoid5 IS NOT NULL
            """
            counties_result = execute_query(client, counties_in_cbsas_query)
            target_county_geoids = [row['geoid5'] for row in counties_result if row.get('geoid5')]
            
            logger.info(f"Found {len(target_cbsa_codes)} CBSAs with >1% branches, {len(target_county_geoids)} total counties for {geography_scope}")
                
        elif geography_scope == 'loan_cbsas':
            # Query counties where the lender has >1% of loans
            years_str = "', '".join(map(str, validated_years))
            
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
            
            # Build loan_purpose filter clause
            loan_purpose = query_filters.get('loan_purpose', ['purchase', 'refinance', 'equity'])
            logger.info(f"[loan_cbsas] Applying loan_purpose filter: {loan_purpose}")
            loan_purpose_conditions = []
            if 'purchase' in loan_purpose:
                loan_purpose_conditions.append("h.loan_purpose = '1'")
            if 'refinance' in loan_purpose:
                loan_purpose_conditions.append("h.loan_purpose IN ('31','32')")
            if 'equity' in loan_purpose:
                loan_purpose_conditions.append("h.loan_purpose IN ('2','4')")
            
            if loan_purpose_conditions:
                loan_purpose_clause = "(" + " OR ".join(loan_purpose_conditions) + ")"
            else:
                loan_purpose_clause = "1=1"  # No loan purpose filter
            
            logger.info(f"[loan_cbsas] loan_purpose_clause: {loan_purpose_clause}")
            
            # Get lender loans per CBSA (aggregate at CBSA level, not county level)
            # Join to cbsa_to_county to get CBSA for each county, then aggregate by CBSA
            # Note: This queries hmda.hmda (not de_hmda), so activity_year is STRING
            years_str = "', '".join(map(str, validated_years))
            lender_loans_query = f"""
            SELECT
                CAST(c.cbsa_code AS STRING) as cbsa_code,
                COUNT(*) as lender_loans
            FROM `{PROJECT_ID}.shared.de_hmda` h
            LEFT JOIN `{PROJECT_ID}.shared.census` ct_tract
                ON CAST(h.county_code AS STRING) LIKE '09%'
                AND CAST(h.county_code AS STRING) NOT LIKE '091%'
                AND h.census_tract IS NOT NULL
                AND SUBSTR(LPAD(CAST(h.census_tract AS STRING), 11, '0'), 6, 6) = SUBSTR(LPAD(CAST(ct_tract.geoid AS STRING), 11, '0'), 6, 6)
            LEFT JOIN `{PROJECT_ID}.shared.cbsa_to_county` c
                ON COALESCE(
                    -- For 2022-2023 Connecticut: Use planning region from tract
                    CASE
                        WHEN CAST(h.county_code AS STRING) LIKE '09%'
                             AND CAST(h.county_code AS STRING) NOT LIKE '091%'
                             AND ct_tract.geoid IS NOT NULL THEN
                            SUBSTR(LPAD(CAST(ct_tract.geoid AS STRING), 11, '0'), 1, 5)
                        ELSE NULL
                    END,
                    -- For other states or 2024+: Use county_code directly
                    CAST(h.county_code AS STRING)
                ) = CAST(c.geoid5 AS STRING)
            WHERE h.lei = '{escape_sql_string(subject_lei)}'
              AND h.activity_year IN ('{years_str}')
              AND {action_taken_clause}
              AND {occupancy_clause}
              AND {total_units_clause}
              AND {construction_clause}
              AND {loan_type_clause}
              AND {loan_purpose_clause}
              AND {reverse_clause}
              AND c.cbsa_code IS NOT NULL
            GROUP BY cbsa_code
            """
            lender_loans_result = execute_query(client, lender_loans_query)
            logger.info(f"[loan_cbsas] Found {len(lender_loans_result)} CBSAs with lender loans")
            
            if not lender_loans_result:
                logger.warning(f"[loan_cbsas] No loans found for lender {subject_lei} with filters")
                if progress_tracker:
                    progress_tracker.complete(success=False, error=f'No loans found for this lender with the selected filters. Please try different filters or use "All CBSAs where lender operates".')
                return {
                    'success': False,
                    'error': 'No loans found for this lender with the selected filters. Please try different filters or use "All CBSAs where lender operates".'
                }
            
            # Calculate lender's total national loans (sum across all CBSAs)
            lender_loans_by_cbsa = {}
            null_cbsa_count = 0
            lender_total_national_loans = 0

            for row in lender_loans_result:
                cbsa_code = row.get('cbsa_code')
                if not cbsa_code:
                    null_cbsa_count += 1
                    logger.warning(f"[loan_cbsas] Skipping row with NULL cbsa_code: lender_loans={row.get('lender_loans', 0)}")
                    continue
                lender_loans = row.get('lender_loans', 0)
                lender_loans_by_cbsa[cbsa_code] = lender_loans
                lender_total_national_loans += lender_loans

            logger.info(f"[loan_cbsas] Lender total national loans: {lender_total_national_loans:,} across {len(lender_loans_by_cbsa)} CBSAs")

            if lender_total_national_loans == 0:
                logger.warning(f"[loan_cbsas] Lender has 0 total national loans")
                if progress_tracker:
                    progress_tracker.complete(success=False, error=f'No loans found for this lender with the selected filters. Please try different filters or use "All CBSAs where lender operates".')
                return {
                    'success': False,
                    'error': 'No loans found for this lender with the selected filters. Please try different filters or use "All CBSAs where lender operates".'
                }

            # Filter CBSAs where lender has >=1% of their national loans
            target_cbsa_codes = []
            for cbsa_code, lender_loans_in_cbsa in lender_loans_by_cbsa.items():
                # Calculate percentage: (lender loans in CBSA / lender total national loans) * 100
                percentage = (lender_loans_in_cbsa / lender_total_national_loans) * 100
                # Use >= 1.0 to include CBSAs at exactly 1%
                if percentage >= 1.0:
                    target_cbsa_codes.append(cbsa_code)
                    logger.info(f"[loan_cbsas] CBSA {cbsa_code}: {lender_loans_in_cbsa}/{lender_total_national_loans:,} = {percentage:.2f}% of lender's national loans - INCLUDED")
                else:
                    logger.debug(f"[loan_cbsas] CBSA {cbsa_code}: {lender_loans_in_cbsa}/{lender_total_national_loans:,} = {percentage:.2f}% of lender's national loans - below 1% threshold")

            logger.info(f"[loan_cbsas] Found {len(target_cbsa_codes)} CBSAs with >=1% of lender's national loans")

            # If no CBSAs found but lender has loans, provide more helpful error with details
            if not target_cbsa_codes and lender_loans_result:
                logger.warning(f"[loan_cbsas] Lender has {lender_total_national_loans:,} total national loans across {len(lender_loans_by_cbsa)} CBSAs, but none meet >=1% threshold")

                # Show top CBSAs by percentage of lender's national loans for debugging
                cbsa_details = []
                for cbsa_code, lender_count in lender_loans_by_cbsa.items():
                    pct = (lender_count / lender_total_national_loans) * 100
                    cbsa_details.append((cbsa_code, lender_count, pct))

                # Sort by percentage descending
                cbsa_details.sort(key=lambda x: x[2], reverse=True)
                top_cbsas = cbsa_details[:10]

                logger.info(f"[loan_cbsas] Top 10 CBSAs by percentage of lender's national loans:")
                for cbsa_code, lender_count, pct in top_cbsas:
                    logger.info(f"[loan_cbsas]   {cbsa_code}: {lender_count} loans = {pct:.4f}% of lender's national loans")

                # Build detailed error message
                if top_cbsas:
                    top_cbsa, top_lender, top_pct = top_cbsas[0]
                    error_msg = f'This lender has loans in {len(lender_loans_by_cbsa)} CBSAs, but none meet the >=1% threshold. '
                    error_msg += f'Top CBSA ({top_cbsa}) has {top_lender} loans, which is {top_pct:.2f}% of the lender\'s {lender_total_national_loans:,} total national loans. '
                    error_msg += 'Try using "All CBSAs where lender operates" instead.'
                else:
                    error_msg = f'This lender has loans in {len(lender_loans_by_cbsa)} CBSAs, but none meet the >=1% threshold. Try using "All CBSAs where lender operates" instead.'

                if progress_tracker:
                    progress_tracker.complete(success=False, error=error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }

            # Get ALL counties within the qualifying CBSAs
            cbsa_codes_str = "', '".join([escape_sql_string(c) for c in target_cbsa_codes])
            counties_in_cbsas_query = f"""
            SELECT DISTINCT CAST(geoid5 AS STRING) as geoid5
            FROM `{PROJECT_ID}.shared.cbsa_to_county`
            WHERE CAST(cbsa_code AS STRING) IN ('{cbsa_codes_str}')
              AND geoid5 IS NOT NULL
            """
            counties_result = execute_query(client, counties_in_cbsas_query)
            target_county_geoids = [row['geoid5'] for row in counties_result if row.get('geoid5')]

            logger.info(f"Found {len(target_cbsa_codes)} CBSAs with >=1% of lender's loans, {len(target_county_geoids)} total counties for {geography_scope}")
        else:
            if progress_tracker:
                progress_tracker.complete(success=False, error=f'Unknown geography_scope: {geography_scope}')
            return {
                'success': False,
                'error': f'Unknown geography_scope: {geography_scope}'
            }
        
        if not target_county_geoids:
            if progress_tracker:
                progress_tracker.complete(success=False, error=f'No counties found for geography_scope: {geography_scope}')
            return {
                'success': False,
                'error': f'No counties found for the selected geography scope. Please try a different option.'
            }
        
        # Get county_state strings for the WHERE clause
        # Convert geoids to county_state format for the data query
        # If target_counties was already set (e.g., for all_cbsas), use it; otherwise convert geoids
        if 'target_counties' not in locals() or not target_counties:
            # Batch geoids to avoid very long IN clauses
            geoids_escaped = [escape_sql_string(g) for g in target_county_geoids]
            geoid_batch_size = 200  # Process 200 geoids at a time
            all_county_states = []
            
            for i in range(0, len(geoids_escaped), geoid_batch_size):
                batch = geoids_escaped[i:i + geoid_batch_size]
                geoids_batch = "', '".join(batch)
                
                # First try shared.cbsa_to_county
                county_state_query = f"""
                SELECT DISTINCT
                    CAST(geoid5 AS STRING) as geoid5,
                    county_state
                FROM `{PROJECT_ID}.shared.cbsa_to_county`
                WHERE CAST(geoid5 AS STRING) IN ('{geoids_batch}')
                  AND county_state IS NOT NULL
                """
                batch_result = execute_query(client, county_state_query)
                found_geoids = set()
                if batch_result:
                    for row in batch_result:
                        if row.get('county_state'):
                            all_county_states.append(row['county_state'])
                            found_geoids.add(row.get('geoid5'))
                
                # For any GEOIDs not found in cbsa_to_county (e.g., CT planning regions),
                # query HMDA data directly to get county_state
                missing_geoids = [g for g in batch if g not in found_geoids]
                if missing_geoids:
                    missing_batch = "', '".join(missing_geoids)
                    # Query HMDA data with Connecticut normalization to get county_state
                    hmda_county_state_query = f"""
                    SELECT DISTINCT
                        COALESCE(
                            -- For 2022-2023 legacy county codes, get planning region from tract
                            CASE 
                                WHEN CAST(h.county_code AS STRING) LIKE '09%' 
                                     AND CAST(h.county_code AS STRING) NOT LIKE '091%'
                                     AND h.census_tract IS NOT NULL
                                     AND ct_tract.geoid IS NOT NULL THEN
                                    SUBSTR(LPAD(CAST(ct_tract.geoid AS STRING), 11, '0'), 1, 5)
                                ELSE NULL
                            END,
                            -- For 2024 planning region codes or if tract join fails, use county_code as-is
                            CAST(h.county_code AS STRING)
                        ) as geoid5,
                        h.county_state
                    FROM `{PROJECT_ID}.shared.de_hmda` h
                    LEFT JOIN `{PROJECT_ID}.shared.census` ct_tract
                        ON CAST(h.county_code AS STRING) LIKE '09%'
                        AND CAST(h.county_code AS STRING) NOT LIKE '091%'
                        AND h.census_tract IS NOT NULL
                        AND SUBSTR(LPAD(CAST(h.census_tract AS STRING), 11, '0'), 6, 6) = SUBSTR(LPAD(CAST(ct_tract.geoid AS STRING), 11, '0'), 6, 6)
                    WHERE COALESCE(
                            CASE 
                                WHEN CAST(h.county_code AS STRING) LIKE '09%' 
                                     AND CAST(h.county_code AS STRING) NOT LIKE '091%'
                                     AND h.census_tract IS NOT NULL
                                     AND ct_tract.geoid IS NOT NULL THEN
                                    SUBSTR(LPAD(CAST(ct_tract.geoid AS STRING), 11, '0'), 1, 5)
                                ELSE NULL
                            END,
                            CAST(h.county_code AS STRING)
                        ) IN ('{missing_batch}')
                      AND h.county_state IS NOT NULL
                    LIMIT 1000
                    """
                    hmda_result = execute_query(client, hmda_county_state_query)
                    if hmda_result:
                        for row in hmda_result:
                            if row.get('county_state'):
                                all_county_states.append(row['county_state'])
            
            target_counties = list(set(all_county_states))  # Remove duplicates
            logger.info(f"Converted {len(target_county_geoids)} GEOIDs to {len(target_counties)} county_state values")
            if target_counties:
                logger.info(f"Sample county_state values: {target_counties[:5]}")
            else:
                logger.warning(f"No county_state values found for GEOIDs: {target_county_geoids[:10]}")
        
        if not target_counties:
            if progress_tracker:
                progress_tracker.complete(success=False, error='Could not determine county states for selected geography')
            return {
                'success': False,
                'error': 'Could not determine county states for selected geography'
            }
        
        # For the WHERE clause, we'll use IN with all county_state values
        # But the SQL template uses a single @county, so we need to modify the approach
        # We'll query each county separately and combine results, or modify the query to use IN
        # For now, let's use the first county as a test, but we should enhance this to handle multiple counties
        # Actually, let's build a query that handles multiple counties using IN clause
        
        logger.info(f"Using {len(target_counties)} counties for analysis")
        
        if progress_tracker:
            progress_tracker.update_progress('querying_data', 20, f'Querying {lender_info.get("name", "lender")} HMDA data for {len(target_counties)} counties...')
        
        # Step 1: Find peer lenders based on comparison_group and geography
        peer_min_percent = 0.5
        peer_max_percent = 2.0
        
        if progress_tracker:
            progress_tracker.update_progress('querying_data', 25, 'Finding peer lenders...')
        
        # Query aggregated volumes for all lenders to find peers
        years_str = "', '".join(map(str, validated_years))
        # Batch counties into chunks to avoid very long IN clauses
        counties_escaped = [escape_sql_string(c) for c in target_counties]
        # Use smaller batch size for volume query to avoid SQL string length issues
        volume_batch_size = 100  # Process 100 counties at a time for volume query
        # Use smaller batch size for detailed queries (more complex)
        batch_size = 100  # Process 100 counties at a time for detailed data queries
        all_volumes = {}
        
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
        
        # Use GEOIDs directly instead of county_state to avoid matching issues
        geoids_escaped_for_query = [escape_sql_string(g) for g in target_county_geoids]
        geoids_batch_size = 200  # Process 200 geoids at a time
        
        logger.info(f"Querying lender volumes for peer selection: {len(target_county_geoids)} GEOIDs, {len(validated_years)} years")
        logger.info(f"GEOIDs being used: {target_county_geoids[:10]}... (showing first 10)")
        logger.debug(f"Subject lender LEI: {subject_lei}")
        logger.debug(f"Years: {years_str}")
        logger.debug(f"Filter clauses: action_taken={action_taken_clause}, occupancy={occupancy_clause}")
        
        total_batches = (len(geoids_escaped_for_query) + geoids_batch_size - 1) // geoids_batch_size
        for i in range(0, len(geoids_escaped_for_query), geoids_batch_size):
            batch_num = i // geoids_batch_size + 1
            geoid_batch = geoids_escaped_for_query[i:i + geoids_batch_size]
            geoids_array = ', '.join([f"'{g}'" for g in geoid_batch])
            
            # Update progress during volume query
            if progress_tracker and total_batches > 1:
                progress_pct = 25 + int((batch_num / total_batches) * 10)  # 25% to 35%
                progress_tracker.update_progress('querying_data', progress_pct, 
                    f'Querying lender volumes (batch {batch_num}/{total_batches})...')
            
            # Build lender type filter based on comparison_group
            lender_type_filter = ""
            if comparison_group == 'banks':
                lender_type_filter = "AND (LOWER(l.type_name) LIKE '%bank%' OR LOWER(l.type_name) LIKE '%affiliate%')"
            elif comparison_group == 'credit_unions':
                lender_type_filter = "AND LOWER(l.type_name) LIKE '%credit union%'"
            elif comparison_group == 'mortgage':
                lender_type_filter = "AND LOWER(l.type_name) LIKE '%mortgage%'"
            # For 'all' or 'peers', no type filter needed
            
            volume_query = f"""
            SELECT 
                h.lei,
                SUM(h.loan_amount) as total_volume,
                l.type_name
            FROM `{PROJECT_ID}.shared.de_hmda` h
            LEFT JOIN `{PROJECT_ID}.shared.census` ct_tract
                ON CAST(h.county_code AS STRING) LIKE '09%'
                AND CAST(h.county_code AS STRING) NOT LIKE '091%'
                AND h.census_tract IS NOT NULL
                AND SUBSTR(LPAD(CAST(h.census_tract AS STRING), 11, '0'), 6, 6) = SUBSTR(LPAD(CAST(ct_tract.geoid AS STRING), 11, '0'), 6, 6)
            LEFT JOIN `{PROJECT_ID}.lendsight.lenders18` l
                ON h.lei = l.lei
            WHERE COALESCE(
                    -- For 2022-2023: Use planning region from tract
                    CASE 
                        WHEN CAST(h.county_code AS STRING) LIKE '09%' 
                             AND CAST(h.county_code AS STRING) NOT LIKE '091%'
                             AND ct_tract.geoid IS NOT NULL THEN
                            SUBSTR(LPAD(CAST(ct_tract.geoid AS STRING), 11, '0'), 1, 5)
                        ELSE NULL
                    END,
                    -- For 2024: Use planning region code directly from county_code
                    CAST(h.county_code AS STRING)
                ) IN UNNEST([{geoids_array}])
              AND h.activity_year IN ('{years_str}')
              AND {action_taken_clause}
              AND {occupancy_clause}
              AND {total_units_clause}
              AND {construction_clause}
              AND {loan_type_clause}
              AND {reverse_clause}
              {lender_type_filter}
            GROUP BY h.lei, l.type_name
            """
            
            try:
                logger.debug(f"Executing volume query for batch {batch_num} with {len(geoid_batch)} GEOIDs")
                batch_result = execute_query(client, volume_query)
                # Aggregate results across batches
                for row in batch_result:
                    lei = row.get('lei')
                    volume = row.get('total_volume', 0)
                    type_name = row.get('type_name', '')
                    if lei:
                        if lei not in all_volumes:
                            all_volumes[lei] = {'total_volume': 0, 'type_name': type_name}
                        all_volumes[lei]['total_volume'] += volume
                logger.info(f"Batch {batch_num}: Found {len(batch_result)} lenders, total unique LEIs so far: {len(all_volumes)}")
            except Exception as e:
                logger.error(f"Error querying lender volumes for batch {batch_num}: {e}", exc_info=True)
                # Continue with other batches rather than failing completely
                continue
        
        # Convert aggregated results to list format
        lender_volumes_result = [
            {'lei': lei, 'total_volume': data['total_volume'], 'type_name': data.get('type_name', '')} 
            for lei, data in all_volumes.items()
        ]
        lender_volumes_df = pd.DataFrame(lender_volumes_result)
        
        logger.info(f"Total lenders found in volume query: {len(lender_volumes_df)}")
        
        if lender_volumes_df.empty:
            error_msg = f'No lenders found in selected geography ({len(target_county_geoids)} GEOIDs). This may indicate: 1) No HMDA data for the selected filters, 2) Geography selection issue, or 3) Query error.'
            logger.error(error_msg)
            if progress_tracker:
                progress_tracker.complete(success=False, error=error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        
        # Get subject lender volume
        subject_volume_row = lender_volumes_df[lender_volumes_df['lei'] == subject_lei]
        if subject_volume_row.empty:
            # Check if subject LEI is in the results at all (case sensitivity, etc.)
            all_leis = lender_volumes_df['lei'].tolist()
            logger.warning(f"Subject lender LEI '{subject_lei}' not found in volume results.")
            logger.debug(f"Sample LEIs found (first 10): {all_leis[:10] if len(all_leis) > 0 else 'None'}")
            logger.debug(f"Total unique LEIs: {len(all_leis)}")
            
            # Try case-insensitive match
            subject_lei_lower = subject_lei.lower()
            matching_leis = [lei for lei in all_leis if lei and lei.lower() == subject_lei_lower]
            if matching_leis:
                logger.info(f"Found case-insensitive match: using '{matching_leis[0]}' instead of '{subject_lei}'")
                subject_volume_row = lender_volumes_df[lender_volumes_df['lei'] == matching_leis[0]]
                subject_lei = matching_leis[0]  # Update to use the matched LEI
                lender_info['lei'] = subject_lei  # Update lender_info for consistency
            
            if subject_volume_row.empty:
                error_msg = f'No HMDA data found for {lender_info.get("name", "lender")} (LEI: {subject_lei}) in selected geography ({len(target_counties)} counties). The lender may not have originated loans matching the selected filters in this geography.'
                logger.error(error_msg)
                if progress_tracker:
                    progress_tracker.complete(success=False, error=error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }
        
        subject_volume = float(subject_volume_row['total_volume'].iloc[0])
        logger.info(f"{lender_info.get('name', 'Lender')} volume in {len(target_counties)} counties: ${subject_volume:,.0f}")
        
        # Find peers based on comparison_group
        if comparison_group == 'peers':
            # For "Peer Lenders (50-200%)", filter by volume range
            min_volume = subject_volume * peer_min_percent
            max_volume = subject_volume * peer_max_percent
            peer_volumes = lender_volumes_df[
                (lender_volumes_df['lei'] != subject_lei) &
                (lender_volumes_df['total_volume'] >= min_volume) &
                (lender_volumes_df['total_volume'] <= max_volume)
            ]
            peer_leis = peer_volumes['lei'].tolist()
            
            # If no peers found with standard range, try expanding the range for very large lenders
            if len(peer_leis) == 0:
                logger.warning(f"No peers found in standard range (50%-200%). Subject volume: ${subject_volume:,.0f}")
                # Try expanding to 25% to 400% for very large lenders
                expanded_min_volume = subject_volume * 0.25
                expanded_max_volume = subject_volume * 4.0
                expanded_peer_volumes = lender_volumes_df[
                    (lender_volumes_df['lei'] != subject_lei) &
                    (lender_volumes_df['total_volume'] >= expanded_min_volume) &
                    (lender_volumes_df['total_volume'] <= expanded_max_volume)
                ]
                if len(expanded_peer_volumes) > 0:
                    # Take top 20 by volume to avoid too many peers
                    expanded_peer_volumes = expanded_peer_volumes.sort_values('total_volume', ascending=False).head(20)
                    peer_leis = expanded_peer_volumes['lei'].tolist()
                    logger.info(f"Found {len(peer_leis)} peer lenders using expanded range (25%-400%)")
                else:
                    # If still no peers, try top 20 lenders by volume (excluding subject)
                    top_lenders = lender_volumes_df[
                        lender_volumes_df['lei'] != subject_lei
                    ].sort_values('total_volume', ascending=False).head(20)
                    peer_leis = top_lenders['lei'].tolist()
                    if len(peer_leis) > 0:
                        logger.info(f"Found {len(peer_leis)} peer lenders using top lenders by volume")
                    else:
                        logger.warning(f"No peer lenders found even with expanded criteria")
        else:
            # For other comparison groups (all, banks, credit_unions, mortgage), include ALL lenders of that type
            # (lender type filtering is already done in the volume query)
            peer_volumes = lender_volumes_df[
                lender_volumes_df['lei'] != subject_lei
            ]
            peer_leis = peer_volumes['lei'].tolist()
            logger.info(f"Found {len(peer_leis)} {comparison_group} lenders (all lenders of this type, no volume filter)")
        
        logger.info(f"Using {len(peer_leis)} peer lenders for comparison")
        
        if progress_tracker:
            progress_tracker.update_progress('querying_data', 40, f'Querying data for subject lender and {len(peer_leis)} peers...')
        
        # Query subject lender data - OPTIMIZED: Query all years at once
        # Use GEOIDs directly instead of county_state to avoid matching issues
        subject_results = []
        try:
            total_subject_batches = (len(geoids_escaped_for_query) + batch_size - 1) // batch_size
            # Process GEOIDs in batches
            for i in range(0, len(geoids_escaped_for_query), batch_size):
                batch_num = i // batch_size + 1
                geoid_batch = geoids_escaped_for_query[i:i + batch_size]
                geoids_array = ', '.join([f"'{g}'" for g in geoid_batch])
                
                # Update progress during subject lender query
                if progress_tracker and total_subject_batches > 1:
                    progress_pct = 40 + int((batch_num / total_subject_batches) * 15)  # 40% to 55%
                    progress_tracker.update_progress('querying_data', progress_pct, 
                        f'Querying subject lender data (batch {batch_num}/{total_subject_batches})...')
                
                # Replace WHERE clause to handle multiple GEOIDs
                # Check if using de_hmda table (has geoid5 directly) or old hmda.hmda table
                if 'justdata.de_hmda' in sql_template or 'de_hmda' in sql_template:
                    # For de_hmda: use geoid5 directly (already normalized)
                    sql = sql_template.replace(
                        "WHERE h.county_state = @county",
                        f"""WHERE h.geoid5 IN UNNEST([{geoids_array}])
                    AND h.lei = '{escape_sql_string(subject_lei)}'"""
                    )
                    sql = sql.replace('@county', f"UNNEST([{geoids_array}])")
                else:
                    # For old hmda.hmda: use COALESCE with county_code normalization
                    sql = sql_template.replace(
                        "WHERE c.county_state = @county",
                        f"""WHERE COALESCE(
                        -- For 2022-2023: Use planning region from tract
                        CASE 
                            WHEN CAST(h.county_code AS STRING) LIKE '09%' 
                                 AND CAST(h.county_code AS STRING) NOT LIKE '091%'
                                 AND ct_tract.geoid IS NOT NULL THEN
                                SUBSTR(LPAD(CAST(ct_tract.geoid AS STRING), 11, '0'), 1, 5)
                            ELSE NULL
                        END,
                        -- For 2024: Use planning region code directly from county_code
                        CAST(h.county_code AS STRING)
                    ) IN UNNEST([{geoids_array}])
                    AND h.lei = '{escape_sql_string(subject_lei)}'"""
                    )
                    sql = sql.replace('@county', f"UNNEST([{geoids_array}])")
                # Replace single year with IN clause for all years (do this BEFORE the general @year replace)
                # Check if using de_hmda table (activity_year is INT64, not STRING)
                if 'justdata.de_hmda' in sql or 'de_hmda' in sql:
                    # For de_hmda: activity_year is INT64, use unquoted integers
                    years_int_str = ', '.join(map(str, validated_years))
                    sql = sql.replace("AND h.activity_year = @year", f"AND h.activity_year IN ({years_int_str})")
                    if '@year' in sql:
                        sql = sql.replace('@year', years_int_str)
                else:
                    # For old hmda.hmda table: activity_year is STRING, use quoted strings
                    sql = sql.replace("AND h.activity_year = @year", f"AND h.activity_year IN ('{years_str}')")
                    if '@year' in sql:
                        sql = sql.replace('@year', f"'{years_str}'")
                sql = sql.replace('@loan_purpose', "'all'")
                
                # Apply filters to the SQL template
                sql = apply_filters_to_sql_template(sql, query_filters)
                
                batch_results = execute_query(client, sql)
                if batch_results:
                    subject_results.extend(batch_results)
        except Exception as e:
            logger.warning(f"Error querying subject lender: {e}")
        
        logger.info(f"Found {len(subject_results)} aggregated rows for subject lender")
        
        # Log total loans by year for subject lender
        if subject_results:
            year_totals = {}
            for row in subject_results:
                year = row.get('year')
                loans = int(row.get('total_originations', 0)) if row.get('total_originations') else 0
                if year:
                    year_totals[year] = year_totals.get(year, 0) + loans
            for year, total in sorted(year_totals.items()):
                logger.info(f"Subject lender Year {year}: {total:,} loans (from selected geography)")
        # Note: build_lender_report expects a list and will convert to DataFrame internally
        
        # Query ALL CBSAs for subject lender (for top metros table) - OPTIMIZED: Query all years at once
        # This shows all metros where the lender operates, not just the selected geography
        if progress_tracker:
            progress_tracker.update_progress('querying_data', 75, 'Querying all metros for subject lender...')
        
        all_metros_results = []
        try:
            # Query ALL loans for subject lender nationally (no geography filter) - all years at once
            # Build a direct query that doesn't rely on county_state join to ensure we get ALL loans
            years_str = "', '".join(map(str, validated_years))
            
            # Build filter clauses
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
            
            # Use SQL template but ensure filtering matches Tableau's exact logic
            # CONNECTICUT NORMALIZATION: The SQL template now normalizes 2024 planning region codes
            # (09110-09190) to legacy county codes (09001-09015) for consistency across years.
            # This ensures all Connecticut data uses the same county structure regardless of year.
            
            sql_template = load_sql_template()
            
            # Replace WHERE clause to query by LEI (matching Tableau's approach of filtering by lender)
            # Tableau filters by respondent_name, we filter by LEI (which is equivalent)
            sql = sql_template.replace("WHERE c.county_state = @county", f"WHERE h.lei = '{escape_sql_string(subject_lei)}'")
            sql = sql.replace('@county', "'all'")
            # Check if using de_hmda table (activity_year is INT64, not STRING)
            if 'justdata.de_hmda' in sql or 'de_hmda' in sql:
                # For de_hmda: activity_year is INT64, use unquoted integers
                years_int_str = ', '.join(map(str, validated_years))
                sql = sql.replace("AND h.activity_year = @year", f"AND h.activity_year IN ({years_int_str})")
                if '@year' in sql:
                    sql = sql.replace('@year', years_int_str)
            else:
                # For old hmda.hmda table: activity_year is STRING, use quoted strings
                sql = sql.replace("AND h.activity_year = @year", f"AND h.activity_year IN ('{years_str}')")
                if '@year' in sql:
                    sql = sql.replace('@year', f"'{years_str}'")
            sql = sql.replace('@loan_purpose', "'all'")
            
            # Apply filters (this will replace the hardcoded filters in the template)
            sql = apply_filters_to_sql_template(sql, query_filters)
            
            # CRITICAL: Match Tableau's approach - Tableau uses INNER JOIN, which means it only includes
            # loans with county mappings. Since Tableau gets the correct totals, all loans have mappings.
            # However, we use LEFT JOIN in the template, so we need to ensure we're not excluding loans.
            # The key is: don't add any WHERE conditions that would exclude loans with NULL county_state.
            # But since Tableau's INNER JOIN works, our LEFT JOIN should also work (all loans have mappings).
            
            # CONNECTICUT NORMALIZATION: The SQL template normalizes all Connecticut data to
            # planning region codes (new standard) in both the SELECT (geoid5) and JOIN clauses.
            # Strategy:
            # - 2024 data: Already uses planning region codes (09110-09190) - keep as-is
            # - 2022-2023 data: Uses legacy county codes (09001-09015) - map to planning regions via tract
            # - Join to shared.census using tract portion (last 6 digits) to get planning region
            # This ensures:
            # 1. All Connecticut data uses consistent planning region codes across all years
            # 2. The JOIN to cbsa_to_county works correctly (cbsa_to_county has both codes)
            # 3. Planning region selections work for all years, including 2022-2023
            # 4. CBSA assignments align with the planning region structure
            
            # Remove any county_state IS NOT NULL checks that might exclude loans
            sql = sql.replace("AND c.county_state IS NOT NULL", "")
            sql = sql.replace("WHERE c.county_state IS NOT NULL AND", "WHERE")
            sql = sql.replace("WHERE c.county_state IS NOT NULL", "WHERE 1=1")
            
            # Remove any remaining county_state = ... clauses
            import re
            sql = re.sub(r'\s+AND\s+c\.county_state\s*=\s*[^\s]+', '', sql, flags=re.IGNORECASE)
            
            logger.info(f"All metros query: Querying ALL loans for {subject_lei} with filters applied (matching Tableau's filtering logic)")
            # Log the full SQL query for comparison with Tableau
            logger.info(f"=== ALL METROS SQL QUERY (FULL) ===")
            logger.info(sql)
            logger.info(f"=== END SQL QUERY ===")
            metros_results = execute_query(client, sql)
            if metros_results:
                all_metros_results.extend(metros_results)
                total_loans = sum([int(row.get('total_originations', 0)) for row in metros_results if row.get('total_originations')])
                logger.info(f"All metros query returned {len(metros_results)} aggregated rows, total loans: {total_loans:,}")
                
                # Log breakdown by year
                if metros_results:
                    year_totals = {}
                    for row in metros_results:
                        year = row.get('year')
                        loans = int(row.get('total_originations', 0))
                        if year:
                            year_totals[year] = year_totals.get(year, 0) + loans
                    for year, total in sorted(year_totals.items()):
                        logger.info(f"  Year {year}: {total:,} loans")
        except Exception as e:
            logger.error(f"Error querying all metros for subject lender: {e}", exc_info=True)
        
        logger.info(f"Found {len(all_metros_results)} aggregated rows for all metros (subject lender)")
        
        # Query peer lenders data - OPTIMIZED: Query all years at once, combine all peers in single query
        peer_results = []
        if peer_leis:
            logger.info(f"Querying data for {len(peer_leis)} peer lenders")
            peer_leis_str = "', '".join([escape_sql_string(lei) for lei in peer_leis])
            
            try:
                total_peer_batches = (len(geoids_escaped_for_query) + batch_size - 1) // batch_size
                # Process GEOIDs in batches to avoid very long IN clauses
                # But query all years and all peers in a single query per batch
                # Use UNNEST with ARRAY for better performance with large lists
                for i in range(0, len(geoids_escaped_for_query), batch_size):
                    batch_num = i // batch_size + 1
                    geoid_batch = geoids_escaped_for_query[i:i + batch_size]
                    geoids_array = ', '.join([f"'{g}'" for g in geoid_batch])
                    
                    # Update progress during peer queries
                    if progress_tracker and total_peer_batches > 1:
                        progress_pct = 55 + int((batch_num / total_peer_batches) * 20)  # 55% to 75%
                        progress_tracker.update_progress('querying_data', progress_pct, 
                            f'Querying peer lender data (batch {batch_num}/{total_peer_batches})...')
                    
                    # Replace WHERE clause to handle multiple GEOIDs
                    # Check if using de_hmda table (has geoid5 directly) or old hmda.hmda table
                    if 'justdata.de_hmda' in sql_template or 'de_hmda' in sql_template:
                        # For de_hmda: use geoid5 directly (already normalized)
                        sql = sql_template.replace(
                            "WHERE h.county_state = @county",
                            f"""WHERE h.geoid5 IN UNNEST([{geoids_array}])
                        AND h.lei IN ('{peer_leis_str}')"""
                        )
                        sql = sql.replace('@county', f"UNNEST([{geoids_array}])")
                    else:
                        # For old hmda.hmda: use COALESCE with county_code normalization
                        sql = sql_template.replace(
                            "WHERE c.county_state = @county",
                            f"""WHERE COALESCE(
                            -- For 2022-2023: Use planning region from tract
                            CASE 
                                WHEN CAST(h.county_code AS STRING) LIKE '09%' 
                                     AND CAST(h.county_code AS STRING) NOT LIKE '091%'
                                     AND ct_tract.geoid IS NOT NULL THEN
                                    SUBSTR(LPAD(CAST(ct_tract.geoid AS STRING), 11, '0'), 1, 5)
                                ELSE NULL
                            END,
                            -- For 2024: Use planning region code directly from county_code
                            CAST(h.county_code AS STRING)
                        ) IN UNNEST([{geoids_array}])
                        AND h.lei IN ('{peer_leis_str}')"""
                        )
                        sql = sql.replace('@county', f"UNNEST([{geoids_array}])")
                    # Replace single year with IN clause for all years (do this BEFORE the general @year replace)
                    # Check if using de_hmda table (activity_year is INT64, not STRING)
                    if 'justdata.de_hmda' in sql or 'de_hmda' in sql:
                        # For de_hmda: activity_year is INT64, use unquoted integers
                        years_int_str = ', '.join(map(str, validated_years))
                        sql = sql.replace("AND h.activity_year = @year", f"AND h.activity_year IN ({years_int_str})")
                        if '@year' in sql:
                            sql = sql.replace('@year', years_int_str)
                    else:
                        # For old hmda.hmda table: activity_year is STRING, use quoted strings
                        sql = sql.replace("AND h.activity_year = @year", f"AND h.activity_year IN ('{years_str}')")
                        if '@year' in sql:
                            sql = sql.replace('@year', f"'{years_str}'")
                    sql = sql.replace('@loan_purpose', "'all'")
                    
                    # Apply filters to the SQL template
                    sql = apply_filters_to_sql_template(sql, query_filters)
                    
                    batch_results = execute_query(client, sql)
                    if batch_results:
                        peer_results.extend(batch_results)
            except Exception as e:
                logger.warning(f"Error querying peers: {e}")
            
            logger.info(f"Found {len(peer_results)} aggregated rows for {len(peer_leis)} peer lenders")
        else:
            logger.warning(f"No peer lenders found for comparison. Analysis will proceed with subject lender data only.")
            if progress_tracker:
                progress_tracker.update_progress('querying_data', 45, 'No peer lenders found - proceeding with subject lender only...')
        
        if progress_tracker:
            progress_tracker.update_progress('building_report', 80, 'Building lender report...')
        
        # Try to get assets from CFPB API if available
        assets = None
        try:
            from justdata.apps.dataexplorer.utils.cfpb_client import CFPBClient
            cfpb_client = CFPBClient()
            if cfpb_client and cfpb_client._is_enabled():
                logger.info(f"CFPB client is enabled, attempting to fetch assets for LEI: {subject_lei}")
                institution = cfpb_client.get_institution_by_lei(subject_lei)
                if not institution:
                    lender_name = lender_info.get('name', '')
                    logger.info(f"No institution found by LEI, trying by name: {lender_name}")
                    institution = cfpb_client.get_institution_by_name(lender_name)
                if institution:
                    logger.info(f"Found institution in CFPB API: {institution.get('name', 'Unknown')}")
                    # Try multiple possible asset field names
                    assets = (institution.get('assets') or 
                             institution.get('total_assets') or
                             institution.get('asset_size') or
                             institution.get('assetSize') or
                             institution.get('totalAssets') or
                             institution.get('asset_size_category'))
                    if assets is not None:
                        try:
                            # If it's a string with numbers, try to extract
                            if isinstance(assets, str):
                                # Remove commas and try to parse
                                assets_clean = assets.replace(',', '').replace('$', '').strip()
                                assets = float(assets_clean) if assets_clean else None
                            else:
                                assets = float(assets) if assets else None
                            logger.info(f"Successfully parsed assets: ${assets:,.0f}" if assets else "Assets is None")
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Could not convert assets to float: {assets}, error: {e}")
                            assets = None
                    else:
                        logger.info("No assets field found in institution data")
                else:
                    logger.info(f"No institution found in CFPB API for LEI: {subject_lei} or name: {lender_info.get('name', '')}")
            else:
                logger.info("CFPB client is not enabled or not available")
        except Exception as e:
            logger.warning(f"Could not get assets from CFPB API: {e}", exc_info=True)
        
        # Update lender_info with assets
        lender_info['assets'] = assets
        
        # Build report
        # Pass all metros data separately so top metros table shows ALL metros, not just selected geography
        report_data = build_lender_report(
            subject_hmda_data=subject_results,
            peer_hmda_data=peer_results,
            lender_info=lender_info,
            years=validated_years,
            census_data={},
            historical_census_data={},
            hud_data={},
            progress_tracker=progress_tracker,
            action_taken=query_filters.get('action_taken', ['1']),
            all_metros_data=all_metros_results,  # For top metros table - shows all metros, not just selected geography
            geography_scope=geography_scope  # Pass geography scope to conditionally build Table 3
        )
        
        # Store metadata
        original_filters = wizard_data.get('filters', {})
        
        # Determine peer selection method text based on comparison_group
        if comparison_group == 'peers':
            peer_selection_method_text = f'{int(peer_min_percent * 100)}% to {int(peer_max_percent * 100)}% of subject lender volume'
        elif comparison_group == 'banks':
            peer_selection_method_text = 'All banks'
        elif comparison_group == 'credit_unions':
            peer_selection_method_text = 'All credit unions'
        elif comparison_group == 'mortgage':
            peer_selection_method_text = 'All mortgage companies'
        else:  # 'all'
            peer_selection_method_text = 'All other lenders'
        
        metadata = {
            'lender': lender_info,
            'years': validated_years,
            'peer_count': len(peer_leis),
            'report_type': 'lender',
            'peer_selection_method': peer_selection_method_text,
            'peer_min_percent': peer_min_percent,
            'peer_max_percent': peer_max_percent,
            'geography': f"{len(target_counties)} counties",  # Don't list all counties
            # Format geographic selection method: replace underscores, title case, then fix CBSAs capitalization
            'geographic_selection_method': geography_scope.replace('_', ' ').title().replace('Cbsas', 'CBSAs').replace('Cbsa', 'CBSA'),  # e.g., "All CBSAs", "Branch CBSAs", "Loan CBSAs"
            'geography_scope': geography_scope,
            'comparison_group': comparison_group,
            'hmda_filters': {
                'action_taken': query_filters.get('action_taken', ['1']),
                'occupancy_type': query_filters.get('occupancy', ['1']),
                'total_units': query_filters.get('total_units', ['1', '2', '3', '4']),
                'construction_method': query_filters.get('construction', ['1']),
                'loan_type': query_filters.get('loan_type', ['1', '2', '3', '4']),
                'reverse_mortgage': 'excluded' if query_filters.get('exclude_reverse_mortgages', True) else 'included'
            }
        }
        
        # Generate peer data sheet for Excel export
        peer_data_sheet = _generate_peer_data_sheet_for_excel(
            subject_lei, peer_leis, validated_years, target_counties, query_filters, PROJECT_ID, client
        )
        
        # Convert all_metros_results to list of dicts for Excel
        all_metros_list = []
        if all_metros_results:
            if isinstance(all_metros_results, list):
                # Already a list, but may need to aggregate by CBSA
                metros_df = pd.DataFrame(all_metros_results)
                if not metros_df.empty:
                    # Aggregate by CBSA and loan purpose
                    all_metros_list = _format_all_metros_for_excel(metros_df, validated_years, PROJECT_ID, client)
            else:
                all_metros_list = []
        
        # Store analysis result with all data for Excel export
        result_dict = {
            'success': True,
            'report_data': report_data,
            'metadata': metadata,
            'all_metros_data': all_metros_list,
            'peer_data': peer_data_sheet
        }
        
        if job_id:
            store_analysis_result(job_id, result_dict)
        
        if progress_tracker:
            progress_tracker.complete(success=True)
        
        return result_dict
        
    except Exception as e:
        logger.error(f"Error in lender analysis: {e}", exc_info=True)
        if progress_tracker:
            progress_tracker.complete(success=False, error=str(e))
        return {
            'success': False,
            'error': f'An error occurred during analysis: {str(e)}'
        }

