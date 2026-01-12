#!/usr/bin/env python3
"""
ElectWatch Data Store

Local storage layer for pre-computed weekly data.
All data is fetched during weekly updates and stored in JSON files.
The app serves this static data throughout the week.

Directory structure:
    data/
        current/           # Symlink/copy of latest valid data
            officials.json
            firms.json
            industries.json
            committees.json
            news.json
            summaries.json
            metadata.json
        weekly/
            2026-01-05/    # Weekly snapshots
            2026-01-12/
            ...
"""

import os
import json
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Data directory
DATA_DIR = Path(__file__).parent.parent / 'data'
CURRENT_DIR = DATA_DIR / 'current'
WEEKLY_DIR = DATA_DIR / 'weekly'


def ensure_dirs():
    """Ensure data directories exist."""
    DATA_DIR.mkdir(exist_ok=True)
    CURRENT_DIR.mkdir(exist_ok=True)
    WEEKLY_DIR.mkdir(exist_ok=True)


def get_current_data_path() -> Path:
    """Get path to current data directory."""
    ensure_dirs()
    return CURRENT_DIR


def get_weekly_data_path(date: Optional[datetime] = None) -> Path:
    """Get path to a weekly snapshot directory."""
    ensure_dirs()
    if date is None:
        date = datetime.now()
    # Use Sunday's date for the week
    days_since_sunday = date.weekday() + 1 if date.weekday() != 6 else 0
    sunday = date.replace(hour=0, minute=0, second=0, microsecond=0)
    week_str = sunday.strftime('%Y-%m-%d')
    week_dir = WEEKLY_DIR / week_str
    week_dir.mkdir(exist_ok=True)
    return week_dir


# =============================================================================
# DATA READING (for app endpoints)
# =============================================================================

def load_json(filename: str) -> Optional[Dict]:
    """Load a JSON file from current data directory."""
    filepath = CURRENT_DIR / filename
    if not filepath.exists():
        logger.warning(f"Data file not found: {filepath}")
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading {filepath}: {e}")
        return None


def get_metadata() -> Dict[str, Any]:
    """Get metadata about the current data."""
    data = load_json('metadata.json')
    if not data:
        return {
            'last_updated': None,
            'data_sources': {},
            'status': 'no_data'
        }
    return data


def get_officials() -> List[Dict]:
    """Get all officials data."""
    data = load_json('officials.json')
    return data.get('officials', []) if data else []


def get_official(official_id: str) -> Optional[Dict]:
    """Get a specific official by ID."""
    data = load_json('officials.json')
    if not data:
        return None
    officials_by_id = data.get('by_id', {})
    return officials_by_id.get(official_id)


def get_firms() -> List[Dict]:
    """Get all firms data."""
    data = load_json('firms.json')
    return data.get('firms', []) if data else []


def get_firm(firm_name: str) -> Optional[Dict]:
    """Get a specific firm by name."""
    data = load_json('firms.json')
    if not data:
        return None
    firms_by_name = data.get('by_name', {})
    # Try exact match first, then case-insensitive
    normalized = firm_name.lower().strip()
    return firms_by_name.get(normalized) or firms_by_name.get(firm_name)


def get_industries() -> List[Dict]:
    """Get all industries data."""
    data = load_json('industries.json')
    return data.get('industries', []) if data else []


def get_industry(sector: str) -> Optional[Dict]:
    """Get a specific industry sector."""
    data = load_json('industries.json')
    if not data:
        return None
    by_sector = data.get('by_sector', {})
    return by_sector.get(sector.lower())


def get_committees() -> List[Dict]:
    """Get all committees data."""
    data = load_json('committees.json')
    return data.get('committees', []) if data else []


def get_committee(committee_id: str) -> Optional[Dict]:
    """Get a specific committee by ID."""
    data = load_json('committees.json')
    if not data:
        return None
    by_id = data.get('by_id', {})
    normalized = committee_id.lower().replace(' ', '-').replace('_', '-')
    return by_id.get(normalized) or by_id.get(committee_id)


def get_news() -> List[Dict]:
    """Get all news articles."""
    data = load_json('news.json')
    return data.get('articles', []) if data else []


def get_summaries() -> Dict[str, str]:
    """Get AI-generated summaries."""
    data = load_json('summaries.json')
    return data if data else {}


