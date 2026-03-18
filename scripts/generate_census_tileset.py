#!/usr/bin/env python3
"""
Generate a national census tract GeoJSON with income + minority data baked in.

Minority quartiles are computed per CBSA (metro area), NOT per state.
Each tract is graded against the other tracts in its metro area.
Rural tracts (not in any CBSA) are graded against rural tracts in their state.

Fetches TIGERweb boundaries and Census ACS data for all US states/territories,
merges them, and outputs line-delimited GeoJSON for Mapbox Tiling Service upload.

Requires BigQuery access to fetch county-to-CBSA mapping from shared.cbsa_to_county.

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
from collections import defaultdict
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


def fetch_cbsa_county_mapping():
    """Fetch county-to-CBSA mapping from BigQuery shared.cbsa_to_county.

    Returns dict: geoid5 (5-digit county FIPS) -> {'cbsa_code': str, 'cbsa_name': str}
    """
    from google.cloud import bigquery

    project_id = os.environ.get('JUSTDATA_PROJECT_ID', 'justdata-ncrc')

    # Check for credentials JSON in env
    creds_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    if creds_json:
        import tempfile
        creds_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        creds_file.write(creds_json)
        creds_file.close()
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = creds_file.name

    client = bigquery.Client(project=project_id)

    query = """
    SELECT DISTINCT
        CAST(geoid5 AS STRING) as geoid5,
        CAST(cbsa_code AS STRING) as cbsa_code,
        CBSA as cbsa_name
    FROM shared.cbsa_to_county
    WHERE cbsa_code IS NOT NULL
    """

    print("Fetching county-to-CBSA mapping from BigQuery...")
    results = client.query(query).result()

    mapping = {}
    for row in results:
        geoid5 = str(row.geoid5).zfill(5)
        mapping[geoid5] = {
            'cbsa_code': str(row.cbsa_code),
            'cbsa_name': row.cbsa_name
        }

    print(f"  Loaded {len(mapping)} county-to-CBSA mappings")
    return mapping


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


def compute_quartiles(pct_list):
    """Compute Q1, Q2 (median), Q3 from a sorted list of percentages."""
    vals = sorted([p for p in pct_list if 0 <= p <= 100])
    n = len(vals)
    if n == 0:
        return None
    return {
        'q1': vals[int(n * 0.25)],
        'q2': vals[int(n * 0.50)],
        'q3': vals[int(n * 0.75)]
    }


def categorize_by_quartile(pct, quartiles):
    """Assign minority category based on quartile thresholds."""
    if quartiles is None:
        return 'Unknown'
    if pct < quartiles['q1']:
        return 'Q1 (Lowest 25%)'
    elif pct < quartiles['q2']:
        return 'Q2 (25-50%)'
    elif pct < quartiles['q3']:
        return 'Q3 (50-75%)'
    else:
        return 'Q4 (Highest 25%)'


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

    # ── Phase 1: Fetch county-to-CBSA mapping from BigQuery ──
    print("=" * 60)
    print("PHASE 1: Loading county-to-CBSA mapping")
    print("=" * 60)
    cbsa_map = fetch_cbsa_county_mapping()
    print()

    # ── Phase 2: Fetch all tract minority data (all states) ──
    print("=" * 60)
    print("PHASE 2: Fetching tract-level data from Census API")
    print("=" * 60)
    print(f"Processing {len(states_to_process)} states/territories...")
    print()

    # Accumulated data across all states
    all_minority_data = {}   # geoid11 -> {total_population, minority_population, minority_percentage}
    all_income_data = {}     # geoid11 -> income value
    state_incomes = {}       # state_fips -> median income
    failed_states = []

    for i, state_fips in enumerate(states_to_process):
        print(f"[{i+1}/{len(states_to_process)}] State FIPS {state_fips}...")

        try:
            # State baseline income (still needed for income categorization)
            state_income = fetch_state_median_income(state_fips, api_key)
            time.sleep(CENSUS_DELAY)
            state_incomes[state_fips] = state_income

            print(f"  Baseline income: ${state_income:,.0f}" if state_income else "  Baseline income: N/A")

            # Tract-level income
            income_data = fetch_tract_income(state_fips, api_key)
            time.sleep(CENSUS_DELAY)
            print(f"  Income data: {len(income_data)} tracts")
            all_income_data.update(income_data)

            # Tract-level minority
            minority_data = fetch_tract_minority(state_fips, api_key)
            time.sleep(CENSUS_DELAY)
            print(f"  Minority data: {len(minority_data)} tracts")
            all_minority_data.update(minority_data)

            print()

        except Exception as e:
            print(f"  ERROR: {e}")
            failed_states.append((state_fips, str(e)))
            print()
            continue

    print(f"Total tracts collected: {len(all_minority_data)} minority, {len(all_income_data)} income")
    print()

    # ── Phase 3: Compute CBSA-scoped minority quartiles ──
    print("=" * 60)
    print("PHASE 3: Computing CBSA-scoped minority quartiles")
    print("=" * 60)

    # Group tract minority percentages by CBSA
    cbsa_tracts = defaultdict(list)       # cbsa_code -> [minority_pct, ...]
    rural_tracts = defaultdict(list)      # state_fips -> [minority_pct, ...]
    tract_cbsa_lookup = {}                # geoid11 -> {'cbsa_code': str, 'cbsa_name': str} or None

    for geoid, data in all_minority_data.items():
        county_geoid5 = geoid[:5]  # state(2) + county(3)
        cbsa_info = cbsa_map.get(county_geoid5)

        if cbsa_info:
            cbsa_tracts[cbsa_info['cbsa_code']].append(data['minority_percentage'])
            tract_cbsa_lookup[geoid] = cbsa_info
        else:
            state_fips = geoid[:2]
            rural_tracts[state_fips].append(data['minority_percentage'])
            tract_cbsa_lookup[geoid] = None

    # Compute quartiles per CBSA
    cbsa_quartiles = {}
    for cbsa_code, pcts in cbsa_tracts.items():
        cbsa_quartiles[cbsa_code] = compute_quartiles(pcts)

    # Compute quartiles for rural tracts per state
    rural_quartiles = {}
    for state_fips, pcts in rural_tracts.items():
        rural_quartiles[state_fips] = compute_quartiles(pcts)

    # Get CBSA names for reporting
    cbsa_names = {}
    for info in cbsa_map.values():
        cbsa_names[info['cbsa_code']] = info['cbsa_name']

    metro_count = len(cbsa_tracts)
    rural_state_count = len(rural_tracts)
    metro_tract_count = sum(len(v) for v in cbsa_tracts.values())
    rural_tract_count = sum(len(v) for v in rural_tracts.values())

    print(f"  {metro_count} CBSAs with {metro_tract_count} tracts")
    print(f"  {rural_state_count} states with {rural_tract_count} rural tracts")
    print()

    # ── Phase 4: Fetch boundaries and write features ──
    print("=" * 60)
    print("PHASE 4: Fetching boundaries and writing features")
    print("=" * 60)
    print(f"Output: {output_path} ({'append' if append_mode else 'overwrite'})")
    print()

    total_features = 0

    with open(output_path, file_mode) as f:
        for i, state_fips in enumerate(states_to_process):
            if state_fips in [sf for sf, _ in failed_states]:
                print(f"[{i+1}/{len(states_to_process)}] State FIPS {state_fips} — skipped (failed in phase 2)")
                continue

            print(f"[{i+1}/{len(states_to_process)}] State FIPS {state_fips}...")

            try:
                state_income = state_incomes.get(state_fips)

                # Get county list for TIGERweb fallback
                county_fips_set = set()
                for geoid in list(all_income_data.keys()) + list(all_minority_data.keys()):
                    if geoid[:2] == state_fips and len(geoid) >= 5:
                        county_fips_set.add(geoid[2:5])
                county_fips_list = sorted(county_fips_set)

                # Fetch boundaries
                features = fetch_tract_boundaries(state_fips, county_fips_list)
                time.sleep(TIGER_DELAY)
                print(f"  Boundaries: {len(features)} tracts")

                state_count = 0
                for feature in features:
                    geoid = str(feature['properties'].get('GEOID', '')).strip().zfill(11)
                    props = feature['properties']

                    # ── Income data (unchanged — still state-relative) ──
                    tract_income = all_income_data.get(geoid)
                    props['median_family_income'] = tract_income
                    props['income_category'] = categorize_income(tract_income, state_income)
                    props['baseline_median_income'] = state_income
                    props['baseline_type'] = 'state'
                    if tract_income and state_income and state_income > 0:
                        props['income_ratio'] = round(tract_income / state_income, 3)
                    else:
                        props['income_ratio'] = None

                    # ── Minority data (CBSA-scoped quartiles) ──
                    m = all_minority_data.get(geoid)
                    if m:
                        pct = m['minority_percentage']
                        props['minority_percentage'] = round(pct, 1)
                        props['total_population'] = m['total_population']
                        props['minority_population'] = m['minority_population']

                        cbsa_info = tract_cbsa_lookup.get(geoid)
                        if cbsa_info:
                            # Metro tract — grade against CBSA
                            q = cbsa_quartiles.get(cbsa_info['cbsa_code'])
                            props['minority_category'] = categorize_by_quartile(pct, q)
                            props['cbsa_code'] = cbsa_info['cbsa_code']
                            props['cbsa_name'] = cbsa_info['cbsa_name']
                        else:
                            # Rural tract — grade against rural tracts in state
                            q = rural_quartiles.get(geoid[:2])
                            props['minority_category'] = categorize_by_quartile(pct, q)
                            props['cbsa_code'] = None
                            props['cbsa_name'] = None
                    else:
                        props['minority_percentage'] = None
                        props['minority_category'] = 'Unknown'
                        props['total_population'] = None
                        props['minority_population'] = None
                        props['cbsa_code'] = None
                        props['cbsa_name'] = None

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
