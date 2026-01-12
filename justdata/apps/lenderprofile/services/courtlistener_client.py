#!/usr/bin/env python3
"""
CourtListener API Client
Searches federal court litigation and case details.
"""

import requests
import logging
from typing import Optional, Dict, Any, List
from justdata.shared.utils.unified_env import get_unified_config

logger = logging.getLogger(__name__)


class CourtListenerClient:
    """
    Client for CourtListener API.
    
    Base URL: https://www.courtlistener.com/api/rest/v4/
    Authentication: Token in Authorization header
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize CourtListener API client.
        
        Args:
            api_key: API key (or from unified_env if not provided)
        """
        self.base_url = 'https://www.courtlistener.com/api/rest/v4'
        self.timeout = 30
        
        if not api_key:
            config = get_unified_config(load_env=True, verbose=False)
            api_key = config.get('COURTLISTENER_API_KEY')
        
        self.api_key = api_key
        if not self.api_key:
            logger.warning("CourtListener API key not set, skipping search")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Token {self.api_key}'
        return headers
    
    def search_dockets(self, query: str, filed_after: Optional[str] = None, 
                     limit: int = 20, ordering: str = '-date_created') -> List[Dict[str, Any]]:
        """
        Search for dockets (cases).
        
        Tries multiple search strategies:
        1. Exact company name
        2. Company name with variations
        3. Original query
        
        Args:
            query: Search query (party name, description, etc.)
            filed_after: Filter by filing date (YYYY-MM-DD)
            limit: Maximum number of results
            ordering: Sort order (default: '-date_created' for most recent first)
            
        Returns:
            List of matching dockets
        """
        if not self.api_key:
            logger.warning("CourtListener API key not set, skipping search")
            return []
        
        # Build query variations
        query_variations = []
        
        # Try exact company name (uppercase, as it appears in case names)
        query_upper = query.upper()
        query_variations.append(query_upper)
        
        # Try with "Financial Services" if it's a bank
        if 'Bank' in query:
            financial_name = query.replace(' Bank', ' Financial Services').upper()
            query_variations.append(financial_name)
            query_variations.append(f'{query_upper} FINANCIAL SERVICES')
        
        # Add original query
        if query not in query_variations:
            query_variations.append(query)
        
        # Remove duplicates while preserving order
        seen = set()
        query_variations = [q for q in query_variations if q not in seen and not seen.add(q)]
        
        all_results = []
        seen_docket_ids = set()
        
        for search_query in query_variations:
            try:
                url = f'{self.base_url}/search/'
                params = {
                    'type': 'r',  # r = docket
                    'q': search_query,
                    'page_size': min(limit, 100),  # API limit is 100
                    'ordering': ordering
                }
                
                if filed_after:
                    params['filed_after'] = filed_after
                
                logger.debug(f"CourtListener search: {url} with query '{search_query}'")
                response = requests.get(
                    url,
                    params=params,
                    headers=self._get_headers(),
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                data = response.json()
                results = data.get('results', [])
                
                # Add results, avoiding duplicates
                for result in results:
                    docket_id = result.get('docket_id')
                    if docket_id and docket_id not in seen_docket_ids:
                        seen_docket_ids.add(docket_id)
                        all_results.append(result)
                
                # If we got good results, we can stop
                if len(all_results) >= limit:
                    break
                    
            except requests.exceptions.RequestException as e:
                logger.debug(f"CourtListener API error with query '{search_query}': {e}")
                continue
        
        # Return up to limit results
        return all_results[:limit]
    
    def get_docket(self, docket_id: int) -> Optional[Dict[str, Any]]:
        """
        Get docket details by ID.
        
        Args:
            docket_id: Docket ID
            
        Returns:
            Docket details or None
        """
        if not self.api_key:
            logger.warning("CourtListener API key not set, skipping request")
            return None
        
        try:
            url = f'{self.base_url}/dockets/{docket_id}/'
            
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"CourtListener API error getting docket {docket_id}: {e}")
            return None
    
    def search_parties(self, name: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for parties (individuals/entities) in cases.
        
        Note: Parties endpoint may return 403 (forbidden) depending on API key permissions.
        Falls back to searching dockets and extracting party information.
        
        Args:
            name: Party name to search for
            limit: Maximum number of results
            
        Returns:
            List of matching parties (or empty list if endpoint unavailable)
        """
        if not self.api_key:
            logger.warning("CourtListener API key not set, skipping search")
            return []
        
        try:
            url = f'{self.base_url}/parties/'
            params = {
                'name': name,
                'page_size': limit,
                'ordering': '-date_created'
            }
            
            response = requests.get(
                url,
                params=params,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            # If 403, parties endpoint not available - that's okay, we can use docket search
            if response.status_code == 403:
                logger.debug("CourtListener parties endpoint returns 403 - using docket search instead")
                # Fallback: search dockets and extract party info
                dockets = self.search_dockets(name, limit=limit)
                parties = []
                for docket in dockets:
                    party_names = docket.get('party', [])
                    for party_name in party_names:
                        if name.upper() in party_name.upper():
                            parties.append({
                                'name': party_name,
                                'docket_id': docket.get('docket_id'),
                                'case_name': docket.get('caseName'),
                                'court': docket.get('court'),
                                'date_filed': docket.get('dateFiled')
                            })
                return parties[:limit]
            
            response.raise_for_status()
            
            data = response.json()
            return data.get('results', [])
            
        except requests.exceptions.RequestException as e:
            logger.debug(f"CourtListener API error searching parties '{name}': {e}")
            # Fallback to docket search
            dockets = self.search_dockets(name, limit=limit)
            parties = []
            for docket in dockets:
                party_names = docket.get('party', [])
                for party_name in party_names:
                    if name.upper() in party_name.upper():
                        parties.append({
                            'name': party_name,
                            'docket_id': docket.get('docket_id'),
                            'case_name': docket.get('caseName'),
                            'court': docket.get('court'),
                            'date_filed': docket.get('dateFiled')
                        })
            return parties[:limit]

