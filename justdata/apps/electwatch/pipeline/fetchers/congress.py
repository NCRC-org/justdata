"""Congress.gov fetcher for the ElectWatch weekly pipeline."""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def fetch_all_congress_members(coordinator):
    """Fetch complete list of all Congress members from Congress.gov API."""
    logger.info("--- Fetching ALL Congress Members from Congress.gov ---")

    # Try to load from cache first
    cached = coordinator.load_cache('congress_members')
    if cached:
        members = cached.get('data', [])
        if members:
            coordinator.officials_data = members
            coordinator._officials_by_name = {}
            for m in coordinator.officials_data:
                name_key = m['name'].lower().strip()
                coordinator._officials_by_name[name_key] = m

                # Handle "Last, First" format (Congress.gov) vs "First Last" (FMP)
                name = m['name']
                if ',' in name:
                    # "Pelosi, Nancy" -> last_name = "pelosi"
                    last_name = name.split(',')[0].strip().lower()
                else:
                    # "Nancy Pelosi" -> last_name = "pelosi"
                    parts = name.split()
                    last_name = parts[-1].lower() if parts else name_key

                if last_name and last_name not in coordinator._officials_by_name:
                    coordinator._officials_by_name[last_name] = m

            coordinator.source_status['congress_members'] = cached.get('metadata', {})
            coordinator.source_status['congress_members']['from_cache'] = True
            logger.info(f"  [CACHE] Loaded {len(members)} Congress members from cache")
            return

    try:
        from justdata.apps.electwatch.services.congress_api_client import CongressAPIClient
        client = CongressAPIClient()

        members = client.get_all_members()

        if members:
            coordinator.officials_data = members
            coordinator._officials_by_name = {}
            for m in coordinator.officials_data:
                name_key = m['name'].lower().strip()
                coordinator._officials_by_name[name_key] = m

                # Handle "Last, First" format (Congress.gov) vs "First Last" (FMP)
                name = m['name']
                if ',' in name:
                    # "Pelosi, Nancy" -> last_name = "pelosi"
                    last_name = name.split(',')[0].strip().lower()
                else:
                    # "Nancy Pelosi" -> last_name = "pelosi"
                    parts = name.split()
                    last_name = parts[-1].lower() if parts else name_key

                if last_name and last_name not in coordinator._officials_by_name:
                    coordinator._officials_by_name[last_name] = m

            house = len([m for m in members if m['chamber'] == 'house'])
            senate = len([m for m in members if m['chamber'] == 'senate'])

            coordinator.source_status['congress_members'] = {
                'status': 'success',
                'house_members': house,
                'senate_members': senate,
                'total': len(members),
                'timestamp': datetime.now().isoformat()
            }
            logger.info(f"Fetched {len(members)} Congress members ({house} House, {senate} Senate)")

            # Save to cache
            coordinator.save_cache('congress_members', members, coordinator.source_status['congress_members'])
        else:
            logger.warning("No Congress members fetched - check API key")
            coordinator.warnings.append("Congress.gov: No members fetched")
            coordinator.source_status['congress_members'] = {'status': 'failed', 'error': 'No members returned'}

    except Exception as e:
        logger.error(f"Congress members fetch failed: {e}")
        coordinator.warnings.append(f"Congress.gov members: {e}")
        coordinator.source_status['congress_members'] = {'status': 'failed', 'error': str(e)}


def fetch_congress_data(coordinator):
    """Fetch bills and member data from Congress.gov."""
    logger.info("\n--- Fetching Congress.gov Data ---")
    try:
        from justdata.apps.electwatch.services.congress_api_client import CongressAPIClient
        client = CongressAPIClient()

        # Fetch recent financial-related bills
        bills = client.search_bills(query="financial services", limit=20)
        crypto_bills = client.search_bills(query="cryptocurrency", limit=20)

        all_bills = (bills or []) + (crypto_bills or [])

        coordinator.source_status['congress'] = {
            'status': 'success',
            'bills_found': len(all_bills),
            'timestamp': datetime.now().isoformat()
        }
        logger.info(f"Fetched {len(all_bills)} bills from Congress.gov")

    except Exception as e:
        logger.error(f"Congress.gov fetch failed: {e}")
        coordinator.warnings.append(f"Congress.gov: {e}")
        coordinator.source_status['congress'] = {'status': 'failed', 'error': str(e)}
