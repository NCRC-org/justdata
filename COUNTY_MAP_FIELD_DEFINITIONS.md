# County Exemption Map - Field Definitions and Calculations

## Data Year: 2024

## Field Definitions

### 1. **Total_Banks**
**Definition:** Total number of unique banks/lenders that operate in each county (have loans in that county).

**Calculation:**
```sql
COUNT(DISTINCT respondent_id)
```
- Counts each unique `respondent_id` (bank) that has at least one loan in the county
- A bank can appear in multiple counties if it operates in multiple counties
- This is the denominator for calculating exemption percentages

**Example:** If 5 different banks have loans in Cook County, IL, then `Total_Banks = 5`

---

### 2. **Exempt_Banks**
**Definition:** Number of banks operating in the county that have **less than 1,000 total loans nationwide** in 2024 (and would therefore be exempt from reporting).

**Calculation:**
```sql
COUNT(DISTINCT CASE WHEN lender_total_loans_2024 < 1000 THEN respondent_id END)
```

**Step-by-step:**
1. First, calculate each bank's **total loans across ALL counties** in 2024:
   ```sql
   SUM(num_under_100k + num_100k_250k + num_250k_1m) 
   GROUP BY respondent_id
   ```
2. Then, for each county, count how many banks operating there have <1,000 total loans

**Important:** The exemption is based on the bank's **total nationwide loan volume**, not just loans in that specific county.

**Example:** 
- Bank A has 500 loans total (300 in County X, 200 in County Y) → Exempt
- Bank B has 2,000 loans total (100 in County X, 1,900 in County Y) → Not Exempt
- In County X: `Exempt_Banks = 1` (only Bank A is exempt)

---

### 3. **NonExempt_Banks**
**Definition:** Number of banks operating in the county that have **1,000 or more total loans nationwide** in 2024 (and would NOT be exempt).

**Calculation:**
```sql
COUNT(DISTINCT CASE WHEN lender_total_loans_2024 >= 1000 THEN respondent_id END)
```

**Relationship:**
- `Total_Banks = Exempt_Banks + NonExempt_Banks`

**Example:** If County X has 5 total banks, and 3 are exempt, then `NonExempt_Banks = 2`

---

### 4. **Pct_Exempt**
**Definition:** Percentage of banks operating in the county that would be exempt from reporting.

**Calculation:**
```sql
ROUND(100.0 * Exempt_Banks / Total_Banks, 2)
```

**Formula:**
```
Pct_Exempt = (Exempt_Banks / Total_Banks) × 100
```

**Example:**
- County X has 10 total banks
- 7 banks are exempt (<1,000 loans)
- `Pct_Exempt = (7 / 10) × 100 = 70.0%`

**Interpretation:**
- **High percentage (80-90%+):** Most banks in that county would stop reporting
- **Low percentage (<50%):** Most banks in that county would continue reporting

---

### 5. **Loans_Exempt_Banks**
**Definition:** Total number of loans made in the county by banks that are exempt (<1,000 total loans nationwide).

**Calculation:**
```sql
SUM(CASE WHEN lender_total_loans_2024 < 1000 THEN loans_in_county ELSE 0 END)
```

**Step-by-step:**
1. For each bank-county combination, calculate loans in that county
2. If the bank's total nationwide loans < 1,000, include those loans
3. Sum all loans from exempt banks in that county

**Important:** This counts loans **in that specific county** from exempt banks, not the exempt banks' total loans.

**Example:**
- Bank A (exempt, 500 total loans) has 200 loans in County X
- Bank B (exempt, 800 total loans) has 150 loans in County X
- Bank C (not exempt, 2,000 total loans) has 300 loans in County X
- `Loans_Exempt_Banks in County X = 200 + 150 = 350`

---

## Key Concepts

### Exemption is Based on Nationwide Totals
- A bank's exemption status is determined by its **total loans across all counties**, not just in one county
- A bank with 500 loans total is exempt everywhere it operates
- A bank with 2,000 loans total is not exempt anywhere it operates

### County-Level Impact
- The map shows **where exempt banks operate**, not where they're headquartered
- A county with high `Pct_Exempt` means most banks operating there would stop reporting
- This affects the availability of lending data in that county

### Data Source
- **Source Table:** `sb.disclosure` (original disclosure table, not 1071_1k_lenders)
- **Year:** 2024 only
- **Loan Counts:** Sum of `num_under_100k + num_100k_250k + num_250k_1m`

---

## Connecticut Counties Note

Connecticut counties may appear differently because:
- Some Connecticut counties have unusual FIPS codes or naming conventions
- The geo table join might not match all Connecticut counties correctly
- Some counties might have no bank data in 2024

If Connecticut is missing, it could be:
1. No disclosure data for Connecticut in 2024
2. FIPS code mismatch in the geo table join
3. County names not matching between disclosure and geo tables

