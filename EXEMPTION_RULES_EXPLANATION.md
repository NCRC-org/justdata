# 1071 Exemption Rules - Explanation

## The Exemption Rule

**A bank is EXEMPT from 1071 reporting if:**
- The bank made **fewer than 1,000 total loans nationwide** in 2024

**A bank is NOT EXEMPT (must report) if:**
- The bank made **1,000 or more total loans nationwide** in 2024

## Key Points

1. **Nationwide Total**: The exemption is based on the bank's **total loans across ALL counties**, not just loans in one county.

2. **Per Year**: This is calculated for each year (2024 in our case).

3. **All or Nothing**: A bank is either exempt everywhere it operates, or not exempt anywhere. You can't be exempt in one county and not exempt in another.

## Example

**Bank A:**
- 500 loans in County X
- 300 loans in County Y
- 200 loans in County Z
- **Total: 1,000 loans nationwide**
- **Status: NOT EXEMPT** (exactly at the threshold)

**Bank B:**
- 800 loans in County X
- 100 loans in County Y
- **Total: 900 loans nationwide**
- **Status: EXEMPT** (< 1,000)

**Bank C:**
- 50 loans in County X
- 50 loans in County Y
- **Total: 100 loans nationwide**
- **Status: EXEMPT** (< 1,000)

## What We're Calculating

For each county, we calculate:

1. **Total_Banks**: How many unique banks operate in that county (have loans there)

2. **Exempt_Banks**: Of those banks, how many have <1,000 total loans nationwide

3. **Pct_Exempt**: (Exempt_Banks / Total_Banks) × 100

4. **Loans_Exempt_Banks**: Total loans in the county from exempt banks

5. **Pct_Loans_Exempt**: (Loans from exempt banks / Total loans in county) × 100

## Why High-Activity Counties Might Show High Exemption %

This could be CORRECT if:

- **Many small banks** (exempt) operate in the county
- **Few large banks** (non-exempt) also operate there
- The large banks make **most of the loans**, but there are **more small banks**

**Example Scenario:**
- County has 10 banks total
- 8 are small banks (exempt, <1K loans each) → 8,000 loans total
- 2 are large banks (non-exempt, >1K loans each) → 100,000 loans total
- **Pct_Exempt = 80%** (8 out of 10 banks)
- **Pct_Loans_Exempt = 7.4%** (8K out of 108K loans)

This would explain why you see high exemption % for BANKS but the county still has high lending activity.

## What to Look For

**If results are CORRECT:**
- High `Pct_Exempt` (banks) BUT low `Pct_Loans_Exempt` (loans)
- This means: Many small banks, but large banks make most loans

**If there's an ERROR:**
- High `Pct_Exempt` (banks) AND high `Pct_Loans_Exempt` (loans)
- This would be unusual and might indicate a calculation problem

## Our Calculation Logic

1. ✅ Calculate each bank's total loans nationwide (across all counties)
2. ✅ Mark banks as exempt if total < 1,000
3. ✅ For each county, count how many exempt banks operate there
4. ✅ Calculate percentage of banks that are exempt
5. ✅ Calculate percentage of loans from exempt banks

The logic appears correct. The key is comparing `Pct_Exempt` (banks) vs `Pct_Loans_Exempt` (loans) to verify results make sense.
