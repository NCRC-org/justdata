"""
Generate assessment areas from branch locations.

This module queries all branch locations for a bank and groups them by CBSA/metro area
to automatically create assessment areas. This serves as a proxy for assessment areas
when manual definition is not available.
"""

from typing import List, Dict, Optional, Tuple
from shared.utils.bigquery_client import get_bigquery_client, execute_query
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
        FROM `{PROJECT_ID}.branches.sod25` b
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


def generate_assessment_areas_from_branches(
    rssd: str,
    year: int = 2025,
    group_by_cbsa: bool = True,
    min_branches_per_county: int = 1,
    min_branch_percentage: float = 0.01
) -> List[Dict[str, any]]:
    """
    Generate assessment areas from branch locations.
    
    Groups branches by CBSA/metro area (or by individual county if group_by_cbsa=False)
    to create assessment areas. Counties with fewer than min_branches_per_county are excluded.
    Additionally, counties with less than min_branch_percentage (default 1%) of the bank's
    total branch locations are excluded.
    
    Args:
        rssd: Bank's RSSD ID (string)
        year: Year for branch data (default: 2025)
        group_by_cbsa: If True, group counties by CBSA/metro area. If False, create one
                       assessment area per county.
        min_branches_per_county: Minimum number of branches required in a county to include it
        min_branch_percentage: Minimum percentage (as decimal, e.g., 0.01 for 1%) of total
                              branches required in a county to include it. Counties with less
                              than this percentage are excluded.
    
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
        Counties with less than 1% of the bank's total branch locations are automatically
        excluded to focus on significant market presence areas.
    """
    if not rssd or not rssd.strip():
        return []
    
    # Get all branches for the bank
    branch_df = get_all_branches_for_bank(rssd, year)
    
    if branch_df.empty:
        return []
    
    # Calculate total branches across all counties
    total_branches = branch_df['branch_count'].sum()
    
    # Filter by minimum branches per county (absolute count)
    branch_df = branch_df[branch_df['branch_count'] >= min_branches_per_county]
    
    # Filter by minimum percentage of total branches (1% threshold)
    if total_branches > 0 and min_branch_percentage > 0:
        min_branches_by_percentage = max(1, int(total_branches * min_branch_percentage))
        branch_df = branch_df[branch_df['branch_count'] >= min_branches_by_percentage]
        print(f"  Filtered counties: keeping only those with >= {min_branches_by_percentage} branches ({min_branch_percentage*100:.1f}% of total {total_branches} branches)")
    
    if branch_df.empty:
        return []
    
    assessment_areas = []
    
    if group_by_cbsa:
        # Group by CBSA/metro area
        for cbsa_code, group in branch_df.groupby('cbsa_code'):
            if group.empty:
                continue
            cbsa_name = group.iloc[0]['cbsa_name'] if 'cbsa_name' in group.columns else 'Unknown'
            
            # Skip if no valid CBSA (e.g., "N/A" or "Non-Metro Area")
            if cbsa_code in ['N/A', None, ''] or cbsa_name == 'Non-Metro Area':
                # Create individual assessment areas for non-metro counties
                for _, row in group.iterrows():
                    geoid5 = str(row.get('geoid5', '')).zfill(5) if pd.notna(row.get('geoid5')) else ''
                    if len(geoid5) == 5:
                        state_code = geoid5[:2]
                        county_code = geoid5[2:]
                        county_state = row.get('county_state', '') if 'county_state' in row else ''
                        
                        assessment_areas.append({
                            'cbsa_name': county_state or f'County {geoid5}',
                            'counties': [
                                {
                                    'state_code': state_code,
                                    'county_code': county_code
                                }
                            ]
                        })
            else:
                # Group counties by CBSA
                counties = []
                for _, row in group.iterrows():
                    geoid5 = str(row.get('geoid5', '')).zfill(5) if pd.notna(row.get('geoid5')) else ''
                    if len(geoid5) == 5:
                        state_code = geoid5[:2]
                        county_code = geoid5[2:]
                        counties.append({
                            'state_code': state_code,
                            'county_code': county_code
                        })
                
                if counties:
                    assessment_areas.append({
                        'cbsa_name': cbsa_name,
                        'counties': counties
                    })
    else:
        # Create one assessment area per county
        for _, row in branch_df.iterrows():
            geoid5 = str(row.get('geoid5', '')).zfill(5) if pd.notna(row.get('geoid5')) else ''
            if len(geoid5) == 5:
                state_code = geoid5[:2]
                county_code = geoid5[2:]
                county_state = row.get('county_state', '') if 'county_state' in row else ''
                
                assessment_areas.append({
                    'cbsa_name': county_state or f'County {geoid5}',
                    'counties': [
                        {
                            'state_code': state_code,
                            'county_code': county_code
                        }
                    ]
                })
    
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

