#!/usr/bin/env python3
"""
ElectWatch Full Pipeline Runner

Re-runs the complete enrichment pipeline:
1. Load officials data
2. Process PAC contributions with corrected classifier
3. Process individual contributions (with employer classification)
4. Calculate unified HHI across PAC + Individual
5. Run influence scoring
6. Export comprehensive CSV

Usage:
    python run_pipeline.py
"""

import csv
import json
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load from JustData root directory
    env_path = Path(__file__).parent.parent.parent.parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    pass  # dotenv not installed, rely on system environment

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from justdata.apps.electwatch.services.fec_bulk import FECBulkProcessor
from justdata.apps.electwatch.services.pac_classifier import PACClassifier
from justdata.apps.electwatch.services.unified_classifier import UnifiedClassifier
from justdata.apps.electwatch.services.influence_scoring import InfluenceScoringEngine
from justdata.apps.electwatch.services.net_worth_client import get_net_worth, get_wealth_tier

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
CURRENT_DIR = DATA_DIR / "current"
CACHE_DIR = DATA_DIR / "cache"
EXPORT_DIR = DATA_DIR / "exports"


# Employer classification patterns (same approach as PAC classifier)
EMPLOYER_PATTERNS = [
    # Banking - Major banks
    (['JPMORGAN', 'JP MORGAN', 'CHASE'], 'banking', 'major_bank'),
    (['BANK OF AMERICA', 'BOFA'], 'banking', 'major_bank'),
    (['WELLS FARGO'], 'banking', 'major_bank'),
    (['CITIBANK', 'CITIGROUP', 'CITI'], 'banking', 'major_bank'),
    (['GOLDMAN SACHS'], 'investment_banking', 'investment_bank'),
    (['MORGAN STANLEY'], 'investment_banking', 'investment_bank'),

    # Banking - Regional banks
    (['PNC BANK', 'PNC FINANCIAL'], 'banking', 'regional_bank'),
    (['TRUIST', 'SUNTRUST', 'BB&T'], 'banking', 'regional_bank'),
    (['U.S. BANK', 'US BANCORP'], 'banking', 'regional_bank'),
    (['REGIONS BANK', 'REGIONS FINANCIAL'], 'banking', 'regional_bank'),
    (['FIFTH THIRD'], 'banking', 'regional_bank'),
    (['KEYBANK', 'KEYCORP'], 'banking', 'regional_bank'),
    (['CITIZENS BANK', 'CITIZENS FINANCIAL'], 'banking', 'regional_bank'),
    (['M&T BANK'], 'banking', 'regional_bank'),
    (['HUNTINGTON BANK'], 'banking', 'regional_bank'),
    (['ZIONS BANK'], 'banking', 'regional_bank'),
    (['COMERICA'], 'banking', 'regional_bank'),

    # Insurance
    (['AFLAC'], 'insurance', 'life_health'),
    (['METLIFE'], 'insurance', 'life_health'),
    (['PRUDENTIAL'], 'insurance', 'life_health'),
    (['NEW YORK LIFE'], 'insurance', 'life_health'),
    (['NORTHWESTERN MUTUAL'], 'insurance', 'life_health'),
    (['CIGNA'], 'insurance', 'health'),
    (['AETNA'], 'insurance', 'health'),
    (['ANTHEM'], 'insurance', 'health'),
    (['BLUE CROSS', 'BLUE SHIELD', 'BCBS'], 'insurance', 'health'),
    (['UNITEDHEALTH GROUP', 'UNITEDHEALTHCARE'], 'insurance', 'health'),
    (['ALLSTATE'], 'insurance', 'property_casualty'),
    (['STATE FARM'], 'insurance', 'property_casualty'),
    (['PROGRESSIVE INSURANCE', 'PROGRESSIVE CORP'], 'insurance', 'property_casualty'),
    (['LIBERTY MUTUAL'], 'insurance', 'property_casualty'),
    (['TRAVELERS'], 'insurance', 'property_casualty'),
    (['HARTFORD'], 'insurance', 'property_casualty'),
    (['CHUBB'], 'insurance', 'property_casualty'),
    (['NATIONWIDE'], 'insurance', 'property_casualty'),
    (['USAA'], 'insurance', 'property_casualty'),
    (['AIG', 'AMERICAN INTERNATIONAL GROUP'], 'insurance', 'conglomerate'),

    # Investment/Asset Management
    (['BLACKROCK'], 'investment', 'asset_management'),
    (['VANGUARD'], 'investment', 'asset_management'),
    (['FIDELITY'], 'investment', 'asset_management'),
    (['STATE STREET'], 'investment', 'asset_management'),
    (['SCHWAB', 'CHARLES SCHWAB'], 'investment', 'brokerage'),
    (['TIAA'], 'investment', 'retirement'),
    (['EDWARD JONES'], 'investment', 'brokerage'),
    (['RAYMOND JAMES'], 'investment', 'brokerage'),
    (['AMERIPRISE'], 'investment', 'brokerage'),

    # Private Equity
    (['BLACKSTONE'], 'private_equity', 'buyout'),
    (['KKR', 'KOHLBERG KRAVIS'], 'private_equity', 'buyout'),
    (['CARLYLE'], 'private_equity', 'buyout'),
    (['APOLLO'], 'private_equity', 'buyout'),
    (['BAIN CAPITAL'], 'private_equity', 'buyout'),
    (['TPG CAPITAL'], 'private_equity', 'buyout'),

    # Payments/Fintech
    (['VISA'], 'payments', 'card_network'),
    (['MASTERCARD'], 'payments', 'card_network'),
    (['AMERICAN EXPRESS', 'AMEX'], 'payments', 'card_issuer'),
    (['DISCOVER FINANCIAL'], 'payments', 'card_issuer'),
    (['CAPITAL ONE'], 'payments', 'card_issuer'),
    (['PAYPAL'], 'payments', 'digital'),
    (['FISERV'], 'payments', 'processing'),
    (['FIS GLOBAL', 'FIDELITY NATIONAL INFO'], 'payments', 'processing'),
    (['GLOBAL PAYMENTS'], 'payments', 'processing'),

    # Real Estate
    (['REALTOR', 'REALTORS'], 'real_estate', 'brokerage'),
    (['CBRE'], 'real_estate', 'commercial'),
    (['JLL', 'JONES LANG'], 'real_estate', 'commercial'),
    (['CUSHMAN'], 'real_estate', 'commercial'),
    (['COLDWELL BANKER'], 'real_estate', 'residential'),
    (['KELLER WILLIAMS'], 'real_estate', 'residential'),
    (['REMAX', 'RE/MAX'], 'real_estate', 'residential'),
    (['COMPASS REAL ESTATE'], 'real_estate', 'residential'),
    (['TITLE INSURANCE', 'FIRST AMERICAN TITLE'], 'real_estate', 'title'),

    # Mortgage/Lending
    (['ROCKET MORTGAGE', 'QUICKEN LOANS'], 'lending', 'mortgage'),
    (['LOAN DEPOT', 'LOANDEPOT'], 'lending', 'mortgage'),
    (['UNITED WHOLESALE', 'UWM'], 'lending', 'mortgage'),
    (['PENNYMAC'], 'lending', 'mortgage'),
    (['FREEDOM MORTGAGE'], 'lending', 'mortgage'),

    # Credit Unions
    (['CREDIT UNION', 'FCU', 'FEDERAL CREDIT UNION'], 'credit_unions', 'institution'),
]

