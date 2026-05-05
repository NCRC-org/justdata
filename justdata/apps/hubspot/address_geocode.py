"""
Geocode HubSpot company addresses for BigQuery sync.

Strategy:
1. US Census Bureau oneline geocoder (no API key; US addresses).
2. If no match, try Census again with city + state + ZIP only (postal-level).
3. If still no match or non-US, Nominatim (OpenStreetMap) with required rate limit.

Coordinates: latitude, longitude (WGS84).
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

CENSUS_ONELINE = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
NOMINATIM = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "JustData-HubSpotSync/1.0 (NCRC; contact: https://justdata.org)"

# HubSpot / US postal code patterns
ZIP_US_RE = re.compile(r"^\d{5}(-\d{4})?$")


def _strip(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


def _is_probably_us(props: Dict[str, Any]) -> bool:
    country = (_strip(props.get("country")) or "").lower()
    if country in ("us", "usa", "united states", "united states of america", ""):
        z = _strip(props.get("zip"))
        if z and ZIP_US_RE.match(z.split()[0]):
            return True
        if _strip(props.get("state")) and country in ("", "us", "usa", "united states"):
            return True
    return country in ("us", "usa", "united states", "united states of america")


def _build_full_address_line(props: Dict[str, Any]) -> Optional[str]:
    """Single line for Census / Nominatim: street, city, state zip, country."""
    parts = []
    a1 = _strip(props.get("address"))
    a2 = _strip(props.get("address2"))
    city = _strip(props.get("city"))
    st = _strip(props.get("state"))
    z = _strip(props.get("zip"))
    country = _strip(props.get("country")) or "USA"

    if a1:
        line = a1
        if a2:
            line = f"{line}, {a2}"
        if city:
            line = f"{line}, {city}"
        if st:
            line = f"{line}, {st}"
        if z:
            line = f"{line} {z}"
        if country and country.upper() not in ("US", "USA"):
            line = f"{line}, {country}"
        return line

    if city and st and z:
        return f"{city}, {st} {z}, {country}"
    if city and st:
        return f"{city}, {st}, {country}"
    return None


def _build_postal_fallback_line(props: Dict[str, Any]) -> Optional[str]:
    """When street match fails: city + state + ZIP (approximate centroid / area)."""
    city = _strip(props.get("city"))
    st = _strip(props.get("state"))
    z = _strip(props.get("zip"))
    country = _strip(props.get("country")) or "USA"
    if z and city and st:
        return f"{city}, {st} {z}, {country}"
    if z and st:
        return f"{st} {z}, {country}"
    if z:
        return f"{z}, {country}"
    return None


def _parse_census_coords(payload: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    matches = payload.get("result", {}).get("addressMatches") or []
    if not matches:
        return None
    coords = matches[0].get("coordinates")
    if not coords or not isinstance(coords, dict):
        return None
    x = coords.get("x")
    y = coords.get("y")
    if x is None or y is None:
        return None
    return (float(y), float(x))  # lat, lng (Census: x=lon, y=lat)


class CompanyAddressGeocoder:
    """
    Geocode with in-run cache; reuse one httpx client.
    Census calls: short delay between requests.
    Nominatim: >= 1s between requests (usage policy).
    """

    def __init__(self, client: httpx.Client) -> None:
        self._client = client
        self._cache: Dict[str, Tuple[Optional[float], Optional[float]]] = {}
        self._last_census = 0.0
        self._last_nominatim = 0.0
        self._census_delay = 0.06
        self._nominatim_delay = 1.05

    def _census_throttle(self) -> None:
        elapsed = time.monotonic() - self._last_census
        if elapsed < self._census_delay:
            time.sleep(self._census_delay - elapsed)
        self._last_census = time.monotonic()

    def _nominatim_throttle(self) -> None:
        elapsed = time.monotonic() - self._last_nominatim
        if elapsed < self._nominatim_delay:
            time.sleep(self._nominatim_delay - elapsed)
        self._last_nominatim = time.monotonic()

    def _census_oneline(self, line: str) -> Optional[Tuple[float, float]]:
        self._census_throttle()
        try:
            r = self._client.get(
                CENSUS_ONELINE,
                params={
                    "address": line,
                    "benchmark": "Public_AR_Current",
                    "format": "json",
                },
                timeout=30.0,
            )
            r.raise_for_status()
            return _parse_census_coords(r.json())
        except Exception as e:
            logger.debug("Census geocode failed for %r: %s", line[:120], e)
            return None

    def _nominatim(self, q: str) -> Optional[Tuple[float, float]]:
        self._nominatim_throttle()
        try:
            r = self._client.get(
                NOMINATIM,
                params={"q": q, "format": "json", "limit": 1},
                headers={"User-Agent": USER_AGENT},
                timeout=30.0,
            )
            r.raise_for_status()
            data = r.json()
            if not data:
                return None
            lat = float(data[0]["lat"])
            lng = float(data[0]["lon"])
            return (lat, lng)
        except Exception as e:
            logger.debug("Nominatim failed for %r: %s", q[:120], e)
            return None

    def geocode(self, props: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
        """
        Return (latitude, longitude) or (None, None) if nothing geocodes.
        """
        cache_key = "|".join(
            [
                _strip(props.get("address")) or "",
                _strip(props.get("address2")) or "",
                _strip(props.get("city")) or "",
                _strip(props.get("state")) or "",
                _strip(props.get("zip")) or "",
                _strip(props.get("country")) or "",
            ]
        ).lower()
        if cache_key in self._cache:
            lat, lng = self._cache[cache_key]
            return lat, lng

        if not any(
            _strip(props.get(k))
            for k in ("address", "address2", "city", "state", "zip")
        ):
            self._cache[cache_key] = (None, None)
            return (None, None)

        lat: Optional[float] = None
        lng: Optional[float] = None

        full = _build_full_address_line(props)
        postal_line = _build_postal_fallback_line(props)

        if full:
            if _is_probably_us(props):
                coords = self._census_oneline(full)
                if coords:
                    lat, lng = coords
            if lat is None:
                coords = self._nominatim(full)
                if coords:
                    lat, lng = coords

        # Postal-level when street missing or full geocode failed
        if lat is None and postal_line:
            if not full or postal_line.strip().lower() != full.strip().lower():
                if _is_probably_us(props):
                    coords = self._census_oneline(postal_line)
                    if coords:
                        lat, lng = coords
                if lat is None:
                    coords = self._nominatim(postal_line)
                    if coords:
                        lat, lng = coords

        # Last resort: US ZIP + state (Census)
        if lat is None and _is_probably_us(props):
            z = _strip(props.get("zip"))
            st = _strip(props.get("state"))
            if z:
                z5 = z.split()[0]
                if ZIP_US_RE.match(z5) and st:
                    line = f"{z5} {st} USA"
                    coords = self._census_oneline(line)
                    if coords:
                        lat, lng = coords

        self._cache[cache_key] = (lat, lng)
        return lat, lng
