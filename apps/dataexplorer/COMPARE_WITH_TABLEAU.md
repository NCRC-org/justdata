# Comparing DataExplorer Query with Tableau Query

## Purpose
To identify why DataExplorer area analysis shows incorrect loan numbers compared to Tableau.

## Steps

1. **Run a DataExplorer Area Analysis** with specific counties/years that you know the correct numbers for
   - This will generate a query in `dataexplorer_query_log.sql`
   - This will also log the query in `dataexplorer_bigquery_queries.log`

2. **Run the same analysis in Tableau**
   - Note the exact counties and years used
   - Note the loan count/amount results

3. **Compare the queries:**
   - DataExplorer query: Check `dataexplorer_query_log.sql` or `dataexplorer_bigquery_queries.log`
   - Tableau query: Check BigQuery query history or export from Tableau

4. **Key differences to look for:**
   - How geoids are matched (county_code format)
   - How loans are counted (COUNT vs SUM)
   - Deduplication logic
   - Filtering logic (action_taken, loan_purpose, etc.)
   - Grouping/aggregation structure

## Files to Check

- `dataexplorer_query_log.sql` - Latest DataExplorer query
- `dataexplorer_bigquery_queries.log` - All BigQuery queries executed
- BigQuery Console → Query History - To see Tableau queries

## What to Share

Please share:
1. The Tableau query (from BigQuery query history)
2. The counties/years used in both
3. The loan numbers from Tableau vs DataExplorer
4. Any filters applied in Tableau

