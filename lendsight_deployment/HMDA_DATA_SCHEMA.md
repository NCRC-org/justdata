# HMDA Data Connection and Schema

## Connection Details

- **Project ID**: `hdma1-242116`
- **Dataset**: `hmda`
- **Table**: `hmda`
- **Connection Method**: BigQuery via Google Cloud credentials (environment variables or service account key file)

## Data Availability

The HMDA table contains mortgage lending data with the following year coverage:
- **2024**: 12,229,298 records, 4,908 lenders, 3,224 counties
- **2023**: 11,483,889 records, 5,113 lenders, 3,225 counties
- **2022**: 16,085,455 records, 4,464 lenders, 3,224 counties
- **2021**: 26,192,390 records, 4,341 lenders, 3,224 counties
- **2020**: 25,551,868 records, 4,475 lenders, 3,222 counties
- **2019**: 17,545,457 records, 5,508 lenders, 3,223 counties
- **2018**: 15,119,651 records, 5,678 lenders, 3,310 counties

## Complete Schema (99 Columns)

### Geographic Identifiers
- `activity_year` (STRING) - Year of the loan application
- `state_code` (STRING) - 2-digit state FIPS code
- `county_code` (STRING) - 3-digit county FIPS code
- `census_tract` (STRING) - Census tract identifier
- `derived_msa_md` (STRING) - MSA/MD code

**Note**: `geoid5` is NOT directly in the HMDA table. It must be derived as: `CONCAT(LPAD(state_code, 2, '0'), LPAD(county_code, 3, '0'))` (state FIPS + county FIPS = 5-digit geoid5)

### Lender Information
- `lei` (STRING) - Legal Entity Identifier (unique lender identifier)

**Note**: `respondent_name` is NOT directly in the HMDA table. Lender names must be looked up from a separate LEI registry table or joined with the `geo.cbsa_to_county` table if it contains lender information.

### Loan Characteristics
- `action_taken` (STRING) - Action taken on application (e.g., '1' = originated, '3' = denied)
- `loan_purpose` (STRING) - Purpose of loan (e.g., '1' = home purchase)
- `loan_type` (STRING) - Type of loan
- `loan_amount` (INT64) - Loan amount in dollars
- `occupancy_type` (STRING) - Occupancy type (e.g., '1' = owner-occupied)
- `total_units` (STRING) - Number of units (e.g., '1','2','3','4' for 1-4 units)
- `construction_method` (STRING) - Construction method (e.g., '1' = site-built)
- `reverse_mortgage` (STRING) - Whether it's a reverse mortgage (e.g., '1' = yes)
- `lien_status` (STRING) - Lien status
- `open_end_line_of_credit` (STRING) - Open-end line of credit indicator
- `business_or_commercial_purpose` (STRING) - Business/commercial purpose indicator

### Financial Metrics
- `income` (INT64) - Applicant income (in thousands)
- `property_value` (INT64) - Property value
- `combined_loan_to_value_ratio` (FLOAT64) - Combined LTV ratio
- `interest_rate` (FLOAT64) - Interest rate
- `rate_spread` (FLOAT64) - Rate spread
- `debt_to_income_ratio` (STRING) - Debt-to-income ratio
- `total_loan_costs` (FLOAT64) - Total loan costs
- `total_points_and_fees` (FLOAT64) - Total points and fees
- `origination_charges` (FLOAT64) - Origination charges
- `discount_points` (FLOAT64) - Discount points
- `lender_credits` (FLOAT64) - Lender credits
- `loan_term` (STRING) - Loan term
- `prepayment_penalty_term` (STRING) - Prepayment penalty term
- `intro_rate_period` (STRING) - Introductory rate period
- `negative_amortization` (STRING) - Negative amortization indicator
- `interest_only_payment` (STRING) - Interest-only payment indicator
- `balloon_payment` (STRING) - Balloon payment indicator
- `other_nonamortizing_features` (STRING) - Other non-amortizing features
- `hoepa_status` (STRING) - HOEPA status
- `conforming_loan_limit` (STRING) - Conforming loan limit

### Applicant Demographics
- `applicant_race_1` through `applicant_race_5` (STRING) - Primary and additional race codes
- `applicant_ethnicity_1` through `applicant_ethnicity_5` (STRING) - Primary and additional ethnicity codes
- `applicant_race_observed` (STRING) - Whether race was observed
- `applicant_ethnicity_observed` (STRING) - Whether ethnicity was observed
- `applicant_sex` (STRING) - Applicant sex
- `applicant_sex_observed` (STRING) - Whether sex was observed
- `applicant_age` (STRING) - Applicant age
- `applicant_age_above_62` (STRING) - Whether applicant is above 62
- `derived_race` (STRING) - Derived race classification
- `derived_ethnicity` (STRING) - Derived ethnicity classification
- `derived_sex` (STRING) - Derived sex classification

