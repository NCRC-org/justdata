"""Market concentration (HHI) calculations for the mortgage report."""
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

def calculate_mortgage_hhi(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate Herfindahl-Hirschman Index (HHI) for mortgage loan amounts in the latest year.
    
    Similar to branch HHI but uses loan amounts instead of deposits.
    
    Returns:
        Dictionary with HHI value, concentration level, year, and top lenders by loan volume
    """
    if 'total_loan_amount' not in df.columns:
        return {
            'hhi': None,
            'concentration_level': 'Not Available',
            'year': None,
            'total_loan_amount': None,
            'top_lenders': []
        }
    
    # Find latest year
    latest_year = df['year'].max()
    latest_year_df = df[df['year'] == latest_year].copy()
    
    # Aggregate loan amounts by lender (across all counties)
    lender_loans = latest_year_df.groupby('lender_name')['total_loan_amount'].sum().reset_index()
    lender_loans = lender_loans[lender_loans['total_loan_amount'] > 0]  # Remove lenders with zero loans
    
    if lender_loans.empty:
        return {
            'hhi': None,
            'concentration_level': 'Not Available',
            'year': latest_year,
            'total_loan_amount': 0,
            'top_lenders': []
        }
    
    total_loan_amount = lender_loans['total_loan_amount'].sum()
    
    # Calculate market shares (as percentages)
    lender_loans['market_share'] = (lender_loans['total_loan_amount'] / total_loan_amount) * 100
    
    # Calculate HHI: sum of squared market shares (0-10,000 scale)
    hhi = (lender_loans['market_share'] ** 2).sum()
    
    # Determine concentration level
    if hhi < 1500:
        concentration_level = 'Low concentration (competitive market)'
    elif hhi < 2500:
        concentration_level = 'Moderate concentration'
    else:
        concentration_level = 'High concentration'
    
    # Get top lenders by loan amount
    top_lenders = lender_loans.nlargest(10, 'total_loan_amount').copy()
    top_lenders_list = []
    for _, row in top_lenders.iterrows():
        top_lenders_list.append({
            'lender_name': row['lender_name'],
            'total_loan_amount': float(row['total_loan_amount']),
            'market_share': float(row['market_share'])
        })
    
    return {
        'hhi': float(hhi),
        'concentration_level': concentration_level,
        'year': int(latest_year),
        'total_loan_amount': float(total_loan_amount),
        'total_lenders': len(lender_loans),
        'top_lenders': top_lenders_list
    }


def create_market_concentration_table(df: pd.DataFrame, years: List[int], metadata: Dict = None) -> List[Dict[str, Any]]:
    """
    Create market concentration table showing HHI (Herfindahl-Hirschman Index) by year and loan purpose.
    
    This function calculates HHI for:
    - All Loans (combined)
    - Home purchase loans (loan_purpose = '1')
    - Refinance loans (loan_purpose IN ('31', '32'))
    - Home equity loans (loan_purpose IN ('2', '4'))
    
    Args:
        df: DataFrame with mortgage data (must have 'year', 'lender_name', 'total_loan_amount', 'loan_purpose')
        years: List of years to calculate HHI for
        metadata: Optional metadata dict
    
    Returns:
        List of dictionaries with HHI data by year and loan purpose category
    """
    # Define loan purpose filters
    loan_purpose_filters = {
        'All Loans': None,  # No filter, use all data
        'Home Purchase': ['1'],
        'Refinance': ['31', '32'],
        'Home Equity': ['2', '4']
    }
    
    hhi_results = []
    
    # Check if loan_purpose column exists
    has_loan_purpose = 'loan_purpose' in df.columns
    
    for purpose_label, purpose_codes in loan_purpose_filters.items():
        purpose_hhi_data = {'Loan Purpose': purpose_label}
        
        # Filter DataFrame by loan purpose if codes are specified
        if purpose_codes is None:
            # All Loans - use full DataFrame
            filtered_df = df.copy()
        elif has_loan_purpose:
            # Filter by loan purpose codes
            filtered_df = df[df['loan_purpose'].isin(purpose_codes)].copy()
        else:
            # loan_purpose column not available - can only calculate for All Loans
            if purpose_label == 'All Loans':
                filtered_df = df.copy()
            else:
                # Cannot calculate for specific loan purposes without loan_purpose column
                # Fill with None for all years
                for year in sorted(years):
                    purpose_hhi_data[year] = None
                hhi_results.append(purpose_hhi_data)
                continue
        
        # Calculate HHI for each year
        for year in sorted(years):
            year_df = filtered_df[filtered_df['year'] == year].copy()
            hhi_value = calculate_mortgage_hhi_for_year(year_df, year)
            purpose_hhi_data[year] = hhi_value['hhi'] if hhi_value['hhi'] is not None else None
        
        hhi_results.append(purpose_hhi_data)
    
    return hhi_results


def calculate_mortgage_hhi_for_year(df: pd.DataFrame, year: int) -> Dict[str, Any]:
    """
    Calculate Herfindahl-Hirschman Index (HHI) for mortgage loan amounts for a specific year.
    
    Args:
        df: DataFrame with mortgage data for the year (must have 'lender_name', 'total_loan_amount')
        year: Year being calculated (for metadata)
    
    Returns:
        Dictionary with HHI value, concentration level, year, and metadata
    """
    if 'total_loan_amount' not in df.columns or 'lender_name' not in df.columns:
        return {
            'hhi': None,
            'concentration_level': 'Not Available',
            'year': year,
            'total_loan_amount': None,
            'top_lenders': []
        }
    
    # Aggregate loan amounts by lender (across all counties)
    lender_loans = df.groupby('lender_name')['total_loan_amount'].sum().reset_index()
    lender_loans = lender_loans[lender_loans['total_loan_amount'] > 0]  # Remove lenders with zero loans
    
    if lender_loans.empty:
        return {
            'hhi': None,
            'concentration_level': 'Not Available',
            'year': year,
            'total_loan_amount': 0,
            'top_lenders': []
        }
    
    total_loan_amount = lender_loans['total_loan_amount'].sum()
    
    # Calculate market shares (as percentages)
    lender_loans['market_share'] = (lender_loans['total_loan_amount'] / total_loan_amount) * 100
    
    # Calculate HHI: sum of squared market shares (0-10,000 scale)
    hhi = (lender_loans['market_share'] ** 2).sum()
    
    # Determine concentration level
    if hhi < 1500:
        concentration_level = 'Low concentration (competitive market)'
    elif hhi < 2500:
        concentration_level = 'Moderate concentration'
    else:
        concentration_level = 'High concentration'
    
    return {
        'hhi': float(hhi),
        'concentration_level': concentration_level,
        'year': int(year),
        'total_loan_amount': float(total_loan_amount),
        'total_lenders': len(lender_loans)
    }


