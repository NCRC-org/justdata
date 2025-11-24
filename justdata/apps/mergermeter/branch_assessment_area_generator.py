"""
Generate assessment areas from branch locations.

This module queries all branch locations for a bank and groups them by CBSA/metro area
to automatically create assessment areas. This serves as a proxy for assessment areas
when manual definition is not available.
"""

from typing import List, Dict, Optional, Tuple
from justdata.shared.utils.bigquery_client import get_bigquery_client, execute_query
from .config import PROJECT_ID
import pandas as pd


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
    -- CBSA crosswalk to get CBSA codes and names from GEOID5
    cbsa_crosswalk AS (
        SELECT
            CAST(geoid5 AS STRING) as geoid5,
            CAST(cbsa_code AS STRING) as cbsa_code,
            CBSA as cbsa_name,
            County as county_name,
            State as state_name,
            CONCAT(County, ', ', State) as county_state
        FROM `{PROJECT_ID}.geo.cbsa_to_county`
    ),
    
    -- Get all branches for the bank
    bank_branches AS (
        SELECT 
            CAST(b.rssd AS STRING) as rssd,
            CAST(b.geoid5 AS STRING) as geoid5,
            b.uninumbr
        FROM `{PROJECT_ID}.branches.sod` b
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
            COALESCE(c.cbsa_code, 'N/A') as cbsa_code,
            COALESCE(c.cbsa_name, 'Non-Metro Area') as cbsa_name,
            COUNT(*) as branch_count
        FROM deduplicated_branches db
        LEFT JOIN cbsa_crosswalk c
            ON db.geoid5 = c.geoid5
        GROUP BY db.geoid5, c.county_state, c.cbsa_code, c.cbsa_name
    )
    
    SELECT 
        geoid5,
        county_state,
        cbsa_code,
        cbsa_name,
        branch_count
    FROM branch_counties
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
    -- CBSA crosswalk to get CBSA codes and names from GEOID5
    cbsa_crosswalk AS (
        SELECT
            CAST(geoid5 AS STRING) as geoid5,
            CAST(cbsa_code AS STRING) as cbsa_code,
            CBSA as cbsa_name
        FROM `{PROJECT_ID}.geo.cbsa_to_county`
    ),
    
    -- Get all branch deposits by county for the subject bank
    bank_deposits_by_county AS (
        SELECT 
            CAST(b.geoid5 AS STRING) as geoid5,
            SUM(b.deposits_000s * 1000) as bank_deposits  -- Convert from thousands to actual amount
        FROM `{PROJECT_ID}.branches.sod` b
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
        FROM `{PROJECT_ID}.geo.cbsa_to_county`
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


def generate_assessment_areas_from_branches(
    rssd: str,
    year: int = 2025,
    min_deposit_share: float = 0.01
) -> List[Dict[str, any]]:
    """
    Generate assessment areas from branch locations based on CBSA deposit share.
    
    Includes all counties in CBSAs where the bank has >1% (or min_deposit_share) 
    of its total national deposits. If a CBSA qualifies, ALL counties in that CBSA
    are included (not just counties where the bank has branches).
    
    Args:
        rssd: Bank's RSSD ID (string)
        year: Year for branch data (default: 2025)
        min_deposit_share: Minimum deposit share (as decimal, e.g., 0.01 for 1%) of the
                          bank's national deposits required in a CBSA to include it.
                          CBSAs where the bank has less than this share are excluded.
    
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
    
    Note:
        - Calculates bank's total national deposits across all branches
        - For each CBSA, calculates bank's deposits in that CBSA
        - Includes CBSAs where bank has >1% of its national deposits
        - For qualifying CBSAs, includes ALL counties in that CBSA (from geo.cbsa_to_county)
    """
    if not rssd or not rssd.strip():
        return []
    
    # Get CBSA deposit shares (percentage of bank's national deposits)
    cbsa_df, total_national_deposits = get_cbsa_deposit_shares(rssd, year)
    
    if cbsa_df.empty or total_national_deposits == 0:
        print(f"  No deposit data found for RSSD {rssd}")
        return []
    
    print(f"  Bank total national deposits: ${total_national_deposits:,.0f}")
    
    # Filter by minimum deposit share (default 1% of bank's national deposits)
    min_share_pct = min_deposit_share * 100
    qualifying_cbsas = cbsa_df[cbsa_df['national_deposit_share_pct'] > min_share_pct].copy()
    
    print(f"  Found {len(qualifying_cbsas)} CBSAs where bank has >{min_share_pct:.1f}% of national deposits")
    
    if qualifying_cbsas.empty:
        return []
    
    # Get all counties for qualifying CBSAs
    assessment_areas = []
    
    try:
        client = get_bigquery_client(PROJECT_ID)
        
        for _, cbsa_row in qualifying_cbsas.iterrows():
            cbsa_code = str(cbsa_row['cbsa_code'])
            cbsa_name = str(cbsa_row['cbsa_name'])
            cbsa_deposits = cbsa_row['cbsa_deposits']
            share_pct = cbsa_row['national_deposit_share_pct']
            
            # Handle non-metro areas (counties without a CBSA code) - grouped by state
            if cbsa_code.startswith('NON-METRO-'):
                state_name = cbsa_row.get('state_name', '') or cbsa_name.replace(' Non-Metro Area', '')
                
                # Query all non-metro counties in this state
                non_metro_query = f"""
                SELECT DISTINCT
                    CAST(geoid5 AS STRING) as geoid5,
                    County as county_name,
                    State as state_name,
                    CONCAT(County, ', ', State) as county_state
                FROM `{PROJECT_ID}.geo.cbsa_to_county`
                WHERE (cbsa_code IS NULL OR CAST(cbsa_code AS STRING) = 'N/A')
                    AND State = '{state_name.replace("'", "''")}'
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
                                'county_code': county_code
                            })
                    
                    if counties:
                        print(f"  {cbsa_name}: {len(counties)} counties, ${cbsa_deposits:,.0f} deposits ({share_pct:.2f}% of national)")
                        assessment_areas.append({
                            'cbsa_name': cbsa_name,
                            'counties': counties
                        })
                continue
            
            # Query all counties in this CBSA
            query = f"""
            SELECT DISTINCT
                CAST(geoid5 AS STRING) as geoid5,
                County as county_name,
                State as state_name,
                CONCAT(County, ', ', State) as county_state
            FROM `{PROJECT_ID}.geo.cbsa_to_county`
            WHERE CAST(cbsa_code AS STRING) = '{cbsa_code}'
            ORDER BY State, County
            """
            
            county_results = execute_query(client, query)
            
            if not county_results:
                print(f"  Warning: No counties found for CBSA {cbsa_code} ({cbsa_name})")
                continue
            
            # Build counties list
            counties = []
            for county_row in county_results:
                geoid5 = str(county_row.get('geoid5', '')).zfill(5)
                if len(geoid5) == 5:
                    state_code = geoid5[:2]
                    county_code = geoid5[2:]
                    counties.append({
                        'state_code': state_code,
                        'county_code': county_code
                    })
            
            if counties:
                print(f"  CBSA {cbsa_name}: {len(counties)} counties, ${cbsa_deposits:,.0f} deposits ({share_pct:.2f}% of national)")
                assessment_areas.append({
                    'cbsa_name': cbsa_name,
                    'counties': counties
                })
        
    except Exception as e:
        print(f"Error generating assessment areas for RSSD {rssd}: {e}")
        import traceback
        traceback.print_exc()
        return []
    
    return assessment_areas


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

