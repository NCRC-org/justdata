# Testing Checklist for de_hmda Migration

## ✅ Completed Steps

1. ✅ Created `justdata.de_hmda` table in BigQuery
2. ✅ Updated `mortgage_report.sql` template to use `de_hmda`
3. ✅ Simplified all race/ethnicity calculations
4. ✅ Simplified all income/tract calculations
5. ✅ Removed unnecessary JOINs

## 🧪 Testing Steps

### Step 1: Verify Table Data
Run the queries in `verify_de_hmda.sql`:
- ✅ Row counts by year match source HMDA
- ✅ Race/ethnicity flags are populated correctly
- ✅ No overlaps (multi-racial + Hispanic = 0, etc.)
- ✅ Income flags are populated
- ✅ Lender information is populated

### Step 2: Test SQL Template
Run the test query in `test_de_hmda_query.sql`:
- ✅ Query executes without errors
- ✅ Returns expected number of rows
- ✅ Race/ethnicity counts are reasonable
- ✅ Query completes quickly (should be 5-10x faster)

### Step 3: Test Area Analysis
1. Go to DataExplorer
2. Run an area analysis for a small area:
   - Single county (e.g., "Baltimore County, Maryland")
   - Single year (e.g., 2024)
   - All loan purposes
3. Verify:
   - ✅ Analysis completes successfully
   - ✅ Results match previous results (or are very close)
   - ✅ Query time is significantly faster
   - ✅ No errors in logs

### Step 4: Test Lender Analysis
1. Go to DataExplorer
2. Run a lender analysis:
   - Select a lender
   - Single county
   - Single year
3. Verify:
   - ✅ Analysis completes successfully
   - ✅ Results are reasonable
   - ✅ No errors

### Step 5: Compare Results
Compare new results with previous results:
- ✅ Total originations match (or are close)
- ✅ Race/ethnicity breakdowns match (or are close)
- ✅ Income category breakdowns match (or are close)
- ✅ Any differences are explainable (e.g., data corrections)

## 📝 Files That May Need Updates (Non-Critical)

These files have direct queries to `hmda.hmda` but may not be critical for main analysis:

1. **`lender_analysis_core.py`** (lines 196, 589, 921, 1101, 1251)
   - Status: May need updates for lender-specific queries
   - Action: Test lender analysis first, update if needed

2. **`app.py`** (line 829)
   - Status: Check if this is used in main flow
   - Action: Test first, update if needed

3. **`data_utils.py`** (line 710)
   - Status: Check if this is used in main flow
   - Action: Test first, update if needed

4. **Test files** (`test_*.py`, `check_*.py`)
   - Status: Not critical for production
   - Action: Update later if needed

## 🚨 If Issues Arise

### Issue: Results don't match
- Check if `de_hmda` table has all years
- Verify race/ethnicity flags are calculated correctly
- Compare sample rows between `hmda.hmda` and `de_hmda`

### Issue: Query errors
- Check BigQuery console for error details
- Verify table exists: `SELECT COUNT(*) FROM \`hdma1-242116.justdata.de_hmda\``
- Check column names match (activity_year is INT64, not STRING)

### Issue: Performance not improved
- Check if query is actually using `de_hmda` table
- Verify table is partitioned and clustered correctly
- Check BigQuery query execution details

## ✅ Success Criteria

- [ ] All verification queries pass
- [ ] Test query executes successfully
- [ ] Area analysis works and is faster
- [ ] Lender analysis works (if applicable)
- [ ] Results match previous results (within 1-2% tolerance)
- [ ] Query performance improved (5-10x faster)

## 📊 Performance Monitoring

After deployment, monitor:
- Query execution times (should be 5-10x faster)
- BigQuery costs (should be 5-10x lower per query)
- Error rates (should be same or lower)
- User feedback on analysis speed

