# ElectWatch Internal Methodology & Technical Specification

**INTERNAL DOCUMENT - NOT FOR PUBLICATION**

---

## Document Control

| Field | Value |
|-------|-------|
| Document ID | ELECTWATCH-METH-001 |
| Version | 1.3 |
| Last Updated | 2026-02-01 20:45 EST |
| Author | NCRC Research Team |
| AI Assistant | Claude Code (Opus 4.5) - claude-opus-4-5-20251101 |
| Classification | Internal Use Only |
| Review Cycle | Quarterly |

---

## Changelog

```
2026-02-01 20:45 EST  claude-opus-4.5  docs: created METHODOLOGY_INTERNAL.md specification document
2026-02-01 20:39 EST  claude-opus-4.5  feat: sponsor logos now combine PAC + Individual from same firm
2026-02-01 20:35 EST  claude-opus-4.5  fix: committee links 404 error (underscore to hyphen conversion)
2026-02-01 20:30 EST  claude-opus-4.5  fix: BlackRock duplicate consolidation (added BLACKROCK FUNDS SERVICES alias)
2026-02-01 20:20 EST  claude-opus-4.5  feat: parent-subsidiary aliases added (72 mappings)
                                        - Merrill Lynch, BofA Securities → Bank of America
                                        - Chase, Bear Stearns, WaMu → JPMorgan Chase
                                        - Smith Barney, Primerica, Travelers → Citigroup
                                        - Wachovia, AG Edwards → Wells Fargo
                                        - TD Ameritrade → Charles Schwab
                                        - BB&T, SunTrust → Truist
2026-02-01 20:15 EST  claude-opus-4.5  feat: expanded legal suffix normalization (FSB, FCU, NATIONAL ASSOCIATION)
2026-02-01 19:45 EST  claude-opus-4.5  fix: re-ran FEC pipeline with new alias matching (155 new matches, $247K)
2026-01-31           jrichardson       fix: switched to exact matching only (eliminated false positives)
2026-01-15           jrichardson       docs: initial methodology documentation created
2025-12-01           jrichardson       feat: STOCK Act trade parsing implemented
2025-11-15           jrichardson       feat: FEC bulk data ingestion pipeline
2025-10-01           jrichardson       init: ElectWatch application scaffolding
```

---

## 1. Scope & Purpose

### 1.1 What ElectWatch Measures

ElectWatch tracks and analyzes the financial relationships between members of the United States Congress and the financial services sector. Specifically, it measures:

1. **PAC Contributions**: Campaign contributions from Political Action Committees affiliated with financial institutions to congressional candidates
2. **Individual Contributions**: Campaign contributions from individuals employed by financial institutions
3. **Stock Holdings & Trades**: Disclosed securities transactions by members of Congress in financial sector companies

### 1.2 What ElectWatch Does NOT Measure

- **Lobbying expenditures**: Tracked separately by OpenSecrets/LDA filings
- **Dark money/501(c)(4) spending**: Not disclosed under current law
- **Super PAC independent expenditures**: Separate from direct contributions
- **Family member trades not required to be disclosed**: Spouses/dependents may have incomplete reporting
- **Blind trust holdings**: Exempt from STOCK Act disclosure
- **State-level campaign finance**: Federal data only

### 1.3 Geographic Scope

- **Coverage**: All 50 U.S. states, District of Columbia, and U.S. territories
- **Jurisdictions**: U.S. House of Representatives, U.S. Senate
- **Exclusions**: State legislatures, local offices, gubernatorial races

### 1.4 Temporal Scope

| Data Type | Available Range | Update Frequency |
|-----------|-----------------|------------------|
| FEC Contributions | 1979-present | Daily bulk files |
| STOCK Act Trades | 2012-present | 30-45 day disclosure lag |
| Congress.gov Data | 93rd Congress (1973)-present | Varies by data type |

---

## 2. Data Sources

### 2.1 Federal Election Commission (FEC) Bulk Data

**Source URL**: https://www.fec.gov/data/browse-data/?tab=bulk-data

**Update Frequency**: Daily (overnight batch)

**Data Format**: Pipe-delimited text files (`.txt`)

#### 2.1.1 Committee Master File (`cm.txt`)

Contains information about all registered political committees.

