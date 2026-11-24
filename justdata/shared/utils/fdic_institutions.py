"""Bank headquarters from the FDIC BankFind institutions API, by RSSD.

Used only to tell apart two different banks (RSSDs) that share a name in a
report, so it asks for a handful of RSSDs at a time. Public API; FDIC_API_KEY
is sent when set. A failed lookup returns nothing for that RSSD, and the
caller falls back to showing the RSSD.
"""
import logging
import os
from typing import Dict, Iterable

import requests

log = logging.getLogger(__name__)

URL = 'https://api.fdic.gov/banks/institutions'
TIMEOUT = 6
_cache: Dict[str, str] = {}


def headquarters(rssds: Iterable[str]) -> Dict[str, str]:
    """{rssd: "City, ST"} for the RSSDs the FDIC knows."""
    wanted = sorted({str(r) for r in rssds if r and str(r) != 'nan'})
    missing = [r for r in wanted if r not in _cache]
    if missing:
        params = {'filters': 'FED_RSSD:(' + ' OR '.join(missing) + ')',
                  'fields': 'FED_RSSD,CITY,STALP', 'limit': max(10, len(missing) * 2)}
        if os.environ.get('FDIC_API_KEY'):
            params['api_key'] = os.environ['FDIC_API_KEY']
        try:
            resp = requests.get(URL, params=params, timeout=TIMEOUT)
            resp.raise_for_status()
            for item in resp.json().get('data', []):
                d = item.get('data', {})
                if d.get('FED_RSSD') and d.get('CITY') and d.get('STALP'):
                    _cache[str(d['FED_RSSD'])] = f"{d['CITY']}, {d['STALP']}"
        except Exception as exc:  # the RSSD is shown instead
            log.warning('FDIC headquarters lookup failed for %d RSSDs: %s', len(missing), exc)
    return {r: _cache[r] for r in wanted if r in _cache}
