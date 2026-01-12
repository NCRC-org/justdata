#!/usr/bin/env python3
"""
Area Analysis Processor for DataExplorer 2.0
Processes area-based queries for HMDA, Small Business, and Branch data.
"""

from typing import Dict, List, Any, Optional
import pandas as pd
from apps.dataexplorer.data_utils import (
    execute_hmda_query, execute_sb_query, execute_branch_query
)
from apps.dataexplorer.config import (
    HMDA_YEARS, SB_YEARS, BRANCH_YEARS
)
import logging

logger = logging.getLogger(__name__)


def process_hmda_area_analysis(
    geoids: List[str],
    years: List[int],
    filters: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Process HMDA area analysis.
    
    Args:
        geoids: List of GEOIDs
        years: List of years
        filters: Optional filters (action_taken, loan_purpose, etc.)
        
    Returns:
        Dictionary with analysis results
    """
    try:
        filters = filters or {}
        
        # Execute query
        results = execute_hmda_query(
            geoids=geoids,
            years=years,
            action_taken=filters.get('action_taken'),
            loan_purpose=filters.get('loan_purpose'),
            occupancy=filters.get('occupancy'),
            property_type=filters.get('property_type'),
            exclude_reverse_mortgages=filters.get('exclude_reverse_mortgages', True),
            min_loan_amount=filters.get('min_loan_amount'),
            max_loan_amount=filters.get('max_loan_amount')
        )
        
        if not results:
            return {
                'summary': {
                    'total_loans': 0,
                    'total_volume': 0,
                    'average_loan_amount': 0
                },
                'by_year': [],
                'by_lender': [],
                'demographics': {},
                'trends': []
            }
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame(results)
        
        # Summary statistics
        total_loans = len(df)
        total_volume = df['loan_amount'].sum() if 'loan_amount' in df.columns else 0
        average_loan_amount = total_volume / total_loans if total_loans > 0 else 0
        
        # By year
        by_year = []
        if 'year' in df.columns:
            year_stats = df.groupby('year').agg({
                'loan_amount': ['count', 'sum', 'mean']
            }).reset_index()
            year_stats.columns = ['year', 'loan_count', 'total_volume', 'avg_loan_amount']
            by_year = year_stats.to_dict('records')
        
        # By lender
        by_lender = []
        if 'lender_id' in df.columns and 'lender_name' in df.columns:
            lender_stats = df.groupby(['lender_id', 'lender_name']).agg({
                'loan_amount': ['count', 'sum', 'mean']
            }).reset_index()
            lender_stats.columns = ['lender_id', 'lender_name', 'loan_count', 'total_volume', 'avg_loan_amount']
            lender_stats = lender_stats.sort_values('total_volume', ascending=False).head(20)
            by_lender = lender_stats.to_dict('records')
        
        # Demographics (if available)
        demographics = {}
        if 'applicant_race_1' in df.columns:
            race_counts = df['applicant_race_1'].value_counts().to_dict()
            demographics['race'] = race_counts
        
        if 'applicant_ethnicity_1' in df.columns:
            ethnicity_counts = df['applicant_ethnicity_1'].value_counts().to_dict()
            demographics['ethnicity'] = ethnicity_counts
        
        # Trends
        trends = []
        if 'year' in df.columns:
            for year in sorted(df['year'].unique()):
                year_df = df[df['year'] == year]
                trends.append({
                    'year': int(year),
                    'loan_count': len(year_df),
                    'total_volume': year_df['loan_amount'].sum() if 'loan_amount' in year_df.columns else 0
                })
        
        return {
            'summary': {
                'total_loans': int(total_loans),
                'total_volume': float(total_volume),
                'average_loan_amount': float(average_loan_amount)
            },
            'by_year': by_year,
            'by_lender': by_lender,
            'demographics': demographics,
            'trends': trends,
            'raw_data': results[:1000]  # Limit raw data for response size
        }
        
    except Exception as e:
        logger.error(f"Error processing HMDA area analysis: {e}")
        raise Exception(f"Error processing HMDA area analysis: {str(e)}")


def process_sb_area_analysis(
    geoids: List[str],
    years: List[int],
    filters: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Process Small Business area analysis.
    
    Args:
        geoids: List of GEOIDs
        years: List of years
        filters: Optional filters
        
    Returns:
        Dictionary with analysis results
    """
    try:
        filters = filters or {}
        
        # Execute query
        results = execute_sb_query(
            geoids=geoids,
            years=years,
            min_loan_amount=filters.get('min_loan_amount'),
            max_loan_amount=filters.get('max_loan_amount')
        )
        
        if not results:
            return {
                'summary': {
                    'total_loans': 0,
                    'total_borrowers': 0,
                    'total_volume': 0
                },
                'by_year': [],
                'by_lender': [],
                'trends': []
            }
        
        # Convert to DataFrame
        df = pd.DataFrame(results)
        
        # Summary statistics
        total_loans = df['number_of_loans'].sum() if 'number_of_loans' in df.columns else len(df)
        total_borrowers = df['number_of_borrowers'].sum() if 'number_of_borrowers' in df.columns else 0
        total_volume = df['loan_amount'].sum() if 'loan_amount' in df.columns else 0
        
        # By year
        by_year = []
        if 'year' in df.columns:
            year_stats = df.groupby('year').agg({
                'loan_amount': 'sum',
                'number_of_loans': 'sum',
                'number_of_borrowers': 'sum'
            }).reset_index()
            by_year = year_stats.to_dict('records')
        
        # By lender
        by_lender = []
        if 'lender_id' in df.columns and 'lender_name' in df.columns:
            lender_stats = df.groupby(['lender_id', 'lender_name']).agg({
                'loan_amount': 'sum',
                'number_of_loans': 'sum'
            }).reset_index()
            lender_stats = lender_stats.sort_values('loan_amount', ascending=False).head(20)
            by_lender = lender_stats.to_dict('records')
        
        # Trends
        trends = []
        if 'year' in df.columns:
            for year in sorted(df['year'].unique()):
                year_df = df[df['year'] == year]
                trends.append({
                    'year': int(year),
                    'loan_count': int(year_df['number_of_loans'].sum()) if 'number_of_loans' in year_df.columns else len(year_df),
                    'total_volume': float(year_df['loan_amount'].sum()) if 'loan_amount' in year_df.columns else 0
                })
        
        return {
            'summary': {
                'total_loans': int(total_loans),
                'total_borrowers': int(total_borrowers),
                'total_volume': float(total_volume)
            },
            'by_year': by_year,
            'by_lender': by_lender,
            'trends': trends,
            'raw_data': results[:1000]
        }
        
    except Exception as e:
        logger.error(f"Error processing SB area analysis: {e}")
        raise Exception(f"Error processing SB area analysis: {str(e)}")


def process_branch_area_analysis(
    geoids: List[str] = None,
    years: List[int] = None,
    filters: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Process Branch area analysis.
    
    Args:
        geoids: Optional list of GEOIDs
        years: Optional list of years
        filters: Optional filters
        
    Returns:
        Dictionary with analysis results
    """
    try:
        filters = filters or {}
        
        # Execute query
        results = execute_branch_query(
            geoids=geoids,
            years=years,
            lender_id=filters.get('lender_id'),
            state=filters.get('state'),
            county=filters.get('county')
        )
        
        if not results:
            return {
                'summary': {
                    'total_branches': 0,
                    'total_deposits': 0
                },
                'by_year': [],
                'by_lender': [],
                'by_county': [],
                'trends': []
            }
        
        # Convert to DataFrame
        df = pd.DataFrame(results)
        
        # Summary statistics
        total_branches = len(df)
        total_deposits = df['deposits'].sum() if 'deposits' in df.columns else 0
        
        # By year
        by_year = []
        if 'year' in df.columns:
            year_stats = df.groupby('year').agg({
                'deposits': ['count', 'sum']
            }).reset_index()
            year_stats.columns = ['year', 'branch_count', 'total_deposits']
            by_year = year_stats.to_dict('records')
        
        # By lender
        by_lender = []
        if 'lender_id' in df.columns:
            lender_stats = df.groupby('lender_id').agg({
                'deposits': ['count', 'sum']
            }).reset_index()
            lender_stats.columns = ['lender_id', 'branch_count', 'total_deposits']
            lender_stats = lender_stats.sort_values('total_deposits', ascending=False).head(20)
            by_lender = lender_stats.to_dict('records')
        
        # By county
        by_county = []
        if 'geoid' in df.columns and 'county_name' in df.columns:
            county_stats = df.groupby(['geoid', 'county_name']).agg({
                'deposits': ['count', 'sum']
            }).reset_index()
            county_stats.columns = ['geoid', 'county_name', 'branch_count', 'total_deposits']
            county_stats = county_stats.sort_values('total_deposits', ascending=False)
            by_county = county_stats.to_dict('records')
        
        # Trends
        trends = []
        if 'year' in df.columns:
            for year in sorted(df['year'].unique()):
                year_df = df[df['year'] == year]
                trends.append({
                    'year': int(year),
                    'branch_count': len(year_df),
                    'total_deposits': float(year_df['deposits'].sum()) if 'deposits' in year_df.columns else 0
                })
        
        return {
            'summary': {
                'total_branches': int(total_branches),
                'total_deposits': float(total_deposits)
            },
            'by_year': by_year,
            'by_lender': by_lender,
            'by_county': by_county,
            'trends': trends,
            'raw_data': results[:1000]
        }
        
    except Exception as e:
        logger.error(f"Error processing Branch area analysis: {e}")
        raise Exception(f"Error processing Branch area analysis: {str(e)}")