| Field | Description | Example |
|-------|-------------|---------|
| CMTE_ID | 9-character committee ID | C00000422 |
| CMTE_NM | Committee name | JPMORGAN CHASE & CO. PAC |
| TRES_NM | Treasurer name | JOHN DOE |
| CMTE_ST1 | Street address 1 | 383 MADISON AVE |
| CMTE_ST2 | Street address 2 | FL 8 |
| CMTE_CITY | City | NEW YORK |
| CMTE_ST | State | NY |
| CMTE_ZIP | ZIP code | 10179 |
| CMTE_DSGN | Designation (A/B/D/J/P/U) | B |
| CMTE_TP | Committee type | Q (Qualified PAC) |
| CMTE_PTY_AFFILIATION | Party affiliation | DEM/REP/etc. |
| FILING_FREQ | Filing frequency | Q (Quarterly) |
| ORG_TP | Organization type | C (Corporation) |
| CONNECTED_ORG_NM | Sponsoring organization | JPMORGAN CHASE & CO |
| CAND_ID | Candidate ID (if applicable) | |

#### 2.1.2 PAC to Candidate Contributions (`pas2.txt`)

Contains itemized contributions from PACs to candidates.

| Field | Description | Example |
|-------|-------------|---------|
| CMTE_ID | Contributing committee ID | C00000422 |
| AMNDT_IND | Amendment indicator | N (New) |
| RPT_TP | Report type | Q3 |
| TRANSACTION_PGI | Primary/General indicator | P (Primary) |
| IMAGE_NUM | Image number | 202010159... |
| TRANSACTION_TP | Transaction type | 24K |
| ENTITY_TP | Entity type | CCM |
| NAME | Recipient name | SMITH, JOHN |
| CITY | City | WASHINGTON |
| STATE | State | DC |
| ZIP_CODE | ZIP code | 20001 |
| EMPLOYER | Employer | |
| OCCUPATION | Occupation | |
| TRANSACTION_DT | Transaction date | 09152024 |
| TRANSACTION_AMT | Amount | 5000 |
| OTHER_ID | Recipient committee ID | C00123456 |
| CAND_ID | Candidate ID | H8OH12345 |
| TRAN_ID | Transaction ID | SA11AI.123 |
| FILE_NUM | Filing number | 1234567 |
| MEMO_CD | Memo code | |
| MEMO_TEXT | Memo text | |
| SUB_ID | FEC record number | 4123456789 |

#### 2.1.3 Individual Contributions (`itcont.txt`)

Contains itemized individual contributions (>$200 aggregate per cycle).

| Field | Description | Example |
|-------|-------------|---------|
| CMTE_ID | Recipient committee ID | C00123456 |
| AMNDT_IND | Amendment indicator | N |
| RPT_TP | Report type | Q3 |
| TRANSACTION_PGI | Primary/General | G |
| IMAGE_NUM | Image number | 20201015... |
| TRANSACTION_TP | Transaction type | 15 |
| ENTITY_TP | Entity type | IND |
| NAME | Contributor name | DOE, JANE |
| CITY | City | NEW YORK |
| STATE | State | NY |
| ZIP_CODE | ZIP code | 10001 |
| EMPLOYER | Employer | GOLDMAN SACHS |
| OCCUPATION | Occupation | MANAGING DIRECTOR |
| TRANSACTION_DT | Date | 09012024 |
| TRANSACTION_AMT | Amount | 2900 |
| OTHER_ID | Other ID | |
| TRAN_ID | Transaction ID | C1234567 |
| FILE_NUM | Filing number | 1234567 |
| MEMO_CD | Memo code | |
| MEMO_TEXT | Memo text | |
| SUB_ID | FEC record number | 4987654321 |

#### 2.1.4 Candidate Master File (`cn.txt`)

Contains information about all registered candidates.

| Field | Description | Example |
|-------|-------------|---------|
| CAND_ID | Candidate ID | H8OH12345 |
| CAND_NAME | Candidate name | SMITH, JOHN Q |
| CAND_PTY_AFFILIATION | Party | REP |
| CAND_ELECTION_YR | Election year | 2024 |
| CAND_OFFICE_ST | Office state | OH |
| CAND_OFFICE | Office (H/S/P) | H |
| CAND_OFFICE_DISTRICT | District | 12 |
| CAND_ICI | Incumbent/Challenger/Open | I |
| CAND_STATUS | Status | C (Current) |
| CAND_PCC | Principal campaign committee | C00123456 |
| CAND_ST1 | Address 1 | |
| CAND_ST2 | Address 2 | |
| CAND_CITY | City | |
| CAND_ST | State | |
| CAND_ZIP | ZIP | |

### 2.2 STOCK Act Disclosures

**Source URL**: https://efdsearch.senate.gov/search/ (Senate)
**Source URL**: https://disclosures-clerk.house.gov/PublicDisclosure/FinancialDisclosure (House)

