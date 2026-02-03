# ElectWatch Methodology Documentation

**Classification:** INTERNAL - NOT FOR PUBLICATION

---

## 1. DOCUMENT CONTROL

| Field | Value |
|-------|-------|
| **Version** | 1.1.0 |
| **Status** | DRAFT |
| **Created** | 2026-02-01 |
| **Last Modified** | 2026-02-02 03:45 EST |
| **Author** | Jay Richardson |
| **Maintainer** | Claude (automated updates) |
| **AI Model** | Claude Opus 4.5 (claude-opus-4-5-20251101) |
| **Interface** | Claude.ai with Claude Code agent |

### Review & Approval Tracking

| Date | Reviewer | Action | Notes |
|------|----------|--------|-------|
| 2026-02-01 | Jay Richardson | Created | Initial draft |

---

## 2. CHANGELOG

### [1.1.0] - 2026-02-02

#### Added
- Documentation Standards section (methodology for maintaining this document)
- Model attribution and timestamp tracking
- Cross-project documentation framework reference

#### Changed
- Document control updated with AI model information
- Added maintenance protocol for Claude instances

---

### [1.0.0] - 2026-02-01

#### Added
- Initial methodology documentation
- Complete data source specifications (FEC, STOCK Act, Congress.gov, Bioguide)
- PAC classification methodology (441 verified organizations)
- Employer matching algorithm specification
- Official profile page redesign documentation
- Sub-sector taxonomy (BANK, MORT, CONS, INVT, INSR, CRYP, FNTC, PROP, PYMT)

#### Decisions
- **Decision:** Use exact-match only for employer classification (no fuzzy matching)
  - **Rationale:** False positives are worse than false negatives for advocacy research. Every claim of financial sector influence must be defensible.
  - **Date:** 2026-01-31

- **Decision:** Classify employers only if verifiable through PAC-connected organization data
  - **Rationale:** Provides clear provenance—every match traces to a classified PAC
  - **Date:** 2026-01-31

- **Decision:** Official profile page shows financial sector data only (no all-sector totals in primary cards)
  - **Rationale:** ElectWatch's purpose is tracking financial sector influence specifically
  - **Date:** 2026-02-01

---

## 3. SCOPE & PURPOSE

### What ElectWatch Measures

ElectWatch tracks **financial sector influence** on members of the United States Congress through three data dimensions:

1. **PAC Contributions** — Direct contributions from financial sector Political Action Committees to candidate committees
2. **Individual Contributions** — Contributions from employees of financial sector firms (employer-identified)
3. **Stock Trades** — STOCK Act disclosures of trades in financial sector securities

### What ElectWatch Does NOT Measure

- **Lobbying expenditures** — Not included (separate disclosure regime)
- **Independent expenditures** — Not included (Super PAC spending)
- **Dark money** — 501(c)(4) spending not attributable
- **State/local officials** — Federal officials only
- **Personal investments** — Only disclosed trades, not total holdings
- **Contributions below $200** — Not itemized in FEC data
- **Non-financial sector influence** — Other industries excluded

### Geographic Scope

**Federal officials only:**
- U.S. Senate (100 members)
- U.S. House of Representatives (435 members)
- Non-voting delegates excluded

### Temporal Scope

| Data Type | Date Range | Update Frequency |
|-----------|------------|------------------|
| PAC Contributions | 2019-2024 election cycles | Weekly (FEC bulk) |
| Individual Contributions | 2019-2024 election cycles | Weekly (FEC bulk) |
| Stock Trades | 2012-present | Daily (STOCK Act) |
| Committee Assignments | 118th Congress | As updated |

---

## 4. DATA SOURCES

### 4.1 FEC Bulk Data Files

**Administering Agency:** Federal Election Commission
**Legal Authority:** Federal Election Campaign Act (52 U.S.C. § 30101 et seq.)
**Bulk Data URL:** https://www.fec.gov/data/browse-data/?tab=bulk-data
**Authentication:** None required
**Rate Limits:** None for bulk downloads
**Data Format:** Pipe-delimited text files
**Update Frequency:** Weekly (typically Sunday night)

#### cm.txt — Committee Master File

