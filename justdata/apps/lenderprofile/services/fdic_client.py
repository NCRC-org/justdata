#!/usr/bin/env python3
"""
FDIC BankFind API Client
Fetches bank financial data, branch locations, and institution details.
"""

import requests
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class FDICClient:
    """
    Client for FDIC BankFind API.
    
    Documentation: https://banks.data.fdic.gov/docs/
    Base URL: https://banks.data.fdic.gov/api/
    """
    
    def __init__(self):
        """Initialize FDIC API client."""
        self.base_url = 'https://banks.data.fdic.gov/api'
        self.timeout = 30
    
    def search_institutions(self, name: str, limit: int = 20, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Search for institutions by name.

        Tries multiple search strategies:
        1. Direct name search
        2. Name with common suffixes (National Association, NA, etc.)
        3. Filter by name using filters parameter
        4. Try exact name match with quotes

        Results are sorted by total assets (descending) to prioritize the main/largest
        institution when multiple subsidiaries or legacy entities exist.

        Args:
            name: Institution name to search for
            limit: Maximum number of results
            active_only: If True, only return active institutions (default: True)

        Returns:
            List of matching institutions
        """
        try:
            url = f'{self.base_url}/institutions'
            results = []
            name_clean = name.strip()

            # Try wildcard filter first (most reliable)
            logger.info(f"FDIC API: Searching with wildcard filter for '{name}'")
            wildcard_filter = f'NAME:*{name_clean.replace(" ", "*")}*'
            params = {
                'filters': wildcard_filter,
                'fields': 'NAME,CERT,CITY,STALP,STATE,RSSDID,FED_RSSD,INSTTYPE,ASSET,ACTIVE',
                'sort_by': 'ASSET',
                'sort_order': 'DESC',
                'limit': limit,
                'format': 'json'
            }

            response = requests.get(url, params=params, timeout=self.timeout)
            logger.info(f"FDIC API response status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                results = data.get('data', [])
                logger.info(f"FDIC API returned {len(results)} results with wildcard filter")

            # If no results with wildcard, try exact search parameter
            if not results:
                logger.info(f"No wildcard results, trying 'search' parameter")
                params = {
                    'search': name,
                    'fields': 'NAME,CERT,CITY,STALP,STATE,RSSDID,FED_RSSD,INSTTYPE,ASSET,ACTIVE',
                    'sort_by': 'ASSET',
                    'sort_order': 'DESC',
                    'limit': limit,
                    'format': 'json'
                }
                response = requests.get(url, params=params, timeout=self.timeout)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('data', [])
                    logger.info(f"FDIC API returned {len(results)} results for search '{name}'")
            
            # If no results, try with filters parameter (more specific)
            if not results:
                logger.info(f"No results with 'search' parameter, trying 'filters' parameter")
                # Try exact match with quotes
                filter_queries = [
                    f'NAME:"{name}"',
                    f'NAME:{name}',
                    f'NAME:"*{name}*"',
                ]
                
                for filter_query in filter_queries:
                    params = {
                        'filters': filter_query,
                        'limit': limit,
                        'format': 'json'
                    }
                    try:
                        response = requests.get(url, params=params, timeout=self.timeout)
                        if response.status_code == 200:
                            data = response.json()
                            filter_results = data.get('data', [])
                            if filter_results:
                                logger.info(f"FDIC API returned {len(filter_results)} results with filter '{filter_query}'")
                                results = filter_results
                                break
                    except Exception as e:
                        logger.debug(f"Filter query '{filter_query}' failed: {e}")
                        continue
            
            # If still no results, try name variations
            if not results:
                # Create more comprehensive name variations
                name_clean = name.strip()
                name_variations = [
                    f"{name_clean}, National Association",
                    f"{name_clean} NA",
                    f"{name_clean} National Association",
                    name_clean.replace(" Bank", " Bank, National Association"),
                    name_clean.replace(" BANK", " BANK, NATIONAL ASSOCIATION"),
                    name_clean.replace("Bank", "Bank, National Association"),
                    name_clean.replace("BANK", "BANK, NATIONAL ASSOCIATION"),
                    # Try without "Bank" suffix
                    name_clean.replace(" Bank", "").replace(" BANK", ""),
                    # Try with "Financial Services"
                    name_clean.replace(" Bank", " Financial Services"),
                    name_clean.replace(" BANK", " FINANCIAL SERVICES"),
                ]
                
                # Remove duplicates while preserving order
                seen = set()
                name_variations = [v for v in name_variations if v and v not in seen and not seen.add(v)]
                
                for variation in name_variations:
                    if variation == name:
                        continue
                    logger.info(f"Trying name variation: '{variation}'")
                    params = {
                        'search': variation,
                        'limit': limit,
                        'format': 'json'
                    }
                    response = requests.get(url, params=params, timeout=self.timeout)
                    if response.status_code == 200:
                        data = response.json()
                        variation_results = data.get('data', [])
                        if variation_results:
                            logger.info(f"Found {len(variation_results)} results with variation '{variation}'")
                            results = variation_results
                            break
                
                # If still no results, try searching with wildcards using filters
                if not results:
                    logger.info("Trying wildcard search with filters")
                    params = {
                        'filters': f'NAME:*{name_clean.replace(" ", "*")}*',
                        'limit': limit,
                        'format': 'json'
                    }
                    try:
                        response = requests.get(url, params=params, timeout=self.timeout)
                        if response.status_code == 200:
                            data = response.json()
                            wildcard_results = data.get('data', [])
                            if wildcard_results:
                                logger.info(f"Found {len(wildcard_results)} results with wildcard search")
                                results = wildcard_results
                    except Exception as e:
                        logger.debug(f"Wildcard search failed: {e}")
            
            # FDIC API returns nested structure: {'data': {'NAME': ..., 'CERT': ...}, 'score': ...}
            # Extract the nested 'data' object from each result
            flattened_results = []
            for r in results:
                if isinstance(r, dict) and 'data' in r:
                    flattened_results.append(r['data'])
                else:
                    flattened_results.append(r)
            results = flattened_results

            # Filter to only active institutions if requested
            if active_only and results:
                active_results = [r for r in results if r.get('ACTIVE') == 1]
                if active_results:
                    logger.info(f"Filtered to {len(active_results)} active institutions (from {len(results)} total)")
                    results = active_results
                else:
                    # If no active results, fall back to all results
                    logger.info(f"No active institutions found, returning all {len(results)} results")

            if results:
                logger.info(f"First result: {results[0].get('NAME', 'N/A')} (CERT: {results[0].get('CERT', 'N/A')}, RSSD: {results[0].get('RSSDID', 'N/A')}, Active: {results[0].get('ACTIVE', 'N/A')})")
            return results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"FDIC API error searching for '{name}': {e}", exc_info=True)
            return []
    
    def get_institution(self, cert: str) -> Optional[Dict[str, Any]]:
        """
        Get institution details by FDIC certificate number.
        
        Args:
            cert: FDIC certificate number
            
        Returns:
            Institution details or None
        """
        try:
            url = f'{self.base_url}/institutions/{cert}'
            params = {'format': 'json'}
            
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            return data.get('data', {}).get('data', {})
            
        except requests.exceptions.RequestException as e:
            logger.error(f"FDIC API error getting institution {cert}: {e}")
            return None
    
    def get_institution_by_rssd(self, rssd: str) -> Optional[Dict[str, Any]]:
        """
        Get institution details by RSSD ID.
        
        Tries multiple formats:
        1. Direct RSSD (as provided)
        2. RSSD padded to 10 digits with leading zeros
        3. RSSD without quotes in filter
        
        Args:
            rssd: Federal Reserve System ID (RSSD)
            
        Returns:
            Institution details or None
        """
        try:
            url = f'{self.base_url}/institutions'
            
            # Try different RSSD formats
            rssd_formats = [
                str(rssd).strip(),  # As provided
                str(rssd).strip().zfill(10),  # Padded to 10 digits
                str(rssd).strip().lstrip('0') or '0',  # Without leading zeros
            ]
            
            for rssd_format in rssd_formats:
                # Try with quotes
                params = {
                    'filters': f'RSSDID:"{rssd_format}"',
                    'format': 'json',
                    'limit': 1
                }
                
                logger.info(f"FDIC API request by RSSD: {url} with params: {params}")
                response = requests.get(url, params=params, timeout=self.timeout)
                logger.info(f"FDIC API response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('data', [])
                    logger.info(f"FDIC API returned {len(results)} results for RSSD {rssd_format}")
                    
                    if results:
                        inst = results[0]
                        logger.info(f"Found institution: {inst.get('NAME', 'N/A')} (CERT: {inst.get('CERT', 'N/A')})")
                        return inst
                
                # Try without quotes
                params = {
                    'filters': f'RSSDID:{rssd_format}',
                    'format': 'json',
                    'limit': 1
                }
                
                logger.info(f"FDIC API request by RSSD (no quotes): {url} with params: {params}")
                response = requests.get(url, params=params, timeout=self.timeout)
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('data', [])
                    if results:
                        inst = results[0]
                        logger.info(f"Found institution: {inst.get('NAME', 'N/A')} (CERT: {inst.get('CERT', 'N/A')})")
                        return inst
            
            logger.warning(f"No FDIC institution found for RSSD {rssd} (tried formats: {rssd_formats})")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"FDIC API error getting institution by RSSD {rssd}: {e}")
            return None
    
    def get_financials(self, cert: str, fields: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get financial data (Call Reports) for an institution.

        Args:
            cert: FDIC certificate number
            fields: Optional list of specific fields to retrieve

        Returns:
            List of financial records (quarterly data), sorted by date descending (most recent first)
        """
        try:
            url = f'{self.base_url}/financials'
            params = {
                'filters': f'CERT:{cert}',
                'sort_by': 'REPDTE',
                'sort_order': 'DESC',
                'format': 'json',
                'limit': 100  # Get last 5 years (20 quarters)
            }

            if fields:
                # Always include REPDTE for sorting
                field_list = list(fields) if 'REPDTE' in fields else list(fields) + ['REPDTE']
                params['fields'] = ','.join(field_list)

            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            results = data.get('data', [])

            # FDIC API returns nested structure: {'data': {...}, 'score': ...}
            # Flatten to just the data object
            flattened = []
            for r in results:
                if isinstance(r, dict) and 'data' in r:
                    flattened.append(r['data'])
                else:
                    flattened.append(r)

            logger.info(f"FDIC Financials: Retrieved {len(flattened)} records for cert {cert}")
            if flattened:
                latest = flattened[0]
                logger.info(f"  Latest report date: {latest.get('REPDTE')}, Assets: {latest.get('ASSET')}")

            return flattened
            
        except requests.exceptions.RequestException as e:
            logger.error(f"FDIC API error getting financials for {cert}: {e}")
            return []
    
    def get_branches(self, cert: str, year: Optional[int] = None, max_branches: int = 10000) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Get branch locations for an institution using FDIC Locations API.
        
        Uses the /locations endpoint which provides branch location data.
        Note: The API's year parameter may not filter correctly, so we use
        the actual returned count as the total.
        
        Documentation: https://banks.data.fdic.gov/docs/
        Endpoint: https://banks.data.fdic.gov/api/locations
        
        Args:
            cert: FDIC certificate number
            year: Year to get data for (for reference, API filtering may be limited)
            max_branches: Maximum number of branches to retrieve (default: 10000, API limit)
            
        Returns:
            Tuple of (list of branch location dictionaries, metadata dict with total count)
        """
        try:
            # Use Locations endpoint for branch-level data
            url = f'{self.base_url}/locations'
            params = {
                'cert': cert,
                'format': 'json',
                'limit': min(max_branches, 10000)  # API limit is 10,000
            }
            
            # Year parameter (may not filter correctly, but include for reference)
            if year:
                params['year'] = year
            else:
                # Default to most recent year if not specified
                from datetime import datetime
                params['year'] = datetime.now().year
                year = params['year']
            
            logger.info(f"FDIC Locations API request: {url} with cert={cert}, year={year}, limit={params['limit']}")
            response = requests.get(url, params=params, timeout=self.timeout)
            logger.info(f"FDIC Locations API response status: {response.status_code}")
            response.raise_for_status()
            
            data = response.json()
            
            # The API returns data in nested format: data['data'] is a list where each item has a 'data' field
            branches = []
            
            if 'data' in data and isinstance(data['data'], list):
                # Extract the nested 'data' field from each item
                for item in data['data']:
                    if isinstance(item, dict) and 'data' in item:
                        branch_data = item['data']
                        branches.append(branch_data)
                    elif isinstance(item, dict):
                        # Sometimes the data is directly in the item
                        branches.append(item)
            
            logger.info(f"FDIC Locations API returned {len(branches)} raw branch records for year {year}")
            
            # Format branch data with standardized field names
            formatted_branches = []
            for branch in branches:
                # Extract branch information from FDIC Locations API fields
                branch_info = {
                    'name': branch.get('OFFNAME') or branch.get('NAME') or '',
                    'address': branch.get('ADDRESS') or branch.get('ADDR') or '',
                    'address2': branch.get('ADDRESS2') or '',
                    'city': branch.get('CITY') or '',
                    'state': branch.get('STALP') or branch.get('STATE') or '',
                    'state_name': branch.get('STNAME') or '',
                    'zip': branch.get('ZIP') or branch.get('ZIPCODE') or '',
                    'county': branch.get('COUNTY') or '',
                    'latitude': branch.get('LATITUDE'),
                    'longitude': branch.get('LONGITUDE'),
                    'cbsa_code': branch.get('CBSA_NO') or '',
                    'cbsa_name': branch.get('CBSA_METRO_NAME') or branch.get('CBSA_MICRO_NAME') or '',
                    'acquisition_date': branch.get('ACQDATE') or '',
                    'year': year,  # Use requested year
                    'cert': branch.get('CERT') or cert,
                    'raw': branch  # Keep raw data for reference
                }
                
                # Only include if it has location info (city or state)
                if branch_info['city'] or branch_info['state']:
                    formatted_branches.append(branch_info)
            
            # Use the actual returned count as the total (API total_available is often wrong/aggregated)
            actual_count = len(formatted_branches)
            metadata = {
                'total_available': actual_count,  # Use actual returned count
                'returned': actual_count,
                'hit_limit': actual_count >= 10000
            }
            
            logger.info(f"FDIC Summary API returned {len(formatted_branches)} formatted branches for cert {cert} (year: {year})")
            return formatted_branches, metadata
            
        except requests.exceptions.RequestException as e:
            logger.error(f"FDIC API error getting branches for {cert}: {e}")
            return [], {'total_available': 0, 'returned': 0, 'hit_limit': False}
        except Exception as e:
            logger.error(f"Error processing FDIC branch data: {e}", exc_info=True)
            return [], {'total_available': 0, 'returned': 0, 'hit_limit': False}