# Employer exclusion patterns (same as PAC)
EMPLOYER_EXCLUSIONS = [
    # Labor unions
    'SEIU', 'SERVICE EMPLOYEES INTERNATIONAL',
    'AFSCME', 'AMERICAN FEDERATION OF STATE',
    'AFT', 'AMERICAN FEDERATION OF TEACHERS',
    'UNITE HERE',
    'UFCW', 'UNITED FOOD AND COMMERCIAL',
    'IBEW', 'INTERNATIONAL BROTHERHOOD OF ELECTRICAL',
    'TEAMSTERS',
    'UAW', 'UNITED AUTO WORKERS',
    'USW', 'UNITED STEELWORKERS',
    'CWA', 'COMMUNICATIONS WORKERS',
    'NURSES UNITED', 'NATIONAL NURSES',
    'HEALTHCARE WORKERS',

    # Government/Nonprofit
    'RETIRED', 'NOT EMPLOYED', 'SELF-EMPLOYED', 'HOMEMAKER',
    'US GOVERNMENT', 'FEDERAL GOVERNMENT', 'STATE OF ',
    'UNIVERSITY', 'COLLEGE', 'SCHOOL DISTRICT',
]


def classify_employer(employer: str) -> Dict:
    """Classify an employer into financial sectors."""
    employer = employer.upper().strip()

    result = {
        'employer': employer,
        'is_financial': False,
        'sector': None,
        'subsector': None,
        'confidence': 'none',
    }

    # Check exclusions first
    for exclusion in EMPLOYER_EXCLUSIONS:
        if exclusion in employer:
            return result

    # Check patterns
    for keywords, sector, subsector in EMPLOYER_PATTERNS:
        for kw in keywords:
            if kw in employer:
                result['is_financial'] = True
                result['sector'] = sector
                result['subsector'] = subsector
                result['confidence'] = 'high' if len(kw) > 5 else 'medium'
                return result

    return result


