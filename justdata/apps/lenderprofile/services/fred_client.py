#!/usr/bin/env python3
"""
FRED (Federal Reserve Economic Data) API Client
Fetches economic context data (optional).
"""

import requests
import logging
from typing import Optional, Dict, Any, List
from justdata.shared.utils.unified_env import get_unified_config

logger = logging.getLogger(__name__)


class FREDClient:
    """
    Client for FRED API.
    
    Base URL: https://api.stlouisfed.org/fred/
    Authentication: API key as query parameter
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize FRED API client.
        
        Args:
            api_key: API key (or from unified_env if not provided)
        """
        self.base_url = 'https://api.stlouisfed.org/fred'
        self.timeout = 30
        
        if not api_key:
            config = get_unified_config()
            api_key = config.get('FRED_API_KEY')
        
        self.api_key = api_key
        if not self.api_key:
            logger.warning("FRED API key not set")
    
    def _get_params(self) -> Dict[str, str]:
        """Get request parameters with API key."""
        params = {}
        if self.api_key:
            params['api_key'] = self.api_key
        return params
    
    def get_series(self, series_id: str, start_date: Optional[str] = None,
                   end_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get economic data series.
        
        Args:
            series_id: FRED series ID (e.g., 'FEDFUNDS' for federal funds rate)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            Series data or None
        """
        if not self.api_key:
            logger.warning("FRED API key not set, skipping request")
            return None
        
        try:
            url = f'{self.base_url}/series/observations'
            params = self._get_params()
            params['series_id'] = series_id
            params['file_type'] = 'json'
            
            if start_date:
                params['observation_start'] = start_date
            if end_date:
                params['observation_end'] = end_date
            
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"FRED API error getting series {series_id}: {e}")
            return None

