#!/usr/bin/env python3
"""
Analyze the 1071_1k_Lenders table by year to verify it meets requirements.

For each year, shows:
1. Total number of lenders
2. How many have average loan amount > $10,000
3. How many of those made 1000+ loans in that year AND the previous year
"""

import sys
import os

# Add the apps directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps'))

from bizsight.utils.bigquery_client import BigQueryClient


def analyze_by_year():
    """Analyze lender qualification data by year."""
    print("=" * 80)
    print("LENDER QUALIFICATION ANALYSIS BY YEAR")
    print("=" * 80)
    print()
    
    bq_client = BigQueryClient()
    table_id = f"{bq_client.project_id}.misc.1071_1k_lenders"
    
    # Query to analyze by year
    sql = f"""
WITH yearly_loans AS (
  SELECT 
    CAST(year AS INT64) AS year,
    respondent_id,
    lender_type,
    qualification_status,
    SUM(COALESCE(num_under_100k, 0) + COALESCE(num_100k_250k, 0) + COALESCE(num_250k_1m, 0)) AS loans_this_year
  FROM `{table_id}`
  GROUP BY CAST(year AS INT64), respondent_id, lender_type, qualification_status
),
yearly_stats AS (
  SELECT 
    year,
    COUNT(DISTINCT respondent_id) AS total_lenders,
    -- Count credit card lenders
    COUNT(DISTINCT CASE 
      WHEN lender_type = 'Credit Card Lender' THEN respondent_id 
    END) AS credit_card_lenders,
    -- Count non-credit card lenders (avg loan amount > $10k for this year)
    COUNT(DISTINCT CASE 
      WHEN lender_type = 'Not Credit Card Lender' THEN respondent_id 
    END) AS lenders_avg_over_10k,
    -- Count lenders with >= 1000 loans in this year (non-credit card only)
    COUNT(DISTINCT CASE 
      WHEN lender_type = 'Not Credit Card Lender' 
        AND loans_this_year >= 1000 
      THEN respondent_id 
    END) AS lenders_1000_plus_this_year
  FROM yearly_loans
  GROUP BY year
),
consecutive_qualifiers AS (
  SELECT 
    curr.year,
    COUNT(DISTINCT curr.respondent_id) AS count_qualify
  FROM yearly_loans curr
  INNER JOIN yearly_loans prev
    ON curr.respondent_id = prev.respondent_id
    AND curr.year = prev.year + 1
  WHERE curr.lender_type = 'Not Credit Card Lender'
    AND prev.lender_type = 'Not Credit Card Lender'
    AND curr.loans_this_year >= 1000
    AND prev.loans_this_year >= 1000
  GROUP BY curr.year
)
SELECT 
  s.year,
  s.total_lenders,
  s.credit_card_lenders,
  s.lenders_avg_over_10k,
  s.lenders_1000_plus_this_year,
  COALESCE(c.count_qualify, 0) AS lenders_qualify_consecutive_with_10k_avg
FROM yearly_stats s
LEFT JOIN consecutive_qualifiers c
  ON s.year = c.year
ORDER BY s.year
"""
    
    print("Querying table...")
    print(f"Table: {table_id}")
    print()
    
    try:
        query_job = bq_client.query(sql)
        result = query_job.result()
        
        print("=" * 80)
        print("RESULTS BY YEAR")
        print("=" * 80)
        print()
        print(f"{'Year':<8} {'Total':<12} {'Credit Card':<15} {'Avg>$10k':<12} {'1000+ Loans':<15} {'Qualify*':<12}")
        print(f"{'':<8} {'Lenders':<12} {'Lenders':<15} {'Lenders':<12} {'This Year':<15} {'Consecutive':<12}")
        print("-" * 80)
        
        for row in result:
            year = row.year
            total = row.total_lenders
            credit_card = row.credit_card_lenders
            avg_over_10k = row.lenders_avg_over_10k
            loans_1000_plus = row.lenders_1000_plus_this_year
            qualify = row.lenders_qualify_consecutive_with_10k_avg
            
            print(f"{year:<8} {total:<12,} {credit_card:<15,} {avg_over_10k:<12,} {loans_1000_plus:<15,} {qualify:<12,}")
        
        print()
        print("* Qualify = >= 1000 loans in this year AND previous year, with avg loan amount >= $10k")
        print("  (Credit card lenders are excluded from qualification)")
        print()
        print("=" * 80)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    analyze_by_year()

