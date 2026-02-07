# BizSight Methodology — Internal Reference

## Income Tract Classification

### Data Source
Census tract income classifications come from the FFIEC CRA Small Business Lending
Disclosure data. Each row in the disclosure data represents lending activity for a
specific lender, county, year, and income tract category.

### Income Group Encoding
The `income_group_total` field uses three different encoding formats depending on the
reporting institution and year:

**Summary codes:** 101 (Low), 102 (Moderate), 103 (Middle), 104 (Upper), 105-106 (Unknown/NA)

**Subcategory codes (% of Area Median Income):**
- 001-005: Low Income (0-50% AMI)
- 006-008: Moderate Income (50-80% AMI)
- 009-010: Middle Income (80-100% AMI)
- 011-013: Upper Income (100%+ AMI)
- 014-015: Unknown/NA

**Single-digit codes:** 1 (Low), 2 (Moderate), 3 (Middle), 4 (Upper), 14-15 (Unknown/NA)

**Unpadded subcategory codes (2019 only):** 5 (Low), 6-8 (Moderate), 9-10 (Middle), 11-13 (Upper)

A given institution/county/year uses only one encoding scheme. All formats are
mapped to consistent income categories in the aggregation query.

### Percentage Calculation
When calculating the share of loans to a specific income tract category (e.g.,
"Loans to Low Income Tracts (% of Total)"), the denominator excludes loans where
the census tract income classification is unknown or unavailable. This prevents
loans in unclassified tracts from artificially deflating income category percentages.

Formula: `income_category_loans / (total_loans - unknown_income_loans) x 100`

Total loan counts and amounts include all loans regardless of tract classification.

### LMI Definition
Low-to-Moderate Income (LMI) tracts are census tracts where the median family income
is less than 80% of the area median income, as defined by the FFIEC. LMI equals the
sum of Low Income and Moderate Income tract lending.

### Middle/Upper Combined
BizSight reports Middle Income (80-120% AMI) and Upper Income (120%+ AMI) as a single
combined "Middle + Upper" figure in the midu columns.

### Data Source Citation
FFIEC CRA Small Business Lending Data, compiled by NCRC.