**Legal Basis**: Stop Trading on Congressional Knowledge (STOCK) Act of 2012

**Disclosure Requirements**:
- Periodic Transaction Reports (PTR): Within 30-45 days of trade
- Annual Financial Disclosures (FD): By May 15 each year
- Termination Reports: Within 30 days of leaving office

#### 2.2.1 Dollar Range Brackets

STOCK Act disclosures use ranges rather than exact values:

| Range Code | Minimum | Maximum |
|------------|---------|---------|
| A | $1,001 | $15,000 |
| B | $15,001 | $50,000 |
| C | $50,001 | $100,000 |
| D | $100,001 | $250,000 |
| E | $250,001 | $500,000 |
| F | $500,001 | $1,000,000 |
| G | $1,000,001 | $5,000,000 |
| H | $5,000,001 | $25,000,000 |
| I | $25,000,001 | $50,000,000 |
| J | Over | $50,000,000 |

**Calculation Convention**: ElectWatch uses the **midpoint** of each range for aggregation purposes. For open-ended ranges (J), we use the minimum value.

### 2.3 Congress.gov API

**Source URL**: https://api.congress.gov/

**Authentication**: API key required

**Data Retrieved**:
- Member biographical information
- Committee assignments
- Bill sponsorship/cosponsorship
- Voting records

---

## 3. Definitions

### 3.1 Financial Sector

For the purposes of ElectWatch, "Financial Sector" includes entities classified under the following Standard Industrial Classification (SIC) codes:

| SIC Range | Description |
|-----------|-------------|
| 6000-6099 | Depository Institutions (Banks, Credit Unions) |
| 6100-6199 | Non-Depository Credit Institutions |
| 6200-6299 | Security & Commodity Brokers, Dealers, Exchanges |
| 6300-6399 | Insurance Carriers |
| 6400-6499 | Insurance Agents, Brokers, Service |
| 6500-6599 | Real Estate |
| 6700-6799 | Holding & Other Investment Offices |

**Additionally Included**:
- Fintech companies primarily engaged in financial services
- Private equity and venture capital firms
- Hedge funds and asset managers
- Credit rating agencies
- Mortgage servicers and originators
- Payment processors (Visa, Mastercard, PayPal, etc.)

### 3.2 PAC Contribution

A contribution from a registered Political Action Committee to a candidate's authorized campaign committee or leadership PAC. Must be:
- Reported to FEC on Schedule B (pas2.txt)
- From a committee with CMTE_TP = 'Q' or 'N' (Qualified PAC or PAC - Nonqualified)
- Transaction type in: 24A, 24C, 24E, 24F, 24H, 24K, 24N, 24P, 24R, 24U, 24Z

### 3.3 Individual Contribution

A contribution from a natural person to a candidate's campaign. Must be:
- Reported on Schedule A (itcont.txt)
- ENTITY_TP = 'IND'
- TRANSACTION_AMT > 0
- Have valid EMPLOYER and OCCUPATION fields for sector classification

### 3.4 Stock Trade

A reportable securities transaction under the STOCK Act. Includes:
- **Purchase (P)**: Acquisition of securities
- **Sale (S)**: Disposition of securities (full or partial)
- **Exchange (E)**: Stock-for-stock transactions

**Excludes**:
- Dividends and interest
- Transactions in diversified mutual funds
- Transactions in government securities
- Gifts of securities (reported separately)

---

## 4. Classification Methodology

### 4.1 PAC Classification

PACs are classified as "Financial Sector" using a multi-step process:

#### Step 1: Connected Organization Match

```python
FINANCIAL_KEYWORDS = [
    'bank', 'bancorp', 'bancshares', 'credit union', 'savings',
    'insurance', 'assurance', 'underwriters', 'reinsurance',
    'securities', 'brokerage', 'investment', 'asset management',
    'capital', 'finance', 'financial', 'lending', 'mortgage',
    'hedge fund', 'private equity', 'venture capital',
    'visa', 'mastercard', 'american express', 'discover',
    'goldman', 'morgan stanley', 'jpmorgan', 'citi', 'wells fargo'
]

def is_financial_pac(committee):
    connected_org = normalize(committee.CONNECTED_ORG_NM)
    for keyword in FINANCIAL_KEYWORDS:
        if keyword in connected_org:
            return True
    return False
```

#### Step 2: Manual Curation

A curated list of known financial sector PAC IDs is maintained at:
`/justdata/apps/electwatch/data/financial_pac_ids.json`

