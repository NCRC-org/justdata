#!/usr/bin/env python3
"""
CFPB HMDA API Client
Gets institution metadata (name, LEI, RSSD) for linking to BigQuery data sources.
"""

import requests
import os
import logging
from typing import Optional, Dict, List
from time import time
from functools import wraps

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Raised when API rate limit is exceeded"""
    pass


class RateLimiter:
    """Simple rate limiter for API calls"""
    def __init__(self, max_calls: int, period: int):
        self.max_calls = max_calls
        self.period = period
        self.calls = []
    
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time()
            self.calls = [c for c in self.calls if c > now - self.period]
            
            if len(self.calls) >= self.max_calls:
                raise RateLimitError(f"Rate limit exceeded: {self.max_calls} calls per {self.period} seconds")
            
            self.calls.append(now)
            return func(*args, **kwargs)
        return wrapper


class CFPBClient:
    """
    Client for CFPB HMDA APIs.
    
    Primary purpose: Get institution metadata (name, LEI, RSSD) that can be used
    to query BigQuery data sources (HMDA, SOD25, Disclosure, lenders tables).
    """
    
    def __init__(self, bearer_token: Optional[str] = None, enabled: bool = None):
        """
        Initialize CFPB API client.
        
        Args:
            bearer_token: CFPB bearer token (or from CFPB_BEARER_TOKEN env var)
            enabled: Whether CFPB API is enabled (or from CFPB_API_ENABLED env var)
        """
        self.bearer_token = bearer_token or os.getenv('CFPB_BEARER_TOKEN')
        self.enabled = enabled if enabled is not None else os.getenv('CFPB_API_ENABLED', 'false').lower() == 'true'
        self.timeout = int(os.getenv('CFPB_API_TIMEOUT', '30'))
        
        self.auth_base = 'https://ffiec.cfpb.gov/hmda-auth'
        self.platform_base = 'https://ffiec.cfpb.gov/hmda-platform'
        
        # Rate limiter: 100 calls per minute (adjust based on API limits)
        self.rate_limiter = RateLimiter(max_calls=100, period=60)
        
    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers"""
        if not self.bearer_token:
            raise ValueError("CFPB Bearer Token required. Set CFPB_BEARER_TOKEN environment variable.")
        return {
            'Authorization': f'Bearer {self.bearer_token}',
            'Content-Type': 'application/json'
        }
    
    def _is_enabled(self) -> bool:
        """Check if CFPB API is enabled"""
        return self.enabled and self.bearer_token is not None
    
    @RateLimiter(max_calls=100, period=60)
    def get_user_info(self) -> Dict:
        """
        Get current user information from CFPB API.
        
        Returns:
            User information dictionary
        """
        if not self._is_enabled():
            raise ValueError("CFPB API not enabled or token not configured")
        
        try:
            response = requests.get(
                f'{self.auth_base}/users/',
                headers=self._get_headers(),
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"CFPB API error getting user info: {e}")
            raise
    
    @RateLimiter(max_calls=100, period=60)
    def get_institutions_by_domain(self, email_domain: str) -> List[Dict]:
        """
        Get institutions associated with email domain.
        
        Args:
            email_domain: Email domain (e.g., 'wellsfargo.com')
            
        Returns:
            List of institution dictionaries with name, LEI, RSSD
        """
        if not self._is_enabled():
            raise ValueError("CFPB API not enabled or token not configured")
        
        try:
            response = requests.get(
                f'{self.auth_base}/v2/public/institutions',
                params={'domain': email_domain},
                headers=self._get_headers(),
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"CFPB API error getting institutions by domain: {e}")
            raise
    
    def search_institutions(self, query: str, limit: int = 20, year: int = None) -> List[Dict]:
        """
        Search institutions by name (for autocomplete/search).
        Returns multiple matching institutions with RSSD.
        
        Uses CFPB HMDA API endpoints:
        - /v2/reporting/filers/{year} - Get all institutions for a year
        - /v2/public/institutions/{lei}/year/{year} - Get institution details by LEI
        
        Args:
            query: Search query (institution name or partial name)
            limit: Maximum number of results to return
            year: Year to search (defaults to most recent available, typically 2024)
            
        Returns:
            List of institution dictionaries with name, LEI, RSSD, etc.
        """
        if not self._is_enabled():
            logger.debug("CFPB API not enabled, skipping institution search")
            return []
        
        try:
            # Use most recent year if not specified
            if year is None:
                year = 2024  # Most recent HMDA data year
            
            # Get all filers for the year
            # Note: This endpoint may require different base URL (reporting API vs auth API)
            response = requests.get(
                f'https://ffiec.cfpb.gov/v2/reporting/filers/{year}',
                headers=self._get_headers(),
                timeout=self.timeout
            )
            response.raise_for_status()
            filers = response.json()
            
            # Handle different response formats
            if isinstance(filers, dict):
                filers_list = filers.get('results', filers.get('filers', filers.get('institutions', [])))
            else:
                filers_list = filers if isinstance(filers, list) else []
            
            # Filter by name (case-insensitive partial match)
            query_lower = query.lower()
            matching_filers = []
            
            for filer in filers_list:
                name = filer.get('name') or filer.get('institutionName') or filer.get('institution_name', '')
                if query_lower in name.lower():
                    matching_filers.append(filer)
                    if len(matching_filers) >= limit:
                        break
            
            # Get detailed information for each match (to get RSSD)
            formatted_results = []
            for filer in matching_filers[:limit]:
                lei = filer.get('lei')
                if not lei:
                    # If no LEI in filer response, use what we have
                    formatted_results.append({
                        'name': filer.get('name') or filer.get('institutionName') or filer.get('institution_name'),
                        'lei': filer.get('lei'),
                        'rssd': filer.get('rssd') or filer.get('rssdId') or filer.get('rssd_id'),
                        'type': filer.get('type') or filer.get('institutionType'),
                        'city': filer.get('city'),
                        'state': filer.get('state'),
                        'source': 'cfpb_api'
                    })
                    continue
                
                # Get detailed institution info by LEI to retrieve RSSD and assets
                try:
                    inst_response = requests.get(
                        f'https://ffiec.cfpb.gov/v2/public/institutions/{lei}/year/{year}',
                        headers=self._get_headers(),
                        timeout=self.timeout
                    )
                    inst_response.raise_for_status()
                    institution = inst_response.json()
                    
                    # Extract assets from various possible field names
                    assets = (institution.get('assets') or 
                             institution.get('total_assets') or
                             institution.get('asset_size') or
                             institution.get('assetSize') or
                             institution.get('totalAssets') or
                             institution.get('assetSizeCategory'))
                    
                    formatted_results.append({
                        'name': institution.get('name') or institution.get('institutionName') or filer.get('name'),
                        'lei': institution.get('lei') or lei,
                        'rssd': institution.get('rssd') or institution.get('rssdId') or institution.get('rssd_id'),
                        'type': institution.get('type') or institution.get('institutionType'),
                        'city': institution.get('city'),
                        'state': institution.get('state'),
                        'assets': assets,
                        'source': 'cfpb_api'
                    })
                except requests.exceptions.RequestException as e:
                    logger.debug(f"Could not get details for LEI {lei}: {e}")
                    # Fallback to filer data
                    formatted_results.append({
                        'name': filer.get('name') or filer.get('institutionName'),
                        'lei': lei,
                        'rssd': filer.get('rssd') or filer.get('rssdId'),
                        'type': filer.get('type'),
                        'city': filer.get('city'),
                        'state': filer.get('state'),
                        'source': 'cfpb_api'
                    })
            
            return formatted_results
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"CFPB API error searching institutions: {e}")
            return []
    
    def get_institution_by_name(self, name: str, year: int = None) -> Optional[Dict]:
        """
        Get institution metadata (name, LEI, RSSD) by name.
        
        This is the primary method for DataExplorer lender lookup.
        Uses CFPB API to get authoritative institution identifiers,
        which are then used to query BigQuery data sources.
        
        Args:
            name: Institution name (e.g., "Wells Fargo")
            year: Year to search (defaults to 2024)
            
        Returns:
            Institution dictionary with:
            {
                'name': 'Wells Fargo Bank, NA',
                'lei': 'INR2EJN1ERAN0W5ZP974',
                'rssd': '451965',
                'type': 'Bank',
                ...
            }
            Returns None if not found or API unavailable
        """
        if not self._is_enabled():
            logger.debug("CFPB API not enabled, skipping institution lookup")
            return None
        
        try:
            # Use search_institutions and return first result
            results = self.search_institutions(name, limit=1, year=year)
            if results and len(results) > 0:
                return results[0]
            return None
            
        except Exception as e:
            logger.warning(f"CFPB API error getting institution by name: {e}")
            return None
    
    def get_institution_by_lei(self, lei: str) -> Optional[Dict]:
        """
        Get institution metadata by LEI.
        
        Args:
            lei: Legal Entity Identifier
            
        Returns:
            Institution dictionary or None
        """
        if not self._is_enabled():
            return None
        
        try:
            response = requests.get(
                f'{self.auth_base}/v2/public/institutions',
                params={'lei': lei},
                headers=self._get_headers(),
                timeout=self.timeout
            )
            response.raise_for_status()
            results = response.json()
            
            if results and len(results) > 0:
                institution = results[0]
                # Extract assets from various possible field names
                assets = (institution.get('assets') or 
                         institution.get('total_assets') or
                         institution.get('asset_size') or
                         institution.get('assetSize') or
                         institution.get('totalAssets') or
                         institution.get('assetSizeCategory'))
                return {
                    'name': institution.get('name'),
                    'lei': institution.get('lei'),
                    'rssd': institution.get('rssd') or institution.get('rssd_id'),
                    'type': institution.get('type'),
                    'assets': assets,
                    'source': 'cfpb_api'
                }
            
            return None
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"CFPB API error getting institution by LEI: {e}")
            return None
    
    def get_institution_by_rssd(self, rssd: str) -> Optional[Dict]:
        """
        Get institution metadata by RSSD ID.
        
        Args:
            rssd: Federal Reserve System ID
            
        Returns:
            Institution dictionary or None
        """
        if not self._is_enabled():
            return None
        
        try:
            response = requests.get(
                f'{self.auth_base}/v2/public/institutions',
                params={'rssd': rssd},
                headers=self._get_headers(),
                timeout=self.timeout
            )
            response.raise_for_status()
            results = response.json()
            
            if results and len(results) > 0:
                institution = results[0]
                # Extract assets from various possible field names
                assets = (institution.get('assets') or 
                         institution.get('total_assets') or
                         institution.get('asset_size') or
                         institution.get('assetSize') or
                         institution.get('totalAssets') or
                         institution.get('assetSizeCategory'))
                return {
                    'name': institution.get('name'),
                    'lei': institution.get('lei'),
                    'rssd': institution.get('rssd') or institution.get('rssd_id'),
                    'type': institution.get('type'),
                    'assets': assets,
                    'source': 'cfpb_api'
                }
            
            return None
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"CFPB API error getting institution by RSSD: {e}")
            return None
