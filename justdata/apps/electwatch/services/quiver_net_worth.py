#!/usr/bin/env python3
"""
Quiver-based Net Worth Calculator for ElectWatch

Fetches congress holdings from Quiver Quantitative API and calculates
estimated net worth based on disclosed stock positions.

This is more accurate than hardcoded estimates because it uses actual
disclosed holdings data, updated regularly.

Note: This only captures stock holdings. Real net worth may be higher
due to real estate, private businesses, and other assets not in disclosures.
"""

import os
import json
import logging
import requests
from typing import Dict, Any, Optional, List, Tuple
from functools import lru_cache
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Cache timeout (refresh every 24 hours)
_cache = {}
_cache_timestamp = None
CACHE_DURATION = timedelta(hours=24)


def _get_api_key() -> Optional[str]:
    """Get Quiver API key from environment."""
    return os.getenv('QUIVER_API_KEY')


def _normalize_name(name: str) -> str:
    """Normalize name for matching."""
    if not name:
        return ""
    # Remove leading/trailing spaces and standardize
    name = name.strip().lower()
    # Remove common titles
    for title in ['rep.', 'sen.', 'representative', 'senator', 'mr.', 'mrs.', 'ms.', 'dr.']:
        name = name.replace(title, '')
    return ' '.join(name.split())


def fetch_all_holdings() -> Dict[str, Dict]:
    """
    Fetch all congress holdings from Quiver API.

    Returns:
        Dict mapping normalized politician names to their holdings data
    """
    global _cache, _cache_timestamp

    # Check cache
    if _cache and _cache_timestamp:
        if datetime.now() - _cache_timestamp < CACHE_DURATION:
            return _cache

    api_key = _get_api_key()
    if not api_key:
        logger.warning("QUIVER_API_KEY not set - cannot fetch holdings")
        return {}

    try:
        url = "https://api.quiverquant.com/beta/live/congressholdings"
        headers = {"Authorization": f"Bearer {api_key}"}

        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()

        data = response.json()

        # Build lookup by normalized name
        holdings_by_name = {}
        for record in data:
            politician = record.get('Politician', '').strip()
            holdings_str = record.get('Holdings', '{}')
            pol_type = record.get('Type', '')

            try:
                holdings = json.loads(holdings_str) if isinstance(holdings_str, str) else holdings_str
            except json.JSONDecodeError:
                holdings = {}

            # Calculate total from holdings
            total = sum(v for v in holdings.values() if isinstance(v, (int, float)))

            normalized = _normalize_name(politician)
            holdings_by_name[normalized] = {
                'name': politician,
                'type': pol_type,
                'holdings': holdings,
                'stock_total': total,
                'num_positions': len(holdings)
            }

            # Also index by last name for fuzzy matching
            parts = normalized.split()
            if parts:
                last_name = parts[-1]
                if last_name not in holdings_by_name:
                    holdings_by_name[last_name] = holdings_by_name[normalized]

        _cache = holdings_by_name
        _cache_timestamp = datetime.now()

        logger.info(f"Fetched holdings for {len(data)} politicians from Quiver")
        return holdings_by_name

    except Exception as e:
        logger.error(f"Error fetching Quiver holdings: {e}")
        return _cache if _cache else {}


def get_net_worth_from_quiver(name: str) -> Optional[Dict[str, Any]]:
    """
    Get net worth estimate for a politician from Quiver holdings data.

    Args:
        name: Politician name

    Returns:
        Dict with stock_total, holdings, etc. or None if not found
    """
    holdings = fetch_all_holdings()
    if not holdings:
        return None

    normalized = _normalize_name(name)

    # Try exact match
    if normalized in holdings:
        return holdings[normalized]

    # Try last name match
    parts = normalized.split()
    if parts:
        last_name = parts[-1]
        if last_name in holdings:
            return holdings[last_name]

        # Try first + last name combination
        if len(parts) >= 2:
            first_last = f"{parts[0]} {parts[-1]}"
            for key, data in holdings.items():
                if first_last in key or key in first_last:
                    return data

    return None


def get_net_worth(name: str) -> Dict[str, Any]:
    """
    Get estimated net worth for a member of Congress.

    Combines Quiver stock holdings data with fallback estimates for
    non-stock wealth (real estate, businesses, etc.)

    Args:
        name: Name of the official

    Returns:
        Dict with keys: min, max, midpoint, display, year, source, stock_holdings
    """
    # Try Quiver first
    quiver_data = get_net_worth_from_quiver(name)

    if quiver_data and quiver_data.get('stock_total', 0) != 0:
        stock_total = quiver_data['stock_total']

        # Stock holdings are just part of net worth
        # Estimate total net worth as 1.5-3x stock holdings
        # (accounting for real estate, cash, other assets)
        if stock_total > 0:
            min_val = int(stock_total)
            max_val = int(stock_total * 2.5)
        else:
            # Negative could mean short positions or data quirk
            min_val = 1_000_000
            max_val = 5_000_000

        midpoint = (min_val + max_val) // 2

        return {
            'min': min_val,
            'max': max_val,
            'midpoint': midpoint,
            'display': _format_range(min_val, max_val),
            'year': datetime.now().year,
            'source': 'quiver',
            'stock_holdings': stock_total,
            'num_positions': quiver_data.get('num_positions', 0),
            'is_estimate': False
        }

    # Fall back to hardcoded estimates
    from justdata.apps.electwatch.services.net_worth_client import get_net_worth as get_hardcoded_net_worth
    fallback = get_hardcoded_net_worth(name)
    fallback['source'] = 'estimate'
    return fallback


def _format_range(min_val: int, max_val: int) -> str:
    """Format net worth range for display."""
    def fmt(val):
        if val >= 1_000_000_000:
            return f"${val / 1_000_000_000:.1f}B"
        elif val >= 1_000_000:
            return f"${val / 1_000_000:.0f}M"
        elif val >= 1_000:
            return f"${val / 1_000:.0f}K"
        return f"${val:,.0f}"

    return f"{fmt(min_val)}-{fmt(max_val)}"


def get_wealth_tier(net_worth_midpoint: float) -> Tuple[str, str]:
    """Get wealth tier classification."""
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


# Quick test
if __name__ == '__main__':
    import sys

    # Test with a few names
    test_names = [
        'Dave McCormick',
        'Nancy Pelosi',
        'Josh Gottheimer',
        'French Hill',
        'Marjorie Taylor Greene'
    ]

    print("Testing Quiver-based net worth lookup:\n")

    for name in test_names:
        result = get_net_worth(name)
        tier_code, tier_display = get_wealth_tier(result['midpoint'])

        print(f"{name}:")
        print(f"  Net Worth: {result['display']}")
        print(f"  Source: {result['source']}")
        if result.get('stock_holdings'):
            print(f"  Stock Holdings: ${result['stock_holdings']:,.0f}")
            print(f"  Positions: {result.get('num_positions', 0)}")
        print(f"  Tier: {tier_display}")
        print()
