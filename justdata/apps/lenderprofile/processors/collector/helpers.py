"""Internal helpers for the data collector."""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

def _calculate_financial_trends_deprecated(collector, financial_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    DEPRECATED: Use FinancialDataProcessor.process_fdic_financials() instead.
    This method is kept for backward compatibility but should not be used.
    """
    """Calculate 5-year financial trends."""
    if not financial_records:
        return {}
    
    # Sort by date
    sorted_records = sorted(financial_records, key=lambda x: x.get('REPDTE', ''))
    
    return {
        'years': [r.get('REPDTE', '')[:4] for r in sorted_records[-20:]],  # Last 20 quarters
        'assets': [r.get('ASSET', 0) for r in sorted_records[-20:]],
        'equity': [r.get('EQ', 0) for r in sorted_records[-20:]],
        'net_income': [r.get('NETINC', 0) for r in sorted_records[-20:]]
    }

def _summarize_branches(collector, branches: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Summarize branch network data."""
    if not branches:
        return {}
    
    return {
        'total': len(branches),
        'states': len(set(b.get('STALP') or b.get('STATE', '') for b in branches)),
        'msas': len(set(b.get('MSA', '') for b in branches if b.get('MSA')))
    }

def _is_recent(collector, date_str: str, days: int = 365) -> bool:
    """Check if date is within recent period."""
    try:
        from datetime import datetime
        date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return (datetime.now() - date.replace(tzinfo=None)).days <= days
    except:
        return False

