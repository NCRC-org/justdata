#!/usr/bin/env python3
"""
BigQuery-based credit union branch data client.
Uses justdata.credit_union_branches table.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from justdata.shared.utils.bigquery_client import get_bigquery_client, execute_query, escape_sql_string

logger = logging.getLogger(__name__)


class BigQueryCreditUnionBranchClient:
    """Client for fetching credit union branch data from BigQuery."""
    
    def __init__(self, project_id: str = None):
        """
        Initialize BigQuery credit union branch client.
        
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
    
    def get_branches(self, rssd: str = None, cu_number: str = None, year: int = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Get branch locations for a credit union by RSSD or CU number and year.
        
        Args:
            rssd: RSSD ID (Federal Reserve identifier) - preferred
            cu_number: Credit union number (alternative identifier)
            year: Year to get data for
            
        Returns:
            Tuple of (list of branch location dictionaries, metadata dict)
        """
        try:
            if not rssd and not cu_number:
                raise ValueError("Either RSSD or CU number is required")
            
            if not year:
                from datetime import datetime
                year = datetime.now().year
            
            # Build WHERE clause
            where_conditions = [f"year = {year}"]
            
            if rssd:
                rssd_str = str(rssd).strip()
                escaped_rssd = escape_sql_string(rssd_str)
                where_conditions.append(f"rssd = '{escaped_rssd}'")
            elif cu_number:
                cu_num_str = str(cu_number).strip()
                escaped_cu = escape_sql_string(cu_num_str)
                where_conditions.append(f"cu_number = '{escaped_cu}'")
            
            # Join with CBSA crosswalk to get CBSA codes
            query = f"""
            WITH branches_with_cbsa AS (
                SELECT DISTINCT
                    b.site_id as branch_id,
                    b.cu_name,
                    b.year,
                    b.site_name as branch_name,
                    b.address_line1 as address,
                    b.city,
                    b.county,
                    b.state,
                    b.zip,
                    b.cu_number,
                    b.rssd,
                    COALESCE(c.cbsa_code, 'N/A') as cbsa_code,
                    COALESCE(c.cbsa_name, CONCAT(c.state_name, ' Non-MSA')) as cbsa_name
                FROM `justdata-ncrc.lenderprofile.cu_branches` b
                LEFT JOIN `justdata-ncrc.shared.cbsa_to_county` c
                    ON CAST(b.county AS STRING) = CAST(c.county_name AS STRING)
                    AND CAST(b.state AS STRING) = CAST(c.state_name AS STRING)
                WHERE {' AND '.join(where_conditions)}
            )
            SELECT *
            FROM branches_with_cbsa
            ORDER BY state, city, branch_name
            """
            
            logger.info(f"BigQuery CU branch query for {'RSSD ' + str(rssd) if rssd else 'CU ' + str(cu_number)}, year {year}")
            
            # Get client and execute query
            client = self._get_client()
            results = execute_query(client, query)
            
            branches = []
            for row in results:
                branch = {
                    'name': row.get('branch_name') or '',
                    'address': row.get('address') or '',
                    'city': row.get('city') or '',
                    'state': row.get('state') or '',
                    'zip': str(row.get('zip')) if row.get('zip') else '',
                    'county': row.get('county') or '',
                    'cbsa_code': row.get('cbsa_code') or 'N/A',
                    'cbsa_name': row.get('cbsa_name') or '',
                    'cu_number': row.get('cu_number'),
                    'rssd': row.get('rssd'),
                    'year': row.get('year') or year,
                    'raw': dict(row)
                }
                
                # Only include if it has location info
                if branch['city'] or branch['state']:
                    branches.append(branch)
            
            metadata = {
                'total_available': len(branches),
                'returned': len(branches),
                'hit_limit': False,
                'source': 'bigquery_cu_branches'
            }
            
            logger.info(f"BigQuery returned {len(branches)} CU branches for {'RSSD ' + str(rssd) if rssd else 'CU ' + str(cu_number)}, year {year}")
            return branches, metadata
            
        except Exception as e:
            logger.error(f"Error getting CU branches from BigQuery: {e}", exc_info=True)
            return [], {'total_available': 0, 'returned': 0, 'hit_limit': False, 'source': 'bigquery_cu_branches', 'error': str(e)}

