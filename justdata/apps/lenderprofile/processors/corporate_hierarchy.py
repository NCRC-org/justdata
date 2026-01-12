#!/usr/bin/env python3
"""
Corporate Hierarchy Handler
Manages parent/child relationships from GLEIF data for comprehensive analysis.
"""

import logging
from typing import Dict, Any, List, Optional, Set
from justdata.apps.lenderprofile.services.gleif_client import GLEIFClient

logger = logging.getLogger(__name__)

# Initialize GLEIF client for module-level use
_gleif_client = GLEIFClient()


def get_gleif_data_by_lei(lei: str) -> Optional[Dict[str, Any]]:
    """
    Get GLEIF data for a LEI, including parent/child relationships.

    Args:
        lei: Legal Entity Identifier

    Returns:
        Dictionary with GLEIF data or None
    """
    if not lei:
        return None

    try:
        # Get the main record
        record = _gleif_client.get_lei_record(lei)
        if not record:
            return None

        # Extract entity info
        entity = record.get('entity', {})
        result = {
            'lei': lei,
            'gleif_legal_name': entity.get('legalName', {}).get('name', ''),
            'cleaned_name': entity.get('legalName', {}).get('name', ''),
            'legal_address': entity.get('legalAddress', {}),
            'headquarters_address': entity.get('headquartersAddress', {}),
            'entity_status': entity.get('status', ''),
        }

        # Get parent info
        try:
            ultimate_parent = _gleif_client.get_ultimate_parent(lei)
            if ultimate_parent:
                parent_attrs = ultimate_parent.get('attributes', {})
                parent_entity = parent_attrs.get('entity', {})
                result['ultimate_parent'] = {
                    'lei': ultimate_parent.get('id'),
                    'name': parent_entity.get('legalName', {}).get('name', '')
                }
        except Exception as e:
            logger.debug(f"No ultimate parent for {lei}: {e}")

        try:
            direct_parent = _gleif_client.get_direct_parent(lei)
            if direct_parent:
                parent_attrs = direct_parent.get('attributes', {})
                parent_entity = parent_attrs.get('entity', {})
                result['direct_parent'] = {
                    'lei': direct_parent.get('id'),
                    'name': parent_entity.get('legalName', {}).get('name', '')
                }
        except Exception as e:
            logger.debug(f"No direct parent for {lei}: {e}")

        # Get children info
        try:
            direct_children = _gleif_client.get_direct_children(lei)
            if direct_children:
                result['direct_children'] = [
                    {
                        'lei': child.get('id'),
                        'name': child.get('attributes', {}).get('entity', {}).get('legalName', {}).get('name', '')
                    }
                    for child in direct_children if isinstance(child, dict)
                ]
        except Exception as e:
            logger.debug(f"No direct children for {lei}: {e}")

        try:
            ultimate_children = _gleif_client.get_ultimate_children(lei)
            if ultimate_children:
                result['ultimate_children'] = [
                    {
                        'lei': child.get('id'),
                        'name': child.get('attributes', {}).get('entity', {}).get('legalName', {}).get('name', '')
                    }
                    for child in ultimate_children if isinstance(child, dict)
                ]
        except Exception as e:
            logger.debug(f"No ultimate children for {lei}: {e}")

        return result

    except Exception as e:
        logger.error(f"Error getting GLEIF data for {lei}: {e}")
        return None


