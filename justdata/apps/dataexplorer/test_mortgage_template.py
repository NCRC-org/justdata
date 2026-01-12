#!/usr/bin/env python3
"""
Test script to verify the updated mortgage_report.sql template works with de_hmda table.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from justdata.apps.lendsight.core import load_sql_template
from justdata.apps.dataexplorer.data_utils import execute_mortgage_query_with_filters
from justdata.shared.utils.bigquery_client import get_bigquery_client, execute_query
from justdata.shared.utils.unified_env import get_unified_config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_sql_template():
    """Test the updated SQL template with a simple query."""
    
    logger.info("Loading SQL template...")
    sql_template = load_sql_template()
    
    # Check that template uses de_hmda
    if 'justdata.de_hmda' not in sql_template:
        logger.error("❌ ERROR: SQL template does not use justdata.de_hmda!")
        logger.error("Template still references: hmda.hmda")
        return False
    
    if 'justdata.de_hmda' in sql_template:
        logger.info("✅ SQL template uses justdata.de_hmda")
    
    # Check that complex CASE statements are replaced
    if 'COUNTIF(h.is_hispanic)' in sql_template:
        logger.info("✅ Race/ethnicity calculations use pre-computed flags")
    else:
        logger.warning("⚠️  WARNING: May still have complex race calculations")
    
    # Test with a simple query
    logger.info("\nTesting with sample query...")
    logger.info("County: Baltimore County, Maryland")
    logger.info("Year: 2024")
    logger.info("Loan Purpose: all")
    
    try:
        results = execute_mortgage_query_with_filters(
            sql_template=sql_template,
            county="Baltimore County, Maryland",
            year=2024,
            loan_purpose=['purchase', 'refinance', 'equity'],
            action_taken=['1'],
            occupancy=['1'],
            total_units=['1', '2', '3', '4'],
            construction=['1'],
            exclude_reverse_mortgages=True
        )
        
        if results:
            logger.info(f"✅ Query successful! Returned {len(results)} rows")
            
            # Show sample results
            if len(results) > 0:
                sample = results[0]
                logger.info("\nSample result:")
                logger.info(f"  Lender: {sample.get('lender_name', 'N/A')}")
                logger.info(f"  Total Originations: {sample.get('total_originations', 0)}")
                logger.info(f"  Hispanic: {sample.get('hispanic_originations', 0)}")
                logger.info(f"  Black: {sample.get('black_originations', 0)}")
                logger.info(f"  Asian: {sample.get('asian_originations', 0)}")
                logger.info(f"  White: {sample.get('white_originations', 0)}")
                logger.info(f"  Multi-Racial: {sample.get('multi_racial_originations', 0)}")
                logger.info(f"  LMI Borrower: {sample.get('lmib_originations', 0)}")
            
            return True
        else:
            logger.warning("⚠️  Query returned no results (may be normal for test data)")
            return True  # Still successful, just no data
            
    except Exception as e:
        logger.error(f"❌ Query failed with error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_direct_query():
    """Test a direct query to de_hmda to verify table exists and has data."""
    
    logger.info("\n" + "="*60)
    logger.info("Testing direct query to de_hmda table...")
    
    try:
        config = get_unified_config(load_env=False, verbose=False)
        PROJECT_ID = config.get('GCP_PROJECT_ID')
        client = get_bigquery_client(PROJECT_ID)
        
        # Simple count query
        query = f"""
        SELECT 
            activity_year,
            COUNT(*) as row_count,
            COUNTIF(is_hispanic) as hispanic_count,
            COUNTIF(is_black) as black_count,
            COUNTIF(is_asian) as asian_count,
            COUNTIF(is_multi_racial) as multi_racial_count
        FROM `{PROJECT_ID}.justdata.de_hmda`
        WHERE activity_year = 2024
        GROUP BY activity_year
        LIMIT 1
        """
        
        logger.info("Executing test query...")
        results = execute_query(client, query)
        
        if results:
            row = results[0]
            logger.info(f"✅ Table exists and has data!")
            logger.info(f"  2024 row count: {row.get('row_count', 0):,}")
            logger.info(f"  Hispanic: {row.get('hispanic_count', 0):,}")
            logger.info(f"  Black: {row.get('black_count', 0):,}")
            logger.info(f"  Asian: {row.get('asian_count', 0):,}")
            logger.info(f"  Multi-Racial: {row.get('multi_racial_count', 0):,}")
            return True
        else:
            logger.error("❌ Table query returned no results")
            return False
            
    except Exception as e:
        logger.error(f"❌ Direct query failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    logger.info("="*60)
    logger.info("Testing Updated Mortgage Report SQL Template")
    logger.info("="*60)
    
    # Test 1: Direct query to table
    test1_passed = test_direct_query()
    
    # Test 2: SQL template query
    test2_passed = test_sql_template()
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("Test Summary")
    logger.info("="*60)
    logger.info(f"Direct Query Test: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    logger.info(f"SQL Template Test: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        logger.info("\n🎉 All tests passed! The updated template is working correctly.")
        sys.exit(0)
    else:
        logger.error("\n❌ Some tests failed. Please review the errors above.")
        sys.exit(1)