def calculate_unified_hhi(by_sector_pac: Dict, by_sector_indiv: Dict) -> Tuple[float, Dict]:
    """
    Calculate Herfindahl-Hirschman Index across PAC + Individual contributions combined.

    HHI = sum(s_i^2) where s_i is the market share of sector i
    HHI of 10000 = complete concentration in one sector
    HHI < 1500 = unconcentrated
    HHI 1500-2500 = moderately concentrated
    HHI > 2500 = highly concentrated
    """
    # Combine PAC and Individual by sector
    combined = defaultdict(float)

    for sector, amount in by_sector_pac.items():
        combined[sector] += amount

    for sector, amount in by_sector_indiv.items():
        combined[sector] += amount

    total = sum(combined.values())

    if total == 0:
        return 0.0, {'total': 0, 'by_sector': {}}

    # Calculate HHI
    hhi = 0.0
    shares = {}
    for sector, amount in combined.items():
        share = (amount / total) * 100
        shares[sector] = round(share, 1)
        hhi += share ** 2

    # Find dominant sector
    dominant = max(combined.items(), key=lambda x: x[1]) if combined else (None, 0)

    return round(hhi, 1), {
        'total': round(total, 2),
        'by_sector': dict(sorted(shares.items(), key=lambda x: -x[1])),
        'dominant_sector': dominant[0],
        'dominant_pct': round(dominant[1] / total * 100, 1) if total else 0,
    }


