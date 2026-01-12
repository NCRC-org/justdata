#!/usr/bin/env python3
"""
Comprehensive API Testing Script for LenderProfile
Tests each API/source individually to identify what works and what doesn't.
"""

import sys
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.utils.unified_env import ensure_unified_env_loaded, get_unified_config
from shared.utils.bigquery_client import get_bigquery_client, execute_query, escape_sql_string
from apps.lenderprofile.processors.identifier_resolver import IdentifierResolver
from apps.lenderprofile.processors.data_collector import DataCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment
ensure_unified_env_loaded(verbose=True)
config = get_unified_config(verbose=True)


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_result(success: bool, message: str, data: Any = None):
    """Print a formatted test result."""
    status = "[PASS]" if success else "[FAIL]"
    print(f"\n{status}: {message}")
    if data is not None:
        if isinstance(data, dict):
            print(f"   Data keys: {list(data.keys())}")
            # Print summary of data
            for key, value in list(data.items())[:5]:
                if isinstance(value, (dict, list)):
                    print(f"   {key}: {type(value).__name__} ({len(value) if isinstance(value, (dict, list)) else 'N/A'})")
                else:
                    print(f"   {key}: {str(value)[:100]}")
        elif isinstance(data, list):
            print(f"   List length: {len(data)}")
            if data:
                print(f"   First item: {str(data[0])[:200]}")
        else:
            print(f"   Result: {str(data)[:200]}")


def get_gleif_from_bigquery(lender_name: str):
    """Get GLEIF data from BigQuery by name."""
    try:
        project_id = os.getenv('GCP_PROJECT_ID', 'hdma1-242116')
        client = get_bigquery_client(project_id)
        
        # Search for lender in BigQuery GLEIF table
        query = f"""
        SELECT 
            lei,
            gleif_legal_name,
            cleaned_name,
            display_name,
            legal_address_city,
            legal_address_state,
            headquarters_city,
            headquarters_state,
            direct_parent_lei,
            direct_parent_name,
            ultimate_parent_lei,
            ultimate_parent_name,
            direct_children,
            ultimate_children
        FROM `{project_id}.justdata.gleif_names`
        WHERE UPPER(gleif_legal_name) LIKE '%{escape_sql_string(lender_name.upper())}%'
           OR UPPER(cleaned_name) LIKE '%{escape_sql_string(lender_name.upper())}%'
        ORDER BY 
            CASE 
                WHEN UPPER(gleif_legal_name) = '{escape_sql_string(lender_name.upper())}' THEN 1
                WHEN UPPER(gleif_legal_name) LIKE '{escape_sql_string(lender_name.upper())}%' THEN 2
                ELSE 3
            END
        LIMIT 10
        """
        
        results = execute_query(client, query)
        return results
    except Exception as e:
        logger.error(f"Error querying BigQuery GLEIF: {e}", exc_info=True)
        return []


def test_identifier_resolution(lender_name: str):
    """Test Step 1: Identifier Resolution."""
    print_section("STEP 1: IDENTIFIER RESOLUTION")
    print(f"Testing identifier resolution for: '{lender_name}'")
    
    # First, try BigQuery GLEIF lookup
    print("\n1a. Checking BigQuery GLEIF table...")
    bq_results = get_gleif_from_bigquery(lender_name)
    
    if bq_results:
        print_result(True, f"Found {len(bq_results)} matches in BigQuery GLEIF")
        print("\n   BigQuery GLEIF Results:")
        for i, row in enumerate(bq_results[:5], 1):
            print(f"   {i}. {row.get('gleif_legal_name', 'N/A')}")
            print(f"      LEI: {row.get('lei', 'N/A')}")
            print(f"      Direct Parent: {row.get('direct_parent_name', 'N/A')} ({row.get('direct_parent_lei', 'N/A')})")
            print(f"      Ultimate Parent: {row.get('ultimate_parent_name', 'N/A')} ({row.get('ultimate_parent_lei', 'N/A')})")
            if row.get('direct_children'):
                import json
                children = json.loads(row['direct_children']) if isinstance(row['direct_children'], str) else row['direct_children']
                if children:
                    print(f"      Direct Children: {len(children)}")
    else:
        print_result(False, "No matches in BigQuery GLEIF")
    
    try:
        resolver = IdentifierResolver()
        
        # Get candidates
        print("\n1a. Getting candidates with location...")
        candidates = resolver.get_candidates_with_location(lender_name, limit=10)
        
        if not candidates:
            print_result(False, "No candidates found")
            return None
        
        print_result(True, f"Found {len(candidates)} candidates")
        print("\n   Candidates:")
        for i, candidate in enumerate(candidates[:5], 1):
            print(f"   {i}. {candidate.get('name', 'N/A')}")
            print(f"      Location: {candidate.get('city', '')}, {candidate.get('state', '')}")
            print(f"      FDIC Cert: {candidate.get('fdic_cert', 'N/A')}")
            print(f"      RSSD ID: {candidate.get('rssd_id', 'N/A')}")
            print(f"      LEI: {candidate.get('lei', 'N/A')}")
            print(f"      Confidence: {candidate.get('confidence', 0.0):.2f}")
        
        # Use first candidate for testing
        if candidates:
            selected = candidates[0]
            print(f"\n1b. Using first candidate: {selected.get('name')}")
            
            # Get full details
            identifiers = {
                'name': selected.get('name'),
                'fdic_cert': selected.get('fdic_cert'),
                'rssd_id': selected.get('rssd_id'),
                'lei': selected.get('lei'),
                'confidence': selected.get('confidence', 0.0)
            }
            
            details = resolver.get_institution_details(identifiers)
            print_result(True, "Got institution details", details)
            
            return {
                'identifiers': identifiers,
                'details': details,
                'institution_name': selected.get('name')
            }
        
    except Exception as e:
        print_result(False, f"Error in identifier resolution: {str(e)}")
        logger.exception("Identifier resolution error")
        return None


