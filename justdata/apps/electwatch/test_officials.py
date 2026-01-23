"""
Test script for focused official data processing.
Tests the fixes for name matching, years in congress, and financial PAC data.
"""

import json
import os
import sys
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test officials - last names to match
TEST_OFFICIALS = [
    'McCormick', 'Shreve', 'McCaul', 'Pelosi', 'Tuberville', 'Mullin', 'Cruz', 'Hern',
    'Khanna', 'Whitesides', 'Wied', 'Franklin', 'Jackson', 'Hill', 'Smith', 'Fields',
    'Dingell', 'Auchincloss', 'Gottheimer', 'Greene', 'Moore', 'Johnson', 'Biggs',
    'Moskowitz', 'Cohen', 'Cisneros', 'Lee', 'McClain', 'Gooden', 'Newhouse',
    'Keating', 'Bresnahan', 'Landsman', 'Hoyle', 'Manning', 'Dunn', 'Collins',
    'Capito', 'Kean', 'James', 'Allen', 'Whitehouse', 'Torres', 'Westerman',
    'Blumenauer', 'Moody', 'McConnell', 'Boozman', 'Taylor', 'Thanedar'
]

def main():
    import requests
    from dotenv import load_dotenv
    load_dotenv()

    # Add project to path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

    from justdata.apps.electwatch.services.crosswalk import get_crosswalk
    from justdata.apps.electwatch.services.congress_api_client import CongressAPIClient

    api_key = os.getenv('FEC_API_KEY')
    if not api_key:
        print("ERROR: FEC_API_KEY not set")
        return

    print("=" * 70)
    print("ELECTWATCH TEST - 50 OFFICIALS")
    print("=" * 70)

    # Step 1: Load crosswalk
    print("\n--- Loading Crosswalk ---")
    crosswalk = get_crosswalk()
    stats = crosswalk.get_statistics()
    print(f"Crosswalk: {stats['total_members']} members, {stats['fec_coverage_pct']}% have FEC IDs")

    # Step 2: Load Congress.gov data
    print("\n--- Loading Congress Members ---")
    client = CongressAPIClient()
    all_members = client.get_all_members()
    print(f"Total members: {len(all_members)}")

    # Step 3: Filter to test officials
    test_members = []
    for m in all_members:
        name = m.get('name', '')
        # Handle "Last, First" format
        if ',' in name:
            last_name = name.split(',')[0].strip()
        else:
            parts = name.split()
            last_name = parts[-1] if parts else ''

        if last_name in TEST_OFFICIALS:
            test_members.append(m)

    print(f"Test members found: {len(test_members)}")

    # Step 4: Verify years in congress
    print("\n--- Checking Years in Congress ---")
    known_years = {
        'Pelosi': 38,  # 1987
        'McConnell': 40,  # 1985
        'Cruz': 12,  # 2013
        'Collins': 28,  # 1997
    }

    for m in test_members:
        name = m.get('name', '')
        years = m.get('years_in_congress', 0)

        for known_name, expected in known_years.items():
            if known_name.lower() in name.lower():
                status = "OK" if abs(years - expected) <= 1 else "WRONG"
                print(f"  {name}: {years} years ({status}, expected ~{expected})")

    # Step 5: Get FEC candidate IDs from crosswalk
    print("\n--- Getting FEC Candidate IDs ---")
    officials_with_fec = 0
    for m in test_members:
        bioguide = m.get('bioguide_id')
        if bioguide:
            fec_id = crosswalk.get_fec_id(bioguide)
            if fec_id:
                m['fec_candidate_id'] = fec_id
                officials_with_fec += 1

    print(f"Officials with FEC ID: {officials_with_fec}/{len(test_members)}")

    # Step 6: Get committee IDs for a sample
    print("\n--- Getting Committee IDs (sample of 10) ---")
    sample = [m for m in test_members if m.get('fec_candidate_id')][:10]

    import time
    for m in sample:
        fec_id = m['fec_candidate_id']
        name = m['name']

        # Get committee from FEC API
        url = f'https://api.open.fec.gov/v1/candidate/{fec_id}/committees/'
        params = {'api_key': api_key, 'designation': 'P'}

        try:
            time.sleep(0.5)
            r = requests.get(url, params=params, timeout=30)
            if r.status_code == 429:
                print(f"  Rate limited, waiting...")
                time.sleep(60)
                r = requests.get(url, params=params, timeout=30)

            if r.ok:
                results = r.json().get('results', [])
                if results:
                    committee_id = results[0].get('committee_id')
                    m['fec_committee_id'] = committee_id
                    print(f"  {name}: {fec_id} -> {committee_id}")
                else:
                    # Try without P designation
                    params.pop('designation', None)
                    r2 = requests.get(url, params=params, timeout=30)
                    if r2.ok:
                        results2 = r2.json().get('results', [])
                        if results2:
                            committee_id = results2[0].get('committee_id')
                            m['fec_committee_id'] = committee_id
                            print(f"  {name}: {fec_id} -> {committee_id} (no P)")
                        else:
                            print(f"  {name}: {fec_id} -> NO COMMITTEE")
        except Exception as e:
            print(f"  {name}: Error - {e}")

    # Step 7: Get financial PAC data for officials with committees
    print("\n--- Getting Financial PAC Data (sample of 5) ---")

    FINANCIAL_KEYWORDS = [
        'BANK', 'FINANCIAL', 'CAPITAL', 'CREDIT', 'INSURANCE', 'INVEST',
        'SECURITIES', 'MORTGAGE', 'WELLS', 'CHASE', 'CITI', 'GOLDMAN',
        'MORGAN STANLEY', 'AMERICAN EXPRESS', 'VISA', 'MASTERCARD', 'BLACKROCK',
        'FIDELITY', 'SCHWAB', 'PRUDENTIAL', 'METLIFE', 'PNC', 'TRUIST'
    ]

    sample_with_committee = [m for m in sample if m.get('fec_committee_id')][:5]

    rolling_end = datetime.now()
    rolling_start = rolling_end - timedelta(days=730)
    min_date = rolling_start.strftime('%Y-%m-%d')
    max_date = rolling_end.strftime('%Y-%m-%d')

    for m in sample_with_committee:
        committee_id = m['fec_committee_id']
        name = m['name']

        url = 'https://api.open.fec.gov/v1/schedules/schedule_a/'
        params = {
            'api_key': api_key,
            'committee_id': committee_id,
            'min_date': min_date,
            'max_date': max_date,
            'contributor_type': 'committee',
            'per_page': 100,
            'page': 1
        }

        try:
            time.sleep(0.5)
            r = requests.get(url, params=params, timeout=60)
            if r.status_code == 429:
                print(f"  Rate limited, waiting...")
                time.sleep(60)
                r = requests.get(url, params=params, timeout=60)

            if r.ok:
                results = r.json().get('results', [])
                financial_total = 0
                all_pac_total = 0
                financial_pacs = []

                for c in results:
                    contrib_name = c.get('contributor_name', '').upper()
                    amount = c.get('contribution_receipt_amount', 0)

                    is_pac = 'PAC' in contrib_name or 'POLITICAL ACTION' in contrib_name
                    if amount > 0 and is_pac:
                        all_pac_total += amount
                        if any(kw in contrib_name for kw in FINANCIAL_KEYWORDS):
                            financial_total += amount
                            financial_pacs.append(contrib_name[:40])

                pct = round((financial_total / all_pac_total * 100), 1) if all_pac_total > 0 else 0
                print(f"  {name}: ${financial_total:,.0f} financial / ${all_pac_total:,.0f} total ({pct}%)")
                if financial_pacs[:3]:
                    print(f"    Sample PACs: {financial_pacs[:3]}")
        except Exception as e:
            print(f"  {name}: Error - {e}")

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)

if __name__ == '__main__':
    main()