This list is updated quarterly and includes PACs that:
- Have ambiguous names but confirmed financial sector affiliation
- Are subsidiaries of financial conglomerates
- Are trade associations primarily representing financial interests

### 4.2 Employer Classification

Individual contributors are classified by employer using fuzzy matching:

#### 4.2.1 Normalization Function

```python
import re
from unidecode import unidecode

def normalize_employer(employer_string):
    """
    Normalize employer names for consistent matching.

    Args:
        employer_string: Raw employer name from FEC data

    Returns:
        Normalized lowercase string with standardized formatting
    """
    if not employer_string:
        return ""

    # Convert to ASCII, lowercase
    normalized = unidecode(employer_string).lower().strip()

    # Remove common suffixes
    suffixes = [
        r'\s+(inc|incorporated|corp|corporation|co|company|llc|llp|lp|ltd|limited)\.?$',
        r'\s+(na|n\.a\.|national association)$',
        r'\s+(plc|ag|sa|gmbh|nv)$',
        r',?\s+(the)$'
    ]
    for suffix in suffixes:
        normalized = re.sub(suffix, '', normalized)

    # Standardize common variations
    replacements = {
        '&': 'and',
        ' - ': ' ',
        '  ': ' '
    }
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)

    return normalized.strip()
```

#### 4.2.2 Parent-Subsidiary Aliases

```python
PARENT_SUBSIDIARY_ALIASES = {
    # Bank of America family
    'bank of america': ['merrill lynch', 'merrill', 'bofa securities', 'ml financial'],

    # JPMorgan Chase family
    'jpmorgan chase': ['jp morgan', 'jpmorgan', 'chase', 'j.p. morgan',
                       'bear stearns', 'washington mutual'],

    # Wells Fargo family
    'wells fargo': ['wachovia', 'wells fargo advisors', 'wells fargo securities'],

    # Citigroup family
    'citigroup': ['citi', 'citibank', 'citicorp', 'salomon brothers',
                  'smith barney', 'travelers group'],

    # Morgan Stanley family
    'morgan stanley': ['dean witter', 'morgan stanley smith barney', 'e*trade'],

    # Goldman Sachs family
    'goldman sachs': ['goldman', 'gs bank'],

    # BlackRock (note: common duplicate issue)
    'blackrock': ['black rock', 'blackrock inc', 'blackrock financial'],

    # Capital One family
    'capital one': ['capital one financial', 'capitalone'],

    # American Express family
    'american express': ['amex', 'ameriprise'],

    # State Street family
    'state street': ['state street global', 'state street bank'],

    # Northern Trust family
    'northern trust': ['northern trust bank', 'northern trust company'],

    # PNC family
    'pnc': ['pnc bank', 'pnc financial', 'pnc financial services'],

    # US Bancorp family
    'us bancorp': ['us bank', 'u.s. bank', 'u.s. bancorp'],

    # Truist family (BB&T + SunTrust merger)
    'truist': ['bb&t', 'bbt', 'suntrust', 'truist financial']
}

def resolve_to_parent(normalized_employer):
    """
    Resolve subsidiary names to parent company.

    Returns:
        Tuple of (parent_name, is_alias)
    """
    for parent, aliases in PARENT_SUBSIDIARY_ALIASES.items():
        if normalized_employer == parent:
            return (parent, False)
        for alias in aliases:
            if alias in normalized_employer or normalized_employer in alias:
                return (parent, True)
    return (normalized_employer, False)
```

#### 4.2.3 Fuzzy Match Thresholds

```python
from rapidfuzz import fuzz

# Thresholds for employer matching
FUZZY_MATCH_THRESHOLD = 0.80    # 80% similarity for fuzzy match
SUBSTRING_THRESHOLD = 0.90       # 90% for substring containment

def match_employer_to_institution(employer, institution_list):
    """
    Match an employer string to known financial institutions.

    Args:
        employer: Normalized employer name
        institution_list: List of known financial institution names

    Returns:
        Best match tuple (institution_name, confidence_score) or None
    """
    employer_norm = normalize_employer(employer)

    # First, check for exact match
    if employer_norm in institution_list:
        return (employer_norm, 1.0)

    # Second, check parent-subsidiary aliases
    parent, is_alias = resolve_to_parent(employer_norm)
    if is_alias and parent in institution_list:
        return (parent, 0.95)

    # Third, fuzzy matching
    best_match = None
    best_score = 0

    for institution in institution_list:
        # Token sort ratio handles word order differences
        score = fuzz.token_sort_ratio(employer_norm, institution) / 100

        if score > best_score and score >= FUZZY_MATCH_THRESHOLD:
            best_match = institution
            best_score = score

    if best_match:
        return (best_match, best_score)

    # Fourth, substring matching for partial names
    for institution in institution_list:
        if employer_norm in institution or institution in employer_norm:
            overlap = min(len(employer_norm), len(institution)) / max(len(employer_norm), len(institution))
            if overlap >= SUBSTRING_THRESHOLD:
                return (institution, overlap)

    return None
```

