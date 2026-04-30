"""HMDA footprint fetcher + aggregations."""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

def _aggregate_hmda_all_entities(collector, family: Dict[str, Any], institution_name: str) -> Dict[str, Any]:
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
            hmda_data = collector._get_hmda_footprint([entity_lei], entity_name)

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

def _get_hmda_footprint(collector, leis: list, institution_name: str = None) -> Dict[str, Any]:
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
        cached = collector.cache.get('hmda', cache_key)
        if cached:
            return cached

    try:
        # Get ALL hierarchy LEIs from GLEIF
        all_hierarchy_leis = set()
        for lei in leis:
            hierarchy = collector.hmda_client.get_hierarchy_leis(lei)
            for entity in hierarchy:
                if entity.get('lei'):
                    all_hierarchy_leis.add(entity['lei'])

        # If no hierarchy found, try searching by institution name
        if not all_hierarchy_leis and institution_name:
            logger.info(f"No hierarchy found, searching by name: {institution_name}")
            hmda_lei = collector.hmda_client.find_lei_by_name(institution_name)
            if hmda_lei:
                all_hierarchy_leis.add(hmda_lei)
                # Also get hierarchy for this LEI
                hierarchy = collector.hmda_client.get_hierarchy_leis(hmda_lei)
                for entity in hierarchy:
                    if entity.get('lei'):
                        all_hierarchy_leis.add(entity['lei'])

        if not all_hierarchy_leis:
            logger.warning(f"No HMDA LEIs found for {leis} or name '{institution_name}'")
            return {}

        logger.info(f"Found {len(all_hierarchy_leis)} LEIs in hierarchy: {all_hierarchy_leis}")

        # Get HMDA data by loan purpose for ALL entities (7 years to include 2018-2024)
        hmda_data = collector.hmda_client.get_hmda_by_purpose(list(all_hierarchy_leis), years=7)

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
                    metros = collector.hmda_client.get_top_metros(lei, most_recent_year, limit=20)
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
            collector.cache.set('hmda', footprint, 86400, cache_key)

        purpose_count = len(hmda_data.get('by_purpose_year', {}))
        year_count = len(hmda_data.get('by_year', {}))
        logger.info(f"Found HMDA footprint for {purpose_count} purposes across {year_count} years")
        return footprint

    except Exception as e:
        logger.error(f"Error getting HMDA footprint for LEIs {leis}: {e}", exc_info=True)
        return {}

