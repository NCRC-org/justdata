#!/usr/bin/env python3
"""
Test script to verify Census data fetching for Abilene, TX (Taylor County).
Tests all three distinct datasets:
1. Household income distribution (households by their own income)
2. Tract income distribution (households by tract income status)
3. Tract minority distribution (households by tract minority status)
"""

import sys
import os
from pathlib import Path

# Add the apps directory to the path
sys.path.insert(0, str(Path(__file__).parent))

# Set up environment
os.environ.setdefault('FLASK_ENV', 'development')

# Try to load .env file
try:
    from dotenv import load_dotenv
    # Try loading from parent DREAM Analysis directory
    parent_env_path = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\DREAM Analysis\.env")
    if parent_env_path.exists():
        load_dotenv(parent_env_path, override=False)
    # Also try current directory
    load_dotenv(override=False)
except ImportError:
    pass

# Import the functions
from apps.dataexplorer.acs_utils import (
    get_household_income_distribution_for_geoids,
    get_tract_household_distributions_for_geoids
)
from apps.dataexplorer.mmct_utils import get_average_minority_percentage

# Abilene, TX is in Taylor County, Texas
# Taylor County GEOID5: 48441 (Texas = 48, Taylor County = 441)
abilene_geoid = '48441'

print("=" * 80)
print("Testing Census Data for Abilene, TX (Taylor County, GEOID5: 48441)")
print("=" * 80)
print()

# Test 1: Household Income Distribution
print("1. Testing Household Income Distribution")
print("-" * 80)
print("This should show: Share of households that are themselves low/moderate/middle/upper income")
print()
try:
    household_data = get_household_income_distribution_for_geoids([abilene_geoid])
    print(f"Total Households: {household_data.get('total_households', 0):,}")
    print(f"Metro AMI: ${household_data.get('metro_ami', 0):,.0f}" if household_data.get('metro_ami') else "Metro AMI: N/A")
    print()
    print("Household Income Distribution (% of households):")
    distribution = household_data.get('household_income_distribution', {})
    if distribution:
        for category, pct in distribution.items():
            print(f"  {category}: {pct}%")
    else:
        print("  No data available")
    print()
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    print()

# Test 2: Get average minority percentage (needed for tract distributions)
print("2. Getting Average Minority Percentage")
print("-" * 80)
try:
    avg_minority_pct = get_average_minority_percentage([abilene_geoid], [2024])
    print(f"Average Minority Percentage: {avg_minority_pct:.2f}%")
    print()
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    print()
    avg_minority_pct = None

# Test 3: Tract Income Distribution
print("3. Testing Tract Income Distribution")
print("-" * 80)
print("This should show: Share of households that live in low/moderate/middle/upper income census tracts")
print()
try:
    tract_data = get_tract_household_distributions_for_geoids([abilene_geoid], avg_minority_pct)
    
    print("Tract Income Distribution (% of households):")
    income_dist = tract_data.get('tract_income_distribution', {})
    if income_dist:
        for category, pct in income_dist.items():
            print(f"  {category} Tracts: {pct}%")
    else:
        print("  No data available")
    print()
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    print()

# Test 4: Tract Minority Distribution
print("4. Testing Tract Minority Distribution")
print("-" * 80)
print("This should show: Share of households that live in low/moderate/middle/high minority census tracts")
print()
try:
    tract_data = get_tract_household_distributions_for_geoids([abilene_geoid], avg_minority_pct)
    
    print("Tract Minority Distribution (% of households):")
    minority_dist = tract_data.get('tract_minority_distribution', {})
    if minority_dist:
        for category, pct in minority_dist.items():
            print(f"  {category} Tracts: {pct}%")
    else:
        print("  No data available")
    print()
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    print()

# Summary
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print()

household_data = get_household_income_distribution_for_geoids([abilene_geoid])
tract_data = get_tract_household_distributions_for_geoids([abilene_geoid], avg_minority_pct)

print("✓ Dataset 1 - Household Income Distribution:")
if household_data.get('household_income_distribution'):
    print("  ✓ Data available")
    for cat, pct in household_data.get('household_income_distribution', {}).items():
        print(f"    {cat}: {pct}%")
else:
    print("  ✗ No data")

print()
print("✓ Dataset 2 - Tract Income Distribution:")
if tract_data.get('tract_income_distribution'):
    print("  ✓ Data available")
    for cat, pct in tract_data.get('tract_income_distribution', {}).items():
        print(f"    {cat} Tracts: {pct}%")
else:
    print("  ✗ No data")

print()
print("✓ Dataset 3 - Tract Minority Distribution:")
if tract_data.get('tract_minority_distribution'):
    print("  ✓ Data available")
    for cat, pct in tract_data.get('tract_minority_distribution', {}).items():
        print(f"    {cat} Tracts: {pct}%")
else:
    print("  ✗ No data")

print()
print("=" * 80)

