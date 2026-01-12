#!/usr/bin/env python3
"""
CFPB API Client
Includes both HMDA API (for institution data) and Consumer Complaint Database API (CCDB5).

The CFPB HMDA API provides institution metadata including assets, type, and location.
The CFPB Consumer Complaint Database API provides consumer complaints against financial institutions.

Documentation:
- HMDA API: https://ffiec.cfpb.gov/hmda-auth/
- Consumer Complaints API: https://cfpb.github.io/ccdb5-api/documentation/
"""

import logging
import requests
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class CFPBClient:
    """
    Client for CFPB HMDA APIs.

    Uses the PUBLIC FFIEC Institutions API (no auth required) for institution
    metadata (name, LEI, RSSD, assets, parent/top holder info).

    API Docs: https://ffiec.cfpb.gov/documentation/api/institutions-api/

    Primary use: Get assets and institution data by LEI.
    """

    INSTITUTIONS_BASE_URL = 'https://ffiec.cfpb.gov/v2/public/institutions'
    FILERS_BASE_URL = 'https://ffiec.cfpb.gov/v2/reporting/filers'

    def __init__(self):
        """Initialize CFPB client - uses public API, no auth required."""
        self.timeout = 30

    def _is_enabled(self) -> bool:
        """Check if CFPB API is enabled - always True for public API."""
        return True

    def get_institution_by_lei(self, lei: str, year: int = 2023) -> Optional[Dict[str, Any]]:
        """
        Get institution data by LEI using the public FFIEC API.

        Args:
            lei: Legal Entity Identifier (20 characters)
            year: Filing year (default: 2023)

        Returns:
            Institution data including assets, RSSD, tax ID, parent info
        """
        if not lei or len(lei) != 20:
            logger.warning(f"Invalid LEI format: {lei}")
            return None

        try:
            url = f"{self.INSTITUTIONS_BASE_URL}/{lei}/year/{year}"
            logger.info(f"FFIEC Institutions API request: {url}")

            response = requests.get(url, timeout=self.timeout)

            if response.status_code == 404:
                # Try previous year
                if year > 2018:
                    logger.debug(f"LEI not found for {year}, trying {year-1}")
                    return self.get_institution_by_lei(lei, year - 1)
                return None

            response.raise_for_status()
            data = response.json()

            # Normalize the response
            return {
                'lei': data.get('lei'),
                'name': data.get('respondent', {}).get('name'),
                'city': data.get('respondent', {}).get('city'),
                'state': data.get('respondent', {}).get('state'),
                'assets': data.get('assets'),  # In thousands
                'rssd': data.get('rssd'),
                'tax_id': data.get('taxId'),
                'agency': data.get('agency'),
                'institution_type': data.get('institutionType'),
                'hmda_filer': data.get('hmdaFiler'),
                'quarterly_filer': data.get('quarterlyFiler'),
                'activity_year': data.get('activityYear'),
                'parent': {
                    'name': data.get('parent', {}).get('name', '').strip() if data.get('parent') else None,
                    'rssd': data.get('parent', {}).get('idRssd') if data.get('parent') else None
                },
                'top_holder': {
                    'name': data.get('topHolder', {}).get('name', '').strip() if data.get('topHolder') else None,
                    'rssd': data.get('topHolder', {}).get('idRssd') if data.get('topHolder') else None
                },
                'email_domains': data.get('emailDomains', [])
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"FFIEC Institutions API error for LEI {lei}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing FFIEC response: {e}", exc_info=True)
            return None

    def search_filers_by_name(self, name: str, year: int = 2023) -> List[Dict[str, Any]]:
        """
        Search for HMDA filers by name.

        Args:
            name: Institution name to search for
            year: Filing year

        Returns:
            List of matching institutions with LEI and name
        """
        try:
            url = f"{self.FILERS_BASE_URL}/{year}"
            logger.info(f"FFIEC Filers API request: {url}")

            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            institutions = data.get('institutions', [])
            name_upper = name.upper()

            # Filter by name match
            matches = [
                {'lei': inst.get('lei'), 'name': inst.get('name'), 'period': inst.get('period')}
                for inst in institutions
                if name_upper in inst.get('name', '').upper()
            ]

            logger.info(f"Found {len(matches)} filers matching '{name}'")
            return matches

        except requests.exceptions.RequestException as e:
            logger.error(f"FFIEC Filers API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error processing FFIEC filers response: {e}", exc_info=True)
            return []

    def get_institution_by_name(self, name: str, year: int = 2023) -> Optional[Dict[str, Any]]:
        """
        Get institution metadata by name (searches filers then gets full details).

        Args:
            name: Institution name
            year: Filing year

        Returns:
            Institution dictionary or None
        """
        try:
            matches = self.search_filers_by_name(name, year)
            if matches:
                # Get full details for first match
                return self.get_institution_by_lei(matches[0]['lei'], year)
            return None
        except Exception as e:
            logger.error(f"Error getting institution by name: {e}", exc_info=True)
            return None

    def get_transmittal_sheet_data(self, lei: str, year: int = 2023) -> Optional[Dict[str, Any]]:
        """
        Get HMDA transmittal sheet data by LEI and year.

        Uses the public FFIEC Institutions API which includes assets and institution metadata.

        Args:
            lei: Legal Entity Identifier
            year: Year to get data for (default: 2023)

        Returns:
            Dictionary with institution data including assets
        """
        # Just use get_institution_by_lei - it returns all the data we need
        return self.get_institution_by_lei(lei, year)
    
    def get_cfpb_company_name(self, search_term: str) -> Optional[str]:
        """
        Find the exact CFPB company name using fuzzy search.
        CFPB uses specific company names that may differ from common names.

        Args:
            search_term: Company name to search for

        Returns:
            Exact CFPB company name or None (only if it actually matches the search term)
        """
        try:
            base_url = 'https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/'
            params = {
                'size': 0,  # We only want aggregations
                'search_term': search_term,
                'field': 'company'
            }

            logger.info(f"CFPB looking up company name for: {search_term}")
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Get company aggregation buckets
            aggs = data.get('aggregations', {})
            company_agg = aggs.get('company', {}).get('company', {})
            buckets = company_agg.get('buckets', [])

            if not buckets:
                logger.warning(f"No CFPB company found for: {search_term}")
                return None

            # Normalize search term for comparison
            search_normalized = search_term.upper().strip()
            # Extract key words (ignore common suffixes and generic terms)
            ignore_words = {'INC', 'LLC', 'LP', 'NA', 'N.A.', 'CORPORATION', 'CORP', 'CO', 'THE',
                           'BANK', 'NATIONAL', 'ASSOCIATION', 'FINANCIAL', 'SERVICES', 'GROUP'}
            search_words = set(w for w in search_normalized.replace(',', '').replace('.', '').split()
                              if w not in ignore_words and len(w) > 1)

            # Find best matching company - must have significant word overlap
            best_match = None
            best_overlap = 0

            for bucket in buckets:
                cfpb_name = bucket.get('key', '')
                doc_count = bucket.get('doc_count', 0)

                cfpb_normalized = cfpb_name.upper().strip()
                cfpb_words = set(w for w in cfpb_normalized.replace(',', '').replace('.', '').split()
                                if w not in ignore_words and len(w) > 1)

                # Check for significant word overlap
                if search_words and cfpb_words:
                    overlap = len(search_words & cfpb_words)
                    # Require at least 1 real word match AND good coverage of search words
                    # min_required is at least 1, or at least 50% of search words
                    min_required = max(1, (len(search_words) + 1) // 2)  # Round up for 50%

                    # Additional check: require overlap to be at least 50% of the SMALLER word set
                    smaller_set_size = min(len(search_words), len(cfpb_words))
                    overlap_pct = overlap / smaller_set_size if smaller_set_size > 0 else 0

                    if overlap >= min_required and overlap_pct >= 0.5:
                        # Keep the best match (highest overlap)
                        if overlap > best_overlap:
                            best_overlap = overlap
                            best_match = cfpb_name
                            logger.info(f"CFPB found company: '{cfpb_name}' with {doc_count} complaints (matched {overlap}/{len(search_words)} words)")

            if best_match:
                return best_match

            # No valid match found
            logger.warning(f"No matching CFPB company found for: {search_term} (candidates didn't match)")
            return None

        except Exception as e:
            logger.error(f"Error looking up CFPB company name: {e}")
            return None

    def get_yearly_complaint_counts(self, cfpb_company_name: str, years: int = 5) -> Dict[str, int]:
        """
        Get complaint counts per year for a company.
        Makes efficient requests with size=0 to just get totals.

        Args:
            cfpb_company_name: Exact CFPB company name
            years: Number of years to look back

        Returns:
            Dictionary of year -> count
        """
        from datetime import datetime
        from concurrent.futures import ThreadPoolExecutor, as_completed

        base_url = 'https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/'
        current_year = datetime.now().year
        by_year = {}

        def get_year_count(year: int) -> tuple:
            try:
                params = {
                    'company': cfpb_company_name,
                    'size': 0,  # Just get count
                    'date_received_min': f'{year}-01-01',
                    'date_received_max': f'{year}-12-31'
                }
                response = requests.get(base_url, params=params, timeout=15)
                response.raise_for_status()
                data = response.json()
                hits = data.get('hits', {})
                total = hits.get('total', {}).get('value', 0) if isinstance(hits.get('total'), dict) else hits.get('total', 0)
                return (str(year), total)
            except Exception as e:
                logger.debug(f"Error getting year {year} count: {e}")
                return (str(year), 0)

        # Fetch counts for each year in parallel
        years_to_check = list(range(current_year - years + 1, current_year + 1))

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(get_year_count, year): year for year in years_to_check}
            for future in as_completed(futures):
                year_str, count = future.result()
                by_year[year_str] = count

        logger.info(f"CFPB yearly counts for {cfpb_company_name}: {by_year}")
        return by_year

    def get_national_complaint_counts(self, years: int = 5) -> Dict[str, int]:
        """
        Get national complaint totals per year (all companies).

        Args:
            years: Number of years to look back

        Returns:
            Dictionary of year -> total national count
        """
        from datetime import datetime
        from concurrent.futures import ThreadPoolExecutor, as_completed

        base_url = 'https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/'
        current_year = datetime.now().year
        by_year = {}

        def get_year_count(year: int) -> tuple:
            try:
                params = {
                    'size': 0,  # Just get count
                    'date_received_min': f'{year}-01-01',
                    'date_received_max': f'{year}-12-31'
                }
                response = requests.get(base_url, params=params, timeout=15)
                response.raise_for_status()
                data = response.json()
                hits = data.get('hits', {})
                total = hits.get('total', {}).get('value', 0) if isinstance(hits.get('total'), dict) else hits.get('total', 0)
                return (str(year), total)
            except Exception as e:
                logger.debug(f"Error getting national year {year} count: {e}")
                return (str(year), 0)

        years_to_check = list(range(current_year - years + 1, current_year + 1))

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(get_year_count, year): year for year in years_to_check}
            for future in as_completed(futures):
                year_str, count = future.result()
                by_year[year_str] = count

        logger.info(f"CFPB national yearly counts: {by_year}")
        return by_year

    def get_categories_by_year(self, cfpb_company_name: str, years: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get complaint categories (products) by year for interactive chart.

        Args:
            cfpb_company_name: Exact CFPB company name
            years: Number of years to look back

        Returns:
            Dictionary of year -> list of categories with counts
        """
        from datetime import datetime
        from concurrent.futures import ThreadPoolExecutor, as_completed

        base_url = 'https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/'
        current_year = datetime.now().year
        categories_by_year = {}

        def get_year_categories(year: int) -> tuple:
            try:
                # Request a small number of results to get aggregations
                params = {
                    'company': cfpb_company_name,
                    'size': 1,  # Need at least 1 to get aggregations
                    'date_received_min': f'{year}-01-01',
                    'date_received_max': f'{year}-12-31'
                }
                response = requests.get(base_url, params=params, timeout=15)
                response.raise_for_status()
                data = response.json()

                # Extract product buckets from aggregations
                # Structure: aggregations -> product -> product -> buckets
                aggs = data.get('aggregations', {})
                product_agg = aggs.get('product', {})

                # Try different possible structures
                buckets = []
                if isinstance(product_agg, dict):
                    inner = product_agg.get('product', product_agg)
                    if isinstance(inner, dict):
                        buckets = inner.get('buckets', [])
                    elif isinstance(inner, list):
                        buckets = inner

                categories = []
                for bucket in buckets[:10]:  # Top 10 categories
                    if isinstance(bucket, dict):
                        categories.append({
                            'product': bucket.get('key', 'Unknown'),
                            'count': bucket.get('doc_count', 0)
                        })

                return (str(year), categories)
            except Exception as e:
                logger.debug(f"Error getting categories for year {year}: {e}")
                return (str(year), [])

        years_to_check = list(range(current_year - years + 1, current_year + 1))

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(get_year_categories, year): year for year in years_to_check}
            for future in as_completed(futures):
                year_str, categories = future.result()
                if categories:
                    categories_by_year[year_str] = categories

        logger.info(f"CFPB categories by year for {cfpb_company_name}: {len(categories_by_year)} years")
        return categories_by_year

    def search_consumer_complaints(self, company_name: str, limit: int = 100,
                                  date_received_min: Optional[str] = None,
                                  date_received_max: Optional[str] = None,
                                  product: Optional[str] = None,
                                  issue: Optional[str] = None,
                                  include_analysis: bool = True) -> Dict[str, Any]:
        """
        Search for consumer complaints against a company using CFPB Consumer Complaint Database API (CCDB5).

        Documentation: https://cfpb.github.io/ccdb5-api/documentation/
        Base URL: https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/

        Args:
            company_name: Company name to search for (e.g., "PNC Bank", "PNC Financial")
            limit: Maximum number of complaints to return (default: 100, max: 10000)
            date_received_min: Minimum date (YYYY-MM-DD format)
            date_received_max: Maximum date (YYYY-MM-DD format)
            product: Filter by product type (e.g., "Mortgage", "Credit card", "Bank account or service")
            issue: Filter by issue type
            include_analysis: If True, includes trend analysis and topic analysis

        Returns:
            Dictionary with:
            {
                'total': int,  # Total number of complaints
                'complaints': List[Dict],  # List of complaint records
                'aggregations': Dict,  # Aggregated statistics (by product, issue, etc.)
                'trends': Dict,  # Year-over-year trend analysis (if include_analysis=True)
                'main_topics': List[Dict],  # Top issues/topics (if include_analysis=True)
                'main_products': List[Dict]  # Top products (if include_analysis=True)
            }
        """
        try:
            # First, find the exact CFPB company name using fuzzy search
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
                return {'total': 0, 'complaints': [], 'aggregations': {}}

            logger.info(f"Using CFPB company name: '{cfpb_company_name}' for search")

            base_url = 'https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/'
            params = {
                'company': cfpb_company_name,
                'size': min(limit, 10000),  # API limit is 10000
                'sort': 'created_date_desc'  # Sort by most recent first
            }

            if date_received_min:
                params['date_received_min'] = date_received_min
            if date_received_max:
                params['date_received_max'] = date_received_max
            if product:
                params['product'] = product
            if issue:
                params['issue'] = issue

            logger.info(f"CFPB Complaints API request: {base_url} with company '{cfpb_company_name}'")
            response = requests.get(base_url, params=params, timeout=30)
            logger.info(f"CFPB Complaints API response status: {response.status_code}")
            response.raise_for_status()
            
            data = response.json()
            
            # Extract complaints from Elasticsearch-style response
            hits = data.get('hits', {})
            total = hits.get('total', {}).get('value', 0) if isinstance(hits.get('total'), dict) else hits.get('total', 0)
            complaint_hits = hits.get('hits', [])
            
            # Extract complaint data from _source
            complaints = []
            for hit in complaint_hits:
                source = hit.get('_source', {})
                complaints.append({
                    'complaint_id': source.get('complaint_id'),
                    'date_received': source.get('date_received'),
                    'date_sent_to_company': source.get('date_sent_to_company'),
                    'company': source.get('company'),
                    'product': source.get('product'),
                    'sub_product': source.get('sub_product'),
                    'issue': source.get('issue'),
                    'sub_issue': source.get('sub_issue'),
                    'consumer_complaint_narrative': source.get('consumer_complaint_narrative'),
                    'company_public_response': source.get('company_public_response'),
                    'company_response': source.get('company_response'),
                    'consumer_disputed': source.get('consumer_disputed'),
                    'state': source.get('state'),
                    'zip_code': source.get('zip_code'),
                    'tags': source.get('tags', [])
                })
            
            # Get most recent complaint date
            latest_complaint_date = None
            if complaints:
                latest_complaint_date = complaints[0].get('date_received')

            result = {
                'total': total,
                'complaints': complaints,
                'aggregations': data.get('aggregations', {}),
                'latest_complaint_date': latest_complaint_date
            }

            # Add trend and topic analysis if requested
            if include_analysis:
                # Get yearly counts using parallel requests (more accurate than sample)
                yearly_counts = self.get_yearly_complaint_counts(cfpb_company_name, years=5)
                result['trends'] = self._analyze_complaint_trends(complaints, data.get('aggregations', {}), yearly_counts)
                result['main_topics'] = self._extract_main_topics(complaints, data.get('aggregations', {}))
                result['main_products'] = self._extract_main_products(complaints, data.get('aggregations', {}))
                result['cfpb_company_name'] = cfpb_company_name
            
            logger.info(f"CFPB Complaints API returned {total} total complaints, {len(complaints)} in response")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"CFPB Complaints API error searching for '{company_name}': {e}")
            return {'total': 0, 'complaints': [], 'aggregations': {}}
        except Exception as e:
            logger.error(f"Error processing CFPB complaints response: {e}", exc_info=True)
            return {'total': 0, 'complaints': [], 'aggregations': {}}
    
    def _analyze_complaint_trends(self, complaints: List[Dict[str, Any]], aggregations: Dict[str, Any] = None, yearly_counts: Dict[str, int] = None) -> Dict[str, Any]:
        """
        Analyze complaint trends over time using yearly counts (preferred), aggregations, or complaint list.

        Args:
            complaints: List of complaint dictionaries (fallback)
            aggregations: Aggregations from API response
            yearly_counts: Pre-fetched yearly counts (preferred, most accurate)

        Returns:
            Dictionary with trend analysis including:
            - by_year: Complaints per year
            - recent_trend: 'increasing', 'decreasing', or 'stable'
            - year_over_year_changes: Percentage changes year-over-year
        """
        from collections import defaultdict

        by_year = {}

        # Use pre-fetched yearly counts if available (most accurate)
        if yearly_counts:
            by_year = yearly_counts.copy()
        # Try to get from aggregations
        elif aggregations:
            year_agg = aggregations.get('date_received_year', {}).get('date_received_year', {})
            buckets = year_agg.get('buckets', [])
            for bucket in buckets:
                year_key = bucket.get('key_as_string', str(bucket.get('key', '')))
                year = str(year_key)[:4] if year_key else None
                if year and year.isdigit():
                    by_year[year] = bucket.get('doc_count', 0)

        # Fallback to counting complaints
        if not by_year and complaints:
            by_year = defaultdict(int)
            for complaint in complaints:
                date_received = complaint.get('date_received', '')
                if date_received:
                    try:
                        year = date_received[:4] if len(date_received) >= 4 else None
                        if year and year.isdigit():
                            by_year[year] += 1
                    except Exception:
                        continue
            by_year = dict(by_year)

        # Sort years
        sorted_years = sorted(by_year.keys())
        
        # Calculate year-over-year changes
        year_over_year = {}
        for i in range(1, len(sorted_years)):
            prev_year = sorted_years[i-1]
            curr_year = sorted_years[i]
            prev_count = by_year[prev_year]
            curr_count = by_year[curr_year]
            
            if prev_count > 0:
                change_pct = ((curr_count - prev_count) / prev_count) * 100
                year_over_year[curr_year] = {
                    'change': change_pct,
                    'previous_year': prev_year,
                    'previous_count': prev_count,
                    'current_count': curr_count
                }
        
        # Determine recent trend (last 3 years)
        recent_trend = 'stable'
        if len(sorted_years) >= 2:
            recent_years = sorted_years[-3:] if len(sorted_years) >= 3 else sorted_years[-2:]
            if len(recent_years) >= 2:
                first_count = by_year[recent_years[0]]
                last_count = by_year[recent_years[-1]]
                
                if first_count > 0:
                    change_pct = ((last_count - first_count) / first_count) * 100
                    if change_pct > 10:
                        recent_trend = 'increasing'
                    elif change_pct < -10:
                        recent_trend = 'decreasing'
        
        return {
            'by_year': dict(by_year),
            'recent_trend': recent_trend,
            'year_over_year_changes': year_over_year,
            'years_analyzed': sorted_years,
            'most_recent_year': sorted_years[-1] if sorted_years else None,
            'most_recent_count': by_year[sorted_years[-1]] if sorted_years else 0
        }
    
    def _extract_main_topics(self, complaints: List[Dict[str, Any]], aggregations: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract main topics/issues from complaints.
        
        Args:
            complaints: List of complaint dictionaries
            aggregations: Aggregations from API response
            
        Returns:
            List of top issues with counts
        """
        from collections import defaultdict
        
        # Try to get from aggregations first (more accurate)
        issue_agg = aggregations.get('issue', {})
        if isinstance(issue_agg, dict):
            issue_buckets = issue_agg.get('issue', {}).get('buckets', [])
            if issue_buckets:
                topics = []
                for bucket in issue_buckets[:10]:  # Top 10
                    topics.append({
                        'issue': bucket.get('key', 'Unknown'),
                        'count': bucket.get('doc_count', 0),
                        'percentage': 0.0  # Will calculate below
                    })
                
                # Calculate percentages
                total = sum(t['count'] for t in topics)
                if total > 0:
                    for topic in topics:
                        topic['percentage'] = (topic['count'] / total) * 100
                
                return topics
        
        # Fallback: count from complaints directly
        issue_counts = defaultdict(int)
        for complaint in complaints:
            issue = complaint.get('issue', 'Unknown')
            if issue:
                issue_counts[issue] += 1
        
        # Sort by count and return top 10
        sorted_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        total = sum(count for _, count in sorted_issues)
        
        topics = []
        for issue, count in sorted_issues:
            topics.append({
                'issue': issue,
                'count': count,
                'percentage': (count / total * 100) if total > 0 else 0.0
            })
        
        return topics
    
    def _extract_main_products(self, complaints: List[Dict[str, Any]], aggregations: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract main products from complaints.
        
        Args:
            complaints: List of complaint dictionaries
            aggregations: Aggregations from API response
            
        Returns:
            List of top products with counts
        """
        from collections import defaultdict
        
        # Try to get from aggregations first
        product_agg = aggregations.get('product', {})
        if isinstance(product_agg, dict):
            product_buckets = product_agg.get('product', {}).get('buckets', [])
            if product_buckets:
                products = []
                for bucket in product_buckets[:10]:  # Top 10
                    products.append({
                        'product': bucket.get('key', 'Unknown'),
                        'count': bucket.get('doc_count', 0),
                        'percentage': 0.0
                    })
                
                # Calculate percentages
                total = sum(p['count'] for p in products)
                if total > 0:
                    for product in products:
                        product['percentage'] = (product['count'] / total) * 100
                
                return products
        
        # Fallback: count from complaints directly
        product_counts = defaultdict(int)
        for complaint in complaints:
            product = complaint.get('product', 'Unknown')
            if product:
                product_counts[product] += 1
        
        # Sort by count and return top 10
        sorted_products = sorted(product_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        total = sum(count for _, count in sorted_products)
        
        products = []
        for product, count in sorted_products:
            products.append({
                'product': product,
                'count': count,
                'percentage': (count / total * 100) if total > 0 else 0.0
            })
        
        return products
    
    def search_enforcement_actions(self, institution_name: str) -> List[Dict[str, Any]]:
        """
        Search for enforcement actions by institution name.
        
        Note: CFPB enforcement database requires web scraping.
        This is a placeholder - actual implementation would scrape the site.
        
        Args:
            institution_name: Institution name to search for
            
        Returns:
            List of enforcement actions (empty for now)
        """
        # TODO: Implement web scraping for CFPB enforcement database
        # This would extract:
        # - Date
        # - Institution
        # - Violation type
        # - Penalty amount
        # - Status
        # - Consent order link
        logger.debug(f"CFPB enforcement actions search not yet implemented for '{institution_name}'")
        return []

