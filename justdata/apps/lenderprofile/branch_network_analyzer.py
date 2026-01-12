#!/usr/bin/env python3
"""
Branch Network Analyzer
Analyzes branch network changes over time - growth, shrinkage, and reallocation.
"""

import sys
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logger = logging.getLogger(__name__)

from shared.utils.unified_env import ensure_unified_env_loaded
from apps.lenderprofile.services.fdic_client import FDICClient
from apps.lenderprofile.services.bq_branch_client import BigQueryBranchClient
from apps.lenderprofile.services.bq_credit_union_branch_client import BigQueryCreditUnionBranchClient
from apps.lenderprofile.processors.identifier_resolver import IdentifierResolver

ensure_unified_env_loaded(verbose=True)


class BranchNetworkAnalyzer:
    """Analyzes branch network changes over time."""
    
    def __init__(self, use_bigquery: bool = True, institution_type: str = 'bank'):
        """
        Initialize analyzer.
        
        Args:
            use_bigquery: If True, use BigQuery tables (more accurate). 
                         If False, use FDIC API (may have year filtering issues).
            institution_type: 'bank' or 'credit_union'
        """
        self.use_bigquery = use_bigquery
        self.institution_type = institution_type
        if use_bigquery:
            if institution_type == 'credit_union':
                self.branch_client = BigQueryCreditUnionBranchClient()
            else:
                self.branch_client = BigQueryBranchClient()
        else:
            self.fdic_client = FDICClient()
    
    def get_branch_network_history(self, cert: str = None, rssd: str = None, cu_number: str = None, years: List[int] = None) -> Tuple[Dict[int, List[Dict[str, Any]]], Dict[int, Dict[str, Any]]]:
        """
        Get branch network data for multiple years.
        
        Note: FDIC API has a 10,000 branch limit. For large banks, we may need
        to use pagination or sample-based analysis.
        
        Args:
            cert: FDIC certificate number
            years: List of years to analyze (defaults to last 5 years)
            
        Returns:
            Dictionary mapping year to list of branches
        """
        if years is None:
            current_year = datetime.now().year
            years = list(range(current_year - 4, current_year + 1))  # Last 5 years
        
        branch_history = {}
        
        branch_metadata = {}
        
        # Fetch most recent year first to get accurate total
        most_recent_year = max(years) if years else datetime.now().year
        
        # Need RSSD for banks, RSSD or CU number for credit unions
        if self.use_bigquery:
            if self.institution_type == 'credit_union':
                if not rssd and not cu_number:
                    raise ValueError("RSSD or CU number is required for credit unions")
            else:
                if not rssd:
                    raise ValueError("RSSD is required when using BigQuery for banks")
        else:
            if not cert:
                raise ValueError("FDIC certificate number is required when using FDIC API")
        
        for year in sorted(years, reverse=True):  # Start with most recent
            logger.info(f"Fetching {year} branch data...")

            if self.use_bigquery:
                if self.institution_type == 'credit_union':
                    branches, metadata = self.branch_client.get_branches(rssd=rssd, cu_number=cu_number, year=year)
                else:
                    branches, metadata = self.branch_client.get_branches(rssd, year)
            else:
                branches, metadata = self.fdic_client.get_branches(cert, year=year)

            if branches:
                branch_history[year] = branches
                branch_metadata[year] = metadata
                returned = len(branches)

                if self.use_bigquery:
                    logger.info(f"Found {returned:,} branches for {year} (from BigQuery SOD)")
                else:
                    if metadata.get('hit_limit', False):
                        logger.info(f"Found {returned:,} branches for {year} (API limit reached)")
                    else:
                        logger.info(f"Found {returned:,} branches for {year}")
            else:
                logger.info(f"No data for {year}")
                branch_metadata[year] = {'total_available': 0, 'returned': 0, 'source': 'bigquery_sod' if self.use_bigquery else 'fdic_api'}
        
        return branch_history, branch_metadata
    
    def _create_branch_key(self, branch: Dict[str, Any]) -> str:
        """
        Create a unique key for a branch to track it across years.
        
        Uses city, state, and CBSA only (simplified matching).
        """
        city = (branch.get('city', '') or branch.get('CITY', '') or '').strip().upper()
        state = (branch.get('state', '') or branch.get('STALP', '') or branch.get('state_abbr', '') or '').strip().upper()
        
        # Get CBSA code (should be included in query results)
        cbsa_code = branch.get('cbsa_code') or branch.get('CBSA_CODE') or branch.get('cbsa') or 'N/A'
        
        # Key format: CITY|STATE|CBSA (simplified - no address details)
        return f"{city}|{state}|{cbsa_code}"
    
    def analyze_network_changes(self, branch_history: Dict[int, List[Dict[str, Any]]], branch_metadata: Dict[int, Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze branch network changes year-over-year.
        
        Returns:
            Dictionary with:
            - closures_by_year: Dict mapping year to list of closed branches
            - openings_by_year: Dict mapping year to list of opened branches
            - net_change_by_year: Dict mapping year to net change (openings - closures)
            - geographic_shifts: Analysis of where closures/openings are concentrated
            - trends: Summary statistics
        """
        if len(branch_history) < 2:
            return {
                'error': 'Need at least 2 years of data to analyze changes',
                'years_available': list(branch_history.keys())
            }
        
        # Sort years
        sorted_years = sorted(branch_history.keys())
        
        # Create branch sets for each year
        branch_sets = {}
        branch_details = {}  # Store full branch details by key
        
        for year in sorted_years:
            branch_set = set()
            for branch in branch_history[year]:
                key = self._create_branch_key(branch)
                branch_set.add(key)
                if key not in branch_details:
                    branch_details[key] = branch
            branch_sets[year] = branch_set
        
        # Analyze year-over-year changes
        closures_by_year = {}
        openings_by_year = {}
        net_change_by_year = {}
        
        for i in range(len(sorted_years) - 1):
            prev_year = sorted_years[i]
            curr_year = sorted_years[i + 1]
            
            prev_branches = branch_sets[prev_year]
            curr_branches = branch_sets[curr_year]
            
            # Closures: branches in prev_year but not in curr_year
            closed_keys = prev_branches - curr_branches
            closures = [branch_details[key] for key in closed_keys if key in branch_details]
            closures_by_year[curr_year] = closures
            
            # Openings: branches in curr_year but not in prev_year
            opened_keys = curr_branches - prev_branches
            openings = [branch_details[key] for key in opened_keys if key in branch_details]
            openings_by_year[curr_year] = openings
            
            # Net change
            net_change = len(openings) - len(closures)
            net_change_by_year[curr_year] = net_change
        
        # Analyze geographic patterns
        geographic_shifts = self._analyze_geographic_shifts(
            closures_by_year, openings_by_year, branch_details
        )
        
        # Calculate trends
        trends = self._calculate_trends(
            closures_by_year, openings_by_year, net_change_by_year, sorted_years
        )
        
        # Get total counts - use most recent year's total only, calculate others from changes
        total_branches_by_year = {}
        most_recent_year = max(sorted_years) if sorted_years else None
        
        # Get the most recent year's total (only trust this one)
        if most_recent_year and branch_metadata and most_recent_year in branch_metadata:
            most_recent_total = branch_metadata[most_recent_year].get('total_available', 0)
            # Only use if it's reasonable (not aggregated across all years)
            # If it's the same for all years, it's likely wrong - use returned count instead
            if most_recent_total > 0 and most_recent_total < 50000:  # Reasonable max
                base_total = most_recent_total
            else:
                # Use actual returned count for most recent year
                base_total = len(branch_history.get(most_recent_year, []))
        else:
            base_total = len(branch_history.get(most_recent_year, [])) if most_recent_year else 0
        
        # Calculate totals for each year working backwards from most recent
        total_branches_by_year[most_recent_year] = base_total
        
        for year in reversed(sorted_years[:-1]):  # All years except most recent
            # Calculate backwards: this year's total = next year's total - net change
            next_year = year + 1
            if next_year in total_branches_by_year:
                net_change = net_change_by_year.get(next_year, 0)
                total_branches_by_year[year] = total_branches_by_year[next_year] - net_change
            else:
                # Fallback: use returned count
                total_branches_by_year[year] = len(branch_history.get(year, []))
        
        return {
            'closures_by_year': closures_by_year,
            'openings_by_year': openings_by_year,
            'net_change_by_year': net_change_by_year,
            'geographic_shifts': geographic_shifts,
            'trends': trends,
            'years_analyzed': sorted_years,
            'total_branches_by_year': total_branches_by_year,
            'returned_branches_by_year': {year: len(branches) for year, branches in branch_history.items()},
            'metadata': branch_metadata or {}
        }
    
    def _analyze_geographic_shifts(
        self, 
        closures_by_year: Dict[int, List[Dict[str, Any]]],
        openings_by_year: Dict[int, List[Dict[str, Any]]],
        branch_details: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze where closures and openings are geographically concentrated."""
        
        # Aggregate all closures and openings
        all_closures = []
        for closures in closures_by_year.values():
            all_closures.extend(closures)
        
        all_openings = []
        for openings in openings_by_year.values():
            all_openings.extend(openings)
        
        # Count by state
        closures_by_state = defaultdict(int)
        openings_by_state = defaultdict(int)
        
        for branch in all_closures:
            state = branch.get('state', '') or branch.get('STALP', '')
            if state:
                closures_by_state[state] += 1
        
        for branch in all_openings:
            state = branch.get('state', '') or branch.get('STALP', '')
            if state:
                openings_by_state[state] += 1
        
        # Count by MSA/CBSA
        closures_by_msa = defaultdict(int)
        openings_by_msa = defaultdict(int)
        
        for branch in all_closures:
            msa = branch.get('cbsa_name', '') or branch.get('CBSA_METRO_NAME', '')
            if msa:
                closures_by_msa[msa] += 1
        
        for branch in all_openings:
            msa = branch.get('cbsa_name', '') or branch.get('CBSA_METRO_NAME', '')
            if msa:
                openings_by_msa[msa] += 1
        
        # Count by city
        closures_by_city = defaultdict(int)
        openings_by_city = defaultdict(int)
        
        for branch in all_closures:
            city = branch.get('city', '') or branch.get('CITY', '')
            state = branch.get('state', '') or branch.get('STALP', '')
            if city and state:
                key = f"{city}, {state}"
                closures_by_city[key] += 1
        
        for branch in all_openings:
            city = branch.get('city', '') or branch.get('CITY', '')
            state = branch.get('state', '') or branch.get('STALP', '')
            if city and state:
                key = f"{city}, {state}"
                openings_by_city[key] += 1
        
        return {
            'closures_by_state': dict(closures_by_state),
            'openings_by_state': dict(openings_by_state),
            'closures_by_msa': dict(closures_by_msa),
            'openings_by_msa': dict(openings_by_msa),
            'closures_by_city': dict(closures_by_city),
            'openings_by_city': dict(openings_by_city),
            'total_closures': len(all_closures),
            'total_openings': len(all_openings)
        }
    
    def _calculate_trends(
        self,
        closures_by_year: Dict[int, List[Dict[str, Any]]],
        openings_by_year: Dict[int, List[Dict[str, Any]]],
        net_change_by_year: Dict[int, int],
        years: List[int]
    ) -> Dict[str, Any]:
        """Calculate trend statistics."""
        
        closure_counts = [len(closures_by_year.get(year, [])) for year in years[1:]]
        opening_counts = [len(openings_by_year.get(year, [])) for year in years[1:]]
        net_changes = [net_change_by_year.get(year, 0) for year in years[1:]]
        
        avg_closures_per_year = sum(closure_counts) / len(closure_counts) if closure_counts else 0
        avg_openings_per_year = sum(opening_counts) / len(opening_counts) if opening_counts else 0
        avg_net_change_per_year = sum(net_changes) / len(net_changes) if net_changes else 0
        
        # Determine overall trend
        if avg_net_change_per_year < -50:
            trend = 'significant_shrinkage'
        elif avg_net_change_per_year < -10:
            trend = 'moderate_shrinkage'
        elif avg_net_change_per_year < 10:
            trend = 'stable'
        elif avg_net_change_per_year < 50:
            trend = 'moderate_growth'
        else:
            trend = 'significant_growth'
        
        return {
            'avg_closures_per_year': round(avg_closures_per_year, 1),
            'avg_openings_per_year': round(avg_openings_per_year, 1),
            'avg_net_change_per_year': round(avg_net_change_per_year, 1),
            'total_closures': sum(closure_counts),
            'total_openings': sum(opening_counts),
            'overall_trend': trend,
            'closure_counts_by_year': {years[i+1]: count for i, count in enumerate(closure_counts)},
            'opening_counts_by_year': {years[i+1]: count for i, count in enumerate(opening_counts)}
        }
    
    def generate_narrative(self, analysis: Dict[str, Any]) -> str:
        """
        Generate a narrative summary of branch network changes.
        
        Example: "Bank A has been closing branches at a pace of 100 per year,
        with closures focused in area X and some new openings in area Y."
        """
        if 'error' in analysis:
            return f"Unable to analyze: {analysis['error']}"
        
        trends = analysis['trends']
        geographic = analysis['geographic_shifts']
        years = analysis['years_analyzed']
        
        narrative_parts = []
        
        # Overall trend - use total counts if available
        total_by_year = analysis['total_branches_by_year']
        if len(total_by_year) >= 2:
            sorted_years = sorted(total_by_year.keys())
            first_year = sorted_years[0]
            last_year = sorted_years[-1]
            first_total = total_by_year[first_year]
            last_total = total_by_year[last_year]
            total_change = last_total - first_total
            years_span = last_year - first_year
            
            if years_span > 0:
                avg_net_from_totals = total_change / years_span
                
                if avg_net_from_totals < -50:
                    narrative_parts.append(
                        f"The bank has been closing branches at a pace of approximately "
                        f"{abs(avg_net_from_totals):.0f} per year, reducing from {first_total:,} branches in {first_year} "
                        f"to {last_total:,} branches in {last_year} (net change: {total_change:+,})."
                    )
                elif avg_net_from_totals < -10:
                    narrative_parts.append(
                        f"The bank has been gradually reducing its branch network by approximately "
                        f"{abs(avg_net_from_totals):.0f} branches per year, from {first_total:,} in {first_year} "
                        f"to {last_total:,} in {last_year}."
                    )
                elif avg_net_from_totals > 50:
                    narrative_parts.append(
                        f"The bank has been expanding its branch network at a pace of approximately "
                        f"{avg_net_from_totals:.0f} new branches per year, growing from {first_total:,} branches in {first_year} "
                        f"to {last_total:,} branches in {last_year}."
                    )
                elif avg_net_from_totals > 10:
                    narrative_parts.append(
                        f"The bank has been gradually expanding its branch network by approximately "
                        f"{avg_net_from_totals:.0f} branches per year."
                    )
                else:
                    narrative_parts.append(
                        f"The bank's branch network has remained relatively stable, with "
                        f"{first_total:,} branches in {first_year} and {last_total:,} branches in {last_year}."
                    )
        
        # Fallback to sampled data trends
        if not narrative_parts:
            avg_net = trends['avg_net_change_per_year']
            avg_closures = trends['avg_closures_per_year']
            avg_openings = trends['avg_openings_per_year']
            
            if avg_net < 0:
                narrative_parts.append(
                    f"Based on sampled data, the bank has been closing branches at an average pace of "
                    f"{abs(avg_net):.0f} per year over the {len(years)-1}-year period analyzed."
                )
            elif avg_net > 0:
                narrative_parts.append(
                    f"Based on sampled data, the bank has been expanding its branch network at an average pace of "
                    f"{avg_net:.0f} new branches per year."
                )
            else:
                narrative_parts.append(
                    f"Based on sampled data, the bank's branch network has remained relatively stable, with "
                    f"approximately {avg_closures:.0f} closures and {avg_openings:.0f} openings per year."
                )
        
        # Closure patterns
        if geographic['total_closures'] > 0:
            closures_by_state = sorted(
                geographic['closures_by_state'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            if closures_by_state:
                top_states = [f"{state} ({count})" for state, count in closures_by_state]
                narrative_parts.append(
                    f"Branch closures have been concentrated in: {', '.join(top_states)}."
                )
            
            # Top cities for closures
            closures_by_city = sorted(
                geographic['closures_by_city'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            
            if closures_by_city:
                top_cities = [f"{city} ({count} branches)" for city, count in closures_by_city]
                narrative_parts.append(
                    f"Notable closure concentrations include: {', '.join(top_cities)}."
                )
        
        # Opening patterns
        if geographic['total_openings'] > 0:
            openings_by_state = sorted(
                geographic['openings_by_state'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            if openings_by_state:
                top_states = [f"{state} ({count})" for state, count in openings_by_state]
                narrative_parts.append(
                    f"New branch openings have been focused in: {', '.join(top_states)}."
                )
            
            # Top cities for openings
            openings_by_city = sorted(
                geographic['openings_by_city'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            
            if openings_by_city:
                top_cities = [f"{city} ({count} branches)" for city, count in openings_by_city]
                narrative_parts.append(
                    f"Key expansion areas include: {', '.join(top_cities)}."
                )
        
        # Year-over-year summary
        net_changes = analysis['net_change_by_year']
        total_by_year = analysis.get('total_branches_by_year', {})
        
        if len(net_changes) > 1:
            year_summary = []
            for year in sorted(net_changes.keys()):
                change = net_changes[year]
                closures = len(analysis['closures_by_year'].get(year, []))
                openings = len(analysis['openings_by_year'].get(year, []))
                total = total_by_year.get(year, 0)
                
                if closures > 0 or openings > 0:
                    year_summary.append(
                        f"{year}: {openings} opened, {closures} closed (net: {change:+d}, total: {total})"
                    )
                elif total > 0:
                    year_summary.append(
                        f"{year}: {total} branches (no changes detected)"
                    )
            
            if year_summary:
                narrative_parts.append(
                    f"Year-over-year changes: {'; '.join(year_summary)}."
                )
        
        # Add note about API limitations if applicable
        if analysis.get('most_recent_hit_limit', False):
            narrative_parts.append(
                "Note: Analysis is limited by FDIC API's 10,000 branch limit. The API's year filter may not be working correctly, "
                "so actual branch counts may differ from what's shown. Consider using known branch counts for the most recent year."
            )
        
        return " ".join(narrative_parts)


def analyze_bank_branches(lender_name: str, years: List[int] = None):
    """Main function to analyze a bank's branch network."""
    print("=" * 80)
    print("BRANCH NETWORK ANALYSIS")
    print("=" * 80)
    print(f"\nAnalyzing branch network for: '{lender_name}'")
    
    # Resolve identifiers
    print("\n1. Resolving identifiers...")
    resolver = IdentifierResolver()
    candidates = resolver.get_candidates_with_location(lender_name, limit=1)
    
    if not candidates:
        print("ERROR: Could not find lender")
        return
    
    candidate = candidates[0]
    fdic_cert = candidate.get('fdic_cert')
    rssd = candidate.get('rssd_id') or candidate.get('rssd') or candidate.get('federal_reserve_rssd')
    institution_name = candidate.get('name')
    
    print(f"   Found: {institution_name}")
    print(f"   FDIC Cert: {fdic_cert}")
    print(f"   RSSD: {rssd}")
    
    # Prefer BigQuery (more accurate year filtering) - require RSSD
    use_bigquery = bool(rssd)
    if not rssd:
        print("   WARNING: No RSSD found, falling back to FDIC API")
        use_bigquery = False
        if not fdic_cert:
            print("ERROR: No FDIC certificate number or RSSD found")
            return
    
    # Get branch history
    print(f"\n2. Fetching branch network history from {'BigQuery SOD' if use_bigquery else 'FDIC API'}...")
    analyzer = BranchNetworkAnalyzer(use_bigquery=use_bigquery)
    branch_history, branch_metadata = analyzer.get_branch_network_history(
        cert=fdic_cert, 
        rssd=rssd, 
        years=years
    )
    
    if not branch_history:
        print("ERROR: No branch data found")
        return
    
    # Analyze changes
    print(f"\n3. Analyzing network changes...")
    analysis = analyzer.analyze_network_changes(branch_history, branch_metadata)
    
    # Display results
    print("\n" + "=" * 80)
    print("ANALYSIS RESULTS")
    print("=" * 80)
    
    # Network size by year
    total_by_year = analysis['total_branches_by_year']
    returned_by_year = analysis.get('returned_branches_by_year', {})
    print(f"\nNetwork Size by Year:")
    for year in sorted(total_by_year.keys()):
        total = total_by_year[year]
        returned = returned_by_year.get(year, 0)
        if total > returned:
            print(f"   {year}: {total:,} total branches (sampled: {returned:,})")
        else:
            print(f"   {year}: {total:,} branches")
    
    # Trends
    trends = analysis['trends']
    print(f"\nOverall Trends (based on sampled data):")
    print(f"   Average closures per year: {trends['avg_closures_per_year']:.1f}")
    print(f"   Average openings per year: {trends['avg_openings_per_year']:.1f}")
    print(f"   Average net change per year: {trends['avg_net_change_per_year']:+.1f}")
    print(f"   Overall trend: {trends['overall_trend']}")
    
    # Calculate net change from total counts
    if len(total_by_year) >= 2:
        sorted_years = sorted(total_by_year.keys())
        print(f"\nNetwork Size Changes (from total counts):")
        for i in range(len(sorted_years) - 1):
            prev_year = sorted_years[i]
            curr_year = sorted_years[i + 1]
            prev_total = total_by_year[prev_year]
            curr_total = total_by_year[curr_year]
            change = curr_total - prev_total
            change_pct = (change / prev_total * 100) if prev_total > 0 else 0
            print(f"   {prev_year} to {curr_year}: {change:+,} branches ({change_pct:+.1f}%)")
    
    # Geographic shifts
    geographic = analysis['geographic_shifts']
    print(f"\nGeographic Patterns:")
    
    if geographic['closures_by_state']:
        print(f"\n   Top 10 States for Closures:")
        sorted_states = sorted(geographic['closures_by_state'].items(), key=lambda x: x[1], reverse=True)
        for i, (state, count) in enumerate(sorted_states[:10], 1):
            print(f"   {i:2}. {state}: {count} closures")
    
    if geographic['openings_by_state']:
        print(f"\n   Top 10 States for Openings:")
        sorted_states = sorted(geographic['openings_by_state'].items(), key=lambda x: x[1], reverse=True)
        for i, (state, count) in enumerate(sorted_states[:10], 1):
            print(f"   {i:2}. {state}: {count} openings")
    
    # Narrative
    print(f"\n" + "=" * 80)
    print("NARRATIVE SUMMARY")
    print("=" * 80)
    narrative = analyzer.generate_narrative(analysis)
    print(f"\n{narrative}\n")


if __name__ == '__main__':
    lender_name = sys.argv[1] if len(sys.argv) > 1 else "Fifth Third Bank"
    years = None
    if len(sys.argv) > 2:
        years = [int(y) for y in sys.argv[2].split(',')]
    
    analyze_bank_branches(lender_name, years)

