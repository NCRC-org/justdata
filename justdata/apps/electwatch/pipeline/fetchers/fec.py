"""FEC (Federal Election Commission) data fetcher.

Consolidates the campaign-finance fetch logic that previously lived in
weekly_update.py:
- fetch_fec_crosswalk_ids   -- populate FEC IDs from local crosswalk
- fetch_incremental_fec_updates -- last-7-days OpenFEC pulls + BQ append
- _append_pac_contributions_to_bq -- BQ writer used by the incremental fetch
- fetch_fec_data            -- per-candidate totals from OpenFEC via crosswalk
- fetch_financial_pac_data  -- Schedule A receipts (PAC) by committee
- fetch_individual_financial_contributions -- delegated to services
"""
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

from justdata.apps.electwatch.pipeline.coordinator import ELECTION_CYCLE_START

logger = logging.getLogger(__name__)


def fetch_fec_crosswalk_ids(coordinator):
    """Populate FEC IDs from crosswalk (no API calls needed)."""
    logger.info("\n--- Populating FEC IDs from Crosswalk ---")

    try:
        from justdata.apps.electwatch.services.crosswalk import get_crosswalk
        crosswalk = get_crosswalk()

        crosswalk_matches = 0
        for official in coordinator.officials_data:
            bioguide_id = official.get('bioguide_id', '')
            if not bioguide_id:
                continue

            fec_id = crosswalk.get_fec_id(bioguide_id)
            if fec_id:
                official['fec_candidate_id'] = fec_id
                crosswalk_matches += 1

                # Also get additional IDs
                member_info = crosswalk.get_member_info(bioguide_id)
                if member_info:
                    if member_info.get('opensecrets_id'):
                        official['opensecrets_id'] = member_info['opensecrets_id']
                    if member_info.get('govtrack_id'):
                        official['govtrack_id'] = member_info['govtrack_id']

        logger.info(f"Crosswalk: Matched {crosswalk_matches}/{len(coordinator.officials_data)} officials with FEC IDs")

        coordinator.source_status['fec_crosswalk'] = {
            'status': 'success',
            'matches': crosswalk_matches,
            'total_officials': len(coordinator.officials_data),
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Crosswalk population failed: {e}")
        coordinator.source_status['fec_crosswalk'] = {'status': 'failed', 'error': str(e)}


def fetch_incremental_fec_updates(coordinator):
    """Fetch only the last 7 days of FEC data (incremental update).

    This is much faster than full FEC API pulls since:
    1. Bulk data is already in BigQuery (loaded separately)
    2. We only query FEC API for the last 7 days
    3. New contributions are appended to BigQuery tables
    """
    logger.info("\n--- Fetching Incremental FEC Updates (Last 7 Days) ---")

    import requests
    import time

    api_key = os.getenv('FEC_API_KEY')
    if not api_key:
        logger.warning("FEC_API_KEY not set - skipping incremental updates")
        coordinator.source_status['fec_incremental'] = {'status': 'skipped', 'reason': 'No API key'}
        return

    # Calculate 7-day window
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    min_date_str = start_date.strftime('%Y-%m-%d')
    max_date_str = end_date.strftime('%Y-%m-%d')

    logger.info(f"  Date window: {min_date_str} to {max_date_str}")

    # Get all Congress member FEC IDs
    fec_ids = [o.get('fec_candidate_id') for o in coordinator.officials_data if o.get('fec_candidate_id')]
    logger.info(f"  Checking {len(fec_ids)} Congress member FEC IDs")

    # Financial sector keywords
    FINANCIAL_KEYWORDS = [
        'BANK', 'FINANCIAL', 'CAPITAL', 'CREDIT', 'INSURANCE', 'INVEST',
        'SECURITIES', 'MORTGAGE', 'WELLS', 'CHASE', 'CITI', 'GOLDMAN',
        'MORGAN', 'BLACKROCK', 'FIDELITY', 'SCHWAB', 'PRUDENTIAL'
    ]

    new_pac_contributions = []
    new_individual_contributions = []
    api_calls = 0
    max_api_calls = 200  # Limit for 7-day incremental

    # Build bioguide lookup
    fec_to_bioguide = {o.get('fec_candidate_id'): o.get('bioguide_id')
                      for o in coordinator.officials_data if o.get('fec_candidate_id')}

    try:
        # Query recent PAC contributions (Schedule A from committees)
        logger.info("  Fetching recent PAC contributions...")
        url = 'https://api.open.fec.gov/v1/schedules/schedule_a/'

        for fec_id in fec_ids[:100]:  # Limit to 100 for speed
            if api_calls >= max_api_calls:
                logger.info(f"  Reached API limit ({max_api_calls}), stopping")
                break

            bioguide_id = fec_to_bioguide.get(fec_id)
            if not bioguide_id:
                continue

            params = {
                'api_key': api_key,
                'candidate_id': fec_id,
                'min_date': min_date_str,
                'max_date': max_date_str,
                'contributor_type': 'committee',
                'per_page': 100
            }

            try:
                time.sleep(0.3)
                r = requests.get(url, params=params, timeout=30)
                api_calls += 1

                if r.status_code == 429:
                    logger.warning("  Rate limited - stopping")
                    break

                if r.ok:
                    data = r.json()
                    for c in data.get('results', []):
                        name = c.get('contributor_name', '').upper()
                        amt = c.get('contribution_receipt_amount', 0)

                        if amt > 0:
                            is_financial = any(kw in name for kw in FINANCIAL_KEYWORDS)
                            new_pac_contributions.append({
                                'bioguide_id': bioguide_id,
                                'committee_id': c.get('contributor_id', ''),
                                'committee_name': c.get('contributor_name', ''),
                                'amount': amt,
                                'contribution_date': c.get('contribution_receipt_date'),
                                'is_financial': is_financial,
                                'sector': 'financial' if is_financial else ''
                            })
            except Exception as e:
                logger.debug(f"  Error for {fec_id}: {e}")

            if api_calls % 50 == 0:
                logger.info(f"  Progress: {api_calls} API calls, {len(new_pac_contributions)} new PAC contributions")

        logger.info(f"  Found {len(new_pac_contributions)} new PAC contributions in last 7 days")
        logger.info(f"  Total API calls: {api_calls}")

        # If we found new contributions, append to BigQuery
        if new_pac_contributions:
            _append_pac_contributions_to_bq(coordinator, new_pac_contributions)

        coordinator.source_status['fec_incremental'] = {
            'status': 'success',
            'date_range': f"{min_date_str} to {max_date_str}",
            'api_calls': api_calls,
            'new_pac_contributions': len(new_pac_contributions),
            'new_individual_contributions': len(new_individual_contributions),
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Incremental FEC update failed: {e}")
        coordinator.source_status['fec_incremental'] = {'status': 'failed', 'error': str(e)}


def _append_pac_contributions_to_bq(coordinator, contributions: list):
    """Append new PAC contributions to BigQuery (incremental update)."""
    if not contributions:
        return

    logger.info(f"  Appending {len(contributions)} PAC contributions to BigQuery...")

    try:
        from google.cloud import bigquery
        import hashlib

        client = bigquery.Client(project='justdata-ncrc')
        table_id = 'justdata-ncrc.electwatch.official_pac_contributions'

        # Add IDs and timestamps
        rows = []
        for c in contributions:
            row_id = hashlib.md5(
                f"{c['bioguide_id']}|{c['committee_id']}|{c.get('contribution_date','')}|{c['amount']}".encode()
            ).hexdigest()[:16]

            rows.append({
                'id': row_id,
                'bioguide_id': c['bioguide_id'],
                'committee_id': c.get('committee_id', ''),
                'committee_name': c.get('committee_name', ''),
                'amount': c['amount'],
                'contribution_date': c.get('contribution_date'),
                'sector': c.get('sector', ''),
                'sub_sector': '',
                'is_financial': c.get('is_financial', False),
                'updated_at': datetime.now().isoformat()
            })

        # Use streaming insert for small batches
        errors = client.insert_rows_json(table_id, rows)
        if errors:
            logger.error(f"  BigQuery insert errors: {errors[:3]}")
        else:
            logger.info(f"  Successfully appended {len(rows)} PAC contributions")

    except Exception as e:
        logger.error(f"  Failed to append to BigQuery: {e}")


def fetch_fec_data(coordinator):
    """Fetch campaign finance data from FEC for each official.

    Uses the congress-legislators crosswalk for direct bioguide_id -> fec_candidate_id
    mapping, eliminating error-prone name matching. This improves match rate from ~6%
    to ~95%+ for current Congress members.
    """
    logger.info("\n--- Fetching FEC Campaign Finance (via Crosswalk) ---")

    # Load cached progress to see which officials already have FEC data
    cached = coordinator.load_cache('fec_enrichment')
    cached_officials = set()
    if cached:
        cached_officials = set(cached.get('data', {}).get('processed_bioguides', []))
        logger.info(f"  [CACHE] Found {len(cached_officials)} already-enriched officials")

    try:
        import time
        from justdata.apps.electwatch.services.fec_client import FECClient
        from justdata.apps.electwatch.services.crosswalk import get_crosswalk

        client = FECClient()
        crosswalk = get_crosswalk()

        if not client.test_connection():
            raise Exception("FEC API connection failed")

        # Get crosswalk statistics
        crosswalk_stats = crosswalk.get_statistics()
        logger.info(f"  Crosswalk loaded: {crosswalk_stats['total_members']} members, "
                   f"{crosswalk_stats['fec_coverage_pct']}% have FEC IDs")

        # Track matching results
        officials_enriched = 0
        total_contributions = 0
        api_calls = 0
        max_api_calls = 700  # FEC allows 1000/hour
        processed_bioguides = list(cached_officials)
        crosswalk_matches = 0
        crosswalk_misses = []  # Track officials not in crosswalk
        save_interval = 50

        for idx, official in enumerate(coordinator.officials_data):
            bioguide_id = official.get('bioguide_id', '')
            name = official.get('name', '')

            if not bioguide_id:
                logger.debug(f"Skipping {name}: no bioguide_id")
                continue

            # ALWAYS set fec_candidate_id from crosswalk (even for cached officials)
            # This ensures the ID is available for downstream fetches (financial PACs, etc.)
            if not official.get('fec_candidate_id'):
                fec_id = crosswalk.get_fec_id(bioguide_id)
                if fec_id:
                    official['fec_candidate_id'] = fec_id
                    # Also store additional crosswalk IDs
                    member_info = crosswalk.get_member_info(bioguide_id)
                    if member_info:
                        if member_info.get('opensecrets_id'):
                            official['opensecrets_id'] = member_info['opensecrets_id']
                        if member_info.get('govtrack_id'):
                            official['govtrack_id'] = member_info['govtrack_id']

            # Skip API calls if already processed (from cache)
            if bioguide_id in cached_officials:
                if official.get('fec_candidate_id'):
                    crosswalk_matches += 1
                    officials_enriched += 1
                continue

            if api_calls >= max_api_calls:
                logger.info(f"FEC: Reached API call limit ({max_api_calls}), stopping")
                break

            # Rate limit protection
            if api_calls > 0 and api_calls % 100 == 0:
                logger.info(f"  FEC: Pausing 60s after {api_calls} API calls (rate limit protection)...")
                time.sleep(60)

            try:
                # Use crosswalk for direct FEC ID lookup (no name matching!)
                fec_id = crosswalk.get_fec_id(bioguide_id)

                if fec_id:
                    crosswalk_matches += 1
                    official['fec_candidate_id'] = fec_id

                    # Also store additional crosswalk IDs for reference
                    member_info = crosswalk.get_member_info(bioguide_id)
                    if member_info:
                        if member_info.get('opensecrets_id'):
                            official['opensecrets_id'] = member_info['opensecrets_id']
                        if member_info.get('govtrack_id'):
                            official['govtrack_id'] = member_info['govtrack_id']

                    # Add delay before FEC API call
                    time.sleep(0.5)

                    # Fetch candidate totals directly by FEC ID
                    try:
                        totals = client.get_candidate_totals(fec_id, cycle=2024)
                        api_calls += 1

                        if totals:
                            total_amount = totals.get('receipts', 0)
                            individual_contribs = totals.get('individual_contributions', 0)
                            pac_contribs = totals.get('pac_contributions', 0)

                            # Store all contribution data
                            official['contributions'] = pac_contribs
                            official['total_receipts'] = total_amount
                            official['individual_contributions'] = individual_contribs
                            official['pac_contributions'] = pac_contribs
                            official['fec_cycle'] = totals.get('cycle')

                            total_contributions += 1
                            officials_enriched += 1
                            logger.info(f"  FEC: {name} ({bioguide_id}) - ${pac_contribs:,.0f} PAC (${total_amount:,.0f} total)")
                        else:
                            # FEC ID found but no totals data
                            officials_enriched += 1
                            logger.debug(f"  FEC: {name} - ID found but no totals data")

                    except Exception as ce:
                        logger.debug(f"Could not fetch totals for {name} ({fec_id}): {ce}")
                        officials_enriched += 1  # Still count as enriched (has FEC ID)

                else:
                    # Not in crosswalk - track for reporting
                    crosswalk_misses.append({
                        'name': name,
                        'bioguide_id': bioguide_id,
                        'chamber': official.get('chamber', ''),
                        'state': official.get('state', '')
                    })
                    logger.debug(f"  No FEC ID in crosswalk for {name} ({bioguide_id})")

            except Exception as e:
                logger.debug(f"FEC lookup failed for {name}: {e}")

            # Mark as processed
            if bioguide_id and bioguide_id not in processed_bioguides:
                processed_bioguides.append(bioguide_id)

            # Save progress periodically
            if len(processed_bioguides) % save_interval == 0:
                coordinator.save_cache('fec_enrichment', {
                    'processed_bioguides': processed_bioguides,
                    'officials_enriched': officials_enriched,
                    'api_calls': api_calls,
                    'crosswalk_matches': crosswalk_matches
                }, {'partial': True, 'count': len(processed_bioguides)})

        # Final cache save
        coordinator.save_cache('fec_enrichment', {
            'processed_bioguides': processed_bioguides,
            'officials_enriched': officials_enriched,
            'api_calls': api_calls,
            'crosswalk_matches': crosswalk_matches,
            'crosswalk_misses': crosswalk_misses
        }, {'partial': False, 'count': len(processed_bioguides)})

        # Calculate match rate
        total_with_bioguide = sum(1 for o in coordinator.officials_data if o.get('bioguide_id'))
        match_rate = (crosswalk_matches / total_with_bioguide * 100) if total_with_bioguide else 0

        coordinator.source_status['fec'] = {
            'status': 'success',
            'officials_enriched': officials_enriched,
            'total_contributions': total_contributions,
            'api_calls': api_calls,
            'from_cache_count': len(cached_officials),
            'crosswalk_matches': crosswalk_matches,
            'crosswalk_misses': len(crosswalk_misses),
            'match_rate_pct': round(match_rate, 1),
            'timestamp': datetime.now().isoformat()
        }

        logger.info(f"FEC: Enriched {officials_enriched} officials via crosswalk "
                   f"({crosswalk_matches} matches, {len(crosswalk_misses)} misses, "
                   f"{match_rate:.1f}% rate, {api_calls} API calls)")

        if crosswalk_misses:
            logger.info(f"  Officials without FEC ID in crosswalk: {[m['name'] for m in crosswalk_misses[:5]]}...")

    except Exception as e:
        logger.error(f"FEC fetch failed: {e}")
        coordinator.warnings.append(f"FEC: {e}")
        coordinator.source_status['fec'] = {'status': 'failed', 'error': str(e)}
        # Save whatever progress we made before the error
        if 'processed_bioguides' in dir():
            coordinator.save_cache('fec_enrichment', {
                'processed_bioguides': processed_bioguides,
                'officials_enriched': officials_enriched if 'officials_enriched' in dir() else 0,
                'api_calls': api_calls if 'api_calls' in dir() else 0
            }, {'partial': True, 'error': str(e)})


def fetch_financial_pac_data(coordinator):
    """Fetch financial sector PAC contributions by looking at candidate receipts (Schedule A)."""
    logger.info("\n--- Fetching Financial Sector PAC Contributions (Schedule A Receipts) ---")

    import requests
    import time

    api_key = os.getenv('FEC_API_KEY')
    if not api_key:
        logger.warning("FEC_API_KEY not set - skipping financial PAC data")
        coordinator.source_status['financial_pacs'] = {'status': 'skipped', 'reason': 'No API key'}
        return

    # Keywords to identify financial sector PACs
    FINANCIAL_KEYWORDS = [
        'BANK', 'FINANCIAL', 'CAPITAL', 'CREDIT', 'INSURANCE', 'INVEST',
        'SECURITIES', 'MORTGAGE', 'WELLS', 'CHASE', 'CITI', 'GOLDMAN',
        'MORGAN STANLEY', 'AMERICAN EXPRESS', 'VISA', 'MASTERCARD', 'BLACKROCK',
        'FIDELITY', 'SCHWAB', 'PRUDENTIAL', 'METLIFE', 'AIG', 'TRUIST',
        'PNC', 'REGIONS', 'FIFTH THIRD', 'US BANCORP', 'HUNTINGTON',
        'PAYPAL', 'COINBASE', 'ROBINHOOD', 'ALLY', 'SYNCHRONY', 'DISCOVER',
        'LENDING', 'LOAN', 'FINTECH', 'CRYPTO', 'BLOCKCHAIN', 'EXCHANGE',
        'ASSET', 'FUND', 'MUTUAL', 'EQUITY', 'HEDGE', 'PRIVATE EQUITY',
        'VENTURE', 'BROKER', 'DEALER', 'TRADING', 'REAL ESTATE INVEST',
        'REIT', 'SAVINGS', 'THRIFT', 'CONSUMER BANKER', 'COMMUNITY BANKER',
        'INDEPENDENT BANKER', 'AMERICAN BANKER', 'CREDIT UNION'
    ]

    # Use election cycle start date (covers 2023-2024 and 2025-2026 cycles)
    rolling_end_date = datetime.now()
    min_date_str = ELECTION_CYCLE_START
    max_date_str = rolling_end_date.strftime('%Y-%m-%d')
    logger.info(f"  Using election cycle window: {min_date_str} to {max_date_str}")

    def get_financial_pac_total(committee_id: str) -> dict:
        """Get PAC contributions to a candidate's committee (rolling 24 months)."""
        url = 'https://api.open.fec.gov/v1/schedules/schedule_a/'
        financial_total = 0
        all_pac_total = 0
        contributors = []
        page = 1
        max_pages = 20  # Limit pages to avoid excessive API calls

        while page <= max_pages:
            params = {
                'api_key': api_key,
                'committee_id': committee_id,
                'min_date': min_date_str,
                'max_date': max_date_str,
                'contributor_type': 'committee',
                'per_page': 100,
                'page': page
            }

            try:
                time.sleep(0.5)  # Rate limiting
                r = requests.get(url, params=params, timeout=60)

                if r.status_code == 429:
                    logger.warning("  Rate limited - waiting 60 seconds")
                    time.sleep(60)
                    continue

                if not r.ok:
                    break

                data = r.json()
                results = data.get('results', [])
                if not results:
                    break

                for c in results:
                    name = c.get('contributor_name', '').upper()
                    amt = c.get('contribution_receipt_amount', 0)
                    # Only count PAC contributions (not employee contributions)
                    is_pac = 'PAC' in name or 'POLITICAL ACTION' in name or 'POLITICAL FUND' in name

                    if amt > 0 and is_pac:
                        # Track ALL PAC contributions (denominator)
                        all_pac_total += amt

                        # Track financial sector PACs (numerator)
                        if any(kw in name for kw in FINANCIAL_KEYWORDS):
                            financial_total += amt
                            contributors.append({
                                'name': c.get('contributor_name', ''),
                                'amount': amt
                            })

                pages = data.get('pagination', {}).get('pages', 1)
                if page >= pages:
                    break
                page += 1

            except Exception as e:
                logger.error(f"  Error fetching receipts: {e}")
                break

        # Calculate percentage
        financial_pct = 0
        if all_pac_total > 0:
            financial_pct = round((financial_total / all_pac_total) * 100, 1)

        return {
            'financial_total': financial_total,
            'all_pac_total': all_pac_total,
            'financial_pct': financial_pct,
            'financial_contributors': contributors
        }

    def get_committee_from_candidate_id(fec_candidate_id: str) -> Optional[str]:
        """Get principal campaign committee ID directly from FEC candidate ID."""
        if not fec_candidate_id:
            return None

        # Use the /committees/ sub-endpoint which returns actual committee data
        url = f'https://api.open.fec.gov/v1/candidate/{fec_candidate_id}/committees/'
        params = {
            'api_key': api_key,
            'designation': 'P'  # Principal campaign committee
        }

        try:
            time.sleep(0.3)
            r = requests.get(url, params=params, timeout=30)
            if r.ok:
                data = r.json()
                results = data.get('results', [])
                if results:
                    committee_id = results[0].get('committee_id')
                    logger.debug(f"  Found committee {committee_id} for candidate {fec_candidate_id}")
                    return committee_id
                else:
                    # Try without designation filter (some candidates don't have P designation)
                    params.pop('designation', None)
                    time.sleep(0.3)
                    r2 = requests.get(url, params=params, timeout=30)
                    if r2.ok:
                        data2 = r2.json()
                        results2 = data2.get('results', [])
                        if results2:
                            committee_id = results2[0].get('committee_id')
                            logger.debug(f"  Found committee {committee_id} for candidate {fec_candidate_id} (no P designation)")
                            return committee_id
        except Exception as e:
            logger.debug(f"  Error getting committee for {fec_candidate_id}: {e}")

        return None

    # Load cached progress
    cached = coordinator.load_cache('financial_pacs')
    cached_officials = set()
    if cached:
        cached_officials = set(cached.get('data', {}).get('processed_names', []))
        logger.info(f"  [CACHE] Found {len(cached_officials)} already-processed officials")

    try:
        matched_count = 0
        total_financial = 0
        processed_names = list(cached_officials)
        save_interval = 25  # Save every 25 officials (more frequent due to slower API)

        for i, official in enumerate(coordinator.officials_data):
            name = official.get('name', '')

            # Skip if already processed
            if name in cached_officials:
                if official.get('financial_sector_pac', 0) > 0:
                    matched_count += 1
                    total_financial += official.get('financial_sector_pac', 0)
                continue

            # Use crosswalk FEC candidate ID for reliable committee lookup
            # The crosswalk provides direct bioguide_id -> fec_candidate_id mapping
            fec_candidate_id = official.get('fec_candidate_id')

            # Get principal campaign committee from FEC candidate ID
            committee_id = get_committee_from_candidate_id(fec_candidate_id)

            if not committee_id and fec_candidate_id:
                logger.debug(f"  {name}: Has FEC ID {fec_candidate_id} but no committee found")

            if committee_id:
                pac_result = get_financial_pac_total(committee_id)
                fin_total = pac_result.get('financial_total', 0)
                all_pac_total = pac_result.get('all_pac_total', 0)
                financial_pct = pac_result.get('financial_pct', 0)
                contributors = pac_result.get('financial_contributors', [])

                official['financial_sector_pac'] = fin_total
                official['fec_committee_id'] = committee_id
                # Store calculated percentage from Schedule A data
                official['financial_pac_pct'] = financial_pct

                # If we don't have contributions from the initial FEC fetch,
                # use the total from this Schedule A fetch as denominator
                if not official.get('contributions') and all_pac_total > 0:
                    official['contributions'] = all_pac_total
                    official['pac_contributions'] = all_pac_total

                if fin_total > 0:
                    matched_count += 1
                    total_financial += fin_total
                    # Store top contributors
                    top_contributors = sorted(contributors, key=lambda x: x['amount'], reverse=True)[:5]
                    official['top_financial_pacs'] = top_contributors
                    logger.info(f"  {name}: ${fin_total:,.0f} from {len(contributors)} financial PACs ({financial_pct}% of ${all_pac_total:,.0f} total PACs)")
                else:
                    official['financial_sector_pac'] = 0
                    if all_pac_total > 0:
                        logger.info(f"  {name}: $0 financial PACs (of ${all_pac_total:,.0f} total PACs)")
                    else:
                        logger.info(f"  {name}: $0 from PACs")
            else:
                # Couldn't find committee - set to None (unknown)
                logger.debug(f"  {name}: Could not find FEC committee")

            # Mark as processed
            if name and name not in processed_names:
                processed_names.append(name)

            # Save progress periodically
            if len(processed_names) % save_interval == 0:
                coordinator.save_cache('financial_pacs', {
                    'processed_names': processed_names,
                    'matched_count': matched_count,
                    'total_financial': total_financial
                }, {'partial': True, 'count': len(processed_names)})

            # Progress update
            if (i + 1) % 10 == 0:
                logger.info(f"  Progress: {i + 1}/{len(coordinator.officials_data)} officials processed")

        # Final cache save
        coordinator.save_cache('financial_pacs', {
            'processed_names': processed_names,
            'matched_count': matched_count,
            'total_financial': total_financial
        }, {'partial': False, 'count': len(processed_names)})

        coordinator.source_status['financial_pacs'] = {
            'status': 'success',
            'matched_officials': matched_count,
            'total_financial_contributions': total_financial,
            'from_cache_count': len(cached_officials),
            'timestamp': datetime.now().isoformat()
        }
        logger.info(f"Financial PACs: {matched_count}/{len(coordinator.officials_data)} officials have financial sector contributions (${total_financial:,.0f} total)")

    except Exception as e:
        logger.error(f"Financial PAC fetch failed: {e}")
        coordinator.warnings.append(f"Financial PACs: {e}")
        coordinator.source_status['financial_pacs'] = {'status': 'failed', 'error': str(e)}
        # Save progress before error
        if 'processed_names' in dir():
            coordinator.save_cache('financial_pacs', {
                'processed_names': processed_names,
                'matched_count': matched_count if 'matched_count' in dir() else 0,
                'total_financial': total_financial if 'total_financial' in dir() else 0
            }, {'partial': True, 'error': str(e)})


def fetch_individual_financial_contributions(coordinator):
    """Fetch individual contributions from financial sector executives."""
    # Load cached progress
    cached = coordinator.load_cache('individual_contributions')
    cached_names = set()
    if cached:
        cached_names = set(cached.get('data', {}).get('processed_names', []))
        logger.info(f"  [CACHE] Found {len(cached_names)} already-processed officials")

    def save_progress(processed_names, matched_count, total_amount):
        coordinator.save_cache('individual_contributions', {
            'processed_names': processed_names,
            'matched_count': matched_count,
            'total_amount': total_amount
        }, {'partial': True, 'count': len(processed_names)})

    try:
        from justdata.apps.electwatch.services.individual_contributions import enrich_officials_with_individual_contributions
        status = enrich_officials_with_individual_contributions(
            coordinator.officials_data,
            cached_names=cached_names,
            save_callback=save_progress
        )
        status['from_cache_count'] = len(cached_names)
        coordinator.source_status['individual_financial'] = status
    except Exception as e:
        logger.error(f"Individual financial contributions fetch failed: {e}")
        coordinator.source_status['individual_financial'] = {'status': 'failed', 'error': str(e)}