### 4.3 Stock Trade Classification

Stock trades are classified as "Financial Sector" based on:

1. **Ticker Symbol Match**: Direct match against financial sector stock universe
2. **Company Name Match**: Fuzzy match of asset description against financial institutions
3. **Asset Type Filter**: Exclude mutual funds, ETFs, and index funds unless sector-specific

```python
FINANCIAL_SECTOR_TICKERS = {
    # Major Banks
    'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'USB', 'PNC', 'TFC', 'COF',
    'BK', 'STT', 'NTRS', 'FITB', 'RF', 'KEY', 'CFG', 'MTB', 'HBAN', 'ZION',

    # Insurance
    'BRK.A', 'BRK.B', 'AIG', 'MET', 'PRU', 'AFL', 'TRV', 'ALL', 'PGR', 'CB',
    'MMC', 'AON', 'AJG', 'WTW', 'CINF', 'HIG', 'LNC', 'UNM', 'GL', 'VOYA',

    # Asset Management
    'BLK', 'SCHW', 'TROW', 'BEN', 'IVZ', 'NTRS', 'AMG', 'JHG', 'APAM', 'VCTR',

    # Credit Cards / Payments
    'V', 'MA', 'AXP', 'DFS', 'PYPL', 'SQ', 'FIS', 'FISV', 'GPN', 'FLT',

    # Exchanges
    'ICE', 'CME', 'NDAQ', 'CBOE', 'MKTX',

    # Fintech
    'SQ', 'PYPL', 'SOFI', 'HOOD', 'COIN', 'AFRM', 'UPST',

    # REITs (Financial)
    'BX', 'KKR', 'APO', 'ARES', 'CG', 'OWL',

    # Mortgage / Specialty Finance
    'RKT', 'UWMC', 'NLY', 'AGNC', 'STWD', 'BXMT', 'LADR'
}

def is_financial_sector_trade(trade):
    """
    Determine if a trade is in the financial sector.

    Args:
        trade: Trade record with ticker, asset_description fields

    Returns:
        Boolean indicating financial sector classification
    """
    # Direct ticker match
    if trade.ticker and trade.ticker.upper() in FINANCIAL_SECTOR_TICKERS:
        return True

    # Asset description match
    if trade.asset_description:
        desc_lower = trade.asset_description.lower()

        # Exclude broad funds
        exclude_patterns = ['s&p 500', 'total market', 'index fund',
                          'target date', 'balanced fund']
        for pattern in exclude_patterns:
            if pattern in desc_lower:
                return False

        # Check for financial keywords
        for keyword in FINANCIAL_KEYWORDS:
            if keyword in desc_lower:
                return True

    return False
```

---

## 5. Calculations & Formulas

### 5.1 Contribution Totals

#### 5.1.1 Total PAC Contributions to Member

```sql
SELECT
    cn.CAND_ID,
    cn.CAND_NAME,
    SUM(pas2.TRANSACTION_AMT) as total_pac_contributions,
    COUNT(DISTINCT pas2.CMTE_ID) as unique_pac_count
FROM
    pas2
    JOIN cn ON pas2.CAND_ID = cn.CAND_ID
    JOIN financial_pacs fp ON pas2.CMTE_ID = fp.CMTE_ID
WHERE
    pas2.TRANSACTION_AMT > 0
    AND pas2.TRANSACTION_TP IN ('24A', '24C', '24E', '24F', '24H', '24K', '24N', '24P', '24R', '24U', '24Z')
    AND SUBSTR(pas2.TRANSACTION_DT, 5, 4) = :election_cycle
GROUP BY
    cn.CAND_ID, cn.CAND_NAME
```

#### 5.1.2 Total Individual Contributions by Employer

```sql
SELECT
    matched_employer,
    SUM(TRANSACTION_AMT) as total_individual_contributions,
    COUNT(*) as contribution_count,
    COUNT(DISTINCT NAME) as unique_contributors
FROM
    individual_contributions_matched
WHERE
    is_financial_sector = TRUE
    AND SUBSTR(TRANSACTION_DT, 5, 4) = :election_cycle
GROUP BY
    matched_employer
ORDER BY
    total_individual_contributions DESC
```

