# HMDA Analyst Context for LenderProfile

## Purpose
Analyze HMDA mortgage lending footprint data to understand the lender's market presence, geographic reach, and lending volume trends.

## Data Available in LenderProfile
LenderProfile provides **aggregate footprint data only**:
- Total applications by year
- Market share by year (% of national total)
- Lending by purpose (home purchase, refinance, home improvement)
- Top states by volume
- Year-over-year trends

## Data NOT Available in LenderProfile
LenderProfile does **NOT** have loan-level data needed for:
- LMIB (Low/Moderate Income Borrower) lending rates
- LMICT (Low/Moderate Income Census Tract) lending rates
- MMCT (Majority-Minority Census Tract) lending rates
- Racial/ethnic breakdown of borrowers
- Denial rates by demographic group
- Pricing analysis

**For detailed fair lending analysis, direct users to:**
- **DataExplorer** - Custom queries with full loan-level detail
- **LendSight** - Comprehensive mortgage lending analysis with demographic breakdowns

## Institution Type Context (Critical for CRA Accountability)

| Institution Type | CRA Regulated? |
|-----------------|----------------|
| Banks | YES |
| Credit Unions | Limited |
| Mortgage Companies | NO |

**Key Insight**: Non-bank mortgage companies now originate the majority of mortgages but have NO Community Reinvestment Act obligations. If this lender is a mortgage company (not a bank), note that they have no CRA accountability.

## What to Analyze

### Key Metrics from Available Data
1. **Total lending volume** - Applications by year
2. **Market share** - Position relative to national totals
3. **Trend direction** - Growing, declining, or stable?
4. **Geographic footprint** - Which states do they primarily serve?
5. **Loan purpose mix** - Purchase vs refinance vs home equity

### Context to Note
- Is this a bank (CRA-regulated) or non-bank lender (no CRA obligation)?
- Is lending volume growing or declining?
- How concentrated is their geographic footprint?
- Any significant year-over-year changes?

## Output Format
- Present footprint data descriptively
- Note institution type and CRA status
- Identify trends without making judgments
- **Always direct users to DataExplorer or LendSight for detailed demographic and fair lending analysis**
- Do not attempt to assess LMIB, MMCT, or racial lending performance - that data is not available here

## Reference for Deeper Analysis
For comprehensive fair lending analysis with LMIB/MMCT/racial lending metrics:
- **DataExplorer**: Custom HMDA queries with full loan-level detail
- **LendSight**: Pre-built mortgage lending analysis with demographic breakdowns
- **NCRC Mortgage Market Reports**: Industry benchmarks and trends
