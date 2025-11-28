"""
Production script to enrich ALL CURRENT and GRACE PERIOD members with:
- Website discovery
- Staff/contact information extraction
- Organization information (funders, partners, areas of work)
- Form 990 data (comprehensive financials, officers, board members)

Exports results to JSON format with checkpointing for resuming.
"""
import sys
from pathlib import Path
import pandas as pd
import json
import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any

# Add parent directory to path
BASE_DIR = Path(__file__).parent.parent.parent.parent  # Go up to #JustData_Repo
sys.path.insert(0, str(BASE_DIR))

# Also add the memberview app directory
MEMBERVIEW_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(MEMBERVIEW_DIR))

from apps.memberview.data_utils import MemberDataLoader
from apps.memberview.utils.website_enricher import WebsiteEnricher
from apps.memberview.utils.propublica_client import ProPublicaClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_output_file() -> Path:
    """Get output file path for enriched data."""
    output_dir = Path(__file__).parent.parent / "data" / "enriched_data"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return output_dir / f"enriched_members_{timestamp}.json"


def get_checkpoint_file() -> Path:
    """Get checkpoint file path."""
    output_dir = Path(__file__).parent.parent / "data" / "enriched_data"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / "enrichment_checkpoint.json"


def load_checkpoint() -> Dict[str, Any]:
    """Load checkpoint data if exists."""
    checkpoint_file = get_checkpoint_file()
    if checkpoint_file.exists():
        try:
            with open(checkpoint_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load checkpoint: {e}")
    return {'processed_ids': [], 'last_index': 0}


def save_checkpoint(processed_ids: list, last_index: int):
    """Save checkpoint data."""
    checkpoint_file = get_checkpoint_file()
    checkpoint_data = {
        'processed_ids': processed_ids,
        'last_index': last_index,
        'timestamp': datetime.now().isoformat()
    }
    try:
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
    except Exception as e:
        logger.warning(f"Could not save checkpoint: {e}")


def enrich_all_members(
    output_file: Optional[Path] = None,
    start_from: int = 0,
    limit: Optional[int] = None,
    checkpoint_interval: int = 10
):
    """
    Enrich all CURRENT and GRACE PERIOD members with comprehensive data.
    
    Args:
        output_file: Path to output JSON file (auto-generated if None)
        start_from: Start from this index (for resuming)
        limit: Maximum number of members to process (None for all)
        checkpoint_interval: Save checkpoint every N members
    """
    # Initialize
    loader = MemberDataLoader()
    website_enricher = WebsiteEnricher()
    propublica_client = ProPublicaClient()
    
    # Get all CURRENT and GRACE PERIOD members
    logger.info("Loading member data...")
    members_df = loader.get_members()
    
    # Filter to CURRENT and GRACE PERIOD
    status_col = None
    for col in members_df.columns:
        col_lower = col.lower()
        if 'membership' in col_lower and 'status' in col_lower:
            status_col = col
            break
    
    if status_col:
        current_members = members_df[
            members_df[status_col].isin(['CURRENT', 'GRACE PERIOD'])
        ].copy()
        logger.info(f"Found {len(current_members)} CURRENT and GRACE PERIOD members")
    else:
        logger.warning("Could not find membership status column, processing all members")
        current_members = members_df.copy()
    
    # Find column names
    record_id_col = None
    name_col = None
    city_col = None
    state_col = None
    
    for col in current_members.columns:
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
    
    # Load checkpoint
    checkpoint = load_checkpoint()
    processed_ids = set(checkpoint.get('processed_ids', []))
    start_idx = max(start_from, checkpoint.get('last_index', 0))
    
    # Determine members to process
    total_members = len(current_members)
    if limit:
        end_idx = min(start_idx + limit, total_members)
    else:
        end_idx = total_members
    
    members_to_process = current_members.iloc[start_idx:end_idx]
    logger.info(f"Processing {len(members_to_process)} members (indices {start_idx} to {end_idx-1})")
    
    # Setup output file
    if output_file is None:
        output_file = get_output_file()
    
    # Load existing results if resuming
    enriched_results = []
    if output_file.exists() and start_idx > 0:
        try:
            with open(output_file, 'r') as f:
                enriched_results = json.load(f)
            logger.info(f"Loaded {len(enriched_results)} existing results from {output_file}")
        except Exception as e:
            logger.warning(f"Could not load existing results: {e}")
    
    # Process each member
    stats = {
        'total': len(members_to_process),
        'processed': 0,
        'websites_found': 0,
        'staff_found': 0,
        'form_990_found': 0,
        'errors': 0
    }
    
    for idx, (_, row) in enumerate(members_to_process.iterrows(), start=start_idx):
        member_id = str(row[record_id_col])
        
        # Skip if already processed
        if member_id in processed_ids:
            logger.info(f"[{idx+1}/{total_members}] Skipping {row[name_col]} (already processed)")
            continue
        
        company_name = str(row[name_col]) if pd.notna(row[name_col]) else ''
        city = str(row[city_col]) if city_col and pd.notna(row[city_col]) else None
        state = str(row[state_col]) if state_col and pd.notna(row[state_col]) else None
        
        if not company_name:
            logger.warning(f"[{idx+1}/{total_members}] Skipping member {member_id} (no company name)")
            continue
        
        logger.info(f"[{idx+1}/{total_members}] Processing: {company_name}")
        
        # Initialize enriched data structure
        enriched = {
            'member_id': member_id,
            'company_name': company_name,
            'city': city,
            'state': state,
            'enrichment_date': datetime.now().isoformat(),
            'website': None,
            'staff': [],
            'contacts': {},
            'organization_info': {},
            'form_990': {'found': False}
        }
        
        try:
            # 1. Website discovery and extraction
            logger.info(f"  [SEARCH] Searching for website...")
            website_result = website_enricher.find_website(company_name, city, state)
            
            if website_result:
                url, confidence = website_result
                enriched['website'] = {
                    'url': url,
                    'confidence': confidence,
                    'found': True
                }
                stats['websites_found'] += 1
                logger.info(f"  [OK] Found website: {url} (confidence: {confidence:.2f})")
                
                # Extract comprehensive info from website
                logger.info(f"  [EXTRACT] Extracting comprehensive info from {url}...")
                
                # Staff information
                try:
                    staff = website_enricher.extract_staff_info(url)
                    if staff:
                        enriched['staff'] = staff
                        stats['staff_found'] += 1
                        logger.info(f"  [OK] Found {len(staff)} staff/board members")
                    else:
                        logger.info(f"  [INFO] No staff information found")
                except Exception as e:
                    logger.warning(f"  [ERROR] Error extracting staff: {e}")
                
                # Contact information
                try:
                    contacts = website_enricher.extract_contact_info(url)
                    if contacts:
                        enriched['contacts'] = contacts
                        logger.info(f"  [OK] Found contact information")
                    else:
                        logger.info(f"  [INFO] No contact information found")
                except Exception as e:
                    logger.warning(f"  [ERROR] Error extracting contacts: {e}")
                
                # Organization information
                try:
                    org_info = website_enricher.extract_organization_info(url)
                    if org_info:
                        enriched['organization_info'] = org_info
                        funders_count = len(org_info.get('funders_partners', []))
                        areas_count = len(org_info.get('major_areas_of_work', []))
                        affiliations_count = len(org_info.get('affiliations', []))
                        if funders_count > 0 or areas_count > 0 or affiliations_count > 0:
                            logger.info(f"  [OK] Found org info: {funders_count} funders/partners, {areas_count} areas of work, {affiliations_count} affiliations")
                        else:
                            logger.info(f"  [INFO] No additional organization info found")
                except Exception as e:
                    logger.warning(f"  [ERROR] Error extracting organization info: {e}")
            else:
                enriched['website'] = {'url': None, 'confidence': 0, 'found': False}
                logger.info(f"  [MISSING] No website found")
            
            # 2. Form 990 data
            logger.info(f"  [SEARCH] Searching for Form 990 data...")
            form_990_data = propublica_client.enrich_member_with_form_990(
                company_name=company_name,
                city=city,
                state=state,
                ein=None
            )
            
            if form_990_data and form_990_data.get('found'):
                enriched['form_990'] = form_990_data
                financials = form_990_data.get('financials', {})
                if financials and financials.get('ein'):
                    stats['form_990_found'] += 1
                    logger.info(f"  [OK] Found Form 990 data (EIN: {financials.get('ein')})")
                else:
                    logger.info(f"  [OK] Found Form 990 data")
            else:
                enriched['form_990'] = {'found': False}
                logger.info(f"  [MISSING] No Form 990 data found")
            
            stats['processed'] += 1
            processed_ids.add(member_id)
            
        except Exception as e:
            logger.error(f"  [ERROR] Error processing {company_name}: {e}")
            enriched['error'] = str(e)
            stats['errors'] += 1
        
        # Add to results
        enriched_results.append(enriched)
        
        # Save checkpoint and incremental results
        if (idx + 1) % checkpoint_interval == 0:
            save_checkpoint(list(processed_ids), idx + 1)
            save_results(enriched_results, output_file)
            logger.info(f"  [CHECKPOINT] Saved progress (processed {idx + 1}/{total_members})")
        
        # Rate limiting between members
        if idx < end_idx - 1:  # Don't wait after last member
            time.sleep(2)  # 2 second delay between members
    
    # Final save
    save_checkpoint(list(processed_ids), end_idx)
    save_results(enriched_results, output_file)
    
    # Print summary
    logger.info("=" * 80)
    logger.info("ENRICHMENT COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Total members processed: {stats['processed']}")
    logger.info(f"Websites found: {stats['websites_found']}")
    logger.info(f"Staff info extracted: {stats['staff_found']}")
    logger.info(f"Form 990 data found: {stats['form_990_found']}")
    logger.info(f"Errors: {stats['errors']}")
    logger.info(f"Results saved to: {output_file}")
    logger.info("=" * 80)


def save_results(results: list, output_file: Path):
    """Save enriched results to JSON file."""
    try:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        logger.debug(f"Saved {len(results)} results to {output_file}")
    except Exception as e:
        logger.error(f"Error saving results: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Enrich all CURRENT and GRACE PERIOD members with comprehensive data"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output JSON file path (auto-generated if not specified)"
    )
    parser.add_argument(
        "--start-from",
        type=int,
        default=0,
        help="Start from this index (for resuming)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of members to process (None for all)"
    )
    parser.add_argument(
        "--checkpoint-interval",
        type=int,
        default=10,
        help="Save checkpoint every N members (default: 10)"
    )
    
    args = parser.parse_args()
    
    output_file = Path(args.output) if args.output else None
    
    enrich_all_members(
        output_file=output_file,
        start_from=args.start_from,
        limit=args.limit,
        checkpoint_interval=args.checkpoint_interval
    )



