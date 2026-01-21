#!/usr/bin/env python3
"""
Lender Analysis Processor for DataExplorer 2.0
Processes lender-specific queries with peer comparison.

FIXED: Added timeout handling and limited peer queries to prevent hanging.
"""

from typing import Dict, List, Any, Optional
import pandas as pd
import concurrent.futures
from justdata.apps.dataexplorer.data_utils import (
    execute_hmda_query, execute_sb_query, execute_branch_query,
    get_peer_lenders, get_lender_target_counties
)
from justdata.apps.dataexplorer.config import (
    PEER_VOLUME_MIN_PERCENT, PEER_VOLUME_MAX_PERCENT, DEFAULT_PEER_COUNT
)
import logging

logger = logging.getLogger(__name__)

# Timeout for peer queries (in seconds)
PEER_QUERY_TIMEOUT = 30
# Maximum peers to query in detail (to prevent very long running queries)
MAX_PEERS_TO_QUERY = 5


def process_lender_analysis(
    lender_id: str,
    data_types: List[str] = None,
    years: List[int] = None,
    geoids: List[str] = None,
    enable_peer_comparison: bool = True,
    custom_peers: List[str] = None
) -> Dict[str, Any]:
    """
    Process lender analysis with peer comparison.
    
    FIXED ISSUES FROM V1:
    - Peer comparison enabled by default
    - Proper peer data structure
    - Consistent peer calculations
    
    Args:
        lender_id: Lender ID (LEI for HMDA/SB, RSSD for Branches)
        data_types: List of data types to analyze ('hmda', 'sb', 'branches')
        years: Optional list of years
        geoids: Optional list of GEOIDs (if None, uses lender's target counties)
        enable_peer_comparison: Whether to include peer comparison
        custom_peers: Optional list of custom peer lender IDs
        
    Returns:
        Dictionary with lender analysis and peer comparison
    """
    try:
        data_types = data_types or ['hmda', 'sb', 'branches']
        results = {}
        
        # Process each data type
        if 'hmda' in data_types:
            hmda_data = process_lender_hmda(
                lender_id=lender_id,
                years=years,
                geoids=geoids,
                enable_peer_comparison=enable_peer_comparison,
                custom_peers=custom_peers
            )
            results['hmda'] = hmda_data
        
        if 'sb' in data_types:
            sb_data = process_lender_sb(
                lender_id=lender_id,
                years=years,
                geoids=geoids,
                enable_peer_comparison=enable_peer_comparison,
                custom_peers=custom_peers
            )
            results['sb'] = sb_data
        
        if 'branches' in data_types:
            branch_data = process_lender_branches(
                lender_id=lender_id,
                years=years,
                geoids=geoids
            )
            results['branches'] = branch_data
        
        return results
        
    except Exception as e:
        logger.error(f"Error processing lender analysis: {e}")
        raise Exception(f"Error processing lender analysis: {str(e)}")


def _query_peer_hmda(peer_info: Dict, geoids: List[str], years: List[int]) -> Optional[Dict[str, Any]]:
    """Helper function to query a single peer's HMDA data with timeout protection."""
    try:
        peer_id = peer_info.get('lender_id') or peer_info
        peer_name = peer_info.get('lender_name', 'Unknown') if isinstance(peer_info, dict) else 'Unknown'

        peer_results = execute_hmda_query(
            geoids=geoids or [],
            years=years or [],
            lender_id=peer_id
        )
        if peer_results:
            peer_df = pd.DataFrame(peer_results)
            peer_volume = peer_df['loan_amount'].sum() if 'loan_amount' in peer_df.columns else 0
            return {
                'lender_id': peer_id,
                'lender_name': peer_df['lender_name'].iloc[0] if 'lender_name' in peer_df.columns and len(peer_df) > 0 else peer_name,
                'total_loans': len(peer_df),
                'total_volume': float(peer_volume)
            }
    except Exception as e:
        logger.warning(f"Error querying peer {peer_info}: {e}")
    return None


