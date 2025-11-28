#!/usr/bin/env python3
"""
MMCT (Majority-Minority Census Tract) breakdown utilities.
Calculates minority tract categories using standard deviation method (like BizSight).
"""

from typing import Dict, List, Any
from collections import defaultdict
import math
from .data_utils import execute_query
from .config import DataExplorerConfig


def calculate_mmct_breakdowns_from_query(geoids: List[str], years: List[int], 
                                        loan_purpose: List[str] = None,
                                        action_taken: List[str] = None) -> Dict[str, Dict[str, Any]]:
    """
    Calculate MMCT breakdowns using a separate query to get tract-level data.
    
    Method (from BizSight):
    - Calculate mean and standard deviation of minority population % across all tracts in geography
    - Low: < (mean - stddev)
    - Moderate: (mean - stddev) to mean
    - Middle: mean to (mean + stddev)
    - Upper: > (mean + stddev)
    
    Args:
        geoids: List of GEOID5 codes
        years: List of years
        loan_purpose: Optional loan purpose filter
        action_taken: Optional action taken filter
    
    Returns:
        Dictionary with MMCT breakdown metrics by year
    """
    from .demographic_queries import build_hmda_demographic_query
    from .data_utils import execute_query
    from .config import DataExplorerConfig
    
    # Build query to get tract-level data (not aggregated by lender)
    project_id = DataExplorerConfig.GCP_PROJECT_ID
    
    # Build WHERE clause
    where_conditions = []
    geoid_list = "', '".join([str(g).zfill(5) for g in geoids])
    where_conditions.append(f"LPAD(CAST(h.county_code AS STRING), 5, '0') IN ('{geoid_list}')")
    
    year_list = "', '".join([str(y) for y in years])
    where_conditions.append(f"CAST(h.activity_year AS STRING) IN ('{year_list}')")
    
    if loan_purpose:
        purpose_list = "', '".join(loan_purpose)
        where_conditions.append(f"h.loan_purpose IN ('{purpose_list}')")
    
    if action_taken:
        action_list = "', '".join(action_taken)
        where_conditions.append(f"h.action_taken IN ('{action_list}')")
    
    where_clause = " AND ".join(where_conditions)
    
    # Query to get unique tracts with their minority percentages and loan counts
    query = f"""
    WITH tract_data AS (
        SELECT 
            CAST(h.activity_year AS STRING) as activity_year,
            h.census_tract,
            CAST(h.tract_minority_population_percent AS FLOAT64) as tract_minority_pct,
            COUNT(*) as loan_count
        FROM `{project_id}.{DataExplorerConfig.HMDA_DATASET}.{DataExplorerConfig.HMDA_TABLE}` h
        WHERE {where_clause}
          AND h.census_tract IS NOT NULL
          AND h.tract_minority_population_percent IS NOT NULL
        GROUP BY activity_year, census_tract, tract_minority_pct
    ),
    tract_stats AS (
        SELECT 
            activity_year,
            AVG(tract_minority_pct) as mean_minority,
            STDDEV(tract_minority_pct) as stddev_minority
        FROM tract_data
        GROUP BY activity_year
    )
    SELECT 
        t.activity_year,
        t.census_tract,
        t.tract_minority_pct,
        t.loan_count,
        s.mean_minority,
        s.stddev_minority,
        CASE 
            WHEN t.tract_minority_pct < (s.mean_minority - s.stddev_minority) THEN 'low'
            WHEN t.tract_minority_pct < s.mean_minority THEN 'moderate'
            WHEN t.tract_minority_pct < (s.mean_minority + s.stddev_minority) THEN 'middle'
            ELSE 'upper'
        END as minority_category
    FROM tract_data t
    JOIN tract_stats s ON t.activity_year = s.activity_year
    """
    
    try:
        results = execute_query(query)
        
        # Aggregate by year and category
        result = {}
        for year in years:
            year_str = str(year)
            category_counts = defaultdict(int)
            total_loans = 0
            
            for row in results:
                if str(row.get('activity_year', '')) == year_str:
                    category = row.get('minority_category', 'unknown')
                    loan_count = int(row.get('loan_count', 0))
                    category_counts[category] += loan_count
                    total_loans += loan_count
            
            # Get mean and stddev from first row for this year (they're the same for all rows in a year)
            mean_minority = None
            stddev_minority = None
            for row in results:
                if str(row.get('activity_year', '')) == year_str:
                    mean_minority = float(row.get('mean_minority', 0)) if row.get('mean_minority') else 0
                    stddev_minority = float(row.get('stddev_minority', 0)) if row.get('stddev_minority') else 0
                    break
            
            result[year_str] = {
                'mmct_low': {
                    'count': category_counts['low'],
                    'percent': round((category_counts['low'] / total_loans * 100) if total_loans > 0 else 0, 2)
                },
                'mmct_moderate': {
                    'count': category_counts['moderate'],
                    'percent': round((category_counts['moderate'] / total_loans * 100) if total_loans > 0 else 0, 2)
                },
                'mmct_middle': {
                    'count': category_counts['middle'],
                    'percent': round((category_counts['middle'] / total_loans * 100) if total_loans > 0 else 0, 2)
                },
                'mmct_upper': {
                    'count': category_counts['upper'],
                    'percent': round((category_counts['upper'] / total_loans * 100) if total_loans > 0 else 0, 2)
                },
                'mean_minority': mean_minority,
                'stddev_minority': stddev_minority
            }
        
        return result
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Could not calculate MMCT breakdowns: {e}")
        # Return empty structure
        result = {}
        for year in years:
            result[str(year)] = {
                'mmct_low': {'count': 0, 'percent': 0},
                'mmct_moderate': {'count': 0, 'percent': 0},
                'mmct_middle': {'count': 0, 'percent': 0},
                'mmct_upper': {'count': 0, 'percent': 0}
            }
        return result


