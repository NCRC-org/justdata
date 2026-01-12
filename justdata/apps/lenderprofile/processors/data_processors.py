#!/usr/bin/env python3
"""
Code-First Data Processors for LenderProfile
All data extraction, calculation, and structuring happens here - NO AI calls.
AI is only used for narrative synthesis of pre-processed structured data.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import re

logger = logging.getLogger(__name__)


class FinancialDataProcessor:
    """Process FDIC Call Report financial data."""
    
    @staticmethod
    def process_fdic_financials(fdic_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract and calculate financial metrics from FDIC Call Report data.
        
        Args:
            fdic_data: List of quarterly Call Report records
            
        Returns:
            Structured financial data with trends, metrics, and growth calculations
        """
        if not fdic_data:
            return {
                'trends': {},
                'metrics': {},
                'growth': {},
                'composition': {},
                'available': False
            }
        
        # Sort by date (most recent first)
        sorted_data = sorted(fdic_data, key=lambda x: x.get('REPDTE', ''), reverse=True)
        
        # Extract time series (last 5 years = 20 quarters)
        last_5_years = sorted_data[:20]
        last_5_years.reverse()  # Oldest to newest for trend analysis
        
        # Extract time series data
        trends = {
            'assets': [],
            'deposits': [],
            'equity': [],
            'net_income': [],
            'dates': []
        }
        
        for record in last_5_years:
            date_str = record.get('REPDTE', '')
            if date_str:
                trends['dates'].append(date_str)
                trends['assets'].append(record.get('ASSET', 0) or 0)
                trends['deposits'].append(record.get('DEP', 0) or 0)
                trends['equity'].append(record.get('EQUITY', 0) or record.get('EQ', 0) or 0)
                trends['net_income'].append(record.get('NETINC', 0) or 0)
        
        # Calculate metrics from latest quarter
        latest = sorted_data[0] if sorted_data else {}
        
        metrics = {
            'roa': latest.get('ROA', 0) or 0,
            'roe': latest.get('ROE', 0) or 0,
            'assets': latest.get('ASSET', 0) or 0,
            'deposits': latest.get('DEP', 0) or 0,
            'equity': latest.get('EQUITY', 0) or latest.get('EQ', 0) or 0,
            'net_income': latest.get('NETINC', 0) or 0,
            'report_date': latest.get('REPDTE', '')
        }
        
        # Calculate growth rates (CAGR)
        growth = {}
        if len(trends['assets']) >= 2:
            first_asset = trends['assets'][0]
            last_asset = trends['assets'][-1]
            years = len(trends['assets']) / 4.0  # Quarters to years
            
            if first_asset > 0 and years > 0:
                growth['asset_cagr'] = ((last_asset / first_asset) ** (1 / years) - 1) * 100
            
            first_dep = trends['deposits'][0]
            last_dep = trends['deposits'][-1]
            if first_dep > 0:
                growth['deposit_cagr'] = ((last_dep / first_dep) ** (1 / years) - 1) * 100
            
            first_income = trends['net_income'][0]
            last_income = trends['net_income'][-1]
            if first_income != 0:
                growth['income_cagr'] = ((last_income / first_income) ** (1 / years) - 1) * 100 if first_income > 0 else None
        
        # Calculate year-over-year changes
        if len(trends['assets']) >= 4:
            current_year_asset = trends['assets'][-1]
            prior_year_asset = trends['assets'][-5] if len(trends['assets']) >= 5 else trends['assets'][-4]
            if prior_year_asset > 0:
                growth['asset_yoy'] = ((current_year_asset - prior_year_asset) / prior_year_asset) * 100
        
        # Income composition (if available in data)
        composition = {
            'interest_income_pct': None,  # Would need INTRST_INC field
            'noninterest_income_pct': None,  # Would need NONINTRST_INC field
            'fee_income_pct': None
        }
        
        return {
            'trends': trends,
            'metrics': metrics,
            'growth': growth,
            'composition': composition,
            'available': True,
            'quarters_available': len(sorted_data)
        }
    
    @staticmethod
    def calculate_roa(net_income: float, avg_assets: float) -> float:
        """Calculate Return on Assets."""
        if avg_assets == 0:
            return 0.0
        return (net_income / avg_assets) * 100
    
    @staticmethod
    def calculate_roe(net_income: float, avg_equity: float) -> float:
        """Calculate Return on Equity."""
        if avg_equity == 0:
            return 0.0
        return (net_income / avg_equity) * 100
    
    @staticmethod
    def calculate_efficiency_ratio(non_int_expense: float, revenue: float) -> float:
        """Calculate Efficiency Ratio."""
        if revenue == 0:
            return 0.0
        return (non_int_expense / revenue) * 100


