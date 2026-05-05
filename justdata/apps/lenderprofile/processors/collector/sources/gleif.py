"""GLEIF data fetchers + corporate family resolution."""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

def _get_corporate_family(collector, lei: str, institution_name: str) -> Dict[str, Any]:
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
        gleif_results = collector.gleif_client.search_by_name(institution_name, limit=10)
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
            gleif_family = collector.gleif_client.get_corporate_family(lei)

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

def _get_gleif_data(collector, lei: str) -> Dict[str, Any]:
    """Get GLEIF entity data including tax ID (EIN)."""
    cache_key = f'gleif_{lei}'
    cached = collector.cache.get('gleif', cache_key)
    if cached:
        return cached

    data = collector.gleif_client.get_lei_record(lei)
    result = {'entity': data} if data else {}

    if data:
        # Get direct parent
        result['parent'] = collector.gleif_client.get_direct_parent(lei)
        result['direct_parent'] = result['parent']  # Alias for clarity

        # Get ultimate parent (top of corporate tree)
        try:
            ultimate_parent = collector.gleif_client.get_ultimate_parent(lei)
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
        result['children'] = collector.gleif_client.get_all_subsidiaries(lei)
        collector.cache.set('gleif', result, collector.cache.get_ttl('gleif'), cache_key)

    return result