def get_average_minority_percentage(geoids: List[str], years: List[int]) -> float:
    """
    Get average minority population percentage for the geography.
    This is used as a benchmark in the Income & Neighborhood Indicators table caption.
    """
    project_id = DataExplorerConfig.GCP_PROJECT_ID
    geoid_list = "', '".join([str(g).zfill(5) for g in geoids])
    year_list = "', '".join([str(y) for y in years])
    
    query = f"""
    SELECT 
        AVG(CAST(tract_minority_population_percent AS FLOAT64)) as avg_minority_pct
    FROM `{project_id}.{DataExplorerConfig.HMDA_DATASET}.{DataExplorerConfig.HMDA_TABLE}` h
    WHERE LPAD(CAST(h.county_code AS STRING), 5, '0') IN ('{geoid_list}')
      AND CAST(h.activity_year AS STRING) IN ('{year_list}')
      AND h.tract_minority_population_percent IS NOT NULL
    """
    
    try:
        results = execute_query(query)
        if results and len(results) > 0:
            avg_pct = results[0].get('avg_minority_pct', 0)
            return round(float(avg_pct), 1) if avg_pct else 0.0
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Could not get average minority percentage: {e}")
    
    return 0.0


def calculate_sb_mmct_breakdowns_from_query(geoids: List[str], years: List[int]) -> Dict[str, Dict[str, Any]]:
    """
    Calculate MMCT breakdowns for Small Business data using aggregate table.
    
    Method (same as mortgage):
    - Calculate mean and standard deviation of minority population % across all tracts in geography
    - Low: < (mean - stddev)
    - Moderate: (mean - stddev) to mean
    - Middle: mean to (mean + stddev)
    - Upper: > (mean + stddev)
    
    Args:
        geoids: List of GEOID5 codes
        years: List of years
    
    Returns:
        Dictionary with MMCT breakdown metrics by year
    """
    project_id = DataExplorerConfig.GCP_PROJECT_ID
    
    # Build WHERE clause
    geoid_list = "', '".join([str(g).zfill(5) for g in geoids])
    year_list = "', '".join([str(y) for y in years])
    
    # Query to get unique tracts with their minority percentages and loan counts from aggregate table
    # Note: geoid10 should be 11 characters (state + county + tract), matching census.geoid format
    query = f"""
    WITH tract_data AS (
        SELECT 
            CAST(a.year AS STRING) as activity_year,
            LPAD(CAST(a.geoid10 AS STRING), 11, '0') as census_tract,
            -- Calculate minority population percent from census table (should be same for all rows with same geoid10)
            MAX(SAFE_DIVIDE(
                COALESCE(c.total_persons, 0) - COALESCE(c.total_white, 0),
                NULLIF(COALESCE(c.total_persons, 0), 0)
            ) * 100) as tract_minority_pct,
            -- Sum loan counts from aggregate table (aggregate by tract and year)
            SUM(COALESCE(a.num_under_100k, 0) + COALESCE(a.num_100k_250k, 0) + COALESCE(a.num_250k_1m, 0)) as loan_count
        FROM `{project_id}.{DataExplorerConfig.SB_DATASET}.{DataExplorerConfig.SB_AGGREGATE_TABLE}` a
        LEFT JOIN `{project_id}.{DataExplorerConfig.GEO_DATASET}.{DataExplorerConfig.GEO_CENSUS_TABLE}` c
            ON LPAD(CAST(a.geoid10 AS STRING), 11, '0') = LPAD(CAST(c.geoid AS STRING), 11, '0')
        WHERE LPAD(CAST(a.geoid5 AS STRING), 5, '0') IN ('{geoid_list}')
          AND CAST(a.year AS STRING) IN ('{year_list}')
          AND a.geoid10 IS NOT NULL
          AND LPAD(CAST(a.geoid10 AS STRING), 11, '0') IS NOT NULL
        GROUP BY activity_year, census_tract
    ),
    tract_stats AS (
        SELECT 
            activity_year,
            AVG(tract_minority_pct) as mean_minority,
            STDDEV(tract_minority_pct) as stddev_minority
        FROM tract_data
        WHERE tract_minority_pct IS NOT NULL
        GROUP BY activity_year
    )
    SELECT 
        t.activity_year,
        t.census_tract,
        t.tract_minority_pct,
        t.loan_count,
        s.mean_minority,
        s.stddev_minority,
        CASE 
            WHEN t.tract_minority_pct < (s.mean_minority - s.stddev_minority) THEN 'low'
            WHEN t.tract_minority_pct < s.mean_minority THEN 'moderate'
            WHEN t.tract_minority_pct < (s.mean_minority + s.stddev_minority) THEN 'middle'
            ELSE 'upper'
        END as minority_category
    FROM tract_data t
    LEFT JOIN tract_stats s ON t.activity_year = s.activity_year
    WHERE t.tract_minority_pct IS NOT NULL
       AND s.mean_minority IS NOT NULL
       AND s.stddev_minority IS NOT NULL
    """
    
    try:
        results = execute_query(query)
        
        # Log query results for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[MMCT SB] Query returned {len(results) if results else 0} rows")
        
        # Check if we got any results with valid minority percentages
        if results:
            rows_with_minority_pct = [r for r in results if r.get('tract_minority_pct') is not None]
            logger.info(f"[MMCT SB] Rows with valid minority percentage: {len(rows_with_minority_pct)} out of {len(results)}")
            if len(rows_with_minority_pct) == 0:
                logger.warning(f"[MMCT SB] No rows with valid minority percentage - check geoid10 join with census table")
                # Log sample geoid10 values to debug
                sample_geoids = [r.get('census_tract') for r in results[:5] if r.get('census_tract')]
                logger.info(f"[MMCT SB] Sample geoid10 values from aggregate table: {sample_geoids}")
        
        # Aggregate by year and category
        result = {}
        for year in years:
            year_str = str(year)
            category_counts = defaultdict(int)
            total_loans = 0
            mmct_loans = 0  # Loans in tracts with >=50% minority
            
            if results:
                for row in results:
                    if str(row.get('activity_year', '')) == year_str:
                        category = row.get('minority_category', 'unknown')
                        loan_count = int(row.get('loan_count', 0))
                        tract_minority_pct = float(row.get('tract_minority_pct', 0)) if row.get('tract_minority_pct') else 0
                        
                        category_counts[category] += loan_count
                        total_loans += loan_count
                        
                        # MMCT: tracts where minority % >= 50%
                        if tract_minority_pct >= 50:
                            mmct_loans += loan_count
            
            logger.info(f"[MMCT SB] Year {year_str}: total_loans={total_loans}, mmct_loans={mmct_loans}, categories={dict(category_counts)}")
            
            # Get mean and stddev from first row for this year (they're the same for all rows in a year)
            mean_minority = None
            stddev_minority = None
            for row in results:
                if str(row.get('activity_year', '')) == year_str:
                    mean_minority = float(row.get('mean_minority', 0)) if row.get('mean_minority') else 0
                    stddev_minority = float(row.get('stddev_minority', 0)) if row.get('stddev_minority') else 0
                    break
            
            result[year_str] = {
                'mmct_percentage': {
                    'count': mmct_loans,
                    'percent': round((mmct_loans / total_loans * 100) if total_loans > 0 else 0, 2)
                },
                'mmct_low': {
                    'count': category_counts['low'],
                    'percent': round((category_counts['low'] / total_loans * 100) if total_loans > 0 else 0, 2)
                },
                'mmct_moderate': {
                    'count': category_counts['moderate'],
                    'percent': round((category_counts['moderate'] / total_loans * 100) if total_loans > 0 else 0, 2)
                },
                'mmct_middle': {
                    'count': category_counts['middle'],
                    'percent': round((category_counts['middle'] / total_loans * 100) if total_loans > 0 else 0, 2)
                },
                'mmct_upper': {
                    'count': category_counts['upper'],
                    'percent': round((category_counts['upper'] / total_loans * 100) if total_loans > 0 else 0, 2)
                },
                'mean_minority': mean_minority,
                'stddev_minority': stddev_minority
            }
            logger.info(f"[MMCT SB] Year {year_str} breakdowns - Low: {result[year_str]['mmct_low']['percent']}%, Moderate: {result[year_str]['mmct_moderate']['percent']}%, Middle: {result[year_str]['mmct_middle']['percent']}%, High: {result[year_str]['mmct_upper']['percent']}%, MMCT: {result[year_str]['mmct_percentage']['percent']}%")
        
        return result
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Could not calculate SB MMCT breakdowns: {e}")
        # Return empty structure
        result = {}
        for year in years:
            result[str(year)] = {
                'mmct_percentage': {'count': 0, 'percent': 0},
                'mmct_low': {'count': 0, 'percent': 0},
                'mmct_moderate': {'count': 0, 'percent': 0},
                'mmct_middle': {'count': 0, 'percent': 0},
                'mmct_upper': {'count': 0, 'percent': 0}
            }
        return result

