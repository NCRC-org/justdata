#!/usr/bin/env python3
"""
Generate metros JSON file from BigQuery.
This script fetches all metros from the geo.cbsa_to_county table
and saves them to a JSON file for fast client-side loading.
"""

import json
import sys
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(repo_root))

from justdata.shared.utils.bigquery_client import get_bigquery_client, execute_query
from justdata.apps.dataexplorer.config import PROJECT_ID, STATIC_DIR

def generate_metros_json():
    """Fetch all metros from BigQuery and save to JSON file.
    
    Handles duplicate CBSAs (e.g., Bridgeport) by preferring:
    1. CBSAs with more counties (more comprehensive)
    2. For Connecticut: CBSAs that include planning regions (09110-09190)
    3. Higher CBSA codes (typically newer definitions)
    """
    try:
        print("Fetching metros from BigQuery...")
        
        # Query to get distinct CBSAs, preferring current definitions
        # For duplicates (same CBSA code with different names), prefer names with more counties and CT planning regions
        query = f"""
        WITH cbsa_counts AS (
            SELECT 
                CAST(cbsa_code AS STRING) as code,
                CBSA as name,
                COUNT(DISTINCT geoid5) as county_count,
                -- Check if this CBSA includes CT planning regions (09110-09190)
                COUNTIF(CAST(geoid5 AS STRING) LIKE '091%' 
                       AND CAST(geoid5 AS STRING) >= '09110' 
                       AND CAST(geoid5 AS STRING) <= '09190') as ct_planning_region_count
            FROM `{PROJECT_ID}.geo.cbsa_to_county`
            WHERE cbsa_code IS NOT NULL
              AND CBSA IS NOT NULL
              AND TRIM(CBSA) != ''
            GROUP BY code, name
        ),
        ranked_cbsas AS (
            SELECT 
                code,
                name,
                county_count,
                ct_planning_region_count,
                ROW_NUMBER() OVER (
                    PARTITION BY code 
                    ORDER BY 
                        -- Prefer names with CT planning regions
                        ct_planning_region_count DESC,
                        -- Then prefer names with more counties
                        county_count DESC,
                        -- Finally prefer longer names (typically more complete)
                        LENGTH(name) DESC
                ) as rn
            FROM cbsa_counts
        )
        SELECT 
            code,
            name
        FROM ranked_cbsas
        WHERE rn = 1
        ORDER BY name
        """
        
        client = get_bigquery_client(PROJECT_ID)
        results = execute_query(client, query)
        
        # Results are already sorted by name from the query
        metros = results
        
        print(f"Found {len(metros)} metros (after deduplication)")
        
        # Create data directory if it doesn't exist
        data_dir = STATIC_DIR / 'data'
        data_dir.mkdir(exist_ok=True)
        
        # Save to JSON file
        output_file = data_dir / 'metros.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'success': True,
                'metros': metros,
                'count': len(metros)
            }, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(metros)} metros to {output_file}")
        return True
        
    except Exception as e:
        print(f"Error generating metros JSON: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = generate_metros_json()
    sys.exit(0 if success else 1)
