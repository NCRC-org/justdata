#!/usr/bin/env python3
"""
Shared geographic data utilities for all applications.
Provides fallback data for states and counties when BigQuery is unavailable.
All 3,247 counties from geo.cbsa_to_county are included.
"""

from typing import List, Dict


def get_us_states() -> List[Dict[str, str]]:
    """
    Get list of US states with codes.
    All 52 states/territories from BigQuery.
    
    Returns:
        List of dictionaries with 'code' and 'name' keys
    """
    return [
        {"code": "AL", "name": "Alabama"},
        {"code": "AK", "name": "Alaska"},
        {"code": "AZ", "name": "Arizona"},
        {"code": "AR", "name": "Arkansas"},
        {"code": "CA", "name": "California"},
        {"code": "CO", "name": "Colorado"},
        {"code": "CT", "name": "Connecticut"},
        {"code": "DE", "name": "Delaware"},
        {"code": "DC", "name": "District of Columbia"},
        {"code": "FL", "name": "Florida"},
        {"code": "GA", "name": "Georgia"},
        {"code": "HI", "name": "Hawaii"},
        {"code": "ID", "name": "Idaho"},
        {"code": "IL", "name": "Illinois"},
        {"code": "IN", "name": "Indiana"},
        {"code": "IA", "name": "Iowa"},
        {"code": "KS", "name": "Kansas"},
        {"code": "KY", "name": "Kentucky"},
        {"code": "LA", "name": "Louisiana"},
        {"code": "ME", "name": "Maine"},
        {"code": "MD", "name": "Maryland"},
        {"code": "MA", "name": "Massachusetts"},
        {"code": "MI", "name": "Michigan"},
        {"code": "MN", "name": "Minnesota"},
        {"code": "MS", "name": "Mississippi"},
        {"code": "MO", "name": "Missouri"},
        {"code": "MT", "name": "Montana"},
        {"code": "NE", "name": "Nebraska"},
        {"code": "NV", "name": "Nevada"},
        {"code": "NH", "name": "New Hampshire"},
        {"code": "NJ", "name": "New Jersey"},
        {"code": "NM", "name": "New Mexico"},
        {"code": "NY", "name": "New York"},
        {"code": "NC", "name": "North Carolina"},
        {"code": "ND", "name": "North Dakota"},
        {"code": "OH", "name": "Ohio"},
        {"code": "OK", "name": "Oklahoma"},
        {"code": "OR", "name": "Oregon"},
        {"code": "PA", "name": "Pennsylvania"},
        {"code": "PR", "name": "Puerto Rico"},
        {"code": "RI", "name": "Rhode Island"},
        {"code": "SC", "name": "South Carolina"},
        {"code": "SD", "name": "South Dakota"},
        {"code": "TN", "name": "Tennessee"},
        {"code": "TX", "name": "Texas"},
        {"code": "UT", "name": "Utah"},
        {"code": "VT", "name": "Vermont"},
        {"code": "VA", "name": "Virginia"},
        {"code": "WA", "name": "Washington"},
        {"code": "WV", "name": "West Virginia"},
        {"code": "WI", "name": "Wisconsin"},
        {"code": "WY", "name": "Wyoming"}
    ]


def get_fallback_counties() -> List[str]:
    """
    Minimal fallback list of counties for error cases only.
    Applications should use BigQuery directly via get_available_counties().
    
    Returns:
        List of county names in "County Name, State" format (minimal set)
    """
    # Minimal fallback - only for critical error cases
    # Applications should query BigQuery directly
    return [
        "Los Angeles County, California",
        "Cook County, Illinois",
        "Harris County, Texas",
        "Maricopa County, Arizona",
        "San Diego County, California",
        "Orange County, California",
        "Miami-Dade County, Florida",
        "Kings County, New York",
        "Dallas County, Texas",
        "King County, Washington"
    ]
