# Verifying 1071 Exemption Rule

## From Original SQL File (1071_table_sql.txt)

The SQL file shows:
- **"Qualification"** requires: >= 1,000 loans in **consecutive years** (current year AND previous year)
- Lines 47-57: `qualified` CTE checks for banks with >= 1000 loans in current year AND previous year

## Current Exemption Calculation

I'm currently calculating exemption as:
- **Exempt if:** < 1,000 total loans nationwide in 2024
- **Not Exempt if:** >= 1,000 total loans nationwide in 2024

## Question: What is the ACTUAL Exemption Rule?

Based on the original requirements, I need to verify:

1. **Is exemption based on:**
   - Single year threshold (< 1,000 loans in 2024)? ← What I'm currently using
   - OR consecutive years threshold (< 1,000 loans in 2024 AND 2023)? ← What "qualification" uses

2. **The user mentioned:**
   - "Overall, 75% of banks would no longer report"
   - This suggests exemption is based on a single year threshold
   - But I should verify this is correct

## Need to Confirm

The exemption rule should be clarified:
- If it's simply < 1,000 loans in 2024 → My calculation is correct
- If it requires consecutive years → I need to update the logic

Based on the user's data showing "Large Banks <1 K loans" in Table 1, it appears exemption is based on a single year threshold, not consecutive years.