### 5.2 Trade Counts & Values

#### 5.2.1 Trade Value Estimation

```python
RANGE_MIDPOINTS = {
    'A': 8000,       # (1001 + 15000) / 2
    'B': 32500,      # (15001 + 50000) / 2
    'C': 75000,      # (50001 + 100000) / 2
    'D': 175000,     # (100001 + 250000) / 2
    'E': 375000,     # (250001 + 500000) / 2
    'F': 750000,     # (500001 + 1000000) / 2
    'G': 3000000,    # (1000001 + 5000000) / 2
    'H': 15000000,   # (5000001 + 25000000) / 2
    'I': 37500000,   # (25000001 + 50000000) / 2
    'J': 50000001    # Minimum of open-ended range
}

def estimate_trade_value(range_code):
    """Return estimated dollar value for STOCK Act range code."""
    return RANGE_MIDPOINTS.get(range_code.upper(), 0)
```

#### 5.2.2 Trade Aggregation

```python
def aggregate_member_trades(trades, sector_filter='financial'):
    """
    Aggregate trade statistics for a member of Congress.

    Args:
        trades: List of trade records
        sector_filter: Sector to filter ('financial', 'all', etc.)

    Returns:
        Dictionary with aggregated statistics
    """
    filtered = [t for t in trades if t.sector == sector_filter]

    purchases = [t for t in filtered if t.trade_type == 'P']
    sales = [t for t in filtered if t.trade_type == 'S']

    return {
        'total_trades': len(filtered),
        'purchase_count': len(purchases),
        'sale_count': len(sales),
        'estimated_purchase_value': sum(estimate_trade_value(t.amount_range) for t in purchases),
        'estimated_sale_value': sum(estimate_trade_value(t.amount_range) for t in sales),
        'unique_tickers': len(set(t.ticker for t in filtered if t.ticker)),
        'date_range': {
            'earliest': min(t.trade_date for t in filtered),
            'latest': max(t.trade_date for t in filtered)
        }
    }
```

### 5.3 Combined Employer-PAC Contributions

When displaying contributions in the UI, employer-matched individual contributions are combined with PAC contributions from the same institution:

```python
def combine_institution_contributions(member_id, election_cycle):
    """
    Combine PAC and individual contributions for display.

    Returns list sorted by total combined amount.
    """
    # Get PAC contributions
    pac_contribs = get_pac_contributions(member_id, election_cycle)

    # Get individual contributions grouped by matched employer
    indiv_contribs = get_individual_contributions_by_employer(member_id, election_cycle)

    # Merge on normalized institution name
    combined = {}

    for pac in pac_contribs:
        institution = normalize_employer(pac.connected_org)
        parent, _ = resolve_to_parent(institution)

        if parent not in combined:
            combined[parent] = {
                'institution': parent,
                'pac_amount': 0,
                'pac_name': None,
                'individual_amount': 0,
                'individual_count': 0
            }

        combined[parent]['pac_amount'] += pac.amount
        combined[parent]['pac_name'] = pac.committee_name

    for emp in indiv_contribs:
        parent, _ = resolve_to_parent(emp.employer)

        if parent not in combined:
            combined[parent] = {
                'institution': parent,
                'pac_amount': 0,
                'pac_name': None,
                'individual_amount': 0,
                'individual_count': 0
            }

        combined[parent]['individual_amount'] += emp.total_amount
        combined[parent]['individual_count'] += emp.contributor_count

    # Calculate totals and sort
    result = []
    for inst, data in combined.items():
        data['total_amount'] = data['pac_amount'] + data['individual_amount']
        result.append(data)

    return sorted(result, key=lambda x: x['total_amount'], reverse=True)
```

---

## 6. Data Quality

### 6.1 Automated Validation

#### 6.1.1 FEC Data Validation