def process_lender_hmda(
    lender_id: str,
    years: List[int] = None,
    geoids: List[str] = None,
    enable_peer_comparison: bool = True,
    custom_peers: List[str] = None
) -> Dict[str, Any]:
    """
    Process HMDA lender analysis with peer comparison.

    FIXED: Added timeout handling and limited peer queries to prevent hanging.
    """
    try:
        # Get lender data with timeout
        logger.info(f"Starting HMDA analysis for lender {lender_id}")
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(execute_hmda_query, geoids or [], years or [], lender_id=lender_id)
                lender_results = future.result(timeout=PEER_QUERY_TIMEOUT)
        except concurrent.futures.TimeoutError:
            logger.error(f"Timeout querying HMDA data for lender {lender_id}")
            return {
                'subject': {
                    'lender_id': lender_id,
                    'total_loans': 0,
                    'total_volume': 0,
                    'error': 'Query timed out'
                },
                'comparison': {}
            }

        if not lender_results:
            return {
                'subject': {
                    'lender_id': lender_id,
                    'total_loans': 0,
                    'total_volume': 0
                },
                'comparison': {}
            }

        df = pd.DataFrame(lender_results)
        subject_volume = df['loan_amount'].sum() if 'loan_amount' in df.columns else 0

        # Subject lender summary
        subject_summary = {
            'lender_id': lender_id,
            'lender_name': df['lender_name'].iloc[0] if 'lender_name' in df.columns and len(df) > 0 else 'Unknown',
            'total_loans': len(df),
            'total_volume': float(subject_volume),
            'average_loan_amount': float(subject_volume / len(df)) if len(df) > 0 else 0
        }

        # Peer comparison
        comparison = {}
        if enable_peer_comparison:
            peer_data = []
            peers_to_query = []

            if custom_peers:
                # Use custom peers - limit to MAX_PEERS_TO_QUERY
                peers_to_query = [{'lender_id': pid, 'lender_name': 'Unknown'} for pid in custom_peers[:MAX_PEERS_TO_QUERY]]
            else:
                # Auto-select peers based on volume with timeout
                try:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(
                            get_peer_lenders,
                            lender_id=lender_id,
                            data_type='hmda',
                            volume=subject_volume,
                            min_percent=PEER_VOLUME_MIN_PERCENT,
                            max_percent=PEER_VOLUME_MAX_PERCENT,
                            limit=min(DEFAULT_PEER_COUNT, MAX_PEERS_TO_QUERY)
                        )
                        peers_to_query = future.result(timeout=PEER_QUERY_TIMEOUT)
                except concurrent.futures.TimeoutError:
                    logger.warning(f"Timeout finding peer lenders for {lender_id}")
                    peers_to_query = []
                except Exception as e:
                    logger.warning(f"Error finding peer lenders: {e}")
                    peers_to_query = []

            # Query peer data with timeout protection
            if peers_to_query:
                logger.info(f"Querying {len(peers_to_query)} peers for comparison")
                try:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=min(3, len(peers_to_query))) as executor:
                        futures = {
                            executor.submit(_query_peer_hmda, peer, geoids, years): peer
                            for peer in peers_to_query[:MAX_PEERS_TO_QUERY]
                        }
                        for future in concurrent.futures.as_completed(futures, timeout=PEER_QUERY_TIMEOUT * 2):
                            try:
                                result = future.result(timeout=PEER_QUERY_TIMEOUT)
                                if result:
                                    peer_data.append(result)
                            except concurrent.futures.TimeoutError:
                                logger.warning("Peer query timed out")
                            except Exception as e:
                                logger.warning(f"Error in peer query: {e}")
                except concurrent.futures.TimeoutError:
                    logger.warning("Overall peer queries timed out")

                if custom_peers:
                    comparison['custom_peers'] = peer_data
                else:
                    comparison['auto_peers'] = peer_data

            # Calculate peer averages
            if comparison.get('auto_peers') or comparison.get('custom_peers'):
                peer_list = comparison.get('auto_peers') or comparison.get('custom_peers', [])
                if peer_list:
                    avg_volume = sum(p['total_volume'] for p in peer_list) / len(peer_list)
                    avg_loans = sum(p['total_loans'] for p in peer_list) / len(peer_list)

                    comparison['peer_average'] = {
                        'total_loans': float(avg_loans),
                        'total_volume': float(avg_volume)
                    }

        logger.info(f"Completed HMDA analysis for lender {lender_id}")
        return {
            'subject': subject_summary,
            'comparison': comparison
        }

    except Exception as e:
        logger.error(f"Error processing lender HMDA analysis: {e}", exc_info=True)
        raise Exception(f"Error processing lender HMDA analysis: {str(e)}")


