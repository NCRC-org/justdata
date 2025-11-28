#!/usr/bin/env python3
"""
Lender Analysis Data Processor
Processes raw lender data (subject and peers) from all three data types
and creates comparison metrics.
"""

from typing import List, Dict, Any, Optional
from collections import defaultdict
from .area_analysis_processor import (
    process_hmda_area_analysis,
    process_sb_area_analysis,
    process_branch_area_analysis
)


def process_lender_analysis(
    results: Dict[str, Dict[str, List[Dict[str, Any]]]],
    years: List[int],
    geoids: List[str],
    subject_lender_id: str,
    data_type: str = 'hmda'
) -> Dict[str, Any]:
    """
    Process lender analysis results combining all three data types.
    
    Args:
        results: Dictionary with structure:
            {
                'hmda': {'subject': [...], 'peer': [...]},
                'sb': {'subject': [...], 'peer': [...]},
                'branches': {'subject': [...], 'peer': [...]}
            }
        years: List of years in analysis
        geoids: List of geographic identifiers
        subject_lender_id: Subject lender identifier
        data_type: Primary data type ('hmda', 'sb', or 'branches')
    
    Returns:
        Dictionary with processed analysis results including:
        - Combined summary (all data types)
        - Individual data type results
        - Peer comparison metrics
    """
    processed = {
        'combined_summary': {},
        'hmda': {},
        'sb': {},
        'branches': {},
        'peer_comparison': {},
        'years': years,
        'geoids': geoids,
        'subject_lender_id': subject_lender_id
    }
    
    # Process HMDA data
    if results.get('hmda', {}).get('subject'):
        hmda_subject_data = results['hmda']['subject']
        hmda_peer_data = results['hmda'].get('peer', [])
        
        # Process subject HMDA data using existing processor
        hmda_subject_processed = process_hmda_area_analysis(
            raw_data=hmda_subject_data,
            years=years,
            geoids=geoids
        )
        
        # Process peer HMDA data
        hmda_peer_processed = None
        if hmda_peer_data:
            hmda_peer_processed = process_hmda_area_analysis(
                raw_data=hmda_peer_data,
                years=years,
                geoids=geoids
            )
        
        # Calculate peer comparison metrics
        hmda_comparison = calculate_peer_comparison_metrics(
            subject_data=hmda_subject_processed,
            peer_data=hmda_peer_processed,
            data_type='hmda'
        )
        
        processed['hmda'] = {
            'subject': hmda_subject_processed,
            'peer': hmda_peer_processed,
            'comparison': hmda_comparison
        }
    
    # Process Small Business data
    if results.get('sb', {}).get('subject'):
        sb_subject_data = results['sb']['subject']
        sb_peer_data = results['sb'].get('peer', [])
        
        # Process subject SB data
        sb_subject_processed = process_sb_area_analysis(
            raw_data=sb_subject_data,
            years=years,
            geoids=geoids
        )
        
        # Process peer SB data
        sb_peer_processed = None
        if sb_peer_data:
            sb_peer_processed = process_sb_area_analysis(
                raw_data=sb_peer_data,
                years=years,
                geoids=geoids
            )
        
        # Calculate peer comparison metrics
        sb_comparison = calculate_peer_comparison_metrics(
            subject_data=sb_subject_processed,
            peer_data=sb_peer_processed,
            data_type='sb'
        )
        
        processed['sb'] = {
            'subject': sb_subject_processed,
            'peer': sb_peer_processed,
            'comparison': sb_comparison
        }
    
    # Process Branch data
    if results.get('branches', {}).get('subject'):
        branch_subject_data = results['branches']['subject']
        branch_peer_data = results['branches'].get('peer', [])
        
        # Process subject branch data
        branch_subject_processed = process_branch_area_analysis(
            raw_data=branch_subject_data,
            years=years,
            geoids=geoids
        )
        
        # Process peer branch data
        branch_peer_processed = None
        if branch_peer_data:
            branch_peer_processed = process_branch_area_analysis(
                raw_data=branch_peer_data,
                years=years,
                geoids=geoids
            )
        
        # Calculate peer comparison metrics
        branch_comparison = calculate_peer_comparison_metrics(
            subject_data=branch_subject_processed,
            peer_data=branch_peer_processed,
            data_type='branches'
        )
        
        processed['branches'] = {
            'subject': branch_subject_processed,
            'peer': branch_peer_processed,
            'comparison': branch_comparison
        }
    
    # Create combined summary
    processed['combined_summary'] = create_combined_lender_summary(processed)
    
    return processed


