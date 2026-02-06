#!/usr/bin/env python3
"""
BigQuery-based branch data client for Summary of Deposits (SOD) data.
Uses branches.sod, branches.sod_legacy, and branches.sod25 tables.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from google.cloud import bigquery
from justdata.shared.utils.bigquery_client import get_bigquery_client

logger = logging.getLogger(__name__)


class BigQueryBranchClient:
    """Client for fetching branch data from BigQuery SOD tables."""
    
    def __init__(self, project_id: str = None):
        """
        Initialize BigQuery branch client.
        
        Args:
            project_id: GCP project ID (defaults to environment variable)
        """
        self.project_id = project_id or os.getenv('JUSTDATA_PROJECT_ID', 'justdata-ncrc')
        self.client = None
    
    def _get_client(self):
        """Get BigQuery client (lazy initialization)."""
        if self.client is None:
            self.client = get_bigquery_client(self.project_id)
        return self.client
    
    def get_branches(self, rssd: str, year: int) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Get branch locations for an institution by RSSD and year from BigQuery SOD tables.
        
        Queries branches.sod, branches.sod_legacy, and branches.sod25 tables.
        
        Args:
            rssd: RSSD ID (Federal Reserve identifier)
            year: Year to get data for
            
        Returns:
            Tuple of (list of branch location dictionaries, metadata dict)
        """
        try:
            # Determine which table(s) to query based on year
            # sod25 is for 2025, sod_legacy for older years, sod for intermediate years
            # We'll query all three and let UNION handle it
            
            # RSSD in SOD tables is stored as STRING - try both padded and unpadded formats
            # Use string interpolation (like data_utils.py) to avoid type issues
            from justdata.shared.utils.bigquery_client import escape_sql_string
            
            rssd_str = str(rssd).strip()
            try:
                rssd_unpadded = str(int(rssd_str))  # Remove leading zeros
            except (ValueError, TypeError):
                rssd_unpadded = rssd_str
            rssd_padded = rssd_str.zfill(10) if rssd_str.isdigit() else rssd_str
            
            escaped_rssd_unpadded = escape_sql_string(rssd_unpadded)
            escaped_rssd_padded = escape_sql_string(rssd_padded)
            
            # Use optimized SOD table in justdata (much faster than querying 3 separate tables)
            # RSSD is STRING, year is INT64 in optimized table
            # Join with CBSA crosswalk to get CBSA codes
            query = f"""
            WITH branches_with_cbsa AS (
                SELECT DISTINCT
                    b.branch_id as uninumbr,
                    b.bank_name,
                    b.year,
                    b.branch_name,
                    b.address,
                    b.city,
                    b.county,
                    b.state,
                    b.state_abbr,
                    b.zip,
                    b.latitude,
                    b.longitude,
                    b.deposits,
                    b.br_lmi,
                    b.br_minority,
                    b.service_type,
                    b.rssd,
                    b.assets_000s,
                    COALESCE(CAST(c.cbsa_code AS STRING), 'N/A') as cbsa_code,
                    COALESCE(c.CBSA, CONCAT(c.State, ' Non-MSA')) as cbsa_name
                FROM `{self.project_id}.justdata.sod_branches_optimized` b
                LEFT JOIN `justdata-ncrc.shared.cbsa_to_county` c
                    ON CAST(b.geoid5 AS STRING) = CAST(c.geoid5 AS STRING)
                WHERE (b.rssd = '{escaped_rssd_unpadded}' OR b.rssd = '{escaped_rssd_padded}')
                    AND b.year = '{year}'
            )
            SELECT *
            FROM branches_with_cbsa
            ORDER BY state, city, branch_name
            """
            
            logger.info(f"BigQuery branch query for RSSD {rssd} (unpadded: {rssd_unpadded}, padded: {rssd_padded}), year {year}")
            
            # Get client and execute query
            client = self._get_client()
            from justdata.shared.utils.bigquery_client import execute_query
            results = execute_query(client, query)
            
            branches = []
            for row in results:
                branch = {
                    'name': row.get('branch_name') or '',
                    'address': row.get('address') or '',
                    'city': row.get('city') or '',
                    'state': row.get('state_abbr') or row.get('state') or '',
                    'state_name': row.get('state') or '',
                    'zip': str(row.get('zip')) if row.get('zip') else '',
                    'county': row.get('county') or '',
                    'cbsa_code': row.get('cbsa_code') or 'N/A',
                    'cbsa_name': row.get('cbsa_name') or '',
                    'latitude': float(row.get('latitude')) if row.get('latitude') else None,
                    'longitude': float(row.get('longitude')) if row.get('longitude') else None,
                    'deposits': float(row.get('deposits')) if row.get('deposits') else 0,
                    'uninumbr': row.get('uninumbr'),
                    'year': row.get('year') or year,
                    'rssd': row.get('rssd'),
                    'is_lmi': bool(row.get('br_lmi')) if row.get('br_lmi') is not None else None,
                    'is_minority': bool(row.get('br_minority')) if row.get('br_minority') is not None else None,
                    'service_type': row.get('service_type') or '',
                    'raw': dict(row)  # Keep raw data for reference
                }
                
                # Only include if it has location info
                if branch['city'] or branch['state']:
                    branches.append(branch)
            
            metadata = {
                'total_available': len(branches),
                'returned': len(branches),
                'hit_limit': False,
                'source': 'bigquery_sod'
            }
            
            logger.info(f"BigQuery returned {len(branches)} branches for RSSD {rssd}, year {year}")
            return branches, metadata
            
        except Exception as e:
            logger.error(f"Error getting branches from BigQuery for RSSD {rssd}, year {year}: {e}", exc_info=True)
            return [], {'total_available': 0, 'returned': 0, 'hit_limit': False, 'source': 'bigquery_sod', 'error': str(e)}


import os

