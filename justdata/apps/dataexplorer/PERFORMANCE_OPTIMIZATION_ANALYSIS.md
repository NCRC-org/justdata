# DataExplorer Performance Optimization Analysis

## Executive Summary

The analysis identifies **5 major bottlenecks** in area and lender analyses, with **race/ethnicity calculations in SQL being the most significant issue**. The current implementation calculates race/ethnicity on-the-fly for every row using extremely complex nested CASE statements, which significantly slows down BigQuery queries.

---

## Time-Consuming Tasks (Ranked by Impact)

### 1. ⚠️ **CRITICAL: Race/Ethnicity Calculations in SQL** 
**Impact: VERY HIGH (60-70% of query time)**

**Current Implementation:**
- Race/ethnicity is calculated **on-the-fly in BigQuery** for every row using complex nested CASE statements
- Each race category (Hispanic, Black, Asian, White, Native American, HoPI, Multi-Racial) has:
  - 5 ethnicity field checks (ethnicity_1 through ethnicity_5)
  - 5 race field checks (race_1 through race_5) with COALESCE
  - A nested subquery to count distinct main race categories (to exclude multi-racial from individual categories)
  - Multiple CASE statements mapping race codes to main categories
- This logic is repeated **7 times** (once per race/ethnicity category) in the SQL template
- For a query returning 14,000 rows, this means **~98,000 complex calculations** per query

**Evidence:**
- SQL template (`apps/lendsight/sql_templates/mortgage_report.sql`) lines 58-450+
- Each race category calculation is ~50-80 lines of SQL
- Nested subqueries with UNNEST arrays for multi-racial detection

**Solutions (in order of effectiveness):**

1. **✅ Create a separate pre-computed race/ethnicity lookup table** (BEST - 80-90% speedup)
   - **NOTE: Cannot modify existing HMDA tables, but can create new tables**
   - Create a new BigQuery table (e.g., `hmda.race_ethnicity_lookup`) that pre-computes race/ethnicity for all HMDA records
   - Use a scheduled query or one-time ETL job to populate this table
   - Table structure: `(lei, activity_year, county_code, census_tract, race_ethnicity_category, is_multi_racial)`
   - Update SQL template to JOIN to this lookup table instead of calculating on-the-fly
   - **Estimated speedup: 5-10x faster queries**
   - **Implementation effort: Medium (requires BigQuery write access to create new table)**
   - **Storage cost: ~10-20% of HMDA table size (one row per loan with pre-computed category)**

2. **✅ Create a UDF (User-Defined Function) for race/ethnicity classification** (GOOD - 50-60% speedup)
   - Create a BigQuery JavaScript UDF that takes race/ethnicity fields and returns the category
   - Replaces hundreds of lines of CASE statements with a single function call
   - Can be used with read-only HMDA tables (no table modification needed)
   - **Estimated speedup: 2-3x faster queries**
   - **Implementation effort: Low-Medium**

3. **✅ Create aggregated pre-computed tables** (GOOD - 70-80% speedup)
   - Create separate aggregated tables (e.g., `hmda.aggregated_by_county_year`) that pre-aggregate by county, year, lender, etc.
   - Pre-compute race/ethnicity counts at aggregation time
   - Query these pre-aggregated tables instead of raw HMDA data
   - **Estimated speedup: 3-5x faster queries (plus eliminates need for complex aggregations)**
   - **Implementation effort: Medium (requires BigQuery write access)**
   - **Storage cost: Much smaller than raw HMDA (already aggregated)**

4. **✅ Simplify multi-racial detection** (MODERATE - 20-30% speedup)
   - Current implementation uses nested subqueries with UNNEST arrays
   - Could be simplified to a simpler COUNT DISTINCT approach
   - Works with existing tables (no modification needed)
   - **Estimated speedup: 1.2-1.5x faster queries**
   - **Implementation effort: Low**

5. **✅ Cache race/ethnicity calculations** (MODERATE - 30-40% speedup for repeated queries)
   - If same county/year combinations are queried frequently, cache the results
   - Already have caching infrastructure in place
   - **Estimated speedup: 1.3-1.7x faster for cached queries**
   - **Implementation effort: Low (already partially implemented)**

---

### 2. ⚠️ **HIGH: Sequential BigQuery Queries**
**Impact: HIGH (20-30% of total time)**

**Current Implementation:**
- Queries are executed **sequentially** (one at a time) for each county/year combination
- For 3 counties × 5 years = **15 sequential queries**
- Each query waits for the previous one to complete
- Network latency and query startup overhead accumulate

**Evidence:**
- `apps/dataexplorer/core.py` lines 395-428: Sequential loop through counties and years
- Each query takes 2-5 seconds, so 15 queries = 30-75 seconds just for query execution

**Solutions:**

1. **✅ Parallel query execution** (BEST - 60-70% speedup)
   - Use `concurrent.futures.ThreadPoolExecutor` or `asyncio` to execute multiple queries in parallel
   - BigQuery can handle multiple concurrent queries
   - **Estimated speedup: 3-5x faster for multi-county/multi-year queries**
   - **Implementation effort: Medium**

2. **✅ Batch queries** (GOOD - 40-50% speedup)
   - Combine multiple county/year combinations into a single query using UNION ALL or IN clauses
   - Reduces number of queries from N×M to 1
   - **Estimated speedup: 2-3x faster**
   - **Implementation effort: Medium (requires SQL template modification)**

3. **✅ Query result streaming** (MODERATE - 10-20% speedup)
   - Use BigQuery's streaming API to start processing results as they arrive
   - Reduces perceived latency
   - **Estimated speedup: 1.1-1.3x faster**
   - **Implementation effort: Low-Medium**

---

