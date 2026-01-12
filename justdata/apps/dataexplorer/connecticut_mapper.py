#!/usr/bin/env python3
"""
Connecticut Planning Region to County Code Mapper

Maps 2024 Connecticut planning region codes (09110-09190) back to legacy county codes (09001-09015)
for consistency with 2022-2023 data structure.
"""

# Mapping from planning region codes to legacy county codes
# Based on primary county for each planning region
# Note: Some planning regions span multiple counties, but we map to the primary county
# for aggregated data consistency
PLANNING_REGION_TO_COUNTY = {
    '09110': '09003',  # Capitol Planning Region → Hartford County
    '09120': '09001',  # Greater Bridgeport Planning Region → Fairfield County
    '09130': '09007',  # Lower Connecticut River Valley Planning Region → Middlesex County (primary)
    '09140': '09009',  # Naugatuck Valley Planning Region → New Haven County (primary)
    '09150': '09013',  # Northeastern Connecticut Planning Region → Tolland County (primary)
    '09160': '09005',  # Northwest Hills Planning Region → Litchfield County
    '09170': '09009',  # South Central Connecticut Planning Region → New Haven County (primary)
    '09180': '09011',  # Southeastern Connecticut Planning Region → New London County
    '09190': '09001',  # Western Connecticut Planning Region → Fairfield County (primary)
}

# Legacy county codes (for reference)
LEGACY_COUNTY_CODES = {
    '09001': 'Fairfield County',
    '09003': 'Hartford County',
    '09005': 'Litchfield County',
    '09007': 'Middlesex County',
    '09009': 'New Haven County',
    '09011': 'New London County',
    '09013': 'Tolland County',
    '09015': 'Windham County',
}


def normalize_connecticut_county_code(county_code: str) -> str:
    """
    Normalize Connecticut county code from planning region (2024) to legacy county code.
    
    Args:
        county_code: County code from HMDA data (may be legacy or planning region)
    
    Returns:
        Normalized county code (legacy format)
    """
    county_code_str = str(county_code).strip().zfill(5)
    
    # If it's already a legacy county code (09001-09015), return as-is
    if county_code_str in LEGACY_COUNTY_CODES:
        return county_code_str
    
    # If it's a planning region code (09110-09190), map to legacy county
    if county_code_str in PLANNING_REGION_TO_COUNTY:
        return PLANNING_REGION_TO_COUNTY[county_code_str]
    
    # If it's not a Connecticut code (doesn't start with 09), return as-is
    if not county_code_str.startswith('09'):
        return county_code_str
    
    # Unknown Connecticut code, return as-is (shouldn't happen)
    return county_code_str


def get_connecticut_normalization_sql(column_name: str = 'h.county_code') -> str:
    """
    Generate SQL CASE statement to normalize Connecticut county codes in queries.
    
    Args:
        column_name: Name of the county_code column (default: 'h.county_code')
    
    Returns:
        SQL CASE statement string
    """
    # Build CASE statement for planning region → county mapping
    case_parts = []
    
    # Add mapping for each planning region
    for planning_region, county_code in PLANNING_REGION_TO_COUNTY.items():
        case_parts.append(f"WHEN CAST({column_name} AS STRING) = '{planning_region}' THEN '{county_code}'")
    
    # Build the full CASE statement
    sql = f"""
    CASE 
        -- Map planning region codes (2024) to legacy county codes
        {' '.join(case_parts)}
        -- Keep legacy county codes as-is
        WHEN CAST({column_name} AS STRING) IN ('09001', '09003', '09005', '09007', '09009', '09011', '09013', '09015') 
            THEN CAST({column_name} AS STRING)
        -- Keep non-Connecticut codes as-is
        ELSE CAST({column_name} AS STRING)
    END
    """
    
    return sql.strip()

