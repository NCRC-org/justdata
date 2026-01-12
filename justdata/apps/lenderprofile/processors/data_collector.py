#!/usr/bin/env python3
"""
Data Collector for LenderProfile
Orchestrates data collection from all APIs for a complete institution profile.
"""

import logging
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from apps.lenderprofile.services.fdic_client import FDICClient
from apps.lenderprofile.services.ncua_client import NCUAClient
from apps.lenderprofile.services.sec_client import SECClient
from apps.lenderprofile.services.gleif_client import GLEIFClient
from apps.lenderprofile.services.courtlistener_client import CourtListenerClient
from apps.lenderprofile.services.newsapi_client import NewsAPIClient
from apps.lenderprofile.services.google_news_client import GoogleNewsClient
from apps.lenderprofile.services.duckduckgo_client import DuckDuckGoClient
# TheOrg API removed - not using organizational data
from apps.lenderprofile.services.cfpb_client import CFPBClient
from apps.lenderprofile.services.federal_register_client import FederalRegisterClient
from apps.lenderprofile.services.regulations_client import RegulationsGovClient
from apps.lenderprofile.services.federal_reserve_client import FederalReserveClient
from apps.lenderprofile.services.seeking_alpha_client import SeekingAlphaClient
from apps.lenderprofile.services.bq_hmda_client import BigQueryHMDAClient
from apps.lenderprofile.services.bq_cra_client import BigQueryCRAClient
from apps.lenderprofile.services.congress_trading_client import CongressTradingClient
from apps.lenderprofile.cache.cache_manager import CacheManager
from apps.lenderprofile.processors.corporate_hierarchy import CorporateHierarchy
from apps.lenderprofile.processors.ai_entity_resolver import AIEntityResolver
from apps.lenderprofile.processors.data_analysts import DataSourceAnalysts, compile_analyst_summaries

from apps.lenderprofile.processors.ixbrl_parser import IXBRLParser

logger = logging.getLogger(__name__)


