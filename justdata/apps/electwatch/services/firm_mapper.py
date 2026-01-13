#!/usr/bin/env python3
"""
Firm-to-Industry Mapper for ElectWatch

Maps financial firms, tickers, and PAC names to industry sectors.
This is the critical component that connects contributions and stock trades to industries.

Example flow:
    "WELLS FARGO & COMPANY PAC" -> Wells Fargo -> Banking
    WFC (ticker) -> Wells Fargo -> Banking
"""

import re
import logging
from typing import Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


# =============================================================================
# AMOUNT RANGE CLASS FOR STOCK ACT BUCKETS
# =============================================================================

@dataclass
class AmountRange:
    """
    Represents an amount range from STOCK Act bucket disclosures.

    STOCK Act requires disclosure in buckets, not exact amounts.
    This class properly handles range arithmetic for accurate totals.

    Example:
        3 purchases in $10,001-$15,000 bucket = AmountRange(30003, 45000)
        Display: "$30,003-$45,000"
    """
    min_amount: float
    max_amount: float

    def __add__(self, other):
        """Add two AmountRanges together."""
        if isinstance(other, AmountRange):
            return AmountRange(
                min_amount=self.min_amount + other.min_amount,
                max_amount=self.max_amount + other.max_amount
            )
        elif isinstance(other, (int, float)):
            return AmountRange(
                min_amount=self.min_amount + other,
                max_amount=self.max_amount + other
            )
        return NotImplemented

    def __radd__(self, other):
        """Support sum() with AmountRange."""
        if other == 0:
            return self
        return self.__add__(other)

    def __str__(self):
        """Display as currency range."""
        if self.min_amount == self.max_amount:
            return f"${self.min_amount:,.0f}"
        return f"${self.min_amount:,.0f}-${self.max_amount:,.0f}"

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'min': self.min_amount,
            'max': self.max_amount,
            'display': str(self)
        }

    # STOCK Act disclosure buckets (standard ranges)
    STOCK_ACT_BUCKETS = [
        (1001, 15000),
        (15001, 50000),
        (50001, 100000),
        (100001, 250000),
        (250001, 500000),
        (500001, 1000000),
        (1000001, 5000000),  # "Over $1,000,000"
    ]

    @classmethod
    def from_bucket(cls, bucket_str: str) -> 'AmountRange':
        """
        Parse STOCK Act disclosure bucket string into AmountRange.

        Examples:
            "$1,001 - $15,000" -> AmountRange(1001, 15000)
            "$15,001 - $50,000" -> AmountRange(15001, 50000)
            "$50,001 - $100,000" -> AmountRange(50001, 100000)
            "$100,001 - $250,000" -> AmountRange(100001, 250000)
            "$250,001 - $500,000" -> AmountRange(250001, 500000)
            "$500,001 - $1,000,000" -> AmountRange(500001, 1000000)
            "Over $1,000,000" -> AmountRange(1000001, 5000000)
            "15001" (single number) -> mapped to correct bucket
        """
        bucket = bucket_str.replace(',', '').replace('$', '').strip()

        # Handle "Over $X" format
        if bucket.lower().startswith('over'):
            match = re.search(r'(\d+)', bucket)
            if match:
                min_val = int(match.group(1)) + 1
                return cls(min_val, min_val * 5)  # Estimate max as 5x min

        # Handle "X - Y" range format
        parts = re.findall(r'[\d.]+', bucket)
        if len(parts) >= 2:
            return cls(float(parts[0]), float(parts[1]))
        elif len(parts) == 1:
            # Single number - map to appropriate STOCK Act bucket
            val = float(parts[0])
            return cls._map_to_stock_act_bucket(val)

        # Default fallback
        return cls(0, 0)

    @classmethod
    def _map_to_stock_act_bucket(cls, amount: float) -> 'AmountRange':
        """Map a single amount to its STOCK Act disclosure bucket."""
        # Find which bucket this amount falls into
        for bucket_min, bucket_max in cls.STOCK_ACT_BUCKETS:
            if bucket_min <= amount <= bucket_max:
                return cls(bucket_min, bucket_max)
            # Also check if amount is exactly the lower bound (common in Quiver data)
            if amount == bucket_min or (amount > 0 and abs(amount - bucket_min) < 1):
                return cls(bucket_min, bucket_max)

        # If amount is larger than any bucket, use the largest
        if amount > 1000000:
            return cls(1000001, 5000000)

        # If amount is smaller than smallest bucket
        if 0 < amount <= 1000:
            return cls(1, 1000)

        # Fallback: treat as exact amount
        return cls(amount, amount)

    @classmethod
    def from_exact(cls, amount: float) -> 'AmountRange':
        """Create AmountRange from an exact amount (both min and max are the same)."""
        return cls(amount, amount)

    @classmethod
    def zero(cls) -> 'AmountRange':
        """Create a zero AmountRange."""
        return cls(0, 0)


# Standard STOCK Act disclosure buckets
STOCK_ACT_BUCKETS = {
    '$1,001 - $15,000': AmountRange(1001, 15000),
    '$15,001 - $50,000': AmountRange(15001, 50000),
    '$50,001 - $100,000': AmountRange(50001, 100000),
    '$100,001 - $250,000': AmountRange(100001, 250000),
    '$250,001 - $500,000': AmountRange(250001, 500000),
    '$500,001 - $1,000,000': AmountRange(500001, 1000000),
    'Over $1,000,000': AmountRange(1000001, 5000000),
}


def parse_stock_amount(trade: Dict) -> AmountRange:
    """
    Parse stock trade amount from either 'amount_range' bucket string or 'amount' value.

    Args:
        trade: Trade record dict that may contain:
            - 'amount_range': STOCK Act bucket string (e.g., "$15,001 - $50,000")
            - 'amount': Numeric amount (treated as exact or mid-point estimate)

    Returns:
        AmountRange representing the trade value
    """
    # Prefer amount_range if available (proper STOCK Act bucket)
    if 'amount_range' in trade and trade['amount_range']:
        bucket_str = trade['amount_range']
        # Check if it's a known bucket
        if bucket_str in STOCK_ACT_BUCKETS:
            return STOCK_ACT_BUCKETS[bucket_str]
        # Otherwise parse it
        return AmountRange.from_bucket(bucket_str)

    # Fall back to 'amount' field
    amount = trade.get('amount', 0)
    if amount > 0:
        # If we only have a single amount, treat it as a range estimate
        # Use +/- 25% as uncertainty
        return AmountRange(amount * 0.75, amount * 1.25)

    return AmountRange.zero()


