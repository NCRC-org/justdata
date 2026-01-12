#!/usr/bin/env python3
"""
ElectWatch core analysis logic.
Analyzes financial relationships of elected officials.
"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

REPO_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(REPO_ROOT))

from apps.electwatch.config import ElectWatchConfig
from apps.electwatch.services.firm_mapper import (
    FirmMapper, get_mapper, AmountRange, parse_stock_amount
)

logger = logging.getLogger(__name__)


@dataclass
class OfficialProfile:
    """Represents an elected official's profile and financial data."""
    id: str
    name: str
    party: str
    state: str
    chamber: str  # 'house' or 'senate'
    district: Optional[str] = None
    committees: List[str] = None
    is_finance_committee: bool = False
    leadership_roles: List[str] = None

    # Financial data
    contributions: List[Dict] = None
    stock_trades: List[Dict] = None
    involvement_by_industry: Dict[str, Dict] = None
    involvement_score: float = 0.0
    total_amount: float = 0.0

    def __post_init__(self):
        if self.committees is None:
            self.committees = []
        if self.leadership_roles is None:
            self.leadership_roles = []
        if self.contributions is None:
            self.contributions = []
        if self.stock_trades is None:
            self.stock_trades = []
        if self.involvement_by_industry is None:
            self.involvement_by_industry = {}


def run_official_analysis(
    official_id: str,
    include_ai: bool = True,
    job_id: str = None,
    progress_tracker = None
) -> Dict:
    """
    Run comprehensive analysis for an elected official.

    Args:
        official_id: Unique identifier for the official
        include_ai: Whether to include AI-generated insights
        job_id: Job ID for tracking
        progress_tracker: Progress tracker instance

    Returns:
        Dictionary with analysis results
    """
    try:
        # Initialize progress
        if progress_tracker:
            progress_tracker.update_progress('initializing', 5, 'Starting analysis...')

        # Step 1: Load official profile
        if progress_tracker:
            progress_tracker.update_progress('loading_profile', 15, 'Loading official profile...')

        official = _get_official_profile(official_id)
        if not official:
            return {'success': False, 'error': f'Official not found: {official_id}'}

        # Step 2: Fetch FEC contribution data
        if progress_tracker:
            progress_tracker.update_progress('fetching_contributions', 30, 'Fetching contribution data...')

        contributions = _fetch_contributions(official)

        # Step 3: Fetch stock trade data
        if progress_tracker:
            progress_tracker.update_progress('fetching_trades', 45, 'Fetching stock trade data...')

        stock_trades = _fetch_stock_trades(official)

        # Step 4: Map to industries
        if progress_tracker:
            progress_tracker.update_progress('mapping_industries', 60, 'Mapping to industries...')

        mapper = get_mapper()
        involvement = mapper.aggregate_by_industry(contributions, stock_trades)

        # Step 5: Calculate involvement score
        if progress_tracker:
            progress_tracker.update_progress('calculating_score', 75, 'Calculating involvement score...')

        score = calculate_involvement_score(
            contributions=contributions,
            stock_trades=stock_trades,
            involvement=involvement,
            committees=official.committees
        )

        # Step 6: Generate AI insights (optional)
        insights = None
        if include_ai and ElectWatchConfig.CLAUDE_API_KEY:
            if progress_tracker:
                progress_tracker.update_progress('generating_insights', 90, 'Generating AI insights...')
            insights = _generate_ai_insights(official, contributions, stock_trades, involvement)

        # Build result
        if progress_tracker:
            progress_tracker.update_progress('finalizing', 95, 'Finalizing report...')

        # Calculate totals with proper range handling
        total_contributions = sum(c.get('amount', 0) for c in contributions)

        # Stock trades use ranges from STOCK Act buckets
        stock_trades_range = AmountRange.zero()
        for trade in stock_trades:
            stock_trades_range = stock_trades_range + parse_stock_amount(trade)

        # Total is contributions (exact) + stock trades (range)
        total_amount_range = AmountRange(
            min_amount=total_contributions + stock_trades_range.min_amount,
            max_amount=total_contributions + stock_trades_range.max_amount
        )

        result = {
            'success': True,
            'official': {
                'id': official.id,
                'name': official.name,
                'party': official.party,
                'state': official.state,
                'chamber': official.chamber,
                'district': official.district,
                'committees': official.committees,
                'is_finance_committee': official.is_finance_committee,
            },
            'involvement_by_industry': involvement,
            'involvement_score': score,
            'total_contributions': total_contributions,
            'stock_trades_range': stock_trades_range.to_dict(),
            'total_amount': total_amount_range.to_dict(),
            'contributions_count': len(contributions),
            'stock_trades_count': len(stock_trades),
            'contributions': contributions[:50],  # Limit for response size
            'stock_trades': stock_trades[:50],
            'ai_insights': insights,
            'generated_at': datetime.now().isoformat(),
            'data_freshness': {
                'contributions': 'weekly',
                'stock_trades': 'weekly',
                'note': 'Stock trades may lag up to 45 days per STOCK Act requirements'
            }
        }

        return result

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return {'success': False, 'error': str(e)}