| Field | Description |
|-------|-------------|
| `CMTE_ID` | Committee ID (e.g., C00000935) |
| `CMTE_NM` | Committee name |
| `TRES_NM` | Treasurer name |
| `CMTE_ST1`, `CMTE_ST2` | Street address |
| `CMTE_CITY`, `CMTE_ST`, `CMTE_ZIP` | City, state, ZIP |
| `CMTE_DSGN` | Designation (A=Authorized, B=Lobbyist, etc.) |
| `CMTE_TP` | Type (H=House, S=Senate, P=Presidential, Q=PAC) |
| `CMTE_PTY_AFFILIATION` | Party affiliation |
| `FILING_FREQ` | Filing frequency |
| `ORG_TP` | Organization type (C=Corporation, L=Labor, etc.) |
| `CONNECTED_ORG_NM` | Connected organization name |
| `CAND_ID` | Candidate ID (if authorized committee) |

**Known Limitations:**
- Connected organization names are free-text, not standardized
- Some PACs have blank or generic connected org names
- Historical data may have inconsistent formatting

#### pas2.txt — Contributions from Committees to Candidates

| Field | Description |
|-------|-------------|
| `CMTE_ID` | Contributing committee ID |
| `AMNDT_IND` | Amendment indicator |
| `RPT_TP` | Report type |
| `TRANSACTION_PGI` | Primary/General indicator |
| `IMAGE_NUM` | Image number |
| `TRANSACTION_TP` | Transaction type (24K=contribution) |
| `ENTITY_TP` | Entity type |
| `NAME` | Contributor name |
| `CITY`, `STATE`, `ZIP_CODE` | Address |
| `EMPLOYER`, `OCCUPATION` | Employment info |
| `TRANSACTION_DT` | Transaction date (MMDDYYYY) |
| `TRANSACTION_AMT` | Amount in dollars |
| `OTHER_ID` | Other committee ID |
| `CAND_ID` | Receiving candidate ID |
| `TRAN_ID` | Transaction ID |
| `FILE_NUM` | Filing number |
| `MEMO_CD`, `MEMO_TEXT` | Memo fields |
| `SUB_ID` | Submission ID |

**Known Limitations:**
- Duplicate transactions possible across amendments
- Some transactions are earmarked (pass-through)
- Refunds appear as negative amounts

#### itcont.txt — Individual Contributions

| Field | Description |
|-------|-------------|
| `CMTE_ID` | Receiving committee ID |
| `AMNDT_IND` | Amendment indicator |
| `RPT_TP` | Report type |
| `TRANSACTION_PGI` | Primary/General indicator |
| `IMAGE_NUM` | Image number |
| `TRANSACTION_TP` | Transaction type |
| `ENTITY_TP` | Entity type (IND=Individual) |
| `NAME` | Contributor name |
| `CITY`, `STATE`, `ZIP_CODE` | Address |
| `EMPLOYER` | Self-reported employer |
| `OCCUPATION` | Self-reported occupation |
| `TRANSACTION_DT` | Transaction date |
| `TRANSACTION_AMT` | Amount |
| `OTHER_ID` | Conduit committee ID |
| `TRAN_ID` | Transaction ID |
| `FILE_NUM` | Filing number |
| `MEMO_CD`, `MEMO_TEXT` | Memo fields |
| `SUB_ID` | Submission ID |

**Known Limitations:**
- **CRITICAL:** Employer field is self-reported, free-text, not validated
- Contributions under $200 aggregate not itemized
- Common entries: "RETIRED", "SELF-EMPLOYED", "HOMEMAKER", "NOT EMPLOYED"
- Employer names highly variable (abbreviations, misspellings, subsidiaries)
- ~58 million records total

#### cn.txt — Candidate Master File

| Field | Description |
|-------|-------------|
| `CAND_ID` | Candidate ID |
| `CAND_NAME` | Candidate name (LAST, FIRST) |
| `CAND_PTY_AFFILIATION` | Party |
| `CAND_ELECTION_YR` | Election year |
| `CAND_OFFICE_ST` | Office state |
| `CAND_OFFICE` | Office (H/S/P) |
| `CAND_OFFICE_DISTRICT` | District (House only) |
| `CAND_ICI` | Incumbent/Challenger/Open |
| `CAND_STATUS` | Status |
| `CAND_PCC` | Principal campaign committee ID |
| `CAND_ST1`, `CAND_ST2` | Address |
| `CAND_CITY`, `CAND_ST`, `CAND_ZIP` | City, state, ZIP |

### 4.2 STOCK Act Disclosures

**Administering Agencies:**
- House: Office of the Clerk
- Senate: Secretary of the Senate

**Legal Authority:** STOCK Act (Pub.L. 112–105)
**Data Source:** Periodic Transaction Reports (PTRs)
**Format:** PDF filings, parsed to structured data
**Update Frequency:** Filed within 45 days of trade

**Fields Captured:**

