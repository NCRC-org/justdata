"""
Follow-up script to re-enrich members that missed data in the initial run.
Specifically targets members that:
- Did not find a website (or found one with low confidence)
- Did not find Form 990 data

Uses Google Custom Search API as a fallback for website discovery.
"""
import sys
from pathlib import Path
import json
import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any, List

# Add parent directory to path
BASE_DIR = Path(__file__).parent.parent.parent.parent  # Go up to #JustData_Repo
sys.path.insert(0, str(BASE_DIR))

# Also add the memberview app directory
MEMBERVIEW_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(MEMBERVIEW_DIR))

from apps.memberview.utils.website_enricher import WebsiteEnricher
from apps.memberview.utils.propublica_client import ProPublicaClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_members_needing_reprocessing(enriched_file: Path) -> List[Dict[str, Any]]:
    """
    Find members that need re-processing:
    - No website found, OR
    - Website found but confidence < 0.80, OR
    - No Form 990 data found
    """
    logger.info(f"Loading enriched data from {enriched_file}...")
    
    try:
        with open(enriched_file, 'r') as f:
            all_members = json.load(f)
    except Exception as e:
        logger.error(f"Error loading enriched file: {e}")
        return []
    
    members_needing_reprocessing = []
    
    for member in all_members:
        needs_reprocessing = False
        reasons = []
        
        # Check website
        website = member.get('website', {})
        if not website.get('found') or not website.get('url'):
            needs_reprocessing = True
            reasons.append("no website")
        elif website.get('confidence', 0) < 0.80:
            needs_reprocessing = True
            reasons.append(f"low website confidence ({website.get('confidence', 0):.2f})")
        
        # Check Form 990
        form_990 = member.get('form_990', {})
        if not form_990.get('found'):
            needs_reprocessing = True
            reasons.append("no Form 990 data")
        
        if needs_reprocessing:
            member['_reprocessing_reasons'] = reasons
            members_needing_reprocessing.append(member)
    
    logger.info(f"Found {len(members_needing_reprocessing)} members needing re-processing")
    logger.info(f"  Reasons: {sum(1 for m in members_needing_reprocessing if 'no website' in m.get('_reprocessing_reasons', []))} missing websites")
    logger.info(f"  Reasons: {sum(1 for m in members_needing_reprocessing if 'low website confidence' in str(m.get('_reprocessing_reasons', [])))} low confidence websites")
    logger.info(f"  Reasons: {sum(1 for m in members_needing_reprocessing if 'no Form 990 data' in m.get('_reprocessing_reasons', []))} missing Form 990")
    
    return members_needing_reprocessing


def reprocess_member(member: Dict[str, Any], use_google: bool = True) -> Dict[str, Any]:
    """
    Re-process a single member with enhanced search (Google Custom Search).
    
    Args:
        member: Member data dictionary
        use_google: Whether to use Google Custom Search (requires API key)
    
    Returns:
        Updated member dictionary
    """
    company_name = member.get('company_name', '')
    city = member.get('city')
    state = member.get('state')
    
    logger.info(f"Re-processing: {company_name}")
    
    website_enricher = WebsiteEnricher()
    propublica_client = ProPublicaClient()
    
    # Track what we're trying to fix
    reasons = member.get('_reprocessing_reasons', [])
    needs_website = any('website' in r for r in reasons)
    needs_form_990 = 'no Form 990 data' in reasons
    
    # 1. Re-try website discovery with Google if needed
    if needs_website:
        logger.info(f"  [RETRY] Re-searching for website (using Google if available)...")
        
        # If Google is available and we want to use it, temporarily enable it
        # (The WebsiteEnricher will automatically try Google if DuckDuckGo fails)
        website_result = website_enricher.find_website(company_name, city, state)
        
        if website_result:
            url, confidence = website_result
            old_website = member.get('website', {})
            old_url = old_website.get('url')
            old_confidence = old_website.get('confidence', 0)
            
            # Update if we got a better result
            if not old_url or (confidence > old_confidence and confidence >= 0.80):
                member['website'] = {
                    'url': url,
                    'confidence': confidence,
                    'found': True,
                    'updated': True,
                    'previous_url': old_url,
                    'previous_confidence': old_confidence
                }
                logger.info(f"  [OK] Found/updated website: {url} (confidence: {confidence:.2f})")
                
                # Re-extract data from new/better website
                try:
                    staff = website_enricher.extract_staff_info(url)
                    if staff:
                        member['staff'] = staff
                        logger.info(f"  [OK] Extracted {len(staff)} staff/board members")
                    
                    contacts = website_enricher.extract_contact_info(url)
                    if contacts:
                        member['contacts'] = contacts
                        logger.info(f"  [OK] Extracted contact information")
                    
                    org_info = website_enricher.extract_organization_info(url)
                    if org_info:
                        member['organization_info'] = org_info
                        logger.info(f"  [OK] Extracted organization information")
                except Exception as e:
                    logger.warning(f"  [ERROR] Error extracting data from website: {e}")
            else:
                logger.info(f"  [INFO] No better website found (current: {old_url}, new: {url})")
        else:
            logger.info(f"  [MISSING] Still no website found")
    
    # 2. Re-try Form 990 search if needed
    if needs_form_990:
        logger.info(f"  [RETRY] Re-searching for Form 990 data...")
        
        # Try with more search term variations
        form_990_data = propublica_client.enrich_member_with_form_990(
            company_name=company_name,
            city=city,
            state=state,
            ein=None
        )
        
        if form_990_data and form_990_data.get('found'):
            member['form_990'] = form_990_data
            financials = form_990_data.get('financials', {})
            if financials and financials.get('ein'):
                logger.info(f"  [OK] Found Form 990 data (EIN: {financials.get('ein')})")
            else:
                logger.info(f"  [OK] Found Form 990 data")
            member['form_990']['updated'] = True
        else:
            logger.info(f"  [MISSING] Still no Form 990 data found")
    
    # Update enrichment date
    member['reprocessed_date'] = datetime.now().isoformat()
    member['reprocessing_reasons'] = reasons
    
    return member


