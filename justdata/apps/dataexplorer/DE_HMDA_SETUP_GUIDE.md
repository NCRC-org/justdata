# Step-by-Step Guide: Setting Up `justdata.de_hmda` Table

This guide walks you through creating and populating the optimized `justdata.de_hmda` table for DataExplorer.

---

## Prerequisites

- Access to BigQuery Console (project: `hdma1-242116`)
- Permissions to create tables in the `justdata` dataset
- Access to source tables: `hmda.hmda`, `shared.census`, `shared.cbsa_to_county`, `hmda.lenders18`

---

## Step 1: Verify Dataset Exists

1. **Open BigQuery Console**
   - Go to: https://console.cloud.google.com/bigquery
   - Select project: `hdma1-242116`

2. **Check if `justdata` dataset exists**
   ```sql
   SELECT schema_name 
   FROM `hdma1-242116.INFORMATION_SCHEMA.SCHEMATA`
   WHERE schema_name = 'justdata';
   ```

3. **If dataset doesn't exist, create it:**
   - In BigQuery Console, click "..." next to project name
   - Select "Create dataset"
   - Dataset ID: `justdata`
   - Location: `US` (or your preferred location)
   - Click "Create dataset"

---

## Step 2: Test with a Small Sample First (Recommended)

Before creating the full table, test with a single year to verify the logic works correctly.

1. **Open the SQL script**
   - File: `apps/dataexplorer/create_de_hmda_table.sql`
   - Copy the entire SELECT statement (everything after `AS`)

2. **Modify for testing (add WHERE clause)**
   ```sql
   -- Test with just 2024 data
   CREATE OR REPLACE TABLE `hdma1-242116.justdata.de_hmda_test`
   PARTITION BY activity_year
   CLUSTER BY geoid5, lei, loan_purpose
   AS
   SELECT
     -- ... (paste full SELECT from create_de_hmda_table.sql)
   FROM `hdma1-242116.hmda.hmda` h
   -- ... (paste all JOINs from create_de_hmda_table.sql)
   WHERE h.activity_year = 2024  -- TEST: Only one year
   LIMIT 10000;  -- TEST: Limit to 10k rows for quick test
   ```

3. **Run the test query**
   - Paste into BigQuery Console
   - Click "Run"
   - Wait for completion (should be fast with 10k rows)

4. **Verify the test table**
   ```sql
   -- Check row count
   SELECT COUNT(*) as row_count
   FROM `hdma1-242116.justdata.de_hmda_test`;
   
   -- Check race/ethnicity flags
   SELECT 
     COUNTIF(is_hispanic) as hispanic_count,
     COUNTIF(is_black) as black_count,
     COUNTIF(is_asian) as asian_count,
     COUNTIF(is_white) as white_count,
     COUNTIF(is_multi_racial) as multi_racial_count,
     COUNTIF(is_hispanic AND is_multi_racial) as hispanic_and_multi_racial  -- Should be 0
   FROM `hdma1-242116.justdata.de_hmda_test`;
   
   -- Check that multi-racial and individual races don't overlap
   SELECT 
     COUNTIF(is_multi_racial AND is_black) as multi_racial_and_black,  -- Should be 0
     COUNTIF(is_multi_racial AND is_white) as multi_racial_and_white,  -- Should be 0
     COUNTIF(is_multi_racial AND is_asian) as multi_racial_and_asian  -- Should be 0
   FROM `hdma1-242116.justdata.de_hmda_test`;
   ```

5. **If test looks good, proceed to Step 3. If not, review the SQL logic.**

---

## Step 3: Create the Full Table

Once testing is successful, create the full table with all years.

1. **Open the full SQL script**
   - File: `apps/dataexplorer/create_de_hmda_table.sql`
   - Read through it to understand what it does

2. **Estimate cost and time**
   - The full table will process millions of rows
   - This may take **several hours** and cost **$10-50** depending on data size
   - BigQuery charges by data processed, not storage

3. **Run the full CREATE TABLE query**
   ```sql
   -- Copy the ENTIRE contents of create_de_hmda_table.sql
   -- Paste into BigQuery Console
   -- Click "Run"
   ```

4. **Monitor progress**
   - BigQuery will show progress in the console
   - You can check job status in "Job history"
   - **Don't close the browser** - the query will continue running

5. **Expected completion time:**
   - Small dataset (1-2 years): 10-30 minutes
   - Medium dataset (5-10 years): 1-3 hours
   - Large dataset (20+ years): 3-8 hours

---

## Step 4: Verify the Full Table

After the table is created, verify it's correct:

