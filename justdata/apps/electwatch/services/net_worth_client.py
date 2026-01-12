#!/usr/bin/env python3
"""
Net Worth Data Service for ElectWatch

Provides estimated net worth data for members of Congress based on
annual financial disclosure filings. Data sources:
- OpenSecrets/Center for Responsive Politics
- Congressional Financial Disclosures (OGE 278e forms)

Net worth is reported in ranges (e.g., $1M-$5M) due to disclosure rules.
This service provides midpoint estimates and ranges for scoring calculations.

Updated annually when new disclosures are released (typically May-June).
"""

import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Net worth estimates for members of Congress (2024 disclosures)
# Format: 'normalized_name': {'min': dollars, 'max': dollars, 'year': disclosure_year}
# Names should be lowercase for matching
# Data sources: OpenSecrets, financial disclosures
NET_WORTH_DATA = {
    # Ultra-wealthy members (>$50M)
    'nancy pelosi': {'min': 100_000_000, 'max': 250_000_000, 'year': 2024},
    'rick scott': {'min': 200_000_000, 'max': 300_000_000, 'year': 2024},
    'greg gianforte': {'min': 150_000_000, 'max': 200_000_000, 'year': 2024},
    'mark warner': {'min': 200_000_000, 'max': 250_000_000, 'year': 2024},
    'vern buchanan': {'min': 100_000_000, 'max': 150_000_000, 'year': 2024},
    'michael mccaul': {'min': 75_000_000, 'max': 125_000_000, 'year': 2024},
    'darrell issa': {'min': 200_000_000, 'max': 300_000_000, 'year': 2024},
    'ro khanna': {'min': 25_000_000, 'max': 75_000_000, 'year': 2024},
    'josh gottheimer': {'min': 10_000_000, 'max': 25_000_000, 'year': 2024},
    'trey hollingsworth': {'min': 50_000_000, 'max': 100_000_000, 'year': 2024},

    # Very wealthy members ($10M-$50M)
    'french hill': {'min': 10_000_000, 'max': 25_000_000, 'year': 2024},
    'james french hill': {'min': 10_000_000, 'max': 25_000_000, 'year': 2024},
    'kevin hern': {'min': 25_000_000, 'max': 50_000_000, 'year': 2024},
    'dan crenshaw': {'min': 5_000_000, 'max': 10_000_000, 'year': 2024},
    'ted cruz': {'min': 5_000_000, 'max': 15_000_000, 'year': 2024},
    'mitch mcconnell': {'min': 30_000_000, 'max': 40_000_000, 'year': 2024},
    'john kennedy': {'min': 5_000_000, 'max': 15_000_000, 'year': 2024},
    'shelley moore capito': {'min': 5_000_000, 'max': 10_000_000, 'year': 2024},
    'tommy tuberville': {'min': 5_000_000, 'max': 15_000_000, 'year': 2024},
    'markwayne mullin': {'min': 25_000_000, 'max': 50_000_000, 'year': 2024},

    # Moderately wealthy members ($1M-$10M)
    'marjorie taylor greene': {'min': 1_000_000, 'max': 5_000_000, 'year': 2024},
    'byron donalds': {'min': 1_000_000, 'max': 5_000_000, 'year': 2024},
    'ritchie torres': {'min': 100_000, 'max': 500_000, 'year': 2024},
    'john fetterman': {'min': 500_000, 'max': 1_000_000, 'year': 2024},
    'jared moskowitz': {'min': 1_000_000, 'max': 5_000_000, 'year': 2024},
    'val hoyle': {'min': 500_000, 'max': 2_000_000, 'year': 2024},
    'valerie hoyle': {'min': 500_000, 'max': 2_000_000, 'year': 2024},
    'jake auchincloss': {'min': 5_000_000, 'max': 10_000_000, 'year': 2024},
    'greg landsman': {'min': 500_000, 'max': 2_000_000, 'year': 2024},
    'debbie dingell': {'min': 5_000_000, 'max': 15_000_000, 'year': 2024},
    'rick larsen': {'min': 1_000_000, 'max': 5_000_000, 'year': 2024},
    'bruce westerman': {'min': 1_000_000, 'max': 5_000_000, 'year': 2024},
    'dan newhouse': {'min': 5_000_000, 'max': 15_000_000, 'year': 2024},
    'thomas kean': {'min': 5_000_000, 'max': 10_000_000, 'year': 2024},
    'neal dunn': {'min': 5_000_000, 'max': 15_000_000, 'year': 2024},
    'james comer': {'min': 1_000_000, 'max': 5_000_000, 'year': 2024},
    'dwight evans': {'min': 500_000, 'max': 2_000_000, 'year': 2024},

    # Lower wealth members (<$1M)
    'jonathan jackson': {'min': 100_000, 'max': 500_000, 'year': 2024},
    'cleo fields': {'min': 500_000, 'max': 2_000_000, 'year': 2024},
    'carol miller': {'min': 5_000_000, 'max': 15_000_000, 'year': 2024},
    'daniel meuser': {'min': 5_000_000, 'max': 15_000_000, 'year': 2024},
    'lisa mcclain': {'min': 1_000_000, 'max': 5_000_000, 'year': 2024},
    'julie johnson': {'min': 1_000_000, 'max': 5_000_000, 'year': 2024},
    'rich mccormick': {'min': 1_000_000, 'max': 5_000_000, 'year': 2024},
    'tim moore': {'min': 500_000, 'max': 2_000_000, 'year': 2024},
    'tony wied': {'min': 1_000_000, 'max': 5_000_000, 'year': 2024},
    'sheri biggs': {'min': 500_000, 'max': 2_000_000, 'year': 2024},
}

