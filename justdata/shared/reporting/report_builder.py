"""
Report builder module for creating Excel reports from BigQuery data.
Handles data processing, trend analysis, and Excel export.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import os
import re

from justdata.shared.utils.report_time import analysis_date, analysis_stamp
from justdata.shared.utils.no_data import NO_DATA, dash_missing, is_missing
from justdata.shared.utils import fdic_institutions


def _share_text(pct) -> str:
    """"34.5%", or the em dash when there is no base."""
    return NO_DATA if is_missing(pct) else f"{pct}%"


def sanitize_sheet_name(name: str) -> str:
    r"""
    Sanitize Excel sheet name by removing invalid characters and truncating to 31 characters.
    
    Excel sheet names cannot contain: : \ / ? * [ ]
    Excel sheet names are limited to 31 characters.
    
    Args:
        name: Original sheet name
    
    Returns:
        Sanitized sheet name
    """
    # Replace invalid characters with dash
    invalid_chars = r'[:\\/?*\[\]]'
    sanitized = re.sub(invalid_chars, '-', name)
    
    # Truncate to 31 characters (Excel limit)
    if len(sanitized) > 31:
        sanitized = sanitized[:31]
    
    return sanitized


def build_report(raw_data: List[Dict[str, Any]], counties: List[str], years: List[int]) -> Dict[str, pd.DataFrame]:
    """
    Process raw BigQuery data and build comprehensive report dataframes.
    
    Args:
        raw_data: List of dictionaries from BigQuery results
        counties: List of counties in the report
        years: List of years in the report
        
    Returns:
        Dictionary containing multiple dataframes for different report sections
    """
    if not raw_data:
        raise ValueError("No data provided for report building")
    
    # Convert to DataFrame
    df = pd.DataFrame(raw_data)
    
    
    # Ensure required columns exist
    required_columns = ['bank_name', 'year', 'geoid5', 'county_state', 'total_branches', 'lmict', 'mmct']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")
    
    # Check if deposits column exists (optional but preferred)
    has_deposits = 'total_deposits' in df.columns
    if has_deposits:
        print(f"[DEBUG] Deposits column found. Sample values: {df['total_deposits'].head(5).tolist()}")
    else:
        print("[WARNING] Deposits column (total_deposits) not found in data. Deposits will show as N/A.")
    
    # Clean and prepare data
    df = clean_data(df)

    # One display name per bank (RSSD) for every table in the report.
    names = bank_display_names(df)

    # Calculate HHI for deposits in latest year
    hhi_data = calculate_hhi(df, names)

    # Calculate HHI for all years (for chart and table)
    hhi_by_year_data = calculate_hhi_by_year(df, years)

    # Build different report sections
    report_data = {
        'summary': create_summary_table(df, counties, years),
        'by_bank': create_bank_summary(df, years, names),  # Pass years for net change calculation
        'by_county': create_county_summary(df, counties, years),
        'trends': create_trend_analysis(df, years),
        'raw_data': df,
        'hhi': hhi_data,
        'hhi_by_year': hhi_by_year_data
    }

    return report_data


def _bank_key(df: pd.DataFrame) -> str:
    """Banks are RSSDs. Name grouping adds unrelated banks that share a name
    together (nine RSSDs are "Pinnacle Bank"), so it is only a fallback for
    data without an RSSD column."""
    return 'rssd' if 'rssd' in df.columns else 'bank_name'


def bank_display_names(df: pd.DataFrame) -> Dict[str, str]:
    """{rssd: name to show}: each bank's name in the latest year it appears.

    Where two different RSSDs in the report would show the same name, each
    gets its headquarters city and state from the FDIC, "Pinnacle Bank
    (Nashville, TN)", or its RSSD if the FDIC lookup fails.
    """
    if 'rssd' not in df.columns or df.empty:
        return {}
    rows = df[['year', 'rssd', 'bank_name']].copy()
    rows['rssd'] = rows['rssd'].astype(str)
    latest = rows.sort_values('year').drop_duplicates('rssd', keep='last')
    names = dict(zip(latest['rssd'], latest['bank_name'].astype(str)))

    by_name: Dict[str, List[str]] = {}
    for rssd, name in names.items():
        by_name.setdefault(name.casefold().strip(), []).append(rssd)
    shared = [r for group in by_name.values() if len(group) > 1 for r in group]
    if shared:
        hq = fdic_institutions.headquarters(shared)
        for rssd in shared:
            names[rssd] = f"{names[rssd]} ({hq.get(rssd) or 'RSSD ' + rssd})"
        # Two same-named banks in the same city: add the RSSD too.
        seen: Dict[str, List[str]] = {}
        for rssd in shared:
            seen.setdefault(names[rssd].casefold(), []).append(rssd)
        for group in seen.values():
            if len(group) > 1:
                for rssd in group:
                    names[rssd] = f"{names[rssd][:-1]}; RSSD {rssd})"
    return names


def _deposits_by_bank(year_df: pd.DataFrame, names: Optional[Dict[str, str]] = None) -> pd.DataFrame:
    """Deposits summed per bank (RSSD) for one year, with the name to show."""
    key = _bank_key(year_df)
    frame = year_df.copy()
    frame[key] = frame[key].astype(str)
    frame['total_deposits'] = pd.to_numeric(frame['total_deposits'], errors='coerce').fillna(0)
    out = frame.groupby(key, as_index=False)['total_deposits'].sum()
    if key == 'rssd':
        first_name = frame.drop_duplicates('rssd').set_index('rssd')['bank_name'].astype(str)
        out['bank_name'] = out['rssd'].map(lambda r: (names or {}).get(r) or first_name.get(r, ''))
    return out[out['total_deposits'] > 0]


def calculate_hhi(df: pd.DataFrame, names: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Calculate Herfindahl-Hirschman Index (HHI) for bank deposits in the latest year.
    
    HHI Interpretation:
    - HHI < 1,500: Low concentration (competitive market)
    - HHI 1,500-2,500: Moderate concentration
    - HHI > 2,500: High concentration
    
    Returns:
        Dictionary with HHI value, concentration level, year, and top banks by deposits
    """
    if 'total_deposits' not in df.columns:
        return {
            'hhi': None,
            'concentration_level': 'Not Available',
            'year': None,
            'total_deposits': None,
            'top_banks': []
        }
    
    # Find latest year
    latest_year = df['year'].max()
    latest_year_df = df[df['year'] == latest_year].copy()
    
    # Aggregate deposits by bank (RSSD), across all counties
    bank_deposits = _deposits_by_bank(latest_year_df, names if names is not None else bank_display_names(df))
    
    if bank_deposits.empty:
        return {
            'hhi': None,
            'concentration_level': 'Not Available',
            'year': latest_year,
            'total_deposits': 0,
            'top_banks': []
        }
    
    total_deposits = bank_deposits['total_deposits'].sum()
    
    # Calculate market shares (as percentages)
    bank_deposits['market_share'] = (bank_deposits['total_deposits'] / total_deposits) * 100
    
    # Calculate HHI: sum of squared market shares (0-10,000 scale)
    hhi = (bank_deposits['market_share'] ** 2).sum()
    
    # Determine concentration level
    if hhi < 1500:
        concentration_level = 'Low concentration (competitive market)'
    elif hhi < 2500:
        concentration_level = 'Moderate concentration'
    else:
        concentration_level = 'High concentration'
    
    # Get top banks by deposits
    top_cols = [c for c in ('rssd', 'bank_name', 'total_deposits', 'market_share') if c in bank_deposits.columns]
    top_banks = bank_deposits.nlargest(10, 'total_deposits')[top_cols].to_dict('records')
    
    return {
        'hhi': round(hhi, 2),
        'concentration_level': concentration_level,
        'year': int(latest_year),
        'total_deposits': int(total_deposits),
        'top_banks': top_banks,
        'total_banks': len(bank_deposits)
    }


