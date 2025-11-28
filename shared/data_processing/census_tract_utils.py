#!/usr/bin/env python3
"""
Shared utilities for census tract data processing.
Used across HMDA, Small Business, and Branch reports to ensure consistency.
"""

from typing import Dict, Any, List, Optional

def get_census_tract_join_clause(project_id: str, geo_dataset: str = 'geo', geo_census_table: str = 'census') -> str:
    """
    Generate the standard LEFT JOIN clause for census tract data.
    
    Args:
        project_id: BigQuery project ID
        geo_dataset: Dataset name for geo tables (default: 'geo')
        geo_census_table: Census table name (default: 'census')
    
    Returns:
        SQL JOIN clause string
    """
    return f"""
    LEFT JOIN `{project_id}.{geo_dataset}.{geo_census_table}` c
        ON LPAD(CAST(b.geoid5 AS STRING), 5, '0') = SUBSTR(LPAD(CAST(c.geoid AS STRING), 11, '0'), 1, 5)
        AND LPAD(CAST(b.census_tract AS STRING), 6, '0') = SUBSTR(LPAD(CAST(c.geoid AS STRING), 11, '0'), 6, 6)
    """


def get_income_tract_flags() -> str:
    """
    Generate SQL CASE statements for income tract categorization.
    Uses income_level from geo.census table (1=low, 2=moderate, 3=middle, 4=upper).
    
    Returns:
        SQL SELECT clause fragment with income tract flags
    """
    return """
        -- Income tract flags
        COALESCE(CAST(b.br_lmi AS INT64), 
            CASE WHEN c.income_level IN (1, 2) THEN 1 ELSE 0 END, 0) as is_lmi_tract,
        CASE WHEN c.income_level = 1 THEN 1 ELSE 0 END as is_low_income_tract,
        CASE WHEN c.income_level = 2 THEN 1 ELSE 0 END as is_moderate_income_tract,
        CASE WHEN c.income_level = 3 THEN 1 ELSE 0 END as is_middle_income_tract,
        CASE WHEN c.income_level = 4 THEN 1 ELSE 0 END as is_upper_income_tract,
    """


def get_mmct_flag() -> str:
    """
    Generate SQL CASE statement for MMCT (Majority-Minority Census Tract) flag.
    
    Returns:
        SQL SELECT clause fragment with MMCT flag
    """
    return """
        -- MMCT flag
        COALESCE(CAST(b.cr_minority AS INT64),
            CASE WHEN SAFE_DIVIDE(
                COALESCE(c.total_persons, 0) - COALESCE(c.total_white, 0),
                NULLIF(COALESCE(c.total_persons, 0), 0)
            ) * 100 > 50 THEN 1 ELSE 0 END, 0) as is_mmct_tract,
    """


def get_minority_percentage() -> str:
    """
    Generate SQL expression for minority population percentage.
    
    Returns:
        SQL SELECT clause fragment with minority percentage
    """
    return """
        -- Minority population percentage for breakdowns
        SAFE_DIVIDE(
            COALESCE(c.total_persons, 0) - COALESCE(c.total_white, 0),
            NULLIF(COALESCE(c.total_persons, 0), 0)
        ) * 100 as tract_minority_population_percent
    """


def get_census_tract_fields(project_id: str, geo_dataset: str = 'geo', geo_census_table: str = 'census') -> str:
    """
    Get all census tract-related fields for a query.
    Combines income flags, MMCT flag, and minority percentage.
    
    Args:
        project_id: BigQuery project ID
        geo_dataset: Dataset name for geo tables (default: 'geo')
        geo_census_table: Census table name (default: 'census')
    
    Returns:
        Complete SQL SELECT clause fragment with all census tract fields
    """
    return get_income_tract_flags() + get_mmct_flag() + get_minority_percentage()


def calculate_minority_breakdowns(raw_data: List[Dict[str, Any]], years: List[int]) -> Dict[str, Dict[str, float]]:
    """
    Calculate minority tract breakdowns using mean/stddev method (same as HMDA).
    
    Args:
        raw_data: List of row dictionaries with tract_minority_population_percent
        years: List of years to process
    
    Returns:
        Dictionary with structure: {year_str: {'mean': float, 'stddev': float}}
    """
    from collections import defaultdict
    import statistics
    
    minority_percentages_by_year = defaultdict(list)
    
    # Collect all minority percentages by year
    for row in raw_data:
        year = str(row.get('year', ''))
        if year and year in [str(y) for y in years]:
            minority_pct = row.get('tract_minority_population_percent')
            if minority_pct is not None:
                try:
                    minority_percentages_by_year[year].append(float(minority_pct))
                except (ValueError, TypeError):
                    pass
    
    # Calculate mean and stddev for each year
    minority_stats_by_year = {}
    for year in years:
        year_str = str(year)
        percentages = minority_percentages_by_year.get(year_str, [])
        if percentages:
            mean = statistics.mean(percentages)
            stddev = statistics.stdev(percentages) if len(percentages) > 1 else 0
            minority_stats_by_year[year_str] = {'mean': mean, 'stddev': stddev}
        else:
            minority_stats_by_year[year_str] = {'mean': 0, 'stddev': 0}
    
    return minority_stats_by_year


def categorize_minority_tract(minority_pct: Optional[float], mean: float, stddev: float) -> str:
    """
    Categorize a tract's minority percentage into low/moderate/middle/high.
    
    Args:
        minority_pct: Minority population percentage (0-100)
        mean: Mean minority percentage for the geography
        stddev: Standard deviation of minority percentage
    
    Returns:
        Category: 'low', 'moderate', 'middle', or 'high'
    """
    if minority_pct is None or stddev == 0:
        return 'low'  # Default if no data
    
    if minority_pct < (mean - stddev):
        return 'low'
    elif minority_pct < mean:
        return 'moderate'
    elif minority_pct < (mean + stddev):
        return 'middle'
    else:
        return 'high'

