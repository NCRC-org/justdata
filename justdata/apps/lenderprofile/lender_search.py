"""
Lender search utilities for LenderProfile blueprint.
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def search_lenders(search_term: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for lenders by name using FDIC and identifier resolution.

    Args:
        search_term: The search query string
        limit: Maximum number of results to return

    Returns:
        List of matching lender dictionaries
    """
    if not search_term or len(search_term.strip()) < 2:
        return []

    try:
        from .processors.identifier_resolver import IdentifierResolver

        resolver = IdentifierResolver()
        candidates = resolver.get_candidates_with_location(search_term.strip(), limit=limit)

        if not candidates:
            logger.warning(f"No candidates found for '{search_term}'")
            return []

        # Format results for the API response
        results = []
        for candidate in candidates:
            city = candidate.get('city', '')
            state = candidate.get('state', '')
            location = f"{city}, {state}".strip(', ') if city or state else 'Location unknown'

            results.append({
                'name': candidate.get('name', ''),
                'city': city,
                'state': state,
                'location': location,
                'fdic_cert': candidate.get('fdic_cert'),
                'rssd_id': candidate.get('rssd_id'),
                'lei': candidate.get('lei'),
                'type': candidate.get('type', ''),
                'confidence': candidate.get('confidence', 0.0)
            })

        logger.info(f"Found {len(results)} lenders matching '{search_term}'")
        return results

    except Exception as e:
        logger.error(f"Error searching lenders: {e}", exc_info=True)
        raise
