"""Excel export formatters for lender analysis."""
import logging
from datetime import datetime
from typing import Any, Dict, List
from justdata.apps.dataexplorer.sql_loader import load_sql

import pandas as pd

from justdata.shared.utils.bigquery_client import escape_sql_string

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
        from justdata.apps.dataexplorer.report_builder import filter_df_by_loan_purpose
        
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
        years_int_str = ", ".join(map(str, years))  # Unquoted for INT64 columns (de_hmda)
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
        
        peer_query = load_sql("peer_data.sql").format(PROJECT_ID=PROJECT_ID, action_taken_clause=action_taken_clause, construction_clause=construction_clause, counties_list=counties_list, loan_type_clause=loan_type_clause, occupancy_clause=occupancy_clause, peer_leis_str=peer_leis_str, reverse_clause=reverse_clause, total_units_clause=total_units_clause, years_int_str=years_int_str)
        
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