def test_fdic_apis(identifiers: Dict[str, Any]):
    """Test Step 2: FDIC APIs."""
    print_section("STEP 2: FDIC APIs")
    
    fdic_cert = identifiers.get('fdic_cert')
    rssd_id = identifiers.get('rssd_id')
    
    if not fdic_cert and not rssd_id:
        print_result(False, "No FDIC cert or RSSD ID available")
        return {}
    
    collector = DataCollector()
    results = {}
    
    # Test FDIC Institution
    if fdic_cert:
        print(f"\n2a. Testing FDIC Institution API (Cert: {fdic_cert})...")
        try:
            data = collector._get_fdic_institution(fdic_cert)
            print_result(True, "FDIC Institution API", data)
            results['fdic_institution'] = data
        except Exception as e:
            print_result(False, f"FDIC Institution API: {str(e)}")
            logger.exception("FDIC Institution error")
    
    # Test FDIC Financials
    if fdic_cert:
        print(f"\n2b. Testing FDIC Financials API (Cert: {fdic_cert})...")
        try:
            data = collector._get_fdic_financials(fdic_cert)
            print_result(True, "FDIC Financials API", data)
            results['fdic_financials'] = data
        except Exception as e:
            print_result(False, f"FDIC Financials API: {str(e)}")
            logger.exception("FDIC Financials error")
    
    # Test FDIC Branches
    if fdic_cert:
        print(f"\n2c. Testing FDIC Branches API (Cert: {fdic_cert})...")
        try:
            data = collector._get_fdic_branches(fdic_cert)
            print_result(True, "FDIC Branches API", data)
            results['fdic_branches'] = data
        except Exception as e:
            print_result(False, f"FDIC Branches API: {str(e)}")
            logger.exception("FDIC Branches error")
    
    return results


def test_gleif_api(identifiers: Dict[str, Any]):
    """Test Step 3: GLEIF API."""
    print_section("STEP 3: GLEIF API")
    
    lei = identifiers.get('lei')
    if not lei:
        print_result(False, "No LEI available")
        return {}
    
    print(f"Testing GLEIF API (LEI: {lei})...")
    collector = DataCollector()
    
    try:
        data = collector._get_gleif_data(lei)
        print_result(True, "GLEIF API", data)
        return {'gleif': data}
    except Exception as e:
        print_result(False, f"GLEIF API: {str(e)}")
        logger.exception("GLEIF error")
        return {}


def test_sec_api(institution_name: str):
    """Test Step 4: SEC Edgar API."""
    print_section("STEP 4: SEC EDGAR API")
    
    print(f"Testing SEC API for: '{institution_name}'...")
    collector = DataCollector()
    
    try:
        data = collector._get_sec_data(institution_name)
        print_result(True, "SEC API", data)
        return {'sec': data}
    except Exception as e:
        print_result(False, f"SEC API: {str(e)}")
        logger.exception("SEC error")
        return {}


def test_courtlistener_api(institution_name: str):
    """Test Step 5: CourtListener API."""
    print_section("STEP 5: COURTLISTENER API")
    
    print(f"Testing CourtListener API for: '{institution_name}'...")
    collector = DataCollector()
    
    try:
        data = collector._get_litigation_data(institution_name)
        print_result(True, "CourtListener API", data)
        return {'litigation': data}
    except Exception as e:
        print_result(False, f"CourtListener API: {str(e)}")
        logger.exception("CourtListener error")
        return {}


