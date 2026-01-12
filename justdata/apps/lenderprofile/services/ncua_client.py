#!/usr/bin/env python3
"""
NCUA API Client
Fetches credit union financial data and branch locations.
"""

import requests
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class NCUAClient:
    """
    Client for NCUA API.
    
    Base URL: https://mapping.ncua.gov/api/
    """
    
    def __init__(self):
        """Initialize NCUA API client."""
        self.base_url = 'https://mapping.ncua.gov/api'
        self.timeout = 30
    
    def search_credit_unions(self, name: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for credit unions by name.
        
        Args:
            name: Credit union name
            limit: Maximum number of results
            
        Returns:
            List of matching credit unions
        """
        try:
            # NCUA API endpoint structure may vary
            # This is a placeholder implementation
            url = f'{self.base_url}/credit-unions'
            params = {
                'name': name,
                'limit': limit
            }
            
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            return data if isinstance(data, list) else []
            
        except requests.exceptions.RequestException as e:
            logger.error(f"NCUA API error searching for '{name}': {e}")
            return []
    
    def get_credit_union(self, cu_number: str) -> Optional[Dict[str, Any]]:
        """
        Get credit union details.
        
        Args:
            cu_number: Credit union number
            
        Returns:
            Credit union details or None
        """
        try:
            url = f'{self.base_url}/credit-unions/{cu_number}'
            
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"NCUA API error getting credit union {cu_number}: {e}")
            return None