| Field | Description |
|-------|-------------|
| `official_name` | Member name |
| `transaction_date` | Date of trade |
| `ticker` | Stock ticker symbol |
| `asset_description` | Security description |
| `type` | Transaction type (purchase/sale) |
| `amount` | Value range (e.g., "$1,001 - $15,000") |
| `owner` | Owner (self, spouse, dependent) |

**Known Limitations:**
- Amounts reported as ranges, not exact values
- Filing delays (up to 45 days, extensions possible)
- Some filings are late or amended
- Mutual funds and diversified ETFs often exempt
- PDF parsing may introduce errors

### 4.3 Congress.gov API

**Administering Agency:** Library of Congress
**API Endpoint:** https://api.congress.gov/v3/
**Authentication:** API key required
**Rate Limits:** 5,000 requests/hour
**Data Format:** JSON

**Endpoints Used:**

| Endpoint | Purpose |
|----------|---------|
| `/member` | Member biographical data |
| `/member/{bioguideId}` | Individual member details |
| `/committee` | Committee listings |
| `/member/{bioguideId}/sponsored-legislation` | Sponsored bills |

**Known Limitations:**
- Committee assignment history may be incomplete
- Some biographical data outdated

### 4.4 Bioguide

**Administering Agency:** Office of the Historian, U.S. House of Representatives
**URL:** https://bioguide.congress.gov/
**Data Format:** JSON API

**Fields Used:**
- Bioguide ID (canonical identifier)
- Official photo URL
- Birth date, birthplace
- Party history
- Service dates

### 4.5 SEC EDGAR

**Administering Agency:** Securities and Exchange Commission
**URL:** https://www.sec.gov/cgi-bin/browse-edgar
**Purpose:** Company SIC code lookup for stock classification

**Known Limitations:**
- SIC codes may not reflect current business mix
- Some tickers map to multiple entities

---

## 5. DEFINITIONS

### 5.1 Financial Sector

**Definition:** Organizations whose primary business activity falls within the financial services industry as defined by SIC codes 6000-6799.

**SIC Code Ranges:**

| Range | Description | Included |
|-------|-------------|----------|
| 6000-6099 | Depository Institutions | Yes |
| 6100-6199 | Non-Depository Credit | Yes |
| 6200-6299 | Security & Commodity Brokers | Yes |
| 6300-6399 | Insurance Carriers | Yes |
| 6400-6499 | Insurance Agents & Brokers | Yes |
| 6500-6599 | Real Estate | Yes |
| 6600-6699 | Combined Real Estate/Insurance | Yes |
| 6700-6799 | Holding & Investment Offices | Yes |

**Explicitly Excluded:**
- Government-sponsored enterprises acting as regulators
- Non-profit credit counseling organizations
- Academic institutions studying finance
- Government agencies (FDIC, OCC, Federal Reserve as regulator)

### 5.2 Sub-Sector Taxonomy

| Code | Name | Description | Examples |
|------|------|-------------|----------|
| `BANK` | Banking | Commercial/retail banks, thrifts | JPMorgan, Bank of America, Wells Fargo |
| `MORT` | Mortgage | Mortgage lenders, servicers | Rocket Mortgage, United Wholesale |
| `CONS` | Consumer Finance | Consumer lending, credit cards | Capital One, Synchrony |
| `INVT` | Investment | Asset management, investment advisors | BlackRock, Vanguard, Fidelity |
| `INSR` | Insurance | All insurance types | State Farm, Allstate, MetLife |
| `CRYP` | Crypto | Cryptocurrency exchanges, firms | Coinbase, FTX (historical) |
| `FNTC` | Fintech | Financial technology | Square, Stripe, PayPal |
| `PROP` | Real Estate | REITs, real estate finance | Blackstone RE, CBRE |
| `PYMT` | Payments | Payment processors, networks | Visa, Mastercard, Amex |
| `INVB` | Investment Banking | Investment banks, securities underwriting | Goldman Sachs, Morgan Stanley |
| `PE` | Private Equity | PE firms, venture capital | Blackstone, KKR, Carlyle |
| `CU` | Credit Unions | Credit unions with PACs | Navy Federal, BECU |

### 5.3 PAC Contribution

**Statutory Definition:** A contribution from a political committee (as defined in 52 U.S.C. § 30101(4)) to a candidate's authorized committee.

**Operational Definition for ElectWatch:** A transaction in FEC pas2.txt where:
- `TRANSACTION_TP` = '24K' (contribution to candidate)
- Contributing committee (`CMTE_ID`) is classified as financial sector
- Receiving entity is a candidate's principal campaign committee