1. **Check row counts by year**
   ```sql
   SELECT 
     activity_year,
     COUNT(*) as row_count
   FROM `hdma1-242116.justdata.de_hmda`
   GROUP BY activity_year
   ORDER BY activity_year DESC;
   ```

2. **Compare with source HMDA table**
   ```sql
   -- Source HMDA
   SELECT 
     activity_year,
     COUNT(*) as source_count
   FROM `hdma1-242116.hmda.hmda`
   WHERE activity_year >= 2018
   GROUP BY activity_year
   ORDER BY activity_year DESC;
   
   -- de_hmda (should match or be close)
   SELECT 
     activity_year,
     COUNT(*) as de_hmda_count
   FROM `hdma1-242116.justdata.de_hmda`
   GROUP BY activity_year
   ORDER BY activity_year DESC;
   ```

3. **Verify race/ethnicity flags**
   ```sql
   SELECT 
     activity_year,
     COUNTIF(is_hispanic) as hispanic_count,
     COUNTIF(is_black) as black_count,
     COUNTIF(is_asian) as asian_count,
     COUNTIF(is_white) as white_count,
     COUNTIF(is_multi_racial) as multi_racial_count,
     COUNTIF(is_hispanic AND is_multi_racial) as hispanic_and_multi_racial,  -- Should be 0
     COUNTIF(is_multi_racial AND is_black) as multi_racial_and_black,  -- Should be 0
     COUNTIF(is_multi_racial AND is_white) as multi_racial_and_white,  -- Should be 0
     COUNT(*) as total_rows
   FROM `hdma1-242116.justdata.de_hmda`
   WHERE activity_year = 2024  -- Test with one year
   GROUP BY activity_year;
   ```

4. **Verify pre-computed flags work**
   ```sql
   -- Test that flags are populated
   SELECT 
     COUNTIF(is_hispanic) as has_hispanic_flag,
     COUNTIF(is_black) as has_black_flag,
     COUNTIF(is_asian) as has_asian_flag,
     COUNTIF(is_lmib) as has_lmib_flag,
     COUNTIF(is_lmict) as has_lmict_flag
   FROM `hdma1-242116.justdata.de_hmda`
   WHERE activity_year = 2024
   LIMIT 1000;
   ```

---

## Step 5: Set Up Automatic Updates

Set up a scheduled query to automatically add new years when HMDA data is released.

1. **Go to Scheduled Queries**
   - In BigQuery Console, click "Scheduled Queries" in left sidebar
   - Click "Create Scheduled Query"

2. **Configure the scheduled query**
   - **Name**: `update_de_hmda_incremental`
   - **Description**: "Automatically update justdata.de_hmda when new HMDA data is available"
   - **Schedule**: 
     - Frequency: **Monthly** (HMDA data is typically released annually)
     - Start date: Today
     - Time: Choose off-peak hours (e.g., 2 AM)

3. **Set the query**
   - Open file: `apps/dataexplorer/update_de_hmda_incremental.sql`
   - Copy the entire contents
   - Paste into the scheduled query editor

