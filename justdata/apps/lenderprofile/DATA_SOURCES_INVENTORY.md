# LenderProfile Data Sources Inventory

Complete list of all data sources and what they provide.

## External APIs

### 1. **FDIC BankFind API** ✅
**Base URL:** `https://banks.data.fdic.gov/api/`  
**Status:** Active (Call Reports only)  
**What It Provides:**
- **Financial API (`/financials`)**: Quarterly Call Report data
  - ASSET, DEP, EQUITY, NETINC, ROA, ROE, REPDTE
  - Last 5 years of quarterly financial data
-

**Documentation:** https://api.fdic.gov/banks/docs/

---

### 2. **CFPB HMDA API** ✅
**Base URL:** `https://ffiec.cfpb.gov/hmda-auth/` and `https://ffiec.cfpb.gov/hmda-platform`  
**Status:** Active (requires bearer token)  
**What It Provides:**
- **Institution Metadata:**
  - Institution name, type, location
  - Assets (when available)
  - RSSD, LEI identifiers
- **Transmittal Sheet Data:**
  - LAR counts per year
  - Assets from transmittal sheets
  - Tax ID (EIN)

**Documentation:** 
- HMDA API: https://ffiec.cfpb.gov/hmda-auth/
- Public Verification: https://ffiec.cfpb.gov/documentation/api/public-verification/

---

### 3. **CFPB Consumer Complaint Database (CCDB5)** ✅
**Base URL:** `https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/`  
**Status:** Active  
**What It Provides:**
- Consumer complaints by company
- Complaint details: date, product, issue, sub-issue, state, ZIP
- Complaint trends over time
- Topic analysis (most common issues)
- Response analysis (timely, disputed, etc.)

**Documentation:** https://cfpb.github.io/api/ccdb/api.html

---

### 4. **GLEIF API** ✅
**Base URL:** `https://api.gleif.org/api/v1/`  
**Status:** Active  
**What It Provides:**
- **Entity Information:**
  - Legal name
  - Legal address (city, state, country)
  - Headquarters address
  - Registration authorities (FDIC cert, etc.)
- **Parent/Child Relationships:**
  - Direct parent LEI and name
  - Ultimate parent LEI and name
  - Direct children (subsidiaries)
  - Ultimate children
- **Entity Status:**
  - Registration status
  - Entity category

**Documentation:** https://www.gleif.org/en/market-data/gleif-api

---

### 5. **SEC EDGAR API** ✅
**Base URL:** `https://www.sec.gov/`  
**Status:** Active  
**What It Provides:**
- **Company Information:**
  - CIK (Central Index Key)
  - Company name
  - Ticker symbol (from submissions API)
- **Filing Data:**
  - Last 5 10-K filings (annual reports)
  - Full 10-K content (for AI analysis)
  - 10-Q filings (quarterly reports)
  - 8-K filings (current reports)
  - DEF 14A (proxy statements)
- **Financial Data:**
  - XBRL financials (if available)
  - Filing history

**Documentation:** https://www.sec.gov/edgar/sec-api-documentation

---

### 6. **Seeking Alpha API** ✅
**Base URL:** `https://seeking-alpha.p.rapidapi.com/` and `https://seeking-alpha-api.p.rapidapi.com/`  
**Status:** Active (requires RapidAPI subscription)  
**What It Provides:**
- **Financial Data:**
  - Company profile
  - Financial statements (income, balance sheet, cash flow)
  - Earnings data and estimates
- **Analyst Ratings:**
  - Author ratings (Buy/Hold/Sell)
  - Quant ratings
  - Sell-side ratings
  - Rating distribution (buy/hold/sell counts)
- **News/Articles:**
  - Leading news stories
  - Recent articles about the company

**Documentation:** 
- Financial API: https://rapidapi.com/seeking-alpha/api/seeking-alpha
- Articles API: https://rapidapi.com/belchiorarkad-FqvHs2EDOtP/api/seeking-alpha-api

---

### 7. **CourtListener API** ✅
**Base URL:** `https://www.courtlistener.com/api/rest/v4/`  
**Status:** Active  
**What It Provides:**
- **Litigation Data:**
  - Federal court dockets
  - Cases where institution is a party
  - Case details: date filed, court, case type
  - Docket entries
  - Party information

**Documentation:** https://www.courtlistener.com/api/rest-info/

---

### 8. **NewsAPI** ✅
**Base URL:** `https://newsapi.org/v2/`  
**Status:** Active (100 requests/day free tier)  
**What It Provides:**
- **News Articles:**
  - Recent news about the institution (last 30 days on free tier)
  - Article titles, descriptions, URLs
  - Source information
  - Publication dates
  - Article content snippets

**Documentation:** https://newsapi.org/docs


---


---

---


## BigQuery Data Sources