# Default net worth estimate for members without specific data
DEFAULT_NET_WORTH = {'min': 1_000_000, 'max': 5_000_000, 'year': 2024}


def normalize_name(name: str) -> str:
    """Normalize name for matching (lowercase, remove titles)."""
    if not name:
        return ""

    name = name.lower().strip()

    # Remove common titles and suffixes
    for title in ['rep.', 'sen.', 'mr.', 'mrs.', 'ms.', 'dr.', 'jr.', 'sr.', 'iii', 'ii', 'iv']:
        name = name.replace(title, '')

    # Remove extra spaces
    return ' '.join(name.split())


def get_net_worth(name: str) -> Dict[str, Any]:
    """
    Get estimated net worth for a member of Congress.

    Args:
        name: Name of the official

    Returns:
        Dict with keys: min, max, midpoint, display, year, is_estimate
    """
    normalized = normalize_name(name)

    # Try exact match first
    data = NET_WORTH_DATA.get(normalized)

    # Try last name match if no exact match
    if not data:
        parts = normalized.split()
        if parts:
            last_name = parts[-1]
            for known_name, known_data in NET_WORTH_DATA.items():
                if last_name in known_name.split():
                    data = known_data
                    break

    # Use default if no match found
    is_estimate = data is None
    if not data:
        data = DEFAULT_NET_WORTH

    # Calculate midpoint and display string
    min_val = data['min']
    max_val = data['max']
    midpoint = (min_val + max_val) // 2

    # Format display string
    def format_amount(val):
        if val >= 1_000_000_000:
            return f"${val / 1_000_000_000:.1f}B"
        elif val >= 1_000_000:
            return f"${val / 1_000_000:.0f}M"
        elif val >= 1_000:
            return f"${val / 1_000:.0f}K"
        return f"${val:,.0f}"

    display = f"{format_amount(min_val)}-{format_amount(max_val)}"

    return {
        'min': min_val,
        'max': max_val,
        'midpoint': midpoint,
        'display': display,
        'year': data.get('year', 2024),
        'is_estimate': is_estimate
    }


def calculate_wealth_weight(trade_amount: float, net_worth_midpoint: float) -> float:
    """
    Calculate a wealth-adjusted weight for a trade.

    A $50K trade means more for someone worth $500K than someone worth $100M.
    This returns a multiplier that increases the significance of trades
    relative to the official's wealth.

    Args:
        trade_amount: Dollar amount of the trade
        net_worth_midpoint: Estimated net worth midpoint

    Returns:
        Wealth adjustment factor (higher = more significant relative to wealth)
    """
    if net_worth_midpoint <= 0:
        return 1.0

    # Calculate trade as percentage of net worth
    trade_pct = (trade_amount / net_worth_midpoint) * 100

    # Apply a logarithmic scale to avoid extreme outliers
    # Base weight of 1.0, with bonus for high trade-to-wealth ratio
    import math
    weight = 1.0 + math.log10(1 + trade_pct)

    return round(weight, 2)


def get_wealth_tier(net_worth_midpoint: float) -> Tuple[str, str]:
    """
    Get wealth tier classification for display.

    Returns:
        Tuple of (tier_code, tier_display)
    """
    if net_worth_midpoint >= 100_000_000:
        return ('ultra_wealthy', '$100M+')
    elif net_worth_midpoint >= 25_000_000:
        return ('very_wealthy', '$25M-$100M')
    elif net_worth_midpoint >= 5_000_000:
        return ('wealthy', '$5M-$25M')
    elif net_worth_midpoint >= 1_000_000:
        return ('comfortable', '$1M-$5M')
    else:
        return ('modest', '<$1M')


# Testing
if __name__ == '__main__':
    # Test cases
    test_names = [
        'Nancy Pelosi',
        'Marjorie Taylor Greene',
        'Rep. French Hill',
        'John Unknown',  # Should use default
    ]

    for name in test_names:
        nw = get_net_worth(name)
        tier_code, tier_display = get_wealth_tier(nw['midpoint'])
        print(f"{name}:")
        print(f"  Net Worth: {nw['display']} (est: {nw['is_estimate']})")
        print(f"  Tier: {tier_display}")

        # Test wealth weight for a $50K trade
        weight = calculate_wealth_weight(50000, nw['midpoint'])
        print(f"  $50K trade weight: {weight}")
        print()
