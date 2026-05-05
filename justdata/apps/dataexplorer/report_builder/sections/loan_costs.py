"""Loan costs section table (area + lender variants)."""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def create_loan_costs_table(df: pd.DataFrame, years: List[int]) -> pd.DataFrame:
    """
    Create Section 2 Loan Costs table with years as columns.
    
    Metrics:
    - Property Value (average)
    - Loan Amount (average)
    - Downpayment/Equity (average: property_value - loan_amount)
    - Interest Rate (average)
    - Closing Costs (average: total_loan_costs)
    - Origination Fees (average: origination_charges)
    
    Args:
        df: DataFrame with loan data
        years: List of years to include
        
    Returns:
        DataFrame with Metric column and year columns + Change column
    """
    if df.empty:
        return pd.DataFrame()
    
    # Required columns
    required_cols = ['year', 'avg_property_value', 'avg_loan_amount', 'avg_interest_rate', 
                     'avg_total_loan_costs', 'avg_origination_charges']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        logger.warning(f"[DEBUG] Missing columns for loan costs table: {missing_cols}")
        return pd.DataFrame()
    
    # Filter to specified years
    df_years = df[df['year'].isin(years)].copy()
    if df_years.empty:
        return pd.DataFrame()
    
    # Identify exempt lenders (those with <1,000 total loans across all years)
    # Exempt lenders are not required to report property_value, total_loan_costs, origination_charges
    # We'll exclude their $0 values from calculations, but keep legitimate $0 values from non-exempt lenders
    exempt_lenders = set()
    if 'lei' in df_years.columns and 'total_originations' in df_years.columns:
        # Calculate total loans per lender across all years
        lender_totals = df_years.groupby('lei')['total_originations'].sum()
        # Lenders with <1,000 total loans are exempt
        exempt_lenders = set(lender_totals[lender_totals < 1000].index)
        logger.info(f"[DEBUG] Identified {len(exempt_lenders)} exempt lenders (total loans < 1,000)")
    elif 'lender_name' in df_years.columns and 'total_originations' in df_years.columns:
        # Fallback to lender_name if lei not available
        lender_totals = df_years.groupby('lender_name')['total_originations'].sum()
        exempt_lenders = set(lender_totals[lender_totals < 1000].index)
        logger.info(f"[DEBUG] Identified {len(exempt_lenders)} exempt lenders by name (total loans < 1,000)")
    
    # Aggregate by year
    year_data = {}
    for year in sorted(years):
        year_df = df_years[df_years['year'] == year]
        if year_df.empty:
            continue
        
        # Calculate averages (weighted by loan count if available, otherwise simple average)
        # For property_value, total_loan_costs, origination_charges: exclude $0 values from exempt lenders only
        # This preserves legitimate $0 values (e.g., home equity loans with $0 closing costs)
        if 'total_originations' in year_df.columns:
            total_loans = year_df['total_originations'].sum()
            if total_loans > 0:
                # Weighted average
                # For exempt lenders, exclude $0 values; for non-exempt lenders, include all values
                if exempt_lenders and ('lei' in year_df.columns or 'lender_name' in year_df.columns):
                    lender_col = 'lei' if 'lei' in year_df.columns else 'lender_name'
                    # Filter: exclude exempt lenders with $0 values, but keep non-exempt lenders (including $0)
                    property_value_df = year_df[
                        ~((year_df[lender_col].isin(exempt_lenders)) & 
                          ((year_df['avg_property_value'] == 0) | (year_df['avg_property_value'].isna())))
                    ]
                    total_loan_costs_df = year_df[
                        ~((year_df[lender_col].isin(exempt_lenders)) & 
                          ((year_df['avg_total_loan_costs'] == 0) | (year_df['avg_total_loan_costs'].isna())))
                    ]
                    origination_charges_df = year_df[
                        ~((year_df[lender_col].isin(exempt_lenders)) & 
                          ((year_df['avg_origination_charges'] == 0) | (year_df['avg_origination_charges'].isna())))
                    ]
                else:
                    # No lender identifier available, fall back to excluding all $0 values
                    property_value_df = year_df[(year_df['avg_property_value'] > 0) & (year_df['avg_property_value'].notna())]
                    total_loan_costs_df = year_df[(year_df['avg_total_loan_costs'] > 0) & (year_df['avg_total_loan_costs'].notna())]
                    origination_charges_df = year_df[(year_df['avg_origination_charges'] > 0) & (year_df['avg_origination_charges'].notna())]
                
                # Calculate weighted averages
                property_value_total = property_value_df['total_originations'].sum()
                total_loan_costs_total = total_loan_costs_df['total_originations'].sum()
                origination_charges_total = origination_charges_df['total_originations'].sum()
                
                year_data[year] = {
                    'property_value': (property_value_df['avg_property_value'] * property_value_df['total_originations']).sum() / property_value_total if property_value_total > 0 else np.nan,
                    'loan_amount': (year_df['avg_loan_amount'] * year_df['total_originations']).sum() / total_loans,
                    'interest_rate': (year_df['avg_interest_rate'] * year_df['total_originations']).sum() / total_loans,
                    'total_loan_costs': (total_loan_costs_df['avg_total_loan_costs'] * total_loan_costs_df['total_originations']).sum() / total_loan_costs_total if total_loan_costs_total > 0 else np.nan,
                    'origination_charges': (origination_charges_df['avg_origination_charges'] * origination_charges_df['total_originations']).sum() / origination_charges_total if origination_charges_total > 0 else np.nan
                }
            else:
                # Simple average
                if exempt_lenders and ('lei' in year_df.columns or 'lender_name' in year_df.columns):
                    lender_col = 'lei' if 'lei' in year_df.columns else 'lender_name'
                    property_value_filtered = year_df[
                        ~((year_df[lender_col].isin(exempt_lenders)) & 
                          ((year_df['avg_property_value'] == 0) | (year_df['avg_property_value'].isna())))
                    ]['avg_property_value']
                    total_loan_costs_filtered = year_df[
                        ~((year_df[lender_col].isin(exempt_lenders)) & 
                          ((year_df['avg_total_loan_costs'] == 0) | (year_df['avg_total_loan_costs'].isna())))
                    ]['avg_total_loan_costs']
                    origination_charges_filtered = year_df[
                        ~((year_df[lender_col].isin(exempt_lenders)) & 
                          ((year_df['avg_origination_charges'] == 0) | (year_df['avg_origination_charges'].isna())))
                    ]['avg_origination_charges']
                else:
                    property_value_filtered = year_df[(year_df['avg_property_value'] > 0) & (year_df['avg_property_value'].notna())]['avg_property_value']
                    total_loan_costs_filtered = year_df[(year_df['avg_total_loan_costs'] > 0) & (year_df['avg_total_loan_costs'].notna())]['avg_total_loan_costs']
                    origination_charges_filtered = year_df[(year_df['avg_origination_charges'] > 0) & (year_df['avg_origination_charges'].notna())]['avg_origination_charges']
                
                year_data[year] = {
                    'property_value': property_value_filtered.mean() if len(property_value_filtered) > 0 else np.nan,
                    'loan_amount': year_df['avg_loan_amount'].mean(),
                    'interest_rate': year_df['avg_interest_rate'].mean(),
                    'total_loan_costs': total_loan_costs_filtered.mean() if len(total_loan_costs_filtered) > 0 else np.nan,
                    'origination_charges': origination_charges_filtered.mean() if len(origination_charges_filtered) > 0 else np.nan
                }
        else:
            # Simple average
            if exempt_lenders and ('lei' in year_df.columns or 'lender_name' in year_df.columns):
                lender_col = 'lei' if 'lei' in year_df.columns else 'lender_name'
                property_value_filtered = year_df[
                    ~((year_df[lender_col].isin(exempt_lenders)) & 
                      ((year_df['avg_property_value'] == 0) | (year_df['avg_property_value'].isna())))
                ]['avg_property_value']
                total_loan_costs_filtered = year_df[
                    ~((year_df[lender_col].isin(exempt_lenders)) & 
                      ((year_df['avg_total_loan_costs'] == 0) | (year_df['avg_total_loan_costs'].isna())))
                ]['avg_total_loan_costs']
                origination_charges_filtered = year_df[
                    ~((year_df[lender_col].isin(exempt_lenders)) & 
                      ((year_df['avg_origination_charges'] == 0) | (year_df['avg_origination_charges'].isna())))
                ]['avg_origination_charges']
            else:
                property_value_filtered = year_df[(year_df['avg_property_value'] > 0) & (year_df['avg_property_value'].notna())]['avg_property_value']
                total_loan_costs_filtered = year_df[(year_df['avg_total_loan_costs'] > 0) & (year_df['avg_total_loan_costs'].notna())]['avg_total_loan_costs']
                origination_charges_filtered = year_df[(year_df['avg_origination_charges'] > 0) & (year_df['avg_origination_charges'].notna())]['avg_origination_charges']
            
            year_data[year] = {
                'property_value': property_value_filtered.mean() if len(property_value_filtered) > 0 else np.nan,
                'loan_amount': year_df['avg_loan_amount'].mean(),
                'interest_rate': year_df['avg_interest_rate'].mean(),
                'total_loan_costs': total_loan_costs_filtered.mean() if len(total_loan_costs_filtered) > 0 else np.nan,
                'origination_charges': origination_charges_filtered.mean() if len(origination_charges_filtered) > 0 else np.nan
            }
        
        # Calculate downpayment/equity
        year_data[year]['downpayment_equity'] = year_data[year]['property_value'] - year_data[year]['loan_amount']
    
    if not year_data:
        return pd.DataFrame()
    
    # Build table rows
    metrics = [
        ('Property Value', 'property_value', 'currency'),
        ('Loan Amount', 'loan_amount', 'currency'),
        ('Downpayment/Equity', 'downpayment_equity', 'currency'),
        ('Interest Rate', 'interest_rate', 'percentage'),
        ('Closing Costs', 'total_loan_costs', 'currency'),
        ('Origination Fees', 'origination_charges', 'currency')
    ]
    
    rows = []
    for metric_name, metric_key, format_type in metrics:
        row = {'Metric': metric_name}
        
        # Add year columns (ensure year is string for JSON serialization)
        for year in sorted(years):
            year_str = str(year)  # Convert to string for consistent column names
            if year in year_data:
                value = year_data[year][metric_key]
                if pd.isna(value) or value is None:
                    row[year_str] = 'N/A'
                elif format_type == 'currency':
                    row[year_str] = f"${value:,.0f}"
                elif format_type == 'percentage':
                    row[year_str] = f"{value:.2f}%"
                else:
                    row[year_str] = f"{value:,.0f}"
            else:
                row[year_str] = 'N/A'
        
        # Calculate change (first to last year)
        if len(years) >= 2 and years[0] in year_data and years[-1] in year_data:
            first_value = year_data[years[0]][metric_key]
            last_value = year_data[years[-1]][metric_key]
            if not pd.isna(first_value) and not pd.isna(last_value) and first_value != 0:
                if format_type == 'percentage':
                    change = last_value - first_value
                    row[f'Change Over Time ({years[0]}-{years[-1]})'] = f"{change:+.2f}pp"
                else:
                    change_pct = ((last_value - first_value) / first_value) * 100
                    row[f'Change Over Time ({years[0]}-{years[-1]})'] = f"{change_pct:+.1f}%"
            else:
                row[f'Change Over Time ({years[0]}-{years[-1]})'] = 'N/A'
        else:
            row[f'Change Over Time ({years[0]}-{years[-1]})'] = 'N/A'
        
        rows.append(row)
    
    result_df = pd.DataFrame(rows)
    return result_df