# =============================================================================
# INDUSTRY TAXONOMY
# =============================================================================

FINANCIAL_SECTORS = {
    'banking': {
        'name': 'Banking & Depository',
        'description': 'Commercial banks, credit unions, bank holding companies',
        'color': '#1e40af',  # Blue
        'keywords': ['bank', 'bancorp', 'savings', 'credit union', 'depository'],
        'sample_officials': 45,
        'sample_total': 4200000,
    },
    'mortgage': {
        'name': 'Mortgage & Real Estate Finance',
        'description': 'Mortgage lenders, servicers, GSEs, title companies',
        'color': '#059669',  # Green
        'keywords': ['mortgage', 'home loan', 'fannie', 'freddie', 'housing'],
        'sample_officials': 32,
        'sample_total': 1800000,
    },
    'consumer_lending': {
        'name': 'Consumer Lending',
        'description': 'Credit cards, auto lending, personal loans, BNPL',
        'color': '#d97706',  # Amber
        'keywords': ['credit card', 'auto finance', 'consumer credit', 'personal loan'],
        'sample_officials': 28,
        'sample_total': 1200000,
    },
    'investment': {
        'name': 'Investment & Securities',
        'description': 'Investment banks, asset managers, hedge funds, broker-dealers',
        'color': '#7c3aed',  # Purple
        'keywords': ['securities', 'investment', 'capital', 'asset management', 'hedge fund'],
        'sample_officials': 52,
        'sample_total': 3800000,
    },
    'insurance': {
        'name': 'Insurance',
        'description': 'Life, health, property & casualty, mortgage insurance',
        'color': '#dc2626',  # Red
        'keywords': ['insurance', 'underwriter', 'reinsurance', 'casualty'],
        'sample_officials': 38,
        'sample_total': 2100000,
    },
    'crypto': {
        'name': 'Digital Assets & Crypto',
        'description': 'Exchanges, stablecoins, custody, DeFi, mining',
        'color': '#f59e0b',  # Orange
        'keywords': ['crypto', 'bitcoin', 'blockchain', 'digital asset', 'defi'],
        'sample_officials': 24,
        'sample_total': 1500000,
    },
    'fintech': {
        'name': 'Financial Technology',
        'description': 'Payments, credit bureaus, data providers',
        'color': '#06b6d4',  # Cyan
        'keywords': ['fintech', 'payment', 'credit bureau', 'paypal', 'stripe'],
        'sample_officials': 35,
        'sample_total': 1900000,
    },
    'proptech': {
        'name': 'PropTech & Real Estate Tech',
        'description': 'Real estate platforms, digital mortgages, property tech',
        'color': '#84cc16',  # Lime
        'keywords': ['proptech', 'real estate tech', 'redfin', 'opendoor', 'compass'],
        'sample_officials': 15,
        'sample_total': 500000,
    },
    'payments': {
        'name': 'Payments & Processing',
        'description': 'Payment processors, money transfer, digital wallets',
        'color': '#8b5cf6',  # Violet
        'keywords': ['payment', 'visa', 'mastercard', 'square', 'paypal', 'remittance'],
        'sample_officials': 40,
        'sample_total': 2500000,
    },
}


# =============================================================================
# FIRM DATABASE
# Maps firm names to tickers, PAC names, and industries
# =============================================================================

@dataclass
class FirmRecord:
    """Represents a financial firm with its identifiers and industry classification."""
    name: str
    ticker: Optional[str]
    pac_names: List[str]
    industries: List[str]
    subsectors: List[str] = None
    aliases: List[str] = None

    def __post_init__(self):
        if self.subsectors is None:
            self.subsectors = []
        if self.aliases is None:
            self.aliases = []


