#!/usr/bin/env python3
"""
HHI (Herfindahl-Hirschman Index) calculator for merger analysis.
Calculates deposit market concentration before and after merger.
"""

import pandas as pd
from typing import Dict, List, Tuple, Optional
from justdata.shared.utils.bigquery_client import get_bigquery_client, execute_query
from justdata.apps.mergermeter.config import PROJECT_ID


def calculate_hhi(deposits_by_bank: Dict[str, float]) -> float:
    """
    Calculate HHI (Herfindahl-Hirschman Index) for deposit market concentration.
    
    HHI = Σ(market_share_i)² × 10,000
    Where market_share_i is each bank's share of total deposits.
    
    Args:
        deposits_by_bank: Dictionary mapping bank RSSD to total deposits
        
    Returns:
        HHI value (0-10,000)
    """
    if not deposits_by_bank:
        return 0.0
    
    total_deposits = sum(deposits_by_bank.values())
    if total_deposits == 0:
        return 0.0
    
    # Calculate market shares and sum of squares
    hhi = 0.0
    for deposits in deposits_by_bank.values():
        market_share = deposits / total_deposits
        hhi += market_share ** 2
    
    # Scale to 0-10,000 range
    return hhi * 10000


def get_hhi_concentration_level(hhi: float) -> str:
    """
    Classify HHI value into concentration level.
    
    Args:
        hhi: HHI value (0-10,000)
        
    Returns:
        Concentration level string
    """
    if hhi < 1500:
        return "Low Concentration (Competitive)"
    elif hhi < 2500:
        return "Moderate Concentration"
    else:
        return "High Concentration"


def get_county_deposit_data(
    county_geoids: List[str],
    acquirer_rssd: str,
    target_rssd: str,
    year: int = 2025
) -> pd.DataFrame:
    """
    Query BigQuery for branch deposit data in counties where both banks have branches.
    
    Args:
        county_geoids: List of GEOID5 codes (5-digit strings) for counties
        acquirer_rssd: RSSD ID of acquiring bank
        target_rssd: RSSD ID of target bank
        year: Year for branch data (default: 2025)
        
    Returns:
        DataFrame with columns: geoid5, county_state, rssd, bank_name, total_deposits
    """
    if not county_geoids:
        return pd.DataFrame()
    
    # Format GEOID5 list
    geoid5_list = [str(g).zfill(5) for g in county_geoids]
    geoid5_str = ', '.join([f"'{g}'" for g in geoid5_list])
    
    query = f"""
    WITH county_branches AS (
        SELECT 
            CAST(b.geoid5 AS STRING) as geoid5,
            CONCAT(c.County, ', ', c.State) as county_state,
            CAST(b.rssd AS STRING) as rssd,
            b.bank_name,
            SUM(b.deposits_000s * 1000) as total_deposits  -- Convert from thousands to actual amount
        FROM `hdma1-242116.branches.sod25` b
        LEFT JOIN `hdma1-242116.geo.cbsa_to_county` c
            ON CAST(b.geoid5 AS STRING) = CAST(c.geoid5 AS STRING)
        WHERE CAST(b.year AS STRING) = '{year}'
            AND CAST(b.geoid5 AS STRING) IN ({geoid5_str})
            AND b.deposits_000s IS NOT NULL
            AND b.deposits_000s > 0
        GROUP BY geoid5, county_state, rssd, bank_name
    ),
    
    -- Find counties where both banks have branches
    counties_with_both_banks AS (
        SELECT geoid5, county_state
        FROM county_branches
        WHERE rssd IN ('{acquirer_rssd}', '{target_rssd}')
        GROUP BY geoid5, county_state
        HAVING COUNT(DISTINCT rssd) = 2  -- Both banks present
    )
    
    -- Get all bank deposits in counties where both banks have branches
    SELECT 
        cb.geoid5,
        cb.county_state,
        cb.rssd,
        cb.bank_name,
        cb.total_deposits
    FROM county_branches cb
    INNER JOIN counties_with_both_banks cwb
        ON cb.geoid5 = cwb.geoid5
    ORDER BY cb.geoid5, cb.total_deposits DESC
    """
    
    try:
        client = get_bigquery_client(PROJECT_ID)
        results = execute_query(client, query)
        
        if not results:
            print(f"[HHI] No deposit data found for {len(county_geoids)} counties, year {year}")
            print(f"[HHI] Query was for RSSDs: {acquirer_rssd}, {target_rssd}")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(results)
        print(f"[HHI] Found deposit data for {len(df)} bank-county combinations")
        print(f"[HHI] Counties with data: {df['geoid5'].nunique() if 'geoid5' in df.columns else 0}")
        return df
        
    except Exception as e:
        print(f"[HHI] Error querying county deposit data: {e}")
        print(f"[HHI] Query parameters: {len(county_geoids)} counties, year {year}, RSSDs: {acquirer_rssd}, {target_rssd}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def calculate_county_hhi(
    county_data: pd.DataFrame,
    acquirer_rssd: str,
    target_rssd: str
) -> Tuple[float, float, Dict[str, float], Dict[str, float]]:
    """
    Calculate pre-merger and post-merger HHI for a single county.
    
    Args:
        county_data: DataFrame with deposit data for one county
        acquirer_rssd: RSSD ID of acquiring bank
        target_rssd: RSSD ID of target bank
        
    Returns:
        Tuple of (pre_merger_hhi, post_merger_hhi, pre_merger_deposits, post_merger_deposits)
    """
    if county_data.empty:
        return 0.0, 0.0, {}, {}
    
    # Group deposits by RSSD
    deposits_by_rssd = county_data.groupby('rssd')['total_deposits'].sum().to_dict()
    
    # Pre-merger: banks are separate
    pre_merger_hhi = calculate_hhi(deposits_by_rssd)
    pre_merger_deposits = deposits_by_rssd.copy()
    
    # Post-merger: combine acquirer and target deposits
    post_merger_deposits = deposits_by_rssd.copy()
    
    # Combine acquirer and target into merged entity
    merged_deposits = 0.0
    merged_rssd = f"{acquirer_rssd}_merged_{target_rssd}"
    
    if acquirer_rssd in post_merger_deposits:
        merged_deposits += post_merger_deposits.pop(acquirer_rssd)
    if target_rssd in post_merger_deposits:
        merged_deposits += post_merger_deposits.pop(target_rssd)
    
    if merged_deposits > 0:
        post_merger_deposits[merged_rssd] = merged_deposits
    
    post_merger_hhi = calculate_hhi(post_merger_deposits)
    
    return pre_merger_hhi, post_merger_hhi, pre_merger_deposits, post_merger_deposits