**Amount Limits (2023-2024 cycle):**
- $5,000 per candidate per election (primary and general are separate)

### 5.4 Individual Contribution

**Statutory Definition:** A contribution from an individual to a political committee, subject to disclosure if aggregate exceeds $200 in a calendar year.

**Operational Definition for ElectWatch:** A transaction in FEC itcont.txt where:
- `ENTITY_TP` = 'IND' (individual)
- `EMPLOYER` field matches a verified financial sector firm
- Contribution is to a candidate's authorized committee

**Legal Disclaimer:** Individual contributions reflect personal political activity. They do not represent the views or positions of the contributor's employer. Correlation between employment and political contribution does not imply employer direction, coordination, or endorsement.

### 5.5 Financial Sector Stock Trade

**Definition:** A securities transaction disclosed under the STOCK Act where the traded security is issued by a financial sector company (SIC 6000-6799).

**Classification Method:**
1. Extract ticker symbol from disclosure
2. Look up company SIC code via SEC EDGAR
3. If SIC 6000-6799, classify as financial sector trade

---

## 6. CLASSIFICATION METHODOLOGY

### 6.1 PAC Classification

**Approach:** Classify PACs based on their connected organization, which is required to be disclosed in FEC filings.

**Source:** FEC cm.txt `CONNECTED_ORG_NM` field

**Process:**
1. Extract all PACs from cm.txt where `CMTE_TP` = 'Q' (qualified PAC)
2. Match `CONNECTED_ORG_NM` to known financial sector firms
3. Assign sub-sector based on primary business activity

**Verified Organizations:** 441 financial sector firms with PACs

**Confidence Levels:**

| Level | Criteria | Count |
|-------|----------|-------|
| HIGH | Direct name match to major financial institution | 350 |
| MEDIUM | Subsidiary/affiliate of known financial firm | 75 |
| LOW | Industry classification only (edge cases) | 16 |

### 6.2 Employer Classification (Individual Contributions)

**The Problem (Pre-January 2026):**

Original methodology used keyword pattern matching:
- Any employer containing "BANK" → banking
- Any employer containing "INSURANCE" → insurance
- etc.

With 58 million records and free-text employer names, this created massive false positives:

| Employer | False Classification | Actual Business |
|----------|---------------------|-----------------|
| INDIANA SPINE GROUP | banking | Medical practice |
| UNIVERSITY OF MICHIGAN | insurance | University |
| STATE OF CALIFORNIA | investment | Government |
| WELLS ENTERPRISES | banking | Ice cream company |
| US DEPARTMENT OF STATE | investment | Federal agency |

**The Solution (January 2026):**

**Exact match against PAC-connected organizations only.**

**Algorithm:**
```
function classify_employer(employer_name):
    normalized = normalize(employer_name)

    if normalized in verified_pac_connected_orgs:
        return verified_pac_connected_orgs[normalized].sector

    return NULL  # Not classified as financial sector
```

**Normalization Rules:**
1. Convert to uppercase
2. Remove punctuation except hyphens
3. Remove common suffixes: INC, LLC, CORP, CO, LTD, LP, NA, FSB
4. Collapse multiple spaces
5. Trim whitespace

**Why This Approach:**
- **Zero false positives** — Only verified firms classified
- **Defensible** — Every match traces to a PAC disclosure
- **Auditable** — Clear provenance for each classification
- **Conservative** — Undercounting preferable to overcounting

**Trade-offs:**
- Misses small financial firms without PACs
- Misses fintech startups
- Misses boutique advisors

**Assessment:** Acceptable. Lost coverage represents smaller dollar amounts and harder-to-verify entities. Signal-to-noise improvement is significant.

### 6.3 Alias & Parent-Subsidiary Mapping

Many financial firms operate under multiple names. The alias table maps variations to canonical names:

| Alias | Canonical | Type |
|-------|-----------|------|
| BOFA | BANK OF AMERICA | Abbreviation |
| JPMC | JPMORGAN CHASE | Abbreviation |
| CHASE | JPMORGAN CHASE | Brand name |
| MERRILL | BANK OF AMERICA | Subsidiary |
| SCHWAB | CHARLES SCHWAB | Short name |
| FIDELITY INVESTMENTS | FIDELITY | Full name |

**Maintenance:** Aliases added when discovered through data validation.

### 6.4 Stock Trade Classification

**Process:**
1. Parse ticker symbol from STOCK Act disclosure
2. Query SEC EDGAR for company SIC code
3. If SIC 6000-6799 → financial sector
4. Apply sub-sector based on SIC range

