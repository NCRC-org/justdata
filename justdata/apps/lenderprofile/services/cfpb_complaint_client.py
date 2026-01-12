#!/usr/bin/env python3
"""
CFPB Consumer Complaint Database (CCDB) API Client
Searches consumer complaints filed with the CFPB.

Documentation: https://cfpb.github.io/ccdb5-api/documentation/
Base URL: https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/
"""

import requests
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CFPBComplaintClient:
    """
    Client for CFPB Consumer Complaint Database API.
    
    This API allows searching consumer complaints by company name, product, state, etc.
    No authentication required - public API.
    """
    
    def __init__(self):
        """Initialize CFPB Complaint Database client."""
        self.base_url = 'https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1'
        self.timeout = 30
        self.user_agent = 'NCRC Lender Intelligence Platform (contact@ncrc.org)'
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        return {
            'User-Agent': self.user_agent,
            'Accept': 'application/json'
        }
    
    def get_cfpb_company_name(self, search_term: str) -> Optional[str]:
        """
        Find the exact CFPB company name using the suggest API.
        CFPB uses specific company names that may differ from common names.

        Args:
            search_term: Company name to search for

        Returns:
            Exact CFPB company name or None
        """
        try:
            url = f'{self.base_url}/'
            params = {
                'size': 0,  # We only want aggregations
                'search_term': search_term,
                'field': 'company'
            }

            logger.info(f"CFPB looking up company name for: {search_term}")
            response = requests.get(url, params=params, headers=self._get_headers(), timeout=self.timeout)
            response.raise_for_status()

            data = response.json()

            # Get company aggregation buckets
            aggs = data.get('aggregations', {})
            company_agg = aggs.get('company', {}).get('company', {})
            buckets = company_agg.get('buckets', [])

            if buckets:
                # Return the top matching company name
                best_match = buckets[0]
                cfpb_name = best_match.get('key', '')
                doc_count = best_match.get('doc_count', 0)
                logger.info(f"CFPB found company: '{cfpb_name}' with {doc_count} complaints")
                return cfpb_name

            logger.warning(f"No CFPB company found for: {search_term}")
            return None

        except Exception as e:
            logger.error(f"Error looking up CFPB company name: {e}")
            return None

    def search_complaints(self, company: Optional[str] = None,
                         product: Optional[str] = None,
                         state: Optional[str] = None,
                         date_received_min: Optional[str] = None,
                         date_received_max: Optional[str] = None,
                         limit: int = 100,
                         size: int = 100,
                         use_search_term: bool = False) -> Optional[Dict[str, Any]]:
        """
        Search consumer complaints.

        Args:
            company: Company name (e.g., "PNC Bank", "PNC Financial Services")
            product: Product type (e.g., "Mortgage", "Credit card", "Bank account or service")
            state: State abbreviation (e.g., "PA", "NY")
            date_received_min: Minimum date (YYYY-MM-DD format)
            date_received_max: Maximum date (YYYY-MM-DD format)
            limit: Maximum number of results to return
            size: Page size (max 1000)
            use_search_term: If True, use search_term for fuzzy matching instead of exact company

        Returns:
            Dictionary with complaints data or None
        """
        try:
            url = f'{self.base_url}/'
            params = {
                'size': min(size, 1000),  # API max is 1000
                'format': 'json'
            }

            # Add filters
            if company:
                if use_search_term:
                    params['search_term'] = company
                else:
                    params['company'] = company
            if product:
                params['product'] = product
            if state:
                params['state'] = state.upper()
            if date_received_min:
                params['date_received_min'] = date_received_min
            if date_received_max:
                params['date_received_max'] = date_received_max
            
            logger.info(f"CFPB Complaint API request: {url} with params: {params}")
            response = requests.get(url, params=params, headers=self._get_headers(), timeout=self.timeout)
            logger.info(f"CFPB Complaint API response status: {response.status_code}")
            response.raise_for_status()
            
            data = response.json()
            
            # Handle different response formats
            # The API might return a list directly or a dict with hits
            if isinstance(data, list):
                # If it's a list, limit it
                if len(data) > limit:
                    data = data[:limit]
                logger.info(f"CFPB Complaint API returned {len(data)} complaints (list format)")
                # Convert to expected format
                return {
                    'hits': {
                        'hits': [{'_source': item} if isinstance(item, dict) else {'_source': {}} for item in data],
                        'total': {'value': len(data)}
                    }
                }
            elif isinstance(data, dict):
                # Standard Elasticsearch format
                if 'hits' in data and 'hits' in data['hits']:
                    hits = data['hits']['hits']
                    if len(hits) > limit:
                        data['hits']['hits'] = hits[:limit]
                        if 'total' in data['hits']:
                            if isinstance(data['hits']['total'], dict):
                                data['hits']['total']['value'] = limit
                            else:
                                data['hits']['total'] = limit
                
                total = 0
                if 'hits' in data and 'total' in data['hits']:
                    if isinstance(data['hits']['total'], dict):
                        total = data['hits']['total'].get('value', 0)
                    else:
                        total = data['hits']['total']
                
                logger.info(f"CFPB Complaint API returned {total} total complaints")
                return data
            else:
                logger.warning(f"Unexpected CFPB Complaint API response format: {type(data)}")
                return {'hits': {'hits': [], 'total': {'value': 0}}}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"CFPB Complaint API error searching complaints: {e}")
            return None
    
    def get_complaints_by_company(self, company_name: str,
                                  limit: int = 100,
                                  years_back: int = 5) -> List[Dict[str, Any]]:
        """
        Get complaints for a specific company.

        Args:
            company_name: Company name to search for
            limit: Maximum number of complaints to return
            years_back: Number of years to look back (default: 5)

        Returns:
            List of complaint dictionaries
        """
        # First, find the exact CFPB company name
        cfpb_company_name = self.get_cfpb_company_name(company_name)

        if not cfpb_company_name:
            # Try variations if first lookup fails
            variations = [
                company_name.replace(' BANK', '').replace(' Bank', ''),
                company_name.split(',')[0].strip(),  # Remove ", N.A." etc
                company_name.replace(' BANCORP', '').replace(' Bancorp', ''),
            ]
            for variant in variations:
                cfpb_company_name = self.get_cfpb_company_name(variant)
                if cfpb_company_name:
                    break

        if not cfpb_company_name:
            logger.warning(f"Could not find CFPB company name for: {company_name}")
            return []

        logger.info(f"Using CFPB company name: '{cfpb_company_name}' for search")

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years_back * 365)

        date_min = start_date.strftime('%Y-%m-%d')
        date_max = end_date.strftime('%Y-%m-%d')

        # Search with the exact CFPB company name
        all_complaints = []
        seen_complaint_ids = set()

        result = self.search_complaints(
            company=cfpb_company_name,
            date_received_min=date_min,
            date_received_max=date_max,
            size=min(limit, 1000)
        )

        if result and 'hits' in result and 'hits' in result['hits']:
            for hit in result['hits']['hits']:
                complaint = hit.get('_source', {})
                complaint_id = complaint.get('complaint_id')

                if complaint_id and complaint_id not in seen_complaint_ids:
                    seen_complaint_ids.add(complaint_id)
                    all_complaints.append(complaint)

        return all_complaints[:limit]
    
    def get_complaint_stats(self, company_name: str, years_back: int = 5) -> Dict[str, Any]:
        """
        Get complaint statistics using CFPB aggregations (more accurate than counting hits).
        Returns total count, yearly breakdown, and top 5 categories.

        Args:
            company_name: Company name to search for
            years_back: Number of years to look back

        Returns:
            Dictionary with complaint statistics
        """
        # First, find the exact CFPB company name
        cfpb_company_name = self.get_cfpb_company_name(company_name)

        if not cfpb_company_name:
            variations = [
                company_name.replace(' BANK', '').replace(' Bank', ''),
                company_name.split(',')[0].strip(),
                company_name.replace(' BANCORP', '').replace(' Bancorp', ''),
            ]
            for variant in variations:
                cfpb_company_name = self.get_cfpb_company_name(variant)
                if cfpb_company_name:
                    break

        if not cfpb_company_name:
            logger.warning(f"Could not find CFPB company for stats: {company_name}")
            return {
                'total': 0,
                'cfpb_company_name': None,
                'by_year': {},
                'top_categories': [],
                'by_product': {},
                'trend': 'unknown'
            }

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years_back * 365)
        date_min = start_date.strftime('%Y-%m-%d')
        date_max = end_date.strftime('%Y-%m-%d')

        try:
            url = f'{self.base_url}/'
            params = {
                'size': 0,  # We only want aggregations
                'company': cfpb_company_name,
                'date_received_min': date_min,
                'date_received_max': date_max,
                'field': 'product,issue,date_received_year'
            }

            logger.info(f"CFPB getting stats for: {cfpb_company_name}")
            response = requests.get(url, params=params, headers=self._get_headers(), timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            # Get total from hits
            total = 0
            if 'hits' in data and 'total' in data['hits']:
                if isinstance(data['hits']['total'], dict):
                    total = data['hits']['total'].get('value', 0)
                else:
                    total = data['hits']['total']

            logger.info(f"CFPB total complaints for {cfpb_company_name}: {total}")

            # Get aggregations
            aggs = data.get('aggregations', {})

            # By year
            by_year = {}
            year_agg = aggs.get('date_received_year', {}).get('date_received_year', {})
            for bucket in year_agg.get('buckets', []):
                year = bucket.get('key_as_string', bucket.get('key', ''))
                if year:
                    # Extract just the year
                    year_str = str(year)[:4] if len(str(year)) >= 4 else str(year)
                    by_year[year_str] = bucket.get('doc_count', 0)

            # By product (top 5 categories)
            by_product = {}
            product_agg = aggs.get('product', {}).get('product', {})
            for bucket in product_agg.get('buckets', []):
                product = bucket.get('key', 'Unknown')
                by_product[product] = bucket.get('doc_count', 0)

            # Sort and get top 5
            sorted_products = sorted(by_product.items(), key=lambda x: x[1], reverse=True)
            top_categories = [
                {'category': cat, 'count': count, 'percentage': round(count / total * 100, 1) if total > 0 else 0}
                for cat, count in sorted_products[:5]
            ]

            # Calculate trend (compare most recent year to previous)
            sorted_years = sorted(by_year.keys(), reverse=True)
            trend = 'stable'
            if len(sorted_years) >= 2:
                current = by_year.get(sorted_years[0], 0)
                previous = by_year.get(sorted_years[1], 0)
                if previous > 0:
                    pct_change = (current - previous) / previous * 100
                    if pct_change > 10:
                        trend = 'increasing'
                    elif pct_change < -10:
                        trend = 'decreasing'

            return {
                'total': total,
                'cfpb_company_name': cfpb_company_name,
                'by_year': by_year,
                'top_categories': top_categories,
                'by_product': by_product,
                'trend': trend
            }

        except Exception as e:
            logger.error(f"Error getting CFPB complaint stats: {e}")
            return {
                'total': 0,
                'cfpb_company_name': cfpb_company_name,
                'by_year': {},
                'top_categories': [],
                'by_product': {},
                'trend': 'unknown'
            }

    def get_complaint_summary(self, company_name: str, years_back: int = 5) -> Dict[str, Any]:
        """
        Get summary statistics for complaints about a company.

        Args:
            company_name: Company name to search for
            years_back: Number of years to look back

        Returns:
            Dictionary with complaint summary statistics
        """
        # Use the new stats method for accurate totals
        stats = self.get_complaint_stats(company_name, years_back=years_back)

        if stats['total'] == 0:
            return {
                'total_complaints': 0,
                'by_product': {},
                'by_state': {},
                'by_year': stats.get('by_year', {}),
                'timely_response_rate': 0.0,
                'consumer_disputed_rate': 0.0,
                'top_categories': [],
                'trend': stats.get('trend', 'unknown'),
                'cfpb_company_name': stats.get('cfpb_company_name')
            }

        return {
            'total_complaints': stats['total'],
            'by_product': stats.get('by_product', {}),
            'by_state': {},  # Would need separate query
            'by_year': stats.get('by_year', {}),
            'timely_response_rate': 0.0,  # Would need sample query
            'consumer_disputed_rate': 0.0,
            'top_categories': stats.get('top_categories', []),
            'trend': stats.get('trend', 'unknown'),
            'cfpb_company_name': stats.get('cfpb_company_name')
        }