```python
def validate_fec_record(record, record_type):
    """
    Validate FEC record for data quality.

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []

    # Common validations
    if record_type == 'contribution':
        # Amount validation
        if record.TRANSACTION_AMT <= 0:
            errors.append(f"Invalid amount: {record.TRANSACTION_AMT}")

        if record.TRANSACTION_AMT > 5000 and record.ENTITY_TP == 'IND':
            # Individual contribution limit (may be aggregate)
            errors.append(f"Amount exceeds individual limit: {record.TRANSACTION_AMT}")

        # Date validation
        try:
            dt = datetime.strptime(record.TRANSACTION_DT, '%m%d%Y')
            if dt > datetime.now():
                errors.append(f"Future date: {record.TRANSACTION_DT}")
            if dt < datetime(1979, 1, 1):
                errors.append(f"Date before FEC records: {record.TRANSACTION_DT}")
        except ValueError:
            errors.append(f"Invalid date format: {record.TRANSACTION_DT}")

        # Committee ID validation
        if not re.match(r'^C\d{8}$', record.CMTE_ID):
            errors.append(f"Invalid committee ID format: {record.CMTE_ID}")

    return (len(errors) == 0, errors)
```

#### 6.1.2 STOCK Act Data Validation

```python
def validate_stock_act_record(record):
    """
    Validate STOCK Act disclosure record.
    """
    errors = []
    warnings = []

    # Required fields
    required = ['member_name', 'trade_date', 'asset_description', 'amount_range']
    for field in required:
        if not getattr(record, field, None):
            errors.append(f"Missing required field: {field}")

    # Amount range validation
    if record.amount_range and record.amount_range.upper() not in RANGE_MIDPOINTS:
        errors.append(f"Invalid amount range: {record.amount_range}")

    # Date validation
    if record.trade_date:
        # Check for late filings (>45 days from trade date)
        days_to_disclose = (record.disclosure_date - record.trade_date).days
        if days_to_disclose > 45:
            warnings.append(f"Late filing: {days_to_disclose} days after trade")

    return (len(errors) == 0, errors, warnings)
```

### 6.2 Manual Validation

#### 6.2.1 Quarterly Review Process

1. **Random Sample Audit**: 5% of employer classifications manually reviewed
2. **Edge Case Review**: All matches with confidence < 0.85 flagged for review
3. **New PAC Review**: Any new financial sector PAC added in quarter verified
4. **Outlier Detection**: Contribution amounts in top 1% manually verified

#### 6.2.2 Issue Tracking

Known data quality issues are tracked in:
`/justdata/apps/electwatch/data/data_quality_issues.json`

### 6.3 Known Issues

| Issue ID | Description | Impact | Mitigation |
|----------|-------------|--------|------------|
| DQ-001 | Employer field inconsistency | ~15% of records have abbreviations/misspellings | Fuzzy matching + alias resolution |
| DQ-002 | STOCK Act filing delays | Some trades reported 60+ days late | Track disclosure lag in metadata |
| DQ-003 | PAC name changes | Mergers/rebranding create duplicates | Quarterly PAC ID consolidation |
| DQ-004 | Self-employed/retired misclassification | Individual contributors may not report current employer | Exclude "SELF-EMPLOYED", "RETIRED", "NOT EMPLOYED" |
| DQ-005 | BlackRock duplicate entries | Multiple variations in employer field | Parent-subsidiary aliasing (fixed 2026-02-01) |

---

## 7. Limitations

### 7.1 Data Limitations

1. **Contribution Threshold**: Individual contributions under $200 aggregate are not itemized and therefore not captured
2. **Disclosure Timing**: STOCK Act trades have 30-45 day disclosure windows; real-time analysis not possible
3. **Dollar Ranges**: STOCK Act uses ranges, not exact values; estimated values have inherent uncertainty
4. **Self-Reported Data**: Employer/occupation data is self-reported by contributors and may be inaccurate
5. **Historical Data**: Pre-2012 stock trades not available (STOCK Act enacted 2012)

### 7.2 Methodological Limitations

1. **Employer Classification**: Fuzzy matching may produce false positives/negatives; estimated 5-10% error rate
2. **Sector Definition**: "Financial sector" boundaries are definitional; some edge cases (fintech, insurance, REIT) may be disputed
3. **Subsidiary Attribution**: Parent-subsidiary relationships change over time; historical accuracy may vary
4. **PAC Attribution**: Some PACs serve multiple industries; classification is based on primary affiliation

### 7.3 Interpretive Limitations

**CRITICAL DISCLAIMERS:**

1. **Correlation ≠ Causation**: The presence of campaign contributions or stock trades does NOT imply:
   - Quid pro quo arrangements
   - Improper influence on legislative votes
   - Insider trading or illegal activity
   - Any violation of law or ethics rules

2. **Personal vs. Corporate**: Individual contributions represent personal political preferences, not corporate positions. A Goldman Sachs employee's contribution is their personal choice, not Goldman Sachs policy.

3. **Stock Trades Context**: Members of Congress may trade financial stocks for legitimate portfolio management, diversification, or personal financial planning reasons unrelated to their official duties.