def test_newsapi(institution_name: str):
    """Test Step 6: NewsAPI."""
    print_section("STEP 6: NEWSAPI")
    
    print(f"Testing NewsAPI for: '{institution_name}'...")
    collector = DataCollector()
    
    try:
        data = collector._get_news_data(institution_name)
        print_result(True, "NewsAPI", data)
        return {'news': data}
    except Exception as e:
        print_result(False, f"NewsAPI: {str(e)}")
        logger.exception("NewsAPI error")
        return {}


def test_theorg_api(institution_name: str):
    """Test Step 7: TheOrg API."""
    print_section("STEP 7: THEORG API")
    
    print(f"Testing TheOrg API for: '{institution_name}'...")
    collector = DataCollector()
    
    try:
        data = collector._get_theorg_data(institution_name)
        print_result(True, "TheOrg API", data)
        return {'theorg': data}
    except Exception as e:
        print_result(False, f"TheOrg API: {str(e)}")
        logger.exception("TheOrg error")
        return {}


def test_cfpb_apis(institution_name: str, identifiers: Dict[str, Any]):
    """Test Step 8: CFPB APIs."""
    print_section("STEP 8: CFPB APIs")
    
    rssd_id = identifiers.get('rssd_id')
    lei = identifiers.get('lei')
    
    collector = DataCollector()
    results = {}
    
    # Test CFPB Metadata (includes assets and transmittal sheet data)
    print(f"\n8a. Testing CFPB Metadata API (assets, transmittal sheet)...")
    try:
        data = collector._get_cfpb_metadata(rssd_id, lei, institution_name)
        if data:
            assets = data.get('assets') or (data.get('transmittal_sheet', {}).get('assets') if data.get('transmittal_sheet') else None)
            lar_count = data.get('transmittal_sheet', {}).get('total_lines') if data.get('transmittal_sheet') else None
            print_result(True, f"CFPB Metadata API - Assets: {assets}, LAR Count: {lar_count}", data)
        else:
            print_result(False, "CFPB Metadata API - No data returned")
        results['cfpb_metadata'] = data
    except Exception as e:
        print_result(False, f"CFPB Metadata API: {str(e)}")
        logger.exception("CFPB Metadata error")
    
    # Test CFPB Enforcement
    print(f"\n8b. Testing CFPB Enforcement (scraping)...")
    try:
        data = collector._get_enforcement_data(institution_name)
        print_result(True, "CFPB Enforcement", data)
        results['enforcement'] = data
    except Exception as e:
        print_result(False, f"CFPB Enforcement: {str(e)}")
        logger.exception("CFPB Enforcement error")
    
    # Test CFPB Complaints
    print(f"\n8c. Testing CFPB Complaints API...")
    try:
        data = collector._get_cfpb_complaints(institution_name)
        print_result(True, "CFPB Complaints API", data)
        results['cfpb_complaints'] = data
    except Exception as e:
        print_result(False, f"CFPB Complaints API: {str(e)}")
        logger.exception("CFPB Complaints error")
    
    return results


def test_ffiec_api(identifiers: Dict[str, Any]):
    """Test Step 9: FFIEC CRA API."""
    print_section("STEP 9: FFIEC CRA API")
    
    fdic_cert = identifiers.get('fdic_cert')
    if not fdic_cert:
        print_result(False, "No FDIC cert available")
        return {}
    
    print(f"Testing FFIEC CRA API (Cert: {fdic_cert})...")
    collector = DataCollector()
    
    try:
        data = collector._get_cra_data(fdic_cert)
        print_result(True, "FFIEC CRA API", data)
        return {'ffiec_cra': data}
    except Exception as e:
        print_result(False, f"FFIEC CRA API: {str(e)}")
        logger.exception("FFIEC error")
        return {}


def test_federal_reserve_api(identifiers: Dict[str, Any]):
    """Test Step 10: Federal Reserve NIC API."""
    print_section("STEP 10: FEDERAL RESERVE NIC API")
    
    rssd_id = identifiers.get('rssd_id')
    if not rssd_id:
        print_result(False, "No RSSD ID available")
        return {}
    
    print(f"Testing Federal Reserve NIC API (RSSD: {rssd_id})...")
    collector = DataCollector()
    
    try:
        data = collector._get_federal_reserve_data(rssd_id)
        print_result(True, "Federal Reserve NIC API", data)
        return {'federal_reserve': data}
    except Exception as e:
        print_result(False, f"Federal Reserve NIC API: {str(e)}")
        logger.exception("Federal Reserve error")
        return {}