class GLEIFDataProcessor:
    """Process GLEIF entity data."""
    
    @staticmethod
    def build_corporate_structure(gleif_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build corporate hierarchy structure from GLEIF data.
        
        Args:
            gleif_data: GLEIF entity data
            
        Returns:
            Structured corporate hierarchy
        """
        if not gleif_data:
            return {'available': False}
        
        entity = gleif_data.get('entity', {})
        legal_name = entity.get('legalName', {}).get('name', 'Unknown')
        
        # Extract addresses
        legal_address = entity.get('legalAddress', {})
        headquarters_address = entity.get('headquartersAddress', {})
        
        # Extract direct parent from parent field
        parent_data = gleif_data.get('parent', {}) or gleif_data.get('direct_parent', {})
        direct_parent = None
        if parent_data and isinstance(parent_data, dict):
            if 'attributes' in parent_data:
                parent_attrs = parent_data.get('attributes', {})
                parent_entity = parent_attrs.get('entity', {})
                direct_parent = {
                    'lei': parent_data.get('id', ''),
                    'name': parent_entity.get('legalName', {}).get('name', 'Unknown')
                }
            else:
                direct_parent = {
                    'lei': parent_data.get('lei', parent_data.get('id', '')),
                    'name': parent_data.get('name', 'Unknown')
                }

        # Extract ultimate parent (top of corporate tree)
        # This comes from gleif_client.get_corporate_family() -> ultimate_parent field
        ultimate_parent_data = gleif_data.get('ultimate_parent', {})
        ultimate_parent = None
        if ultimate_parent_data and isinstance(ultimate_parent_data, dict):
            if 'attributes' in ultimate_parent_data:
                parent_attrs = ultimate_parent_data.get('attributes', {})
                parent_entity = parent_attrs.get('entity', {})
                ultimate_parent = {
                    'lei': ultimate_parent_data.get('id', ultimate_parent_data.get('lei', '')),
                    'name': parent_entity.get('legalName', {}).get('name', 'Unknown')
                }
            else:
                ultimate_parent = {
                    'lei': ultimate_parent_data.get('lei', ultimate_parent_data.get('id', '')),
                    'name': ultimate_parent_data.get('name', 'Unknown')
                }

        # Fall back to direct parent if no ultimate parent
        if not ultimate_parent:
            ultimate_parent = direct_parent

        # Extract children from direct field (from gleif_client.get_all_subsidiaries)
        children_data = gleif_data.get('children', {})
        direct_children = []
        ultimate_children = []

        if isinstance(children_data, dict):
            for child in children_data.get('direct', []):
                if isinstance(child, dict):
                    if 'attributes' in child:
                        child_entity = child.get('attributes', {}).get('entity', {})
                        direct_children.append({
                            'lei': child.get('id', ''),
                            'name': child_entity.get('legalName', {}).get('name', 'Unknown')
                        })
                    else:
                        direct_children.append({
                            'lei': child.get('lei', child.get('id', '')),
                            'name': child.get('name', 'Unknown')
                        })

            for child in children_data.get('ultimate', []):
                if isinstance(child, dict):
                    if 'attributes' in child:
                        child_entity = child.get('attributes', {}).get('entity', {})
                        ultimate_children.append({
                            'lei': child.get('id', ''),
                            'name': child_entity.get('legalName', {}).get('name', 'Unknown')
                        })
                    else:
                        ultimate_children.append({
                            'lei': child.get('lei', child.get('id', '')),
                            'name': child.get('name', 'Unknown')
                        })
        
        # Extract registration authorities (FDIC cert, etc.)
        registration_authorities = []
        registrations = entity.get('registration', {}).get('authorities', [])
        for reg in registrations:
            registration_authorities.append({
                'authority': reg.get('authorityName', ''),
                'registration_id': reg.get('registrationId', '')
            })
        
        return {
            'available': True,
            'legal_name': legal_name,
            'lei': entity.get('id', ''),
            'headquarters': {
                'city': headquarters_address.get('city', ''),
                'state': headquarters_address.get('region', ''),
                'country': headquarters_address.get('country', '')
            },
            'legal_address': {
                'city': legal_address.get('city', ''),
                'state': legal_address.get('region', ''),
                'country': legal_address.get('country', '')
            },
            'direct_parent': direct_parent,
            'ultimate_parent': ultimate_parent,
            'children': direct_children + ultimate_children,  # Combined list for section builder
            'subsidiaries': {
                'direct': direct_children,
                'ultimate': ultimate_children,
                'total_direct': len(direct_children),
                'total_ultimate': len(ultimate_children)
            },
            'registration_authorities': registration_authorities
        }


class ComplaintDataProcessor:
    """Process CFPB consumer complaint data."""
    
    @staticmethod
    def analyze_complaints(complaints: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate and analyze complaint patterns.
        
        Args:
            complaints: List of complaint records
            
        Returns:
            Structured complaint analysis
        """
        if not complaints:
            return {
                'summary': {
                    'total': 0,
                    'available': False
                }
            }
        
        # Summary statistics
        total = len(complaints)
        
        # Date range
        dates = [c.get('date_received', '') for c in complaints if c.get('date_received')]
        date_range = {
            'earliest': min(dates) if dates else None,
            'latest': max(dates) if dates else None
        }
        
        # Response analysis
        timely_responses = sum(1 for c in complaints if c.get('timely', '').lower() == 'yes')
        timely_rate = (timely_responses / total * 100) if total > 0 else 0
        
        disputed = sum(1 for c in complaints if c.get('consumer_disputed', '').lower() == 'yes')
        disputed_rate = (disputed / total * 100) if total > 0 else 0
        
        # Top issues
        issues = defaultdict(int)
        for c in complaints:
            issue = c.get('issue', '')
            if issue:
                issues[issue] += 1
        
        top_issues = sorted(issues.items(), key=lambda x: x[1], reverse=True)[:10]
        top_issues_list = [{'issue': issue, 'count': count, 'pct': (count / total * 100)} 
                          for issue, count in top_issues]
        
        # Top products
        products = defaultdict(int)
        for c in complaints:
            product = c.get('product', '')
            if product:
                products[product] += 1
        
        top_products = sorted(products.items(), key=lambda x: x[1], reverse=True)[:10]
        top_products_list = [{'product': product, 'count': count, 'pct': (count / total * 100)} 
                            for product, count in top_products]
        
        # Geographic distribution
        states = defaultdict(int)
        for c in complaints:
            state = c.get('state', '')
            if state:
                states[state] += 1
        
        state_distribution = dict(sorted(states.items(), key=lambda x: x[1], reverse=True))
        
        # Trend data (group by month)
        monthly_counts = defaultdict(int)
        for c in complaints:
            date_str = c.get('date_received', '')
            if date_str and len(date_str) >= 7:
                month_key = date_str[:7]  # YYYY-MM
                monthly_counts[month_key] += 1
        
        trend_data = dict(sorted(monthly_counts.items()))
        
        return {
            'summary': {
                'total': total,
                'date_range': date_range,
                'timely_response_rate': round(timely_rate, 1),
                'disputed_rate': round(disputed_rate, 1),
                'available': True
            },
            'top_issues': top_issues_list,
            'top_products': top_products_list,
            'geographic_distribution': state_distribution,
            'trend_data': trend_data
        }


class AnalystRatingsProcessor:
    """Process Seeking Alpha analyst ratings data."""
    
    @staticmethod
    def process_analyst_ratings(seeking_alpha_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Structure analyst opinion data.
        
        Args:
            seeking_alpha_data: Seeking Alpha API response
            
        Returns:
            Structured analyst ratings data
        """
        if not seeking_alpha_data:
            return {'available': False}
        
        ratings = seeking_alpha_data.get('ratings', {}) or {}
        profile = seeking_alpha_data.get('profile') or {}
        
        # Rating distribution
        sell_side = ratings.get('sell_side_ratings', []) if ratings else []
        buy_count = sum(1 for r in sell_side if r.get('rating', '').upper() in ['BUY', 'STRONG BUY'])
        hold_count = sum(1 for r in sell_side if r.get('rating', '').upper() == 'HOLD')
        sell_count = sum(1 for r in sell_side if r.get('rating', '').upper() in ['SELL', 'STRONG SELL'])
        
        distribution = {
            'buy': buy_count,
            'hold': hold_count,
            'sell': sell_count,
            'total': len(sell_side)
        }
        
        # Price targets
        price_targets = []
        for r in sell_side:
            target = r.get('price_target')
            if target:
                price_targets.append(float(target))
        
        price_target = {
            'current': profile.get('current_price', 0) if profile else 0,
            'average': sum(price_targets) / len(price_targets) if price_targets else None,
            'high': max(price_targets) if price_targets else None,
            'low': min(price_targets) if price_targets else None
        }
        
        # Earnings data
        earnings = seeking_alpha_data.get('earnings') or {}
        earnings_data = {
            'last_quarter': earnings.get('last_earnings') if earnings else None,
            'next_report': earnings.get('next_earnings_date') if earnings else None,
            'vs_estimate': None  # Would need to calculate from earnings data
        }
        
        return {
            'available': True,
            'distribution': distribution,
            'quant_rating': ratings.get('quant_rating'),
            'author_rating': ratings.get('author_rating'),
            'price_target': price_target,
            'earnings': earnings_data
        }


class LitigationProcessor:
    """Process CourtListener litigation data."""
    
    @staticmethod
    def process_litigation(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Filter and categorize cases for material litigation only.
        
        Args:
            cases: List of court docket records
            
        Returns:
            Structured litigation data
        """
        if not cases:
            return {
                'summary': {
                    'total_cases': 0,
                    'available': False
                }
            }
        
        # Filter for material cases (fair lending, class action, regulatory, significant amounts)
        material_cases = []
        for case in cases:
            case_type = case.get('case_type', '').upper()
            description = (case.get('description', '') or '').upper()
            
            is_material = (
                'FAIR LENDING' in description or
                'DISCRIMINAT' in description or
                'CLASS ACTION' in case_type or
                'REGULATORY' in description or
                'ENFORCEMENT' in description
            )
            
            if is_material:
                material_cases.append(case)
        
        # Categorize by type
        by_type = defaultdict(list)
        for case in material_cases:
            case_type = case.get('case_type', 'Other')
            by_type[case_type].append(case)
        
        # Group by court
        by_court = defaultdict(list)
        for case in material_cases:
            court = case.get('court', 'Unknown')
            by_court[court].append(case)
        
        # Status counts
        active = sum(1 for c in material_cases if c.get('status', '').lower() == 'active')
        closed = len(material_cases) - active
        
        return {
            'summary': {
                'total_cases': len(material_cases),
                'active_cases': active,
                'closed_cases': closed,
                'available': True
            },
            'by_type': dict(by_type),
            'by_court': dict(by_court),
            'recent_cases': material_cases[:10],
            'significant_settlements': []  # Would need to extract from case details
        }


class NewsProcessor:
    """Process news articles from NewsAPI and Seeking Alpha."""
    
    # Keyword categories for news classification
    EXECUTIVE_KEYWORDS = ['ceo', 'cfo', 'president', 'resign', 'appoint', 'hire', 'depart', 'executive']
    STRATEGY_KEYWORDS = ['acquisition', 'merger', 'expand', 'launch', 'partner', 'strategic']
    REGULATORY_KEYWORDS = ['fine', 'penalty', 'consent order', 'investigation', 'compliance', 'regulatory']
    FINANCIAL_KEYWORDS = ['earnings', 'profit', 'loss', 'revenue', 'quarter', 'financial']
    CONTROVERSY_KEYWORDS = ['lawsuit', 'scandal', 'fraud', 'discriminat', 'redlining', 'controversy']
    
    @staticmethod
    def deduplicate_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate articles based on URL and similar titles."""
        seen_urls = set()
        seen_titles = set()
        unique = []

        for article in articles:
            url = article.get('url', '')
            title = (article.get('title', '') or '').strip().lower()

            # Skip if exact URL match
            if url and url in seen_urls:
                continue

            # Check for similar titles (normalize for comparison)
            # Remove common prefixes/suffixes and punctuation
            normalized_title = re.sub(r'[^\w\s]', '', title)
            normalized_title = re.sub(r'\s+', ' ', normalized_title).strip()

            # Also create a shorter "fingerprint" from first 50 chars
            title_fingerprint = normalized_title[:50] if normalized_title else ''

            # Skip if we've seen very similar title
            if title_fingerprint and title_fingerprint in seen_titles:
                continue

            # Add to unique list
            if url:
                seen_urls.add(url)
            if title_fingerprint:
                seen_titles.add(title_fingerprint)
            unique.append(article)

        return unique
    
    @staticmethod
    def filter_by_keywords(articles: List[Dict[str, Any]], keywords: List[str]) -> List[Dict[str, Any]]:
        """Filter articles containing any of the keywords."""
        filtered = []
        for article in articles:
            title = (article.get('title', '') or '').lower()
            description = (article.get('description', '') or '').lower()
            content = title + ' ' + description

            if any(keyword.lower() in content for keyword in keywords):
                filtered.append(article)
        return filtered

    @staticmethod
    def extract_related_names(gleif_data: Dict[str, Any]) -> List[str]:
        """
        Extract parent and subsidiary names from GLEIF corporate structure.

        Args:
            gleif_data: GLEIF entity data with parent/children info

        Returns:
            List of related company names
        """
        related_names = []

        if not gleif_data:
            return related_names

        # Get parent name
        parent_data = gleif_data.get('parent', {})
        if isinstance(parent_data, dict):
            parent_name = parent_data.get('name', '')
            if parent_name and parent_name != 'Unknown':
                related_names.append(parent_name)

        # Get children names (both direct and ultimate)
        children_data = gleif_data.get('children', {})
        if isinstance(children_data, dict):
            for child in children_data.get('direct', []):
                if isinstance(child, dict):
                    name = child.get('name', '')
                    if name and name != 'Unknown':
                        related_names.append(name)
            for child in children_data.get('ultimate', []):
                if isinstance(child, dict):
                    name = child.get('name', '')
                    if name and name != 'Unknown':
                        related_names.append(name)

        return related_names

    @staticmethod
    def build_search_terms(company_name: str) -> List[str]:
        """
        Build search terms from a company name using fuzzy matching logic.

        Args:
            company_name: Company name (e.g., "Fifth Third Bank")

        Returns:
            List of search terms to match against
        """
        if not company_name:
            return []

        # Common words to filter out when building search terms
        common_words = {
            'first', 'bank', 'american', 'national', 'united', 'federal',
            'trust', 'financial', 'bancorp', 'bancshares', 'corporation',
            'corp', 'inc', 'llc', 'company', 'co', 'services', 'group',
            'holdings', 'holding', 'the', 'of', 'and', 'na', 'fsb'
        }

        name_lower = company_name.lower().strip()
        search_terms = [name_lower]

        # Remove common suffixes for cleaner matching
        for suffix in [', n.a.', ' n.a.', ', na', ' na', ', inc', ' inc',
                       ', llc', ' llc', ' corp', ' corporation', ' bancorp',
                       ' bancshares', ' financial corporation']:
            if name_lower.endswith(suffix):
                name_lower = name_lower[:-len(suffix)].strip()
                search_terms.append(name_lower)
                break

        words = name_lower.split()

        # Add first 2 words if meaningful
        if len(words) >= 2:
            first_two = ' '.join(words[:2])
            search_terms.append(first_two)

        # Add first 3 words for longer names
        if len(words) >= 3:
            first_three = ' '.join(words[:3])
            search_terms.append(first_three)

        # Add distinctive individual words (longer than 4 chars, not common)
        for word in words:
            if len(word) > 4 and word not in common_words:
                search_terms.append(word)

        # Remove duplicates while preserving order
        return list(dict.fromkeys(search_terms))

    @staticmethod
    def filter_by_primary_subject(
        articles: List[Dict[str, Any]],
        company_name: str,
        related_names: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Filter articles where the company or related entities are the primary subject.

        An article passes if the company name (or key words from it, or related
        parent/subsidiary names) appears in:
        - The title (headline), OR
        - The first 200 characters of the description

        Args:
            articles: List of news articles
            company_name: Primary company name to search for
            related_names: Optional list of parent/subsidiary names to also match

        Returns:
            Filtered list of articles where company/related entity is primary subject
        """
        if not company_name:
            return articles

        # Build search terms for primary company
        all_search_terms = NewsProcessor.build_search_terms(company_name)

        # Add search terms for related companies (parent/subsidiaries)
        if related_names:
            for related_name in related_names:
                related_terms = NewsProcessor.build_search_terms(related_name)
                all_search_terms.extend(related_terms)

        # Remove duplicates
        all_search_terms = list(dict.fromkeys(all_search_terms))

        filtered = []
        for article in articles:
            title = (article.get('title', '') or '').lower()
            description = (article.get('description', '') or '').lower()

            # Check title first (most important)
            title_match = any(term in title for term in all_search_terms)

            # Check first 200 chars of description (expanded from 150)
            first_paragraph = description[:200] if description else ''
            desc_match = any(term in first_paragraph for term in all_search_terms)

            if title_match or desc_match:
                # Mark how it matched for potential sorting
                article['_relevance'] = 'title' if title_match else 'description'
                filtered.append(article)

        # Sort: title matches first, then by date (newest first within each group)
        # First sort by date (newest first), then stable sort by relevance
        filtered.sort(key=lambda x: x.get('publishedAt', '') or '', reverse=True)
        filtered.sort(key=lambda x: 0 if x.get('_relevance') == 'title' else 1)

        return filtered

    @staticmethod
    def process_news(newsapi_articles: List[Dict[str, Any]],
                     seeking_alpha_articles: List[Dict[str, Any]],
                     company_name: str = None,
                     related_names: List[str] = None) -> Dict[str, Any]:
        """
        Deduplicate, filter by relevance, and categorize news articles.

        Args:
            newsapi_articles: Articles from NewsAPI
            seeking_alpha_articles: Articles from Seeking Alpha
            company_name: Company name for relevance filtering (filters to primary subject)
            related_names: Optional list of parent/subsidiary names to also match

        Returns:
            Structured news data
        """
        all_articles = NewsProcessor.deduplicate_articles(
            (newsapi_articles or []) + (seeking_alpha_articles or [])
        )

        # Filter to articles where company or related entities are the primary subject
        if company_name and all_articles:
            original_count = len(all_articles)
            all_articles = NewsProcessor.filter_by_primary_subject(
                all_articles, company_name, related_names
            )
            filtered_count = len(all_articles)
            if original_count != filtered_count:
                import logging
                related_info = f" + {len(related_names)} related" if related_names else ""
                logging.getLogger(__name__).info(
                    f"News filtered: {original_count} -> {filtered_count} articles (company{related_info} as primary subject)"
                )

        if not all_articles:
            return {
                'summary': {
                    'total': 0,
                    'available': False
                }
            }
        
        # Get date range
        dates = [a.get('publishedAt', '') for a in all_articles if a.get('publishedAt')]
        date_range = {
            'earliest': min(dates) if dates else None,
            'latest': max(dates) if dates else None
        }
        
        # Get unique sources
        sources = set()
        for article in all_articles:
            source = article.get('source', {})
            if isinstance(source, dict):
                sources.add(source.get('name', 'Unknown'))
            else:
                sources.add(str(source))
        
        # Categorize articles
        categorized = {
            'executive': NewsProcessor.filter_by_keywords(all_articles, NewsProcessor.EXECUTIVE_KEYWORDS),
            'strategy': NewsProcessor.filter_by_keywords(all_articles, NewsProcessor.STRATEGY_KEYWORDS),
            'regulatory': NewsProcessor.filter_by_keywords(all_articles, NewsProcessor.REGULATORY_KEYWORDS),
            'financial': NewsProcessor.filter_by_keywords(all_articles, NewsProcessor.FINANCIAL_KEYWORDS),
            'controversy': NewsProcessor.filter_by_keywords(all_articles, NewsProcessor.CONTROVERSY_KEYWORDS)
        }
        
        # Sort by date (most recent first) - no limit on articles
        all_articles_sorted = sorted(
            all_articles,
            key=lambda x: x.get('publishedAt', ''),
            reverse=True
        )

        return {
            'summary': {
                'total': len(all_articles),
                'date_range': date_range,
                'sources': list(sources),
                'available': True
            },
            'categorized': categorized,
            'articles': all_articles_sorted,  # Return all articles, no limit
            'recent': all_articles_sorted[:20]  # Keep for backward compatibility
        }