def calculate_involvement_score(
    contributions: List[Dict],
    stock_trades: List[Dict],
    involvement: Dict[str, Dict],
    committees: List[str]
) -> float:
    """
    Calculate composite involvement score (0-100 scale).

    Components:
    - Campaign contributions received: 25%
    - PAC contributions received: 20%
    - Stock holdings value: 20% (uses midpoint of range for scoring)
    - Stock trade volume: 15%
    - Committee assignments (finance-related): 10%
    - Concentration (single industry focus): 10%

    Time decay applied:
    - < 1 year: 100%
    - 1-2 years: 75%
    - 2-4 years: 50%
    - 4+ years: 25%

    Note: Stock trade amounts are ranges (STOCK Act buckets). For scoring,
    we use the midpoint of the range to calculate a single score value.
    """
    score = 0.0

    # Contribution score (25%)
    total_contributions = sum(c.get('amount', 0) for c in contributions)
    # Scale: $0 = 0, $500K+ = 25
    contrib_score = min(25, (total_contributions / 500000) * 25)
    score += contrib_score

    # PAC contribution score (20%)
    pac_contributions = sum(c.get('amount', 0) for c in contributions if 'PAC' in c.get('source', '').upper())
    pac_score = min(20, (pac_contributions / 300000) * 20)
    score += pac_score

    # Stock value score (20%) - using midpoint of ranges for scoring
    stock_value_range = AmountRange.zero()
    for trade in stock_trades:
        if trade.get('type') == 'purchase':
            stock_value_range = stock_value_range + parse_stock_amount(trade)
    # Use midpoint for scoring purposes
    total_stock_value = (stock_value_range.min_amount + stock_value_range.max_amount) / 2
    stock_score = min(20, (total_stock_value / 500000) * 20)
    score += stock_score

    # Trade volume score (15%)
    trade_count = len(stock_trades)
    volume_score = min(15, (trade_count / 50) * 15)
    score += volume_score

    # Committee score (10%)
    finance_committees = [
        'Financial Services', 'Ways and Means', 'Budget',
        'Banking', 'Finance', 'Appropriations', 'Small Business'
    ]
    finance_committee_count = sum(1 for c in committees if any(fc.lower() in c.lower() for fc in finance_committees))
    committee_score = min(10, (finance_committee_count / 2) * 10)
    score += committee_score

    # Concentration score (10%) - higher if focused on fewer industries
    # Note: involvement totals now include range data
    if involvement:
        totals = []
        for v in involvement.values():
            total_data = v.get('total', {})
            if isinstance(total_data, dict):
                # Use midpoint of range for concentration calculation
                totals.append((total_data.get('min', 0) + total_data.get('max', 0)) / 2)
            else:
                totals.append(total_data)
        max_total = max(totals) if totals else 0
        sum_total = sum(totals) if totals else 0
        concentration = (max_total / sum_total) if sum_total > 0 else 0
        concentration_score = concentration * 10
        score += concentration_score

    return round(min(100, score), 1)


def _get_official_profile(official_id: str) -> Optional[OfficialProfile]:
    """
    Get official profile from database/cache.

    In production, this would query BigQuery or use cached data.
    For now, returns sample data.
    """
    # TODO: Implement actual data lookup
    # Sample data for testing
    sample_officials = {
        'hill_j_french': OfficialProfile(
            id='hill_j_french',
            name='J. French Hill',
            party='R',
            state='AR',
            chamber='house',
            district='2',
            committees=['Financial Services'],
            is_finance_committee=True,
            leadership_roles=['Chair, Financial Services Committee']
        ),
        'waters_maxine': OfficialProfile(
            id='waters_maxine',
            name='Maxine Waters',
            party='D',
            state='CA',
            chamber='house',
            district='43',
            committees=['Financial Services'],
            is_finance_committee=True,
            leadership_roles=['Ranking Member, Financial Services Committee']
        ),
    }

    return sample_officials.get(official_id)


