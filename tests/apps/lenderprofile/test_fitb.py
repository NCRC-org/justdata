#!/usr/bin/env python3
"""
Test script for FITB (Fifth Third Bancorp) report generation.
Tests ticker resolution, preferred stock filtering, and report building.
"""

import os
import sys
import json
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from justdata.shared.utils.unified_env import ensure_unified_env_loaded
ensure_unified_env_loaded(verbose=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_ticker_resolver():
    """Test the ticker resolver with FITB-related lookups."""
    print("\n" + "="*60)
    print("TESTING TICKER RESOLVER")
    print("="*60)

    from justdata.apps.lenderprofile.services.ticker_resolver import TickerResolver

    resolver = TickerResolver()

    # Test 1: Preferred stock detection
    print("\n--- Test 1: Preferred Stock Detection ---")
    test_tickers = ['FITB', 'FITBI', 'FITBO', 'FITBP', 'JPM', 'BAC.PRA', 'WFC-PL']
    for ticker in test_tickers:
        is_preferred = resolver._is_preferred_stock(ticker)
        is_common = resolver._is_common_stock(ticker)
        print(f"  {ticker}: preferred={is_preferred}, common={is_common}")

    # Test 2: Get common stock from list
    print("\n--- Test 2: Get Common Stock Ticker ---")
    fitb_family = ['FITB', 'FITBI', 'FITBO', 'FITBP']
    common = resolver.get_common_stock_ticker(fitb_family)
    print(f"  From {fitb_family} -> common stock: {common}")

    # Test 3: Resolve ticker for Fifth Third
    print("\n--- Test 3: Resolve Ticker by Name ---")
    test_names = [
        'Fifth Third Bancorp',
        'Fifth Third Bank',
        'JPMorgan Chase & Co.',
        'Bank of America Corporation'
    ]
    for name in test_names:
        ticker = resolver.resolve_ticker(company_name=name)
        print(f"  '{name}' -> {ticker}")

    print("\n[TICKER RESOLVER TESTS COMPLETE]")
    return True


def test_identifier_resolution():
    """Test identifier resolution for FITB."""
    print("\n" + "="*60)
    print("TESTING IDENTIFIER RESOLUTION")
    print("="*60)

    from justdata.apps.lenderprofile.processors.identifier_resolver import IdentifierResolver

    resolver = IdentifierResolver()

    # Search for Fifth Third
    print("\n--- Searching for 'Fifth Third' ---")
    candidates = resolver.get_candidates_with_location('Fifth Third', limit=5)

    if candidates:
        print(f"Found {len(candidates)} candidates:")
        for i, c in enumerate(candidates[:5], 1):
            print(f"  {i}. {c.get('name')}")
            print(f"     Location: {c.get('city', '')}, {c.get('state', '')}")
            print(f"     FDIC Cert: {c.get('fdic_cert')}")
            print(f"     LEI: {c.get('lei')}")
            print(f"     Confidence: {c.get('confidence', 0):.2f}")
    else:
        print("  No candidates found")

    print("\n[IDENTIFIER RESOLUTION TESTS COMPLETE]")
    return candidates[0] if candidates else None


def test_data_collection(identifiers):
    """Test data collection for FITB."""
    print("\n" + "="*60)
    print("TESTING DATA COLLECTION")
    print("="*60)

    if not identifiers:
        print("  No identifiers provided, skipping...")
        return None

    from justdata.apps.lenderprofile.processors.data_collector import DataCollector

    collector = DataCollector()

    print(f"\n--- Collecting data for: {identifiers.get('name')} ---")
    print(f"    Identifiers: FDIC={identifiers.get('fdic_cert')}, LEI={identifiers.get('lei')}")

    data = collector.collect_all_data(identifiers, identifiers.get('name'))

    # Print summary of collected data
    print("\n--- Data Collection Summary ---")
    for key, value in data.items():
        if value is None:
            print(f"  {key}: None")
        elif isinstance(value, dict):
            print(f"  {key}: {len(value)} fields")
        elif isinstance(value, list):
            print(f"  {key}: {len(value)} items")
        else:
            print(f"  {key}: {type(value).__name__}")

    print("\n[DATA COLLECTION TESTS COMPLETE]")
    return data


def test_section_builders_v2():
    """Test the new intelligence-focused section builders."""
    print("\n" + "="*60)
    print("TESTING SECTION BUILDERS V2")
    print("="*60)

    from justdata.apps.lenderprofile.report_builder import section_builders_v2 as sb

    # Create sample data
    sample_data = {
        'fdic_data': {
            'NAME': 'Fifth Third Bank',
            'ASSET': 200000000,
            'DEP': 150000000,
            'NETINC': 2500000,
            'ROA': 1.25,
            'ROE': 12.5,
            'RBC1AAJ': 12.0,
        },
        'sec_data': {
            'business_description': 'Fifth Third is a diversified financial services company.',
            'risk_factors': [
                {'category': 'Credit Risk', 'text': 'Credit losses could increase...'},
                {'category': 'Interest Rate Risk', 'text': 'Changes in interest rates...'},
            ],
        },
        'gleif_data': {
            'entity': {'legalName': {'name': 'Fifth Third Bancorp'}},
            'parent': {'name': 'Fifth Third Bancorp', 'lei': '549300GT0BCQX0NNG046'},
            'children': [
                {'name': 'Fifth Third Bank', 'lei': '549300EXAMPLE123'},
            ]
        }
    }

    # Test each section builder
    print("\n--- Testing Section Builders ---")

    # Financial Performance
    print("  Building Financial Performance section...")
    fin_section = sb.build_financial_performance(sample_data)
    print(f"    -> {len(fin_section.get('metrics', []))} metrics")

    # Risk Factors
    print("  Building Risk Factors section...")
    risk_section = sb.build_risk_factors(sample_data.get('sec_data', {}))
    print(f"    -> {len(risk_section.get('categories', []))} categories")

    # Corporate Structure
    print("  Building Corporate Structure section...")
    corp_section = sb.build_corporate_structure(sample_data)
    print(f"    -> Parent: {corp_section.get('parent', {}).get('name', 'N/A')}")
    print(f"    -> Subsidiaries: {len(corp_section.get('subsidiaries', []))}")

    print("\n[SECTION BUILDERS V2 TESTS COMPLETE]")
    return True


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("  FITB (Fifth Third Bancorp) TEST SUITE")
    print("="*70)

    # Test 1: Ticker Resolver
    try:
        test_ticker_resolver()
    except Exception as e:
        print(f"\n[ERROR] Ticker resolver test failed: {e}")
        import traceback
        traceback.print_exc()

    # Test 2: Identifier Resolution
    identifiers = None
    try:
        identifiers = test_identifier_resolution()
    except Exception as e:
        print(f"\n[ERROR] Identifier resolution test failed: {e}")
        import traceback
        traceback.print_exc()

    # Test 3: Data Collection (optional - takes longer)
    if identifiers and os.getenv('RUN_FULL_TEST', '').lower() == 'true':
        try:
            test_data_collection(identifiers)
        except Exception as e:
            print(f"\n[ERROR] Data collection test failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\n[SKIPPING] Data collection test (set RUN_FULL_TEST=true to enable)")

    # Test 4: Section Builders
    try:
        test_section_builders_v2()
    except Exception as e:
        print(f"\n[ERROR] Section builders test failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*70)
    print("  ALL TESTS COMPLETE")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