class DataCollector:
    """
    Collects data from all APIs for a complete institution profile.
    """
    
    def __init__(self):
        """Initialize data collector with all API clients."""
        self.fdic_client = FDICClient()
        self.ncua_client = NCUAClient()
        self.sec_client = SECClient()
        self.gleif_client = GLEIFClient()
        self.courtlistener_client = CourtListenerClient()
        self.newsapi_client = NewsAPIClient()
        self.google_news_client = GoogleNewsClient()
        self.duckduckgo_client = DuckDuckGoClient()
        # TheOrg client removed - not using organizational data
        self.cfpb_client = CFPBClient()
        self.federal_register_client = FederalRegisterClient()
        self.regulations_client = RegulationsGovClient()
        self.federal_reserve_client = FederalReserveClient()
        self.seeking_alpha_client = SeekingAlphaClient()
        self.hmda_client = BigQueryHMDAClient()
        self.cra_client = BigQueryCRAClient()
        self.congress_trading_client = CongressTradingClient()
        self.cache = CacheManager()
        self.hierarchy = CorporateHierarchy()
        self.ai_resolver = AIEntityResolver()
        self.data_analysts = DataSourceAnalysts()
    
    def _get_corporate_family(self, lei: str, institution_name: str) -> Dict[str, Any]:
        """
        Get complete corporate family using GLEIF API.

        Returns structure with all entities to query for data.
        Each entity is tagged with its relationship (parent, subsidiary, sibling).
        """
        family = {
            'queried_entity': {'lei': lei, 'name': institution_name, 'relationship': 'queried'},
            'ultimate_parent': None,
            'all_entities': [{'lei': lei, 'name': institution_name, 'relationship': 'queried'}] if lei else [],
            'all_names': [institution_name],
            'all_leis': [lei] if lei else [],
            'parent_name': None,
            'parent_lei': None
        }

        if not lei:
            # Try to find LEI by name - select best match from results
            gleif_results = self.gleif_client.search_by_name(institution_name, limit=10)
            if gleif_results:
                # Score results to find best match
                best_match = None
                best_score = -1
                search_upper = institution_name.upper()

                for result in gleif_results:
                    result_name = result.get('legal_name', '').upper()
                    country = result.get('country', '').upper()
                    score = 0

                    # Exact match is best
                    if result_name == search_upper:
                        score += 100

                    # National Association (N.A.) banks are likely the main entity
                    if 'NATIONAL ASSOCIATION' in result_name or ', N.A.' in result_name:
                        score += 50

                    # US-based entities preferred
                    if country == 'US':
                        score += 30

                    # Contains the search term
                    if search_upper in result_name:
                        score += 20

                    # Penalize foreign branches/subsidiaries
                    if 'GERMAN' in result_name or 'UK ' in result_name or 'LONDON' in result_name:
                        score -= 40
                    if 'GESCHÄFTSSTELLE' in result_name or 'BRANCH' in result_name:
                        score -= 30

                    if score > best_score:
                        best_score = score
                        best_match = result

                if best_match:
                    lei = best_match.get('lei')
                    family['queried_entity']['lei'] = lei
                    family['all_leis'] = [lei] if lei else []
                    # CRITICAL: Add queried entity to all_entities (wasn't added at init since LEI was None)
                    family['all_entities'] = [{'lei': lei, 'name': institution_name, 'relationship': 'queried'}] if lei else []
                    logger.info(f"Found LEI {lei} for {institution_name} via GLEIF search (score: {best_score}, name: {best_match.get('legal_name', 'N/A')})")

        if lei:
            try:
                gleif_family = self.gleif_client.get_corporate_family(lei)

                # Add ultimate parent
                if gleif_family.get('ultimate_parent'):
                    parent = gleif_family['ultimate_parent']
                    parent['relationship'] = 'ultimate_parent'
                    family['ultimate_parent'] = parent
                    family['parent_name'] = parent.get('name')
                    family['parent_lei'] = parent.get('lei')

                    # Add parent to all_entities if not already there
                    if parent.get('lei') and parent['lei'] not in family['all_leis']:
                        family['all_entities'].append(parent)
                        family['all_leis'].append(parent['lei'])
                        if parent.get('name'):
                            family['all_names'].append(parent['name'])

                # Add siblings (other subsidiaries of parent)
                for sib in gleif_family.get('siblings', []):
                    sib['relationship'] = 'sibling'
                    if sib.get('lei') and sib['lei'] not in family['all_leis']:
                        family['all_entities'].append(sib)
                        family['all_leis'].append(sib['lei'])
                        if sib.get('name'):
                            family['all_names'].append(sib['name'])

                # Add children (subsidiaries of queried entity)
                for child in gleif_family.get('children', []):
                    child['relationship'] = 'subsidiary'
                    if child.get('lei') and child['lei'] not in family['all_leis']:
                        family['all_entities'].append(child)
                        family['all_leis'].append(child['lei'])
                        if child.get('name'):
                            family['all_names'].append(child['name'])

                # Add any additional entities from the full tree
                for entity in gleif_family.get('all_entities', []):
                    if entity.get('lei') and entity['lei'] not in family['all_leis']:
                        if not entity.get('relationship'):
                            entity['relationship'] = 'related'
                        family['all_entities'].append(entity)
                        family['all_leis'].append(entity['lei'])
                        if entity.get('name'):
                            family['all_names'].append(entity['name'])

                logger.info(f"Corporate family for {institution_name}: {len(family['all_entities'])} entities, "
                           f"parent={family.get('parent_name', 'N/A')}")

            except Exception as e:
                logger.warning(f"Error getting corporate family for {lei}: {e}")

        return family

    def _aggregate_news_by_keywords(self, news_keywords: List[str], institution_name: str) -> Dict[str, Any]:
        """Query news using AI-resolved keywords instead of all entities.

        This is much faster than querying all 24 subsidiaries - instead uses
        AI-determined keywords like ["Bank of America", "BofA"] for focused search.

        Args:
            news_keywords: List of search keywords from AI entity resolution
            institution_name: Primary institution name for fallback
        """
        all_articles = []
        seen_titles = set()

        # Limit to first 3 keywords to prevent timeout
        keywords_to_search = news_keywords[:3] if news_keywords else [institution_name]

        logger.info(f"News searching for keywords: {keywords_to_search}")

        for keyword in keywords_to_search:
            if not keyword:
                continue

            try:
                news_data = self._get_news_data(keyword)
                articles = news_data.get('articles', [])

                for article in articles:
                    # Deduplicate by title
                    title = article.get('title', '')
                    if title and title not in seen_titles:
                        seen_titles.add(title)
                        # Tag with search keyword
                        article['source_entity'] = keyword
                        article['entity_relationship'] = 'primary'
                        all_articles.append(article)

            except Exception as e:
                logger.warning(f"Error getting news for {keyword}: {e}")

        logger.info(f"News search found {len(all_articles)} total articles")

        return {
            'articles': all_articles,
            'total_articles': len(all_articles),
            'source': 'aggregated'
        }

    def _aggregate_cfpb_by_names(self, brand_names: List[str], institution_name: str) -> Dict[str, Any]:
        """Query CFPB complaints for AI-determined consumer-facing brand names.

        Instead of searching all 20+ subsidiaries, use AI-determined brand names
        like ["Bank of America", "BofA", "Merrill Lynch"] for faster, more accurate results.

        Args:
            brand_names: List of consumer-facing brand names from AI resolution
            institution_name: Primary institution name for fallback
        """
        all_complaints = []
        total_count = 0
        by_entity = {}
        seen_cfpb_names = set()  # Track which CFPB company names we've already queried

        # Track merged data from all brand names
        merged_by_year = {}
        all_topics = {}
        all_products = {}
        cfpb_company_name = None
        national_by_year = {}
        categories_by_year = {}
        latest_complaint_date = None

        logger.info(f"CFPB searching for brand names: {brand_names}")

        for brand_name in brand_names:
            if not brand_name:
                continue

            try:
                cfpb_data = self._get_cfpb_complaints(brand_name)
                entity_total = cfpb_data.get('total', 0)
                entity_cfpb_name = cfpb_data.get('cfpb_company_name')

                # Skip if we've already seen this CFPB company name (dedup)
                if entity_cfpb_name and entity_cfpb_name in seen_cfpb_names:
                    logger.info(f"Skipping duplicate CFPB name: {entity_cfpb_name}")
                    continue

                if entity_cfpb_name:
                    seen_cfpb_names.add(entity_cfpb_name)

                if entity_total > 0:
                    by_entity[brand_name] = {
                        'count': entity_total,
                        'cfpb_name': entity_cfpb_name,
                        'trends': cfpb_data.get('trends', {}),
                        'top_categories': cfpb_data.get('top_categories', [])
                    }
                    total_count += entity_total

                    # Merge by_year data
                    entity_trends = cfpb_data.get('trends', {})
                    for year, count in entity_trends.get('by_year', {}).items():
                        merged_by_year[year] = merged_by_year.get(year, 0) + count

                    # Merge main_topics
                    for topic in cfpb_data.get('main_topics', []):
                        if isinstance(topic, dict):
                            topic_name = topic.get('topic') or topic.get('issue') or str(topic)
                            topic_count = topic.get('count', 1)
                        else:
                            topic_name = str(topic)
                            topic_count = 1
                        if topic_name:
                            all_topics[topic_name] = all_topics.get(topic_name, 0) + topic_count

                    # Merge main_products
                    for product in cfpb_data.get('main_products', []):
                        if isinstance(product, dict):
                            product_name = product.get('product') or product.get('name') or str(product)
                            product_count = product.get('count', 1)
                        else:
                            product_name = str(product)
                            product_count = 1
                        if product_name:
                            all_products[product_name] = all_products.get(product_name, 0) + product_count

                    # Use first CFPB company name and national data
                    if not cfpb_company_name and entity_cfpb_name:
                        cfpb_company_name = entity_cfpb_name
                    if not national_by_year and cfpb_data.get('national_by_year'):
                        national_by_year = cfpb_data.get('national_by_year', {})
                    if not categories_by_year and cfpb_data.get('categories_by_year'):
                        categories_by_year = cfpb_data.get('categories_by_year', {})

                    # Track latest complaint date
                    entity_latest = cfpb_data.get('latest_complaint_date')
                    if entity_latest and (not latest_complaint_date or entity_latest > latest_complaint_date):
                        latest_complaint_date = entity_latest

                    # Collect sample complaints
                    all_complaints.extend(cfpb_data.get('complaints', [])[:50])

            except Exception as e:
                logger.error(f"Error getting CFPB complaints for {brand_name}: {e}")
                continue

        logger.info(f"CFPB aggregation complete: {total_count} total complaints from {len(brand_names)} brand names")

        # Build sorted topic and product lists
        sorted_topics = sorted(all_topics.items(), key=lambda x: x[1], reverse=True)[:10]
        sorted_products = sorted(all_products.items(), key=lambda x: x[1], reverse=True)[:10]

        main_topics = [{'issue': t[0], 'count': t[1]} for t in sorted_topics]
        main_products = [{'product': p[0], 'count': p[1]} for p in sorted_products]

        # Determine overall trend
        sorted_years = sorted(merged_by_year.keys())
        recent_trend = 'stable'
        if len(sorted_years) >= 2:
            recent_years = sorted_years[-3:] if len(sorted_years) >= 3 else sorted_years[-2:]
            if len(recent_years) >= 2:
                first_count = merged_by_year.get(recent_years[0], 0)
                last_count = merged_by_year.get(recent_years[-1], 0)
                if first_count > 0:
                    change_pct = ((last_count - first_count) / first_count) * 100
                    if change_pct > 10:
                        recent_trend = 'increasing'
                    elif change_pct < -10:
                        recent_trend = 'decreasing'

        return {
            'total': total_count,
            'complaints': all_complaints[:100],
            'by_entity': by_entity,
            'trends': {
                'by_year': merged_by_year,
                'recent_trend': recent_trend,
                'years_analyzed': sorted_years
            },
            'main_topics': main_topics,
            'main_products': main_products,
            'cfpb_company_name': cfpb_company_name,
            'national_by_year': national_by_year,
            'categories_by_year': categories_by_year,
            'latest_complaint_date': latest_complaint_date,
            'brand_names_searched': brand_names,
            'source': 'ai_resolved_brands'
        }

    def _aggregate_cfpb_all_entities(self, family: Dict[str, Any]) -> Dict[str, Any]:
        """Query CFPB complaints for US-based entities in corporate family only.

        DEPRECATED: Use _aggregate_cfpb_by_names instead for faster, more accurate results.

        CFPB only has jurisdiction over US consumer complaints, so we skip
        foreign subsidiaries to improve performance.
        """
        all_complaints = []
        total_count = 0
        by_entity = {}
        skipped_foreign = 0

        # Track merged data from all entities
        merged_by_year = {}
        all_topics = {}
        all_products = {}
        cfpb_company_name = None
        national_by_year = {}
        categories_by_year = {}
        latest_complaint_date = None

        for entity in family.get('all_entities', []):
            entity_name = entity.get('name')
            relationship = entity.get('relationship', 'related')
            country = (entity.get('country') or '').upper()

            if not entity_name:
                continue

            # Only query CFPB for US-based entities (CFPB has no jurisdiction over foreign entities)
            if country and country not in ('US', 'USA', ''):
                skipped_foreign += 1
                logger.debug(f"Skipping CFPB query for non-US entity: {entity_name} ({country})")
                continue

            try:
                cfpb_data = self._get_cfpb_complaints(entity_name)
                complaints = cfpb_data.get('complaints', [])
                entity_total = cfpb_data.get('total', 0)

                if entity_total > 0:
                    by_entity[entity_name] = {
                        'count': entity_total,
                        'relationship': relationship,
                        'trends': cfpb_data.get('trends', {}),
                        'top_categories': cfpb_data.get('top_categories', [])
                    }
                    total_count += entity_total

                    # Merge by_year data
                    entity_trends = cfpb_data.get('trends', {})
                    for year, count in entity_trends.get('by_year', {}).items():
                        merged_by_year[year] = merged_by_year.get(year, 0) + count

                    # Merge main_topics
                    for topic in cfpb_data.get('main_topics', []):
                        if isinstance(topic, dict):
                            topic_name = topic.get('topic') or topic.get('issue') or str(topic)
                            topic_count = topic.get('count', 1)
                        else:
                            topic_name = str(topic)
                            topic_count = 1
                        if topic_name:
                            all_topics[topic_name] = all_topics.get(topic_name, 0) + topic_count

                    # Merge main_products
                    for product in cfpb_data.get('main_products', []):
                        if isinstance(product, dict):
                            product_name = product.get('product') or product.get('name') or str(product)
                            product_count = product.get('count', 1)
                        else:
                            product_name = str(product)
                            product_count = 1
                        if product_name:
                            all_products[product_name] = all_products.get(product_name, 0) + product_count

                    # Use national data from first entity with data
                    if not national_by_year and cfpb_data.get('national_by_year'):
                        national_by_year = cfpb_data['national_by_year']
                    if not categories_by_year and cfpb_data.get('categories_by_year'):
                        categories_by_year = cfpb_data['categories_by_year']

                    # Use cfpb_company_name from queried entity if available
                    if relationship == 'queried' and cfpb_data.get('cfpb_company_name'):
                        cfpb_company_name = cfpb_data['cfpb_company_name']
                    elif not cfpb_company_name and cfpb_data.get('cfpb_company_name'):
                        cfpb_company_name = cfpb_data['cfpb_company_name']

                    # Track latest complaint date
                    entity_latest = cfpb_data.get('latest_complaint_date')
                    if entity_latest and (not latest_complaint_date or entity_latest > latest_complaint_date):
                        latest_complaint_date = entity_latest

                for complaint in complaints[:50]:  # Limit per entity
                    complaint['source_entity'] = entity_name
                    complaint['entity_relationship'] = relationship
                    all_complaints.append(complaint)

            except Exception as e:
                logger.warning(f"Error getting CFPB data for {entity_name}: {e}")

        if skipped_foreign > 0:
            logger.info(f"CFPB aggregation: skipped {skipped_foreign} foreign entities (CFPB US-only)")

        # Sort and format topics/products as lists
        sorted_topics = sorted(all_topics.items(), key=lambda x: x[1], reverse=True)
        sorted_products = sorted(all_products.items(), key=lambda x: x[1], reverse=True)

        main_topics = [{'topic': t, 'count': c} for t, c in sorted_topics[:10]]
        main_products = [{'product': p, 'count': c} for p, c in sorted_products[:10]]

        # Determine recent trend based on merged by_year data
        recent_trend = 'stable'
        years_sorted = sorted(merged_by_year.keys())
        if len(years_sorted) >= 2:
            recent_year = years_sorted[-1]
            prev_year = years_sorted[-2]
            recent_count = merged_by_year.get(recent_year, 0)
            prev_count = merged_by_year.get(prev_year, 0)
            if prev_count > 0:
                change_pct = (recent_count - prev_count) / prev_count * 100
                if change_pct > 10:
                    recent_trend = 'increasing'
                elif change_pct < -10:
                    recent_trend = 'decreasing'

        logger.info(f"CFPB aggregation complete: {total_count} total complaints from {len(by_entity)} entities")

        return {
            'complaints': all_complaints,
            'total': total_count,
            'by_entity': by_entity,
            'source': 'aggregated',
            # Additional fields for report builder
            'trends': {
                'by_year': merged_by_year,
                'recent_trend': recent_trend
            },
            'main_topics': main_topics,
            'main_products': main_products,
            'cfpb_company_name': cfpb_company_name,
            'latest_complaint_date': latest_complaint_date,
            'national_by_year': national_by_year,
            'categories_by_year': categories_by_year
        }

    def _aggregate_hmda_all_entities(self, family: Dict[str, Any], institution_name: str) -> Dict[str, Any]:
        """Query HMDA for all LEIs in corporate family, tagged by source entity.

        Returns merged data with top-level by_year, by_purpose_year, etc. for report builder,
        plus by_entity breakdown for attribution.
        """
        all_data = {
            'by_entity': {},
            'combined_totals': {},
            'source': 'aggregated',
            # Top-level merged data for report builder
            'by_year': {},
            'by_purpose_year': {},
            'states_by_year': {},
            'national_by_year': {},
            'national_by_purpose_year': {},
            'top_metros': []
        }

        for entity in family.get('all_entities', []):
            entity_lei = entity.get('lei')
            entity_name = entity.get('name', 'Unknown')
            relationship = entity.get('relationship', 'related')

            if not entity_lei:
                continue

            try:
                hmda_data = self._get_hmda_footprint([entity_lei], entity_name)

                if hmda_data and hmda_data.get('total_applications', 0) > 0:
                    hmda_data['entity_relationship'] = relationship
                    all_data['by_entity'][entity_name] = hmda_data

                    # Combine totals
                    for key in ['total_applications', 'total_originations']:
                        current = all_data['combined_totals'].get(key, 0)
                        all_data['combined_totals'][key] = current + hmda_data.get(key, 0)

                    # Merge by_year data (add application counts per year)
                    for year, count in hmda_data.get('by_year', {}).items():
                        all_data['by_year'][year] = all_data['by_year'].get(year, 0) + count

                    # Merge by_purpose_year data
                    for purpose, year_data in hmda_data.get('by_purpose_year', {}).items():
                        if purpose not in all_data['by_purpose_year']:
                            all_data['by_purpose_year'][purpose] = {}
                        for year, count in year_data.items():
                            all_data['by_purpose_year'][purpose][year] = (
                                all_data['by_purpose_year'][purpose].get(year, 0) + count
                            )

                    # Merge states_by_year data
                    for year, states in hmda_data.get('states_by_year', {}).items():
                        if year not in all_data['states_by_year']:
                            all_data['states_by_year'][year] = {}
                        if isinstance(states, dict):
                            for state, count in states.items():
                                all_data['states_by_year'][year][state] = (
                                    all_data['states_by_year'][year].get(state, 0) + count
                                )

                    # Use national data from first entity with data (it's the same for all)
                    if not all_data['national_by_year'] and hmda_data.get('national_by_year'):
                        all_data['national_by_year'] = hmda_data['national_by_year']
                    if not all_data['national_by_purpose_year'] and hmda_data.get('national_by_purpose_year'):
                        all_data['national_by_purpose_year'] = hmda_data['national_by_purpose_year']

                    # Use top_metros from queried entity (primary bank)
                    if relationship == 'queried' and hmda_data.get('top_metros'):
                        all_data['top_metros'] = hmda_data['top_metros']

            except Exception as e:
                logger.warning(f"Error getting HMDA data for {entity_name}: {e}")

        # Set total_applications for report builder
        all_data['total_applications'] = sum(all_data['by_year'].values())

        logger.info(f"Aggregated HMDA data: {len(all_data['by_entity'])} entities, "
                   f"{all_data['total_applications']} total applications across {len(all_data['by_year'])} years")

        return all_data

    def collect_all_data(self, identifiers: Dict[str, Any], institution_name: str) -> Dict[str, Any]:
        """
        Collect data from all APIs for the institution and its corporate family.

        Queries ALL entities in the corporate family (parent + subsidiaries)
        for each data source, then aggregates results with entity attribution.

        Args:
            identifiers: Resolved identifiers (fdic_cert, rssd_id, lei, etc.)
            institution_name: Institution name

        Returns:
            Complete institution data dictionary with aggregated family data
        """
        logger.info(f"Collecting data for {institution_name}")

        institution_data = {
            'institution': {
                'name': institution_name,
                'identifiers': identifiers
            },
            'identifiers': identifiers
        }

        fdic_cert = identifiers.get('fdic_cert')
        rssd_id = identifiers.get('rssd_id')
        lei = identifiers.get('lei')

        # STEP 1: Get complete corporate family (parent + all subsidiaries)
        corporate_family = self._get_corporate_family(lei, institution_name)
        institution_data['corporate_family'] = corporate_family

        # CRITICAL: Update lei if it was resolved via GLEIF search
        queried_lei = corporate_family.get('queried_entity', {}).get('lei')
        if queried_lei and not lei:
            lei = queried_lei
            identifiers['lei'] = lei
            institution_data['identifiers']['lei'] = lei
            logger.info(f"Updated identifiers with resolved LEI: {lei}")

        # STEP 2: AI Entity Resolution - determine optimal entity for each data source
        try:
            ai_entity_resolution = self.ai_resolver.resolve_entities(
                institution_name,
                corporate_family,
                identifiers
            )
            institution_data['ai_entity_resolution'] = ai_entity_resolution

            # Extract search context for downstream processes
            search_context = self.ai_resolver.generate_search_context(ai_entity_resolution)
            institution_data['search_context'] = search_context

            logger.info(f"AI Entity Resolution complete: {ai_entity_resolution.get('corporate_context', {}).get('institution_type', 'Unknown type')}")
        except Exception as e:
            logger.error(f"AI Entity Resolution failed: {e}")
            institution_data['ai_entity_resolution'] = {}
            institution_data['search_context'] = {}

        
        # Store key family info for easy access
        primary_lei = corporate_family.get('parent_lei') or lei
        primary_name = corporate_family.get('parent_name') or institution_name
        all_related_leis = corporate_family.get('all_leis', [lei] if lei else [])
        all_entity_names = corporate_family.get('all_names', [institution_name])

        logger.info(f"Corporate family: {len(all_entity_names)} entities to query")
        logger.info(f"Entity names: {all_entity_names[:5]}{'...' if len(all_entity_names) > 5 else ''}")

        # Check for corporate hierarchy (parent/child relationships) - legacy support
        hierarchy_info = None
        if lei:
            hierarchy_info = self.hierarchy.get_related_entities(lei)
            if hierarchy_info and hierarchy_info.get('hierarchy_type') != 'standalone':
                logger.info(f"Corporate hierarchy detected: {hierarchy_info.get('hierarchy_type')}")
        
        # Collect data in parallel where possible
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {}
            
            # Try to get FDIC cert from RSSD if not available (only for Call Reports API)
            # Note: We don't use FDIC Institution API - we use CFPB/GLEIF for institution data
            if not fdic_cert and rssd_id:
                logger.info(f"FDIC cert not available, trying to get it from RSSD: {rssd_id}")
                # Try to get just the cert number from FDIC API (minimal call)
                try:
                    # Use a minimal query to get just the cert number
                    fdic_results = self.fdic_client.get_institution_by_rssd(rssd_id)
                    if fdic_results and isinstance(fdic_results, dict) and fdic_results.get('CERT'):
                        fdic_cert = str(fdic_results.get('CERT'))
                        logger.info(f"Found FDIC cert {fdic_cert} from RSSD {rssd_id} (for Call Reports only)")
                except Exception as e:
                    logger.debug(f"Could not get FDIC cert from RSSD {rssd_id}: {e}")
                    # Continue without FDIC cert - Call Reports won't be available

            # Fallback: Try searching FDIC by institution name if RSSD lookup failed
            if not fdic_cert and institution_name:
                logger.info(f"Trying FDIC search by name: {institution_name}")
                try:
                    fdic_search = self.fdic_client.search_institutions(institution_name, limit=5)
                    if fdic_search:
                        # Find the best match (first result is sorted by assets)
                        for inst in fdic_search:
                            inst_data = inst.get('data', inst) if isinstance(inst, dict) else inst
                            if inst_data.get('CERT'):
                                fdic_cert = str(inst_data.get('CERT'))
                                # Also get RSSD ID for branch data if not already set
                                if not rssd_id and inst_data.get('FED_RSSD'):
                                    rssd_id = str(inst_data.get('FED_RSSD'))
                                    identifiers['rssd_id'] = rssd_id
                                    logger.info(f"Found RSSD {rssd_id} from FDIC search")
                                logger.info(f"Found FDIC cert {fdic_cert} by name search: {inst_data.get('NAME')}")
                                break
                except Exception as e:
                    logger.debug(f"Could not get FDIC cert by name search: {e}")

            # FDIC data - only use for call report (financials) API
            # Branch data comes from BigQuery SOD tables, not FDIC API
            if fdic_cert:
                # Only get financials (call report data) from FDIC
                futures['fdic_financials'] = executor.submit(
                    self._get_fdic_financials, fdic_cert
                )
                # Get basic institution info if needed (but prefer CFPB/GLEIF)
                # Note: We're not using FDIC branches - using BigQuery SOD instead
            
            # CFPB API for institution metadata (assets, type, location)
            if rssd_id or lei:
                futures['cfpb_metadata'] = executor.submit(
                    self._get_cfpb_metadata, rssd_id, lei, institution_name
                )
            
            # GLEIF data
            if lei:
                futures['gleif'] = executor.submit(
                    self._get_gleif_data, lei
                )
            
            # SEC data (if public company) - use AI-resolved SEC entity name
            # AI determines which entity files SEC reports (usually the holding company)
            sec_entity_name = ai_entity_resolution.get('entity_mapping', {}).get('sec', {}).get('name', primary_name)
            futures['sec'] = executor.submit(
                self._get_sec_data, sec_entity_name
            )

            # Seeking Alpha data (requires ticker symbol) - use SEC entity name
            futures['seeking_alpha'] = executor.submit(
                self._get_seeking_alpha_data, sec_entity_name
            )
            
            # CourtListener - query all entity names
            futures['litigation'] = executor.submit(
                self._get_litigation_data, institution_name
            )

            # NewsAPI - Use AI-resolved keywords (not all 24 subsidiaries)
            # AI determines primary keywords like "Bank of America", "BofA"
            news_keywords = ai_entity_resolution.get('news_strategy', {}).get('primary_keywords', [])
            if not news_keywords:
                news_keywords = [institution_name]
            futures['news'] = executor.submit(
                self._aggregate_news_by_keywords, news_keywords, institution_name
            )

            # TheOrg - REMOVED per user request

            # CFPB enforcement
            futures['enforcement'] = executor.submit(
                self._get_enforcement_data, institution_name
            )

            # CFPB consumer complaints - Use AI-resolved brand names (not all subsidiaries)
            # AI determines consumer-facing brand names like "Bank of America", "Merrill Lynch"
            cfpb_names = ai_entity_resolution.get('entity_mapping', {}).get('cfpb', {}).get('names', [])
            if not cfpb_names:
                # Fallback to institution name and parent name
                cfpb_names = [institution_name]
                if corporate_family.get('parent_name'):
                    cfpb_names.append(corporate_family.get('parent_name'))
            futures['cfpb_complaints'] = executor.submit(
                self._aggregate_cfpb_by_names, cfpb_names, institution_name
            )
            
            # Federal Register
            futures['federal_register'] = executor.submit(
                self._get_federal_register_data, institution_name
            )
            
            # FFIEC CRA - REMOVED per user request
            
            # Federal Reserve
            if rssd_id:
                futures['federal_reserve'] = executor.submit(
                    self._get_federal_reserve_data, rssd_id
                )
            
            # Regulations.gov
            futures['regulations'] = executor.submit(
                self._get_regulations_data, institution_name
            )

            # HMDA lending footprint data - AGGREGATE across all corporate family LEIs
            # Each entity's lending tagged with relationship (parent/subsidiary)
            futures['hmda_footprint'] = executor.submit(
                self._aggregate_hmda_all_entities, corporate_family, institution_name
            )

            # CRA Small Business Lending data
            futures['sb_lending'] = executor.submit(
                self._get_sb_lending_data, lei, fdic_cert, institution_name
            )

            # Collect results
            for key, future in futures.items():
                try:
                    # SEC data takes longer due to fetching multiple large filings
                    data_timeout = 120 if key == 'sec' else 30
                    result = future.result(timeout=data_timeout)
                    institution_data[key] = result
                    # Debug logging to verify data collection
                    if result:
                        if isinstance(result, dict):
                            result_size = len(str(result))
                            logger.info(f"Collected {key} data: {result_size} chars, keys: {list(result.keys())[:5]}")
                        elif isinstance(result, list):
                            logger.info(f"Collected {key} data: {len(result)} items")
                        else:
                            logger.info(f"Collected {key} data: {type(result).__name__}")
                    else:
                        logger.warning(f"Collected {key} data: empty/None")
                except Exception as e:
                    logger.error(f"Error collecting {key} data: {e}", exc_info=True)
                    institution_data[key] = {}
        
        # Get ticker from SEC or Seeking Alpha and add to identifiers
        ticker = None
        sec_data = institution_data.get('sec', {})
        if sec_data.get('ticker'):
            ticker = sec_data.get('ticker')
        elif institution_data.get('seeking_alpha', {}).get('ticker'):
            ticker = institution_data.get('seeking_alpha', {}).get('ticker')

        # IMPORTANT: Copy ticker and CIK to identifiers for report builder
        if ticker:
            identifiers['ticker'] = ticker
            institution_data['identifiers']['ticker'] = ticker
            if 'institution' in institution_data and 'identifiers' in institution_data['institution']:
                institution_data['institution']['identifiers']['ticker'] = ticker
        if sec_data.get('cik'):
            identifiers['sec_cik'] = sec_data.get('cik')
            institution_data['identifiers']['sec_cik'] = sec_data.get('cik')

        # Get congressional trading data (requires ticker)
        # Uses free public data from Senate/House Stock Watcher
        if ticker:
            try:
                # Use free Congress Trading Client (Senate/House Stock Watcher data)
                congressional_data = self.congress_trading_client.get_congressional_summary(ticker)
                institution_data['congressional_trading'] = congressional_data
                if congressional_data.get('has_data'):
                    logger.info(f"Collected congressional trading data for {ticker}: {congressional_data.get('total_trades')} trades (source: {congressional_data.get('data_source', 'free public data')})")
                else:
                    logger.info(f"No congressional trading data found for {ticker}")
            except Exception as e:
                logger.error(f"Error collecting congressional trading data for {ticker}: {e}")
                institution_data['congressional_trading'] = {'has_data': False, 'total_trades': 0}
        else:
            logger.info(f"No ticker symbol available for congressional trading lookup")
            institution_data['congressional_trading'] = {'has_data': False, 'total_trades': 0, 'no_ticker': True}
        
        # Add hierarchy information
        if hierarchy_info:
            institution_data['hierarchy'] = {
                'primary_lei': primary_lei,
                'primary_name': primary_name,
                'hierarchy_type': hierarchy_info.get('hierarchy_type'),
                'parent': hierarchy_info.get('parent'),
                'children': hierarchy_info.get('children', []),
                'all_entities': all_related_leis,
                'entity_map': self.hierarchy.get_all_entity_names(lei) if lei else {}
            }
            # Keep the original institution name - don't replace with parent holding company
            # Store parent info separately for context but report should focus on searched entity
            if primary_name != institution_name:
                institution_data['institution']['parent_name'] = primary_name
                institution_data['institution']['parent_lei'] = primary_lei
                institution_data['institution']['is_subsidiary'] = True
                logger.info(f"Entity '{institution_name}' is subsidiary of '{primary_name}' - keeping original name for report")
        
        # Process GLEIF data using code-based processor
        from apps.lenderprofile.processors.data_processors import GLEIFDataProcessor
        gleif_raw = institution_data.get('gleif', {})
        gleif_processed = GLEIFDataProcessor.build_corporate_structure(gleif_raw)
        institution_data['corporate_structure'] = gleif_processed
        
        # Process complaints using code-based processor
        from apps.lenderprofile.processors.data_processors import ComplaintDataProcessor
        complaints_raw = institution_data.get('cfpb_complaints', {}).get('complaints', [])
        complaints_processed = ComplaintDataProcessor.analyze_complaints(complaints_raw)
        institution_data['complaints_processed'] = complaints_processed
        
        # Process analyst ratings using code-based processor
        from apps.lenderprofile.processors.data_processors import AnalystRatingsProcessor
        seeking_alpha_raw = institution_data.get('seeking_alpha', {})
        ratings_processed = AnalystRatingsProcessor.process_analyst_ratings(seeking_alpha_raw)
        institution_data['analyst_ratings'] = ratings_processed
        
        # Process litigation using code-based processor
        from apps.lenderprofile.processors.data_processors import LitigationProcessor
        litigation_raw = institution_data.get('litigation', {}).get('cases', [])
        litigation_processed = LitigationProcessor.process_litigation(litigation_raw)
        institution_data['litigation_processed'] = litigation_processed
        
        # Process news using code-based processor
        # Filter to articles where company (or parent/subsidiaries) is primary subject
        from apps.lenderprofile.processors.data_processors import NewsProcessor
        newsapi_articles = institution_data.get('news', {}).get('articles', [])
        # Get leading story and news articles from Seeking Alpha
        seeking_alpha_news = seeking_alpha_raw.get('leading_story', []) if isinstance(seeking_alpha_raw.get('leading_story'), list) else []
        seeking_alpha_articles = seeking_alpha_raw.get('news', []) if isinstance(seeking_alpha_raw.get('news'), list) else []
        # Combine all Seeking Alpha news sources
        all_seeking_alpha = seeking_alpha_news + seeking_alpha_articles

        # Extract related company names (parent/subsidiaries) from GLEIF data
        gleif_data = institution_data.get('gleif', {})
        related_names = NewsProcessor.extract_related_names(gleif_data)
        logger.info(f"News filtering with {len(related_names)} related entities: {related_names[:3]}..." if related_names else "No related entities for news filtering")

        news_processed = NewsProcessor.process_news(
            newsapi_articles,
            all_seeking_alpha,
            company_name=institution_name,
            related_names=related_names
        )
        institution_data['news_processed'] = news_processed
        
        # Process SEC filings using code-based parser and XBRL API
        from apps.lenderprofile.processors.sec_parser import SECFilingParser
        from apps.lenderprofile.services.sec_client import SECClient
        sec_data = institution_data.get('sec', {})
        ten_k_content = sec_data.get('filings', {}).get('10k_content', [])
        sec_parsed = {}

        # Parse 10-K text content
        if ten_k_content:
            latest_10k = ten_k_content[0] if ten_k_content else None
            if latest_10k and latest_10k.get('content'):
                sec_parsed = SECFilingParser.parse_10k(latest_10k['content'])

        # Fetch structured XBRL data from SEC API (more reliable than text parsing)
        # Get CIK from sec_data (populated by _get_sec_data) or identifiers
        cik = sec_data.get('cik') or identifiers.get('sec_cik')
        if cik:
            try:
                sec_client = SECClient()
                xbrl_data = sec_client.get_comprehensive_xbrl_data(cik)
                if xbrl_data:
                    # Merge XBRL data with text-parsed data
                    sec_parsed = SECFilingParser.merge_with_xbrl_data(sec_parsed, xbrl_data)
                    logger.info(f"Merged SEC XBRL data with parsed 10-K data for CIK {cik}")
            except Exception as e:
                logger.warning(f"Could not fetch XBRL data for CIK {cik}: {e}")

        # Additionally, fetch and parse DEF 14A (proxy) statement for executive/board info
        # Use iXBRL parser for structured data extraction (more reliable than text parsing)
        try:
            def14a_list = sec_data.get('filings', {}).get('def14a', [])
            proxy_parsed = {}
            if def14a_list:
                latest_proxy = def14a_list[0]
                accession = latest_proxy.get('accession_number')

                if accession and cik:
                    # Use iXBRL parser for structured executive compensation data
                    ixbrl_parser = IXBRLParser()
                    cik_int = int(cik)
                    doc_url = ixbrl_parser.get_def14a_doc_url('https://www.sec.gov', cik_int, accession)

                    if doc_url:
                        proxy_parsed = ixbrl_parser.fetch_and_parse_def14a(doc_url)
                        logger.info(f"Parsed DEF 14A iXBRL for CIK {cik}: PEOs={len(proxy_parsed.get('peo_names', []))}, executives={len(proxy_parsed.get('executive_compensation', []))}")
                    else:
                        # Fallback to text-based parsing
                        proxy_content = SECClient().get_def14a_filing_content(cik, accession)
                        if proxy_content:
                            proxy_parsed = SECFilingParser.parse_proxy_statement(proxy_content)
                            logger.info(f"Parsed DEF 14A text for CIK {cik}: executives={len(proxy_parsed.get('executive_compensation', []))}")

            if proxy_parsed and proxy_parsed.get('available', True):
                if not sec_parsed:
                    sec_parsed = {}
                sec_parsed['proxy'] = proxy_parsed
        except Exception as e:
            logger.warning(f"Error fetching/parsing DEF 14A for CIK {cik}: {e}")

        if sec_parsed:
            institution_data['sec_parsed'] = sec_parsed

        # Check 8-K filings for pending mergers/acquisitions
        eight_k_filings = sec_data.get('filings', {}).get('8k', [])
        pending_mergers = []
        for filing in eight_k_filings[:10]:  # Check last 10 8-Ks
            desc = (filing.get('description', '') or '').lower()
            filing_type = (filing.get('type', '') or '').lower()
            # 8-K items that often contain merger info: Item 1.01 (entry into material agreement)
            if any(kw in desc for kw in ['merger', 'acquisition', 'agreement', 'combination']):
                pending_mergers.append({
                    'date': filing.get('date', ''),
                    'description': filing.get('description', '')[:200],
                    'url': filing.get('url', '')
                })
        if pending_mergers:
            if 'mergers' not in institution_data:
                institution_data['mergers'] = {}
            institution_data['mergers']['pending'] = pending_mergers
            logger.info(f"Found {len(pending_mergers)} potential merger announcements in 8-K filings")
        
        # Combine details
        details = institution_data.get('details', {})
        # Note: We don't store fdic_institution anymore - use CFPB/GLEIF for institution data
        details['gleif_data'] = gleif_raw
        details['cfpb_metadata'] = institution_data.get('cfpb_metadata', {})
        institution_data['details'] = details
        
        # Extract tax ID from GLEIF data if available
        gleif_data = institution_data.get('gleif', {})
        if isinstance(gleif_data, dict):
            entity = gleif_data.get('entity', {})
            if isinstance(entity, dict):
                tax_id = entity.get('tax_id') or entity.get('ein')
                if tax_id:
                    institution_data['institution']['tax_id'] = tax_id
                    identifiers['tax_id'] = tax_id
                    logger.info(f"Added tax ID {tax_id} to institution data from GLEIF")
        
        # Update institution info with CFPB metadata if available
        cfpb_meta = institution_data.get('cfpb_metadata', {})
        if cfpb_meta:
            # Get assets from CFPB or transmittal sheet
            assets = cfpb_meta.get('assets')
            if not assets and cfpb_meta.get('transmittal_sheet'):
                assets = cfpb_meta['transmittal_sheet'].get('assets')
            
            # Get type from CFPB
            institution_type = cfpb_meta.get('type')
            
            # Build location from GLEIF if CFPB doesn't have it
            location = cfpb_meta.get('location')
            if not location:
                # Try to get from GLEIF corporate structure
                corporate_structure = institution_data.get('corporate_structure', {})
                if corporate_structure:
                    hq = corporate_structure.get('headquarters', {})
                    if hq:
                        city = hq.get('city', '')
                        state = hq.get('state', '')
                        if city and state:
                            location = f"{city}, {state}"
            
            institution_data['institution'].update({
                'assets': assets,
                'type': institution_type,
                'location': location
            })
            
            logger.info(f"Updated institution data: assets={assets}, type={institution_type}, location={location}")
        
        # Process financial data using code-based processor
        from apps.lenderprofile.processors.data_processors import FinancialDataProcessor
        fdic_financials_raw = institution_data.get('fdic_financials', {}).get('data', [])
        financial_processed = FinancialDataProcessor.process_fdic_financials(fdic_financials_raw)
        
        # Organize financial data
        institution_data['financial'] = {
            'fdic_call_reports': fdic_financials_raw,
            'processed': financial_processed,  # Code-processed structured data
            'trends': financial_processed.get('trends', {}),
            'metrics': financial_processed.get('metrics', {}),
            'growth': financial_processed.get('growth', {})
        }
        
        # Analyze branch network using BigQuery SOD data
        from apps.lenderprofile.branch_network_analyzer import BranchNetworkAnalyzer
        branch_analysis = None
        
        # Determine institution type (bank vs credit union)
        institution_type = 'bank'  # Default to bank
        cfpb_meta = institution_data.get('cfpb_metadata', {})
        if cfpb_meta and 'credit union' in (cfpb_meta.get('type', '') or '').lower():
            institution_type = 'credit_union'
        
        # Get RSSD for branch analysis
        rssd_for_branches = rssd_id or identifiers.get('rssd_id')
        
        if rssd_for_branches:
            try:
                analyzer = BranchNetworkAnalyzer(use_bigquery=True, institution_type=institution_type)
                current_year = datetime.now().year
                years = list(range(current_year - 4, current_year + 1))  # Last 5 years
                
                # Get branch network history
                branch_history, branch_metadata = analyzer.get_branch_network_history(
                    rssd=rssd_for_branches,
                    cu_number=identifiers.get('cu_number') if institution_type == 'credit_union' else None,
                    years=years
                )
                
                # Analyze the branch network
                if branch_history:
                    # The analyze_network_changes method returns a dict with closures, openings, trends, etc.
                    branch_analysis_result = analyzer.analyze_network_changes(branch_history, branch_metadata)

                    # Find the most recent year that actually has data
                    years_with_data = sorted([y for y in branch_history.keys() if branch_history[y]], reverse=True)
                    most_recent_year = years_with_data[0] if years_with_data else max(years)

                    # Get all branches from most recent year with data for map visualization
                    all_branches = branch_history.get(most_recent_year, [])

                    # Get summary from the analysis
                    summary = {
                        'total_branches_current': len(all_branches),
                        'total_branches_by_year': branch_analysis_result.get('total_branches_by_year', {}),
                        'trends': branch_analysis_result.get('trends', {}),
                        'geographic_shifts': branch_analysis_result.get('geographic_shifts', {})
                    }

                    branch_analysis = {
                        'summary': summary,
                        'closures_by_year': branch_analysis_result.get('closures_by_year', {}),
                        'openings_by_year': branch_analysis_result.get('openings_by_year', {}),
                        'net_change_by_year': branch_analysis_result.get('net_change_by_year', {}),
                        'all_branches': all_branches,
                        'years_analyzed': years,
                        'most_recent_year': most_recent_year
                    }

                    logger.info(f"Branch network analysis complete: {len(all_branches)} branches in {most_recent_year}")
            except Exception as e:
                logger.error(f"Error analyzing branch network: {e}", exc_info=True)
                branch_analysis = None
        
        # Organize branch data
        institution_data['branches'] = {
            'analysis': branch_analysis if 'branch_analysis' in locals() else None,
            'history': branch_history if 'branch_history' in locals() else {},
            'metadata': branch_metadata if 'branch_metadata' in locals() else {},
            'locations': branch_analysis.get('all_branches', []) if 'branch_analysis' in locals() and branch_analysis else [],
            'summary': branch_analysis.get('summary', {}) if 'branch_analysis' in locals() and branch_analysis else {}
        }
        
        # Organize merger data
        institution_data['mergers'] = {
            'historical': institution_data.get('federal_reserve', {}).get('historical_mergers', []),
            'pending': institution_data.get('federal_register', {}).get('pending_mergers', [])
        }

        # STEP 3: Run Data Source Analysts (Haiku-powered parallel analysis)
        # Each analyst produces standardized findings that feed into the final synthesis
        try:
            ai_entity_resolution = institution_data.get('ai_entity_resolution', {})

            if ai_entity_resolution:
                logger.info("Running Tier 1 Data Source Analysts (Haiku)...")
                analyst_results = self.data_analysts.analyze_all(
                    institution_data,
                    ai_entity_resolution
                )

                # Compile summaries for Tier 2 synthesizer
                compiled_summaries = compile_analyst_summaries(analyst_results)
                institution_data['analyst_summaries'] = compiled_summaries

                # Store individual analyst results for detailed inspection
                institution_data['analyst_results'] = {
                    source: {
                        'has_data': result.has_data,
                        'data_quality': result.data_quality,
                        'key_findings': result.key_findings,
                        'ncrc_insights': result.ncrc_insights,
                        'risk_flags': result.risk_flags,
                        'positive_indicators': result.positive_indicators,
                        'talking_points': result.talking_points,
                        'metrics': result.metrics,
                        'raw_summary': result.raw_summary
                    }
                    for source, result in analyst_results.items()
                }

                # Log summary
                quality_summary = compiled_summaries.get('data_quality_summary', {})
                logger.info(f"Tier 1 analysis complete: {len(analyst_results)} sources analyzed")
                logger.info(f"Data quality: {quality_summary}")
                logger.info(f"Key findings: {len(compiled_summaries.get('all_key_findings', []))}, "
                           f"Risk flags: {len(compiled_summaries.get('all_risk_flags', []))}")
            else:
                logger.warning("Skipping Tier 1 analysts - no AI entity resolution available")
                institution_data['analyst_summaries'] = {}
                institution_data['analyst_results'] = {}
        except Exception as e:
            logger.error(f"Tier 1 Data Source Analysts failed: {e}", exc_info=True)
            institution_data['analyst_summaries'] = {}
            institution_data['analyst_results'] = {}

        logger.info(f"Data collection complete for {institution_name}")
        return institution_data
    
    # FDIC Institution API removed - we use CFPB/GLEIF for institution data
    # Only FDIC Financial API (Call Reports) is used
    def _get_fdic_institution(self, cert: str) -> Dict[str, Any]:
        """Get FDIC institution details - REMOVED: Use CFPB/GLEIF instead."""
        return {}
    
    def _get_fdic_financials(self, cert: str) -> Dict[str, Any]:
        """
        Get FDIC Call Report data (Financial API).
        
        This is the ONLY FDIC API we use - for Call Report financial data.
        Branch data comes from BigQuery SOD tables, not FDIC Location API.
        Institution data comes from CFPB/GLEIF, not FDIC Institution API.
        
        Documentation: https://api.fdic.gov/banks/docs/
        """
        cache_key = f'fdic_financials_{cert}'
        cached = self.cache.get('financial', cache_key)
        if cached:
            return cached
        
        try:
            # Use FDIC Financial API for Call Report data
            data = self.fdic_client.get_financials(cert, fields=['ASSET', 'REPDTE', 'ROA', 'ROE', 'EQUITY', 'DEP', 'NETINC', 'LNLSNET', 'RBCT1J', 'NPAASSET', 'EEFFR'])
            result = {'data': data}
            if data:
                self.cache.set('financial', result, self.cache.get_ttl('financial'), cache_key)
            return result
        except Exception as e:
            logger.error(f"Error getting FDIC Call Report data for {cert}: {e}")
            return {'data': []}
    
    # Note: Removed _get_fdic_branches - we use BigQuery SOD tables instead
    # Note: Removed _get_fdic_institution - we use CFPB/GLEIF for institution data
    
    def _get_gleif_data(self, lei: str) -> Dict[str, Any]:
        """Get GLEIF entity data including tax ID (EIN)."""
        cache_key = f'gleif_{lei}'
        cached = self.cache.get('gleif', cache_key)
        if cached:
            return cached

        data = self.gleif_client.get_lei_record(lei)
        result = {'entity': data} if data else {}

        if data:
            # Get direct parent
            result['parent'] = self.gleif_client.get_direct_parent(lei)
            result['direct_parent'] = result['parent']  # Alias for clarity

            # Get ultimate parent (top of corporate tree)
            try:
                ultimate_parent = self.gleif_client.get_ultimate_parent(lei)
                if ultimate_parent:
                    # Extract entity info from the GLEIF response
                    if isinstance(ultimate_parent, dict):
                        if 'attributes' in ultimate_parent:
                            attrs = ultimate_parent.get('attributes', {})
                            entity_data = attrs.get('entity', {})
                            result['ultimate_parent'] = {
                                'lei': ultimate_parent.get('id', ''),
                                'name': entity_data.get('legalName', {}).get('name', 'Unknown')
                            }
                        else:
                            result['ultimate_parent'] = {
                                'lei': ultimate_parent.get('lei', ultimate_parent.get('id', '')),
                                'name': ultimate_parent.get('name', 'Unknown')
                            }
            except Exception as e:
                logger.warning(f"Error getting ultimate parent for {lei}: {e}")

            # Get all subsidiaries
            result['children'] = self.gleif_client.get_all_subsidiaries(lei)
            self.cache.set('gleif', result, self.cache.get_ttl('gleif'), cache_key)

        return result
    
    def _get_sec_data(self, name: str) -> Dict[str, Any]:
        """Get SEC filing data using JSON APIs."""
        try:
            companies = self.sec_client.search_companies(name)
            if not companies:
                logger.warning(f"No SEC companies found for {name}")
                return {}

            # Try to find the best match - prefer parent holding companies for banks
            # Banks are subsidiaries; their parent holding companies have SEC filings
            best_match = None
            search_name = name.upper()

            # Extract core company name (remove "BANK", "NATIONAL ASSOCIATION", etc.)
            core_name = search_name
            for suffix in [' BANK', ' NATIONAL ASSOCIATION', ', N.A.', ', NA', ' N.A.']:
                core_name = core_name.replace(suffix, '')
            core_name = core_name.strip()

            # Holding company indicators - these have SEC filings
            holding_indicators = ['& CO', '& COMPANY', 'CORP', 'INC', 'HOLDINGS', 'FINANCIAL', 'BANCORP', 'BANCSHARES']

            # Score each company: higher = better match
            def score_company(company):
                company_name = (company.get('name') or '').upper()
                score = 0

                # Strong match if core name is in company name
                if core_name in company_name:
                    score += 100

                # Prefer holding companies (they have SEC filings, executive comp, etc.)
                for indicator in holding_indicators:
                    if indicator in company_name:
                        score += 50
                        break

                # Penalize if it's a bank subsidiary (not the parent)
                if ' BANK' in company_name and 'HOLDING' not in company_name and 'BANCORP' not in company_name:
                    score -= 30

                # Prefer exact matches
                if search_name == company_name:
                    score += 75

                return score

            # Find best match by score
            scored_companies = [(score_company(c), c) for c in companies]
            scored_companies.sort(key=lambda x: -x[0])  # Highest score first

            if scored_companies:
                best_match = scored_companies[0][1]
                logger.info(f"SEC match scores: {[(s, c.get('name')) for s, c in scored_companies[:3]]}")
            
            cik = best_match.get('cik')
            if not cik:
                logger.warning(f"No CIK found for SEC company: {best_match.get('name')}")
                return {}
            
            logger.info(f"Using SEC CIK {cik} for company: {best_match.get('name')}")
            
            # Get submissions (filing history) - also contains ticker symbol
            submissions = self.sec_client.get_company_submissions(cik)
            if not submissions:
                logger.warning(f"No submissions found for CIK {cik}")
            
            # Extract ticker from submissions (most reliable source)
            # Prefer the main ticker (shortest, without suffix like I, A, B)
            ticker = None
            if submissions and 'tickers' in submissions:
                tickers = submissions.get('tickers', [])
                if tickers:
                    # Sort tickers: prefer shorter ones without suffixes (e.g., FITB over FITBI)
                    # Main trading tickers are usually the shortest
                    sorted_tickers = sorted(tickers, key=lambda t: (len(t), t))
                    ticker = sorted_tickers[0]
                    if len(tickers) > 1:
                        logger.info(f"Multiple tickers available {tickers}, selected main ticker: {ticker}")

            # If no ticker in submissions, try to get from best_match
            if not ticker:
                ticker = best_match.get('ticker')
            
            # Get last 10-K filing for AI analysis (annual report)
            ten_k_filings = self.sec_client.get_10k_filings(cik, limit=1)

            # Get full text content of 10-K filing for AI analysis
            ten_k_content = []
            for filing in ten_k_filings:
                accession_num = filing.get('accession_number')
                if accession_num:
                    content = self.sec_client.get_10k_filing_content(cik, accession_num)
                    if content:
                        ten_k_content.append({
                            'filing_date': filing.get('date'),
                            'accession_number': accession_num,
                            'url': filing.get('url'),
                            'content': content[:500000]
                        })

            # Get last 3 10-Q filings (quarterly reports)
            # Together with 1 10-K, this covers all 4 quarters
            ten_q_filings = self.sec_client.get_company_filings(cik, filing_type='10-Q', limit=3)
            logger.info(f"Found {len(ten_q_filings)} 10-Q filings for CIK {cik}")

            # Get 10-Q content for AI analysis
            ten_q_content = []
            for filing in ten_q_filings:
                accession_num = filing.get('accession_number')
                if accession_num:
                    # Use same method as 10-K to get content
                    content = self.sec_client.get_10k_filing_content(cik, accession_num)
                    if content:
                        ten_q_content.append({
                            'filing_date': filing.get('date'),
                            'accession_number': accession_num,
                            'url': filing.get('url'),
                            'content': content[:200000]  # 10-Q is shorter than 10-K
                        })

            # Get other filings list - need to fetch by type for companies with many filings
            # (e.g., JPMorgan has 21,000+ filings, DEF 14A is at index 16000+)
            filings = self.sec_client.get_company_filings(cik, limit=100)

            # Fetch DEF 14A filings specifically (they're often buried under 424B2 prospectuses)
            def14a_filings = self.sec_client.get_company_filings(cik, filing_type='DEF 14A', limit=5)
            if def14a_filings:
                logger.info(f"Found {len(def14a_filings)} DEF 14A filings for CIK {cik}")
            else:
                # Fallback: try filtering from general filings
                def14a_filings = [f for f in filings if 'DEF 14A' in f.get('type', '')]

            # Get XBRL financial data (this may fail for some companies)
            financials = None
            try:
                financials = self.sec_client.parse_xbrl_financials(cik)
            except Exception as e:
                logger.debug(f"Could not parse XBRL financials for CIK {cik}: {e}")

            return {
                'cik': cik,
                'company_name': best_match.get('name'),
                'ticker': ticker,  # From submissions API (most reliable)
                'submissions': submissions,
                'filings': {
                    '10k': ten_k_filings,
                    '10k_content': ten_k_content,  # Full text for AI analysis
                    '10q': ten_q_filings,
                    '10q_content': ten_q_content,  # 10-Q content for quarterly analysis
                    '8k': [f for f in filings if f.get('type') == '8-K'],
                    'def14a': def14a_filings  # Fetch specifically to find buried DEF 14A filings
                },
                'financials': financials
            }
        except Exception as e:
            logger.error(f"Error getting SEC data for {name}: {e}", exc_info=True)
            return {}
    
    def _get_seeking_alpha_data(self, name: str) -> Dict[str, Any]:
        """Get Seeking Alpha data (requires ticker symbol)."""
        try:
            # Known ticker mappings for common banks (fallback for edge cases)
            ticker_map = {
                'FIFTH THIRD BANK': 'FITB',
                'FIFTH THIRD': 'FITB',
                'FIFTH THIRD BANCORP': 'FITB',
            }
            
            # Check known mappings first (fast lookup)
            name_upper = name.upper()
            ticker = ticker_map.get(name_upper)
            
            # If not found, use reliable SEC-based lookup
            if not ticker:
                ticker = self.sec_client.get_ticker_from_company_name(name)
            
            if not ticker:
                logger.info(f"Could not determine ticker symbol for {name}, skipping Seeking Alpha")
                return {}
            
            logger.info(f"Fetching Seeking Alpha data for ticker: {ticker}")
            
            # Get comprehensive data
            result = self.seeking_alpha_client.search_by_ticker(ticker)
            
            if result:
                logger.info(f"Successfully retrieved Seeking Alpha data for {ticker}")

                # Also fetch news articles
                news = self.seeking_alpha_client.get_news(ticker, limit=10)

                return {
                    'ticker': ticker,
                    'profile': result.get('profile'),
                    'financials': result.get('financials'),
                    'ratings': result.get('ratings'),  # Analyst ratings and recommendations
                    'earnings': result.get('earnings'),  # Earnings estimates
                    'leading_story': result.get('leading_story'),  # Leading news stories/articles
                    'analysis_articles': result.get('analysis_articles'),  # Ticker-specific analysis articles
                    'news': news  # News articles with headlines and snippets
                }
            else:
                logger.info(f"No Seeking Alpha data found for ticker {ticker}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting Seeking Alpha data for {name}: {e}", exc_info=True)
            return {}
    
    def _get_litigation_data(self, name: str) -> Dict[str, Any]:
        """Get CourtListener litigation data."""
        cache_key = f'litigation_{name}'
        cached = self.cache.get('court_search', cache_key)
        if cached:
            return cached
        
        # Search for institution as party
        dockets = self.courtlistener_client.search_dockets(
            f'party_name:"{name}"',
            filed_after='2015-01-01',
            limit=20
        )
        
        result = {
            'cases': dockets,
            'total_cases': len(dockets)
        }
        
        if dockets:
            self.cache.set('court_search', result, self.cache.get_ttl('court_search'), cache_key)
        
        return result
    
    def _get_news_data(self, name: str) -> Dict[str, Any]:
        """
        Get news data from reputable sources.

        Priority order:
        1. Google Custom Search (higher quality, limited free tier)
        2. NewsAPI with reputable domain filtering (fallback)

        Both sources are filtered to only include reputable financial news outlets.
        """
        cache_key = f'news_{name}'
        cached = self.cache.get('news', cache_key)
        if cached:
            return cached

        articles = []
        source = 'none'

        # Try Google Custom Search first (higher quality results)
        try:
            if self.google_news_client.api_key and self.google_news_client.search_engine_id:
                logger.info(f"Fetching news via Google Custom Search for: {name}")
                google_result = self.google_news_client.search_news_extended(
                    query=name,
                    num_results=20,
                    date_restrict='m3'  # Last 3 months
                )
                articles = google_result.get('articles', [])
                if articles:
                    source = 'google_custom_search'
                    logger.info(f"Google Custom Search found {len(articles)} articles for {name}")
        except Exception as e:
            logger.warning(f"Google Custom Search failed for {name}: {e}")

        # Fallback to NewsAPI with reputable domain filtering
        if not articles:
            try:
                logger.info(f"Fetching news via NewsAPI (reputable sources only) for: {name}")
                response = self.newsapi_client.search_everything(
                    query=f'"{name}"',
                    language='en',
                    sort_by='relevancy',
                    page_size=50,
                    use_reputable_sources=True  # Filter to reputable domains
                )
                articles = response.get('articles', [])
                if articles:
                    source = 'newsapi_filtered'
                    logger.info(f"NewsAPI found {len(articles)} articles from reputable sources for {name}")
            except Exception as e:
                logger.warning(f"NewsAPI failed for {name}: {e}")

        # Fallback to DuckDuckGo search
        if not articles:
            try:
                logger.info(f"Fetching news via DuckDuckGo for: {name}")
                ddg_articles = self.duckduckgo_client.search_news(name, max_results=20)
                if ddg_articles:
                    articles = ddg_articles
                    source = 'duckduckgo'
                    logger.info(f"DuckDuckGo found {len(articles)} results for {name}")
            except Exception as e:
                logger.warning(f"DuckDuckGo search failed for {name}: {e}")

        result = {
            'articles': articles,
            'total_articles': len(articles),
            'source': source
        }

        if articles:
            self.cache.set('news', result, self.cache.get_ttl('news'), cache_key)

        return result
    
    # TheOrg API removed - not using organizational data
    def _get_theorg_data(self, name: str) -> Dict[str, Any]:
        """Get TheOrg organizational data - REMOVED per user request."""
        return {'available': False}
    
    def _get_enforcement_data(self, name: str) -> Dict[str, Any]:
        """Get CFPB enforcement data."""
        actions = self.cfpb_client.search_enforcement_actions(name)
        
        return {
            'actions': actions,
            'total_actions': len(actions),
            'recent_actions': [a for a in actions if self._is_recent(a.get('date', ''))]
        }
    
    def _get_cfpb_complaints(self, company_name: str, limit: int = 1000) -> Dict[str, Any]:
        """
        Get CFPB consumer complaints for a company with trend and topic analysis.
        
        Args:
            company_name: Company name to search for
            limit: Maximum number of complaints to retrieve (default: 1000 for better analysis)
            
        Returns:
            Dictionary with complaints data including trends and main topics
        """
        try:
            # Try the company name directly first - CFPB client will fuzzy match
            # Avoid adding generic suffixes that could cause false matches
            name_variations = [
                company_name,
                company_name.upper(),
                # Try without common suffixes
                company_name.replace(" Bank", "").replace(" BANK", ""),
                company_name.replace(", LLC", "").replace(", Inc.", "").replace(", Inc", ""),
            ]

            # Remove duplicates and empty strings while preserving order
            seen = set()
            name_variations = [n.strip() for n in name_variations if n and n.strip() and n.strip() not in seen and not seen.add(n.strip())]

            best_result = None
            best_total = 0

            for name_var in name_variations:
                # Request with analysis enabled to get trends and topics
                result = self.cfpb_client.search_consumer_complaints(
                    name_var,
                    limit=limit,
                    include_analysis=True  # Enable trend and topic analysis
                )
                total = result.get('total', 0)

                if total > best_total:
                    best_total = total
                    best_result = result
                    best_result['search_name_used'] = name_var

                # If we found results, we can stop
                if total > 0:
                    break
            
            if best_result:
                logger.info(f"Found {best_total} CFPB complaints for '{company_name}' (searched as '{best_result.get('search_name_used')}')")
                if best_result.get('trends'):
                    trend = best_result['trends'].get('recent_trend', 'unknown')
                    logger.info(f"Complaint trend: {trend}")

                # Get additional data for trend charts
                cfpb_company_name = best_result.get('cfpb_company_name')
                if cfpb_company_name:
                    # Get national totals for comparison
                    national_by_year = self.cfpb_client.get_national_complaint_counts(years=5)
                    best_result['national_by_year'] = national_by_year

                    # Get categories by year for interactive chart
                    categories_by_year = self.cfpb_client.get_categories_by_year(cfpb_company_name, years=5)
                    best_result['categories_by_year'] = categories_by_year

                return best_result
            else:
                logger.debug(f"No CFPB complaints found for '{company_name}' after trying {len(name_variations)} variations")
                return {
                    'total': 0, 
                    'complaints': [], 
                    'aggregations': {},
                    'trends': {},
                    'main_topics': [],
                    'main_products': []
                }
                
        except Exception as e:
            logger.error(f"Error getting CFPB complaints for '{company_name}': {e}", exc_info=True)
            return {
                'total': 0, 
                'complaints': [], 
                'aggregations': {},
                'trends': {},
                'main_topics': [],
                'main_products': []
            }
    
    def _get_cfpb_metadata(self, rssd_id: Optional[str], lei: Optional[str], name: str) -> Dict[str, Any]:
        """
        Get CFPB institution metadata (assets, type, location) and transmittal sheet data.
        
        Uses both:
        1. CFPB HMDA API for institution metadata (assets, name, type)
        2. CFPB HMDA Platform API for transmittal sheet data (LAR counts per year)
        
        Documentation:
        - HMDA API: https://ffiec.cfpb.gov/hmda-auth/
        - Public Verification API: https://ffiec.cfpb.gov/documentation/api/public-verification/
        """
        try:
            # Try to use LenderProfile's CFPB client (which wraps DataExplorer's)
            from apps.lenderprofile.services.cfpb_client import CFPBClient
            cfpb_client = CFPBClient()
            
            if not cfpb_client._is_enabled():
                return {}
            
            institution = None
            transmittal_data = None
            
            # Try RSSD first
            if rssd_id:
                institution = cfpb_client.get_institution_by_rssd(str(rssd_id))
            
            # Fallback to LEI
            if not institution and lei:
                institution = cfpb_client.get_institution_by_lei(lei)
                # Also get transmittal sheet data by LEI
                if lei:
                    transmittal_data = cfpb_client.get_transmittal_sheet_data(lei)
            
            # Fallback to name search
            if not institution:
                institution = cfpb_client.get_institution_by_name(name)
            
            result = {}
            
            if institution:
                logger.info(f"Found CFPB metadata: {institution.get('name')} (Assets: {institution.get('assets')})")
                
                # Build location from city/state if available
                city = institution.get('city', '')
                state = institution.get('state', '')
                location = None
                if city and state:
                    location = f"{city}, {state}"
                elif city:
                    location = city
                elif state:
                    location = state
                
                result.update({
                    'name': institution.get('name'),
                    'assets': institution.get('assets'),
                    'type': institution.get('type'),
                    'lei': institution.get('lei'),
                    'rssd': institution.get('rssd'),
                    'city': city,
                    'state': state,
                    'location': location,
                    'source': 'cfpb_hmda_api'
                })
            
            # Add transmittal sheet data if available
            if transmittal_data:
                result.update({
                    'transmittal_sheet': {
                        'assets': transmittal_data.get('assets'),
                        'total_lines': transmittal_data.get('total_lines'),  # LAR count
                        'year': transmittal_data.get('year'),
                        'quarter': transmittal_data.get('quarter'),
                        'tax_id': transmittal_data.get('tax_id')
                    }
                })
                logger.info(f"Found transmittal sheet data: {transmittal_data.get('total_lines')} LARs in {transmittal_data.get('year')}")
            
            # Fallback: Get LAR counts from BigQuery HMDA data if CFPB API not available
            if not result.get('transmittal_sheet') and lei:
                try:
                    from shared.utils.bigquery_client import get_bigquery_client, execute_query
                    import os
                    project_id = os.getenv('GCP_PROJECT_ID', 'hdma1-242116')
                    client = get_bigquery_client(project_id)
                    
                    # Get LAR counts by year from BigQuery HMDA data
                    query = f"""
                    SELECT 
                        CAST(activity_year AS STRING) as year,
                        COUNT(*) as lar_count
                    FROM `{project_id}.hmda.hmda`
                    WHERE lei = '{lei.upper()}'
                    GROUP BY activity_year
                    ORDER BY activity_year DESC
                    LIMIT 5
                    """
                    
                    lar_results = execute_query(client, query)
                    if lar_results:
                        lar_counts_by_year = {row['year']: row['lar_count'] for row in lar_results}
                        if not result.get('transmittal_sheet'):
                            result['transmittal_sheet'] = {}
                        result['transmittal_sheet']['lar_counts_by_year'] = lar_counts_by_year
                        logger.info(f"Found LAR counts from BigQuery: {lar_counts_by_year}")
                except Exception as e:
                    logger.debug(f"Could not get LAR counts from BigQuery: {e}")
            
            return result
            
        except ImportError:
            logger.debug("CFPB client not available")
            return {}
        except Exception as e:
            logger.error(f"Error getting CFPB metadata: {e}", exc_info=True)
            return {}
    
    def _get_federal_register_data(self, name: str) -> Dict[str, Any]:
        """Get Federal Register merger notices."""
        documents = self.federal_register_client.search_merger_notices(name)
        
        return {
            'merger_notices': documents,
            'pending_mergers': [d for d in documents if 'pending' in d.get('status', '').lower()]
        }
    
    def _get_cra_data(self, cert: str) -> Dict[str, Any]:
        """Get FFIEC CRA performance data - REMOVED per user request."""
        return {}
    
    def _get_federal_reserve_data(self, rssd_id: str) -> Dict[str, Any]:
        """Get Federal Reserve NIC data."""
        structure = self.federal_reserve_client.get_holding_company_structure(rssd_id)
        
        return {
            'structure': structure,
            'historical_mergers': []  # TODO: Parse transformation database
        }
    
    def _get_regulations_data(self, name: str) -> Dict[str, Any]:
        """Get Regulations.gov comment letters."""
        result = self.regulations_client.search_comments(
            organization_name=name,
            search_term=name,
            limit=20
        )
        
        comments = result.get('data', [])
        meta = result.get('meta', {})
        
        return {
            'comment_letters': comments,
            'total_comments': meta.get('totalElements', len(comments)),
            'meta': meta
        }

    def _get_hmda_footprint(self, leis: list, institution_name: str = None) -> Dict[str, Any]:
        """
        Get HMDA lending footprint data for ALL entities in the corporate hierarchy.

        Shows where the lender concentrates their lending activity.
        Queries HMDA for all LEIs in the hierarchy and returns data by entity
        for stacked column charts.

        Args:
            leis: List of Legal Entity Identifiers from hierarchy
            institution_name: Institution name for fallback search

        Returns:
            Lending footprint data with:
            - by_entity_year: Applications by entity and year
            - entity_names: Entity names
            - states_by_year: Aggregated states
            - national_by_year: National totals
            - by_year: Total applications per year
        """
        # Normalize leis to a list
        if isinstance(leis, str):
            leis = [leis]

        # Check cache first
        primary_lei = leis[0] if leis else None
        if primary_lei:
            cache_key = f'hmda_footprint_{primary_lei}'
            cached = self.cache.get('hmda', cache_key)
            if cached:
                return cached

        try:
            # Get ALL hierarchy LEIs from GLEIF
            all_hierarchy_leis = set()
            for lei in leis:
                hierarchy = self.hmda_client.get_hierarchy_leis(lei)
                for entity in hierarchy:
                    if entity.get('lei'):
                        all_hierarchy_leis.add(entity['lei'])

            # If no hierarchy found, try searching by institution name
            if not all_hierarchy_leis and institution_name:
                logger.info(f"No hierarchy found, searching by name: {institution_name}")
                hmda_lei = self.hmda_client.find_lei_by_name(institution_name)
                if hmda_lei:
                    all_hierarchy_leis.add(hmda_lei)
                    # Also get hierarchy for this LEI
                    hierarchy = self.hmda_client.get_hierarchy_leis(hmda_lei)
                    for entity in hierarchy:
                        if entity.get('lei'):
                            all_hierarchy_leis.add(entity['lei'])

            if not all_hierarchy_leis:
                logger.warning(f"No HMDA LEIs found for {leis} or name '{institution_name}'")
                return {}

            logger.info(f"Found {len(all_hierarchy_leis)} LEIs in hierarchy: {all_hierarchy_leis}")

            # Get HMDA data by loan purpose for ALL entities (7 years to include 2018-2024)
            hmda_data = self.hmda_client.get_hmda_by_purpose(list(all_hierarchy_leis), years=7)

            if not hmda_data.get('by_purpose_year'):
                logger.warning(f"No HMDA data found for any LEIs in hierarchy")
                return {}

            # Get the most recent year with data
            by_year = hmda_data.get('by_year', {})
            most_recent_year = max(by_year.keys()) if by_year else None

            # Get top metros (CBSAs) for the most recent year
            top_metros = []
            if most_recent_year:
                for lei in list(all_hierarchy_leis)[:3]:  # Check top 3 LEIs for metros
                    try:
                        metros = self.hmda_client.get_top_metros(lei, most_recent_year, limit=20)
                        if metros:
                            top_metros = metros
                            break
                    except Exception as e:
                        logger.debug(f"Could not get metros for LEI {lei}: {e}")

            # Calculate total applications from by_year
            total_applications = sum(by_year.values()) if by_year else 0

            # Build result with aggregated data by purpose
            footprint = {
                'by_purpose_year': hmda_data.get('by_purpose_year', {}),
                'by_year': by_year,
                'states_by_year': hmda_data.get('states_by_year', {}),
                'national_by_year': hmda_data.get('national_by_year', {}),
                'national_by_purpose_year': hmda_data.get('national_by_purpose_year', {}),
                'hierarchy_leis': list(all_hierarchy_leis),
                'year': most_recent_year,
                'top_metros': top_metros,  # CBSA-level data for AI analysis
                'total_applications': total_applications  # Total across all years
            }

            # Cache for 24 hours
            if primary_lei:
                cache_key = f'hmda_footprint_{primary_lei}'
                self.cache.set('hmda', footprint, 86400, cache_key)

            purpose_count = len(hmda_data.get('by_purpose_year', {}))
            year_count = len(hmda_data.get('by_year', {}))
            logger.info(f"Found HMDA footprint for {purpose_count} purposes across {year_count} years")
            return footprint

        except Exception as e:
            logger.error(f"Error getting HMDA footprint for LEIs {leis}: {e}", exc_info=True)
            return {}

    def _calculate_financial_trends_deprecated(self, financial_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        DEPRECATED: Use FinancialDataProcessor.process_fdic_financials() instead.
        This method is kept for backward compatibility but should not be used.
        """
        """Calculate 5-year financial trends."""
        if not financial_records:
            return {}
        
        # Sort by date
        sorted_records = sorted(financial_records, key=lambda x: x.get('REPDTE', ''))
        
        return {
            'years': [r.get('REPDTE', '')[:4] for r in sorted_records[-20:]],  # Last 20 quarters
            'assets': [r.get('ASSET', 0) for r in sorted_records[-20:]],
            'equity': [r.get('EQ', 0) for r in sorted_records[-20:]],
            'net_income': [r.get('NETINC', 0) for r in sorted_records[-20:]]
        }
    
    def _summarize_branches(self, branches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Summarize branch network data."""
        if not branches:
            return {}
        
        return {
            'total': len(branches),
            'states': len(set(b.get('STALP') or b.get('STATE', '') for b in branches)),
            'msas': len(set(b.get('MSA', '') for b in branches if b.get('MSA')))
        }

    def _get_sb_lending_data(self, lei: str, fdic_cert: str, institution_name: str) -> Dict[str, Any]:
        """
        Get CRA small business lending data for the institution.

        Args:
            lei: Legal Entity Identifier
            fdic_cert: FDIC Certificate Number
            institution_name: Institution name

        Returns:
            SB lending data with yearly volumes, national comparison, and state breakdown
        """
        try:
            sb_data = self.cra_client.get_sb_lending_summary(
                lei=lei,
                fdic_cert=fdic_cert,
                institution_name=institution_name
            )
            if sb_data.get('has_data'):
                logger.info(f"Collected CRA SB lending data: {len(sb_data.get('yearly_lending', {}).get('years', []))} years")
            return sb_data
        except Exception as e:
            logger.error(f"Error getting CRA SB lending data: {e}")
            return {'has_data': False, 'error': str(e)}

    def _is_recent(self, date_str: str, days: int = 365) -> bool:
        """Check if date is within recent period."""
        try:
            from datetime import datetime
            date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return (datetime.now() - date.replace(tzinfo=None)).days <= days
        except:
            return False