def process_lender_sb(
    lender_id: str,
    years: List[int] = None,
    geoids: List[str] = None,
    enable_peer_comparison: bool = True,
    custom_peers: List[str] = None
) -> Dict[str, Any]:
    """
    Process Small Business lender analysis with peer comparison.
    """
    try:
        # Similar structure to HMDA but for SB data
        lender_results = execute_sb_query(
            geoids=geoids or [],
            years=years or [],
            lender_id=lender_id
        )
        
        if not lender_results:
            return {
                'subject': {
                    'lender_id': lender_id,
                    'total_loans': 0,
                    'total_volume': 0
                },
                'comparison': {}
            }
        
        df = pd.DataFrame(lender_results)
        subject_volume = df['loan_amount'].sum() if 'loan_amount' in df.columns else 0
        
        subject_summary = {
            'lender_id': lender_id,
            'lender_name': df['lender_name'].iloc[0] if 'lender_name' in df.columns and len(df) > 0 else 'Unknown',
            'total_loans': int(df['number_of_loans'].sum()) if 'number_of_loans' in df.columns else len(df),
            'total_volume': float(subject_volume)
        }
        
        comparison = {}
        if enable_peer_comparison:
            if custom_peers:
                peer_data = []
                for peer_id in custom_peers[:DEFAULT_PEER_COUNT]:
                    peer_results = execute_sb_query(
                        geoids=geoids or [],
                        years=years or [],
                        lender_id=peer_id
                    )
                    if peer_results:
                        peer_df = pd.DataFrame(peer_results)
                        peer_volume = peer_df['loan_amount'].sum() if 'loan_amount' in peer_df.columns else 0
                        peer_data.append({
                            'lender_id': peer_id,
                            'lender_name': peer_df['lender_name'].iloc[0] if 'lender_name' in peer_df.columns else 'Unknown',
                            'total_loans': int(peer_df['number_of_loans'].sum()) if 'number_of_loans' in peer_df.columns else len(peer_df),
                            'total_volume': float(peer_volume)
                        })
                comparison['custom_peers'] = peer_data
            else:
                peers = get_peer_lenders(
                    lender_id=lender_id,
                    data_type='sb',
                    volume=subject_volume,
                    min_percent=PEER_VOLUME_MIN_PERCENT,
                    max_percent=PEER_VOLUME_MAX_PERCENT,
                    limit=DEFAULT_PEER_COUNT
                )
                
                peer_data = []
                for peer in peers:
                    peer_id = peer['lender_id']
                    peer_results = execute_sb_query(
                        geoids=geoids or [],
                        years=years or [],
                        lender_id=peer_id
                    )
                    if peer_results:
                        peer_df = pd.DataFrame(peer_results)
                        peer_volume = peer_df['loan_amount'].sum() if 'loan_amount' in peer_df.columns else 0
                        peer_data.append({
                            'lender_id': peer_id,
                            'lender_name': peer.get('lender_name', 'Unknown'),
                            'total_loans': int(peer_df['number_of_loans'].sum()) if 'number_of_loans' in peer_df.columns else len(peer_df),
                            'total_volume': float(peer_volume)
                        })
                comparison['auto_peers'] = peer_data
            
            # Calculate peer averages
            if comparison.get('auto_peers') or comparison.get('custom_peers'):
                peer_list = comparison.get('auto_peers') or comparison.get('custom_peers', [])
                if peer_list:
                    avg_volume = sum(p['total_volume'] for p in peer_list) / len(peer_list)
                    avg_loans = sum(p['total_loans'] for p in peer_list) / len(peer_list)
                    
                    comparison['peer_average'] = {
                        'total_loans': float(avg_loans),
                        'total_volume': float(avg_volume)
                    }
        
        return {
            'subject': subject_summary,
            'comparison': comparison
        }
        
    except Exception as e:
        logger.error(f"Error processing lender SB analysis: {e}")
        raise Exception(f"Error processing lender SB analysis: {str(e)}")


def process_lender_branches(
    lender_id: str,
    years: List[int] = None,
    geoids: List[str] = None
) -> Dict[str, Any]:
    """
    Process Branch lender analysis.
    """
    try:
        # Get target counties if not provided
        if not geoids and years:
            target_year = max(years) if years else None
            if target_year:
                geoids = get_lender_target_counties(lender_id, target_year)
        
        branch_results = execute_branch_query(
            geoids=geoids,
            years=years,
            lender_id=lender_id
        )
        
        if not branch_results:
            return {
                'lender_id': lender_id,
                'total_branches': 0,
                'total_deposits': 0,
                'target_counties': geoids or []
            }
        
        df = pd.DataFrame(branch_results)
        
        return {
            'lender_id': lender_id,
            'total_branches': len(df),
            'total_deposits': float(df['deposits'].sum()) if 'deposits' in df.columns else 0,
            'target_counties': geoids or [],
            'by_county': df.groupby('geoid').agg({
                'deposits': ['count', 'sum']
            }).reset_index().to_dict('records') if 'geoid' in df.columns else []
        }
        
    except Exception as e:
        logger.error(f"Error processing lender branch analysis: {e}")
        raise Exception(f"Error processing lender branch analysis: {str(e)}")