def calculate_hhi_by_year(df: pd.DataFrame, years: Optional[List[int]] = None) -> List[Dict[str, Any]]:
    """
    Calculate Herfindahl-Hirschman Index (HHI) for bank deposits for each year.

    Every requested year gets a row. A year with no deposit data has
    hhi_value None, so it shows as a gap (an em dash in tables), never as a
    zero and never silently dropped (no-data decision, 2026-11-17; BS-002).

    Returns:
        List of dictionaries with year and hhi_value
    """
    if 'total_deposits' not in df.columns or 'year' not in df.columns:
        return []

    results = []
    data_years = {int(y) for y in df['year'].unique()}
    years = sorted({int(y) for y in years} | data_years) if years else sorted(data_years)

    for year in years:
        year_df = df[df['year'] == year].copy()

        # Aggregate deposits by bank (RSSD), across all counties
        bank_deposits = _deposits_by_bank(year_df) if not year_df.empty else pd.DataFrame()

        total_deposits = bank_deposits['total_deposits'].sum() if not bank_deposits.empty else 0
        if total_deposits == 0:
            results.append({'year': int(year), 'hhi_value': None})
            continue

        # Calculate market shares (as percentages)
        bank_deposits['market_share'] = (bank_deposits['total_deposits'] / total_deposits) * 100

        # Calculate HHI: sum of squared market shares (0-10,000 scale)
        hhi = (bank_deposits['market_share'] ** 2).sum()

        results.append({
            'year': int(year),
            'hhi_value': round(hhi, 2)
        })

    return results


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and prepare the raw data."""
    # Convert numeric columns
    numeric_columns = ['total_branches', 'lmict', 'mmct']
    if 'total_deposits' in df.columns:
        numeric_columns.append('total_deposits')
    
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Map lmict/mmct to br_lmi/br_minority for compatibility with existing code
    if 'lmict' in df.columns:
        df['br_lmi'] = df['lmict'].astype(int)
    if 'mmct' in df.columns:
        df['br_minority'] = df['mmct'].astype(int)
    
    # Ensure uninumbr exists (it should come from SQL query)
    if 'uninumbr' not in df.columns:
        # If missing, try to create a unique identifier from geoid5 + bank_name + year
        # This is a fallback, but ideally uninumbr should come from the query
        if 'geoid5' in df.columns and 'bank_name' in df.columns and 'year' in df.columns:
            df['uninumbr'] = df['geoid5'].astype(str) + '_' + df['bank_name'].astype(str) + '_' + df['year'].astype(str)
        else:
            raise ValueError("Missing required columns: uninumbr (and cannot create fallback)")
    
    # Convert year to integer
    df['year'] = pd.to_numeric(df['year'], errors='coerce').fillna(0).astype(int)
    
    # Clean bank names - remove "National Association" and variations, and remove everything after commas
    if 'bank_name' in df.columns:
        df['bank_name'] = df['bank_name'].str.strip()
        # Remove everything after the first comma (including the comma)
        df['bank_name'] = df['bank_name'].str.split(',').str[0].str.strip()
        # Remove "National Association" and variations (case-insensitive)
        df['bank_name'] = df['bank_name'].str.replace(r'\s+National\s+Association\s*$', '', case=False, regex=True)
        df['bank_name'] = df['bank_name'].str.replace(r'\s+National\s+Assoc\.?\s*$', '', case=False, regex=True)
        df['bank_name'] = df['bank_name'].str.replace(r'\s+N\.?A\.?\s*$', '', case=False, regex=True)
        # Clean up any extra whitespace
        df['bank_name'] = df['bank_name'].str.strip()
    
    # Remove rows with invalid data
    df = df[df['year'] > 0]
    if 'total_branches' in df.columns:
        df = df[df['total_branches'] >= 0]
    
    return df


def create_summary_table(df: pd.DataFrame, counties: List[str], years: List[int]) -> pd.DataFrame:
    """Create a high-level summary table with years as columns and variables as rows.
    Properly dedupes: LMI only, MMCT only, and both LMICT/MMCT."""
    
    # Need to work with unique branches (uninumbr) to properly dedupe
    if 'uninumbr' not in df.columns or 'br_lmi' not in df.columns or 'br_minority' not in df.columns:
        raise ValueError("Missing required columns: uninumbr, br_lmi, br_minority")
    
    result_data = {
        'Variable': ['Total Branches', 'LMI Only Branches', 'MMCT Only Branches', 'Both LMICT/MMCT Branches']
    }
    
    # Calculate for each year
    for year in sorted(years):
        year_df = df[df['year'] == year].copy()

        # No rows at all: the whole year is no data, an em dash, never 0
        # (no-data decision, 2026-11-17; a geography gap such as BS-002 shows
        # as no data instead of zero branches).
        if year_df.empty:
            result_data[str(year)] = [None, None, None, None]
            continue
        
        # Count unique total branches
        total_unique = year_df['uninumbr'].nunique()
    
        # Count unique branches that are LMI only (LMI=1, MMCT=0)
        lmi_only = year_df[(year_df['br_lmi'] == 1) & (year_df['br_minority'] == 0)]['uninumbr'].nunique()
        
        # Count unique branches that are MMCT only (LMI=0, MMCT=1)
        mmct_only = year_df[(year_df['br_lmi'] == 0) & (year_df['br_minority'] == 1)]['uninumbr'].nunique()
        
        # Count unique branches that are both (LMI=1, MMCT=1)
        both = year_df[(year_df['br_lmi'] == 1) & (year_df['br_minority'] == 1)]['uninumbr'].nunique()
        
        result_data[str(year)] = [
            int(total_unique),
            int(lmi_only),
            int(mmct_only),
            int(both)
        ]
    
    result = pd.DataFrame(result_data)
    
    # Calculate net change from first to last year
    if len(years) >= 2:
        first_year = str(min(years))
        last_year = str(max(years))
        
        net_changes = []
        for idx, row in result.iterrows():
            first_val = row[first_year]
            last_val = row[last_year]
            # No change when either end has no data
            net_change = None if is_missing(first_val) or is_missing(last_val) else last_val - first_val
            net_changes.append(net_change)
        
        result['Net Change'] = net_changes
    
    return result


# Net change by bank (T4, Jad 2026-11-20). Banks are matched across years on
# RSSD, never the name: the 2026 SOD table publishes names in title case and
# 2017 to 2025 in upper case, banks rename, and unrelated banks share names.
NEW_TO_COUNTY = 'New to this county'
BANK_CHANGE_NOTE = ("Net change counts all of a bank's branches. "
                    "Acquired shows how many came from another institution. "
                    "Acquired and transferred show branches that moved between institutions.")


def bank_branch_changes(df: pd.DataFrame, first_year: int, latest_year: int) -> Dict[str, Dict[str, Any]]:
    """Per-RSSD branch changes between the first and latest year.

    For each bank in either year: ``first`` and ``latest`` branch counts,
    ``opened`` (latest-year branches not in the first year at all),
    ``acquired`` (latest-year branches that were another RSSD's in the first
    year), ``closed`` (first-year branches gone by the latest year) and
    ``transferred_out`` (first-year branches another RSSD holds in the latest
    year). ``net = latest - first = opened + acquired - closed - transferred_out``.
    Branches are UNINUMBR, which the FDIC keeps with a branch through mergers.
    """
    rows = df[['year', 'rssd', 'bank_name', 'uninumbr']].copy()
    rows['rssd'] = rows['rssd'].astype(str)
    rows['uninumbr'] = rows['uninumbr'].astype(str)
    first = rows[rows['year'] == first_year].drop_duplicates('uninumbr')
    latest = rows[rows['year'] == latest_year].drop_duplicates('uninumbr')
    owner_first = dict(zip(first['uninumbr'], first['rssd']))
    owner_latest = dict(zip(latest['uninumbr'], latest['rssd']))
    names = {}
    for frame in (first, latest):          # latest year's name wins
        names.update(dict(zip(frame['rssd'], frame['bank_name'])))

    changes = {}
    for rssd in set(owner_first.values()) | set(owner_latest.values()):
        had = {u for u, r in owner_first.items() if r == rssd}
        has = {u for u, r in owner_latest.items() if r == rssd}
        acquired = sum(1 for u in has if u in owner_first and owner_first[u] != rssd)
        opened = sum(1 for u in has if u not in owner_first)
        closed = sum(1 for u in had if u not in owner_latest)
        transferred_out = sum(1 for u in had if u in owner_latest and owner_latest[u] != rssd)
        changes[rssd] = {
            'rssd': rssd, 'bank_name': names.get(rssd, ''),
            'first': len(had), 'latest': len(has), 'net': len(has) - len(had),
            'opened': opened, 'closed': closed, 'acquired': acquired,
            'transferred_out': transferred_out,
            'new_to_county': not had and acquired == 0 and bool(has),
        }
    return changes


def bank_changes_for_narrative(df: pd.DataFrame, years: List[int],
                               names: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """The bank-change figures the Section 2 narrative may use, precomputed.

    Opened, closed and acquired are separate figures; the narrative may not
    call acquired branches opened (spec 11's rule, applied early here).
    """
    if not years or 'rssd' not in df.columns:
        return {}
    first_year, latest_year = min(years), max(years)
    if first_year == latest_year or df[df['year'] == first_year].empty:
        return {}
    changes = bank_branch_changes(df, first_year, latest_year)
    names = names if names is not None else bank_display_names(df)
    for rssd, c in changes.items():
        c['bank_name'] = names.get(rssd, c['bank_name'])
    banks = sorted((c for c in changes.values() if c['latest'] > 0),
                   key=lambda c: (-c['latest'], c['bank_name']))
    left = sorted((c for c in changes.values() if c['latest'] == 0),
                  key=lambda c: (-c['first'], c['bank_name']))
    keep = ('bank_name', 'first', 'latest', 'opened', 'closed', 'acquired', 'transferred_out')
    return {
        'first_year': first_year, 'latest_year': latest_year,
        'banks': [{k: c[k] for k in keep} | {'new_to_county': c['new_to_county']} for c in banks[:10]],
        'banks_that_left': [{k: c[k] for k in keep} for c in left[:10]],
        'county_totals': {k: sum(c[k] for c in changes.values())
                          for k in ('first', 'latest', 'opened', 'closed', 'acquired')},
    }


def create_bank_summary(df: pd.DataFrame, years: List[int] = None,
                        names: Optional[Dict[str, str]] = None) -> pd.DataFrame:
    """Summary by bank (RSSD) for the latest year, every bank, largest first.

    Net Change is the bank's latest-year branch count minus its first-year
    count, matched on RSSD; Acquired counts latest-year branches that another
    RSSD held in the first year; Transferred Out counts first-year branches
    another RSSD holds in the latest year. A bank with no first-year branches and none
    acquired shows "New to this county". With no first-year data at all, both
    show the em dash.
    """
    if years is None:
        years = sorted(df['year'].unique().tolist())

    latest_year = max(years)
    first_year = min(years)

    if 'uninumbr' not in df.columns or 'br_lmi' not in df.columns or 'br_minority' not in df.columns:
        raise ValueError("Missing required columns: uninumbr, br_lmi, br_minority")
    if 'rssd' not in df.columns:
        raise ValueError("Missing required column: rssd")

    df = df.copy()
    df['rssd'] = df['rssd'].astype(str)
    latest_year_df = df[df['year'] == latest_year]
    has_first_year = not df[df['year'] == first_year].empty
    changes = bank_branch_changes(df, first_year, latest_year)
    names = names if names is not None else bank_display_names(df)

    bank_data = []
    for rssd in latest_year_df['rssd'].unique():
        bank_latest = latest_year_df[latest_year_df['rssd'] == rssd]
        bank_name = names.get(rssd) or bank_latest['bank_name'].iloc[0]
        total_branches_latest = bank_latest['uninumbr'].nunique()

        # Dedupe: LMI only, MMCT only, both
        lmi_only_latest = bank_latest[(bank_latest['br_lmi'] == 1) & (bank_latest['br_minority'] == 0)]['uninumbr'].nunique()
        mmct_only_latest = bank_latest[(bank_latest['br_lmi'] == 0) & (bank_latest['br_minority'] == 1)]['uninumbr'].nunique()
        both_latest = bank_latest[(bank_latest['br_lmi'] == 1) & (bank_latest['br_minority'] == 1)]['uninumbr'].nunique()

        lmi_only_pct = round((lmi_only_latest / total_branches_latest * 100), 1) if total_branches_latest > 0 else None
        mmct_only_pct = round((mmct_only_latest / total_branches_latest * 100), 1) if total_branches_latest > 0 else None
        both_pct = round((both_latest / total_branches_latest * 100), 1) if total_branches_latest > 0 else None

        change = changes[rssd]
        if first_year == latest_year:
            net_change, acquired, transferred = 0, 0, 0
        elif not has_first_year:
            net_change, acquired, transferred = NO_DATA, NO_DATA, NO_DATA
        elif change['new_to_county']:
            net_change, acquired, transferred = NEW_TO_COUNTY, 0, 0
        else:
            net_change, acquired, transferred = change['net'], change['acquired'], change['transferred_out']

        total_deposits = 0.0
        if 'total_deposits' in bank_latest.columns:
            total_deposits = float(pd.to_numeric(bank_latest['total_deposits'], errors='coerce').fillna(0).sum())
        deposits_formatted = f"{total_deposits / 1_000_000:,.0f}" if total_deposits > 0 else NO_DATA

        bank_data.append({
            'Bank Name': bank_name,
            'Total Branches': total_branches_latest,
            'Deposits ($ Millions)': deposits_formatted,
            'LMI Only Branches': f"{lmi_only_latest} ({_share_text(lmi_only_pct)})",
            'MMCT Only Branches': f"{mmct_only_latest} ({_share_text(mmct_only_pct)})",
            'Both LMICT/MMCT Branches': f"{both_latest} ({_share_text(both_pct)})",
            'Net Change': net_change,
            'Acquired': acquired,
            'Transferred Out': transferred,
            '_total_branches': total_branches_latest,
        })

    result = pd.DataFrame(bank_data)
    if result.empty:
        return result
    result = result.sort_values(['_total_branches', 'Bank Name'], ascending=[False, True]).reset_index(drop=True)
    return result.drop(columns=['_total_branches'])


def create_county_summary(df: pd.DataFrame, counties: List[str] = None, years: List[int] = None) -> pd.DataFrame:
    """Create summary by county for the most recent year. Returns empty DataFrame if only one county.
    Includes deduped LMI Only, MMCT Only, and Both LMICT/MMCT columns."""
    # Only create this table if multiple counties
    if counties and len(counties) <= 1:
        return pd.DataFrame()
    
    if not years or len(years) == 0:
        return pd.DataFrame()
    
    # Use the most recent year instead of hardcoded 2024
    latest_year = max(years)
    df_latest = df[df['year'] == latest_year].copy()
    
    if df_latest.empty:
        return pd.DataFrame()
    
    # Need to work with unique branches (uninumbr) to properly dedupe
    if 'uninumbr' not in df_latest.columns or 'br_lmi' not in df_latest.columns or 'br_minority' not in df_latest.columns:
        raise ValueError("Missing required columns: uninumbr, br_lmi, br_minority")
    
    county_data = []
    
    # Process each county
    for county in df_latest['county_state'].unique():
        county_df = df_latest[df_latest['county_state'] == county]
        
        # Count unique total branches
        total_unique = county_df['uninumbr'].nunique()
        
        # Dedupe: LMI only, MMCT only, both
        lmi_only = county_df[(county_df['br_lmi'] == 1) & (county_df['br_minority'] == 0)]['uninumbr'].nunique()
        mmct_only = county_df[(county_df['br_lmi'] == 0) & (county_df['br_minority'] == 1)]['uninumbr'].nunique()
        both = county_df[(county_df['br_lmi'] == 1) & (county_df['br_minority'] == 1)]['uninumbr'].nunique()
        
        # Count unique banks
        num_banks = county_df['bank_name'].nunique()
        
        # Calculate percentages
        lmi_only_pct = round((lmi_only / total_unique * 100), 1) if total_unique > 0 else None
        mmct_only_pct = round((mmct_only / total_unique * 100), 1) if total_unique > 0 else None
        both_pct = round((both / total_unique * 100), 1) if total_unique > 0 else None
        
        county_data.append({
            'County': county,
            'Total Branches': total_unique,
            'LMI Only Branches': f"{lmi_only} ({_share_text(lmi_only_pct)})",
            'MMCT Only Branches': f"{mmct_only} ({_share_text(mmct_only_pct)})",
            'Both LMICT/MMCT Branches': f"{both} ({_share_text(both_pct)})",
            'Number of Banks': num_banks
        })
    
    result = pd.DataFrame(county_data)
    
    # Sort by Total Branches descending
    result = result.sort_values('Total Branches', ascending=False).reset_index(drop=True)
    
    return result


def create_trend_analysis(df: pd.DataFrame, years: List[int]) -> pd.DataFrame:
    """Create trend analysis across years."""
    if len(years) < 2:
        # Not enough years for trend analysis
        return pd.DataFrame()
    
    # Aggregate by year
    yearly_totals = df.groupby('year').agg({
        'total_branches': 'sum',
        'lmict': 'sum',
        'mmct': 'sum',
        'bank_name': 'nunique'
    }).reset_index()
    
    # Calculate year-over-year changes (guard against zero denominators producing Infinity)
    yearly_totals['Total Branches YoY %'] = yearly_totals['total_branches'].pct_change() * 100
    yearly_totals['LMI Branches YoY %'] = yearly_totals['lmict'].pct_change() * 100
    yearly_totals['Minority Branches YoY %'] = yearly_totals['mmct'].pct_change() * 100

    # Replace inf/-inf with 0 (occurs when previous year value is 0)
    yearly_totals = yearly_totals.replace([np.inf, -np.inf], 0)

    # Calculate percentages (guard against zero total_branches)
    yearly_totals['LMI %'] = np.where(
        yearly_totals['total_branches'] > 0,
        (yearly_totals['lmict'] / yearly_totals['total_branches'] * 100).round(1),
        0.0
    )
    yearly_totals['Minority %'] = np.where(
        yearly_totals['total_branches'] > 0,
        (yearly_totals['mmct'] / yearly_totals['total_branches'] * 100).round(1),
        0.0
    )
    
    # Rename columns
    yearly_totals.columns = ['Year', 'Total Branches', 'LMI Branches', 'Minority Branches', 'Number of Banks', 
                           'Total Branches YoY %', 'LMI Branches YoY %', 'Minority Branches YoY %', 'LMI %', 'Minority %']
    
    return yearly_totals.round(1)


def save_excel_report(report_data: Dict[str, pd.DataFrame], output_path: str, metadata: Dict[str, Any] = None, app_version: str = None):
    """
    Save the report data to an Excel file with multiple sheets.
    
    Args:
        report_data: Dictionary containing dataframes for different report sections
        output_path: Path where the Excel file should be saved
        metadata: Optional dictionary with report metadata (counties, years, etc.)
    """
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Create Excel writer
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        
        # Write report tables matching the report sections
        # Section 1: Yearly Breakdown
        if 'summary' in report_data and not report_data['summary'].empty:
            dash_missing(report_data['summary']).to_excel(writer, sheet_name=sanitize_sheet_name('Section 1: Yearly Breakdown'), index=False)
        
        # Section 2: Analysis by Bank. Branch counts are for the last year of
        # the run, which the sheet name states (Jay round 2 #11); the name
        # stays within Excel's 31 characters.
        if 'by_bank' in report_data and not report_data['by_bank'].empty:
            run_years = (metadata or {}).get('years') or []
            bank_year = max((str(y) for y in run_years), default='') if isinstance(run_years, (list, tuple)) else str(run_years)
            bank_sheet = f'Section 2: Banks ({bank_year})' if bank_year else 'Section 2: Analysis by Bank'
            bank_sheet = sanitize_sheet_name(bank_sheet)
            dash_missing(report_data['by_bank']).to_excel(writer, sheet_name=bank_sheet, index=False)
            if 'Acquired' in report_data['by_bank'].columns:
                # The one-line note under the table (T4).
                writer.sheets[bank_sheet].cell(row=len(report_data['by_bank']) + 3, column=1, value=BANK_CHANGE_NOTE)
        
        # Section 3: County by County Analysis (only if multiple counties)
        if 'by_county' in report_data and not report_data['by_county'].empty:
            # Check if multiple counties were selected
            multiple_counties = False
            if metadata and 'counties' in metadata:
                counties = metadata['counties']
                if isinstance(counties, list) and len(counties) > 1:
                    multiple_counties = True
            
            if multiple_counties:
                dash_missing(report_data['by_county']).to_excel(writer, sheet_name=sanitize_sheet_name('Section 3: County by County'), index=False)
        
        # Raw Data sheet
        if 'raw_data' in report_data and not report_data['raw_data'].empty:
            report_data['raw_data'].to_excel(writer, sheet_name=sanitize_sheet_name('Raw Data'), index=False)
        
        # Create Notes sheet with metadata
        workbook = writer.book
        notes_sheet = workbook.create_sheet(sanitize_sheet_name('Notes'), 0)  # Insert as first sheet
        
        # Prepare notes content
        notes_content = []
        
        # Report Information
        notes_content.append(('Report Information', ''))
        notes_content.append(('', ''))
        notes_content.append(('Report Generated:', analysis_stamp(metadata)))

        # Add application version
        if app_version:
            notes_content.append(('Application Version:', app_version))
        else:
            # Default to branchsight version if not specified
            from justdata.shared.utils.versions import get_version
            notes_content.append(('Application Version:', get_version('branchsight')))
        notes_content.append(('', ''))
        
        # Dates Analyzed
        notes_content.append(('Dates Analyzed', ''))
        notes_content.append(('', ''))
        if metadata and 'years' in metadata:
            years = metadata['years']
            if isinstance(years, list) and years:
                year_range = f"{min(years)} to {max(years)}"
                notes_content.append(('Year Range:', year_range))
                notes_content.append(('Years Included:', ', '.join(map(str, sorted(years)))))
            else:
                notes_content.append(('Year Range:', str(years)))
        else:
            notes_content.append(('Year Range:', 'Not specified'))
        notes_content.append(('', ''))
        
        # Locations Analyzed
        notes_content.append(('Locations Analyzed', ''))
        notes_content.append(('', ''))
        if metadata and 'counties' in metadata:
            counties = metadata['counties']
            if isinstance(counties, list):
                notes_content.append(('Counties:', ', '.join(counties)))
                notes_content.append(('Number of Counties:', len(counties)))
            else:
                notes_content.append(('Counties:', str(counties)))
        else:
            notes_content.append(('Counties:', 'Not specified'))
        notes_content.append(('', ''))
        
        # Data Filters
        notes_content.append(('Data Filters', ''))
        notes_content.append(('', ''))
        notes_content.append(('Branch Service Types:', 'All branch service types are included in the analysis'))
        notes_content.append(('Data Source:', 'FDIC Summary of Deposits (SOD) data'))
        notes_content.append(('Geographic Level:', 'County level (using geoid5: state FIPS + county FIPS)'))
        notes_content.append(('', ''))
        
        # Data Sources
        notes_content.append(('Data Sources', ''))
        notes_content.append(('', ''))
        notes_content.append(('Primary Source:', 'FDIC Summary of Deposits (SOD)'))
        notes_content.append(('Data Tables:', 'branchsight.sod, branchsight.sod_legacy (from NCRC datasets)'))
        notes_content.append(('Geographic Crosswalk:', 'shared.cbsa_to_county (for county-state mapping)'))
        notes_content.append(('Data Quality:', 'All data has been downloaded, cleaned, and tested by NCRC Research staff'))
        notes_content.append(('', ''))
        
        # Calculations and Methods
        notes_content.append(('Calculations and Methods', ''))
        notes_content.append(('', ''))
        notes_content.append(('Branch Deduplication:', 'Each branch (uninumbr) appears only once per year. LMI Only, MMCT Only, and Both LMICT/MMCT categories are mutually exclusive.'))
        notes_content.append(('Net Change Calculation:', 'Difference between the first year and final year of the analysis period. Positive values indicate growth, negative values indicate decline. In the bank table, banks are matched across years on their FDIC RSSD ID, not their name, and the latest year\'s name is shown.'))
        notes_content.append(('Acquired:', 'In the bank table, the number of a bank\'s latest-year branches that another institution held in the first year (same FDIC branch number, UNINUMBR). ' + BANK_CHANGE_NOTE))
        notes_content.append(('Transferred Out:', 'In the bank table, the number of a bank\'s first-year branches that another institution held in the latest year (same UNINUMBR).'))
        notes_content.append(('New to this County:', 'A bank with no branches in the first year and none acquired. Its branch count is not shown as a change.'))
        notes_content.append(('HHI (Herfindahl-Hirschman Index):', 'Calculated using deposit shares of all banks in the study area for the most recent year. HHI < 1,500 = Low concentration; HHI 1,500-2,500 = Moderate concentration; HHI > 2,500 = High concentration. Each bank is one FDIC RSSD ID, never a name; same-named banks show their headquarters city and state.'))
        notes_content.append(('LMI Classification:', 'Branches located in Low-to-Moderate Income (LMI) census tracts'))
        notes_content.append(('MMCT Classification:', 'Branches located in Majority-Minority Census Tracts (MMCT)'))
        notes_content.append(('Deposit Aggregation:', 'Total deposits are summed across all branches for each bank in each county/year'))
        notes_content.append(('', ''))
        
        # Important Notes
        notes_content.append(('Important Notes', ''))
        notes_content.append(('', ''))
        notes_content.append(('Census Boundary Changes:', 'The 2020 Census boundaries took effect in 2022. This resulted in a dramatic increase in the number of middle- and upper-income majority-minority census tracts nationally. Therefore, a dramatic increase in majority-minority branch locations is expected between 2021 and 2022.'))
        notes_content.append(('Bank Name Cleaning:', 'Variations of "National Association" are removed from bank names for consistency.'))
        notes_content.append(('Data Completeness:', 'All branch service types are included in the analysis. The Raw Data sheet contains all available fields for each branch record.'))
        notes_content.append(('', ''))
        
        # Record Count
        if metadata and 'total_records' in metadata:
            notes_content.append(('Data Summary', ''))
            notes_content.append(('', ''))
            notes_content.append(('Total Records:', metadata['total_records']))
            notes_content.append(('', ''))
        
        # Write notes to sheet
        for row_idx, (label, value) in enumerate(notes_content, start=1):
            notes_sheet.cell(row=row_idx, column=1, value=label)
            notes_sheet.cell(row=row_idx, column=2, value=value)
            
            # Style header rows (non-empty labels in first column)
            if label and value == '':
                notes_sheet.cell(row=row_idx, column=1).font = Font(bold=True, size=12)
                notes_sheet.cell(row=row_idx, column=1).fill = PatternFill(start_color='D3D3D3', end_color='D3D3D3', fill_type='solid')
        
        # Adjust column widths for Notes sheet
        notes_sheet.column_dimensions['A'].width = 35
        notes_sheet.column_dimensions['B'].width = 80
        
        # Auto-adjust column widths for all other sheets
        sanitized_notes_name = sanitize_sheet_name('Notes')
        for sheet_name in writer.sheets:
            if sheet_name != sanitized_notes_name:
                worksheet = writer.sheets[sheet_name]
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width


def generate_report_metadata(counties: List[str], years: List[int], record_count: int) -> Dict[str, Any]:
    """Generate metadata for the report."""
    return {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'counties': counties,
        'years': years,
        'total_records': record_count,
        'report_type': 'FDIC Bank Branch Analysis'
    }
