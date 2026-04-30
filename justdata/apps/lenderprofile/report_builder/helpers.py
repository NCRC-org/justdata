"""Shared helpers for the lenderprofile report builder.

Formatting (currency / truncation / growth / recency) plus the text
extraction utilities used by multiple sections.
"""
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


def _format_currency(value: Optional[float], suffix: str = '') -> str:
    """Format currency value with appropriate suffix."""
    if value is None or value == 0:
        return '--'

    if value >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.2f}T{suffix}"
    elif value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B{suffix}"
    elif value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M{suffix}"
    elif value >= 1_000:
        return f"${value / 1_000:.1f}K{suffix}"
    else:
        return f"${value:,.0f}{suffix}"


def _truncate_text(text: Optional[str], max_length: int) -> str:
    """Truncate text to max length."""
    if not text:
        return ''
    if len(text) <= max_length:
        return text
    return text[:max_length] + '...'


def _calculate_growth(current: float, previous: float) -> Optional[float]:
    """Calculate growth rate."""
    if not previous or previous == 0:
        return None
    return ((current - previous) / previous) * 100


def _is_recent(date_str: Optional[str], years: int = 3) -> bool:
    """Check if date is within recent years."""
    if not date_str:
        return False
    try:
        date = datetime.strptime(date_str[:10], '%Y-%m-%d')
        cutoff = datetime.now() - timedelta(days=years * 365)
        return date >= cutoff
    except:
        return False


def _extract_business_segments(text: str) -> List[Dict[str, str]]:
    """Extract business segment information from Item 1."""
    if not text:
        return []

    segments = []
    # Look for common segment patterns
    patterns = [
        r'(?:commercial|retail|consumer|corporate|investment|wealth|mortgage)\s*banking',
        r'(?:commercial|residential)\s*(?:real estate|lending)',
        r'(?:treasury|capital markets|trading)',
        r'(?:insurance|wealth management|asset management)'
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if match.strip() not in [s.get('name') for s in segments]:
                segments.append({'name': match.strip().title()})

    return segments[:10]


def _extract_strategic_priorities(text: str) -> List[str]:
    """Extract strategic priorities from MD&A."""
    if not text:
        return []

    priorities = []
    # Look for priority indicators
    indicators = ['focus on', 'priority', 'key initiative', 'strategic', 'invest in', 'expand']

    sentences = text.split('.')
    for sentence in sentences:
        if any(ind in sentence.lower() for ind in indicators):
            clean = sentence.strip()
            if 10 < len(clean) < 300:
                priorities.append(clean)

    return priorities[:5]


def _extract_growth_areas(text: str) -> List[str]:
    """Extract growth areas from MD&A."""
    if not text:
        return []

    growth = []
    indicators = ['growth', 'expand', 'increase', 'opportunity', 'invest']

    sentences = text.split('.')
    for sentence in sentences:
        if any(ind in sentence.lower() for ind in indicators):
            if 'expect' in sentence.lower() or 'will' in sentence.lower() or 'plan' in sentence.lower():
                clean = sentence.strip()
                if 10 < len(clean) < 300:
                    growth.append(clean)

    return growth[:5]


def _extract_contraction_areas(text: str) -> List[str]:
    """Extract contraction/exit areas from MD&A."""
    if not text:
        return []

    contraction = []
    indicators = ['exit', 'reduce', 'decline', 'close', 'divest', 'wind down']

    sentences = text.split('.')
    for sentence in sentences:
        if any(ind in sentence.lower() for ind in indicators):
            clean = sentence.strip()
            if 10 < len(clean) < 300:
                contraction.append(clean)

    return contraction[:5]


def _categorize_risks(text: str) -> Dict[str, int]:
    """Categorize risk factors by type."""
    if not text:
        return {}

    categories = {
        'credit_risk': ['credit', 'loan', 'default', 'non-performing'],
        'market_risk': ['interest rate', 'market', 'trading', 'investment'],
        'operational_risk': ['operational', 'cyber', 'technology', 'systems'],
        'regulatory_risk': ['regulatory', 'compliance', 'legislation', 'law'],
        'competitive_risk': ['competition', 'competitor', 'market share'],
        'economic_risk': ['economic', 'recession', 'unemployment', 'housing']
    }

    counts = {}
    text_lower = text.lower()

    for category, keywords in categories.items():
        count = sum(1 for kw in keywords if kw in text_lower)
        if count > 0:
            counts[category] = count

    return counts


