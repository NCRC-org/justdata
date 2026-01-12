#!/usr/bin/env python3
"""
ElectWatch Data Source Test Utility

Tests connectivity and data retrieval for all external APIs used by ElectWatch.
Run this to verify API keys are working and data is flowing correctly.

Usage:
    python test_data_sources.py --all          # Test all data sources
    python test_data_sources.py --fec          # Test FEC API only
    python test_data_sources.py --congress     # Test Congress.gov API only
    python test_data_sources.py --quiver       # Test Quiver API only
    python test_data_sources.py --finnhub      # Test Finnhub API only
    python test_data_sources.py --fmp          # Test FMP API only
    python test_data_sources.py --sec          # Test SEC EDGAR API only
    python test_data_sources.py --news         # Test NewsAPI only
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / '.env')

import requests


# ANSI color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(title: str):
    """Print a formatted section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}  {title}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")


def print_success(msg: str):
    """Print a success message."""
    print(f"{Colors.GREEN}[SUCCESS]{Colors.END} {msg}")


def print_error(msg: str):
    """Print an error message."""
    print(f"{Colors.RED}[ERROR]{Colors.END} {msg}")


def print_warning(msg: str):
    """Print a warning message."""
    print(f"{Colors.YELLOW}[WARNING]{Colors.END} {msg}")


def print_info(msg: str):
    """Print an info message."""
    print(f"{Colors.CYAN}[INFO]{Colors.END} {msg}")


def print_data(label: str, data, indent: int = 2):
    """Print formatted data."""
    prefix = " " * indent
    if isinstance(data, dict):
        print(f"{prefix}{Colors.BOLD}{label}:{Colors.END}")
        for k, v in list(data.items())[:10]:  # Limit to first 10 items
            if isinstance(v, (dict, list)):
                print(f"{prefix}  {k}: {type(v).__name__} ({len(v) if hasattr(v, '__len__') else '?'} items)")
            else:
                print(f"{prefix}  {k}: {v}")
    elif isinstance(data, list):
        print(f"{prefix}{Colors.BOLD}{label}:{Colors.END} {len(data)} items")
        for item in data[:3]:  # Show first 3 items
            if isinstance(item, dict):
                summary = {k: v for k, v in list(item.items())[:4]}
                print(f"{prefix}  - {summary}")
            else:
                print(f"{prefix}  - {item}")
        if len(data) > 3:
            print(f"{prefix}  ... and {len(data) - 3} more")
    else:
        print(f"{prefix}{Colors.BOLD}{label}:{Colors.END} {data}")


# =============================================================================
# FEC API TESTS
# =============================================================================