def calculate_hhi_by_county(
    county_geoids: List[str],
    acquirer_rssd: str,
    target_rssd: str,
    year: int = 2025
) -> pd.DataFrame:
    """
    Calculate HHI for each county where both banks have branches.
    
    Args:
        county_geoids: List of GEOID5 codes for counties in assessment areas
        acquirer_rssd: RSSD ID of acquiring bank
        target_rssd: RSSD ID of target bank
        year: Year for branch data (default: 2025)
        
    Returns:
        DataFrame with columns:
        - County, State
        - GEOID5
        - Pre-Merger HHI
        - Post-Merger HHI
        - HHI Change
        - Pre-Merger Concentration Level
        - Post-Merger Concentration Level
        - Total Deposits (Pre-Merger)
        - Total Deposits (Post-Merger)
    """
    # Get deposit data for all counties
    deposit_df = get_county_deposit_data(county_geoids, acquirer_rssd, target_rssd, year)
    
    if deposit_df.empty:
        return pd.DataFrame(columns=[
            'County, State', 'GEOID5', 'Pre-Merger HHI', 'Post-Merger HHI',
            'HHI Change', 'Pre-Merger Concentration', 'Post-Merger Concentration',
            'Total Deposits (Pre-Merger)', 'Total Deposits (Post-Merger)'
        ])
    
    # Group by county and calculate HHI
    results = []
    
    for geoid5 in deposit_df['geoid5'].unique():
        county_data = deposit_df[deposit_df['geoid5'] == geoid5]
        if county_data.empty:
            continue
        county_state = county_data['county_state'].iloc[0] if 'county_state' in county_data.columns else 'Unknown'
        
        pre_hhi, post_hhi, pre_deposits, post_deposits = calculate_county_hhi(
            county_data, acquirer_rssd, target_rssd
        )
        
        hhi_change = post_hhi - pre_hhi
        
        total_pre = sum(pre_deposits.values())
        total_post = sum(post_deposits.values())
        
        results.append({
            'County, State': county_state,
            'GEOID5': geoid5,
            'Pre-Merger HHI': round(pre_hhi, 2),
            'Post-Merger HHI': round(post_hhi, 2),
            'HHI Change': round(hhi_change, 2),
            'Pre-Merger Concentration': get_hhi_concentration_level(pre_hhi),
            'Post-Merger Concentration': get_hhi_concentration_level(post_hhi),
            'Total Deposits (Pre-Merger)': total_pre,
            'Total Deposits (Post-Merger)': total_post
        })
    
    hhi_df = pd.DataFrame(results)
    hhi_df = hhi_df.sort_values('County, State')
    
    return hhi_df