**Ticker-to-SIC Cache:** Maintained locally to reduce API calls

**Edge Cases:**
- Diversified companies (e.g., Berkshire Hathaway) → Classified based on primary SIC
- Mutual funds → Classified if financial-sector focused
- ETFs → Classified if financial-sector focused (e.g., XLF)

---

## 7. CALCULATIONS & FORMULAS

### 7.1 Contribution Totals

**PAC_TOTAL** (All Sectors)
```
PAC_TOTAL = SUM(pas2.TRANSACTION_AMT)
WHERE recipient_candidate_id = target
AND transaction_type = '24K'
AND election_cycle IN (target_cycles)
```

**INDIVIDUAL_TOTAL** (All Sectors)
```
INDIVIDUAL_TOTAL = SUM(itcont.TRANSACTION_AMT)
WHERE recipient_committee = candidate_pcc
AND election_cycle IN (target_cycles)
```

**FINANCIAL_PAC_TOTAL**
```
FINANCIAL_PAC_TOTAL = SUM(pas2.TRANSACTION_AMT)
WHERE recipient_candidate_id = target
AND contributing_committee IN (financial_sector_pacs)
AND transaction_type = '24K'
AND election_cycle IN (target_cycles)
```

**FINANCIAL_INDIVIDUAL_TOTAL**
```
FINANCIAL_INDIVIDUAL_TOTAL = SUM(itcont.TRANSACTION_AMT)
WHERE recipient_committee = candidate_pcc
AND employer IN (verified_financial_employers)
AND election_cycle IN (target_cycles)
```

**FINANCIAL_TOTAL**
```
FINANCIAL_TOTAL = FINANCIAL_PAC_TOTAL + FINANCIAL_INDIVIDUAL_TOTAL
```

### 7.2 Percentage Calculations

**FINANCIAL_PCT** (Financial sector as % of total)
```
FINANCIAL_PCT = (FINANCIAL_TOTAL / (PAC_TOTAL + INDIVIDUAL_TOTAL)) * 100
```

**PAC_PCT** (PAC as % of financial)
```
PAC_PCT = (FINANCIAL_PAC_TOTAL / FINANCIAL_TOTAL) * 100
```

**INDIVIDUAL_PCT** (Individual as % of financial)
```
INDIVIDUAL_PCT = (FINANCIAL_INDIVIDUAL_TOTAL / FINANCIAL_TOTAL) * 100
```

### 7.3 Trade Counting

**TRADE_COUNT**
```
TRADE_COUNT = COUNT(stock_trades)
WHERE official_bioguide_id = target
AND ticker_sic IN (6000-6799)
```

**Note:** Each transaction is counted separately. A buy and subsequent sell of the same security = 2 trades.

---

## 8. DATA QUALITY & VALIDATION

### 8.1 Automated Validation (Each Data Refresh)

| Check | Description | Action if Failed |
|-------|-------------|------------------|
| Record count | Compare to previous load ±10% | Alert, investigate |
| Null rate | Key fields null rate <5% | Alert if exceeds |
| Amount outliers | Flag transactions >$50,000 | Manual review |
| Date validity | All dates within expected range | Reject invalid |
| Duplicate check | Same SUB_ID appearing twice | Deduplicate |

### 8.2 Manual Validation (Quarterly)

| Check | Description |
|-------|-------------|
| Top 10 recipients | Verify totals against FEC website |
| Random sample (n=50) | Trace contributions to source documents |
| New PAC review | Manually verify any newly classified PACs |
| Employer spot check | Verify 10 random employer classifications |

### 8.3 Known Issues Log

| Issue | Description | Status | Workaround |
|-------|-------------|--------|------------|
| Earmarked contributions | Some PAC contributions are earmarked pass-throughs | Documented | Included in totals, noted in methodology |
| Amendment handling | Amended filings may create apparent duplicates | Mitigated | Use latest amendment only |
| Late STOCK Act filings | Some trades disclosed late | Documented | Data is point-in-time |

---

## 9. LIMITATIONS & DISCLAIMERS

### 9.1 Data Limitations

1. **Contributions under $200 not itemized** — FEC only requires disclosure of contributors whose aggregate exceeds $200 in a calendar year. Small-dollar contributions from financial sector employees are not captured.

2. **Employer field is self-reported** — Contributors self-report their employer on contribution forms. This data is not validated by the FEC. Errors, abbreviations, and variations are common.

3. **STOCK Act reporting delays** — Trades must be disclosed within 45 days. Our data reflects disclosures as filed, not necessarily all trades as of any given date.

