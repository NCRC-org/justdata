"""
Process Census Bureau Gazetteer files to create clean centroid CSV files.

Input files (from Census Bureau):
- 2024_Gaz_counties_national.txt - County centroids
- 2024_Gaz_cbsa_national.txt - CBSA (metro/micro area) centroids

Output files (for BigQuery upload):
- county_centroids_2024.csv
- cbsa_centroids_2024.csv
"""

import pandas as pd
import re
from pathlib import Path

# File paths
DESKTOP = Path(r"C:\Users\edite\OneDrive - NCRC\Desktop")
OUTPUT_DIR = Path(r"C:\Users\edite\OneDrive - NCRC\Code\JustData\justdata\apps\analytics\demo_data")

COUNTY_FILE = DESKTOP / "2024_Gaz_counties_national.txt"
CBSA_FILE = DESKTOP / "2024_Gaz_cbsa_national.txt"


def process_counties():
    """Process county Gazetteer file."""
    print("Processing county centroids...")

    # Read tab-delimited file
    df = pd.read_csv(COUNTY_FILE, sep='\t', encoding='latin-1')

    # Strip whitespace from column names
    df.columns = df.columns.str.strip()

    # Select and rename columns
    counties = df[['USPS', 'GEOID', 'NAME', 'INTPTLAT', 'INTPTLONG']].copy()
    counties.columns = ['state_code', 'county_fips', 'county_name', 'latitude', 'longitude']

    # Ensure county_fips is string with leading zeros (5 digits)
    counties['county_fips'] = counties['county_fips'].astype(str).str.zfill(5)

    # Create normalized name for matching (lowercase, trimmed)
    counties['county_name_normalized'] = counties['county_name'].str.lower().str.strip()

    # Also create version without "County" suffix for flexible matching
    counties['county_name_base'] = counties['county_name'].apply(
        lambda x: re.sub(r'\s+(County|Parish|Borough|Municipality|Census Area|city)$', '', x, flags=re.IGNORECASE)
    )
    counties['county_name_base_normalized'] = counties['county_name_base'].str.lower().str.strip()

    # Validate coordinates
    valid_counties = counties[
        (counties['latitude'].notna()) &
        (counties['longitude'].notna()) &
        (counties['latitude'].abs() <= 90) &
        (counties['longitude'].abs() <= 180)
    ].copy()

    print(f"  Total counties: {len(df)}")
    print(f"  Valid counties: {len(valid_counties)}")

    # Show sample of Maryland counties for verification
    md_counties = valid_counties[valid_counties['state_code'] == 'MD']
    print(f"\n  Maryland counties ({len(md_counties)}):")
    for _, row in md_counties.head(10).iterrows():
        print(f"    {row['county_name']}: ({row['latitude']}, {row['longitude']})")

    # Check for Baltimore city specifically
    baltimore = valid_counties[valid_counties['county_name'].str.contains('Baltimore', case=False)]
    print(f"\n  Baltimore entries:")
    for _, row in baltimore.iterrows():
        print(f"    {row['county_name']}, {row['state_code']}: ({row['latitude']}, {row['longitude']})")

    # Save to CSV
    output_file = OUTPUT_DIR / "county_centroids_2024.csv"
    valid_counties.to_csv(output_file, index=False)
    print(f"\n  Saved to: {output_file}")

    return valid_counties


def process_cbsas():
    """Process CBSA Gazetteer file."""
    print("\nProcessing CBSA centroids...")

    # Read tab-delimited file
    df = pd.read_csv(CBSA_FILE, sep='\t', encoding='latin-1')

    # Strip whitespace from column names
    df.columns = df.columns.str.strip()

    # Select and rename columns
    cbsas = df[['GEOID', 'NAME', 'CBSA_TYPE', 'INTPTLAT', 'INTPTLONG']].copy()
    cbsas.columns = ['cbsa_code', 'cbsa_name', 'cbsa_type', 'latitude', 'longitude']

    # Convert cbsa_code to string
    cbsas['cbsa_code'] = cbsas['cbsa_code'].astype(str)

    # Extract principal city (first city before comma)
    cbsas['principal_city'] = cbsas['cbsa_name'].apply(
        lambda x: re.match(r'^([^,]+)', x).group(1) if re.match(r'^([^,]+)', x) else x
    )

    # Extract states from CBSA name (after the cities, before "Metro/Micro Area")
    def extract_states(name):
        # Pattern: "City1-City2, ST1-ST2 Metro Area" or "City, ST Metro Area"
        match = re.search(r',\s*([A-Z]{2}(?:-[A-Z]{2})*)\s+(?:Metro|Micro)', name)
        if match:
            return match.group(1)
        return None

    cbsas['states'] = cbsas['cbsa_name'].apply(extract_states)

    # Determine metro vs micro
    cbsas['is_metro'] = cbsas['cbsa_type'] == 1

    # Create normalized name for matching
    cbsas['cbsa_name_normalized'] = cbsas['cbsa_name'].str.lower().str.strip()

    # Validate coordinates
    valid_cbsas = cbsas[
        (cbsas['latitude'].notna()) &
        (cbsas['longitude'].notna()) &
        (cbsas['latitude'].abs() <= 90) &
        (cbsas['longitude'].abs() <= 180)
    ].copy()

    print(f"  Total CBSAs: {len(df)}")
    print(f"  Valid CBSAs: {len(valid_cbsas)}")
    print(f"  Metro areas: {len(valid_cbsas[valid_cbsas['is_metro']])}")
    print(f"  Micro areas: {len(valid_cbsas[~valid_cbsas['is_metro']])}")

    # Show key metro areas for verification
    key_cbsas = ['47900', '31080', '35620', '12060', '16980']  # DC, LA, NYC, Atlanta, Chicago
    print(f"\n  Key metro areas:")
    for code in key_cbsas:
        match = valid_cbsas[valid_cbsas['cbsa_code'] == code]
        if len(match) > 0:
            row = match.iloc[0]
            print(f"    {row['cbsa_code']} - {row['cbsa_name']}: ({row['latitude']}, {row['longitude']})")

    # Save to CSV
    output_file = OUTPUT_DIR / "cbsa_centroids_2024.csv"
    valid_cbsas.to_csv(output_file, index=False)
    print(f"\n  Saved to: {output_file}")

    return valid_cbsas


if __name__ == "__main__":
    print("=" * 60)
    print("Census Bureau Gazetteer Processing")
    print("=" * 60)

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Process both files
    counties = process_counties()
    cbsas = process_cbsas()

    print("\n" + "=" * 60)
    print("Processing complete!")
    print("=" * 60)
    print(f"\nOutput files ready for BigQuery upload:")
    print(f"  1. {OUTPUT_DIR / 'county_centroids_2024.csv'}")
    print(f"  2. {OUTPUT_DIR / 'cbsa_centroids_2024.csv'}")
    print("\nNext steps for Jay:")
    print("  1. Upload CSV files to BigQuery using bq load")
    print("  2. Create final tables with proper typing")
    print("  3. Verify table permissions")