### 15. **BigQuery - GLEIF Names** ✅
**Table:** `justdata.gleif_names`  
**Status:** Active  
**What It Provides:**
- Legal entity names (6,481 records)
- Parent/child relationships
- Direct parent LEI and name
- Ultimate parent LEI and name
- Direct children (JSON array)
- Ultimate children (JSON array)
- Legal and headquarters addresses

**Used For:** Entity identification, hierarchy detection

---



---

### 17. **BigQuery - SOD Branch Data** ✅
**Table:** `justdata.sod_branches_optimized`  
**Status:** Active  
**What It Provides:**
- **Branch Network Data:**
  - Branch locations by year (2017-2025)
  - 740,974 branch records
  - 5,871 banks
  - City, state, ZIP
  - CBSA codes and names (via join)
  - Branch coordinates (latitude/longitude)
  - RSSD identifier

**Used For:** Branch network analysis, geographic footprint

---

### 18. **BigQuery - Credit Union Branch Data** ✅
**Table:** `justdata.credit_union_branches`  
**Status:** Active  
**What It Provides:**
- **Credit Union Branch Data:**
  - Branch locations by year (2021-2025)
  - 109,104 branch records
  - City, state, ZIP
  - CBSA codes and names (via join)
  - CU number or RSSD identifier

**Used For:** Credit union branch network analysis

---

### 19. **BigQuery - Credit Union Call Reports** ✅
**Table:** `justdata.credit_union_call_reports`  
**Status:** Active  
**What It Provides:**
- **Credit Union Financial Data:**
  - Institution-level data (2021-2025)
  - 23,971 records
  - Financial metrics
  - Assets, deposits, etc.

**Used For:** Credit union financial analysis

---

### 20. **BigQuery - Geographic Data** ✅
**Table:** `geo.cbsa_to_county`  
**Status:** Active  
**What It Provides:**
- CBSA codes and names
- County to CBSA mapping
- Geographic crosswalks

**Used For:** Branch geographic analysis, metro area identification

---

## Data Collection Summary

### Currently Collected (in `data_collector.py`):

1. ✅ **FDIC Financials** - Call Report data only
2. ✅ **CFPB Metadata** - Institution info, assets, LAR counts
3. ✅ **CFPB Complaints** - Consumer complaint database
4. ✅ **GLEIF** - Entity info, parent/child relationships
5. ✅ **SEC** - 10-K filings, ticker, CIK, filing history
6. ✅ **Seeking Alpha** - Financials, ratings, earnings, news
7. ✅ **CourtListener** - Litigation data
8. ✅ **NewsAPI** - Recent news articles
9. ✅ **TheOrg** - Organizational charts, people
10. ✅ **Federal Register** - Merger notices, regulatory documents
11. ⚠️ **Federal Reserve** - Placeholder (needs implementation)
12. ⚠️ **Regulations.gov** - Placeholder (needs API key)
13. ⚠️ **CFPB Enforcement** - Placeholder (needs web scraping)

### Available but NOT Currently Integrated:

- **BigQuery Branch Analysis** - Available via `branch_network_analyzer.py` but not automatically called
- **BigQuery HMDA Analysis** - Available but not integrated into reports

---

## What Each Source Provides (Summary)

| Source | Institution Info | Financials | Branches | Litigation | News | Ratings | Filings | Complaints | Enforcement |
|--------|-----------------|------------|----------|------------|------|---------|---------|------------|-------------|
| FDIC | ❌ | ✅ Call Reports | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| CFPB HMDA | ✅ | ✅ Assets | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| CFPB Complaints | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| GLEIF | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| SEC | ✅ | ✅ XBRL | ❌ | ❌ | ❌ | ❌ | ✅ 10-K/10-Q | ❌ | ❌ |
| Seeking Alpha | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| CourtListener | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| NewsAPI | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| TheOrg | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Federal Register | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| BigQuery SOD | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| BigQuery HMDA | ✅ LAR counts | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

---

## Key Gaps

1. **Branch Data** - Not automatically integrated into reports (available but separate)
2. **CRA Performance** - No data source (FFIEC web scraping needed)
3. **Enforcement Actions** - No data source (CFPB web scraping needed)
4. **Merger History** - Limited (Federal Reserve NIC needs implementation)
5. **HMDA Lending Analysis** - Available in BigQuery but not integrated

---

## Recommendations

1. **Integrate Branch Analysis** - Automatically run `branch_network_analyzer.py` during data collection
2. **Add HMDA Lending Summary** - Query BigQuery HMDA for lending trends
3. **Implement CFPB Enforcement Scraping** - High priority for regulatory history
4. **Implement FFIEC CRA Scraping** - High priority for CRA section
5. **Fix Federal Reserve NIC** - For merger history
6. **Remove Unused APIs** - Regulations.gov, Federal Register (if not needed)