def calculate_peer_comparison_metrics(
    subject_data: Dict[str, Any],
    peer_data: Optional[Dict[str, Any]],
    data_type: str = 'hmda'
) -> Dict[str, Any]:
    """
    Calculate peer comparison metrics comparing subject to peer averages.
    
    Args:
        subject_data: Processed subject lender data
        peer_data: Processed peer lender data (aggregated)
        data_type: Data type ('hmda', 'sb', or 'branches')
    
    Returns:
        Dictionary with comparison metrics
    """
    if not subject_data or not peer_data:
        return {}
    
    comparison = {
        'summary': {},
        'demographics': {},
        'income_neighborhood': {},
        'top_lenders': []
    }
    
    # Compare summary metrics
    subject_summary = subject_data.get('summary', [])
    peer_summary = peer_data.get('summary', [])
    
    if subject_summary and peer_summary:
        # Get latest year data
        subject_latest = subject_summary[0] if subject_summary else {}
        peer_latest = peer_summary[0] if peer_summary else {}
        
        comparison['summary'] = {
            'subject': subject_latest,
            'peer_average': peer_latest,
            'difference': {
                'total_loans': (subject_latest.get('total_loans', 0) or 0) - (peer_latest.get('total_loans', 0) or 0),
                'total_amount': (subject_latest.get('total_amount', 0) or 0) - (peer_latest.get('total_amount', 0) or 0)
            }
        }
    
    # Compare demographics
    subject_demo = subject_data.get('demographics', [])
    peer_demo = peer_data.get('demographics', [])
    
    if subject_demo and peer_demo:
        comparison['demographics'] = {
            'subject': subject_demo,
            'peer_average': peer_demo
        }
    
    # Compare income & neighborhood
    subject_income = subject_data.get('income_neighborhood', [])
    peer_income = peer_data.get('income_neighborhood', [])
    
    if subject_income and peer_income:
        comparison['income_neighborhood'] = {
            'subject': subject_income,
            'peer_average': peer_income
        }
    
    return comparison


def create_combined_lender_summary(processed_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create combined summary across all three data types.
    
    Args:
        processed_data: Processed lender analysis data
    
    Returns:
        Combined summary dictionary
    """
    summary = {
        'hmda': processed_data.get('hmda', {}).get('subject', {}).get('summary', []),
        'sb': processed_data.get('sb', {}).get('subject', {}).get('summary', []),
        'branches': processed_data.get('branches', {}).get('subject', {}).get('summary', [])
    }
    
    return summary


def aggregate_peer_data(
    peer_raw_data: List[Dict[str, Any]],
    data_type: str = 'hmda'
) -> Dict[str, Any]:
    """
    Aggregate peer data for comparison.
    
    Args:
        peer_raw_data: List of peer lender data rows
        data_type: Data type ('hmda', 'sb', or 'branches')
    
    Returns:
        Aggregated peer data dictionary
    """
    if not peer_raw_data:
        return {}
    
    # Group by year and aggregate
    by_year = defaultdict(lambda: {
        'total_loans': 0,
        'total_amount': 0,
        'lmict_loans': 0,
        'mmct_loans': 0,
        'peer_count': 0
    })
    
    for row in peer_raw_data:
        year = str(row.get('activity_year') or row.get('year', ''))
        by_year[year]['total_loans'] += row.get('total_loans', 0) or 0
        by_year[year]['total_amount'] += row.get('total_amount', 0) or 0
        by_year[year]['lmict_loans'] += row.get('lmict_loans', 0) or 0
        by_year[year]['mmct_loans'] += row.get('mmct_loans', 0) or 0
        by_year[year]['peer_count'] += 1
    
    # Calculate averages
    aggregated = []
    for year, data in sorted(by_year.items(), reverse=True):
        peer_count = data['peer_count'] or 1
        aggregated.append({
            'year': year,
            'total_loans': data['total_loans'] / peer_count,  # Average
            'total_amount': data['total_amount'] / peer_count,  # Average
            'lmict_percentage': (data['lmict_loans'] / data['total_loans'] * 100) if data['total_loans'] > 0 else 0,
            'mmct_percentage': (data['mmct_loans'] / data['total_loans'] * 100) if data['total_loans'] > 0 else 0,
            'peer_count': peer_count
        })
    
    return {
        'summary': aggregated
    }