def create_lender_loan_costs_table(df: pd.DataFrame, latest_year: int, lender_type: str = None) -> pd.DataFrame:
    """
    Create Section 3 Loan Costs table with lenders as rows and most recent year metrics as columns.
    
    Metrics for most recent year:
    - Property Value (average)
    - Loan Amount (average)
    - Downpayment/Equity (average: property_value - loan_amount)
    - Interest Rate (average)
    - Closing Costs (average: total_loan_costs)
    - Origination Fees (average: origination_charges)
    
    Args:
        df: DataFrame with loan data
        latest_year: Most recent year to use for metrics
        lender_type: Optional filter by lender type ('Bank', 'Mortgage Company', 'Credit Union')
        
    Returns:
        DataFrame with Lender column and metric columns for most recent year
    """
    if df.empty:
        return pd.DataFrame()
    
    # Filter by lender type if specified
    if lender_type and 'lender_type' in df.columns:
        df = df[df['lender_type'] == lender_type].copy()
    
    # Filter to latest year
    df_latest = df[df['year'] == latest_year].copy()
    if df_latest.empty:
        return pd.DataFrame()
    
    # Required columns
    required_cols = ['lender_name', 'avg_property_value', 'avg_loan_amount', 'avg_interest_rate', 
                     'avg_total_loan_costs', 'avg_origination_charges', 'total_originations']
    missing_cols = [col for col in required_cols if col not in df_latest.columns]
    if missing_cols:
        logger.warning(f"[DEBUG] Missing columns for lender loan costs table: {missing_cols}")
        return pd.DataFrame()
    
    # Aggregate by lender (weighted averages)
    lender_data = []
    for lender_name in df_latest['lender_name'].unique():
        lender_df = df_latest[df_latest['lender_name'] == lender_name]
        total_loans = lender_df['total_originations'].sum()
        
        if total_loans > 0:
            # Weighted averages
            property_value = (lender_df['avg_property_value'] * lender_df['total_originations']).sum() / total_loans
            loan_amount = (lender_df['avg_loan_amount'] * lender_df['total_originations']).sum() / total_loans
            interest_rate = (lender_df['avg_interest_rate'] * lender_df['total_originations']).sum() / total_loans
            total_loan_costs = (lender_df['avg_total_loan_costs'] * lender_df['total_originations']).sum() / total_loans
            origination_charges = (lender_df['avg_origination_charges'] * lender_df['total_originations']).sum() / total_loans
            downpayment_equity = property_value - loan_amount
            
            lender_data.append({
                'Lender': lender_name,
                'Total Loans': f"{total_loans:,}",
                'Property Value': f"${property_value:,.0f}" if not pd.isna(property_value) else 'N/A',
                'Loan Amount': f"${loan_amount:,.0f}" if not pd.isna(loan_amount) else 'N/A',
                'Downpayment/Equity': f"${downpayment_equity:,.0f}" if not pd.isna(downpayment_equity) else 'N/A',
                'Interest Rate': f"{interest_rate:.2f}%" if not pd.isna(interest_rate) else 'N/A',
                'Closing Costs': f"${total_loan_costs:,.0f}" if not pd.isna(total_loan_costs) else 'N/A',
                'Origination Fees': f"${origination_charges:,.0f}" if not pd.isna(origination_charges) else 'N/A'
            })
    
    if not lender_data:
        return pd.DataFrame()
    
    result_df = pd.DataFrame(lender_data)
    # Sort by Total Loans descending
    result_df['Total Loans Sort'] = result_df['Total Loans'].str.replace(',', '').astype(int)
    result_df = result_df.sort_values('Total Loans Sort', ascending=False).drop('Total Loans Sort', axis=1)
    
    return result_df


