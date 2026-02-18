#!/usr/bin/env python3
"""
Generate a national census tract GeoJSON with income + minority data baked in.

Fetches TIGERweb boundaries and Census ACS data for all US states/territories,
merges them, and outputs line-delimited GeoJSON for Mapbox Tiling Service upload.

Usage:
    python scripts/generate_census_tileset.py

Output:
    scripts/census_tracts_national.geojson.ld  (line-delimited GeoJSON)

After generation, upload to Mapbox:
    1. Install tilesets CLI: pip install mapbox-tilesets
    2. export MAPBOX_ACCESS_TOKEN=sk.eyJ...  (secret token with tilesets:write scope)
    3. tilesets upload-source jedlebi census-tracts scripts/census_tracts_national.geojson.ld
    4. tilesets create jedlebi.census-tracts --recipe scripts/census_tileset_recipe.json --name "Census Tracts"
    5. tilesets publish jedlebi.census-tracts
"""

import json
import os
import sys
import time
import requests
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Census API config
ACS_YEAR = "2022"
CENSUS_BASE_URL = f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5"
TIGERWEB_URL = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer/8/query"

# All US state/territory FIPS codes
STATE_FIPS = [
    '01', '02', '04', '05', '06', '08', '09', '10', '11', '12',
    '13', '15', '16', '17', '18', '19', '20', '21', '22', '23',
    '24', '25', '26', '27', '28', '29', '30', '31', '32', '33',
    '34', '35', '36', '37', '38', '39', '40', '41', '42', '44',
    '45', '46', '47', '48', '49', '50', '51', '53', '54', '55',
    '56',  # 50 states + DC
    '72',  # Puerto Rico
    '78',  # US Virgin Islands
    '66',  # Guam
    '60',  # American Samoa
    '69',  # Northern Mariana Islands
]

# Rate limiting
CENSUS_DELAY = 0.5  # seconds between Census API calls
TIGER_DELAY = 1.0   # seconds between TIGERweb calls (heavier)

# Invalid Census sentinel values
INVALID_VALUES = {'-888888888', '-666666666', '-999999999', 'null', 'None', ''}


def fetch_with_retry(url, params, timeout=120, retries=3, delay=5):
    """Fetch URL with retry logic."""
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp
        except (requests.RequestException, requests.Timeout) as e:
            if attempt < retries - 1:
                print(f"    Retry {attempt + 1}/{retries} after error: {e}")
                time.sleep(delay * (attempt + 1))
            else:
                raise


def fetch_state_median_income(state_fips, api_key):
    """Get state-level median family income."""
    params = {
        'get': 'NAME,B19113_001E',
        'for': f'state:{state_fips}',
        'key': api_key
    }
    resp = fetch_with_retry(CENSUS_BASE_URL, params, timeout=30)
    data = resp.json()
    if len(data) > 1 and len(data[1]) > 1:
        val = data[1][1]
        if val and val not in INVALID_VALUES:
            income = float(val)
            if income > 0:
                return income
    return None


def fetch_state_minority_pct(state_fips, api_key):
    """Get state-level minority percentage."""
    params = {
        'get': 'NAME,B01003_001E,B03002_003E',
        'for': f'state:{state_fips}',
        'key': api_key
    }
    resp = fetch_with_retry(CENSUS_BASE_URL, params, timeout=30)
    data = resp.json()
    if len(data) > 1 and len(data[1]) > 2:
        total_str = data[1][1]
        white_str = data[1][2]
        if total_str and white_str and total_str not in INVALID_VALUES and white_str not in INVALID_VALUES:
            total = float(total_str)
            white = float(white_str)
            if total > 0:
                return ((total - white) / total) * 100
    return None


def fetch_tract_income(state_fips, api_key):
    """Get tract-level median family income for a state. Returns dict keyed by GEOID."""
    params = {
        'get': 'NAME,B19113_001E,GEO_ID',
        'for': 'tract:*',
        'in': f'state:{state_fips}',
        'key': api_key
    }
    resp = fetch_with_retry(CENSUS_BASE_URL, params, timeout=60)
    data = resp.json()

    if len(data) < 2:
        return {}

    headers = data[0]
    income_idx = headers.index('B19113_001E')
    county_idx = headers.index('county')
    tract_idx = headers.index('tract')

    result = {}
    for row in data[1:]:
        county = row[county_idx]
        tract = row[tract_idx].zfill(6)
        geoid = f"{state_fips}{county}{tract}"
        val = row[income_idx]
        if val and val not in INVALID_VALUES:
            try:
                income = float(val)
                if income > 0:
                    result[geoid] = income
            except ValueError:
                pass
    return result