### Co-Applicant Demographics
- `co_applicant_race_1` through `co_applicant_race_5` (STRING)
- `co_applicant_ethnicity_1` through `co_applicant_ethnicity_5` (STRING)
- `co_applicant_race_observed` (STRING)
- `co_applicant_ethnicity_observed` (STRING)
- `co_applicant_sex` (STRING)
- `co_applicant_sex_observed` (STRING)
- `co_applicant_age` (STRING)
- `co_applicant_age_above_62` (STRING)

### Credit and Underwriting
- `applicant_credit_score_type` (STRING) - Credit score type
- `co_applicant_credit_score_type` (STRING) - Co-applicant credit score type
- `aus_1` through `aus_5` (STRING) - Automated underwriting system codes
- `denial_reason_1` through `denial_reason_4` (STRING) - Denial reasons (if denied)
- `preapproval` (STRING) - Preapproval indicator
- `submission_of_application` (STRING) - Submission method
- `initially_payable_to_institution` (STRING) - Initially payable to institution indicator

### Property Characteristics
- `manufactured_home_secured_property_type` (STRING) - Manufactured home property type
- `manufactured_home_land_property_interest` (STRING) - Manufactured home land interest
- `multifamily_affordable_units` (INT64) - Number of affordable units in multifamily property
- `derived_dwelling_category` (STRING) - Derived dwelling category
- `derived_loan_product_type` (STRING) - Derived loan product type

### Purchaser Information
- `purchaser_type` (STRING) - Type of purchaser (e.g., Fannie Mae, Freddie Mac, etc.)

### Census Tract Demographics
- `tract_population` (INT64) - Census tract population
- `tract_minority_population_percent` (FLOAT64) - Percentage of minority population in tract
- `ffiec_msa_md_median_family_income` (INT64) - FFIEC MSA/MD median family income
- `tract_to_msa_income_percentage` (INT64) - Tract income as percentage of MSA/MD median
- `tract_owner_occupied_units` (INT64) - Number of owner-occupied units in tract
- `tract_one_to_four_family_homes` (INT64) - Number of 1-4 family homes in tract
- `tract_median_age_of_housing_units` (INT64) - Median age of housing units in tract

## Key Columns Used in Current SQL Template

### ✅ Available Columns
- `activity_year` - Year filter and grouping
- `lei` - Lender identifier
- `county_code` - County identifier
- `action_taken` - Filter for originated loans ('1')
- `occupancy_type` - Filter for owner-occupied ('1')
- `loan_purpose` - Filter for home purchase ('1')
- `total_units` - Filter for 1-4 units ('1','2','3','4')
- `construction_method` - Filter for site-built ('1')
- `reverse_mortgage` - Filter out reverse mortgages (not '1')
- `loan_amount` - Loan amount aggregation
- `income` - Income aggregation
- `applicant_race_1` - Race classification
- `applicant_ethnicity_1` - Ethnicity classification
- `ffiec_msa_md_median_family_income` - MSA median income for LMI calculation
- `tract_to_msa_income_percentage` - Tract income percentage for LMICT calculation
- `tract_minority_population_percent` - Tract minority percentage for MMCT calculation

### ⚠️ Missing Columns (Need Derivation or Lookup)
- `geoid5` - **MUST BE DERIVED**: `CONCAT(LPAD(state_code, 2, '0'), LPAD(county_code, 3, '0'))`
- `respondent_name` - **MUST BE LOOKED UP**: From `hmda.lenders18` table using LEI

## Current SQL Template Status

The `mortgage_report.sql` template has been updated to:
1. ✅ **Derive geoid5**: `CONCAT(LPAD(h.state_code, 2, '0'), LPAD(h.county_code, 3, '0')) as geoid5`
2. ✅ **Join lenders18 table**: `LEFT JOIN hmda.lenders18 l ON h.lei = l.lei` to get `respondent_name`
3. ✅ **Updated geographic join**: Uses derived geoid5 to join with `geo.cbsa_to_county`

## Lender Information

The `respondent_name` (lender name) is retrieved from the `hmda.lenders18` table by joining on the `lei` (Legal Entity Identifier) field:

```sql
LEFT JOIN hmda.lenders18 l
    ON h.lei = l.lei
```

The `lenders18` table contains lender information linked to HMDA data via the LEI number.

## Additional Available Data

The schema includes many additional fields that could be used for more detailed analysis:
- Loan costs and fees breakdown
- Credit score types
- Automated underwriting system codes
- Denial reasons (for denial analysis)
- Property characteristics
- Co-applicant information
- More detailed demographic breakdowns

## Geographic Joins

The template joins with `geo.cbsa_to_county` table using the derived `geoid5`:
```sql
LEFT JOIN geo.cbsa_to_county c
    ON CONCAT(LPAD(h.state_code, 2, '0'), LPAD(h.county_code, 3, '0')) = CAST(c.geoid5 AS STRING)
```

