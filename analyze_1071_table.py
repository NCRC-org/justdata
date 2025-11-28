#!/usr/bin/env python3
"""
Analyze the 1071_1k_lenders table and show summary statistics.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps'))

from bizsight.utils.bigquery_client import BigQueryClient


def analyze_table():
    """Analyze the 1071_1k_lenders table."""
    print("=" * 80)
    print("1071_1K_LENDERS TABLE ANALYSIS")
    print("=" * 80)
    print()
    
    bq_client = BigQueryClient()
    table_id = f"{bq_client.project_id}.misc.1071_1k_lenders"
    
    # Summary by year
    sql = f"""
    SELECT 
      CAST(year AS INT64) AS year,
      COUNT(*) AS total_records,
      COUNT(DISTINCT respondent_id) AS unique_lenders,
      COUNT(DISTINCT CASE WHEN is_credit_card_lender = 1 THEN respondent_id END) AS credit_card_lenders,
      COUNT(DISTINCT CASE WHEN is_credit_card_lender = 0 THEN respondent_id END) AS non_credit_card_lenders,
      COUNT(DISTINCT CASE WHEN qualification_status = 'Qualifies' THEN respondent_id END) AS qualified_lenders,
      COUNT(DISTINCT CASE WHEN qualification_status = 'Does Not Qualify' THEN respondent_id END) AS not_qualified_lenders
    FROM `{table_id}`
    GROUP BY CAST(year AS INT64)
    ORDER BY year
    """
    
    print("Querying table for summary statistics...")
    print()
    
    try:
        result = bq_client.query(sql)
        rows = list(result)
        
        print("=" * 80)
        print("SUMMARY BY YEAR")
        print("=" * 80)
        print()
        print(f"{'Year':<8} {'Total':<12} {'Unique':<12} {'Credit Card':<15} {'Non-Card':<12} {'Qualified':<12} {'Not Qual':<12}")
        print(f"{'':<8} {'Records':<12} {'Lenders':<12} {'Lenders':<15} {'Lenders':<12} {'Lenders':<12} {'Lenders':<12}")
        print("-" * 80)
        
        total_records = 0
        total_lenders = set()
        total_cc_lenders = set()
        total_qualified = set()
        
        for row in rows:
            year = row.year
            records = row.total_records
            lenders = row.unique_lenders
            cc_lenders = row.credit_card_lenders or 0
            non_cc_lenders = row.non_credit_card_lenders or 0
            qualified = row.qualified_lenders or 0
            not_qualified = row.not_qualified_lenders or 0
            
            print(f"{year:<8} {records:<12,} {lenders:<12,} {cc_lenders:<15,} {non_cc_lenders:<12,} {qualified:<12,} {not_qualified:<12,}")
            
            total_records += records
        
        print("-" * 80)
        print(f"{'TOTAL':<8} {total_records:<12,}")
        print()
        
        # Overall statistics
        overall_sql = f"""
        SELECT 
          COUNT(*) AS total_records,
          COUNT(DISTINCT respondent_id) AS total_unique_lenders,
          COUNT(DISTINCT CASE WHEN is_credit_card_lender = 1 THEN respondent_id END) AS total_cc_lenders,
          COUNT(DISTINCT CASE WHEN is_credit_card_lender = 0 THEN respondent_id END) AS total_non_cc_lenders,
          COUNT(DISTINCT CASE WHEN qualification_status = 'Qualifies' THEN respondent_id END) AS total_qualified
        FROM `{table_id}`
        """
        
        overall_result = bq_client.query(overall_sql)
        overall = list(overall_result)[0]
        
        print("=" * 80)
        print("OVERALL STATISTICS")
        print("=" * 80)
        print()
        print(f"Total records: {overall.total_records:,}")
        print(f"Total unique lenders: {overall.total_unique_lenders:,}")
        print(f"  - Credit card lenders: {overall.total_cc_lenders or 0:,}")
        print(f"  - Non-credit card lenders: {overall.total_non_cc_lenders or 0:,}")
        print(f"  - Qualified lenders (non-card, 1000+ loans consecutive years): {overall.total_qualified or 0:,}")
        print()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 80)


if __name__ == '__main__':
    analyze_table()