def fetch_tract_minority(state_fips, api_key):
    """Get tract-level minority data for a state. Returns dict keyed by GEOID."""
    params = {
        'get': 'NAME,B01003_001E,B03002_003E,GEO_ID',
        'for': 'tract:*',
        'in': f'state:{state_fips}',
        'key': api_key
    }
    resp = fetch_with_retry(CENSUS_BASE_URL, params, timeout=60)
    data = resp.json()

    if len(data) < 2:
        return {}

    headers = data[0]
    total_idx = headers.index('B01003_001E')
    white_idx = headers.index('B03002_003E')
    county_idx = headers.index('county')
    tract_idx = headers.index('tract')

    result = {}
    for row in data[1:]:
        county = row[county_idx]
        tract = row[tract_idx].zfill(6)
        geoid = f"{state_fips}{county}{tract}"
        total_str = row[total_idx]
        white_str = row[white_idx]

        if (total_str and white_str and
                total_str not in INVALID_VALUES and white_str not in INVALID_VALUES):
            try:
                total = float(total_str)
                white = float(white_str)
                if total > 0 and white >= 0:
                    minority = total - white
                    if minority >= 0:
                        result[geoid] = {
                            'total_population': total,
                            'minority_population': minority,
                            'minority_percentage': (minority / total) * 100
                        }
            except ValueError:
                pass
    return result


def fetch_tract_boundaries(state_fips, county_fips_list=None):
    """Fetch census tract GeoJSON boundaries from TIGERweb for a state.

    Falls back to per-county queries if state-level query fails (common for large states).
    county_fips_list: optional list of 3-digit county FIPS codes to query individually.
    """
    # Try state-level first
    try:
        params = {
            'where': f"STATE='{state_fips}'",
            'outFields': 'GEOID,NAME,STATE,COUNTY,TRACT',
            'f': 'geojson',
            'outSR': '4326'
        }
        resp = fetch_with_retry(TIGERWEB_URL, params, timeout=180)
        text = resp.text.strip()
        if text.startswith('{'):
            geojson = json.loads(text)
            if 'features' in geojson and len(geojson['features']) > 0:
                return geojson['features']
    except Exception as e:
        print(f"    State-level TIGERweb query failed: {e}")

    # Fallback: query per county
    if not county_fips_list:
        print(f"    No county list for per-county fallback")
        return []

    print(f"    Falling back to per-county queries ({len(county_fips_list)} counties)...")
    all_features = []
    for i, county_fips in enumerate(county_fips_list):
        try:
            params = {
                'where': f"STATE='{state_fips}' AND COUNTY='{county_fips}'",
                'outFields': 'GEOID,NAME,STATE,COUNTY,TRACT',
                'f': 'geojson',
                'outSR': '4326'
            }
            resp = fetch_with_retry(TIGERWEB_URL, params, timeout=60, retries=2)
            text = resp.text.strip()
            if text.startswith('{'):
                geojson = json.loads(text)
                if 'features' in geojson:
                    all_features.extend(geojson['features'])
            time.sleep(0.3)
        except Exception as e:
            print(f"    County {county_fips} failed: {e}")
            continue
        if (i + 1) % 20 == 0:
            print(f"    ... {i+1}/{len(county_fips_list)} counties done ({len(all_features)} tracts)")

    return all_features


def categorize_income(tract_income, state_income):
    """Categorize income relative to state median."""
    if not tract_income or not state_income or state_income <= 0:
        return 'Unknown'
    ratio = tract_income / state_income
    if ratio <= 0.50:
        return 'Low'
    elif ratio <= 0.80:
        return 'Moderate'
    elif ratio <= 1.20:
        return 'Middle'
    else:
        return 'Upper'