def test_fec_api() -> bool:
    """Test the FEC (Federal Election Commission) API."""
    print_header("FEC API (Campaign Finance)")

    api_key = os.getenv('FEC_API_KEY')
    if not api_key:
        print_error("FEC_API_KEY not found in environment")
        return False

    print_info(f"API Key: {api_key[:10]}...{api_key[-4:]}")

    base_url = "https://api.open.fec.gov/v1"
    headers = {'X-Api-Key': api_key}

    # Test 1: Search for a candidate
    print_info("Test 1: Searching for candidate 'French Hill'...")
    try:
        response = requests.get(
            f"{base_url}/candidates/search/",
            params={'name': 'French Hill', 'office': 'H'},
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if data.get('results'):
            print_success(f"Found {len(data['results'])} candidate(s)")
            candidate = data['results'][0]
            print_data("First candidate", {
                'name': candidate.get('name'),
                'candidate_id': candidate.get('candidate_id'),
                'state': candidate.get('state'),
                'party': candidate.get('party'),
                'office_full': candidate.get('office_full')
            })
            candidate_id = candidate.get('candidate_id')
        else:
            print_warning("No candidates found")
            candidate_id = None
    except Exception as e:
        print_error(f"Candidate search failed: {e}")
        return False

    # Test 2: Get contributions for a candidate
    if candidate_id:
        print_info(f"Test 2: Getting contributions for {candidate_id}...")
        try:
            response = requests.get(
                f"{base_url}/schedules/schedule_a/",
                params={
                    'candidate_id': candidate_id,
                    'per_page': 5,
                    'sort': '-contribution_receipt_amount'
                },
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if data.get('results'):
                print_success(f"Found {data.get('pagination', {}).get('count', 0)} total contributions")
                print_data("Sample contributions", data['results'][:3])
            else:
                print_warning("No contributions found")
        except Exception as e:
            print_error(f"Contributions query failed: {e}")

    # Test 3: Get PAC/Committee data
    print_info("Test 3: Searching for Wells Fargo PAC...")
    try:
        response = requests.get(
            f"{base_url}/committees/",
            params={'q': 'Wells Fargo', 'per_page': 5},
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if data.get('results'):
            print_success(f"Found {len(data['results'])} committee(s)")
            print_data("Committees", data['results'][:3])
        else:
            print_warning("No committees found")
    except Exception as e:
        print_error(f"Committee search failed: {e}")

    print_success("FEC API tests completed")
    return True


# =============================================================================
# CONGRESS.GOV API TESTS
# =============================================================================

def test_congress_api() -> bool:
    """Test the Congress.gov API."""
    print_header("Congress.gov API (Bills & Legislation)")

    api_key = os.getenv('CONGRESS_GOV_API_KEY')
    if not api_key:
        print_error("CONGRESS_GOV_API_KEY not found in environment")
        return False

    print_info(f"API Key: {api_key[:10]}...{api_key[-4:]}")

    base_url = "https://api.congress.gov/v3"

    # Test 1: Search for bills
    print_info("Test 1: Searching for 'cryptocurrency' bills...")
    try:
        response = requests.get(
            f"{base_url}/bill",
            params={
                'api_key': api_key,
                'format': 'json',
                'limit': 5
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if data.get('bills'):
            print_success(f"Found {len(data['bills'])} bills")
            print_data("Sample bills", data['bills'][:3])
        else:
            print_warning("No bills found")
    except Exception as e:
        print_error(f"Bill search failed: {e}")
        return False

    # Test 2: Get specific bill (H.R. 4763 - FIT21)
    print_info("Test 2: Getting H.R. 4763 (FIT21 Act)...")
    try:
        response = requests.get(
            f"{base_url}/bill/118/hr/4763",
            params={'api_key': api_key, 'format': 'json'},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if data.get('bill'):
            bill = data['bill']
            print_success("Bill retrieved successfully")
            print_data("Bill details", {
                'title': bill.get('title'),
                'number': bill.get('number'),
                'type': bill.get('type'),
                'originChamber': bill.get('originChamber'),
                'latestAction': bill.get('latestAction', {}).get('text', '')
            })
        else:
            print_warning("Bill not found")
    except Exception as e:
        print_error(f"Bill retrieval failed: {e}")

    # Test 3: Get members of Congress
    print_info("Test 3: Getting current members of Congress...")
    try:
        response = requests.get(
            f"{base_url}/member",
            params={'api_key': api_key, 'format': 'json', 'limit': 5, 'currentMember': 'true'},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if data.get('members'):
            print_success(f"Found members")
            print_data("Sample members", data['members'][:3])
        else:
            print_warning("No members found")
    except Exception as e:
        print_error(f"Member query failed: {e}")

    print_success("Congress.gov API tests completed")
    return True


# =============================================================================
# QUIVER API TESTS
# =============================================================================

def test_quiver_api() -> bool:
    """Test the Quiver Quantitative API (congressional trading)."""
    print_header("Quiver API (Congressional Stock Trades)")

    api_key = os.getenv('QUIVER_API_KEY')
    if not api_key:
        print_error("QUIVER_API_KEY not found in environment")
        return False

    print_info(f"API Key: {api_key[:10]}...{api_key[-4:]}")

    base_url = "https://api.quiverquant.com/beta"
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Accept': 'application/json'
    }

    # Test 1: Get live congressional trades (most reliable endpoint)
    print_info("Test 1: Getting live congressional trades...")
    try:
        response = requests.get(
            f"{base_url}/live/congresstrading",
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if data:
            print_success(f"Found {len(data)} trades")
            # Show sample with key fields
            sample = data[0] if data else {}
            print_data("Sample trade", {
                'Representative': sample.get('Representative'),
                'BioGuideID': sample.get('BioGuideID'),
                'Ticker': sample.get('Ticker'),
                'Transaction': sample.get('Transaction'),
                'Range': sample.get('Range'),
                'TransactionDate': sample.get('TransactionDate'),
                'Party': sample.get('Party'),
                'House': sample.get('House')
            })
        else:
            print_warning("No trades found")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print_error("Authentication failed - check API key")
        elif e.response.status_code == 403:
            print_error("Access forbidden - check subscription tier")
        else:
            print_error(f"HTTP error: {e}")
        return False
    except Exception as e:
        print_error(f"Request failed: {e}")
        return False

    # Test 2: Filter by politician
    print_info("Test 2: Filtering for Nancy Pelosi trades...")
    try:
        response = requests.get(
            f"{base_url}/live/congresstrading",
            headers=headers,
            params={'representative': 'Pelosi'},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if data:
            print_success(f"Found {len(data)} Pelosi trades")
            print_data("Pelosi trades", data[:3])
        else:
            print_warning("No Pelosi trades found")
    except Exception as e:
        print_warning(f"Pelosi filter query: {e}")

    # Test 3: Get trades using the ElectWatch client
    print_info("Test 3: Testing ElectWatch Quiver client integration...")
    try:
        from apps.electwatch.services.quiver_client import QuiverClient
        client = QuiverClient()

        if client.test_connection():
            print_success("ElectWatch QuiverClient connection successful")

            # Get recent trades
            trades = client.get_recent_trades(days=30)
            print_success(f"QuiverClient returned {len(trades)} recent trades")

            if trades:
                sample = trades[0]
                print_data("Normalized trade", {
                    'politician_name': sample.get('politician_name'),
                    'ticker': sample.get('ticker'),
                    'type': sample.get('type'),
                    'amount_range': sample.get('amount_range'),
                    'chamber': sample.get('chamber'),
                    'party': sample.get('party')
                })
        else:
            print_error("ElectWatch QuiverClient connection failed")
    except Exception as e:
        print_error(f"Client integration test failed: {e}")

    print_success("Quiver API tests completed")
    return True


# =============================================================================
# FINNHUB API TESTS
# =============================================================================

def test_finnhub_api() -> bool:
    """Test the Finnhub API (stock data, congressional trading, news)."""
    print_header("Finnhub API (Stock Data, Congressional Trading, News)")

    api_key = os.getenv('FINNHUB_API_KEY')
    if not api_key:
        print_error("FINNHUB_API_KEY not found in environment")
        return False

    print_info(f"API Key: {api_key[:10]}...{api_key[-4:]}")

    base_url = "https://finnhub.io/api/v1"

    # Test 1: Congressional trading
    print_info("Test 1: Getting congressional trading data...")
    try:
        response = requests.get(
            f"{base_url}/stock/congressional-trading",
            params={'token': api_key, 'symbol': 'AAPL'},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if data.get('data'):
            print_success(f"Found {len(data['data'])} congressional trades")
            print_data("Congressional trades", data['data'][:3])
        else:
            print_warning("No congressional trading data found for AAPL")
    except Exception as e:
        print_error(f"Congressional trading query failed: {e}")

    # Test 2: Company news
    print_info("Test 2: Getting company news for COIN...")
    try:
        from_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        to_date = datetime.now().strftime('%Y-%m-%d')

        response = requests.get(
            f"{base_url}/company-news",
            params={
                'token': api_key,
                'symbol': 'COIN',
                'from': from_date,
                'to': to_date
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if data:
            print_success(f"Found {len(data)} news articles")
            print_data("News articles", [{
                'headline': a.get('headline', '')[:60] + '...',
                'source': a.get('source'),
                'datetime': datetime.fromtimestamp(a.get('datetime', 0)).isoformat()
            } for a in data[:3]])
        else:
            print_warning("No news found")
    except Exception as e:
        print_error(f"News query failed: {e}")

    # Test 3: Insider trading (SEC Form 4)
    print_info("Test 3: Getting insider trading for WFC...")
    try:
        response = requests.get(
            f"{base_url}/stock/insider-transactions",
            params={'token': api_key, 'symbol': 'WFC'},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if data.get('data'):
            print_success(f"Found {len(data['data'])} insider transactions")
            print_data("Insider trades", data['data'][:3])
        else:
            print_warning("No insider trading data found")
    except Exception as e:
        print_error(f"Insider trading query failed: {e}")

    # Test 4: Stock quote
    print_info("Test 4: Getting stock quote for COIN...")
    try:
        response = requests.get(
            f"{base_url}/quote",
            params={'token': api_key, 'symbol': 'COIN'},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if data.get('c'):  # 'c' is current price
            print_success("Quote retrieved")
            print_data("COIN Quote", {
                'current_price': data.get('c'),
                'high': data.get('h'),
                'low': data.get('l'),
                'open': data.get('o'),
                'prev_close': data.get('pc')
            })
        else:
            print_warning("No quote data found")
    except Exception as e:
        print_error(f"Quote query failed: {e}")

    print_success("Finnhub API tests completed")
    return True


# =============================================================================
# FMP (FINANCIAL MODELING PREP) API TESTS
# =============================================================================

def test_fmp_api() -> bool:
    """Test the Financial Modeling Prep API (Senate/House trading, SEC filings)."""
    print_header("FMP API (Senate/House Trading, SEC Filings)")

    api_key = os.getenv('FMP_API_KEY')
    if not api_key:
        print_error("FMP_API_KEY not found in environment")
        return False

    print_info(f"API Key: {api_key[:10]}...{api_key[-4:]}")

    base_url = "https://financialmodelingprep.com/api"

    # Test 1: Senate trading
    print_info("Test 1: Getting Senate trading data...")
    try:
        response = requests.get(
            f"{base_url}/v4/senate-trading",
            params={'apikey': api_key},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if data:
            print_success(f"Found {len(data)} Senate trades")
            print_data("Senate trades", data[:3])
        else:
            print_warning("No Senate trading data found")
    except Exception as e:
        print_error(f"Senate trading query failed: {e}")

    # Test 2: House trading
    print_info("Test 2: Getting House trading data...")
    try:
        response = requests.get(
            f"{base_url}/v4/senate-trading-rss-feed",  # House trades endpoint
            params={'apikey': api_key, 'page': 0},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if data:
            print_success(f"Found {len(data)} House trades")
            print_data("House trades", data[:3])
        else:
            print_warning("No House trading data found")
    except Exception as e:
        print_error(f"House trading query failed: {e}")

    # Test 3: Stock news
    print_info("Test 3: Getting stock news for COIN...")
    try:
        response = requests.get(
            f"{base_url}/v3/stock_news",
            params={'apikey': api_key, 'tickers': 'COIN', 'limit': 5},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if data:
            print_success(f"Found {len(data)} news articles")
            print_data("News", [{
                'title': a.get('title', '')[:60] + '...',
                'site': a.get('site'),
                'publishedDate': a.get('publishedDate')
            } for a in data[:3]])
        else:
            print_warning("No news found")
    except Exception as e:
        print_error(f"News query failed: {e}")

    # Test 4: SEC filings
    print_info("Test 4: Getting SEC filings for WFC...")
    try:
        response = requests.get(
            f"{base_url}/v3/sec_filings/WFC",
            params={'apikey': api_key, 'limit': 5},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if data:
            print_success(f"Found {len(data)} SEC filings")
            print_data("SEC filings", data[:3])
        else:
            print_warning("No SEC filings found")
    except Exception as e:
        print_error(f"SEC filings query failed: {e}")

    # Test 5: Company profile
    print_info("Test 5: Getting company profile for COIN...")
    try:
        response = requests.get(
            f"{base_url}/v3/profile/COIN",
            params={'apikey': api_key},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if data:
            profile = data[0] if isinstance(data, list) else data
            print_success("Profile retrieved")
            print_data("Company profile", {
                'companyName': profile.get('companyName'),
                'symbol': profile.get('symbol'),
                'industry': profile.get('industry'),
                'sector': profile.get('sector'),
                'mktCap': profile.get('mktCap'),
                'price': profile.get('price')
            })
        else:
            print_warning("No profile found")
    except Exception as e:
        print_error(f"Profile query failed: {e}")

    print_success("FMP API tests completed")
    return True


# =============================================================================
# SEC EDGAR API TESTS
# =============================================================================

def test_sec_api() -> bool:
    """Test the SEC EDGAR API (company filings - no API key required)."""
    print_header("SEC EDGAR API (Company Filings)")

    print_info("No API key required - public endpoint")

    # SEC requires a User-Agent header
    headers = {
        'User-Agent': 'NCRC ElectWatch contact@ncrc.org',
        'Accept-Encoding': 'gzip, deflate'
    }

    # Test 1: Get company filings for Wells Fargo
    print_info("Test 1: Getting filings for Wells Fargo (CIK: 0000072971)...")
    try:
        response = requests.get(
            "https://data.sec.gov/submissions/CIK0000072971.json",
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        print_success("Company data retrieved")
        print_data("Company info", {
            'name': data.get('name'),
            'cik': data.get('cik'),
            'sic': data.get('sic'),
            'sicDescription': data.get('sicDescription'),
            'tickers': data.get('tickers'),
            'exchanges': data.get('exchanges')
        })

        filings = data.get('filings', {}).get('recent', {})
        if filings:
            forms = filings.get('form', [])[:10]
            dates = filings.get('filingDate', [])[:10]
            print_data("Recent filings", [
                {'form': f, 'date': d} for f, d in zip(forms, dates)
            ])
    except Exception as e:
        print_error(f"SEC query failed: {e}")
        return False

    # Test 2: Get Coinbase filings
    print_info("Test 2: Getting filings for Coinbase (CIK: 0001679788)...")
    try:
        response = requests.get(
            "https://data.sec.gov/submissions/CIK0001679788.json",
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        print_success("Coinbase data retrieved")
        print_data("Company info", {
            'name': data.get('name'),
            'tickers': data.get('tickers'),
            'sicDescription': data.get('sicDescription')
        })
    except Exception as e:
        print_error(f"SEC query failed: {e}")

    print_success("SEC EDGAR API tests completed")
    return True


# =============================================================================
# NEWSAPI TESTS
# =============================================================================

def test_newsapi() -> bool:
    """Test the NewsAPI with quality filtering and deduplication."""
    print_header("NewsAPI (Quality-Filtered News)")

    api_key = os.getenv('NEWSAPI_API_KEY')
    if not api_key:
        print_error("NEWSAPI_API_KEY not found in environment")
        return False

    print_info(f"API Key: {api_key[:10]}...{api_key[-4:]}")

    # Test using the NewsClient with quality filtering
    print_info("Test 1: Testing NewsClient with source quality filtering...")
    try:
        from apps.electwatch.services.news_client import NewsClient, get_source_info

        client = NewsClient()

        # Show source quality tiers
        print_info("Source Quality Tiers:")
        test_sources = ['Reuters', 'Bloomberg', 'CNBC', 'Yahoo', 'ZyCrypto']
        for source in test_sources:
            score, canonical, verified = get_source_info(source)
            status = "Verified" if verified else "Unverified"
            print(f"    {source}: Score={score} ({status})")

        # Get filtered news
        print_info("Test 2: Getting deduplicated crypto regulation news...")
        news = client.search_news('cryptocurrency regulation congress', days=7, limit=5)
        print_success(f"Found {len(news)} deduplicated articles")

        for article in news[:3]:
            coverage = article.get('coverage_count', 1)
            score = article.get('authority_score', 0)
            verified = "V" if article.get('is_verified_source') else "?"
            print(f"    [{verified}] [{score}] {article['title'][:55]}...")
            print(f"        Source: {article.get('source_canonical', article['source'])} | Coverage: {coverage}")

        # Test company news
        print_info("Test 3: Getting Wells Fargo news (quality filtered)...")
        news = client.get_company_news('Wells Fargo', days=7, limit=3)
        print_success(f"Found {len(news)} articles")
        for article in news[:3]:
            verified = "V" if article.get('is_verified_source') else "?"
            print(f"    [{verified}] {article['title'][:55]}... ({article['source']})")

    except Exception as e:
        print_error(f"NewsClient test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    print_success("NewsAPI tests completed (with quality filtering)")
    return True


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='ElectWatch Data Source Test Utility',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('--all', action='store_true', help='Test all data sources')
    parser.add_argument('--fec', action='store_true', help='Test FEC API')
    parser.add_argument('--congress', action='store_true', help='Test Congress.gov API')
    parser.add_argument('--quiver', action='store_true', help='Test Quiver API')
    parser.add_argument('--finnhub', action='store_true', help='Test Finnhub API')
    parser.add_argument('--fmp', action='store_true', help='Test FMP API')
    parser.add_argument('--sec', action='store_true', help='Test SEC EDGAR API')
    parser.add_argument('--news', action='store_true', help='Test NewsAPI')

    args = parser.parse_args()

    # If no specific tests selected, run all
    if not any([args.all, args.fec, args.congress, args.quiver,
                args.finnhub, args.fmp, args.sec, args.news]):
        args.all = True

    print(f"\n{Colors.BOLD}ElectWatch Data Source Test Utility{Colors.END}")
    print(f"Run time: {datetime.now().isoformat()}\n")

    results = {}

    if args.all or args.fec:
        results['FEC'] = test_fec_api()

    if args.all or args.congress:
        results['Congress.gov'] = test_congress_api()

    if args.all or args.quiver:
        results['Quiver'] = test_quiver_api()

    if args.all or args.finnhub:
        results['Finnhub'] = test_finnhub_api()

    if args.all or args.fmp:
        results['FMP'] = test_fmp_api()

    if args.all or args.sec:
        results['SEC EDGAR'] = test_sec_api()

    if args.all or args.news:
        results['NewsAPI'] = test_newsapi()

    # Summary
    print_header("Test Summary")

    for name, passed in results.items():
        if passed:
            print_success(f"{name}: PASSED")
        else:
            print_error(f"{name}: FAILED")

    passed_count = sum(1 for v in results.values() if v)
    total_count = len(results)

    print(f"\n{Colors.BOLD}Results: {passed_count}/{total_count} tests passed{Colors.END}")

    return 0 if all(results.values()) else 1


if __name__ == '__main__':
    sys.exit(main())