# Comprehensive mapping of major financial firms
FIRM_DATABASE: Dict[str, FirmRecord] = {
    # =========================================================================
    # BANKING
    # =========================================================================
    'wells_fargo': FirmRecord(
        name='Wells Fargo',
        ticker='WFC',
        pac_names=[
            'WELLS FARGO & COMPANY PAC',
            'WELLS FARGO BANK PAC',
            'WELLS FARGO EMPLOYEES PAC',
        ],
        industries=['banking'],
        subsectors=['commercial_bank', 'mortgage'],
        aliases=['Wells Fargo Bank', 'Wells Fargo & Co']
    ),
    'jpmorgan': FirmRecord(
        name='JPMorgan Chase',
        ticker='JPM',
        pac_names=[
            'JPMORGAN CHASE & CO. PAC',
            'JPMORGAN PAC',
            'CHASE BANK PAC',
        ],
        industries=['banking', 'investment'],
        subsectors=['commercial_bank', 'investment_bank'],
        aliases=['JP Morgan', 'Chase', 'JPMorgan Chase & Co']
    ),
    'bank_of_america': FirmRecord(
        name='Bank of America',
        ticker='BAC',
        pac_names=[
            'BANK OF AMERICA CORPORATION PAC',
            'BANK OF AMERICA PAC',
            'BOFA PAC',
        ],
        industries=['banking', 'investment'],
        subsectors=['commercial_bank'],
        aliases=['BofA', 'Bank of America Corp']
    ),
    'citigroup': FirmRecord(
        name='Citigroup',
        ticker='C',
        pac_names=[
            'CITIGROUP INC. PAC',
            'CITI PAC',
            'CITIBANK PAC',
        ],
        industries=['banking', 'investment'],
        subsectors=['commercial_bank', 'investment_bank'],
        aliases=['Citi', 'Citibank']
    ),
    'us_bank': FirmRecord(
        name='U.S. Bancorp',
        ticker='USB',
        pac_names=[
            'U.S. BANCORP PAC',
            'US BANK PAC',
        ],
        industries=['banking'],
        subsectors=['commercial_bank'],
        aliases=['US Bank', 'U.S. Bank']
    ),
    'pnc': FirmRecord(
        name='PNC Financial Services',
        ticker='PNC',
        pac_names=[
            'PNC FINANCIAL SERVICES GROUP PAC',
            'PNC BANK PAC',
        ],
        industries=['banking'],
        subsectors=['commercial_bank'],
        aliases=['PNC Bank', 'PNC Financial']
    ),
    'truist': FirmRecord(
        name='Truist Financial',
        ticker='TFC',
        pac_names=[
            'TRUIST FINANCIAL CORPORATION PAC',
            'TRUIST PAC',
            'BB&T PAC',  # Legacy
            'SUNTRUST PAC',  # Legacy
        ],
        industries=['banking'],
        subsectors=['commercial_bank'],
        aliases=['Truist', 'BB&T', 'SunTrust']
    ),
    'capital_one': FirmRecord(
        name='Capital One',
        ticker='COF',
        pac_names=[
            'CAPITAL ONE FINANCIAL CORPORATION PAC',
            'CAPITAL ONE PAC',
        ],
        industries=['banking', 'consumer_lending'],
        subsectors=['commercial_bank', 'credit_cards'],
        aliases=['Capital One Financial']
    ),
    'td_bank': FirmRecord(
        name='TD Bank',
        ticker='TD',
        pac_names=[
            'TD BANK PAC',
            'TD AMERITRADE PAC',
        ],
        industries=['banking'],
        subsectors=['commercial_bank'],
        aliases=['Toronto-Dominion Bank']
    ),
    'regions': FirmRecord(
        name='Regions Financial',
        ticker='RF',
        pac_names=[
            'REGIONS FINANCIAL CORPORATION PAC',
            'REGIONS BANK PAC',
        ],
        industries=['banking'],
        subsectors=['regional_bank'],
        aliases=['Regions Bank']
    ),
    'fifth_third': FirmRecord(
        name='Fifth Third Bank',
        ticker='FITB',
        pac_names=[
            'FIFTH THIRD BANCORP PAC',
            'FIFTH THIRD BANK PAC',
        ],
        industries=['banking'],
        subsectors=['regional_bank'],
        aliases=['Fifth Third Bancorp']
    ),
    'huntington': FirmRecord(
        name='Huntington Bancshares',
        ticker='HBAN',
        pac_names=[
            'HUNTINGTON BANCSHARES PAC',
        ],
        industries=['banking'],
        subsectors=['regional_bank'],
        aliases=['Huntington Bank']
    ),
    'key_bank': FirmRecord(
        name='KeyCorp',
        ticker='KEY',
        pac_names=[
            'KEYCORP PAC',
            'KEY BANK PAC',
        ],
        industries=['banking'],
        subsectors=['regional_bank'],
        aliases=['KeyBank']
    ),
    'citizens': FirmRecord(
        name='Citizens Financial',
        ticker='CFG',
        pac_names=[
            'CITIZENS FINANCIAL GROUP PAC',
        ],
        industries=['banking'],
        subsectors=['regional_bank'],
        aliases=['Citizens Bank']
    ),
    'm_and_t': FirmRecord(
        name='M&T Bank',
        ticker='MTB',
        pac_names=[
            'M&T BANK CORPORATION PAC',
        ],
        industries=['banking'],
        subsectors=['regional_bank'],
        aliases=['M&T Bank Corporation']
    ),
    'comerica': FirmRecord(
        name='Comerica',
        ticker='CMA',
        pac_names=[
            'COMERICA INCORPORATED PAC',
        ],
        industries=['banking'],
        subsectors=['regional_bank'],
    ),
    'zions': FirmRecord(
        name='Zions Bancorporation',
        ticker='ZION',
        pac_names=[
            'ZIONS BANCORPORATION PAC',
        ],
        industries=['banking'],
        subsectors=['regional_bank'],
    ),

    # =========================================================================
    # CREDIT UNIONS
    # =========================================================================
    'cuna': FirmRecord(
        name='Credit Union National Association',
        ticker=None,
        pac_names=[
            'CREDIT UNION NATIONAL ASSOCIATION PAC',
            'CUNA PAC',
        ],
        industries=['banking'],
        subsectors=['credit_union', 'trade_association'],
        aliases=['CUNA']
    ),
    'nafcu': FirmRecord(
        name='NAFCU',
        ticker=None,
        pac_names=[
            'NATIONAL ASSOCIATION OF FEDERALLY-INSURED CREDIT UNIONS PAC',
            'NAFCU PAC',
        ],
        industries=['banking'],
        subsectors=['credit_union', 'trade_association'],
    ),
    'navy_federal': FirmRecord(
        name='Navy Federal Credit Union',
        ticker=None,
        pac_names=[
            'NAVY FEDERAL CREDIT UNION PAC',
        ],
        industries=['banking'],
        subsectors=['credit_union'],
    ),

    # =========================================================================
    # MORTGAGE & REAL ESTATE FINANCE
    # =========================================================================
    'fannie_mae': FirmRecord(
        name='Fannie Mae',
        ticker='FNMA',
        pac_names=[
            'FANNIE MAE PAC',
            'FEDERAL NATIONAL MORTGAGE ASSOCIATION PAC',
        ],
        industries=['mortgage'],
        subsectors=['gse', 'mortgage_securitization'],
        aliases=['Federal National Mortgage Association', 'FNMA']
    ),
    'freddie_mac': FirmRecord(
        name='Freddie Mac',
        ticker='FMCC',
        pac_names=[
            'FREDDIE MAC PAC',
            'FEDERAL HOME LOAN MORTGAGE CORPORATION PAC',
        ],
        industries=['mortgage'],
        subsectors=['gse', 'mortgage_securitization'],
        aliases=['Federal Home Loan Mortgage Corporation', 'FMCC']
    ),
    'rocket': FirmRecord(
        name='Rocket Companies',
        ticker='RKT',
        pac_names=[
            'ROCKET COMPANIES PAC',
            'QUICKEN LOANS PAC',
            'ROCKET MORTGAGE PAC',
        ],
        industries=['mortgage'],
        subsectors=['mortgage_lender'],
        aliases=['Quicken Loans', 'Rocket Mortgage']
    ),
    'uwm': FirmRecord(
        name='United Wholesale Mortgage',
        ticker='UWMC',
        pac_names=[
            'UNITED WHOLESALE MORTGAGE PAC',
            'UWM PAC',
        ],
        industries=['mortgage'],
        subsectors=['mortgage_lender'],
        aliases=['UWM']
    ),
    'pennymac': FirmRecord(
        name='PennyMac',
        ticker='PFSI',
        pac_names=[
            'PENNYMAC FINANCIAL SERVICES PAC',
        ],
        industries=['mortgage'],
        subsectors=['mortgage_servicer'],
    ),
    'mr_cooper': FirmRecord(
        name='Mr. Cooper Group',
        ticker='COOP',
        pac_names=[
            'MR. COOPER GROUP PAC',
            'NATIONSTAR MORTGAGE PAC',
        ],
        industries=['mortgage'],
        subsectors=['mortgage_servicer'],
        aliases=['Nationstar']
    ),
    'freedom_mortgage': FirmRecord(
        name='Freedom Mortgage',
        ticker=None,
        pac_names=[
            'FREEDOM MORTGAGE PAC',
        ],
        industries=['mortgage'],
        subsectors=['mortgage_lender'],
    ),
    'loancare': FirmRecord(
        name='LoanCare',
        ticker=None,
        pac_names=[
            'LOANCARE PAC',
        ],
        industries=['mortgage'],
        subsectors=['mortgage_servicer'],
    ),
    'mba': FirmRecord(
        name='Mortgage Bankers Association',
        ticker=None,
        pac_names=[
            'MORTGAGE BANKERS ASSOCIATION PAC',
            'MBA PAC',
        ],
        industries=['mortgage'],
        subsectors=['trade_association'],
    ),
    'first_american': FirmRecord(
        name='First American Financial',
        ticker='FAF',
        pac_names=[
            'FIRST AMERICAN FINANCIAL CORPORATION PAC',
        ],
        industries=['mortgage'],
        subsectors=['title_insurance'],
    ),
    'fidelity_national': FirmRecord(
        name='Fidelity National Financial',
        ticker='FNF',
        pac_names=[
            'FIDELITY NATIONAL FINANCIAL PAC',
        ],
        industries=['mortgage'],
        subsectors=['title_insurance'],
    ),

    # =========================================================================
    # CONSUMER LENDING / CREDIT CARDS
    # =========================================================================
    'visa': FirmRecord(
        name='Visa',
        ticker='V',
        pac_names=[
            'VISA INC. PAC',
            'VISA PAC',
        ],
        industries=['consumer_lending', 'fintech'],
        subsectors=['credit_cards', 'payments'],
    ),
    'mastercard': FirmRecord(
        name='Mastercard',
        ticker='MA',
        pac_names=[
            'MASTERCARD INCORPORATED PAC',
            'MASTERCARD PAC',
        ],
        industries=['consumer_lending', 'fintech'],
        subsectors=['credit_cards', 'payments'],
    ),
    'american_express': FirmRecord(
        name='American Express',
        ticker='AXP',
        pac_names=[
            'AMERICAN EXPRESS COMPANY PAC',
            'AMEX PAC',
        ],
        industries=['consumer_lending'],
        subsectors=['credit_cards'],
        aliases=['Amex']
    ),
    'discover': FirmRecord(
        name='Discover Financial',
        ticker='DFS',
        pac_names=[
            'DISCOVER FINANCIAL SERVICES PAC',
        ],
        industries=['consumer_lending'],
        subsectors=['credit_cards'],
    ),
    'synchrony': FirmRecord(
        name='Synchrony Financial',
        ticker='SYF',
        pac_names=[
            'SYNCHRONY FINANCIAL PAC',
        ],
        industries=['consumer_lending'],
        subsectors=['credit_cards', 'retail_lending'],
    ),
    'ally': FirmRecord(
        name='Ally Financial',
        ticker='ALLY',
        pac_names=[
            'ALLY FINANCIAL INC. PAC',
        ],
        industries=['consumer_lending'],
        subsectors=['auto_lending'],
        aliases=['Ally Bank']
    ),

    # =========================================================================
    # INVESTMENT & SECURITIES
    # =========================================================================
    'goldman_sachs': FirmRecord(
        name='Goldman Sachs',
        ticker='GS',
        pac_names=[
            'GOLDMAN SACHS GROUP INC. PAC',
            'GOLDMAN SACHS PAC',
        ],
        industries=['investment'],
        subsectors=['investment_bank'],
    ),
    'morgan_stanley': FirmRecord(
        name='Morgan Stanley',
        ticker='MS',
        pac_names=[
            'MORGAN STANLEY PAC',
        ],
        industries=['investment'],
        subsectors=['investment_bank', 'wealth_management'],
    ),
    'blackrock': FirmRecord(
        name='BlackRock',
        ticker='BLK',
        pac_names=[
            'BLACKROCK INC. PAC',
            'BLACKROCK PAC',
        ],
        industries=['investment'],
        subsectors=['asset_manager'],
    ),
    'vanguard': FirmRecord(
        name='Vanguard',
        ticker=None,
        pac_names=[
            'VANGUARD GROUP PAC',
        ],
        industries=['investment'],
        subsectors=['asset_manager'],
    ),
    'fidelity': FirmRecord(
        name='Fidelity Investments',
        ticker=None,
        pac_names=[
            'FIDELITY INVESTMENTS PAC',
            'FMR LLC PAC',
        ],
        industries=['investment'],
        subsectors=['asset_manager', 'broker_dealer'],
    ),
    'state_street': FirmRecord(
        name='State Street',
        ticker='STT',
        pac_names=[
            'STATE STREET CORPORATION PAC',
        ],
        industries=['investment'],
        subsectors=['asset_manager', 'custody'],
    ),
    'charles_schwab': FirmRecord(
        name='Charles Schwab',
        ticker='SCHW',
        pac_names=[
            'CHARLES SCHWAB CORPORATION PAC',
        ],
        industries=['investment'],
        subsectors=['broker_dealer', 'wealth_management'],
    ),
    'raymond_james': FirmRecord(
        name='Raymond James',
        ticker='RJF',
        pac_names=[
            'RAYMOND JAMES FINANCIAL PAC',
        ],
        industries=['investment'],
        subsectors=['broker_dealer'],
    ),
    'lpl_financial': FirmRecord(
        name='LPL Financial',
        ticker='LPLA',
        pac_names=[
            'LPL FINANCIAL PAC',
        ],
        industries=['investment'],
        subsectors=['broker_dealer'],
    ),
    'interactive_brokers': FirmRecord(
        name='Interactive Brokers',
        ticker='IBKR',
        pac_names=[
            'INTERACTIVE BROKERS GROUP PAC',
        ],
        industries=['investment'],
        subsectors=['broker_dealer'],
    ),
    'citadel': FirmRecord(
        name='Citadel',
        ticker=None,
        pac_names=[
            'CITADEL LLC PAC',
        ],
        industries=['investment'],
        subsectors=['hedge_fund', 'market_maker'],
    ),
    'sifma': FirmRecord(
        name='SIFMA',
        ticker=None,
        pac_names=[
            'SECURITIES INDUSTRY AND FINANCIAL MARKETS ASSOCIATION PAC',
            'SIFMA PAC',
        ],
        industries=['investment'],
        subsectors=['trade_association'],
    ),

    # =========================================================================
    # INSURANCE
    # =========================================================================
    'metlife': FirmRecord(
        name='MetLife',
        ticker='MET',
        pac_names=[
            'METLIFE INC. PAC',
        ],
        industries=['insurance'],
        subsectors=['life_insurance'],
    ),
    'prudential': FirmRecord(
        name='Prudential Financial',
        ticker='PRU',
        pac_names=[
            'PRUDENTIAL FINANCIAL PAC',
        ],
        industries=['insurance'],
        subsectors=['life_insurance'],
    ),
    'aig': FirmRecord(
        name='AIG',
        ticker='AIG',
        pac_names=[
            'AMERICAN INTERNATIONAL GROUP PAC',
            'AIG PAC',
        ],
        industries=['insurance'],
        subsectors=['property_casualty'],
        aliases=['American International Group']
    ),
    'allstate': FirmRecord(
        name='Allstate',
        ticker='ALL',
        pac_names=[
            'ALLSTATE INSURANCE COMPANY PAC',
        ],
        industries=['insurance'],
        subsectors=['property_casualty'],
    ),
    'progressive': FirmRecord(
        name='Progressive',
        ticker='PGR',
        pac_names=[
            'PROGRESSIVE CORPORATION PAC',
        ],
        industries=['insurance'],
        subsectors=['property_casualty', 'auto_insurance'],
    ),
    'travelers': FirmRecord(
        name='Travelers',
        ticker='TRV',
        pac_names=[
            'TRAVELERS COMPANIES PAC',
        ],
        industries=['insurance'],
        subsectors=['property_casualty'],
    ),
    'chubb': FirmRecord(
        name='Chubb',
        ticker='CB',
        pac_names=[
            'CHUBB LIMITED PAC',
        ],
        industries=['insurance'],
        subsectors=['property_casualty'],
    ),
    'aflac': FirmRecord(
        name='Aflac',
        ticker='AFL',
        pac_names=[
            'AFLAC INCORPORATED PAC',
        ],
        industries=['insurance'],
        subsectors=['supplemental_insurance'],
    ),
    'namic': FirmRecord(
        name='NAMIC',
        ticker=None,
        pac_names=[
            'NATIONAL ASSOCIATION OF MUTUAL INSURANCE COMPANIES PAC',
            'NAMIC PAC',
        ],
        industries=['insurance'],
        subsectors=['trade_association'],
    ),
    'acli': FirmRecord(
        name='ACLI',
        ticker=None,
        pac_names=[
            'AMERICAN COUNCIL OF LIFE INSURERS PAC',
            'ACLI PAC',
        ],
        industries=['insurance'],
        subsectors=['trade_association'],
    ),

    # =========================================================================
    # CRYPTO / DIGITAL ASSETS
    # =========================================================================
    'coinbase': FirmRecord(
        name='Coinbase',
        ticker='COIN',
        pac_names=[
            'COINBASE GLOBAL INC PAC',
            'COINBASE PAC',
        ],
        industries=['crypto'],
        subsectors=['exchange'],
    ),
    'robinhood': FirmRecord(
        name='Robinhood',
        ticker='HOOD',
        pac_names=[
            'ROBINHOOD MARKETS INC PAC',
        ],
        industries=['crypto', 'fintech'],
        subsectors=['exchange', 'broker_dealer'],
    ),
    'microstrategy': FirmRecord(
        name='MicroStrategy',
        ticker='MSTR',
        pac_names=[
            'MICROSTRATEGY PAC',
        ],
        industries=['crypto'],
        subsectors=['holdings'],
    ),
    'block': FirmRecord(
        name='Block',
        ticker='SQ',
        pac_names=[
            'BLOCK INC PAC',
            'SQUARE PAC',
        ],
        industries=['crypto', 'fintech'],
        subsectors=['payments'],
        aliases=['Square']
    ),
    'marathon_digital': FirmRecord(
        name='Marathon Digital',
        ticker='MARA',
        pac_names=[
            'MARATHON DIGITAL HOLDINGS PAC',
        ],
        industries=['crypto'],
        subsectors=['mining'],
    ),
    'riot_platforms': FirmRecord(
        name='Riot Platforms',
        ticker='RIOT',
        pac_names=[
            'RIOT PLATFORMS PAC',
        ],
        industries=['crypto'],
        subsectors=['mining'],
    ),
    # Bitcoin ETFs
    'ibit': FirmRecord(
        name='iShares Bitcoin Trust',
        ticker='IBIT',
        pac_names=[],
        industries=['crypto'],
        subsectors=['etf'],
        aliases=['BlackRock Bitcoin ETF']
    ),
    'bito': FirmRecord(
        name='ProShares Bitcoin Strategy ETF',
        ticker='BITO',
        pac_names=[],
        industries=['crypto'],
        subsectors=['etf'],
    ),
    'gbtc': FirmRecord(
        name='Grayscale Bitcoin Trust',
        ticker='GBTC',
        pac_names=[],
        industries=['crypto'],
        subsectors=['etf'],
        aliases=['Grayscale']
    ),
    'fbtc': FirmRecord(
        name='Fidelity Wise Origin Bitcoin Fund',
        ticker='FBTC',
        pac_names=[],
        industries=['crypto'],
        subsectors=['etf'],
    ),
    'arkb': FirmRecord(
        name='ARK 21Shares Bitcoin ETF',
        ticker='ARKB',
        pac_names=[],
        industries=['crypto'],
        subsectors=['etf'],
    ),
    'circle': FirmRecord(
        name='Circle',
        ticker=None,
        pac_names=[
            'CIRCLE INTERNET FINANCIAL PAC',
        ],
        industries=['crypto'],
        subsectors=['stablecoin'],
        aliases=['USDC']
    ),
    'blockchain_association': FirmRecord(
        name='Blockchain Association',
        ticker=None,
        pac_names=[
            'BLOCKCHAIN ASSOCIATION PAC',
        ],
        industries=['crypto'],
        subsectors=['trade_association'],
    ),
    'crypto_council': FirmRecord(
        name='Crypto Council for Innovation',
        ticker=None,
        pac_names=[
            'CRYPTO COUNCIL FOR INNOVATION PAC',
        ],
        industries=['crypto'],
        subsectors=['trade_association'],
    ),
    'dcg': FirmRecord(
        name='Digital Currency Group',
        ticker=None,
        pac_names=[
            'DIGITAL CURRENCY GROUP PAC',
        ],
        industries=['crypto'],
        subsectors=['holdings'],
    ),
    'andreessen_horowitz': FirmRecord(
        name='Andreessen Horowitz',
        ticker=None,
        pac_names=[
            'ANDREESSEN HOROWITZ PAC',
            'A16Z PAC',
        ],
        industries=['crypto', 'investment'],
        subsectors=['venture_capital'],
        aliases=['a16z']
    ),

    # =========================================================================
    # FINTECH / PAYMENTS
    # =========================================================================
    'paypal': FirmRecord(
        name='PayPal',
        ticker='PYPL',
        pac_names=[
            'PAYPAL HOLDINGS INC PAC',
        ],
        industries=['fintech'],
        subsectors=['payments'],
    ),
    'stripe': FirmRecord(
        name='Stripe',
        ticker=None,
        pac_names=[
            'STRIPE INC PAC',
        ],
        industries=['fintech'],
        subsectors=['payments'],
    ),
    'intuit': FirmRecord(
        name='Intuit',
        ticker='INTU',
        pac_names=[
            'INTUIT INC PAC',
        ],
        industries=['fintech'],
        subsectors=['software'],
    ),
    'sofi': FirmRecord(
        name='SoFi',
        ticker='SOFI',
        pac_names=[
            'SOFI TECHNOLOGIES PAC',
        ],
        industries=['fintech', 'consumer_lending'],
        subsectors=['neobank', 'personal_loans'],
    ),
    'affirm': FirmRecord(
        name='Affirm',
        ticker='AFRM',
        pac_names=[
            'AFFIRM HOLDINGS PAC',
        ],
        industries=['fintech', 'consumer_lending'],
        subsectors=['bnpl'],
    ),
    'klarna': FirmRecord(
        name='Klarna',
        ticker=None,
        pac_names=[
            'KLARNA PAC',
        ],
        industries=['fintech', 'consumer_lending'],
        subsectors=['bnpl'],
    ),
    'plaid': FirmRecord(
        name='Plaid',
        ticker=None,
        pac_names=[
            'PLAID INC PAC',
        ],
        industries=['fintech'],
        subsectors=['data_aggregation'],
    ),
    'fis': FirmRecord(
        name='FIS',
        ticker='FIS',
        pac_names=[
            'FIS PAC',
            'FIDELITY NATIONAL INFORMATION SERVICES PAC',
        ],
        industries=['fintech'],
        subsectors=['payments', 'infrastructure'],
    ),
    'fiserv': FirmRecord(
        name='Fiserv',
        ticker='FI',
        pac_names=[
            'FISERV INC PAC',
        ],
        industries=['fintech'],
        subsectors=['payments', 'infrastructure'],
    ),
    'global_payments': FirmRecord(
        name='Global Payments',
        ticker='GPN',
        pac_names=[
            'GLOBAL PAYMENTS INC PAC',
        ],
        industries=['fintech'],
        subsectors=['payments'],
    ),
    'equifax': FirmRecord(
        name='Equifax',
        ticker='EFX',
        pac_names=[
            'EQUIFAX INC PAC',
        ],
        industries=['fintech'],
        subsectors=['credit_bureau'],
    ),
    'experian': FirmRecord(
        name='Experian',
        ticker='EXPN',
        pac_names=[
            'EXPERIAN PAC',
        ],
        industries=['fintech'],
        subsectors=['credit_bureau'],
    ),
    'transunion': FirmRecord(
        name='TransUnion',
        ticker='TRU',
        pac_names=[
            'TRANSUNION PAC',
        ],
        industries=['fintech'],
        subsectors=['credit_bureau'],
    ),
}


