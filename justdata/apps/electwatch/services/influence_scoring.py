#!/usr/bin/env python3
"""
ElectWatch Influence Scoring Framework

Calculates a three-dimensional influence score for Congress members based on:
1. SCALE - Total dollar volume of financial sector activity
2. CONCENTRATION - How focused activity is on specific firms/sectors
3. PERSONAL INVOLVEMENT - Trading relative to personal wealth

Each dimension is scored 0-100, with a composite score also 0-100.
"""

import logging
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class InfluenceScore:
    """Holds the three-dimensional influence score for an official."""
    scale_score: float  # 0-100
    concentration_score: float  # 0-100
    personal_involvement_score: float  # 0-100
    composite_score: float  # 0-100 weighted average

    # Component details for transparency
    scale_details: Dict
    concentration_details: Dict
    personal_involvement_details: Dict

    def to_dict(self) -> Dict:
        return {
            'scale_score': round(self.scale_score, 1),
            'concentration_score': round(self.concentration_score, 1),
            'personal_involvement_score': round(self.personal_involvement_score, 1),
            'composite_score': round(self.composite_score, 1),
            'scale_details': self.scale_details,
            'concentration_details': self.concentration_details,
            'personal_involvement_details': self.personal_involvement_details,
        }


class InfluenceScoringEngine:
    """
    Calculates influence scores for Congress members.

    Methodology:

    1. SCALE (weight: 40%)
       Measures total financial sector activity in dollars.
       - Stock trades in financial sector tickers (using SEC SIC codes 6000-6799)
       - PAC contributions from financial sector
       - Individual contributions from financial sector employers

       Scoring: Log-scaled percentile ranking among all officials

    2. CONCENTRATION (weight: 30%)
       Measures how focused activity is on specific entities.
       - Top firm concentration (% of activity in top 3 firms)
       - Sector concentration (% in single subsector like banking vs diversified)
       - Repeat trading patterns (same ticker traded multiple times)

       Scoring: Higher concentration = higher score (more potential for quid pro quo)

    3. PERSONAL INVOLVEMENT (weight: 30%)
       Measures trading activity relative to personal wealth.
       - Trade volume as % of estimated net worth
       - Frequency of trades (trades per month)
       - Direct ownership vs spouse/dependent

       Scoring: Higher ratio of trading to wealth = higher score
    """

    # Scoring weights
    WEIGHT_SCALE = 0.40
    WEIGHT_CONCENTRATION = 0.30
    WEIGHT_PERSONAL = 0.30

    # Financial sector SIC range
    FINANCIAL_SIC_MIN = 6000
    FINANCIAL_SIC_MAX = 6799

    def __init__(self,
                 officials: List[Dict],
                 ticker_classifications: Optional[Dict[str, Dict]] = None,
                 net_worth_data: Optional[Dict[str, float]] = None):
        """
        Initialize the scoring engine.

        Args:
            officials: List of official records with trades, contributions
            ticker_classifications: Dict mapping ticker -> {is_financial, sector, subsector}
            net_worth_data: Dict mapping bioguide_id -> estimated net worth in dollars
        """
        self.officials = officials
        self.ticker_classifications = ticker_classifications or {}
        self.net_worth_data = net_worth_data or {}

        # Pre-calculate population statistics for percentile scoring
        self._calculate_population_stats()

    def _calculate_population_stats(self):
        """Calculate population-level statistics for percentile scoring."""
        # Collect all scale values for percentile calculation
        scale_values = []
        for official in self.officials:
            scale = self._calculate_raw_scale(official)
            if scale > 0:
                scale_values.append(scale)

        self._scale_values_sorted = sorted(scale_values)
        self._scale_population_size = len(scale_values)

        logger.info(f"Population stats: {self._scale_population_size} officials with financial activity")

    def _is_financial_ticker(self, ticker: str) -> bool:
        """Check if a ticker is in the financial sector."""
        ticker = ticker.upper().strip()

        if ticker in self.ticker_classifications:
            return self.ticker_classifications[ticker].get('is_financial', False)

        # Default to False if not classified
        return False

    def _get_ticker_subsector(self, ticker: str) -> Optional[str]:
        """Get the subsector for a ticker."""
        ticker = ticker.upper().strip()
        if ticker in self.ticker_classifications:
            return self.ticker_classifications[ticker].get('subsector')
        return None

    def _calculate_raw_scale(self, official: Dict) -> float:
        """
        Calculate raw scale value (total financial sector dollars).

        Components:
        - Financial sector stock trades (min amount)
        - Financial sector PAC contributions
        - Financial sector individual contributions
        """
        total = 0.0

        # Stock trades in financial sector
        for trade in official.get('trades', []):
            ticker = trade.get('ticker', '')
            if self._is_financial_ticker(ticker):
                amount = trade.get('amount', {})
                if isinstance(amount, dict):
                    total += amount.get('min', 0)
                else:
                    total += amount or 0

        # Financial PAC contributions (already filtered to financial in pipeline)
        for pac in official.get('top_financial_pacs', []):
            total += pac.get('amount', 0)

        # Financial individual contributions
        total += official.get('financial_individual_total', 0)

        return total

    def _calculate_scale_score(self, official: Dict) -> Tuple[float, Dict]:
        """
        Calculate scale score (0-100) based on percentile ranking.

        Uses log-scaled values to handle the wide range of activity levels.
        """
        raw_scale = self._calculate_raw_scale(official)

        if raw_scale == 0:
            return 0.0, {
                'raw_dollars': 0,
                'percentile': 0,
                'financial_trades_dollars': 0,
                'financial_pac_dollars': 0,
                'financial_individual_dollars': 0,
            }

        # Calculate percentile
        # Find position in sorted list
        position = 0
        for val in self._scale_values_sorted:
            if val <= raw_scale:
                position += 1
            else:
                break

        percentile = (position / self._scale_population_size) * 100 if self._scale_population_size > 0 else 0

        # Component breakdown
        financial_trades = sum(
            (t.get('amount', {}).get('min', 0) if isinstance(t.get('amount'), dict) else t.get('amount', 0))
            for t in official.get('trades', [])
            if self._is_financial_ticker(t.get('ticker', ''))
        )

        financial_pac = sum(p.get('amount', 0) for p in official.get('top_financial_pacs', []))
        financial_individual = official.get('financial_individual_total', 0)

        details = {
            'raw_dollars': round(raw_scale, 2),
            'percentile': round(percentile, 1),
            'financial_trades_dollars': round(financial_trades, 2),
            'financial_pac_dollars': round(financial_pac, 2),
            'financial_individual_dollars': round(financial_individual, 2),
        }

        return percentile, details

    def _calculate_concentration_score(self, official: Dict) -> Tuple[float, Dict]:
        """
        Calculate concentration score (0-100).

        Higher concentration = higher score (more focused on specific entities).

        Components:
        - Top 3 ticker concentration (% of trade value in top 3 tickers)
        - Subsector concentration (% in dominant subsector)
        - Repeat trading (average trades per ticker)
        """
        trades = official.get('trades', [])

        if not trades:
            return 0.0, {
                'top3_concentration': 0,
                'subsector_concentration': 0,
                'repeat_trading_ratio': 0,
                'top_tickers': [],
                'dominant_subsector': None,
            }

        # Calculate ticker concentration
        ticker_amounts = defaultdict(float)
        ticker_counts = defaultdict(int)
        subsector_amounts = defaultdict(float)

        total_amount = 0
        for trade in trades:
            ticker = trade.get('ticker', '').upper()
            if not ticker:
                continue

            amount = trade.get('amount', {})
            if isinstance(amount, dict):
                amt = amount.get('min', 0)
            else:
                amt = amount or 0

            ticker_amounts[ticker] += amt
            ticker_counts[ticker] += 1
            total_amount += amt

            subsector = self._get_ticker_subsector(ticker)
            if subsector:
                subsector_amounts[subsector] += amt

        # Top 3 ticker concentration
        sorted_tickers = sorted(ticker_amounts.items(), key=lambda x: -x[1])
        top3 = sorted_tickers[:3]
        top3_amount = sum(amt for _, amt in top3)
        top3_concentration = (top3_amount / total_amount * 100) if total_amount > 0 else 0

        # Subsector concentration
        if subsector_amounts:
            dominant_subsector = max(subsector_amounts.items(), key=lambda x: x[1])
            subsector_concentration = (dominant_subsector[1] / total_amount * 100) if total_amount > 0 else 0
            dominant_subsector_name = dominant_subsector[0]
        else:
            subsector_concentration = 0
            dominant_subsector_name = None

        # Repeat trading ratio (avg trades per ticker, normalized)
        unique_tickers = len(ticker_counts)
        total_trades = len(trades)
        repeat_ratio = (total_trades / unique_tickers) if unique_tickers > 0 else 0
        # Normalize: 1 trade per ticker = 0, 10+ trades per ticker = 100
        repeat_score = min(100, (repeat_ratio - 1) * 11.1)

        # Composite concentration score
        # Weight: 50% top3, 30% subsector, 20% repeat
        concentration_score = (
            top3_concentration * 0.5 +
            subsector_concentration * 0.3 +
            repeat_score * 0.2
        )

        details = {
            'top3_concentration': round(top3_concentration, 1),
            'subsector_concentration': round(subsector_concentration, 1),
            'repeat_trading_ratio': round(repeat_ratio, 2),
            'top_tickers': [t[0] for t in top3],
            'dominant_subsector': dominant_subsector_name,
        }

        return concentration_score, details

    def _calculate_personal_involvement_score(self, official: Dict) -> Tuple[float, Dict]:
        """
        Calculate personal involvement score (0-100).

        Measures trading activity relative to personal wealth.

        Components:
        - Trade volume as % of net worth (if available)
        - Trading frequency (trades per month)
        - Direct ownership ratio (vs spouse/dependent)
        """
        trades = official.get('trades', [])
        bioguide_id = official.get('bioguide_id', '')

        if not trades:
            return 0.0, {
                'trade_to_wealth_ratio': None,
                'trades_per_month': 0,
                'direct_ownership_ratio': 0,
                'net_worth_available': False,
            }

        # Calculate total trade volume
        total_trade_volume = 0
        direct_trades = 0

        for trade in trades:
            amount = trade.get('amount', {})
            if isinstance(amount, dict):
                total_trade_volume += amount.get('min', 0)
            else:
                total_trade_volume += amount or 0

            owner_type = trade.get('owner_type', '').lower()
            if owner_type in ['self', 'joint', ''] or 'self' in owner_type:
                direct_trades += 1

        # Trade to wealth ratio
        net_worth = self.net_worth_data.get(bioguide_id)
        if net_worth and net_worth > 0:
            trade_to_wealth = (total_trade_volume / net_worth) * 100
            # Cap at 100% for scoring
            wealth_score = min(100, trade_to_wealth)
            net_worth_available = True
        else:
            trade_to_wealth = None
            wealth_score = 50  # Neutral if unknown
            net_worth_available = False

        # Trading frequency (trades per month over 3-year window)
        # Data window is Jan 2023 - present (~36 months)
        months = 36
        trades_per_month = len(trades) / months
        # Normalize: 0 = 0, 10+ per month = 100
        frequency_score = min(100, trades_per_month * 10)

        # Direct ownership ratio
        direct_ratio = (direct_trades / len(trades) * 100) if trades else 0

        # Composite score
        if net_worth_available:
            # Weight: 50% wealth ratio, 30% frequency, 20% direct ownership
            score = wealth_score * 0.5 + frequency_score * 0.3 + direct_ratio * 0.2
        else:
            # Without net worth, weight frequency more
            score = frequency_score * 0.6 + direct_ratio * 0.4

        details = {
            'trade_to_wealth_ratio': round(trade_to_wealth, 2) if trade_to_wealth else None,
            'total_trade_volume': round(total_trade_volume, 2),
            'trades_per_month': round(trades_per_month, 2),
            'direct_ownership_ratio': round(direct_ratio, 1),
            'net_worth': net_worth,
            'net_worth_available': net_worth_available,
        }

        return score, details

    def calculate_score(self, official: Dict) -> InfluenceScore:
        """
        Calculate the complete influence score for an official.

        Returns:
            InfluenceScore with all three dimensions and composite
        """
        scale_score, scale_details = self._calculate_scale_score(official)
        concentration_score, concentration_details = self._calculate_concentration_score(official)
        personal_score, personal_details = self._calculate_personal_involvement_score(official)

        # Weighted composite
        composite = (
            scale_score * self.WEIGHT_SCALE +
            concentration_score * self.WEIGHT_CONCENTRATION +
            personal_score * self.WEIGHT_PERSONAL
        )

        return InfluenceScore(
            scale_score=scale_score,
            concentration_score=concentration_score,
            personal_involvement_score=personal_score,
            composite_score=composite,
            scale_details=scale_details,
            concentration_details=concentration_details,
            personal_involvement_details=personal_details,
        )

    def calculate_all_scores(self) -> Dict[str, InfluenceScore]:
        """
        Calculate scores for all officials.

        Returns:
            Dict mapping bioguide_id -> InfluenceScore
        """
        scores = {}
        for official in self.officials:
            bioguide_id = official.get('bioguide_id')
            if bioguide_id:
                scores[bioguide_id] = self.calculate_score(official)

        logger.info(f"Calculated influence scores for {len(scores)} officials")
        return scores

    def get_leaderboard(self,
                        dimension: str = 'composite',
                        limit: int = 25) -> List[Tuple[Dict, InfluenceScore]]:
        """
        Get ranked leaderboard by specified dimension.

        Args:
            dimension: 'composite', 'scale', 'concentration', or 'personal'
            limit: Number of results to return

        Returns:
            List of (official, score) tuples, sorted descending
        """
        results = []

        for official in self.officials:
            score = self.calculate_score(official)

            if dimension == 'composite':
                sort_value = score.composite_score
            elif dimension == 'scale':
                sort_value = score.scale_score
            elif dimension == 'concentration':
                sort_value = score.concentration_score
            elif dimension == 'personal':
                sort_value = score.personal_involvement_score
            else:
                sort_value = score.composite_score

            results.append((official, score, sort_value))

        # Sort by the chosen dimension
        results.sort(key=lambda x: -x[2])

        return [(official, score) for official, score, _ in results[:limit]]


