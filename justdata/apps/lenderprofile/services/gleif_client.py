#!/usr/bin/env python3
"""
GLEIF API Client
Fetches legal entity information and corporate structure.
"""

import requests
import logging
import json
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class GLEIFClient:
    """
    Client for GLEIF (Global Legal Entity Identifier Foundation) API.
    
    Base URL: https://api.gleif.org/api/v1/
    """
    
    def __init__(self):
        """Initialize GLEIF API client."""
        self.base_url = 'https://api.gleif.org/api/v1'
        self.timeout = 30
    
    def get_lei_record(self, lei: str) -> Optional[Dict[str, Any]]:
        """
        Get entity details by LEI.
        
        Args:
            lei: Legal Entity Identifier (20 characters)
            
        Returns:
            Entity details or None
        """
        try:
            url = f'{self.base_url}/lei-records/{lei.strip().upper()}'
            headers = {'Accept': 'application/vnd.api+json'}
            
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # Log full response structure for debugging
            if logger.isEnabledFor(logging.DEBUG):
                import json
                logger.debug(f"GLEIF full response for LEI {lei}: {json.dumps(data, indent=2, default=str)[:2000]}")
            
            if 'data' in data and 'attributes' in data['data']:
                attrs = data['data']['attributes']
                entity = attrs.get('entity', {})
                
                # Log the full entity structure for debugging
                if logger.isEnabledFor(logging.DEBUG):
                    import json
                    logger.debug(f"GLEIF entity structure for LEI {lei}: {json.dumps(entity, indent=2, default=str)[:2000]}")
                
                # Extract tax ID (EIN) from registration authorities
                # GLEIF stores tax IDs in registrationAuthorities array
                # Check multiple possible locations for registrationAuthorities
                tax_id = None
                registration_authorities = (
                    entity.get('registrationAuthorities', []) or
                    attrs.get('registrationAuthorities', []) or
                    data.get('data', {}).get('attributes', {}).get('registrationAuthorities', []) or
                    []
                )
                
                logger.info(f"GLEIF record for LEI {lei} has {len(registration_authorities) if isinstance(registration_authorities, list) else 0} registration authorities")
                
                if isinstance(registration_authorities, list):
                    for idx, auth in enumerate(registration_authorities):
                        if isinstance(auth, dict):
                            logger.debug(f"Checking registration authority {idx}: {json.dumps(auth, default=str)}")
                            
                            # Check for IRS/US tax ID - look for US-IRS authority
                            auth_id = auth.get('registrationAuthorityId', '')
                            auth_entity_id = auth.get('registrationAuthorityEntityId', '')
                            other_id = auth.get('otherRegistrationAuthorityId', '')
                            
                            logger.debug(f"  auth_id: {auth_id}, auth_entity_id: {auth_entity_id}, other_id: {other_id}")
                            
                            # Check if this is an IRS authority
                            # IRS authority ID is typically 'RA000000000000000000000000000001' or contains 'IRS'
                            if 'IRS' in str(auth_id) or 'US-IRS' in str(auth_id) or auth_id == 'RA000000000000000000000000000001':
                                # Tax ID is usually in registrationAuthorityEntityId for IRS
                                tax_id = auth_entity_id or other_id
                                if tax_id:
                                    logger.info(f"Found tax_id {tax_id} from IRS registration authority (auth_id: {auth_id})")
                                    break
                            
                            # Also check if registrationAuthorityEntityId looks like an EIN (9 digits, possibly with dashes)
                            if not tax_id and auth_entity_id:
                                ein_candidate = str(auth_entity_id).replace('-', '').replace(' ', '').strip()
                                if ein_candidate.isdigit() and len(ein_candidate) == 9:
                                    tax_id = ein_candidate
                                    logger.info(f"Found tax_id {tax_id} from registrationAuthorityEntityId (looks like EIN)")
                                    break
                            
                            # Fallback: try other fields
                            if not tax_id:
                                candidate = (auth_entity_id or other_id or
                                            auth.get('taxId') or
                                            auth.get('registrationAuthorityId'))
                                if candidate:
                                    candidate_clean = str(candidate).replace('-', '').replace(' ', '').strip()
                                    if candidate_clean.isdigit() and len(candidate_clean) >= 9:
                                        tax_id = candidate_clean
                                        logger.info(f"Found tax_id {tax_id} from registration authority field")
                                        break
                
                # Also check if tax_id is directly in the entity or attributes
                if not tax_id:
                    # Sometimes tax_id might be at the top level of entity or attributes
                    tax_id = (entity.get('taxId') or entity.get('ein') or 
                             attrs.get('taxId') or attrs.get('ein'))
                    if tax_id:
                        tax_id_clean = str(tax_id).replace('-', '').replace(' ', '').strip()
                        if tax_id_clean.isdigit() and len(tax_id_clean) >= 9:
                            tax_id = tax_id_clean
                            logger.info(f"Found tax_id {tax_id} from entity/attributes top level")
                
                # Add tax_id to the returned attributes
                if tax_id:
                    attrs['tax_id'] = tax_id
                    attrs['ein'] = tax_id  # Also include as 'ein' for convenience
                    logger.info(f"Extracted tax ID {tax_id} from GLEIF for LEI {lei}")
                else:
                    logger.warning(f"No tax_id found in GLEIF record for LEI {lei}. Registration authorities count: {len(registration_authorities) if isinstance(registration_authorities, list) else 0}")
                    if logger.isEnabledFor(logging.DEBUG) and registration_authorities:
                        import json
                        logger.debug(f"Registration authorities: {json.dumps(registration_authorities, indent=2, default=str)}")
                
                return attrs
            return None
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.info(f"LEI not found: {lei}")
                return None
            logger.error(f"GLEIF API HTTP error for LEI {lei}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"GLEIF API error for LEI {lei}: {e}")
            return None
    
    def get_direct_parent(self, lei: str) -> Optional[Dict[str, Any]]:
        """
        Get direct parent entity.
        
        Args:
            lei: Legal Entity Identifier
            
        Returns:
            Parent entity details or None
        """
        try:
            url = f'{self.base_url}/lei-records/{lei.strip().upper()}/direct-parent'
            headers = {'Accept': 'application/vnd.api+json'}
            
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            if 'data' in data:
                return data['data']
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"GLEIF API error getting parent for {lei}: {e}")
            return None
    
    def get_ultimate_parent(self, lei: str) -> Optional[Dict[str, Any]]:
        """
        Get ultimate parent entity.
        
        Args:
            lei: Legal Entity Identifier
            
        Returns:
            Ultimate parent entity details or None
        """
        try:
            url = f'{self.base_url}/lei-records/{lei.strip().upper()}/ultimate-parent'
            headers = {'Accept': 'application/vnd.api+json'}
            
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            if 'data' in data:
                return data['data']
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"GLEIF API error getting ultimate parent for {lei}: {e}")
            return None
    
    def get_direct_children(self, lei: str) -> List[Dict[str, Any]]:
        """
        Get direct child entities (subsidiaries).
        
        Args:
            lei: Legal Entity Identifier
            
        Returns:
            List of child entities
        """
        try:
            url = f'{self.base_url}/lei-records/{lei.strip().upper()}/direct-children'
            headers = {'Accept': 'application/vnd.api+json'}
            
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            if 'data' in data:
                return data['data'] if isinstance(data['data'], list) else [data['data']]
            return []
            
        except requests.exceptions.RequestException as e:
            logger.error(f"GLEIF API error getting children for {lei}: {e}")
            return []
    
    def get_ultimate_children(self, lei: str) -> List[Dict[str, Any]]:
        """Get ultimate child entities (all subsidiaries in hierarchy)."""
        try:
            url = f'{self.base_url}/lei-records/{lei.strip().upper()}/ultimate-children'
            headers = {'Accept': 'application/vnd.api+json'}
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            if 'data' in data:
                return data['data'] if isinstance(data['data'], list) else [data['data']]
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"GLEIF API error getting ultimate children for {lei}: {e}")
            return []

    def get_all_subsidiaries(self, lei: str) -> Dict[str, List[Dict[str, Any]]]:
        """Get all subsidiaries (direct and ultimate children)."""
        direct = self.get_direct_children(lei)
        ultimate = self.get_ultimate_children(lei)
        direct_names = [c.get('attributes', {}).get('entity', {}).get('legalName', {}).get('name', 'N/A')
                       for c in direct if isinstance(c, dict)]
        ultimate_names = [c.get('attributes', {}).get('entity', {}).get('legalName', {}).get('name', 'N/A')
                        for c in ultimate if isinstance(c, dict)]
        logger.info(f"GLEIF subsidiaries for {lei}: {len(direct)} direct, {len(ultimate)} ultimate")
        return {'direct': direct, 'ultimate': ultimate, 'direct_names': direct_names, 'ultimate_names': ultimate_names}

    def _extract_entity_info(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Extract standardized entity info from a GLEIF record."""
        if not record or not isinstance(record, dict):
            return {}

        try:
            # Handle both direct API response and nested data structure
            attrs = None
            lei = None

            if 'attributes' in record and record['attributes']:
                attrs = record['attributes']
                lei = record.get('id')
            elif 'entity' in record:
                attrs = record
                lei = record.get('lei')
            else:
                # Try to extract LEI from various possible locations
                lei = record.get('id') or record.get('lei')
                if not lei:
                    return {}
                # Minimal info if we at least have LEI
                return {'lei': lei, 'name': '', 'legal_name': ''}

            if not attrs or not isinstance(attrs, dict):
                return {'lei': lei, 'name': '', 'legal_name': ''} if lei else {}

            entity = attrs.get('entity', {}) or {}
            if not isinstance(entity, dict):
                entity = {}

            legal_name = entity.get('legalName', {})
            if isinstance(legal_name, dict):
                name = legal_name.get('name', '')
            else:
                name = str(legal_name) if legal_name else ''

            # Get addresses with defensive handling
            legal_addr = entity.get('legalAddress', {}) or {}
            hq_addr = entity.get('headquartersAddress', {}) or {}
            if not isinstance(legal_addr, dict):
                legal_addr = {}
            if not isinstance(hq_addr, dict):
                hq_addr = {}

            return {
                'lei': lei,
                'name': name,
                'legal_name': name,
                'city': hq_addr.get('city') or legal_addr.get('city', ''),
                'state': hq_addr.get('region') or legal_addr.get('region', ''),
                'country': hq_addr.get('country') or legal_addr.get('country', ''),
                'status': entity.get('status', ''),
                'category': entity.get('category', ''),  # e.g., 'BRANCH', 'FUND', 'GENERAL'
            }
        except Exception as e:
            logger.warning(f"Error extracting entity info: {e}")
            return {}

    def get_corporate_family(self, lei: str) -> Dict[str, Any]:
        """
        Get complete corporate family: ultimate parent + all subsidiaries.

        Returns a structure with all entities that should be queried for data:
        {
            'queried_entity': {...},      # The entity we started with
            'ultimate_parent': {...},      # Top of corporate tree
            'direct_parent': {...},        # Immediate parent
            'siblings': [...],             # Other children of direct parent
            'children': [...],             # Direct children of queried entity
            'all_entities': [...],         # Deduplicated list of ALL entities
            'all_names': [...],            # All entity names for searching
            'all_leis': [...]              # All LEIs for querying
        }
        """
        result = {
            'queried_entity': None,
            'ultimate_parent': None,
            'direct_parent': None,
            'siblings': [],
            'children': [],
            'all_entities': [],
            'all_names': [],
            'all_leis': []
        }

        if not lei:
            return result

        lei = lei.strip().upper()
        seen_leis = set()
        all_entities = []

        # 1. Get the queried entity
        queried_record = self.get_lei_record(lei)
        if queried_record:
            queried_info = self._extract_entity_info({'attributes': queried_record, 'id': lei})
            queried_info['lei'] = lei  # Ensure LEI is set
            result['queried_entity'] = queried_info
            if lei not in seen_leis:
                all_entities.append(queried_info)
                seen_leis.add(lei)

        # 2. Get ultimate parent (top of tree)
        try:
            ultimate = self.get_ultimate_parent(lei)
            if ultimate:
                ultimate_info = self._extract_entity_info(ultimate)
                result['ultimate_parent'] = ultimate_info
                if ultimate_info.get('lei') and ultimate_info['lei'] not in seen_leis:
                    all_entities.append(ultimate_info)
                    seen_leis.add(ultimate_info['lei'])
        except Exception as e:
            logger.warning(f"Error getting ultimate parent for {lei}: {e}")

        # 3. Get direct parent
        try:
            direct_parent = self.get_direct_parent(lei)
            if direct_parent:
                parent_info = self._extract_entity_info(direct_parent)
                result['direct_parent'] = parent_info
                if parent_info.get('lei') and parent_info['lei'] not in seen_leis:
                    all_entities.append(parent_info)
                    seen_leis.add(parent_info['lei'])

                # 4. Get siblings (other children of direct parent)
                parent_lei = parent_info.get('lei')
                if parent_lei:
                    try:
                        siblings = self.get_direct_children(parent_lei)
                        for sib in siblings:
                            sib_info = self._extract_entity_info(sib)
                            sib_lei = sib_info.get('lei')
                            if sib_lei and sib_lei != lei and sib_lei not in seen_leis:
                                result['siblings'].append(sib_info)
                                all_entities.append(sib_info)
                                seen_leis.add(sib_lei)
                    except Exception as e:
                        logger.warning(f"Error getting siblings: {e}")
        except Exception as e:
            logger.warning(f"Error getting direct parent for {lei}: {e}")

        # 5. Get children of queried entity
        try:
            children = self.get_direct_children(lei)
            for child in children:
                child_info = self._extract_entity_info(child)
                child_lei = child_info.get('lei')
                if child_lei and child_lei not in seen_leis:
                    result['children'].append(child_info)
                    all_entities.append(child_info)
                    seen_leis.add(child_lei)
        except Exception as e:
            logger.warning(f"Error getting children for {lei}: {e}")

        # 6. If we have ultimate parent, also get ALL their children (full tree)
        ultimate_lei = result.get('ultimate_parent', {}).get('lei')
        if ultimate_lei and ultimate_lei != lei:
            try:
                all_children = self.get_ultimate_children(ultimate_lei)
                for child in all_children:
                    child_info = self._extract_entity_info(child)
                    child_lei = child_info.get('lei')
                    if child_lei and child_lei not in seen_leis:
                        all_entities.append(child_info)
                        seen_leis.add(child_lei)
            except Exception as e:
                logger.warning(f"Error getting all children of ultimate parent: {e}")

        # Compile final lists
        result['all_entities'] = all_entities
        result['all_names'] = [e['name'] for e in all_entities if e.get('name')]
        result['all_leis'] = [e['lei'] for e in all_entities if e.get('lei')]

        logger.info(f"Corporate family for {lei}: {len(all_entities)} entities, "
                   f"parent={result.get('ultimate_parent', {}).get('name', 'N/A')}, "
                   f"{len(result['children'])} children, {len(result['siblings'])} siblings")

        return result

    def search_by_name(self, name: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for entities by legal name using a tiered GLEIF search strategy.

        Strategy:
        1. Try exact legal name match (most precise)
        2. Try with common bank suffixes (", NATIONAL ASSOCIATION", ", N.A.")
        3. Fall back to fulltext search with scoring to prefer main entities

        Args:
            name: Entity name to search for
            limit: Maximum number of results (default 20, max 200)

        Returns:
            List of matching entities with LEI, legal name, and other attributes
        """
        headers = {'Accept': 'application/vnd.api+json'}
        url = f'{self.base_url}/lei-records'

        # Tier 1: Try exact legal name match with bank suffixes
        search_variations = [
            name,
            f"{name}, NATIONAL ASSOCIATION",
            f"{name}, N.A.",
            f"{name} NATIONAL ASSOCIATION",
        ]

        for search_term in search_variations:
            try:
                params = {
                    'filter[entity.legalName]': search_term,
                    'page[size]': min(limit, 200),
                    'page[number]': 1
                }

                logger.info(f"GLEIF exact name search: '{search_term}'")
                response = requests.get(url, headers=headers, params=params, timeout=self.timeout)

                if response.status_code == 200:
                    data = response.json()
                    if 'data' in data and isinstance(data['data'], list) and len(data['data']) > 0:
                        results = self._parse_search_results(data['data'])
                        # Filter to prefer US entities and main banks (not pension funds)
                        main_results = self._filter_main_entities(results, name)
                        if main_results:
                            logger.info(f"GLEIF exact match found: {main_results[0].get('legal_name')} (LEI: {main_results[0].get('lei')})")
                            return main_results

            except requests.exceptions.RequestException as e:
                logger.debug(f"GLEIF exact search failed for '{search_term}': {e}")
                continue

        # Tier 2: Fall back to fulltext search with scoring
        try:
            params = {
                'filter[fulltext]': name,
                'page[size]': min(limit * 2, 200),  # Get more results for better filtering
                'page[number]': 1
            }

            logger.info(f"GLEIF fulltext search: '{name}'")
            response = requests.get(url, headers=headers, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            results = []

            if 'data' in data and isinstance(data['data'], list):
                results = self._parse_search_results(data['data'])
                # Score and sort results to prefer main entities
                results = self._score_and_sort_results(results, name)

            logger.info(f"GLEIF fulltext returned {len(results)} results for '{name}'")
            if results:
                logger.info(f"Best match: {results[0].get('legal_name', 'N/A')} (LEI: {results[0].get('lei', 'N/A')})")

            return results[:limit]

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.info(f"No entities found for: {name}")
                return []
            logger.error(f"GLEIF API HTTP error searching for '{name}': {e}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"GLEIF API error searching for '{name}': {e}", exc_info=True)
            return []

    def _parse_search_results(self, data_items: List[Dict]) -> List[Dict[str, Any]]:
        """Parse GLEIF search results into standardized format."""
        results = []
        for item in data_items:
            if 'attributes' in item:
                attrs = item['attributes']
                entity = attrs.get('entity', {})

                # Extract tax ID (EIN) from entity registration authorities
                tax_id = None
                registration_authorities = entity.get('registrationAuthorities', [])
                if isinstance(registration_authorities, list):
                    for auth in registration_authorities:
                        if isinstance(auth, dict):
                            tax_id = (auth.get('registrationAuthorityEntityId') or
                                     auth.get('otherRegistrationAuthorityId') or
                                     auth.get('taxId'))
                            if tax_id:
                                break

                # Get country from legal address
                legal_addr = entity.get('legalAddress', {}) or {}
                country = legal_addr.get('country', '')

                entity_info = {
                    'lei': item.get('id'),
                    'legal_name': entity.get('legalName', {}).get('name', ''),
                    'legal_address': legal_addr,
                    'headquarters_address': entity.get('headquartersAddress', {}),
                    'country': country,
                    'tax_id': tax_id,
                    'registration_status': attrs.get('registration', {}).get('status', ''),
                    'entity_status': entity.get('status', ''),
                    'entity_category': entity.get('category', ''),
                    'registration_date': attrs.get('registration', {}).get('initialRegistrationDate', ''),
                    'last_update': attrs.get('registration', {}).get('lastUpdateDate', '')
                }
                results.append(entity_info)
        return results

    def _filter_main_entities(self, results: List[Dict], search_name: str) -> List[Dict[str, Any]]:
        """Filter results to exclude pension funds and foreign branches, prefer main banks."""
        search_upper = search_name.upper()
        filtered = []

        for r in results:
            name = r.get('legal_name', '').upper()
            country = r.get('country', '').upper()
            status = r.get('entity_status', '').upper()
            category = r.get('entity_category', '').upper()

            # Skip inactive entities
            if status == 'INACTIVE':
                continue

            # Skip pension funds and trust funds
            if any(term in name for term in ['PENSION', 'TRUST FUND', 'COMMINGLED']):
                continue

            # Skip foreign branches for US bank searches
            if 'BANK' in search_upper and country not in ('US', 'USA', ''):
                if 'GERMAN' in name or 'GESCHÄFTSSTELLE' in name or 'SUCURSAL' in name:
                    continue

            # Skip funds (category check)
            if category == 'FUND':
                continue

            # Add a priority score for sorting
            priority = 0
            if 'NATIONAL ASSOCIATION' in name or ', N.A.' in name:
                priority = 100  # Main national bank is highest priority
            elif search_upper == name:
                priority = 50  # Exact match
            elif search_upper in name:
                priority = 25  # Partial match

            r['_priority'] = priority
            filtered.append(r)

        # Sort by priority (highest first)
        filtered.sort(key=lambda x: x.get('_priority', 0), reverse=True)

        # Remove priority field
        for r in filtered:
            r.pop('_priority', None)

        return filtered

    def _score_and_sort_results(self, results: List[Dict], search_name: str) -> List[Dict[str, Any]]:
        """Score and sort results to prefer main entities over subsidiaries/funds."""
        search_upper = search_name.upper()

        for r in results:
            name = r.get('legal_name', '').upper()
            country = r.get('country', '').upper()
            status = r.get('entity_status', '').upper()
            category = r.get('entity_category', '').upper()

            score = 0

            # Exact match bonus
            if name == search_upper:
                score += 100
            elif name.startswith(search_upper):
                score += 50
            elif search_upper in name:
                score += 20

            # US bank with "NATIONAL ASSOCIATION" or ", N.A." is the main entity
            if 'NATIONAL ASSOCIATION' in name or ', N.A.' in name:
                score += 80

            # US-based entities preferred
            if country in ('US', 'USA'):
                score += 40

            # Active entities preferred
            if status == 'ACTIVE':
                score += 10

            # General entities preferred over funds/branches
            if category == 'GENERAL':
                score += 20
            elif category == 'BRANCH':
                score -= 20
            elif category == 'FUND':
                score -= 50

            # Penalize pension funds and trust funds heavily
            if any(term in name for term in ['PENSION', 'TRUST FUND', 'COMMINGLED']):
                score -= 100

            # Penalize foreign branches
            if 'GERMAN' in name or 'GESCHÄFTSSTELLE' in name or 'SUCURSAL' in name:
                score -= 60

            r['_score'] = score

        # Sort by score descending
        results.sort(key=lambda x: x.get('_score', 0), reverse=True)

        # Remove scoring field before returning
        for r in results:
            r.pop('_score', None)

        return results