def get_freshness() -> Dict[str, Any]:
    """Get data freshness information."""
    metadata = get_metadata()
    return {
        'last_updated': metadata.get('last_updated'),
        'last_updated_display': metadata.get('last_updated_display'),
        'data_window': metadata.get('data_window'),
        'sources': metadata.get('data_sources', {}),
        'next_update': metadata.get('next_update')
    }


# =============================================================================
# DATA WRITING (for weekly updates)
# =============================================================================

def save_json(filename: str, data: Dict, weekly_dir: Optional[Path] = None):
    """Save data to JSON file."""
    ensure_dirs()

    # Save to current
    current_path = CURRENT_DIR / filename
    with open(current_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    # Also save to weekly snapshot if provided
    if weekly_dir:
        weekly_path = weekly_dir / filename
        with open(weekly_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    logger.info(f"Saved {filename}")


def save_officials(officials: List[Dict], weekly_dir: Optional[Path] = None):
    """Save officials data with index."""
    by_id = {}
    for official in officials:
        oid = official.get('id', official.get('name', '').lower().replace(' ', '_'))
        by_id[oid] = official

    data = {
        'officials': officials,
        'by_id': by_id,
        'count': len(officials),
        'generated_at': datetime.now().isoformat()
    }
    save_json('officials.json', data, weekly_dir)


def save_firms(firms: List[Dict], weekly_dir: Optional[Path] = None):
    """Save firms data with index."""
    by_name = {}
    for firm in firms:
        name = firm.get('name', '').lower().strip()
        by_name[name] = firm
        # Also index by ticker if available
        ticker = firm.get('ticker')
        if ticker:
            by_name[ticker.lower()] = firm

    data = {
        'firms': firms,
        'by_name': by_name,
        'count': len(firms),
        'generated_at': datetime.now().isoformat()
    }
    save_json('firms.json', data, weekly_dir)


def save_industries(industries: List[Dict], weekly_dir: Optional[Path] = None):
    """Save industries data with index."""
    by_sector = {}
    for industry in industries:
        sector = industry.get('sector', '').lower()
        by_sector[sector] = industry

    data = {
        'industries': industries,
        'by_sector': by_sector,
        'count': len(industries),
        'generated_at': datetime.now().isoformat()
    }
    save_json('industries.json', data, weekly_dir)


def save_committees(committees: List[Dict], weekly_dir: Optional[Path] = None):
    """Save committees data with index."""
    by_id = {}
    for committee in committees:
        cid = committee.get('id', '').lower()
        by_id[cid] = committee

    data = {
        'committees': committees,
        'by_id': by_id,
        'count': len(committees),
        'generated_at': datetime.now().isoformat()
    }
    save_json('committees.json', data, weekly_dir)


def save_news(articles: List[Dict], weekly_dir: Optional[Path] = None):
    """Save news articles."""
    data = {
        'articles': articles,
        'count': len(articles),
        'generated_at': datetime.now().isoformat()
    }
    save_json('news.json', data, weekly_dir)


def save_summaries(summaries: Dict[str, str], weekly_dir: Optional[Path] = None):
    """Save AI-generated summaries."""
    summaries['generated_at'] = datetime.now().isoformat()
    save_json('summaries.json', summaries, weekly_dir)


def save_metadata(metadata: Dict[str, Any], weekly_dir: Optional[Path] = None):
    """Save metadata about the update."""
    save_json('metadata.json', metadata, weekly_dir)


# =============================================================================
# DATA STATUS
# =============================================================================

def has_valid_data() -> bool:
    """Check if we have valid current data."""
    metadata = get_metadata()
    return metadata.get('status') == 'valid'


def get_data_age_days() -> Optional[int]:
    """Get how many days old the current data is."""
    metadata = get_metadata()
    last_updated = metadata.get('last_updated')
    if not last_updated:
        return None
    try:
        updated_dt = datetime.fromisoformat(last_updated)
        return (datetime.now() - updated_dt).days
    except:
        return None


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    print("Data Store Test")
    print("=" * 40)
    print(f"Data directory: {DATA_DIR}")
    print(f"Current directory: {CURRENT_DIR}")
    print(f"Has valid data: {has_valid_data()}")
    print(f"Data age: {get_data_age_days()} days")

    metadata = get_metadata()
    print(f"\nMetadata: {json.dumps(metadata, indent=2)}")

    officials = get_officials()
    print(f"\nOfficials count: {len(officials)}")
