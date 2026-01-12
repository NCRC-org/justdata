#!/usr/bin/env python3
"""
TheOrg API Client
Fetches organizational charts and leadership structure.
"""

import requests
import logging
from typing import Optional, Dict, Any, List
from shared.utils.unified_env import get_unified_config

logger = logging.getLogger(__name__)


class TheOrgClient:
    """
    Client for TheOrg API.
    
    Base URL: https://api.theorg.com/v2/
    Authentication: Bearer token in Authorization header
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize TheOrg API client.
        
        Args:
            api_key: API key (or from unified_env if not provided)
        """
        self.base_url = 'https://api.theorg.com/v2'
        self.timeout = 30
        
        if not api_key:
            config = get_unified_config(load_env=True, verbose=False)
            api_key = config.get('THEORG_API_KEY')
        
        self.api_key = api_key
        if not self.api_key:
            logger.warning("TheOrg API key not set, skipping search")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        return headers
    
    def search_companies(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for companies by name.
        
        Tries multiple search strategies:
        1. Direct search with query
        2. Search with variations (removing "Bank", "Inc", etc.)
        3. Try constructing slug from name
        
        Args:
            query: Company name to search for
            limit: Maximum number of results
            
        Returns:
            List of matching companies
        """
        if not self.api_key:
            logger.warning("TheOrg API key not set, skipping search")
            return []
        
        # Try different search variations
        search_queries = [
            query,  # Original
            query.replace(' Bank', '').replace(' BANK', ''),  # Remove "Bank"
            query.replace(' Bank, National Association', '').replace(' BANK, NATIONAL ASSOCIATION', ''),
            query.replace(', National Association', '').replace(', NATIONAL ASSOCIATION', ''),
            query.replace(' Inc', '').replace(' INC', '').replace(' Inc.', '').replace(' INC.', ''),
            query.replace(' Financial Services', '').replace(' FINANCIAL SERVICES', ''),
        ]
        
        # Remove duplicates while preserving order
        seen = set()
        search_queries = [q for q in search_queries if q and q not in seen and not seen.add(q)]
        
        for search_query in search_queries:
            try:
                url = f'{self.base_url}/companies/search'
                params = {'q': search_query}
                
                logger.debug(f"TheOrg API search: {url} with params: {params}")
                response = requests.get(
                    url,
                    params=params,
                    headers=self._get_headers(),
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    results = data if isinstance(data, list) else []
                    if results:
                        logger.info(f"TheOrg API found {len(results)} results for '{search_query}'")
                        return results[:limit]
                elif response.status_code == 404:
                    logger.debug(f"TheOrg API returned 404 for '{search_query}', trying next variation")
                    continue
                else:
                    response.raise_for_status()
                    
            except requests.exceptions.RequestException as e:
                logger.debug(f"TheOrg API error searching '{search_query}': {e}")
                continue
        
        # If all searches failed, try to construct slug and get company directly
        # Slug format: lowercase, replace spaces with dashes, remove special chars
        slug_candidates = [
            query.lower().replace(' ', '-').replace(',', '').replace('.', '').replace(' inc', '').replace(' bank', ''),
            query.lower().replace(' ', '-').replace(',', '').replace('.', '').replace(' financial services', ''),
            'pnc-financial-services',  # Known slug for PNC
            'pnc-bank',
        ]
        
        for slug in slug_candidates:
            try:
                company = self.get_company(slug)
                if company:
                    logger.info(f"Found company via slug '{slug}'")
                    return [company]
            except Exception:
                continue
        
        logger.warning(f"TheOrg API could not find company for '{query}' after trying all variations")
        return []
    
    def get_company(self, slug: str) -> Optional[Dict[str, Any]]:
        """
        Get company details by slug.
        
        Args:
            slug: Company slug (e.g., 'pnc-bank')
            
        Returns:
            Company details or None
        """
        if not self.api_key:
            logger.warning("TheOrg API key not set, skipping request")
            return None
        
        try:
            url = f'{self.base_url}/companies/{slug}'
            
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"TheOrg API error getting company {slug}: {e}")
            return None
    
    def get_org_chart(self, slug: str) -> Optional[Dict[str, Any]]:
        """
        Get organizational chart for a company.
        
        Args:
            slug: Company slug
            
        Returns:
            Organizational chart data or None
        """
        if not self.api_key:
            logger.warning("TheOrg API key not set, skipping request")
            return None
        
        try:
            url = f'{self.base_url}/companies/{slug}/org-chart'
            
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"TheOrg API error getting org chart for {slug}: {e}")
            return None
    
    def get_company_people(self, slug: str) -> List[Dict[str, Any]]:
        """
        Get all people at a company.
        
        Args:
            slug: Company slug
            
        Returns:
            List of people
        """
        if not self.api_key:
            logger.warning("TheOrg API key not set, skipping request")
            return []
        
        try:
            url = f'{self.base_url}/companies/{slug}/people'
            
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            return data if isinstance(data, list) else []
            
        except requests.exceptions.RequestException as e:
            logger.error(f"TheOrg API error getting people for {slug}: {e}")
            return []
    
    def get_person(self, person_id: str) -> Optional[Dict[str, Any]]:
        """
        Get person details by ID.
        
        Args:
            person_id: Person ID
            
        Returns:
            Person details or None
        """
        if not self.api_key:
            logger.warning("TheOrg API key not set, skipping request")
            return None
        
        try:
            url = f'{self.base_url}/people/{person_id}'
            
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"TheOrg API error getting person {person_id}: {e}")
            return None