def reprocess_missing_data(
    enriched_file: Path,
    output_file: Optional[Path] = None,
    use_google: bool = True
):
    """
    Re-process members that missed data in the initial enrichment.
    
    Args:
        enriched_file: Path to the original enriched JSON file
        output_file: Path to output file (updates original if None)
        use_google: Whether to use Google Custom Search (requires API key)
    """
    # Find members needing re-processing
    members_to_reprocess = find_members_needing_reprocessing(enriched_file)
    
    if not members_to_reprocess:
        logger.info("No members need re-processing. All data is complete!")
        return
    
    # Load all members
    logger.info(f"Loading all members from {enriched_file}...")
    with open(enriched_file, 'r') as f:
        all_members = json.load(f)
    
    # Create lookup by member_id
    members_by_id = {m.get('member_id'): m for m in all_members}
    
    # Re-process each member
    stats = {
        'total': len(members_to_reprocess),
        'processed': 0,
        'websites_found': 0,
        'form_990_found': 0,
        'errors': 0
    }
    
    logger.info(f"Re-processing {stats['total']} members...")
    
    for idx, member in enumerate(members_to_reprocess, 1):
        member_id = member.get('member_id')
        company_name = member.get('company_name', 'Unknown')
        
        logger.info(f"[{idx}/{stats['total']}] Re-processing: {company_name}")
        
        try:
            updated_member = reprocess_member(member, use_google=use_google)
            
            # Update in the main dictionary
            if member_id in members_by_id:
                # Merge updates
                original = members_by_id[member_id]
                
                # Update website if we got a better one
                if updated_member.get('website', {}).get('updated'):
                    original['website'] = updated_member['website']
                    if updated_member.get('staff'):
                        original['staff'] = updated_member['staff']
                    if updated_member.get('contacts'):
                        original['contacts'] = updated_member['contacts']
                    if updated_member.get('organization_info'):
                        original['organization_info'] = updated_member['organization_info']
                    stats['websites_found'] += 1
                
                # Update Form 990 if we found it
                if updated_member.get('form_990', {}).get('updated'):
                    original['form_990'] = updated_member['form_990']
                    stats['form_990_found'] += 1
                
                # Add reprocessing metadata
                original['reprocessed_date'] = updated_member.get('reprocessed_date')
                original['reprocessing_reasons'] = updated_member.get('reprocessing_reasons')
            
            stats['processed'] += 1
            
        except Exception as e:
            logger.error(f"  [ERROR] Error re-processing {company_name}: {e}")
            stats['errors'] += 1
        
        # Rate limiting
        if idx < stats['total']:
            time.sleep(2)  # 2 second delay between members
    
    # Save updated results
    if output_file is None:
        output_file = enriched_file
    
    logger.info(f"Saving updated results to {output_file}...")
    try:
        with open(output_file, 'w') as f:
            json.dump(list(members_by_id.values()), f, indent=2, default=str)
        logger.info(f"Saved {len(members_by_id)} members to {output_file}")
    except Exception as e:
        logger.error(f"Error saving results: {e}")
    
    # Print summary
    logger.info("=" * 80)
    logger.info("RE-PROCESSING COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Total members re-processed: {stats['processed']}")
    logger.info(f"Websites found/updated: {stats['websites_found']}")
    logger.info(f"Form 990 data found: {stats['form_990_found']}")
    logger.info(f"Errors: {stats['errors']}")
    logger.info(f"Updated results saved to: {output_file}")
    logger.info("=" * 80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Re-process members that missed data in initial enrichment"
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Path to the enriched JSON file from initial run"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output JSON file path (updates input file if not specified)"
    )
    parser.add_argument(
        "--no-google",
        action="store_true",
        help="Don't use Google Custom Search (DuckDuckGo only)"
    )
    
    args = parser.parse_args()
    
    input_file = Path(args.input)
    if not input_file.exists():
        logger.error(f"Input file not found: {input_file}")
        sys.exit(1)
    
    output_file = Path(args.output) if args.output else None
    
    reprocess_missing_data(
        enriched_file=input_file,
        output_file=output_file,
        use_google=not args.no_google
    )



