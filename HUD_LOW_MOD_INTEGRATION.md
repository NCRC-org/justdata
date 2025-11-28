# HUD Low-Mod Summary Data Integration

## Overview
The current implementation uses Census B19001 table which approximates household income distribution using bracket upper bounds. However, this is not sufficient for accurately measuring the share of households at or below 80% of AMI.

HUD provides the **Low and Moderate Income Summary Data (LMISD)** which uses HUD's official methodology to calculate accurate percentages.

## Data Source
- **URL**: https://www.hudexchange.info/programs/acs-low-mod-summary-data/acs-low-mod-summary-data-local-government/
- **Format**: Excel spreadsheets organized by state
- **Geography Levels**: 
  - PLACE (local governments and Census Designated Places)
  - COUSUB/MCD (sections/subsections of local governments within each county)
  - COUNTY (county-wide data)

## Implementation Plan

### Option 1: Download and Cache Excel Files
1. Download HUD Excel files for all states
2. Parse Excel files to extract county-level data
3. Cache parsed data in BigQuery or local JSON/Parquet files
4. Match GEOID5 codes to HUD data

### Option 2: Use HUD API (if available)
- Check if HUD provides an API endpoint
- If yes, make direct API calls

### Option 3: Pre-process and Store in BigQuery
1. Download HUD data once
2. Process and load into BigQuery table
3. Query from BigQuery when needed

## Required Data Fields
From HUD's Low-Mod Summary Data, we need:
- GEOID5 (county FIPS code)
- Percentage of households at or below 80% of AMI
- Percentage breakdown by income categories (if available):
  - Low Income (≤50% AMI)
  - Moderate Income (50-80% AMI)
  - Middle Income (80-120% AMI)
  - Upper Income (>120% AMI)

## Next Steps
1. Download sample HUD Excel file to understand structure
2. Create parser for HUD Excel format
3. Implement caching mechanism
4. Update `get_hud_low_mod_data_for_geoids()` function
5. Test with Abilene, TX (GEOID5: 48441)

## Current Status
- Function stub created: `get_hud_low_mod_data_for_geoids()`
- Falls back to Census B19001 if HUD data unavailable
- Ready for implementation once HUD file structure is understood

