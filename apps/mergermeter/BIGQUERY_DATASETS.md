# MergerMeter BigQuery Datasets

This document lists all BigQuery datasets and tables used by MergerMeter.

## Project ID

**Default Project:** `hdma1-242116`

This can be configured via the `GCP_PROJECT_ID` environment variable in `.env`.

## Datasets and Tables

### 1. HMDA Dataset (`hmda`)

**Purpose:** Home Mortgage Disclosure Act mortgage lending data

**Tables Used:**
- `hdma1-242116.hmda.hmda` - Main HMDA loan-level data
  - Used for: Mortgage lending analysis, race/ethnicity classification, LMI/MINB calculations
  - Years: 2020-2024 (configurable)

**Key Fields:**
- `activity_year` - Loan year
- `lei` - Legal Entity Identifier (bank identifier)
- `county_code` - 5-digit FIPS county code
- `loan_amount` - Loan amount
- `tract_to_msa_income_percentage` - For LMICT calculation
- `income`, `ffiec_msa_md_median_family_income` - For LMIB calculation
- `tract_minority_population_percent` - For MMCT calculation
- `applicant_race_1` through `applicant_race_5` - Race classification
- `applicant_ethnicity_1` through `applicant_ethnicity_5` - Ethnicity classification

---

### 2. Small Business Dataset (`sb`)

**Purpose:** Section 1071 Small Business Lending data

**Tables Used:**
- `hdma1-242116.sb.disclosure` - Small business loan disclosure data
  - Used for: Small business lending analysis
  - Years: 2019-2023 (configurable)
  
- `hdma1-242116.sb.lenders` - Small business lender information
  - Used for: Linking disclosure data to lender identifiers
  - Links via: `respondent_id` = `sb_resid`

**Key Fields:**
- `year` - Loan year
- `geoid5` - 5-digit FIPS county code
- `msamd` - MSA/MD code
- `income_group_total` - Income group classification
- `numsbrev_under_1m` - Number of loans to businesses with revenue under $1M
- `amtsbrev_under_1m` - Amount of loans to businesses with revenue under $1M
- `respondent_id` - Small business respondent ID

---

### 3. Branch Dataset (`branches`)

**Purpose:** FDIC Summary of Deposits branch data

**Tables Used:**
- `hdma1-242116.branches.sod25` - 2025 Summary of Deposits data
  - Used for: Branch network analysis, HHI calculations
  - Year: 2025 (hard-coded, latest available)

**Key Fields:**
- `year` - Data year
- `rssd` - RSSD ID (bank identifier)
- `geoid5` - 5-digit FIPS county code
- `deposits_000s` - Deposits in thousands
- `uninumbr` - Unique branch identifier
- `br_lmi` - Branch in Low-to-Moderate Income Census Tract (0/1)
- `cr_minority` - Branch in Majority-Minority Census Tract (0/1)

---

### 4. Geographic Dataset (`geo`)

**Purpose:** Geographic crosswalk and mapping data

**Tables Used:**
- `hdma1-242116.geo.cbsa_to_county` - CBSA to county mapping
  - Used for: Mapping counties to CBSAs, getting CBSA names
  - Links via: `geoid5` = `geoid5`

**Key Fields:**
- `geoid5` - 5-digit FIPS county code
- `cbsa_code` - CBSA/MSA code
- `cbsa` - CBSA name
- `County` - County name
- `State` - State name

---

## Dataset Access Requirements

To use MergerMeter, the GCP service account must have:

1. **BigQuery Data Viewer** role on:
   - `hdma1-242116.hmda` dataset
   - `hdma1-242116.sb` dataset
   - `hdma1-242116.branches` dataset
   - `hdma1-242116.geo` dataset

2. **BigQuery Job User** role (to run queries)

## Alternative Project/Dataset Configuration

If using a different GCP project or dataset names, you would need to:

1. Update `GCP_PROJECT_ID` in `.env` file
2. Modify query builders in `apps/mergermeter/query_builders.py` to use different dataset names
3. Ensure the dataset structure matches the expected schema

## Query Examples

All queries are built dynamically in `apps/mergermeter/query_builders.py`:

- `build_hmda_subject_query()` - Subject bank HMDA data
- `build_hmda_peer_query()` - Peer bank HMDA data
- `build_sb_subject_query()` - Subject bank Small Business data
- `build_sb_peer_query()` - Peer bank Small Business data
- `build_branch_query()` - Branch data aggregation
- `build_branch_details_query()` - Individual branch records

---

**Note:** The project ID `hdma1-242116` is hard-coded in queries. To use a different project, update all query builders or set `GCP_PROJECT_ID` environment variable and modify queries to use it dynamically.

