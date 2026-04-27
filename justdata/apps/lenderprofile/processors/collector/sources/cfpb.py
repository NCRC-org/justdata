"""CFPB complaints + metadata fetchers and aggregations."""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

def _aggregate_cfpb_by_names(collector, brand_names: List[str], institution_name: str) -> Dict[str, Any]:
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
            cfpb_data = collector._get_cfpb_complaints(brand_name)
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

def _aggregate_cfpb_all_entities(collector, family: Dict[str, Any]) -> Dict[str, Any]:
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
            cfpb_data = collector._get_cfpb_complaints(entity_name)
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

def _get_cfpb_complaints(collector, company_name: str, limit: int = 1000) -> Dict[str, Any]:
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
            result = collector.cfpb_client.search_consumer_complaints(
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
                national_by_year = collector.cfpb_client.get_national_complaint_counts(years=5)
                best_result['national_by_year'] = national_by_year

                # Get categories by year for interactive chart
                categories_by_year = collector.cfpb_client.get_categories_by_year(cfpb_company_name, years=5)
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

def _get_cfpb_metadata(collector, rssd_id: Optional[str], lei: Optional[str], name: str) -> Dict[str, Any]:
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
        from justdata.apps.lenderprofile.services.cfpb_client import CFPBClient
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
                from justdata.shared.utils.bigquery_client import get_bigquery_client, execute_query
                import os
                project_id = os.getenv('JUSTDATA_PROJECT_ID', 'justdata-ncrc')
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