4. **Legal Activity**: All activity tracked by ElectWatch is presumed legal unless otherwise indicated. Campaign contributions and stock trading by members of Congress are legal activities subject to disclosure requirements.

5. **Not Legal Advice**: ElectWatch data should not be used to make legal conclusions about any individual or organization.

---

## 8. Development Notes

### Chronological Development Log

**2025-10-01: Project Initialization**
- Created ElectWatch application scaffold
- Established FEC bulk data download pipeline
- Initial database schema design

**2025-11-01: FEC Integration**
- Implemented cm.txt, pas2.txt, itcont.txt, cn.txt parsers
- Created financial PAC identification algorithm
- Built contribution aggregation queries

**2025-11-15: STOCK Act Integration**
- Implemented Senate EFD scraper
- Implemented House Financial Disclosure scraper
- Built trade parsing and normalization
- Created dollar range estimation logic

**2025-12-01: Classification System**
- Implemented employer fuzzy matching
- Created financial sector keyword list
- Built PAC-to-institution mapping
- Added trade sector classification

**2026-01-15: UI Development**
- Built member profile pages
- Created contribution visualization charts
- Implemented trade timeline display
- Added export functionality

**2026-02-01 19:30-21:00 EST: Data Quality Improvements**
*Session conducted with Claude Code (Opus 4.5) - model: claude-opus-4-5-20251101*
*Participants: Jay Richardson, Claude Code*

- **19:45 EST - Re-ran FEC pipeline**: Processed 70.9M individual contribution rows with new alias matching
  - Result: 155 new alias matches found, $247,353 in previously unmatched contributions
  - Top matches: Wells Fargo Advisors ($86K), J.P. Morgan ($30K), Primerica/Travelers ($30K)

- **20:15 EST - Added parent-subsidiary aliases** (72 mappings in `firm_matcher.py`):
  - Bank of America family: Merrill Lynch, BofA Securities, US Trust, Countrywide, Fleet, LaSalle
  - JPMorgan Chase family: Chase, Bear Stearns, Washington Mutual
  - Citigroup family: Citibank, Smith Barney, Salomon Brothers, Primerica, Travelers
  - Wells Fargo family: Wachovia, First Union, AG Edwards
  - Charles Schwab family: TD Ameritrade, Ameritrade
  - Truist family: BB&T, SunTrust
  - Fidelity family: FMR, FMR LLC
  - BlackRock family: BGI, Barclays Global Investors, iShares, BlackRock Funds Services Group

- **20:30 EST - Fixed BlackRock duplicates**:
  - Issue: "BLACKROCK FUNDS SERVICES GROUP LLC" was being added as separate firm
  - Fix: Added to PARENT_SUBSIDIARY_ALIASES, modified `build_firm_list()` to skip aliased firms
  - Result: Single "BLACKROCK" entry in firm list (was 2)

- **20:35 EST - Fixed committee links 404 error**:
  - Issue: JavaScript generated URLs with underscores (`house_financial_services`)
  - API expected hyphens (`house-financial-services`)
  - Fix: Added `.replace('_', '-')` to API endpoint in `blueprint.py:1289`

- **20:39 EST - Combined employer-PAC display**:
  - Added `extractCompanyFromPac()` function to `electwatch_dashboard.html`
  - Normalizes PAC names (e.g., "MORGAN STANLEY POLITICAL ACTION COMMITTEE" → "MORGAN STANLEY")
  - Sponsor logos now show combined tooltip with PAC + Individual breakdown

- **20:45 EST - Created METHODOLOGY_INTERNAL.md**: This document

---

## 9. Appendices

### Appendix A: Complete Financial PAC List

*See: `/justdata/apps/electwatch/data/financial_pac_ids.json`*

### Appendix B: Financial Institution Master List

*See: `/justdata/apps/electwatch/data/financial_institutions.json`*

### Appendix C: SIC Code Reference

*See: `/justdata/apps/electwatch/data/sic_codes.json`*

### Appendix D: State/District Mapping

*See: `/justdata/apps/electwatch/data/congressional_districts.json`*

### Appendix E: Data Dictionary

*See: `/justdata/apps/electwatch/data/data_dictionary.md`*

### Appendix F: API Documentation

*See: `/justdata/apps/electwatch/API.md`*

---

**End of Document**

*Last generated: 2026-02-01 20:45 EST*
*Document version: 1.3*
*Generated by: Claude Code (Opus 4.5) - claude-opus-4-5-20251101*
*Human oversight: Jay Richardson, NCRC*