# =============================================================================
# FIRM MAPPER CLASS
# =============================================================================

class FirmMapper:
    """
    Maps firms, tickers, and PAC names to industry sectors.

    Example usage:
        mapper = FirmMapper()
        industries = mapper.get_industry_from_ticker('WFC')  # ['banking']
        industries = mapper.get_industry_from_pac('WELLS FARGO & COMPANY PAC')  # ['banking']
    """

    def __init__(self):
        self._ticker_index: Dict[str, FirmRecord] = {}
        self._pac_index: Dict[str, FirmRecord] = {}
        self._name_index: Dict[str, FirmRecord] = {}
        self._build_indexes()

    def _build_indexes(self):
        """Build lookup indexes for fast search."""
        for firm_id, firm in FIRM_DATABASE.items():
            # Index by ticker
            if firm.ticker:
                self._ticker_index[firm.ticker.upper()] = firm

            # Index by PAC names (normalized)
            for pac_name in firm.pac_names:
                normalized = self._normalize_pac_name(pac_name)
                self._pac_index[normalized] = firm

            # Index by firm name and aliases
            self._name_index[firm.name.lower()] = firm
            for alias in firm.aliases or []:
                self._name_index[alias.lower()] = firm

    def _normalize_pac_name(self, pac_name: str) -> str:
        """Normalize PAC name for matching."""
        # Remove common suffixes and normalize
        name = pac_name.upper().strip()
        name = re.sub(r'\s+(PAC|POLITICAL ACTION COMMITTEE)$', '', name)
        name = re.sub(r'\s+(INC\.?|INCORPORATED|LLC|CORP\.?|CORPORATION|CO\.?)$', '', name)
        name = re.sub(r'\s+', ' ', name)
        return name.strip()

    def get_industry_from_ticker(self, ticker: str) -> List[str]:
        """
        Get industries for a stock ticker.

        Args:
            ticker: Stock ticker symbol (e.g., 'WFC', 'COIN')

        Returns:
            List of industry codes (e.g., ['banking'], ['crypto'])
        """
        ticker = ticker.upper().strip()
        firm = self._ticker_index.get(ticker)
        if firm:
            return firm.industries
        return []

    def get_industry_from_pac(self, pac_name: str) -> List[str]:
        """
        Get industries for a PAC name.

        Args:
            pac_name: PAC name (e.g., 'WELLS FARGO & COMPANY PAC')

        Returns:
            List of industry codes
        """
        normalized = self._normalize_pac_name(pac_name)

        # Exact match
        firm = self._pac_index.get(normalized)
        if firm:
            return firm.industries

        # Fuzzy match
        firm = self._fuzzy_match_pac(normalized)
        if firm:
            return firm.industries

        return []

    def _fuzzy_match_pac(self, normalized_pac: str, threshold: float = 0.7) -> Optional[FirmRecord]:
        """Fuzzy match a PAC name to a firm."""
        best_match = None
        best_score = 0

        for pac_key, firm in self._pac_index.items():
            score = SequenceMatcher(None, normalized_pac, pac_key).ratio()
            if score > best_score and score >= threshold:
                best_score = score
                best_match = firm

        return best_match

    def get_industry_from_firm_name(self, firm_name: str) -> List[str]:
        """
        Get industries for a firm name.

        Args:
            firm_name: Firm name (e.g., 'Wells Fargo', 'Coinbase')

        Returns:
            List of industry codes
        """
        firm = self._name_index.get(firm_name.lower().strip())
        if firm:
            return firm.industries
        return []

    def get_firm_from_ticker(self, ticker: str) -> Optional[FirmRecord]:
        """Get full firm record from ticker."""
        return self._ticker_index.get(ticker.upper().strip())

    def get_firm_from_pac(self, pac_name: str) -> Optional[FirmRecord]:
        """Get full firm record from PAC name."""
        normalized = self._normalize_pac_name(pac_name)
        return self._pac_index.get(normalized) or self._fuzzy_match_pac(normalized)

    def get_firm_from_name(self, firm_name: str) -> Optional[FirmRecord]:
        """
        Get full firm record from firm name or alias.

        Searches exact matches first, then fuzzy matches.

        Args:
            firm_name: Firm name (e.g., 'JPMorgan Chase', 'JP Morgan', 'Chase')

        Returns:
            FirmRecord or None
        """
        if not firm_name:
            return None

        normalized = firm_name.lower().strip()

        # Exact match
        if normalized in self._name_index:
            return self._name_index[normalized]

        # Try without common suffixes
        cleaned = re.sub(r'\s+(inc\.?|corp\.?|co\.?|corporation|company|&\s*co\.?)$', '', normalized, flags=re.IGNORECASE)
        if cleaned in self._name_index:
            return self._name_index[cleaned]

        # Fuzzy match
        best_match = None
        best_ratio = 0.7  # Minimum threshold

        for name, firm in self._name_index.items():
            ratio = SequenceMatcher(None, normalized, name).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = firm

        return best_match

    def get_firm_pacs(self, firm_name: str) -> List[str]:
        """
        Get PAC names associated with a firm.

        Args:
            firm_name: Firm name (e.g., 'JPMorgan Chase')

        Returns:
            List of PAC names for that firm
        """
        firm = self.get_firm_from_name(firm_name)
        if firm:
            return firm.pac_names
        return []

    def get_sector_info(self, sector_code: str) -> Optional[Dict]:
        """Get sector metadata."""
        return FINANCIAL_SECTORS.get(sector_code)

    def get_all_sectors(self) -> Dict[str, Dict]:
        """Get all sector definitions."""
        return FINANCIAL_SECTORS

    def aggregate_by_industry(
        self,
        contributions: List[Dict],
        stock_trades: List[Dict]
    ) -> Dict[str, Dict]:
        """
        Aggregate financial activity by industry.

        Args:
            contributions: List of contribution records with 'source'/'pac_name' and 'amount'
            stock_trades: List of trade records with 'ticker' and 'amount'/'amount_range'

        Returns:
            Dict mapping industry codes to aggregated amounts:
            {
                'banking': {
                    'contributions': 150000,
                    'stock_trades': {'min': 37500, 'max': 62500, 'display': '$37,500-$62,500'},
                    'total': {'min': 187500, 'max': 212500, 'display': '$187,500-$212,500'},
                    'firms': ['Wells Fargo', 'JPMorgan Chase']
                },
                ...
            }

        Note: Contributions are exact amounts from FEC.
              Stock trades are ranges from STOCK Act buckets.
        """
        result = {}

        # Process contributions (exact amounts from FEC)
        for contrib in contributions:
            # Support both 'pac_name' and 'source' keys
            pac_name = contrib.get('pac_name', '') or contrib.get('source', '')
            amount = contrib.get('amount', 0)
            industries = self.get_industry_from_pac(pac_name)

            for industry in industries:
                if industry not in result:
                    result[industry] = {
                        'contributions': 0,
                        'stock_trades': AmountRange.zero(),
                        'total_contributions': 0,
                        'total_range': AmountRange.zero(),
                        'firms': set()
                    }
                result[industry]['contributions'] += amount
                result[industry]['total_contributions'] += amount

                # Track firm
                firm = self.get_firm_from_pac(pac_name)
                if firm:
                    result[industry]['firms'].add(firm.name)

        # Process stock trades (ranges from STOCK Act buckets)
        for trade in stock_trades:
            ticker = trade.get('ticker', '')
            amount_range = parse_stock_amount(trade)
            industries = self.get_industry_from_ticker(ticker)

            for industry in industries:
                if industry not in result:
                    result[industry] = {
                        'contributions': 0,
                        'stock_trades': AmountRange.zero(),
                        'total_contributions': 0,
                        'total_range': AmountRange.zero(),
                        'firms': set()
                    }
                result[industry]['stock_trades'] = result[industry]['stock_trades'] + amount_range

                # Track firm
                firm = self.get_firm_from_ticker(ticker)
                if firm:
                    result[industry]['firms'].add(firm.name)

        # Finalize results: compute totals and convert to serializable format
        for industry in result:
            contrib_amount = result[industry]['contributions']
            stock_range = result[industry]['stock_trades']

            # Total range = exact contributions + stock trade range
            total_range = AmountRange(
                min_amount=contrib_amount + stock_range.min_amount,
                max_amount=contrib_amount + stock_range.max_amount
            )
            result[industry]['total_range'] = total_range

            # Convert AmountRanges to dicts for JSON serialization
            result[industry]['stock_trades'] = stock_range.to_dict()
            result[industry]['total'] = total_range.to_dict()

            # Convert firms set to list
            result[industry]['firms'] = list(result[industry]['firms'])

        return result


