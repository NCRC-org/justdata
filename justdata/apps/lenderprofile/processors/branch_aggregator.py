#!/usr/bin/env python3
"""
Branch Aggregator
Aggregates branch data across parent/child corporate hierarchy.
"""

import logging
from typing import Dict, Any, List, Optional
from justdata.apps.lenderprofile.services.bq_branch_client import BigQueryBranchClient
from justdata.apps.lenderprofile.services.bq_credit_union_branch_client import BigQueryCreditUnionBranchClient
from justdata.apps.lenderprofile.processors.corporate_hierarchy import CorporateHierarchy
from justdata.apps.dataexplorer.data_utils import get_gleif_data_by_lei

logger = logging.getLogger(__name__)


class BranchAggregator:
    """
    Aggregates branch network data across corporate hierarchy.
    
    For parent companies, aggregates branches from all child entities.
    """
    
    def __init__(self):
        """Initialize branch aggregator."""
        self.bank_client = BigQueryBranchClient()
        self.cu_client = BigQueryCreditUnionBranchClient()
        self.hierarchy = CorporateHierarchy()
    
    def get_aggregated_branches(self, lei: str, year: int, institution_type: str = 'bank') -> Dict[str, Any]:
        """
        Get aggregated branch data across corporate hierarchy.
        
        Args:
            lei: Starting LEI (may be child or parent)
            year: Year to get branches for
            institution_type: 'bank' or 'credit_union'
            
        Returns:
            Dictionary with:
            - total_branches: Total count across all entities
            - branches_by_entity: Breakdown by entity
            - all_branches: Combined list of all branches
            - hierarchy_info: Corporate hierarchy information
        """
        # Get hierarchy information
        hierarchy_info = self.hierarchy.get_related_entities(lei)
        all_entities = hierarchy_info.get('all_entities', [lei])
        
        if len(all_entities) == 1:
            # No hierarchy, just get branches for single entity
            return self._get_single_entity_branches(lei, year, institution_type)
        
        # Aggregate across all entities
        logger.info(f"Aggregating branches across {len(all_entities)} entities for year {year}")
        
        all_branches = []
        branches_by_entity = {}
        total_branches = 0
        
        for entity_lei in all_entities:
            # Get entity name
            entity_gleif = get_gleif_data_by_lei(entity_lei)
            entity_name = entity_gleif.get('gleif_legal_name', 'Unknown') if entity_gleif else 'Unknown'
            
            # Get RSSD for this entity (would need to resolve from LEI)
            # For now, we'll need to get RSSD from identifiers or GLEIF
            # This is a placeholder - actual implementation would need RSSD lookup
            
            # Get branches for this entity
            entity_branches, metadata = self._get_branches_for_entity(
                entity_lei, year, institution_type
            )
            
            if entity_branches:
                branches_by_entity[entity_lei] = {
                    'name': entity_name,
                    'branches': entity_branches,
                    'count': len(entity_branches)
                }
                all_branches.extend(entity_branches)
                total_branches += len(entity_branches)
        
        return {
            'total_branches': total_branches,
            'branches_by_entity': branches_by_entity,
            'all_branches': all_branches,
            'hierarchy_info': hierarchy_info,
            'year': year
        }
    
    def _get_single_entity_branches(self, lei: str, year: int, institution_type: str) -> Dict[str, Any]:
        """Get branches for a single entity (no hierarchy)."""
        # This would need RSSD lookup from LEI
        # Placeholder implementation
        return {
            'total_branches': 0,
            'branches_by_entity': {},
            'all_branches': [],
            'hierarchy_info': {'hierarchy_type': 'standalone'},
            'year': year
        }
    
    def _get_branches_for_entity(self, lei: str, year: int, institution_type: str) -> tuple:
        """Get branches for a specific entity by LEI."""
        # This is a placeholder - would need to:
        # 1. Look up RSSD from LEI (via GLEIF or other mapping)
        # 2. Get branches using RSSD
        # For now, return empty
        return [], {}
    
    def aggregate_branch_analysis(self, lei: str, years: List[int], institution_type: str = 'bank') -> Dict[str, Any]:
        """
        Aggregate branch network analysis across corporate hierarchy.
        
        This would be used by branch_network_analyzer to analyze the entire
        corporate family's branch network.
        
        Args:
            lei: Starting LEI
            years: List of years to analyze
            institution_type: 'bank' or 'credit_union'
            
        Returns:
            Aggregated analysis results
        """
        # Get hierarchy
        hierarchy_info = self.hierarchy.get_related_entities(lei)
        all_entities = hierarchy_info.get('all_entities', [lei])
        
        # For each year, aggregate branches
        aggregated_by_year = {}
        for year in years:
            year_data = self.get_aggregated_branches(lei, year, institution_type)
            aggregated_by_year[year] = year_data
        
        return {
            'hierarchy': hierarchy_info,
            'years': aggregated_by_year,
            'summary': {
                'total_entities': len(all_entities),
                'primary_entity': hierarchy_info.get('primary_name'),
                'years_analyzed': years
            }
        }

