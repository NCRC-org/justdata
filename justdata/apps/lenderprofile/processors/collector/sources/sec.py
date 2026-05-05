"""SEC EDGAR data fetcher."""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

def _get_sec_data(collector, name: str) -> Dict[str, Any]:
    """Get SEC filing data using JSON APIs."""
    try:
        companies = collector.sec_client.search_companies(name)
        if not companies:
            logger.warning(f"No SEC companies found for {name}")
            return {}

        # Try to find the best match - prefer parent holding companies for banks
        # Banks are subsidiaries; their parent holding companies have SEC filings
        best_match = None
        search_name = name.upper()

        # Extract core company name (remove "BANK", "NATIONAL ASSOCIATION", etc.)
        core_name = search_name
        for suffix in [' BANK', ' NATIONAL ASSOCIATION', ', N.A.', ', NA', ' N.A.']:
            core_name = core_name.replace(suffix, '')
        core_name = core_name.strip()

        # Holding company indicators - these have SEC filings
        holding_indicators = ['& CO', '& COMPANY', 'CORP', 'INC', 'HOLDINGS', 'FINANCIAL', 'BANCORP', 'BANCSHARES']

        # Score each company: higher = better match
        def score_company(company):
            company_name = (company.get('name') or '').upper()
            score = 0

            # Strong match if core name is in company name
            if core_name in company_name:
                score += 100

            # Prefer holding companies (they have SEC filings, executive comp, etc.)
            for indicator in holding_indicators:
                if indicator in company_name:
                    score += 50
                    break

            # Penalize if it's a bank subsidiary (not the parent)
            if ' BANK' in company_name and 'HOLDING' not in company_name and 'BANCORP' not in company_name:
                score -= 30

            # Prefer exact matches
            if search_name == company_name:
                score += 75

            return score

        # Find best match by score
        scored_companies = [(score_company(c), c) for c in companies]
        scored_companies.sort(key=lambda x: -x[0])  # Highest score first

        if scored_companies:
            best_match = scored_companies[0][1]
            logger.info(f"SEC match scores: {[(s, c.get('name')) for s, c in scored_companies[:3]]}")
        
        cik = best_match.get('cik')
        if not cik:
            logger.warning(f"No CIK found for SEC company: {best_match.get('name')}")
            return {}
        
        logger.info(f"Using SEC CIK {cik} for company: {best_match.get('name')}")
        
        # Get submissions (filing history) - also contains ticker symbol
        submissions = collector.sec_client.get_company_submissions(cik)
        if not submissions:
            logger.warning(f"No submissions found for CIK {cik}")
        
        # Extract ticker from submissions (most reliable source)
        # Prefer the main ticker (shortest, without suffix like I, A, B)
        ticker = None
        if submissions and 'tickers' in submissions:
            tickers = submissions.get('tickers', [])
            if tickers:
                # Sort tickers: prefer shorter ones without suffixes (e.g., FITB over FITBI)
                # Main trading tickers are usually the shortest
                sorted_tickers = sorted(tickers, key=lambda t: (len(t), t))
                ticker = sorted_tickers[0]
                if len(tickers) > 1:
                    logger.info(f"Multiple tickers available {tickers}, selected main ticker: {ticker}")

        # If no ticker in submissions, try to get from best_match
        if not ticker:
            ticker = best_match.get('ticker')
        
        # Get last 10-K filing for AI analysis (annual report)
        ten_k_filings = collector.sec_client.get_10k_filings(cik, limit=1)

        # Get full text content of 10-K filing for AI analysis
        ten_k_content = []
        for filing in ten_k_filings:
            accession_num = filing.get('accession_number')
            if accession_num:
                content = collector.sec_client.get_10k_filing_content(cik, accession_num)
                if content:
                    ten_k_content.append({
                        'filing_date': filing.get('date'),
                        'accession_number': accession_num,
                        'url': filing.get('url'),
                        'content': content[:500000]
                    })

        # Get last 3 10-Q filings (quarterly reports)
        # Together with 1 10-K, this covers all 4 quarters
        ten_q_filings = collector.sec_client.get_company_filings(cik, filing_type='10-Q', limit=3)
        logger.info(f"Found {len(ten_q_filings)} 10-Q filings for CIK {cik}")

        # Get 10-Q content for AI analysis
        ten_q_content = []
        for filing in ten_q_filings:
            accession_num = filing.get('accession_number')
            if accession_num:
                # Use same method as 10-K to get content
                content = collector.sec_client.get_10k_filing_content(cik, accession_num)
                if content:
                    ten_q_content.append({
                        'filing_date': filing.get('date'),
                        'accession_number': accession_num,
                        'url': filing.get('url'),
                        'content': content[:200000]  # 10-Q is shorter than 10-K
                    })

        # Get other filings list - need to fetch by type for companies with many filings
        # (e.g., JPMorgan has 21,000+ filings, DEF 14A is at index 16000+)
        filings = collector.sec_client.get_company_filings(cik, limit=100)

        # Fetch DEF 14A filings specifically (they're often buried under 424B2 prospectuses)
        def14a_filings = collector.sec_client.get_company_filings(cik, filing_type='DEF 14A', limit=5)
        if def14a_filings:
            logger.info(f"Found {len(def14a_filings)} DEF 14A filings for CIK {cik}")
        else:
            # Fallback: try filtering from general filings
            def14a_filings = [f for f in filings if 'DEF 14A' in f.get('type', '')]

        # Get XBRL financial data (this may fail for some companies)
        financials = None
        try:
            financials = collector.sec_client.parse_xbrl_financials(cik)
        except Exception as e:
            logger.debug(f"Could not parse XBRL financials for CIK {cik}: {e}")

        return {
            'cik': cik,
            'company_name': best_match.get('name'),
            'ticker': ticker,  # From submissions API (most reliable)
            'submissions': submissions,
            'filings': {
                '10k': ten_k_filings,
                '10k_content': ten_k_content,  # Full text for AI analysis
                '10q': ten_q_filings,
                '10q_content': ten_q_content,  # 10-Q content for quarterly analysis
                '8k': [f for f in filings if f.get('type') == '8-K'],
                'def14a': def14a_filings  # Fetch specifically to find buried DEF 14A filings
            },
            'financials': financials
        }
    except Exception as e:
        logger.error(f"Error getting SEC data for {name}: {e}", exc_info=True)
        return {}