4. **STOCK Act amount ranges** — Transaction values are reported in ranges (e.g., "$1,001-$15,000"), not exact amounts. We cannot calculate precise portfolio values.

5. **PDF parsing limitations** — STOCK Act filings are PDFs. Automated parsing may introduce errors. Unusual formatting may be missed.

### 9.2 Methodological Limitations

1. **Conservative employer matching** — Our exact-match methodology intentionally undercounts to avoid false positives. Some legitimate financial sector contributions may be missed.

2. **PAC-only verification** — We only classify employers that have a PAC. Financial firms without PACs are not included in individual contribution tallies.

3. **Point-in-time data** — FEC data is updated weekly. Between updates, recent contributions are not reflected.

4. **Committee assignment lag** — Committee assignments from Congress.gov may not reflect very recent changes.

### 9.3 Critical Disclaimers

**CORRELATION ≠ CAUSATION**

The presence of contributions or stock trades does NOT imply:
- Quid pro quo
- Vote buying
- Corruption
- Improper influence
- Policy positions caused by contributions

Members of Congress receive contributions from many sources and make decisions based on many factors including constituent interests, party positions, personal beliefs, and policy analysis.

**PERSONAL CAPACITY**

Individual contributions represent personal political activity by employees. They do NOT represent:
- Corporate contributions (illegal for corporations to contribute directly)
- Employer endorsement
- Employer direction or coordination
- Corporate policy positions

**LEGAL ACTIVITY**

All activities tracked by ElectWatch are legal under federal law:
- PAC contributions within legal limits
- Individual contributions within legal limits
- Stock trades disclosed per STOCK Act requirements

ElectWatch presents factual disclosure data. It does not allege wrongdoing.

---

## 10. DEVELOPMENT NOTES

### 2026-02-01: Official Profile Page Redesign

**Session:** Complete redesign of official profile page (official_profile.html)

**Template Version:** 2026-02-01-v10

**Changes Made:**

#### Stat Cards Restructured

Previous layout showed generic totals without financial sector focus. New layout (4 cards):

| Position | Card | Data Source | Purpose |
|----------|------|-------------|---------|
| 1 | Total Contributions | `total_pac_bulk + total_individual` | All sectors baseline |
| 2 (highlighted) | Financial Sector | `financial_pac_bulk + financial_individual` | Primary focus metric |
| 3 | Financial Sector PAC | `financial_pac_bulk` | PAC breakdown |
| 4 | Financial Sector Individual | `financial_individual` | Employee contributions |

**Bug Fixed:** PAC card was incorrectly showing all-sector totals (`total_pac_bulk`) instead of financial sector PAC amounts (`financial_pac_bulk`). Example: Ro Khanna showed $45K PAC (all sectors) when financial sector PAC was only $2.5K.

#### Header Sponsor Logos

Top 5 financial sector sponsors displayed in header with company logos, matching leaderboard page style.

**Technical Implementation:**
- Logo Source: Google Favicons API (`https://www.google.com/s2/favicons?domain=${domain}&sz=64`)
- Size: 80x80px container with 64x64px favicon
- Domain Mapping: UPPERCASE lookup table with 150+ firm-to-domain mappings
- Fallback: Sector-colored abbreviation if favicon fails

**Data Merging:** `buildTopSponsors()` function combines:
- `top_financial_pacs` — PAC contributions
- `top_financial_employers` — Individual contributions from firm employees

This ensures sponsors reflect total financial sector influence (PAC + individual).

#### Stock Trades Display
- Cap: Maximum 10 trades shown in main view
- View All Modal: Button appears when trade count exceeds 10
- Formatting Fix: Trade count uses `toLocaleString()` for comma formatting

#### Excel Export
Multi-sheet Excel workbook export using SheetJS:
- Summary — Official info and totals
- Financial PACs — All financial sector PAC contributions
- Financial Employers — Individual contributions by employer
- Stock Trades — Complete STOCK Act disclosure data
- Committees — Committee assignments

#### Link Corrections
- Financial sector firms link to `/electwatch/firm/{name}`
- Trade associations link to `/electwatch/firm/{name}` (not `/electwatch/pac/`)
- Committee links use committee `id` field if available, fall back to name-based slug

---

### 2026-01-31: Employer Classification False Positive Fix

**Session:** Fix massive false positives in employer classification

**Problem:** Keyword matching ("BANK", "INSURANCE", etc.) was tagging non-financial employers:
- INDIANA SPINE GROUP → banking (actually medical practice)
- UNIVERSITY OF MICHIGAN → insurance (actually university)
- WELLS ENTERPRISES → banking (actually ice cream company)

