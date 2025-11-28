# 1071 Table Requirements Summary

Based on the instructions provided, here are the 6 tables needed:

## Tables 1-3: All Lending (Card & Non-Card)

### Table 1: Bank Size Analysis
**Purpose:** Count large banks by loan volume threshold
- **Year**: Reporting year (2018-2024)
- **# Large Banks <1 K loans**: Count of large banks that made fewer than 1,000 loans in that year
- **# All large banks**: Total count of all large banks (all banks in the data)
- **# loans of banks < 1k**: Total number of loans from banks that made fewer than 1,000 loans in that year
- **# all large bank loans**: Total number of loans made by all large banks in that year

**Assumptions:**
- "Large banks" = all banks/lenders in the disclosure table (all `respondent_id` values)
- Loan count = sum of `num_under_100k + num_100k_250k + num_250k_1m` per lender per year
- A bank has "<1K loans" if their total loans in that year < 1,000

### Table 2: Business Revenue Analysis
**Purpose:** Count loans by business revenue size
- **Year**: Reporting year (2018-2024)
- **# loans to biz <$1 mill rev**: Number of loans to businesses with less than $1 million in revenue
- **# loans to biz >$1 mil.**: Number of loans to businesses with more than $1 million in revenue

**Data Source:**
- The disclosure table has `numsbrev_under_1m` = number of loans to businesses with revenue < $1M
- For loans to businesses > $1M, we can calculate: total loans - loans < $1M
- Loan count = sum of `num_under_100k + num_100k_250k + num_250k_1m`

### Table 3: Combined Bank Size + Business Revenue
**Purpose:** Loans from large banks (>1K loans) by business revenue
- **Year**: Reporting year (2018-2024)
- **#loans banks > 1 K to biz <1 mil**: Loans from banks with >1,000 loans to businesses <$1M revenue
- **# loans banks > 1 K to biz >1 mil**: Loans from banks with >1,000 loans to businesses >$1M revenue

**Logic:**
- Filter to only lenders with >1,000 total loans in that year
- Then count loans by business revenue category

## Tables 4-6: Non-Credit Card Lending Only

**Rule:** Non-credit card loans = lenders with average loan amount >= $10,000 per year
- Filter using: `is_credit_card_lender = 0` OR `lender_type = 'Not Credit Card Lender'`

### Table 4: Bank Size Analysis (Non-Card Only)
Same structure as Table 1, but filtered to:
- Only lenders with `is_credit_card_lender = 0`
- Only include data from non-credit card lenders

### Table 5: Business Revenue Analysis (Non-Card Only)
Same structure as Table 2, but filtered to:
- Only lenders with `is_credit_card_lender = 0`
- Only include loans from non-credit card lenders

### Table 6: Combined Analysis (Non-Card Only)
Same structure as Table 3, but filtered to:
- Only lenders with `is_credit_card_lender = 0`
- Only include loans from non-credit card lenders with >1,000 loans

## Implementation Notes:

1. **Loan Counting**: Use sum of `num_under_100k + num_100k_250k + num_250k_1m` for total loans
2. **Business Revenue**: Use `numsbrev_under_1m` for <$1M, calculate >$1M as total - <$1M
3. **Bank Identification**: Use `respondent_id` to identify unique lenders/banks
4. **Year Filtering**: Include years 2018-2024 (2017 used for qualification checks only)
5. **Data Source**: Use the `1071_1k_lenders` table which already has credit card flags