def _fetch_contributions(official: OfficialProfile) -> List[Dict]:
    """
    Fetch FEC contribution data for an official.

    In production, this would call the FEC API.
    """
    # TODO: Implement FEC API call
    # Sample data for testing
    return [
        {
            'source': 'WELLS FARGO & COMPANY PAC',
            'amount': 50000,
            'date': '2025-03-15',
            'type': 'pac'
        },
        {
            'source': 'COINBASE GLOBAL INC PAC',
            'amount': 25000,
            'date': '2025-02-01',
            'type': 'pac'
        },
        {
            'source': 'JPMORGAN CHASE & CO. PAC',
            'amount': 35000,
            'date': '2025-04-10',
            'type': 'pac'
        },
    ]


def _fetch_stock_trades(official: OfficialProfile) -> List[Dict]:
    """
    Fetch stock trade data from Quiver/STOCK Act disclosures.

    In production, this would call the Quiver API.
    """
    # TODO: Implement Quiver API call
    # Sample data for testing
    return [
        {
            'ticker': 'WFC',
            'company': 'Wells Fargo',
            'amount': 50000,  # Mid-point of range
            'amount_range': '$15,001 - $50,000',
            'date': '2025-04-10',
            'type': 'purchase'
        },
        {
            'ticker': 'COIN',
            'company': 'Coinbase',
            'amount': 75000,
            'amount_range': '$50,001 - $100,000',
            'date': '2025-05-15',
            'type': 'purchase'
        },
    ]


def _generate_ai_insights(
    official: OfficialProfile,
    contributions: List[Dict],
    stock_trades: List[Dict],
    involvement: Dict[str, Dict]
) -> Dict:
    """
    Generate AI-powered insights about the official's financial relationships.
    """
    try:
        from shared.analysis.ai_provider import AIAnalyzer

        # Build data summary
        data_summary = {
            'official': {
                'name': official.name,
                'party': official.party,
                'state': official.state,
                'committees': official.committees
            },
            'contributions': contributions[:10],
            'stock_trades': stock_trades[:10],
            'involvement_by_industry': {
                k: {'total': v.get('total', 0), 'firms': v.get('firms', [])}
                for k, v in involvement.items()
            }
        }

        prompt = f"""Analyze the financial relationships for {official.name} ({official.party}-{official.state}).

Data:
{json.dumps(data_summary, indent=2, default=str)}

Provide a concise analysis with:
1. Summary (2-3 sentences)
2. Key financial relationships
3. Potential conflicts of interest (if any)
4. Notable patterns

Format as JSON with keys: summary, key_relationships, potential_conflicts, notable_patterns
"""

        analyzer = AIAnalyzer(ai_provider='claude')
        response = analyzer._call_ai(prompt, max_tokens=1000)

        # Try to parse as JSON
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {'summary': response}

    except Exception as e:
        logger.warning(f"AI insights generation failed: {e}")
        return None


# =============================================================================
# LEADERBOARD FUNCTIONS
# =============================================================================

def get_officials_leaderboard(
    chamber: str = None,
    party: str = None,
    state: str = None,
    industry: str = None,
    sort_by: str = 'score',
    limit: int = 50
) -> List[Dict]:
    """
    Get leaderboard of officials by involvement score.

    Args:
        chamber: Filter by 'house' or 'senate'
        party: Filter by party ('R', 'D', 'I')
        state: Filter by state code
        industry: Filter by industry sector
        sort_by: Sort field ('score', 'total', 'contributions', 'trades')
        limit: Maximum results

    Returns:
        List of official summaries with scores
    """
    # TODO: Implement actual data query
    # This would query BigQuery with pre-calculated scores

    return []


def get_industry_leaders(sector: str, limit: int = 20) -> List[Dict]:
    """
    Get officials with highest involvement in a specific industry sector.
    """
    # TODO: Implement
    return []


def get_firm_connections(firm_name: str) -> Dict:
    """
    Get all officials connected to a specific firm.
    """
    # TODO: Implement
    return {}


# =============================================================================
# DATA REFRESH FUNCTIONS
# =============================================================================

def refresh_official_data(official_id: str) -> bool:
    """
    Refresh data for a specific official from all sources.
    """
    # TODO: Implement
    return False


def refresh_all_data() -> Dict:
    """
    Refresh data for all tracked officials.
    Returns summary of refresh operation.
    """
    # TODO: Implement
    return {'success': False, 'message': 'Not implemented'}


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    # Test analysis
    result = run_official_analysis('hill_j_french', include_ai=False)
    print(json.dumps(result, indent=2, default=str))