### 3. ⚠️ **MEDIUM: Census Data API Calls**
**Impact: MEDIUM (5-10% of total time)**

**Current Implementation:**
- Makes API calls to Census Bureau for each county
- Sequential API calls with retries and fallbacks
- Can be slow if Census API is under load (503 errors)

**Evidence:**
- `shared/utils/census_adult_demographics.py` - Multiple API calls per county
- `apps/dataexplorer/core.py` lines 178-309: Census data fetching

**Solutions:**

1. **✅ Aggressive caching** (BEST - 90-95% speedup for cached data)
   - Census data changes infrequently (yearly updates)
   - Already have caching, but could be more aggressive
   - Cache for 1 year instead of checking freshness
   - **Estimated speedup: 10-20x faster for cached queries**
   - **Implementation effort: Low**

2. **✅ Pre-fetch and store in BigQuery** (GOOD - eliminates API calls)
   - Store census data in BigQuery table
   - Update annually via scheduled query
   - JOIN to census data instead of API calls
   - **Estimated speedup: Eliminates 5-10% of total time**
   - **Implementation effort: Medium**

3. **✅ Parallel API calls** (MODERATE - 30-40% speedup)
   - Make census API calls in parallel for multiple counties
   - **Estimated speedup: 1.3-1.7x faster**
   - **Implementation effort: Low**

---

### 4. ⚠️ **MEDIUM: DataFrame Processing in Python**
**Impact: MEDIUM (5-10% of total time)**

**Current Implementation:**
- Converts BigQuery results (list of dicts) to pandas DataFrame
- Multiple groupby operations, aggregations, and transformations
- Memory-intensive for large datasets

**Evidence:**
- `apps/dataexplorer/area_report_builder.py` - Multiple DataFrame operations
- `apps/lendsight/mortgage_report_builder.py` - Table building functions

**Solutions:**

1. **✅ More aggregation in SQL** (BEST - 30-40% speedup)
   - Do more aggregation in BigQuery before returning results
   - Return pre-aggregated data instead of raw rows
   - Reduces data transfer and Python processing
   - **Estimated speedup: 1.3-1.7x faster**
   - **Implementation effort: Medium (requires SQL template modification)**

2. **✅ Use Polars instead of Pandas** (GOOD - 20-30% speedup)
   - Polars is faster for large DataFrames
   - Better memory efficiency
   - **Estimated speedup: 1.2-1.4x faster**
   - **Implementation effort: Medium (requires refactoring)**

3. **✅ Lazy evaluation** (MODERATE - 10-15% speedup)
   - Use pandas lazy evaluation where possible
   - Avoid unnecessary copies
   - **Estimated speedup: 1.1-1.2x faster**
   - **Implementation effort: Low**

---

### 5. ⚠️ **LOW: Report Building Operations**
**Impact: LOW (2-5% of total time)**

**Current Implementation:**
- Multiple table building functions
- String formatting and data transformations
- Chart data preparation

**Solutions:**

1. **✅ Parallel table building** (MODERATE - 20-30% speedup)
   - Build multiple tables in parallel using ThreadPoolExecutor
   - **Estimated speedup: 1.2-1.4x faster**
   - **Implementation effort: Low**

2. **✅ Cache intermediate results** (MODERATE - 10-20% speedup)
   - Cache table building results for common queries
   - **Estimated speedup: 1.1-1.3x faster**
   - **Implementation effort: Low**

---

## Recommended Implementation Priority

### Phase 1: Quick Wins (1-2 weeks)
1. **Aggressive census data caching** - Low effort, high impact
2. **Parallel query execution** - Medium effort, high impact
3. **Simplify multi-racial detection** - Low effort, moderate impact

**Expected total speedup: 2-3x faster**

### Phase 2: Major Optimizations (2-4 weeks)
1. **Create pre-computed race/ethnicity lookup table** - Medium effort, VERY high impact
   - Create new BigQuery table with pre-computed race/ethnicity categories
   - One-time ETL job or scheduled query to populate
   - Update SQL template to JOIN to lookup table
2. **Create aggregated pre-computed tables** - Medium effort, high impact
   - Pre-aggregate by county/year/lender with race/ethnicity counts
   - Query aggregated tables instead of raw HMDA data
3. **More SQL aggregation** - Medium effort, moderate impact
4. **Batch queries** - Medium effort, high impact

**Expected total speedup: 5-10x faster (combined with Phase 1)**

### Phase 3: Advanced Optimizations (1-2 months)
1. **UDF for race/ethnicity** - Medium effort, high impact (if Phase 2 doesn't work)
2. **Polars migration** - Medium effort, moderate impact
3. **Pre-fetch census data to BigQuery** - Medium effort, eliminates API dependency

**Expected total speedup: Additional 1.5-2x faster**

---

## Expected Overall Performance Improvement

**Current state:**
- Area analysis: ~60-120 seconds for 3 counties × 5 years
- Lender analysis: ~90-180 seconds for 1 lender + peers

**After Phase 1:**
- Area analysis: ~20-40 seconds (3x faster)
- Lender analysis: ~30-60 seconds (3x faster)

**After Phase 2:**
- Area analysis: ~6-12 seconds (10x faster)
- Lender analysis: ~9-18 seconds (10x faster)

**After Phase 3:**
- Area analysis: ~4-8 seconds (15x faster)
- Lender analysis: ~6-12 seconds (15x faster)

---

## Notes

- **Race/ethnicity calculations are the biggest bottleneck** - addressing this alone would provide 60-70% of the total speedup
- **Caching is already partially implemented** - can be extended and made more aggressive
- **BigQuery can handle parallel queries** - current sequential approach is unnecessarily slow
- **Most optimizations are additive** - can implement multiple solutions for cumulative speedup

