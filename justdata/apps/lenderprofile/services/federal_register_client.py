#!/usr/bin/env python3
"""
Federal Register API Client
Fetches bank merger applications and regulatory proposals.
"""

import requests
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class FederalRegisterClient:
    """
    Client for Federal Register API.
    
    Base URL: https://www.federalregister.gov/api/v1/
    Documentation: https://www.federalregister.gov/developers/documentation/api/v1
    """
    
    def __init__(self):
        """Initialize Federal Register API client."""
        self.base_url = 'https://www.federalregister.gov/api/v1'
        self.timeout = 30
    
    def search_documents(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for documents.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching documents
        """
        try:
            url = f'{self.base_url}/documents.json'
            params = {
                'conditions[term]': query,
                'per_page': limit
            }
            
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            return data.get('results', [])
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Federal Register API error searching '{query}': {e}")
            return []
    
    def search_merger_notices(self, institution_name: str) -> List[Dict[str, Any]]:
        """
        Search for bank merger application notices.
        
        Args:
            institution_name: Institution name
            
        Returns:
            List of merger notices
        """
        query = f'"bank merger" AND "{institution_name}"'
        return self.search_documents(query)

