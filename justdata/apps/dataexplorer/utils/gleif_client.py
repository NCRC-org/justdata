#!/usr/bin/env python3
"""
GLEIF (Global Legal Entity Identifier Foundation) API Client
Fetches lender headquarters and entity information for verification.
"""

import requests
import os
import logging
import json
from typing import Optional, Dict, Any
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


class GLEIFClient:
    """
    Client for GLEIF API to verify LEI and get entity information.
    
    GLEIF provides authoritative data about legal entities including:
    - Legal name
    - Headquarters location (city, state, country)
    - Registration status
    - Entity status (active/inactive)
    - Legal address
    
    This is used to verify that the correct lender is selected when
    there are multiple similarly named institutions (e.g., multiple Citizens Banks).
    """
    
    def __init__(self, enabled: bool = None):
        """
        Initialize GLEIF API client.
        
        Args:
            enabled: Whether GLEIF API is enabled (or from GLEIF_API_ENABLED env var)
        """
        self.enabled = enabled if enabled is not None else os.getenv('GLEIF_API_ENABLED', 'true').lower() == 'true'
        self.timeout = int(os.getenv('GLEIF_API_TIMEOUT', '30'))
        
        # GLEIF API endpoints
        self.base_url = 'https://api.gleif.org/api/v1'
        
        # Rate limiter: 100 calls per minute (GLEIF allows 1000/hour, so 100/min is safe)
        self.rate_limiter = RateLimiter(max_calls=100, period=60)
    
    def _is_enabled(self) -> bool:
        """Check if GLEIF API is enabled"""
        return self.enabled
    
    @RateLimiter(max_calls=100, period=60)
    def verify_lei(self, lei: str, expected_name: str = None) -> Dict[str, Any]:
        """
        Verify LEI and get entity information from GLEIF.
        
        Args:
            lei: Legal Entity Identifier (20 characters)
            expected_name: Expected lender name for verification
            
        Returns:
            Dictionary with:
            {
                'entity': {
                    'lei': '...',
                    'legalName': '...',
                    'legalAddress': {
                        'city': '...',
                        'region': '...',
                        'country': '...'
                    },
                    'status': 'ACTIVE' | 'INACTIVE',
                    'registrationStatus': 'ISSUED' | 'LAPSED' | 'PENDING'
                },
                'is_active': bool,
                'name_match': bool,  # True if expected_name matches legalName
                'headquarters': {
                    'city': '...',
                    'state': '...',
                    'country': '...'
                }
            }
        """
        if not self._is_enabled():
            logger.debug("GLEIF API not enabled")
            return {
                'entity': None,
                'is_active': False,
                'name_match': False,
                'headquarters': {}
            }
        
        if not lei or len(lei.strip()) != 20:
            logger.warning(f"Invalid LEI format: {lei}")
            return {
                'entity': None,
                'is_active': False,
                'name_match': False,
                'headquarters': {}
            }
        
        try:
            # GLEIF API endpoint for LEI record
            url = f'{self.base_url}/lei-records/{lei.strip().upper()}'
            
            response = requests.get(
                url,
                headers={'Accept': 'application/vnd.api+json'},
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Parse GLEIF response structure
            # GLEIF uses JSON API format
            if 'data' in data and 'attributes' in data['data']:
                attributes = data['data']['attributes']
                entity = attributes.get('entity', {})
                
                # GLEIF API structure: legalAddress is nested in entity
                legal_address = entity.get('legalAddress', {})
                
                # Also check for headquarters address (some records have this)
                headquarters_address = entity.get('headquartersAddress', legal_address)
                
                # Use headquarters address if available, otherwise use legal address
                address_source = headquarters_address if headquarters_address != legal_address else legal_address
                
                # Extract legal name
                legal_name_obj = entity.get('legalName', {})
                if isinstance(legal_name_obj, dict):
                    legal_name = legal_name_obj.get('name', '')
                elif isinstance(legal_name_obj, str):
                    legal_name = legal_name_obj
                else:
                    legal_name = ''
                
                # Extract headquarters location from address
                # GLEIF API may have city, region (state), country, postalCode, addressLines
                # Filter out "0" values and empty strings
                def clean_value(val):
                    """Clean value - return empty string if None, empty, or "0" """
                    if not val or val == '0' or val == 0:
                        return ''
                    return str(val).strip()
                
                headquarters = {
                    'city': clean_value(address_source.get('city', '')),
                    'region': clean_value(address_source.get('region', '')),
                    'country': clean_value(address_source.get('country', '')),
                    'postal_code': clean_value(address_source.get('postalCode', '') or address_source.get('postal_code', '')),
                    'address_lines': address_source.get('addressLines', []) or address_source.get('address_lines', []) or []
                }
                
                # Try to extract city/state from address lines if not in separate fields
                if not headquarters['city'] and headquarters['address_lines']:
                    # Try to parse city from address lines (usually last line before postal code)
                    address_text = ' '.join(headquarters['address_lines'])
                    # Look for common patterns like "City, ST" or "City, State"
                    import re
                    # Pattern: City, ST (two-letter state)
                    city_state_match = re.search(r'([A-Za-z\s]+),\s*([A-Z]{2})\s*\d{5}', address_text)
                    if city_state_match:
                        headquarters['city'] = city_state_match.group(1).strip()
                        headquarters['region'] = city_state_match.group(2).strip()
                    else:
                        # Try to extract from last address line
                        last_line = headquarters['address_lines'][-1] if headquarters['address_lines'] else ''
                        parts = last_line.split(',')
                        if len(parts) >= 2:
                            headquarters['city'] = parts[0].strip()
                            # Check if second part is state (2-3 letters) or state + zip
                            state_part = parts[1].strip()
                            state_match = re.match(r'([A-Z]{2,3})', state_part)
                            if state_match:
                                headquarters['region'] = state_match.group(1).strip()
                
                # Log for debugging if city/state are still missing
                if not headquarters['city'] and not headquarters['region']:
                    logger.warning(f"GLEIF address data missing city/state for LEI {lei}. Full address data: {address_source}")
                    # Try to log the full entity structure for debugging
                    logger.debug(f"Full GLEIF entity structure for LEI {lei}: {json.dumps(entity, indent=2, default=str)}")
                else:
                    logger.info(f"GLEIF extracted headquarters: {headquarters['city']}, {headquarters['region']} for LEI {lei}")
                
                # Get status
                status = entity.get('status', 'UNKNOWN')
                registration_status = attributes.get('registration', {}).get('status', 'UNKNOWN')
                
                # Check if name matches (case-insensitive partial match)
                name_match = False
                if expected_name and legal_name:
                    expected_lower = expected_name.lower().strip()
                    legal_lower = legal_name.lower().strip()
                    # Check for exact match or if expected name is contained in legal name
                    name_match = (expected_lower == legal_lower or 
                                 expected_lower in legal_lower or 
                                 legal_lower in expected_lower)
                
                return {
                    'entity': {
                        'lei': lei.strip().upper(),
                        'legalName': legal_name,
                        'legalAddress': {
                            'city': headquarters['city'],
                            'region': headquarters['region'],
                            'country': headquarters['country'],
                            'postalCode': headquarters['postal_code'],
                            'addressLines': headquarters['address_lines']
                        },
                        'status': status,
                        'registrationStatus': registration_status
                    },
                    'is_active': status == 'ACTIVE' and registration_status == 'ISSUED',
                    'name_match': name_match,
                    'headquarters': {
                        'city': headquarters['city'],
                        'state': headquarters['region'],  # US states are in 'region' field
                        'country': headquarters['country'],
                        'full_address': ', '.join(filter(None, [
                            ', '.join(headquarters['address_lines']) if headquarters['address_lines'] else '',
                            headquarters['city'],
                            headquarters['region'],
                            headquarters['postal_code'],
                            headquarters['country']
                        ]))
                    }
                }
            else:
                logger.warning(f"Unexpected GLEIF API response format for LEI {lei}")
                return {
                    'entity': None,
                    'is_active': False,
                    'name_match': False,
                    'headquarters': {}
                }
                
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.info(f"LEI not found in GLEIF: {lei}")
                return {
                    'entity': None,
                    'is_active': False,
                    'name_match': False,
                    'headquarters': {}
                }
            else:
                logger.error(f"GLEIF API HTTP error for LEI {lei}: {e}")
                raise
        except requests.exceptions.RequestException as e:
            logger.error(f"GLEIF API error for LEI {lei}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error verifying LEI {lei}: {e}")
            raise
    
    def search_by_name(self, name: str, limit: int = 20) -> list:
        """
        Search for entities by name in GLEIF.
        
        Note: GLEIF API doesn't have a direct name search endpoint.
        This would require using the GLEIF bulk download or a third-party service.
        For now, this is a placeholder.
        
        Args:
            name: Entity name to search for
            limit: Maximum number of results
            
        Returns:
            List of matching entities (empty for now)
        """
        # GLEIF doesn't provide a name search API endpoint
        # Would need to use bulk data download or third-party service
        logger.debug("GLEIF name search not implemented (requires bulk data)")
        return []

