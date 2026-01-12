#!/usr/bin/env python3
"""
Regulations.gov API Client
Fetches comment letters on proposed regulations.

API Documentation: https://open.gsa.gov/api/regulationsgov/
Base URL: https://api.regulations.gov/v4/
"""

import requests
import logging
from typing import Optional, Dict, Any, List
from shared.utils.unified_env import get_unified_config

logger = logging.getLogger(__name__)


class RegulationsGovClient:
    """
    Client for Regulations.gov API.
    
    Base URL: https://api.regulations.gov/v4/
    Authentication: API key in X-Api-Key header
    Rate Limits: See https://api.data.gov/docs/rate-limits/
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Regulations.gov API client.
        
        Args:
            api_key: API key (or from unified_env if not provided)
        """
        self.base_url = 'https://api.regulations.gov/v4'
        self.timeout = 30
        
        if not api_key:
            config = get_unified_config(load_env=True, verbose=False)
            api_key = config.get('REGULATIONS_GOV_API_KEY')
        
        self.api_key = api_key
        if not self.api_key:
            logger.warning("Regulations.gov API key not set, skipping search")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with API key."""
        headers = {}
        if self.api_key:
            headers['X-Api-Key'] = self.api_key
        return headers
    
    def search_comments(self, docket_id: Optional[str] = None,
                       search_term: Optional[str] = None,
                       organization_name: Optional[str] = None,
                       comment_on_id: Optional[str] = None,
                       limit: int = 20,
                       page_number: int = 1) -> Dict[str, Any]:
        """
        Search for comment letters using Regulations.gov v4 API.
        
        API Documentation: https://open.gsa.gov/api/regulationsgov/
        
        Args:
            docket_id: Optional docket ID (e.g., "EPA-HQ-OAR-2003-0129")
            search_term: Optional full-text search term
            organization_name: Optional organization name filter
            comment_on_id: Optional document objectId to get comments for a specific document
            limit: Maximum number of results per page (max 250, default 20)
            page_number: Page number (default 1)
            
        Returns:
            Dictionary with 'data' (list of comments) and 'meta' (pagination info)
        """
        if not self.api_key:
            logger.warning("Regulations.gov API key not set, skipping search")
            return {'data': [], 'meta': {}}
        
        try:
            url = f'{self.base_url}/comments'
            params = {
                'page[size]': min(limit, 250),  # API max is 250
                'page[number]': page_number
            }
            
            # Build filters according to API documentation
            if docket_id:
                params['filter[docketId]'] = docket_id
            if search_term:
                params['filter[searchTerm]'] = search_term
            if organization_name:
                # According to docs, organization is in agency configurable fields
                params['filter[organization]'] = organization_name
            if comment_on_id:
                # Use objectId from document to get comments for that document
                params['filter[commentOnId]'] = comment_on_id
            
            logger.info(f"Regulations.gov API request: {url} with params: {params}")
            response = requests.get(
                url,
                params=params,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            logger.info(f"Regulations.gov API response status: {response.status_code}")
            response.raise_for_status()
            
            data = response.json()
            comments = data.get('data', [])
            meta = data.get('meta', {})
            
            logger.info(f"Regulations.gov API returned {len(comments)} comments (total: {meta.get('totalElements', 'unknown')})")
            
            return {
                'data': comments,
                'meta': meta
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Regulations.gov API error: {e}", exc_info=True)
            return {'data': [], 'meta': {}}
    
    def search_documents(self, search_term: Optional[str] = None,
                        docket_id: Optional[str] = None,
                        agency_id: Optional[str] = None,
                        limit: int = 20,
                        page_number: int = 1) -> Dict[str, Any]:
        """
        Search for documents (proposed rules, rules, etc.).
        
        Args:
            search_term: Optional full-text search term
            docket_id: Optional docket ID
            agency_id: Optional agency ID (e.g., "EPA", "GSA")
            limit: Maximum number of results per page (max 250)
            page_number: Page number
            
        Returns:
            Dictionary with 'data' (list of documents) and 'meta' (pagination info)
        """
        if not self.api_key:
            logger.warning("Regulations.gov API key not set, skipping search")
            return {'data': [], 'meta': {}}
        
        try:
            url = f'{self.base_url}/documents'
            params = {
                'page[size]': min(limit, 250),
                'page[number]': page_number
            }
            
            if search_term:
                params['filter[searchTerm]'] = search_term
            if docket_id:
                params['filter[docketId]'] = docket_id
            if agency_id:
                params['filter[agencyId]'] = agency_id
            
            response = requests.get(
                url,
                params=params,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            return {
                'data': data.get('data', []),
                'meta': data.get('meta', {})
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Regulations.gov API error searching documents: {e}")
            return {'data': [], 'meta': {}}
    
    def search_dockets(self, search_term: Optional[str] = None,
                      agency_id: Optional[str] = None,
                      limit: int = 20) -> Dict[str, Any]:
        """
        Search for dockets.
        
        Args:
            search_term: Optional full-text search term
            agency_id: Optional agency ID or comma-separated list (e.g., "GSA,EPA")
            limit: Maximum number of results
            
        Returns:
            Dictionary with 'data' (list of dockets) and 'meta' (pagination info)
        """
        if not self.api_key:
            logger.warning("Regulations.gov API key not set, skipping search")
            return {'data': [], 'meta': {}}
        
        try:
            url = f'{self.base_url}/dockets'
            params = {'page[size]': min(limit, 250)}
            
            if search_term:
                params['filter[searchTerm]'] = search_term
            if agency_id:
                params['filter[agencyId]'] = agency_id
            
            response = requests.get(
                url,
                params=params,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            return {
                'data': data.get('data', []),
                'meta': data.get('meta', {})
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Regulations.gov API error searching dockets: {e}")
            return {'data': [], 'meta': {}}

