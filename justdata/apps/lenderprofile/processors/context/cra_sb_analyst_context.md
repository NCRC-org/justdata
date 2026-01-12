# CRA/Small Business Lending Analyst Context for LenderProfile

## Purpose
Analyze small business lending data to assess lender performance in serving minority-owned, women-owned, and small businesses in underserved communities.

## The Discrimination Problem in Small Business Lending

### Evidence of Ongoing Discrimination
- **White applicants receive better information** about loan products, particularly regarding fees (NCRC studies)
- **Black-owned businesses less likely to be approved** for financing compared to White-owned firms (Federal Reserve studies)
- **Businesses owned by people of color receive lower loan amounts** than White-owned firms, even after controlling for sales levels (MBDA)
- **LGBTQI+ businesses equally likely to apply but less likely to receive financing**
  - 33% of denied LGBTQI+ businesses told lender doesn't approve "businesses like theirs" (vs 24% non-LGBTQI+)

### Economic Impact of Discrimination
- Citigroup estimates: Fair access to lending for Black-owned businesses alone would result in:
  - **$650 billion additional business revenue per year**
  - **6.1 million additional jobs per year**
- Discrimination harms entire economy by preventing small business expansion

## Section 1071 - New Small Business Lending Data Rule

### Overview
- CFPB finalized rules March 2023 implementing Section 1071 of Dodd-Frank
- Brings transparency to lending to businesses owned by people of color, women, and LGBTQI+ community
- Covers banks, credit unions, online lenders, CDFIs, merchant cash advance providers, equipment financing, etc.

### Coverage Threshold
- Applies to lenders originating 100+ small business loans in each of prior two years
- Covers 94-95% of bank small business loans
- Two-thirds of banks make fewer than 100 loans and won't report

### Implementation Schedule
| Lender Size | Data Collection Start |
|-------------|----------------------|
| 2,500+ loans/year | October 1, 2024 |
| 500-2,499 loans/year | April 1, 2025 |
| 100-499 loans/year | January 1, 2026 |

Data reported to CFPB by June 1 of following year.

### Data Points Collected
**Required by statute:**
- Application number and date
- Loan type and purpose
- Amount applied for and approved
- Action taken and date
- Census tract of principal place of business
- Gross annual revenue
- Race, sex, ethnicity of principal owners

**Discretionary data points added by CFPB:**
- Pricing (interest rate, origination charges, broker fees, prepayment penalties)
- Time in business
- NAICS code (industry sector)
- Number of employees
- Application method
- Denial reasons
- Number of principal owners
- LGBTQI+ status of owners

### Definition of Minority-Owned Business
A business where one or more people of color:
- Hold more than 50% of ownership or control, AND
- More than 50% of net profits/losses accrue to them

### Racial/Ethnic Categories
**Aggregate groups:**
- Hispanic or Latino
- American Indian or Alaska Native
- Asian
- Black or African American
- Native Hawaiian or Other Pacific Islander
- White

**Disaggregated subgroups** (similar to HMDA) for more specific cultural heritage

### Limitations
- No visual observation/surname requirement when applicant doesn't provide demographics (unlike HMDA)
- Large portions of data may lack demographic info as few business applicants volunteer it
- No data on businesses owned by people with disabilities
- No separate category for Middle Eastern/North African communities

## Current CRA Small Business Lending Data

Until Section 1071 data is widely available, we use existing CRA small business lending data which includes:
- Loan counts by year
- Loan amounts by year
- Geographic distribution
- Market share calculations

**Limitations of current CRA data:**
- No demographic breakdown of borrowers
- Limited to CRA-regulated depository institutions
- Less pricing and terms detail

## What to Analyze

### Key Metrics
1. **Total small business lending volume** (loans and dollars)
2. **Trend direction** (growing, declining, stable)
3. **Market share** compared to national totals
4. **Geographic concentration** by state

### Context to Note
- Is this lender CRA-regulated (bank) or not (mortgage company, fintech)?
- How does volume compare to peers?
- Any significant changes year-over-year?

### Future (When 1071 Data Available)
- Lending to minority-owned businesses vs. White-owned
- Lending to women-owned businesses
- Denial rates by demographic group
- Pricing differences by demographic group
- Lending in LMI census tracts

## Output Format
- Present small business lending data descriptively
- Note trends without making judgments
- Direct users to BizSight for deeper analysis
- Note that Section 1071 data will provide more demographic detail in the future

## Reference Sources
- NCRC Report: "Initial Analysis Of Final Section 1071 Small Business Lending Rule" (April 2023)
- CFPB Section 1071 Final Rule
- NCRC studies on discrimination in small business lending