def run_pipeline():
    """Run the complete enrichment pipeline."""

    print("="*70)
    print("ELECTWATCH ENRICHMENT PIPELINE")
    print("="*70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Step 1: Load officials data
    print("Step 1: Loading officials data...")
    officials_path = CURRENT_DIR / "officials.json"
    with open(officials_path) as f:
        data = json.load(f)

    officials = data.get('officials', data.get('data', []))
    print(f"  Loaded {len(officials)} officials")

    # Step 1b: Clear old PAC/contribution data to ensure fresh state
    print("\nStep 1b: Clearing old enrichment data...")
    for official in officials:
        # Clear PAC data
        official['financial_pac_bulk'] = 0
        official['financial_pac_pct'] = 0
        official['financial_pac_count'] = 0
        official['total_pac_bulk'] = 0
        official['total_pac_count'] = 0
        official['top_financial_pacs'] = []
        official['pac_by_sector'] = {}
        official['pac_by_subsector'] = {}
        # Clear individual data
        official['financial_individual'] = 0
        official['financial_individual_pct'] = 0
        official['financial_individual_count'] = 0
        official['total_individual'] = 0
        official['total_individual_count'] = 0
        official['top_financial_employers'] = []
        official['top_financial_contributors'] = []
        official['indiv_by_sector'] = {}
        official['indiv_by_subsector'] = {}
        # Clear HHI
        official['unified_hhi'] = 0
        official['unified_hhi_details'] = {}
        # Clear net worth (will be re-populated)
        official['net_worth'] = None
        official['wealth_tier'] = None
        official['wealth_tier_display'] = None
        # Initialize committees if not present (don't clear to preserve cache)
        if 'committees' not in official:
            official['committees'] = []
        if 'subcommittees' not in official:
            official['subcommittees'] = []
    print("  Cleared old data from all officials")

    # Step 1c: Add net worth data
    print("\nStep 1c: Adding net worth data...")
    net_worth_found = 0
    net_worth_estimated = 0
    for official in officials:
        name = official.get('name', '')
        if name:
            nw = get_net_worth(name)
            official['net_worth'] = nw
            tier_code, tier_display = get_wealth_tier(nw['midpoint'])
            official['wealth_tier'] = tier_code
            official['wealth_tier_display'] = tier_display
            if not nw['is_estimate']:
                net_worth_found += 1
            else:
                net_worth_estimated += 1
    print(f"  {net_worth_found} officials with known net worth data")
    print(f"  {net_worth_estimated} officials with estimated net worth (default range)")

    # Step 1d: Enrich with committee assignments
    print("\nStep 1d: Enriching with committee assignments...")
    try:
        from justdata.apps.electwatch.services.congress_api_client import (
            get_congress_client, enrich_officials_with_committees_github
        )

        # First try GitHub (no API key required, more reliable)
        enriched_count = enrich_officials_with_committees_github(officials)
        if enriched_count > 0:
            print(f"  {enriched_count} officials enriched with committee data from GitHub")
        else:
            # Fallback to Congress.gov API if GitHub fails
            congress_client = get_congress_client()
            if congress_client.api_key:
                enriched_count = congress_client.enrich_officials_with_committees(officials)
                print(f"  {enriched_count} officials enriched with committee data from Congress.gov API")
            else:
                print("  Skipped: No committee data available (GitHub failed, no API key)")
    except Exception as e:
        print(f"  Warning: Committee enrichment failed: {e}")

    # Step 2a: Validate and correct FEC IDs
    print("\nStep 2a: Validating and correcting FEC IDs...")
    processor = FECBulkProcessor()
    corrected = processor.validate_and_correct_fec_ids(officials)
    print(f"  Corrected {corrected} FEC IDs based on contribution data")

    # Step 2b: Process PAC contributions
    print("\nStep 2b: Processing PAC contributions...")
    pac_results = processor.process_pac_contributions(officials)

    # Count financial PAC results
    pac_financial_count = sum(1 for o in officials if o.get('financial_pac_bulk', 0) > 0)
    print(f"  {pac_financial_count} officials have financial PAC contributions")

    # Step 3: Process individual contributions (with employer classification)
    print("\nStep 3: Processing individual contributions...")
    indiv_results = processor.process_individual_contributions(officials)

    # Step 4: Employer classification is now done during FEC processing
    print("\nStep 4: Employer classification already done during FEC processing")
    # Count employers with sector classification
    employers_with_sector = 0
    total_employers = 0
    for official in officials:
        for emp in official.get('top_financial_employers', []):
            total_employers += 1
            if emp.get('sector'):
                employers_with_sector += 1
    print(f"  {employers_with_sector}/{total_employers} employers have sector classification")

    # Step 5: Calculate unified HHI for each official
    print("\nStep 5: Calculating unified HHI...")
    for official in officials:
        # Get PAC sector breakdown (already classified during FEC processing)
        by_sector_pac = official.get('pac_by_sector', {})

        # Get individual sector breakdown (already classified during FEC processing)
        by_sector_indiv = official.get('indiv_by_sector', {})

        # Calculate unified HHI
        hhi, hhi_details = calculate_unified_hhi(by_sector_pac, by_sector_indiv)
        official['unified_hhi'] = hhi
        official['unified_hhi_details'] = hhi_details

    # Step 6: Load ticker classifications for influence scoring
    print("\nStep 6: Loading ticker classifications...")
    classifier = UnifiedClassifier()
    ticker_classifications = classifier._unified_cache
    print(f"  Loaded {len(ticker_classifications)} ticker classifications")

    # Step 7: Run influence scoring
    print("\nStep 7: Running influence scoring...")
    engine = InfluenceScoringEngine(
        officials=officials,
        ticker_classifications={
            t: {'is_financial': c.get('is_financial', False), 'subsector': c.get('sub_sector', '')}
            for t, c in ticker_classifications.items()
        }
    )
    scores = engine.calculate_all_scores()

    # Add scores to officials
    for official in officials:
        bioguide_id = official.get('bioguide_id')
        if bioguide_id and bioguide_id in scores:
            official['influence_score'] = scores[bioguide_id].to_dict()

    print(f"  Calculated scores for {len(scores)} officials")

    # Step 8: Save enriched officials
    print("\nStep 8: Saving enriched officials...")
    with open(officials_path, 'w') as f:
        json.dump({'officials': officials, 'last_updated': datetime.now().isoformat()}, f, indent=2)
    print(f"  Saved to {officials_path}")

    # Step 9: Export comprehensive CSV
    print("\nStep 9: Exporting CSV...")
    export_csv(officials)

    # Step 10: Show validation for Markey and Alsobrooks
    print("\n" + "="*70)
    print("VALIDATION: Markey and Alsobrooks PAC Concentration")
    print("="*70)

    for name_part in ['Markey', 'Alsobrooks']:
        for official in officials:
            if name_part.lower() in official.get('name', '').lower():
                print(f"\n{official.get('name')}")
                print(f"  Financial PAC: ${official.get('financial_pac_bulk', 0):,.0f}")
                print(f"  Total PAC: ${official.get('total_pac_bulk', 0):,.0f}")

                top_pacs = official.get('top_financial_pacs', [])[:3]
                if top_pacs:
                    print(f"  Top Financial PACs:")
                    for pac in top_pacs:
                        print(f"    - {pac.get('name', 'Unknown')}: ${pac.get('amount', 0):,.0f} ({pac.get('sector', 'N/A')})")
                else:
                    print(f"  No financial PACs found (correct - previous SEIU was labor union)")

                print(f"  Unified HHI: {official.get('unified_hhi', 0)}")
                hhi_details = official.get('unified_hhi_details', {})
                if hhi_details.get('dominant_sector'):
                    print(f"  Dominant Sector: {hhi_details.get('dominant_sector')} ({hhi_details.get('dominant_pct', 0)}%)")
                break

    # Show summary statistics
    print("\n" + "="*70)
    print("SUMMARY STATISTICS")
    print("="*70)

    # PAC sector breakdown
    sector_totals = defaultdict(float)
    for official in officials:
        for pac in official.get('top_financial_pacs', []):
            sector = pac.get('sector')
            if sector:
                sector_totals[sector] += pac.get('amount', 0)

    print("\nFinancial PAC Contributions by Sector:")
    for sector, amount in sorted(sector_totals.items(), key=lambda x: -x[1])[:10]:
        print(f"  {sector}: ${amount:,.0f}")

    # Top 10 by unified HHI
    print("\nTop 10 by Unified HHI (most concentrated):")
    by_hhi = sorted(officials, key=lambda x: x.get('unified_hhi', 0), reverse=True)[:10]
    for i, o in enumerate(by_hhi, 1):
        hhi = o.get('unified_hhi', 0)
        details = o.get('unified_hhi_details', {})
        dominant = details.get('dominant_sector', 'N/A')
        print(f"  {i}. {o.get('name', 'Unknown')}: HHI {hhi:.0f} (dominant: {dominant})")

    print("\n" + "="*70)
    print(f"Pipeline completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)


def export_csv(officials: List[Dict]):
    """Export comprehensive CSV with all influence data."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    csv_path = EXPORT_DIR / "financial_influence_analysis.csv"

    # Define columns
    columns = [
        'name', 'bioguide_id', 'party', 'state', 'chamber',
        'composite_score', 'scale_score', 'concentration_score', 'personal_score',
        'total_financial_exposure', 'financial_trades', 'financial_pac', 'financial_individual',
        'trade_count', 'pac_count', 'individual_count',
        'unified_hhi', 'dominant_sector', 'dominant_pct',
        'net_worth_display', 'net_worth_midpoint', 'wealth_tier', 'net_worth_is_estimate',
        'pac_banking', 'pac_insurance', 'pac_real_estate', 'pac_investment', 'pac_lending',
        'pac_payments', 'pac_credit_unions', 'pac_private_equity',
        'top_pac_1', 'top_pac_1_amount', 'top_pac_1_sector',
        'top_pac_2', 'top_pac_2_amount', 'top_pac_2_sector',
        'top_pac_3', 'top_pac_3_amount', 'top_pac_3_sector',
        'top_employer_1', 'top_employer_1_amount', 'top_employer_1_sector',
        'top_employer_2', 'top_employer_2_amount', 'top_employer_2_sector',
        'hfsc_member', 'sbc_member',
    ]

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()

        for official in officials:
            # Get score components
            score = official.get('influence_score', {})
            scale_details = score.get('scale_details', {})

            # Get HHI details
            hhi_details = official.get('unified_hhi_details', {})

            # Get net worth data
            net_worth = official.get('net_worth', {})

            # Get sector breakdowns from PACs
            sector_amounts = {}
            for pac in official.get('top_financial_pacs', []):
                sector = pac.get('sector', '')
                sector_amounts[sector] = sector_amounts.get(sector, 0) + pac.get('amount', 0)

            # Top PACs
            top_pacs = official.get('top_financial_pacs', [])[:3]

            # Top employers (sector already populated during FEC processing)
            top_employers = official.get('top_financial_employers', [])[:2]

            # Check committee membership (committees may be strings or dicts)
            committees = official.get('committees', [])
            hfsc = False
            sbc = False
            for c in committees:
                if isinstance(c, dict):
                    name = c.get('name', '')
                elif isinstance(c, str):
                    name = c
                else:
                    continue
                if 'Financial Services' in name:
                    hfsc = True
                if 'Banking' in name:
                    sbc = True

            row = {
                'name': official.get('name', ''),
                'bioguide_id': official.get('bioguide_id', ''),
                'party': official.get('party', ''),
                'state': official.get('state', ''),
                'chamber': official.get('chamber', ''),

                # Scores
                'composite_score': score.get('composite_score', 0),
                'scale_score': score.get('scale_score', 0),
                'concentration_score': score.get('concentration_score', 0),
                'personal_score': score.get('personal_involvement_score', 0),

                # Totals
                'total_financial_exposure': scale_details.get('raw_dollars', 0),
                'financial_trades': scale_details.get('financial_trades_dollars', 0),
                'financial_pac': official.get('financial_pac', 0),
                'financial_individual': official.get('financial_individual', 0),

                # Counts
                'trade_count': len([t for t in official.get('trades', [])]),
                'pac_count': official.get('financial_pac_count', 0),
                'individual_count': official.get('financial_individual_count', 0),

                # HHI
                'unified_hhi': official.get('unified_hhi', 0),
                'dominant_sector': hhi_details.get('dominant_sector', ''),
                'dominant_pct': hhi_details.get('dominant_pct', 0),

                # Net worth
                'net_worth_display': net_worth.get('display', '') if net_worth else '',
                'net_worth_midpoint': net_worth.get('midpoint', 0) if net_worth else 0,
                'wealth_tier': official.get('wealth_tier_display', ''),
                'net_worth_is_estimate': 'Yes' if net_worth and net_worth.get('is_estimate') else 'No',

                # PAC by sector
                'pac_banking': sector_amounts.get('banking', 0) + sector_amounts.get('investment_banking', 0),
                'pac_insurance': sector_amounts.get('insurance', 0),
                'pac_real_estate': sector_amounts.get('real_estate', 0),
                'pac_investment': sector_amounts.get('investment', 0),
                'pac_lending': sector_amounts.get('lending', 0),
                'pac_payments': sector_amounts.get('payments', 0),
                'pac_credit_unions': sector_amounts.get('credit_unions', 0),
                'pac_private_equity': sector_amounts.get('private_equity', 0),

                # Top PACs
                'top_pac_1': top_pacs[0].get('name', '') if len(top_pacs) > 0 else '',
                'top_pac_1_amount': top_pacs[0].get('amount', 0) if len(top_pacs) > 0 else 0,
                'top_pac_1_sector': top_pacs[0].get('sector', '') if len(top_pacs) > 0 else '',
                'top_pac_2': top_pacs[1].get('name', '') if len(top_pacs) > 1 else '',
                'top_pac_2_amount': top_pacs[1].get('amount', 0) if len(top_pacs) > 1 else 0,
                'top_pac_2_sector': top_pacs[1].get('sector', '') if len(top_pacs) > 1 else '',
                'top_pac_3': top_pacs[2].get('name', '') if len(top_pacs) > 2 else '',
                'top_pac_3_amount': top_pacs[2].get('amount', 0) if len(top_pacs) > 2 else 0,
                'top_pac_3_sector': top_pacs[2].get('sector', '') if len(top_pacs) > 2 else '',

                # Top employers
                'top_employer_1': top_employers[0].get('employer', '') if len(top_employers) > 0 else '',
                'top_employer_1_amount': top_employers[0].get('amount', 0) if len(top_employers) > 0 else 0,
                'top_employer_1_sector': top_employers[0].get('sector', '') if len(top_employers) > 0 else '',
                'top_employer_2': top_employers[1].get('employer', '') if len(top_employers) > 1 else '',
                'top_employer_2_amount': top_employers[1].get('amount', 0) if len(top_employers) > 1 else 0,
                'top_employer_2_sector': top_employers[1].get('sector', '') if len(top_employers) > 1 else '',

                # Committee membership
                'hfsc_member': 'Yes' if hfsc else 'No',
                'sbc_member': 'Yes' if sbc else 'No',
            }

            writer.writerow(row)

    print(f"  Exported {len(officials)} officials to {csv_path}")


def run_validation_only():
    """Run just the validation and export on already-enriched data."""
    print("="*70)
    print("ELECTWATCH VALIDATION")
    print("="*70)

    # Load enriched officials
    officials_path = CURRENT_DIR / "officials.json"
    with open(officials_path) as f:
        data = json.load(f)

    officials = data.get('officials', data.get('data', []))
    print(f"Loaded {len(officials)} officials")

    # Export CSV (employer sectors already populated during FEC processing)
    export_csv(officials)

    # Validation for Markey and Alsobrooks
    print("\n" + "="*70)
    print("VALIDATION: Markey and Alsobrooks (SEIU Fix Check)")
    print("="*70)

    for name_part in ['Markey', 'Alsobrooks']:
        for official in officials:
            if name_part.lower() in official.get('name', '').lower():
                print(f"\n{official.get('name')} ({official.get('party')}-{official.get('state')})")
                print(f"  Financial PAC Total: ${official.get('financial_pac_bulk', 0):,.0f}")
                print(f"  Financial PAC %: {official.get('financial_pac_pct', 0)}%")
                print(f"  Total PAC: ${official.get('total_pac_bulk', 0):,.0f}")

                top_pacs = official.get('top_financial_pacs', [])[:5]
                if top_pacs:
                    print(f"  Top 5 Financial PACs:")
                    for pac in top_pacs:
                        print(f"    - {pac.get('name', 'Unknown')[:50]}: ${pac.get('amount', 0):,.0f} ({pac.get('sector', 'N/A')})")
                else:
                    print(f"  No financial PACs found")

                hhi_details = official.get('unified_hhi_details', {})
                print(f"  Unified HHI: {official.get('unified_hhi', 0)}")
                if hhi_details.get('dominant_sector'):
                    print(f"  Dominant Sector: {hhi_details.get('dominant_sector')} ({hhi_details.get('dominant_pct', 0)}%)")
                break

    # HHI Distribution
    print("\n" + "="*70)
    print("UNIFIED HHI DISTRIBUTION")
    print("="*70)

    hhis = [o.get('unified_hhi', 0) for o in officials if o.get('unified_hhi', 0) > 0]
    if hhis:
        print(f"Officials with HHI > 0: {len(hhis)}")
        print(f"Min HHI: {min(hhis):.0f}")
        print(f"Max HHI: {max(hhis):.0f}")
        print(f"Mean HHI: {sum(hhis)/len(hhis):.0f}")

        # Distribution buckets
        buckets = {
            'Unconcentrated (0-1500)': 0,
            'Moderate (1500-2500)': 0,
            'Concentrated (2500-5000)': 0,
            'Highly Concentrated (5000-7500)': 0,
            'Extreme (7500-10000)': 0,
        }
        for hhi in hhis:
            if hhi < 1500:
                buckets['Unconcentrated (0-1500)'] += 1
            elif hhi < 2500:
                buckets['Moderate (1500-2500)'] += 1
            elif hhi < 5000:
                buckets['Concentrated (2500-5000)'] += 1
            elif hhi < 7500:
                buckets['Highly Concentrated (5000-7500)'] += 1
            else:
                buckets['Extreme (7500-10000)'] += 1

        print("\nDistribution:")
        for bucket, count in buckets.items():
            pct = count / len(hhis) * 100
            print(f"  {bucket}: {count} ({pct:.1f}%)")

    # Top 10 by HHI
    print("\nTop 10 by Unified HHI (most concentrated):")
    by_hhi = sorted(officials, key=lambda x: x.get('unified_hhi', 0), reverse=True)[:10]
    for i, o in enumerate(by_hhi, 1):
        hhi = o.get('unified_hhi', 0)
        details = o.get('unified_hhi_details', {})
        dominant = details.get('dominant_sector', 'N/A')
        print(f"  {i}. {o.get('name', 'Unknown')}: HHI {hhi:.0f} ({dominant})")

    # Financial PAC sector breakdown
    print("\n" + "="*70)
    print("FINANCIAL PAC CONTRIBUTIONS BY SECTOR")
    print("="*70)

    sector_totals = defaultdict(float)
    for official in officials:
        for pac in official.get('top_financial_pacs', []):
            sector = pac.get('sector')
            if sector:
                sector_totals[sector] += pac.get('amount', 0)

    total_financial_pac = sum(sector_totals.values())
    print(f"\nTotal Financial PAC: ${total_financial_pac:,.0f}")
    print("\nBy Sector:")
    for sector, amount in sorted(sector_totals.items(), key=lambda x: -x[1]):
        pct = amount / total_financial_pac * 100 if total_financial_pac > 0 else 0
        print(f"  {sector}: ${amount:,.0f} ({pct:.1f}%)")


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'validate':
        run_validation_only()
    else:
        run_pipeline()
