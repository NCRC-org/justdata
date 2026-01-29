"""
Generate assessment areas from branch locations.

This module queries all branch locations for a bank and groups them by CBSA/metro area
to automatically create assessment areas. This serves as a proxy for assessment areas
when manual definition is not available.
"""

from typing import List, Dict, Optional, Tuple
from justdata.shared.utils.bigquery_client import get_bigquery_client, execute_query, escape_sql_string
from justdata.apps.mergermeter.config import PROJECT_ID
import pandas as pd
import os

# Get PROJECT_ID - handle both relative and absolute imports
# PROJECT_ID is also available via environment variable
PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'justdata-ncrc')
# Try to import from config if available (for consistency with other modules)
try:
    import sys
    from pathlib import Path
    # Try absolute import first
    config_path = Path(__file__).parent / 'config.py'
    if config_path.exists():
        import importlib.util
        spec = importlib.util.spec_from_file_location("config", config_path)
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)
        if hasattr(config_module, 'PROJECT_ID'):
            PROJECT_ID = config_module.PROJECT_ID
except Exception:
    # If all else fails, use environment variable or default
    pass


def get_all_branches_for_bank(
    rssd: str,
    year: int = 2025
) -> pd.DataFrame:
    """
    Query all branch locations for a bank, regardless of assessment area.
    
    Args:
        rssd: Bank's RSSD ID (string)
        year: Year for branch data (default: 2025)
    
    Returns:
        DataFrame with columns: geoid5, county_state, cbsa_code, cbsa_name, branch_count
    """
    if not rssd or not rssd.strip():
        return pd.DataFrame()
    
    query = f"""
    WITH
    -- CBSA crosswalk to get CBSA codes and names from GEOID5 (include all areas for the lookup)
    cbsa_crosswalk AS (
        SELECT
            CAST(geoid5 AS STRING) as geoid5,
            CAST(cbsa_code AS STRING) as cbsa_code,
            CBSA as cbsa_name,
            County as county_name,
            State as state_name,
            CONCAT(County, ', ', State) as county_state
        FROM `{PROJECT_ID}.shared.cbsa_to_county`
    ),

    -- Get all branches for the bank
    bank_branches AS (
        SELECT
            CAST(b.rssd AS STRING) as rssd,
            CAST(b.geoid5 AS STRING) as geoid5,
            b.uninumbr
        FROM `{PROJECT_ID}.branchsight.sod` b
        WHERE CAST(b.year AS STRING) = '{year}'
            AND CAST(b.rssd AS STRING) = '{rssd}'
            AND b.geoid5 IS NOT NULL
    ),

    -- Deduplicate branches (use uninumbr as unique identifier)
    deduplicated_branches AS (
        SELECT
            geoid5
        FROM (
            SELECT *,
                ROW_NUMBER() OVER (PARTITION BY uninumbr ORDER BY rssd) as rn
            FROM bank_branches
        )
        WHERE rn = 1
    ),

    -- Join with CBSA crosswalk and aggregate by county/CBSA
    branch_counties AS (
        SELECT
            db.geoid5,
            COALESCE(c.county_state, 'Unknown') as county_state,
            COALESCE(c.county_name, 'Unknown') as county_name,
            COALESCE(c.state_name, 'Unknown') as state_name,
            -- For CBSA code, treat 99999 (rural) as N/A
            CASE WHEN COALESCE(c.cbsa_code, 'N/A') = '99999' THEN 'N/A' ELSE COALESCE(c.cbsa_code, 'N/A') END as cbsa_code,
            CASE WHEN COALESCE(c.cbsa_code, 'N/A') = '99999' THEN 'Non-Metro Area' ELSE COALESCE(c.cbsa_name, 'Non-Metro Area') END as cbsa_name,
            COUNT(*) as branch_count
        FROM deduplicated_branches db
        LEFT JOIN cbsa_crosswalk c
            ON db.geoid5 = c.geoid5
        GROUP BY db.geoid5, c.county_state, c.county_name, c.state_name, c.cbsa_code, c.cbsa_name
    )

    SELECT
        geoid5,
        county_state,
        county_name,
        state_name,
        cbsa_code,
        cbsa_name,
        branch_count
    FROM branch_counties
    WHERE cbsa_code != '99999'
    ORDER BY cbsa_code, county_state
    """
    
    try:
        client = get_bigquery_client(PROJECT_ID)
        results = execute_query(client, query)
        
        if not results:
            return pd.DataFrame()
        
        df = pd.DataFrame(results)
        return df
        
    except Exception as e:
        print(f"Error querying branches for RSSD {rssd}: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def get_cbsa_deposit_shares(
    rssd: str,
    year: int = 2025
) -> Tuple[pd.DataFrame, float]:
    """
    Get deposit data by CBSA and calculate the bank's deposit share of its national total.
    
    Args:
        rssd: Bank's RSSD ID (string)
        year: Year for branch data (default: 2025)
    
    Returns:
        Tuple of (DataFrame, total_national_deposits)
        DataFrame columns: cbsa_code, cbsa_name, cbsa_deposits, national_deposit_share_pct
        total_national_deposits: Bank's total deposits across all branches nationally
    """
    if not rssd or not rssd.strip():
        return pd.DataFrame(), 0.0
    
    query = f"""
    WITH
    -- CBSA crosswalk to get CBSA codes and names from GEOID5 (exclude rural areas with code 99999)
    cbsa_crosswalk AS (
        SELECT
            CAST(geoid5 AS STRING) as geoid5,
            CAST(cbsa_code AS STRING) as cbsa_code,
            CBSA as cbsa_name
        FROM `{PROJECT_ID}.shared.cbsa_to_county`
        WHERE CAST(cbsa_code AS STRING) != '99999'
    ),
    
    -- Get all branch deposits by county for the subject bank
    bank_deposits_by_county AS (
        SELECT 
            CAST(b.geoid5 AS STRING) as geoid5,
            SUM(b.deposits_000s * 1000) as bank_deposits  -- Convert from thousands to actual amount
        FROM `{PROJECT_ID}.branchsight.sod` b
        WHERE CAST(b.year AS STRING) = '{year}'
            AND CAST(b.rssd AS STRING) = '{rssd}'
            AND b.geoid5 IS NOT NULL
            AND b.deposits_000s IS NOT NULL
            AND b.deposits_000s > 0
        GROUP BY geoid5
    ),
    
    -- Calculate total national deposits for the bank
    total_national_deposits AS (
        SELECT SUM(bank_deposits) as total_deposits
        FROM bank_deposits_by_county
    ),
    
    -- Get state info for non-metro counties
    state_crosswalk AS (
        SELECT
            CAST(geoid5 AS STRING) as geoid5,
            State as state_name
        FROM `{PROJECT_ID}.shared.cbsa_to_county`
    ),
    
    -- Aggregate bank deposits by CBSA (for metro areas) and by State (for non-metro)
    bank_deposits_by_cbsa AS (
        SELECT 
            CASE 
                WHEN c.cbsa_code IS NULL OR CAST(c.cbsa_code AS STRING) = 'N/A' 
                THEN CONCAT('NON-METRO-', s.state_name)
                ELSE CAST(c.cbsa_code AS STRING)
            END as cbsa_code,
            CASE 
                WHEN c.cbsa_code IS NULL OR CAST(c.cbsa_code AS STRING) = 'N/A' 
                THEN CONCAT(s.state_name, ' Non-Metro Area')
                ELSE COALESCE(c.cbsa_name, 'Non-Metro Area')
            END as cbsa_name,
            SUM(bd.bank_deposits) as cbsa_deposits,
            MAX(s.state_name) as state_name  -- For non-metro areas, track the state
        FROM bank_deposits_by_county bd
        LEFT JOIN cbsa_crosswalk c
            ON bd.geoid5 = c.geoid5
        LEFT JOIN state_crosswalk s
            ON bd.geoid5 = s.geoid5
        GROUP BY 
            CASE 
                WHEN c.cbsa_code IS NULL OR CAST(c.cbsa_code AS STRING) = 'N/A' 
                THEN CONCAT('NON-METRO-', s.state_name)
                ELSE CAST(c.cbsa_code AS STRING)
            END,
            CASE 
                WHEN c.cbsa_code IS NULL OR CAST(c.cbsa_code AS STRING) = 'N/A' 
                THEN CONCAT(s.state_name, ' Non-Metro Area')
                ELSE COALESCE(c.cbsa_name, 'Non-Metro Area')
            END,
            s.state_name
        HAVING SUM(bd.bank_deposits) > 0
    )
    
    -- Calculate percentage of national deposits in each CBSA
    SELECT 
        bdc.cbsa_code,
        bdc.cbsa_name,
        bdc.cbsa_deposits,
        SAFE_DIVIDE(bdc.cbsa_deposits, tnd.total_deposits) * 100 as national_deposit_share_pct,
        tnd.total_deposits as total_national_deposits,
        bdc.state_name
    FROM bank_deposits_by_cbsa bdc
    CROSS JOIN total_national_deposits tnd
    WHERE tnd.total_deposits > 0
    ORDER BY national_deposit_share_pct DESC, cbsa_code
    """
    
    try:
        client = get_bigquery_client(PROJECT_ID)
        results = execute_query(client, query)
        
        if not results:
            return pd.DataFrame(), 0.0
        
        df = pd.DataFrame(results)
        total_deposits = df['total_national_deposits'].iloc[0] if not df.empty else 0.0
        
        return df, total_deposits
        
    except Exception as e:
        print(f"Error querying CBSA deposit shares for RSSD {rssd}: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame(), 0.0


def _get_assessment_areas_from_branch_counties(branch_df: pd.DataFrame, client) -> List[Dict[str, any]]:
    """
    Build assessment areas from branch counties only (not all counties in CBSA).

    This function groups branch locations by CBSA but only includes counties
    where the bank actually has branches, not all counties in the metro area.

    Args:
        branch_df: DataFrame from get_all_branches_for_bank() with columns:
                   geoid5, county_state, county_name, state_name, cbsa_code, cbsa_name, branch_count
        client: BigQuery client (not used - kept for API compatibility)

    Returns:
        List of assessment area dictionaries
    """
    if branch_df.empty:
        return []

    # The branch_df now contains all the data we need - no second query required
    # This fixes the timeout issue for large banks like JPMorgan Chase

    # Group counties by CBSA directly from the DataFrame
    cbsa_counties = {}
    for _, row in branch_df.iterrows():
        geoid5 = str(row.get('geoid5', '')).zfill(5)
        cbsa_code = str(row.get('cbsa_code', 'N/A'))
        state_name = row.get('state_name', '')
        county_name = row.get('county_name', '')

        # Handle non-metro areas (N/A or 99999 cbsa_code)
        if cbsa_code in ('N/A', '99999', '', None):
            cbsa_key = f'NON-METRO-{state_name}'
            cbsa_name = f"{state_name} Non-Metro Area"
        else:
            cbsa_key = cbsa_code
            cbsa_name = row.get('cbsa_name', f"CBSA {cbsa_code}")

        if cbsa_key not in cbsa_counties:
            cbsa_counties[cbsa_key] = {
                'cbsa_name': cbsa_name,
                'counties': []
            }

        if len(geoid5) == 5:
            state_code = geoid5[:2]
            county_code = geoid5[2:]
            # Avoid duplicates (same county might appear multiple times if multiple branches)
            county_entry = {
                'state_code': state_code,
                'county_code': county_code,
                'county_name': county_name,
                'state_name': state_name,
                'geoid5': geoid5
            }
            # Check if this county is already in the list
            existing_geoids = [c['geoid5'] for c in cbsa_counties[cbsa_key]['counties']]
            if geoid5 not in existing_geoids:
                cbsa_counties[cbsa_key]['counties'].append(county_entry)

    # Convert to list format
    assessment_areas = []
    for cbsa_key, cbsa_data in cbsa_counties.items():
        if cbsa_data['counties']:
            assessment_areas.append(cbsa_data)

    return assessment_areas


def _get_counties_for_cbsas(cbsa_codes: List[str], client) -> List[Dict[str, any]]:
    """
    Helper function to get all counties for a list of CBSA codes.

    NOTE: This function returns ALL counties in each CBSA, not just counties
    where branches exist. For branch-only counties, use
    _get_assessment_areas_from_branch_counties() instead.

    Args:
        cbsa_codes: List of CBSA codes (strings)
        client: BigQuery client

    Returns:
        List of assessment area dictionaries
    """
    assessment_areas = []

    for cbsa_code in cbsa_codes:
        # Handle non-metro areas
        if cbsa_code.startswith('NON-METRO-'):
            state_name = cbsa_code.replace('NON-METRO-', '')
            cbsa_name = f"{state_name} Non-Metro Area"

            non_metro_query = f"""
            SELECT DISTINCT
                CAST(geoid5 AS STRING) as geoid5,
                County as county_name,
                State as state_name,
                CONCAT(County, ', ', State) as county_state
            FROM `{PROJECT_ID}.shared.cbsa_to_county`
            WHERE (cbsa_code IS NULL OR CAST(cbsa_code AS STRING) = 'N/A')
                AND State = '{escape_sql_string(state_name)}'
            ORDER BY County
            """

            non_metro_results = execute_query(client, non_metro_query)

            if non_metro_results:
                counties = []
                for county_row in non_metro_results:
                    geoid5 = str(county_row.get('geoid5', '')).zfill(5)
                    if len(geoid5) == 5:
                        state_code = geoid5[:2]
                        county_code = geoid5[2:]
                        counties.append({
                            'state_code': state_code,
                            'county_code': county_code,
                            'county_name': county_row.get('county_name', ''),
                            'state_name': county_row.get('state_name', ''),
                            'geoid5': geoid5
                        })

                if counties:
                    assessment_areas.append({
                        'cbsa_name': cbsa_name,
                        'counties': counties
                    })
            continue

        # Query all counties in this CBSA (get CBSA name from first row) - exclude rural areas
        query = f"""
        SELECT DISTINCT
            CAST(geoid5 AS STRING) as geoid5,
            County as county_name,
            State as state_name,
            CBSA as cbsa_name,
            CONCAT(County, ', ', State) as county_state
        FROM `{PROJECT_ID}.shared.cbsa_to_county`
        WHERE CAST(cbsa_code AS STRING) = '{cbsa_code}'
            AND CAST(cbsa_code AS STRING) != '99999'
        ORDER BY State, County
        """

        county_results = execute_query(client, query)

        if not county_results:
            print(f"  Warning: No counties found for CBSA {cbsa_code}")
            continue

        # Get CBSA name from first result
        cbsa_name = county_results[0].get('cbsa_name', f"CBSA {cbsa_code}")

        # Build counties list
        counties = []
        for county_row in county_results:
            geoid5 = str(county_row.get('geoid5', '')).zfill(5)
            if len(geoid5) == 5:
                state_code = geoid5[:2]
                county_code = geoid5[2:]
                counties.append({
                    'state_code': state_code,
                    'county_code': county_code,
                    'county_name': county_row.get('county_name', ''),
                    'state_name': county_row.get('state_name', ''),
                    'geoid5': geoid5
                })

        if counties:
            assessment_areas.append({
                'cbsa_name': cbsa_name,
                'counties': counties
            })

    return assessment_areas


def generate_assessment_areas_from_branches(
    rssd: str,
    year: int = 2025,
    method: str = 'all_branches',
    min_share: float = 0.01,
    lei: str = None
) -> List[Dict[str, any]]:
    """
    Generate assessment areas from branch locations using one of three methods.

    Method 1: 'all_branches' - All CBSAs where the bank has branches
    Method 2: 'deposits' - CBSAs where bank has >=1% of its total branch deposits
    Method 3: 'loans' - CBSAs where bank has >=1% of its total loan applications

    For all methods, ONLY counties where the bank has branches are included
    (not all counties in the metro area).
    
    Args:
        rssd: Bank's RSSD ID (string)
        year: Year for branch data (default: 2025)
        method: Method to use - 'all_branches', 'deposits', or 'loans' (default: 'all_branches')
        min_share: Minimum share threshold (as decimal, e.g., 0.01 for 1%) for deposits/loans methods
    
    Returns:
        List of assessment area dictionaries with format:
        [
            {
                "cbsa_name": "Tampa-St. Petersburg-Clearwater, FL",
                "counties": [
                    {"state_code": "12", "county_code": "057"},
                    {"state_code": "12", "county_code": "103"}
                ]
            },
            ...
        ]
    """
    if not rssd or not rssd.strip():
        return []
    
    try:
        client = get_bigquery_client(PROJECT_ID)
        qualifying_cbsas = []
        
        # Get branch data - needed for all methods to filter to branch-only counties
        branch_df = get_all_branches_for_bank(rssd, year)

        if branch_df.empty:
            print(f"  No branches found for RSSD {rssd}")
            return []

        if method == 'all_branches':
            # Method 1: All CBSAs where bank has branches
            print(f"  Method: All counties where bank has branches (grouped by CBSA)")

            # Get unique CBSA codes where bank has branches (exclude rural areas with code 99999)
            cbsa_codes = branch_df[(branch_df['cbsa_code'] != 'N/A') & (branch_df['cbsa_code'] != '99999')]['cbsa_code'].unique().tolist()
            # Handle non-metro areas
            non_metro_states = branch_df[branch_df['cbsa_code'] == 'N/A']['county_state'].str.extract(r',\s*(\w+)$')[0].unique().tolist()
            for state in non_metro_states:
                if state:
                    cbsa_codes.append(f'NON-METRO-{state}')

            print(f"  Found {len(cbsa_codes)} CBSAs where bank has branches (excluding rural areas)")
            print(f"  Using {len(branch_df)} branch counties (not all counties in metro areas)")
            qualifying_cbsas = cbsa_codes

            # Use branch-only counties directly
            assessment_areas = _get_assessment_areas_from_branch_counties(branch_df, client)
            return assessment_areas
            
        elif method == 'deposits':
            # Method 2: CBSAs with >=1% of bank's branch deposits
            print(f"  Method: CBSAs with >={min_share*100:.1f}% of bank's branch deposits")
            cbsa_df, total_national_deposits = get_cbsa_deposit_shares(rssd, year)

            if cbsa_df.empty or total_national_deposits == 0:
                print(f"  No deposit data found for RSSD {rssd}")
                return []

            print(f"  Bank total national deposits: ${total_national_deposits:,.0f}")

            min_share_pct = min_share * 100
            # Filter by threshold and exclude rural areas (CBSA code 99999)
            qualifying_df = cbsa_df[
                (cbsa_df['national_deposit_share_pct'] >= min_share_pct) &
                (cbsa_df['cbsa_code'].astype(str) != '99999')
            ].copy()

            print(f"  Found {len(qualifying_df)} CBSAs where bank has >={min_share_pct:.1f}% of national deposits (excluding rural areas)")

            if qualifying_df.empty:
                return []

            qualifying_cbsas = qualifying_df['cbsa_code'].astype(str).tolist()

            # Filter branch_df to only qualifying CBSAs, then use branch-only counties
            filtered_branch_df = branch_df[branch_df['cbsa_code'].isin(qualifying_cbsas)].copy()
            print(f"  Using {len(filtered_branch_df)} branch counties in qualifying CBSAs")

            assessment_areas = _get_assessment_areas_from_branch_counties(filtered_branch_df, client)
            return assessment_areas
            
        elif method == 'loans':
            # Method 3: CBSAs with >=1% of bank's loan applications
            print(f"  Method: CBSAs with >={min_share*100:.1f}% of bank's loan applications")
            
            # For loans method, we need LEI (HMDA uses LEI, not RSSD)
            if not lei:
                print(f"  Error: LEI is required for 'loans' method. RSSD cannot be used to query HMDA data.")
                return []
            
            # Get loan data by CBSA
            query = f"""
            WITH
            -- Get CBSA codes for counties (exclude rural areas with code 99999)
            cbsa_crosswalk AS (
                SELECT DISTINCT
                    CAST(geoid5 AS STRING) as geoid5,
                    CAST(cbsa_code AS STRING) as cbsa_code,
                    CBSA as cbsa_name,
                    State as state_name
                FROM `{PROJECT_ID}.shared.cbsa_to_county`
                WHERE CAST(cbsa_code AS STRING) != '99999'
            ),
            
            -- Get bank's loans by county
            -- HMDA county_code is already GEOID5 (5-digit state+county FIPS code)
            bank_loans_by_county AS (
                SELECT 
                    LPAD(CAST(h.county_code AS STRING), 5, '0') as geoid5,
                    COUNT(*) as loan_count
                FROM `{PROJECT_ID}.shared.de_hmda` h
                WHERE CAST(h.activity_year AS STRING) = '{year}'
                    AND CAST(h.lei AS STRING) = '{lei}'
                    AND h.county_code IS NOT NULL
                    AND h.action_taken = '1'  -- Originations only
                GROUP BY geoid5
            ),
            
            -- Calculate total national loans
            total_national_loans AS (
                SELECT SUM(loan_count) as total_loans
                FROM bank_loans_by_county
            ),
            
            -- Aggregate loans by CBSA
            bank_loans_by_cbsa AS (
                SELECT 
                    CASE 
                        WHEN c.cbsa_code IS NULL OR CAST(c.cbsa_code AS STRING) = 'N/A' 
                        THEN CONCAT('NON-METRO-', c.state_name)
                        ELSE CAST(c.cbsa_code AS STRING)
                    END as cbsa_code,
                    CASE 
                        WHEN c.cbsa_code IS NULL OR CAST(c.cbsa_code AS STRING) = 'N/A' 
                        THEN CONCAT(c.state_name, ' Non-Metro Area')
                        ELSE COALESCE(c.cbsa_name, 'Non-Metro Area')
                    END as cbsa_name,
                    SUM(bl.loan_count) as cbsa_loans,
                    MAX(c.state_name) as state_name
                FROM bank_loans_by_county bl
                LEFT JOIN cbsa_crosswalk c
                    ON bl.geoid5 = c.geoid5
                GROUP BY 
                    CASE 
                        WHEN c.cbsa_code IS NULL OR CAST(c.cbsa_code AS STRING) = 'N/A' 
                        THEN CONCAT('NON-METRO-', c.state_name)
                        ELSE CAST(c.cbsa_code AS STRING)
                    END,
                    CASE 
                        WHEN c.cbsa_code IS NULL OR CAST(c.cbsa_code AS STRING) = 'N/A' 
                        THEN CONCAT(c.state_name, ' Non-Metro Area')
                        ELSE COALESCE(c.cbsa_name, 'Non-Metro Area')
                    END,
                    c.state_name
                HAVING SUM(bl.loan_count) > 0
            )
            
            SELECT 
                blc.cbsa_code,
                blc.cbsa_name,
                blc.cbsa_loans,
                SAFE_DIVIDE(blc.cbsa_loans, tnl.total_loans) * 100 as national_loan_share_pct,
                tnl.total_loans as total_national_loans,
                blc.state_name
            FROM bank_loans_by_cbsa blc
            CROSS JOIN total_national_loans tnl
            WHERE tnl.total_loans > 0
            ORDER BY national_loan_share_pct DESC, blc.cbsa_code
            """
            
            results = execute_query(client, query)
            
            if not results:
                print(f"  No loan data found for RSSD {rssd}")
                return []
            
            loan_df = pd.DataFrame(results)
            total_national_loans = loan_df['total_national_loans'].iloc[0] if not loan_df.empty else 0
            
            print(f"  Bank total national loans: {total_national_loans:,.0f}")
            
            min_share_pct = min_share * 100
            # Filter by threshold and exclude rural areas (CBSA code 99999)
            qualifying_df = loan_df[
                (loan_df['national_loan_share_pct'] >= min_share_pct) & 
                (loan_df['cbsa_code'].astype(str) != '99999')
            ].copy()
            
            print(f"  Found {len(qualifying_df)} CBSAs where bank has >={min_share_pct:.1f}% of national loans (excluding rural areas)")
            
            if qualifying_df.empty:
                return []
            
            qualifying_cbsas = qualifying_df['cbsa_code'].astype(str).tolist()

            # Filter branch_df to only qualifying CBSAs, then use branch-only counties
            filtered_branch_df = branch_df[branch_df['cbsa_code'].isin(qualifying_cbsas)].copy()
            print(f"  Using {len(filtered_branch_df)} branch counties in qualifying CBSAs")

            assessment_areas = _get_assessment_areas_from_branch_counties(filtered_branch_df, client)
            return assessment_areas

        else:
            raise ValueError(f"Unknown method: {method}. Must be 'all_branches', 'deposits', or 'loans'")
        
    except Exception as e:
        print(f"Error generating assessment areas for RSSD {rssd}: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_branch_count_by_county(
    rssd: str,
    year: int = 2025
) -> Dict[str, int]:
    """
    Get branch count for each county where the bank has branches.
    
    Args:
        rssd: Bank's RSSD ID (string)
        year: Year for branch data (default: 2025)
    
    Returns:
        Dictionary mapping GEOID5 to branch count
    """
    branch_df = get_all_branches_for_bank(rssd, year)
    
    if branch_df.empty:
        return {}
    
    return dict(zip(branch_df['geoid5'], branch_df['branch_count']))