4. **Set destination**
   - Destination: `justdata.de_hmda`
   - Write preference: **WRITE_APPEND** (only add new rows, don't overwrite)

5. **Set notifications** (Optional but recommended)
   - Email on failure: Your email address
   - Email on success: (optional)

6. **Save and enable**
   - Click "Save"
   - Toggle "Enable" to ON

7. **Test the scheduled query manually** (Optional)
   - Click "Run now" to test it immediately
   - It should only process years that don't exist in `de_hmda` yet
   - If all years already exist, it will insert 0 rows (which is fine)

---

## Step 6: Update Application Code

Now update DataExplorer to use the new `de_hmda` table instead of `hmda.hmda`.

1. **Find SQL templates that use `hmda.hmda`**
   ```bash
   # Search for references to hmda.hmda
   grep -r "hmda.hmda" apps/dataexplorer/
   grep -r "hmda.hmda" apps/lendsight/sql_templates/
   ```

2. **Update SQL templates**
   - File: `apps/lendsight/sql_templates/mortgage_report.sql`
   - Replace: `FROM \`hdma1-242116.hmda.hmda\` h`
   - With: `FROM \`hdma1-242116.justdata.de_hmda\` h`

3. **Simplify race/ethnicity calculations**
   - Instead of complex CASE statements, use the pre-computed flags:
   ```sql
   -- OLD (complex):
   SUM(CASE 
     WHEN (h.applicant_ethnicity_1 IN ('1','11','12','13','14') OR ...)
     AND (complex multi-racial check...)
     THEN 1 ELSE 0 
   END) as hispanic_originations
   
   -- NEW (simple):
   COUNTIF(h.is_hispanic) as hispanic_originations
   ```

4. **Remove joins that are already in de_hmda**
   - Remove: `LEFT JOIN ... shared.cbsa_to_county` (county_state is already in de_hmda)
   - Remove: `LEFT JOIN ... hmda.lenders18` (lender_name, lender_type already in de_hmda)
   - Remove: `LEFT JOIN ... shared.census` (geoid5 normalization already done)

5. **Update income category calculations**
   - Replace complex income calculations with pre-computed flags:
   ```sql
   -- OLD:
   SUM(CASE 
     WHEN h.income IS NOT NULL AND h.ffiec_msa_md_median_family_income IS NOT NULL
     AND (CAST(h.income AS FLOAT64) * 1000.0) / CAST(h.ffiec_msa_md_median_family_income AS FLOAT64) * 100.0 <= 80.0
     THEN 1 ELSE 0 
   END) as lmib_originations
   
   -- NEW:
   COUNTIF(h.is_lmib) as lmib_originations
   ```

6. **See usage guide for examples**
   - File: `apps/dataexplorer/DE_HMDA_TABLE_USAGE.md`
   - Contains detailed examples of how to update SQL templates

---

## Step 7: Test the Updated Application

1. **Run a test analysis**
   - Go to DataExplorer
   - Run an area analysis for a small area (single county, single year)
   - Verify results match previous results (or are close)

2. **Compare query performance**
   - Check BigQuery query logs
   - New queries should be **5-10x faster**
   - Query costs should be **5-10x lower**

3. **Verify race/ethnicity counts**
   - Compare race/ethnicity counts with previous reports
   - They should match (or be very close)

---

## Step 8: Monitor and Maintain

1. **Monitor scheduled query**
   - Check "Scheduled Queries" → "Execution history"
   - Verify it runs monthly and completes successfully
   - Check email notifications for any failures

2. **Monitor table size**
   ```sql
   -- Check table size and cost
   SELECT 
     COUNT(*) as total_rows,
     COUNT(DISTINCT activity_year) as years,
     MIN(activity_year) as min_year,
     MAX(activity_year) as max_year,
     -- Estimate storage cost (first 10GB free, then $0.02/GB/month)
     (COUNT(*) * 200) / 1024 / 1024 / 1024 as estimated_gb
   FROM `hdma1-242116.justdata.de_hmda`;
   ```

3. **Handle data corrections** (if needed)
   - If HMDA data for an existing year is corrected:
   ```sql
   -- Delete existing data for that year
   DELETE FROM `hdma1-242116.justdata.de_hmda`
   WHERE activity_year = 2024;  -- Replace with year to refresh
   
   -- Re-run the INSERT for that year (modify create_de_hmda_table.sql)
   -- Add WHERE h.activity_year = 2024 to the SELECT
   ```

---

## Troubleshooting

### Issue: "Dataset justdata not found"
**Solution**: Create the dataset first (Step 1)

### Issue: "Permission denied"
**Solution**: Ensure you have BigQuery Data Editor and Job User roles

### Issue: Query times out or runs too long
**Solution**: 
- Run for fewer years at a time
- Use `LIMIT` to test with smaller dataset first
- Check if table is properly partitioned/clustered

### Issue: Race/ethnicity counts don't match
**Solution**:
- Verify the logic in `create_de_hmda_table.sql` matches `mortgage_report.sql`
- Check for NULL handling differences
- Compare sample rows between source and de_hmda

### Issue: Scheduled query fails
**Solution**:
- Check error message in execution history
- Verify the incremental query logic is correct
- Ensure destination table exists and is writable

---

## Summary Checklist

- [ ] Step 1: Verify/create `justdata` dataset
- [ ] Step 2: Test with small sample (single year, 10k rows)
- [ ] Step 3: Create full table (all years)
- [ ] Step 4: Verify table is correct (row counts, flags, no overlaps)
- [ ] Step 5: Set up scheduled query for automatic updates
- [ ] Step 6: Update application SQL templates to use `de_hmda`
- [ ] Step 7: Test updated application
- [ ] Step 8: Monitor and maintain

---

## Next Steps

After setup is complete:
1. Update all SQL templates to use `de_hmda`
2. Deploy updated application
3. Monitor query performance improvements
4. Celebrate 5-10x faster queries! 🎉

---

## Questions?

If you run into issues:
1. Check the troubleshooting section above
2. Review the verification queries in Step 4
3. Compare with the original SQL template logic
4. Check BigQuery job logs for error details