# =============================================================================
# MODULE-LEVEL CONVENIENCE FUNCTIONS
# =============================================================================

_mapper = None


def get_mapper() -> FirmMapper:
    """Get singleton FirmMapper instance."""
    global _mapper
    if _mapper is None:
        _mapper = FirmMapper()
    return _mapper


def get_industry_from_ticker(ticker: str) -> List[str]:
    """Convenience function to get industry from ticker."""
    return get_mapper().get_industry_from_ticker(ticker)


def get_industry_from_pac(pac_name: str) -> List[str]:
    """Convenience function to get industry from PAC name."""
    return get_mapper().get_industry_from_pac(pac_name)


def get_sector_info(sector_code: str) -> Optional[Dict]:
    """Convenience function to get sector info."""
    return get_mapper().get_sector_info(sector_code)


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    mapper = FirmMapper()

    # Test ticker lookups
    print("=== Ticker Lookups ===")
    for ticker in ['WFC', 'COIN', 'JPM', 'V', 'BLK', 'MARA']:
        industries = mapper.get_industry_from_ticker(ticker)
        firm = mapper.get_firm_from_ticker(ticker)
        print(f"{ticker}: {industries} ({firm.name if firm else 'Unknown'})")

    print("\n=== PAC Lookups ===")
    pacs = [
        'WELLS FARGO & COMPANY PAC',
        'COINBASE GLOBAL INC PAC',
        'BLOCKCHAIN ASSOCIATION PAC',
        'VISA INC. PAC',
    ]
    for pac in pacs:
        industries = mapper.get_industry_from_pac(pac)
        firm = mapper.get_firm_from_pac(pac)
        print(f"{pac[:40]:40} -> {industries} ({firm.name if firm else 'Unknown'})")

    print("\n=== Aggregation Example (with Amount Ranges) ===")
    contributions = [
        {'source': 'WELLS FARGO & COMPANY PAC', 'amount': 100000},
        {'source': 'COINBASE GLOBAL INC PAC', 'amount': 50000},
    ]
    # Stock trades with STOCK Act bucket ranges
    stock_trades = [
        {'ticker': 'WFC', 'amount_range': '$15,001 - $50,000'},
        {'ticker': 'WFC', 'amount_range': '$15,001 - $50,000'},  # 2nd purchase in same bucket
        {'ticker': 'COIN', 'amount_range': '$50,001 - $100,000'},
    ]
    result = mapper.aggregate_by_industry(contributions, stock_trades)
    for industry, data in result.items():
        info = mapper.get_sector_info(industry)
        stock_display = data['stock_trades']['display']
        total_display = data['total']['display']
        print(f"{info['name']}:")
        print(f"  Contributions: ${data['contributions']:,} (exact)")
        print(f"  Stock Trades:  {stock_display} (range)")
        print(f"  Total:         {total_display}")
        print(f"  Firms: {', '.join(data['firms'])}")

    print("\n=== AmountRange Examples ===")
    # Demonstrate range arithmetic
    r1 = AmountRange.from_bucket('$15,001 - $50,000')
    r2 = AmountRange.from_bucket('$15,001 - $50,000')
    r3 = AmountRange.from_bucket('$15,001 - $50,000')
    total = r1 + r2 + r3
    print(f"3 purchases in $15,001-$50,000 bucket:")
    print(f"  Total range: {total}")
    print(f"  (This is NOT a midpoint estimate - it's the true min/max range)")
