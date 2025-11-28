# Step-by-Step Guide: Comparing DataExplorer vs Tableau Queries

## Step 1: Run DataExplorer Area Analysis

1. **Open DataExplorer** in your browser:
   - Go to: `http://127.0.0.1:8085`
   - Make sure the server is running

2. **Set up your test case:**
   - Select **"Area Analysis"** tab
   - Choose **"HMDA"** as data type
   - Select **1-2 specific counties** (e.g., "Cook County, IL" or "Los Angeles County, CA")
   - Select **1-2 specific years** (e.g., 2023, 2024)
   - Note the loan numbers shown in the summary table

3. **Click "Analyze Area"** and wait for results

4. **Note the results:**
   - Write down the loan counts shown for each year
   - Example: "2023: 15,234 loans, 2024: 18,456 loans"

## Step 2: Find the DataExplorer Query

1. **Open the query log file:**
   - Navigate to: `#JustData_Repo/dataexplorer_query_log.sql`
   - This file contains the exact query that DataExplorer generated

2. **Copy the entire query** (or just share the file path and I can read it)

## Step 3: Run the Same Analysis in Tableau

1. **Open Tableau** and connect to BigQuery

2. **Recreate the exact same analysis:**
   - Use the **same counties** (e.g., "Cook County, IL")
   - Use the **same years** (e.g., 2023, 2024)
   - Apply the **same filters** (if any)
   - Get the loan counts

3. **Note the Tableau results:**
   - Write down the loan counts from Tableau
   - Example: "2023: 20,123 loans, 2024: 22,345 loans"

## Step 4: Get the Tableau Query from BigQuery

### Option A: BigQuery Console Query History (Easiest)

1. **Go to BigQuery Console:**
   - Open: https://console.cloud.google.com/bigquery
   - Make sure you're in the correct project: `hdma1-242116`

2. **View Query History:**
   - In the left sidebar, click **"Query history"** (or go to: https://console.cloud.google.com/bigquery?project=hdma1-242116&ws=!1m5!1m4!4m3!1sbigquery!2squery_history!3s)
   - You should see recent queries listed

3. **Find the Tableau query:**
   - Look for queries executed around the time you ran Tableau
   - Tableau queries often have recognizable patterns or you can identify them by timestamp
   - Click on the query to view it

4. **Copy the query:**
   - Click on the query row to expand it
   - Click **"Query text"** or the query itself
   - Copy the entire SQL query

### Option B: Tableau Query Log (Alternative)

1. **In Tableau Desktop:**
   - Go to **Help → Settings and Performance → Start Performance Recording**
   - Run your analysis
   - Go to **Help → Settings and Performance → Stop Performance Recording**
   - This will show the queries Tableau executed

### Option C: BigQuery Audit Logs (If you have access)

1. **Go to Cloud Logging:**
   - https://console.cloud.google.com/logs
   - Filter by: `resource.type="bigquery_project"` and `protoPayload.serviceName="bigquery"`
   - Find queries executed around the time you ran Tableau

## Step 5: Share the Information

Please share with me:

1. **The counties and years you tested:**
   - Example: "Cook County, IL - Years: 2023, 2024"

2. **DataExplorer results:**
   - The loan numbers shown
   - Example: "2023: 15,234 loans, $2.5B total"

3. **Tableau results:**
   - The loan numbers shown
   - Example: "2023: 20,123 loans, $3.2B total"

4. **The Tableau query:**
   - Either paste the SQL here, or tell me you've run it and I can check the query log file

5. **Any filters applied:**
   - Loan purpose, action taken, etc.

## What I'll Do

Once I have both queries, I will:
1. Compare the query structures
2. Identify differences in:
   - Geoid matching logic
   - Loan counting method
   - Filtering logic
   - Deduplication approach
3. Fix the DataExplorer query to match the correct Tableau approach

## Quick Test Case Suggestion

For a quick test, try:
- **County:** Cook County, IL (geoid: 17031)
- **Years:** 2023 only
- **No additional filters** (or use default filters)
- Compare the total loan count

This will give us a clear comparison point.

