#!/usr/bin/env python3
"""
HUD Low-Mod Summary Data processor for LendSight.
Processes HUD Excel files and provides county-level income distributions.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

# Data directory for HUD files
HUD_DATA_DIR = Path(__file__).parent.parent.parent / 'data' / 'hud'
HUD_DATA_DIR.mkdir(parents=True, exist_ok=True)

# HUD file path
HUD_FILE = HUD_DATA_DIR / 'ACS-2020-Low-Mod-Local-Gov-All.xlsx'

# Cache for processed data
_hud_cache: Optional[Dict[str, Dict[str, float]]] = None


def load_hud_data() -> Dict[str, Dict[str, float]]:
    """
    Load and process HUD Low-Mod Excel file.
    
    Returns:
        Dictionary mapping GEOID5 to income distribution percentages:
        {
            'geoid5': {
                'low_income_pct': float,
                'moderate_income_pct': float,
                'middle_income_pct': float,
                'upper_income_pct': float,
                'low_mod_income_pct': float,  # Low + Moderate combined
                'total_persons': int
            }
        }
    """
    global _hud_cache
    
    if _hud_cache is not None:
        return _hud_cache
    
    if not HUD_FILE.exists():
        logger.warning(f"HUD file not found at {HUD_FILE}")
        return {}
    
    logger.info(f"Loading HUD file: {HUD_FILE}")
    df = pd.read_excel(HUD_FILE)
    
    # Create GEOID5 from STATE and COUNTY FIPS codes
    df['geoid5'] = df['STATE'].astype(str).str.zfill(2) + df['COUNTY'].astype(str).str.zfill(3)
    
    # Aggregate by county (sum sub-county areas)
    county_cols = ['Total Persons', 'Low Income', 'Moderate Income', 'Middle Income', 'Upper Income']
    county_totals = df.groupby('geoid5')[county_cols].sum().reset_index()
    
    # Calculate percentages for each county
    _hud_cache = {}
    for _, row in county_totals.iterrows():
        geoid5 = str(row['geoid5']).zfill(5)
        total_persons = row['Total Persons']
        
        if total_persons > 0:
            _hud_cache[geoid5] = {
                'low_income_pct': (row['Low Income'] / total_persons) * 100,
                'moderate_income_pct': (row['Moderate Income'] / total_persons) * 100,
                'middle_income_pct': (row['Middle Income'] / total_persons) * 100,
                'upper_income_pct': (row['Upper Income'] / total_persons) * 100,
                'low_mod_income_pct': ((row['Low Income'] + row['Moderate Income']) / total_persons) * 100,
                'total_persons': int(total_persons)
            }
        else:
            _hud_cache[geoid5] = {
                'low_income_pct': 0.0,
                'moderate_income_pct': 0.0,
                'middle_income_pct': 0.0,
                'upper_income_pct': 0.0,
                'low_mod_income_pct': 0.0,
                'total_persons': 0
            }
    
    logger.info(f"Loaded HUD data for {len(_hud_cache)} counties")
    return _hud_cache


def get_hud_data_for_counties(geoids: List[str]) -> Dict[str, Dict[str, float]]:
    """
    Get HUD income distribution data for a list of counties.
    
    Args:
        geoids: List of 5-digit GEOID5 codes
        
    Returns:
        Dictionary mapping GEOID5 to income distribution data
    """
    hud_data = load_hud_data()
    result = {}
    
    for geoid in geoids:
        geoid5 = str(geoid).zfill(5)
        if geoid5 in hud_data:
            result[geoid5] = hud_data[geoid5]
        else:
            # Return zeros if county not found
            result[geoid5] = {
                'low_income_pct': 0.0,
                'moderate_income_pct': 0.0,
                'middle_income_pct': 0.0,
                'upper_income_pct': 0.0,
                'low_mod_income_pct': 0.0,
                'total_persons': 0
            }
    
    return result


def load_hud_tract_data() -> pd.DataFrame:
    """
    Load HUD Low-Mod Excel file at tract level (not aggregated).
    
    Returns:
        DataFrame with tract-level data including:
        - geoid5: County GEOID5 code
        - tract_code: Census tract code (if available)
        - Total Persons: Population in tract
        - Low Income: Population in low income category
        - Moderate Income: Population in moderate income category
        - Middle Income: Population in middle income category
        - Upper Income: Population in upper income category
    """
    if not HUD_FILE.exists():
        logger.warning(f"HUD file not found at {HUD_FILE}")
        return pd.DataFrame()
    
    logger.info(f"Loading HUD tract-level data from: {HUD_FILE}")
    df = pd.read_excel(HUD_FILE)
    
    # Create GEOID5 from STATE and COUNTY FIPS codes
    df['geoid5'] = df['STATE'].astype(str).str.zfill(2) + df['COUNTY'].astype(str).str.zfill(3)
    
    return df