def main():
    api_key = os.environ.get('CENSUS_API_KEY')
    if not api_key:
        # Try loading from .env
        try:
            from dotenv import load_dotenv
            load_dotenv(project_root / '.env')
            api_key = os.environ.get('CENSUS_API_KEY')
        except ImportError:
            pass

    if not api_key:
        print("ERROR: CENSUS_API_KEY not set. Set it in environment or .env file.")
        sys.exit(1)

    output_path = project_root / 'scripts' / 'census_tracts_national.geojson.ld'

    # Support --only flag to process specific states (e.g., --only 01,06,48)
    only_states = None
    append_mode = False
    for arg in sys.argv[1:]:
        if arg.startswith('--only='):
            only_states = [s.strip() for s in arg.split('=', 1)[1].split(',')]
            append_mode = True

    states_to_process = only_states if only_states else STATE_FIPS
    file_mode = 'a' if append_mode else 'w'

    print(f"Output: {output_path} ({'append' if append_mode else 'overwrite'})")
    print(f"Processing {len(states_to_process)} states/territories...")
    print()

    total_features = 0
    failed_states = []

    with open(output_path, file_mode) as f:
        for i, state_fips in enumerate(states_to_process):
            print(f"[{i+1}/{len(states_to_process)}] State FIPS {state_fips}...")

            try:
                # Fetch state baselines
                state_income = fetch_state_median_income(state_fips, api_key)
                time.sleep(CENSUS_DELAY)

                state_minority = fetch_state_minority_pct(state_fips, api_key)
                time.sleep(CENSUS_DELAY)

                print(f"  Baselines: income=${state_income:,.0f}" if state_income else "  Baselines: income=N/A", end="")
                print(f", minority={state_minority:.1f}%" if state_minority else ", minority=N/A")

                # Fetch tract-level data
                income_data = fetch_tract_income(state_fips, api_key)
                time.sleep(CENSUS_DELAY)
                print(f"  Income data: {len(income_data)} tracts")

                minority_data = fetch_tract_minority(state_fips, api_key)
                time.sleep(CENSUS_DELAY)
                print(f"  Minority data: {len(minority_data)} tracts")

                # Compute minority quartiles for this state
                minority_pcts = [v['minority_percentage'] for v in minority_data.values()
                                 if 0 <= v['minority_percentage'] <= 100]
                minority_pcts.sort()
                n = len(minority_pcts)
                if n > 0:
                    q1 = minority_pcts[int(n * 0.25)]
                    q2 = minority_pcts[int(n * 0.50)]
                    q3 = minority_pcts[int(n * 0.75)]
                else:
                    q1 = q2 = q3 = None

                # Extract unique county FIPS from income data for per-county fallback
                county_fips_set = set()
                for geoid in list(income_data.keys()) + list(minority_data.keys()):
                    if len(geoid) >= 5:
                        county_fips_set.add(geoid[2:5])
                county_fips_list = sorted(county_fips_set)

                # Fetch boundaries (falls back to per-county if state-level fails)
                features = fetch_tract_boundaries(state_fips, county_fips_list)
                time.sleep(TIGER_DELAY)
                print(f"  Boundaries: {len(features)} tracts")

                # Merge and write features
                state_count = 0
                for feature in features:
                    geoid = str(feature['properties'].get('GEOID', '')).strip().zfill(11)
                    props = feature['properties']

                    # Add income data
                    tract_income = income_data.get(geoid)
                    props['median_family_income'] = tract_income
                    props['income_category'] = categorize_income(tract_income, state_income)
                    props['baseline_median_income'] = state_income
                    props['baseline_type'] = 'state'
                    if tract_income and state_income and state_income > 0:
                        props['income_ratio'] = round(tract_income / state_income, 3)
                    else:
                        props['income_ratio'] = None

                    # Add minority data
                    m = minority_data.get(geoid)
                    if m:
                        pct = m['minority_percentage']
                        props['minority_percentage'] = round(pct, 1)
                        props['total_population'] = m['total_population']
                        props['minority_population'] = m['minority_population']
                        # Categorize by state quartile
                        if q1 is not None:
                            if pct < q1:
                                props['minority_category'] = 'Q1 (Lowest 25%)'
                            elif pct < q2:
                                props['minority_category'] = 'Q2 (25-50%)'
                            elif pct < q3:
                                props['minority_category'] = 'Q3 (50-75%)'
                            else:
                                props['minority_category'] = 'Q4 (Highest 25%)'
                        else:
                            props['minority_category'] = 'Unknown'
                    else:
                        props['minority_percentage'] = None
                        props['minority_category'] = 'Unknown'
                        props['total_population'] = None
                        props['minority_population'] = None

                    # Write as line-delimited GeoJSON (one feature per line)
                    f.write(json.dumps(feature) + '\n')
                    state_count += 1

                total_features += state_count
                print(f"  Written: {state_count} features (total: {total_features})")
                print()

            except Exception as e:
                print(f"  ERROR: {e}")
                failed_states.append((state_fips, str(e)))
                print()
                continue

    print("=" * 60)
    print(f"Total features written: {total_features}")
    file_size = output_path.stat().st_size / (1024 * 1024)
    print(f"File size: {file_size:.1f} MB")

    if failed_states:
        print(f"\nFailed states ({len(failed_states)}):")
        for fips, err in failed_states:
            print(f"  {fips}: {err}")

    print(f"\nNext steps:")
    print(f"  1. pip install mapbox-tilesets")
    print(f"  2. export MAPBOX_ACCESS_TOKEN=sk.eyJ...  (secret token with tilesets:write scope)")
    print(f"  3. tilesets upload-source jedlebi census-tracts {output_path}")
    print(f"  4. tilesets create jedlebi.census-tracts --recipe scripts/census_tileset_recipe.json --name 'Census Tracts'")
    print(f"  5. tilesets publish jedlebi.census-tracts")


if __name__ == '__main__':
    main()