**Solution:** Exact match against PAC-connected organizations only

**Impact:**
- Slotkin: $305K → $138K (universities removed)
- Spartz: $22.8K → $1,000 (medical practice removed)
- Hyde-Smith: $7.4K → $0 (carnival company removed)

**Files Modified:**
- `justdata/apps/electwatch/services/firm_matcher.py`
- `justdata/apps/electwatch/data/cache/financial_firms_list.json`

---

## 11. APPENDICES

### Appendix A: Complete Industry Taxonomy

See Section 5.2 for sub-sector taxonomy with codes.

### Appendix B: PAC-Connected Organizations List

**Count:** 441 verified financial sector organizations

**Top 20 by PAC Contribution Volume:**

| Rank | Organization | Sector | 2023-24 Contributions |
|------|--------------|--------|----------------------|
| 1 | American Bankers Association | BANK | $3.2M |
| 2 | National Association of Realtors | PROP | $2.8M |
| 3 | Credit Union National Association | CU | $2.1M |
| 4 | Investment Company Institute | INVT | $1.9M |
| 5 | American Insurance Association | INSR | $1.7M |
| 6 | JPMorgan Chase | BANK | $1.5M |
| 7 | Bank of America | BANK | $1.4M |
| 8 | Goldman Sachs | INVB | $1.3M |
| 9 | Citigroup | BANK | $1.2M |
| 10 | Wells Fargo | BANK | $1.1M |
| 11 | Morgan Stanley | INVB | $1.0M |
| 12 | BlackRock | INVT | $950K |
| 13 | American Council of Life Insurers | INSR | $920K |
| 14 | Mortgage Bankers Association | MORT | $880K |
| 15 | Capital One | CONS | $850K |
| 16 | State Farm | INSR | $820K |
| 17 | Visa Inc | PYMT | $780K |
| 18 | Mastercard | PYMT | $750K |
| 19 | Charles Schwab | INVT | $720K |
| 20 | Prudential Financial | INSR | $700K |

**Full list:** See `justdata/apps/electwatch/data/cache/financial_firms_list.json`

### Appendix C: Alias & Parent-Subsidiary Mappings

**Sample Mappings:**

| Input Variation | Canonical Name |
|-----------------|----------------|
| BOFA | BANK OF AMERICA |
| BANK OF AMERICA CORP | BANK OF AMERICA |
| BANK OF AMERICA NA | BANK OF AMERICA |
| MERRILL LYNCH | BANK OF AMERICA |
| JPMC | JPMORGAN CHASE |
| JP MORGAN | JPMORGAN CHASE |
| CHASE BANK | JPMORGAN CHASE |
| GOLDMAN | GOLDMAN SACHS |
| GS | GOLDMAN SACHS |
| CITI | CITIGROUP |
| CITIBANK | CITIGROUP |

**Full list:** See `justdata/apps/electwatch/services/firm_matcher.py`

### Appendix D: Code Repository Reference

| Path | Purpose |
|------|---------|
| `justdata/apps/electwatch/` | ElectWatch application root |
| `justdata/apps/electwatch/app.py` | Flask routes |
| `justdata/apps/electwatch/services/` | Business logic |
| `justdata/apps/electwatch/services/pac_classifier.py` | PAC classification |
| `justdata/apps/electwatch/services/firm_matcher.py` | Employer matching |
| `justdata/apps/electwatch/templates/` | Jinja2 templates |
| `justdata/apps/electwatch/templates/official_profile.html` | Official profile page |
| `justdata/apps/electwatch/templates/leaderboard.html` | Leaderboard page |
| `justdata/apps/electwatch/data/cache/` | Cached data files |
| `justdata/apps/electwatch/docs/` | Documentation |

### Appendix E: Sample Validation Queries

**Verify PAC total for specific member:**
```sql
SELECT SUM(transaction_amt) as total
FROM fec_pas2
WHERE cand_id = 'H0CA17000'  -- Ro Khanna
AND cmte_id IN (SELECT cmte_id FROM financial_pacs)
AND election_cycle IN ('2024', '2022')
```

**Verify individual contributions by employer:**
```sql
SELECT employer, SUM(transaction_amt) as total
FROM fec_itcont
WHERE cmte_id IN (
  SELECT cmte_id FROM fec_cm WHERE cand_id = 'H0CA17000'
)
AND UPPER(employer) IN (SELECT UPPER(org_name) FROM verified_financial_orgs)
GROUP BY employer
ORDER BY total DESC
```

