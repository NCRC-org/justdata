#!/usr/bin/env python3
"""
HUD Low-Mod Summary Data processor.
Processes HUD Excel files and provides county-level household income distributions.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
import json

logger = logging.getLogger(__name__)

# Data directory for HUD files
HUD_DATA_DIR = Path(__file__).parent.parent.parent / 'data' / 'hud'
HUD_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Cache file for processed county data
HUD_CACHE_FILE = HUD_DATA_DIR / 'hud_county_data.json'


def process_hud_excel_file(excel_path: Path) -> Dict[str, Any]:
    """
    Process HUD Low-Mod Summary Data Excel file.
    
    Args:
        excel_path: Path to the HUD Excel file
    
    Returns:
        Dictionary mapping GEOID5 to county-level income distribution data
    """
    logger.info(f"Processing HUD Excel file: {excel_path}")
    
    # Read the Excel file
    df = pd.read_excel(excel_path)
    logger.info(f"Loaded {len(df):,} rows from HUD file")
    
    # TODO: Identify column names from actual file structure
    # These will need to be updated based on the actual column names in the file
    # Common patterns:
    # - State FIPS: 'State', 'StateFIPS', 'ST', 'STATE_FIPS'
    # - County FIPS: 'County', 'CountyFIPS', 'CO', 'COUNTY_FIPS'
    # - Population: 'TotalPop', 'Population', 'POP', 'Total Population'
    # - Income brackets: Various patterns for low/moderate/middle/upper income
    
    # Placeholder - will be updated after examining the file structure
    state_col = None
    county_col = None
    pop_col = None
    income_cols = {}
    
    # Try to identify columns
    for col in df.columns:
        col_lower = str(col).lower()
        if 'state' in col_lower and ('fips' in col_lower or col_lower in ['state', 'st']):
            if state_col is None:
                state_col = col
        if 'county' in col_lower and ('fips' in col_lower or col_lower in ['county', 'co']):
            if county_col is None:
                county_col = col
    
    if state_col is None or county_col is None:
        logger.error("Could not identify state/county columns. Please check file structure.")
        return {}
    
    logger.info(f"Using state column: {state_col}, county column: {county_col}")
    
    # Create GEOID5 from state and county FIPS
    df['geoid5'] = df[state_col].astype(str).str.zfill(2) + df[county_col].astype(str).str.zfill(3)
    
    # Group by GEOID5 and sum all numeric columns (aggregating sub-county areas)
    numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
    if 'geoid5' in numeric_cols:
        numeric_cols.remove('geoid5')
    
    county_totals = df.groupby('geoid5')[numeric_cols].sum().reset_index()
    
    logger.info(f"Aggregated to {len(county_totals):,} counties")
    
    # TODO: Calculate income distribution percentages
    # This will depend on the actual column names for income brackets
    
    # Save processed data
    result = {}
    for _, row in county_totals.iterrows():
        geoid5 = str(row['geoid5']).zfill(5)
        # TODO: Extract income distribution from row data
        result[geoid5] = {
            'geoid5': geoid5,
            'household_income_distribution': {},  # Will be populated
            'total_households': 0,  # Will be populated
        }
    
    # Save to cache
    with open(HUD_CACHE_FILE, 'w') as f:
        json.dump(result, f, indent=2)
    
    logger.info(f"Saved processed data to {HUD_CACHE_FILE}")
    
    return result


def get_hud_data_for_geoids(geoids: List[str]) -> Dict[str, Any]:
    """
    Get HUD Low-Mod data for a list of GEOID5 codes.
    
    Args:
        geoids: List of 5-digit GEOID5 codes
    
    Returns:
        Dictionary with household income distribution data
    """
    # Load from cache if available
    if HUD_CACHE_FILE.exists():
        try:
            with open(HUD_CACHE_FILE, 'r') as f:
                cached_data = json.load(f)
            
            # Aggregate data for requested geoids
            total_households = 0
            income_counts = {
                'Low Income': 0,
                'Moderate Income': 0,
                'Middle Income': 0,
                'Upper Income': 0
            }
            
            for geoid in geoids:
                geoid5 = str(geoid).zfill(5)
                if geoid5 in cached_data:
                    county_data = cached_data[geoid5]
                    # TODO: Aggregate income data
                    pass
            
            # Calculate percentages
            distribution = {}
            if total_households > 0:
                for category, count in income_counts.items():
                    distribution[category] = round((count / total_households) * 100, 1)
            
            return {
                'household_income_distribution': distribution,
                'total_households': total_households,
                'data_source': 'HUD Low-Mod Summary Data'
            }
        except Exception as e:
            logger.error(f"Error loading HUD cache: {e}")
    
    return {
        'household_income_distribution': {},
        'total_households': 0,
        'data_source': None
    }


def load_hud_file_if_needed() -> Optional[Path]:
    """
    Check if HUD file exists in data directory, copy from source if needed.
    
    Returns:
        Path to HUD file in data directory, or None if not found
    """
    # Check for HUD file in data directory
    hud_file = HUD_DATA_DIR / 'ACS-2020-Low-Mod-Local-Gov-All.xlsx'
    
    if hud_file.exists():
        logger.info(f"HUD file found in data directory: {hud_file}")
        return hud_file
    
    # Try to find source file
    source_paths = [
        Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\ACS-2020-Low-Mod-Local-Gov-All.xlsx"),
        Path.home() / "Desktop" / "ACS-2020-Low-Mod-Local-Gov-All.xlsx",
    ]
    
    for source_path in source_paths:
        if source_path.exists():
            logger.info(f"Copying HUD file from {source_path} to {hud_file}")
            import shutil
            shutil.copy2(source_path, hud_file)
            return hud_file
    
    logger.warning("HUD file not found. Please ensure it's available.")
    return None