def test_seeking_alpha_api(institution_name: str):
    """Test Step 11: Seeking Alpha API."""
    
    print(f"Testing Seeking Alpha API for: '{institution_name}'...")
    collector = DataCollector()
    
    try:
        data = collector._get_seeking_alpha_data(institution_name)
        print_result(True, "Seeking Alpha API", data)
        return {'seeking_alpha': data}
    except Exception as e:
        print_result(False, f"Seeking Alpha API: {str(e)}")
        logger.exception("Seeking Alpha error")
        return {}


def main():
    """Main test function."""
    if len(sys.argv) < 2:
        print("Usage: python test_all_apis.py <lender_name>")
        print("\nExample: python test_all_apis.py 'JPMorgan Chase'")
        sys.exit(1)
    
    lender_name = ' '.join(sys.argv[1:])
    
    print("\n" + "=" * 80)
    print("  LENDERPROFILE API TESTING SUITE")
    print("=" * 80)
    print(f"\nTesting all APIs for lender: '{lender_name}'")
    print("\nThis will test each API/source individually to identify what works.")
    
    # Step 1: Identifier Resolution
    resolution_result = test_identifier_resolution(lender_name)
    
    if not resolution_result:
        print("\n[FAIL] Cannot proceed without identifier resolution. Exiting.")
        sys.exit(1)
    
    identifiers = resolution_result['identifiers']
    institution_name = resolution_result['institution_name']
    
    # Collect all test results
    all_results = {
        'lender_name': lender_name,
        'resolved_name': institution_name,
        'identifiers': identifiers
    }
    
    # Step 2: FDIC APIs
    all_results.update(test_fdic_apis(identifiers))
    
    # Step 3: GLEIF API
    all_results.update(test_gleif_api(identifiers))
    
    # Step 4: SEC API
    all_results.update(test_sec_api(institution_name))
    
    # Step 5: CourtListener API
    all_results.update(test_courtlistener_api(institution_name))
    
    # Step 6: NewsAPI
    all_results.update(test_newsapi(institution_name))
    
    # Step 7: TheOrg API
    all_results.update(test_theorg_api(institution_name))
    
    # Step 8: CFPB APIs
    all_results.update(test_cfpb_apis(institution_name, identifiers))
    
    # Step 9: FFIEC API
    all_results.update(test_ffiec_api(identifiers))
    
    # Step 10: Federal Reserve API
    all_results.update(test_federal_reserve_api(identifiers))
    
    # Step 11: Seeking Alpha API
    all_results.update(test_seeking_alpha_api(institution_name))
    
    # Summary
    print_section("TEST SUMMARY")
    
    working_apis = []
    failing_apis = []
    
    api_names = {
        'fdic_institution': 'FDIC Institution',
        'fdic_financials': 'FDIC Financials',
        'fdic_branches': 'FDIC Branches',
        'gleif': 'GLEIF',
        'sec': 'SEC Edgar',
        'litigation': 'CourtListener',
        'news': 'NewsAPI',
        'theorg': 'TheOrg',
        'cfpb_metadata': 'CFPB Metadata',
        'enforcement': 'CFPB Enforcement',
        'cfpb_complaints': 'CFPB Complaints',
        'ffiec_cra': 'FFIEC CRA',
        'federal_reserve': 'Federal Reserve',
        'seeking_alpha': 'Seeking Alpha'
    }
    
    for key, name in api_names.items():
        if key in all_results and all_results[key]:
            working_apis.append(name)
        else:
            failing_apis.append(name)
    
    print(f"\n[PASS] Working APIs ({len(working_apis)}):")
    for api in working_apis:
        print(f"   - {api}")
    
    print(f"\n[FAIL] Failing/Missing APIs ({len(failing_apis)}):")
    for api in failing_apis:
        print(f"   - {api}")
    
    # Save results to file
    output_file = Path(__file__).parent / 'logs' / f'api_test_results_{lender_name.replace(" ", "_")}.json'
    output_file.parent.mkdir(exist_ok=True)
    
    # Convert to JSON-serializable format
    json_results = {}
    for key, value in all_results.items():
        if isinstance(value, (dict, list, str, int, float, bool, type(None))):
            json_results[key] = value
        else:
            json_results[key] = str(value)
    
    with open(output_file, 'w') as f:
        json.dump(json_results, f, indent=2, default=str)
    
    print(f"\n[INFO] Detailed results saved to: {output_file}")
    print("\n" + "=" * 80)


if __name__ == '__main__':
    main()

