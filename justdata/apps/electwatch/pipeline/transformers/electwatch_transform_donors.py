"""ElectWatch pipeline: build top_donors list per official from PAC + individual contributions."""
import logging

logger = logging.getLogger(__name__)


def _build_top_donors(coordinator):
    """Build top_donors list for each official by merging PAC and individual contributions."""
    PAC_TO_COMPANY = {
        'JPMORGAN CHASE': 'JPMorgan Chase',
        'JPMORGAN': 'JPMorgan Chase',
        'JP MORGAN': 'JPMorgan Chase',
        'BANK OF AMERICA': 'Bank of America',
        'BOFA': 'Bank of America',
        'GOLDMAN SACHS': 'Goldman Sachs',
        'MORGAN STANLEY': 'Morgan Stanley',
        'WELLS FARGO': 'Wells Fargo',
        'CITIGROUP': 'Citigroup',
        'CITI': 'Citigroup',
        'AMERICAN EXPRESS': 'American Express',
        'AMEX': 'American Express',
        'CAPITAL ONE': 'Capital One',
        'BLACKROCK': 'BlackRock',
        'CHARLES SCHWAB': 'Charles Schwab',
        'SCHWAB': 'Charles Schwab',
        'FIDELITY': 'Fidelity',
        'VANGUARD': 'Vanguard',
        'STATE STREET': 'State Street',
        'BANK OF NEW YORK': 'BNY Mellon',
        'BNY MELLON': 'BNY Mellon',
        'NORTHERN TRUST': 'Northern Trust',
        'PNC': 'PNC Bank',
        'US BANK': 'U.S. Bank',
        'U.S. BANK': 'U.S. Bank',
        'TRUIST': 'Truist',
        'TD BANK': 'TD Bank',
        'CITIZENS': 'Citizens Bank',
        'FIFTH THIRD': 'Fifth Third Bank',
        'REGIONS': 'Regions Bank',
        'HUNTINGTON': 'Huntington Bank',
        'M&T BANK': 'M&T Bank',
        'SYNCHRONY': 'Synchrony Financial',
        'DISCOVER': 'Discover Financial',
        'NAVIENT': 'Navient',
        'SALLIE MAE': 'Sallie Mae',
        'ROCKET': 'Rocket Companies',
        'QUICKEN': 'Rocket Companies',
        'UNITED WHOLESALE': 'UWM Holdings',
        'PENNYMAC': 'PennyMac',
        'MR. COOPER': 'Mr. Cooper',
        'NATIONSTAR': 'Mr. Cooper',
        'LOANCARE': 'LoanCare',
        'ALLY': 'Ally Financial',
        'COINBASE': 'Coinbase',
        'ROBINHOOD': 'Robinhood',
        'PAYPAL': 'PayPal',
        'SQUARE': 'Block Inc',
        'BLOCK INC': 'Block Inc',
        'VISA': 'Visa',
        'MASTERCARD': 'Mastercard',
        'AFLAC': 'Aflac',
        'METLIFE': 'MetLife',
        'PRUDENTIAL': 'Prudential',
        'AIG': 'AIG',
        'ALLSTATE': 'Allstate',
        'PROGRESSIVE': 'Progressive',
        'BERKSHIRE': 'Berkshire Hathaway',
    }

    TICKER_TO_COMPANY = {
        'JPM': 'JPMorgan Chase',
        'BAC': 'Bank of America',
        'GS': 'Goldman Sachs',
        'MS': 'Morgan Stanley',
        'WFC': 'Wells Fargo',
        'C': 'Citigroup',
        'AXP': 'American Express',
        'COF': 'Capital One',
        'BLK': 'BlackRock',
        'SCHW': 'Charles Schwab',
        'BK': 'BNY Mellon',
        'STT': 'State Street',
        'NTRS': 'Northern Trust',
        'PNC': 'PNC Bank',
        'USB': 'U.S. Bank',
        'TFC': 'Truist',
        'TD': 'TD Bank',
        'CFG': 'Citizens Bank',
        'FITB': 'Fifth Third Bank',
        'RF': 'Regions Bank',
        'HBAN': 'Huntington Bank',
        'MTB': 'M&T Bank',
        'SYF': 'Synchrony Financial',
        'DFS': 'Discover Financial',
        'NAVI': 'Navient',
        'RKT': 'Rocket Companies',
        'UWMC': 'UWM Holdings',
        'PFSI': 'PennyMac',
        'COOP': 'Mr. Cooper',
        'ALLY': 'Ally Financial',
        'COIN': 'Coinbase',
        'HOOD': 'Robinhood',
        'PYPL': 'PayPal',
        'SQ': 'Block Inc',
        'V': 'Visa',
        'MA': 'Mastercard',
        'AFL': 'Aflac',
        'MET': 'MetLife',
        'PRU': 'Prudential',
        'AIG': 'AIG',
        'ALL': 'Allstate',
        'PGR': 'Progressive',
        'BRK.A': 'Berkshire Hathaway',
        'BRK.B': 'Berkshire Hathaway',
    }

    def normalize_company_name(name: str) -> str:
        """Normalize a PAC or employer name to canonical company name."""
        name_upper = name.upper().strip()

        for suffix in [' PAC', ' POLITICAL ACTION', ' POLITICAL FUND', ' COMMITTEE',
                       ' INC', ' LLC', ' CORP', ' CORPORATION', ' CO', ' LTD',
                       ' & CO', ' AND CO', ' GROUP', ' HOLDINGS']:
            name_upper = name_upper.replace(suffix, '')

        name_upper = name_upper.strip()

        for key, canonical in PAC_TO_COMPANY.items():
            if key in name_upper:
                return canonical

        return name.strip()

    def get_traded_companies(official: dict) -> set:
        """Get set of canonical company names from stock trades."""
        traded = set()
        for trade in official.get('trades', []):
            ticker = trade.get('ticker', '').upper()
            if ticker in TICKER_TO_COMPANY:
                traded.add(TICKER_TO_COMPANY[ticker])
            company = trade.get('company', '')
            if company:
                canonical = normalize_company_name(company)
                traded.add(canonical)
        return traded

    for official in coordinator.officials_data:
        traded_companies = get_traded_companies(official)

        company_totals = {}

        for pac in official.get('top_financial_pacs', []):
            pac_name = pac.get('name', '')
            amount = pac.get('amount', 0)
            canonical = normalize_company_name(pac_name)

            if canonical not in company_totals:
                company_totals[canonical] = {
                    'name': canonical,
                    'pac_amount': 0,
                    'individual_amount': 0,
                    'total': 0,
                    'stock_overlap': False
                }
            company_totals[canonical]['pac_amount'] += amount
            company_totals[canonical]['total'] += amount

        for employer in official.get('individual_financial_by_employer', []):
            employer_name = employer.get('employer', '')
            amount = employer.get('total', 0)
            canonical = normalize_company_name(employer_name)

            if canonical not in company_totals:
                company_totals[canonical] = {
                    'name': canonical,
                    'pac_amount': 0,
                    'individual_amount': 0,
                    'total': 0,
                    'stock_overlap': False
                }
            company_totals[canonical]['individual_amount'] += amount
            company_totals[canonical]['total'] += amount

        for company, data in company_totals.items():
            if company in traded_companies:
                data['stock_overlap'] = True

        sorted_donors = sorted(
            company_totals.values(),
            key=lambda x: x['total'],
            reverse=True
        )[:5]

        official['top_donors'] = sorted_donors

        overlap_count = sum(1 for d in sorted_donors if d.get('stock_overlap'))
        if overlap_count > 0:
            logger.debug(f"  {official.get('name')}: {overlap_count} contribution/stock overlaps")