def test_scoring():
    """Test the scoring engine with sample data."""
    import json
    from pathlib import Path

    # Load officials
    officials_path = Path(__file__).parent.parent / "data" / "current" / "officials.json"
    if not officials_path.exists():
        officials_path = Path(__file__).parent.parent / "data" / "weekly" / "2026-01-31" / "officials.json"

    with open(officials_path) as f:
        data = json.load(f)

    officials = data.get('officials', data.get('data', []))

    # Load unified ticker classifications (combines SEC + yfinance)
    from justdata.apps.electwatch.services.unified_classifier import UnifiedClassifier

    classifier = UnifiedClassifier()
    all_classifications = classifier.classify_all()

    # Convert to the format expected by the scoring engine
    ticker_classifications = {}
    for ticker, info in all_classifications.items():
        ticker_classifications[ticker] = {
            'is_financial': info.get('is_financial', False),
            'subsector': info.get('sub_sector') or info.get('sector', ''),
        }

    print(f"Loaded {len(officials)} officials")
    print(f"Loaded {len(ticker_classifications)} ticker classifications")

    # Create scoring engine
    engine = InfluenceScoringEngine(
        officials=officials,
        ticker_classifications=ticker_classifications,
        net_worth_data={}  # Not available yet
    )

    # Get composite leaderboard
    print("\n" + "="*80)
    print("TOP 25 BY COMPOSITE INFLUENCE SCORE")
    print("="*80)

    leaderboard = engine.get_leaderboard(dimension='composite', limit=25)

    print(f"{'Rank':<5} {'Name':<30} {'Composite':>10} {'Scale':>10} {'Concen':>10} {'Personal':>10}")
    print("-"*80)

    for i, (official, score) in enumerate(leaderboard, 1):
        name = official.get('name', 'Unknown')[:28]
        print(f"{i:<5} {name:<30} {score.composite_score:>10.1f} {score.scale_score:>10.1f} "
              f"{score.concentration_score:>10.1f} {score.personal_involvement_score:>10.1f}")

    # Show detailed breakdown for top official
    if leaderboard:
        top_official, top_score = leaderboard[0]
        print("\n" + "="*80)
        print(f"DETAILED BREAKDOWN: {top_official.get('name')}")
        print("="*80)
        print(f"\nScale Details: {top_score.scale_details}")
        print(f"\nConcentration Details: {top_score.concentration_details}")
        print(f"\nPersonal Involvement Details: {top_score.personal_involvement_details}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    test_scoring()