**Count financial sector trades:**
```sql
SELECT COUNT(*) as trade_count
FROM stock_trades
WHERE bioguide_id = 'K000389'  -- Ro Khanna
AND ticker_sic BETWEEN 6000 AND 6799
```

---

---

## 12. DOCUMENTATION STANDARDS

### 12.1 Purpose

This section defines the methodology for creating and maintaining internal methodology documentation across all JustData applications. These standards ensure:

1. **Legal defensibility** — Every claim traceable to specific data or decision
2. **Replicability** — Independent researchers can reproduce results
3. **Continuity** — Claude instances can maintain context across sessions
4. **Auditability** — Complete history of methodological decisions

### 12.2 Document Location Standard

All JustData applications must maintain methodology documentation at:

```
justdata/apps/{app_name}/docs/METHODOLOGY_INTERNAL.md
```

**Applications requiring methodology docs (priority order):**

| Priority | Application | Status |
|----------|-------------|--------|
| 1 | ElectWatch | ✓ Complete |
| 2 | MergerMeter | Pending |
| 3 | LendSight | Pending |
| 4 | BizSight | Pending |
| 5 | BranchSight | Pending |
| 6 | DataExplorer | Pending |
| 7 | BranchMapper | Pending |
| 8 | LenderProfile | Pending |

### 12.3 Required Sections

Every METHODOLOGY_INTERNAL.md must include:

1. **Document Control** — Version, status, dates, author, AI model used
2. **Changelog** — Git-commit style history (newest first)
3. **Scope & Purpose** — What is measured, what is NOT measured
4. **Data Sources** — Full specification for each source
5. **Definitions** — Every term that could be contested
6. **Classification Methodology** — Decision trees, thresholds, algorithms
7. **Calculations & Formulas** — Exact formulas, not prose descriptions
8. **Data Quality & Validation** — Automated and manual checks
9. **Limitations & Disclaimers** — What the data cannot tell us
10. **Development Notes** — Chronological decision log
11. **Appendices** — Reference tables, code locations

### 12.4 AI Model Attribution

When Claude assists in creating or updating methodology documentation:

| Field | Description | Example |
|-------|-------------|---------|
| **AI Model** | Full model name and version | Claude Opus 4.5 (claude-opus-4-5-20251101) |
| **Interface** | How Claude was accessed | Claude.ai, Claude Code, API |
| **Session Date** | Date of interaction | 2026-02-02 |
| **Session Time** | Time with timezone | 03:45 EST |

**Why track this:**
- Model capabilities vary across versions
- Enables reproduction of analytical approach
- Audit trail for AI-assisted decisions
- Identifies which Claude instance contributed what

### 12.5 Maintenance Protocol

Claude instances should update this document when:

| Trigger | Action |
|---------|--------|
| Methodology changes | Add to Changelog, update relevant section |
| New data source added | Add to Data Sources section |
| Classification rules change | Update Classification Methodology |
| Bug affecting methodology discovered | Add to Known Issues, document fix |
| Significant decision made | Add to Development Notes with rationale |
| Session ends | Update timestamp, add session summary |

### 12.6 Cross-Project Documentation

This documentation standard applies to all NCRC research projects, not just JustData:

| Project Type | Documentation Location |
|--------------|------------------------|
| JustData apps | `justdata/apps/{app}/docs/METHODOLOGY_INTERNAL.md` |
| HMDA analysis | Project folder `/docs/METHODOLOGY.md` |
| Research reports | Report folder `/methodology/` |
| Social media content | `{project}/docs/CONTENT_METHODOLOGY.md` |

### 12.7 Version Control

**Semantic versioning:** `MAJOR.MINOR.PATCH`

| Change Type | Version Increment | Example |
|-------------|-------------------|----------|
| Breaking methodology change | MAJOR | New classification system |
| New feature/section | MINOR | Added data source |
| Bug fix, clarification | PATCH | Fixed typo, clarified definition |

### 12.8 Review Cycle

| Review Type | Frequency | Reviewer |
|-------------|-----------|----------|
| Automated validation | Each data refresh | Claude Code |
| Content review | Monthly | Jay Richardson |
| Legal review | Before publication | Rose (Corporate Counsel) |
| External audit | As needed | Independent reviewer |

---

## Document End

**Classification:** INTERNAL - NOT FOR PUBLICATION

**Last Updated:** 2026-02-02 03:45 EST

**AI Model:** Claude Opus 4.5 (claude-opus-4-5-20251101) via Claude.ai

**Next Review Date:** 2026-03-01