class CorporateHierarchy:
    """
    Handles corporate parent/child relationships for comprehensive lender analysis.
    
    When analyzing a lender, this class:
    1. Identifies if the entity is a parent, child, or standalone
    2. Collects all related entities (parent + all children)
    3. Provides methods to aggregate data across the hierarchy
    """
    
    def __init__(self):
        """Initialize corporate hierarchy handler."""
        pass
    
    def get_related_entities(self, lei: str) -> Dict[str, Any]:
        """
        Get all related entities (parent + children) for a given LEI.
        
        Args:
            lei: Legal Entity Identifier
            
        Returns:
            Dictionary with:
            - primary_lei: The main entity LEI (parent if exists, otherwise the input)
            - primary_name: Name of primary entity
            - parent: Parent entity info (if exists)
            - children: List of all child entities
            - all_entities: List of all LEIs in the hierarchy (parent + children)
            - hierarchy_type: 'parent', 'child', or 'standalone'
        """
        if not lei:
            return {
                'primary_lei': None,
                'primary_name': None,
                'parent': None,
                'children': [],
                'all_entities': [],
                'hierarchy_type': 'standalone'
            }
        
        # Get GLEIF data for the entity
        gleif_data = get_gleif_data_by_lei(lei)
        if not gleif_data:
            logger.warning(f"No GLEIF data found for LEI: {lei}")
            return {
                'primary_lei': lei,
                'primary_name': None,
                'parent': None,
                'children': [],
                'all_entities': [lei],
                'hierarchy_type': 'standalone'
            }
        
        entity_name = gleif_data.get('gleif_legal_name') or gleif_data.get('cleaned_name')
        ultimate_parent = gleif_data.get('ultimate_parent')
        direct_parent = gleif_data.get('direct_parent')
        direct_children = gleif_data.get('direct_children', [])
        ultimate_children = gleif_data.get('ultimate_children', [])
        
        # Determine if this is a parent, child, or standalone
        has_parent = bool(ultimate_parent or direct_parent)
        has_children = bool(direct_children or ultimate_children)
        
        # Determine primary entity (parent if exists, otherwise the input entity)
        if ultimate_parent:
            # This is a child - get parent data
            parent_lei = ultimate_parent.get('lei')
            parent_name = ultimate_parent.get('name')
            
            # Get parent's GLEIF data to find all children
            parent_gleif = get_gleif_data_by_lei(parent_lei) if parent_lei else None
            if parent_gleif:
                # Use parent's children list (more complete)
                all_children = parent_gleif.get('direct_children', []) or parent_gleif.get('ultimate_children', [])
            else:
                # Fallback to this entity's children
                all_children = direct_children or ultimate_children
            
            # Include this entity in children list if not already there
            all_children_leis = {child.get('lei') if isinstance(child, dict) else child for child in all_children}
            if lei not in all_children_leis:
                all_children.append({'lei': lei, 'name': entity_name})
            
            return {
                'primary_lei': parent_lei,  # Parent is primary
                'primary_name': parent_name,
                'parent': ultimate_parent,
                'children': all_children,
                'all_entities': [parent_lei] + [c.get('lei') if isinstance(c, dict) else c for c in all_children],
                'hierarchy_type': 'child',
                'original_entity': {
                    'lei': lei,
                    'name': entity_name
                }
            }
        
        elif has_children:
            # This is a parent
            all_children = direct_children or ultimate_children
            
            return {
                'primary_lei': lei,  # This entity is primary
                'primary_name': entity_name,
                'parent': None,
                'children': all_children,
                'all_entities': [lei] + [c.get('lei') if isinstance(c, dict) else c for c in all_children],
                'hierarchy_type': 'parent'
            }
        
        else:
            # Standalone entity
            return {
                'primary_lei': lei,
                'primary_name': entity_name,
                'parent': None,
                'children': [],
                'all_entities': [lei],
                'hierarchy_type': 'standalone'
            }
    
    def get_all_entity_leis(self, lei: str) -> List[str]:
        """
        Get list of all LEIs in the corporate hierarchy.
        
        Args:
            lei: Starting LEI
            
        Returns:
            List of all LEIs (parent + children)
        """
        hierarchy = self.get_related_entities(lei)
        return hierarchy.get('all_entities', [])
    
    def get_all_entity_names(self, lei: str) -> Dict[str, str]:
        """
        Get mapping of LEI -> name for all entities in hierarchy.
        
        Args:
            lei: Starting LEI
            
        Returns:
            Dictionary mapping LEI -> name
        """
        hierarchy = self.get_related_entities(lei)
        entity_map = {}
        
        # Add primary entity
        if hierarchy.get('primary_lei'):
            entity_map[hierarchy['primary_lei']] = hierarchy.get('primary_name', 'Unknown')
        
        # Add parent
        if hierarchy.get('parent'):
            parent = hierarchy['parent']
            if isinstance(parent, dict):
                entity_map[parent.get('lei')] = parent.get('name', 'Unknown')
        
        # Add children
        for child in hierarchy.get('children', []):
            if isinstance(child, dict):
                entity_map[child.get('lei')] = child.get('name', 'Unknown')
            else:
                # If child is just a LEI string, get the name
                child_gleif = get_gleif_data_by_lei(child)
                if child_gleif:
                    entity_map[child] = child_gleif.get('gleif_legal_name', 'Unknown')
        
        # Add original entity if different from primary
        if hierarchy.get('original_entity'):
            orig = hierarchy['original_entity']
            entity_map[orig.get('lei')] = orig.get('name', 'Unknown')
        
        return entity_map
    
    def should_aggregate_branches(self, lei: str) -> bool:
        """
        Determine if branch data should be aggregated across hierarchy.
        
        For parent companies, we typically want to aggregate branches from all children.
        
        Args:
            lei: Entity LEI
            
        Returns:
            True if branches should be aggregated
        """
        hierarchy = self.get_related_entities(lei)
        return hierarchy.get('hierarchy_type') in ['parent', 'child']
    
    def get_primary_entity_for_analysis(self, lei: str) -> Dict[str, Any]:
        """
        Get the primary entity to use for analysis (parent if exists).
        
        For example, if searching for "Fifth Third Bank" (a child),
        return "Fifth Third Bancorp" (the parent) for analysis.
        
        Args:
            lei: Starting LEI
            
        Returns:
            Dictionary with primary_lei and primary_name
        """
        hierarchy = self.get_related_entities(lei)
        return {
            'lei': hierarchy.get('primary_lei'),
            'name': hierarchy.get('primary_name'),
            'hierarchy_type': hierarchy.get('hierarchy_type'),
            'is_parent': hierarchy.get('hierarchy_type') == 'parent',
            'is_child': hierarchy.get('hierarchy_type') == 'child'
        }

