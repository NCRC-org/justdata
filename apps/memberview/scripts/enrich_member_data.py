"""
Script to enrich member data with website, contact, and staff information.
"""
import sys
from pathlib import Path

# Add parent directory to path
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from apps.memberview.data_utils import MemberDataLoader
from apps.memberview.utils.website_enricher import WebsiteEnricher
import pandas as pd
import logging
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def enrich_members(limit: Optional[int] = None, start_from: int = 0):
    """
    Enrich member data with website, contact, and staff information.
    
    Args:
        limit: Maximum number of members to process (None for all)
        start_from: Start from this index (for resuming)
    """
    loader = MemberDataLoader()
    enricher = WebsiteEnricher()
    
    # Get all members
    members_df = loader.get_members()
    
    # Find columns
    record_id_col = None
    name_col = None
    city_col = None
    state_col = None
    
    for col in members_df.columns:
        col_lower = col.lower()
        if 'record id' in col_lower:
            record_id_col = col
        elif 'company' in col_lower and 'name' in col_lower:
            name_col = col
        elif col_lower == 'city':
            city_col = col
        elif col_lower == 'state/region' or (col_lower == 'state' and 'country' not in col_lower):
            state_col = col
    
    if not record_id_col or not name_col:
        logger.error("Required columns not found")
        return
    
    # Process members
    total = len(members_df)
    if limit:
        total = min(total, limit)
    
    logger.info(f"Enriching {total} members (starting from index {start_from})")
    
    enriched_data = []
    
    for idx, row in tqdm(members_df.iloc[start_from:start_from+total if limit else None].iterrows(), 
                        total=total, desc="Enriching members"):
        company_name = str(row[name_col]) if name_col and pd.notna(row[name_col]) else ''
        city = str(row[city_col]) if city_col and pd.notna(row[city_col]) else None
        state = str(row[state_col]) if state_col and pd.notna(row[state_col]) else None
        
        if not company_name:
            continue
        
        member_id = str(row[record_id_col])
        
        logger.info(f"Processing: {company_name} ({city}, {state})")
        
        # Enrich
        enriched = enricher.enrich_member(company_name, city, state)
        
        enriched_data.append({
            'member_id': member_id,
            'company_name': company_name,
            'city': city,
            'state': state,
            **enriched
        })
        
        # Save progress every 10 members
        if len(enriched_data) % 10 == 0:
            save_enriched_data(enriched_data)
    
    # Final save
    save_enriched_data(enriched_data)
    logger.info(f"Enrichment complete. Processed {len(enriched_data)} members.")


def save_enriched_data(data: list):
    """Save enriched data to JSON file."""
    output_file = Path(__file__).parent.parent / "data" / "enriched_data" / "enriched_members.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    import json
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    logger.info(f"Saved enriched data to {output_file}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Enrich member data with website information")
    parser.add_argument("--limit", type=int, help="Limit number of members to process")
    parser.add_argument("--start-from", type=int, default=0, help="Start from this index")
    args = parser.parse_args()
    
    enrich_members(limit=args.limit, start_from=args.start_from)




