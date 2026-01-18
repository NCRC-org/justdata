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

# Formal/legal names -> public names mapping
# These are officials whose disclosure names differ from their commonly-used names
FORMAL_TO_PUBLIC_NAME = {
    'Rafael Cruz': 'Ted Cruz',
    'Angus S. King': 'Angus King',
    'Thomas Tuberville': 'Tommy Tuberville',
    'Thomas H. Kean': 'Tom Kean',
    'James French Hill': 'French Hill',
    'Neal P. Dunn': 'Neal Dunn',
    'Carol Devine Miller': 'Carol Miller',
    'Richard McCormick': 'Rich McCormick',
    'Marjorie Taylor Greene': 'Marjorie Greene',
    'Richard W. Allen': 'Rick Allen',
    'William R. Keating': 'Bill Keating',
}

# Missing bioguide IDs - for new members not yet in our data
# These are used to generate House Clerk photo URLs
MISSING_BIOGUIDE_IDS = {
    'Julie Johnson': 'J000310',
    'George Whitesides': 'W000828',
    'Rob Bresnahan': 'B001326',
    'Val Hoyle': 'H001094',
    'Byron Donalds': 'D000032',
    'April Delaney': 'D000637',
    'Rich McCormick': 'M001135',
}

# Bioguide ID corrections - for members with WRONG bioguide IDs in stored data
# These override incorrect stored values
BIOGUIDE_OVERRIDES = {
    'Ritchie Torres': 'T000486',  # Stored as T000481 (Norma Torres) - WRONG
}

# Website URL overrides for officials with non-standard URLs
# Standard format is lastname.house.gov or lastname.senate.gov
# These entries override when the standard format doesn't work
WEBSITE_URL_OVERRIDES = {
    'Julie Johnson': 'https://juliejohnson.house.gov',
    'Bill Johnson': 'https://billjohnson.house.gov',  # Multiple Johnsons
    'Dusty Johnson': 'https://dustyjohnson.house.gov',
    'Mike Johnson': 'https://mikejohnson.house.gov',  # Speaker
    'April Delaney': 'https://aprildelaney.house.gov',  # Not former Rep John Delaney
    'Ritchie Torres': 'https://ritchietorres.house.gov',  # Not Norma Torres
}

# Wikipedia/Wikimedia photo URLs for Senators (House members use clerk.house.gov)
# These are used as fallback when photo_url is not in stored data
WIKIPEDIA_PHOTOS = {
    'Dave McCormick': 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c6/McCormick_Portrait_%28HR%29.jpg/330px-McCormick_Portrait_%28HR%29.jpg',
    'Angus King': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/Angus_King%2C_official_portrait%2C_113th_Congress.jpg/330px-Angus_King%2C_official_portrait%2C_113th_Congress.jpg',
    'Ted Cruz': 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/Ted_Cruz_official_116th_portrait_%283x4_cropped_b%29.jpg/330px-Ted_Cruz_official_116th_portrait_%283x4_cropped_b%29.jpg',
    'Markwayne Mullin': 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c7/Markwayne_Mullin_official_Senate_photo.jpg/330px-Markwayne_Mullin_official_Senate_photo.jpg',
    'Tommy Tuberville': 'https://upload.wikimedia.org/wikipedia/commons/thumb/d/df/Tommy_tuberville.jpg/330px-Tommy_tuberville.jpg',
    'Shelley Moore Capito': 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/75/Shelley_Moore_Capito_official_Senate_photo.jpg/330px-Shelley_Moore_Capito_official_Senate_photo.jpg',
    'John Boozman': 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/30/Senator_John_Boozman_Official_Portrait_%28115th_Congress%29.jpg/330px-Senator_John_Boozman_Official_Portrait_%28115th_Congress%29.jpg',
    'Tina Smith': 'https://upload.wikimedia.org/wikipedia/commons/thumb/f/ff/Tina_Smith%2C_official_portrait%2C_116th_congress.jpg/330px-Tina_Smith%2C_official_portrait%2C_116th_congress.jpg',
    'John Kennedy': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/af/John_Kennedy%2C_official_portrait%2C_115th_Congress_%28cropped%29.jpg/330px-John_Kennedy%2C_official_portrait%2C_115th_Congress_%28cropped%29.jpg',
    'Sheldon Whitehouse': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/Sheldon_Whitehouse%2C_official_portrait%2C_116th_congress.jpg/330px-Sheldon_Whitehouse%2C_official_portrait%2C_116th_congress.jpg',
    'John Fetterman': 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/John_Fetterman_official_portrait.jpg/330px-John_Fetterman_official_portrait.jpg',
    # House members with bioguide mismatches or missing photos
    'Ritchie Torres': 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/8b/Ritchie_Torres%2C_117th_Congress_portrait.jpeg/330px-Ritchie_Torres%2C_117th_Congress_portrait.jpeg',
    'Rich McCormick': 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/0b/Rich_McCormick_118th_Congress_portrait.jpg/330px-Rich_McCormick_118th_Congress_portrait.jpg',
    'Val Hoyle': 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/99/Rep._Val_Hoyle_-_118th_Congress.jpg/330px-Rep._Val_Hoyle_-_118th_Congress.jpg',
    'George Whitesides': 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/6e/George_Whitesides_119th_Congress_portrait.jpg/330px-George_Whitesides_119th_Congress_portrait.jpg',
    'April Delaney': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/April_Delaney_119th_Congress_portrait.jpg/330px-April_Delaney_119th_Congress_portrait.jpg',
}

# First year in Congress for members (to calculate years served correctly)
# These override any incorrectly calculated values from the API
CONGRESS_START_YEAR = {
    # Senators
    'Ted Cruz': 2013,
    'John Boozman': 2001,  # House 2001, Senate 2011
    'Shelley Moore Capito': 2001,  # House 2001, Senate 2015
    'Tommy Tuberville': 2021,
    'Markwayne Mullin': 2013,  # House 2013, Senate 2023
    'John Kennedy': 2017,
    'Angus King': 2013,
    'Tina Smith': 2018,
    'Sheldon Whitehouse': 2007,
    'John Fetterman': 2023,
    'Dave McCormick': 2025,
    'Rand Paul': 2011,
    'Mike Crapo': 1993,  # House 1993, Senate 1999
    'Tim Scott': 2011,  # House 2011, Senate 2013
    'Thom Tillis': 2015,
    'Bill Hagerty': 2021,
    'Cynthia Lummis': 2009,  # House 2009, Senate 2021
    'Kevin Cramer': 2013,  # House 2013, Senate 2019
    'Katie Britt': 2023,
    'Bernie Moreno': 2025,
    'John Curtis': 2017,  # House 2017, Senate 2025
    # House members (key finance committee members)
    'French Hill': 2015,
    'Patrick McHenry': 2005,
    'Maxine Waters': 1991,
    'Andy Barr': 2013,
    'Blaine Luetkemeyer': 2009,
    'Bill Huizenga': 2011,
    'Ann Wagner': 2013,
    'Frank Lucas': 1994,
    'Roger Williams': 2013,
    'Barry Loudermilk': 2015,
    'Alexander Mooney': 2015,
    'Warren Davidson': 2016,
    'Bryan Steil': 2019,
    'Lance Gooden': 2019,
    'William Timmons': 2019,
    'Anthony Gonzalez': 2019,
    'Byron Donalds': 2021,
    'Mike Flood': 2022,
    'Erin Houchin': 2023,
    'Monica De La Cruz': 2023,
    'Andy Ogles': 2023,
    'Mike Lawler': 2023,
    'Zach Nunn': 2023,
    'Young Kim': 2021,
    'Nancy Mace': 2021,
    'Scott Fitzgerald': 2021,
    'Pete Sessions': 1997,  # With gap, but total service
    'Nydia Velazquez': 1993,
    'Brad Sherman': 1997,
    'Gregory Meeks': 1998,
    'David Scott': 2003,
    'Al Green': 2005,
    'Emanuel Cleaver': 2005,
    'Gwen Moore': 2005,
    'Stephen Lynch': 2001,
    'Jim Himes': 2009,
    'Bill Foster': 2008,
    'Joyce Beatty': 2013,
    'Juan Vargas': 2013,
    'Josh Gottheimer': 2017,
    'Vicente Gonzalez': 2017,
    'Al Lawson': 2017,
    'Cindy Axne': 2019,
    'Sean Casten': 2019,
    'Ayanna Pressley': 2019,
    'Ritchie Torres': 2021,
    'Nikema Williams': 2021,
    'Jake Auchincloss': 2021,
    'Brittany Pettersen': 2023,
    'Wiley Nickel': 2023,
}


def get_years_in_congress(name: str, stored_years: int = None) -> int:
    """Get correct years in Congress, using override if available."""
    if name in CONGRESS_START_YEAR:
        return datetime.now().year - CONGRESS_START_YEAR[name]
    return stored_years if stored_years else 1


def normalize_to_public_name(formal_name: str) -> str:
    """Convert a formal/legal name to the publicly-used name."""
    return FORMAL_TO_PUBLIC_NAME.get(formal_name, formal_name)


def get_photo_url(name: str, bioguide_id: str = None, chamber: str = 'house') -> Optional[str]:
    """Get photo URL for an official, checking Wikipedia first then House Clerk."""
    # Check Wikipedia photos (mainly for Senators)
    if name in WIKIPEDIA_PHOTOS:
        return WIKIPEDIA_PHOTOS[name]

    # Check for missing bioguide IDs
    if not bioguide_id and name in MISSING_BIOGUIDE_IDS:
        bioguide_id = MISSING_BIOGUIDE_IDS[name]

    # For House members, use clerk.house.gov with bioguide_id
    if bioguide_id and chamber == 'house':
        return f"https://clerk.house.gov/content/assets/img/members/{bioguide_id}.jpg"

    return None


def get_website_url(name: str, chamber: str = 'house') -> Optional[str]:
    """Get official website URL for a member of Congress."""
    # Check for overrides first (for non-standard URLs)
    if name in WEBSITE_URL_OVERRIDES:
        return WEBSITE_URL_OVERRIDES[name]

    # Generate standard URL from last name
    parts = name.split()
    if parts:
        last_name = parts[-1].lower()
        if chamber == 'house':
            return f"https://{last_name}.house.gov"
        else:
            return f"https://www.{last_name}.senate.gov"

    return None


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
    """Get all officials data with normalized public names and photos."""
    data = load_json('officials.json')
    officials = data.get('officials', []) if data else []

    # Normalize names, parties, and ensure photos
    for official in officials:
        # Normalize name to public version (e.g., 'Rafael Cruz' -> 'Ted Cruz')
        if 'name' in official:
            official['name'] = normalize_to_public_name(official['name'])

        # Also update the ID to match the public name
        if official.get('name'):
            official['id'] = official['name'].lower().replace(' ', '_')

        # Normalize party to single letter (REP -> R, DEM -> D)
        party = official.get('party', '')
        if party == 'REP':
            official['party'] = 'R'
        elif party == 'DEM':
            official['party'] = 'D'
        elif party == 'IND':
            official['party'] = 'I'

        # FIRST: Override incorrect bioguide IDs (must happen before photo lookup)
        name = official.get('name', '')
        if name in BIOGUIDE_OVERRIDES:
            official['bioguide_id'] = BIOGUIDE_OVERRIDES[name]
            # Clear existing photo URL since it was based on wrong bioguide
            official['photo_url'] = None

        # SECOND: Override website URLs for officials with non-standard or wrong URLs
        if name in WEBSITE_URL_OVERRIDES:
            official['website_url'] = WEBSITE_URL_OVERRIDES[name]

        # THIRD: Ensure photo URL - use Wikipedia fallback or generate from bioguide
        if not official.get('photo_url'):
            photo_url = get_photo_url(
                name,
                official.get('bioguide_id'),
                official.get('chamber', 'house')
            )
            if photo_url:
                official['photo_url'] = photo_url
                official['photo_source'] = 'wikipedia' if 'wikimedia' in photo_url else 'house_clerk'

        # Populate contributions_list from top_financial_pacs if available
        if not official.get('contributions_list') and official.get('top_financial_pacs'):
            official['contributions_list'] = [
                {
                    'source': pac.get('name', 'Unknown PAC'),
                    'pac_name': pac.get('name', 'Unknown PAC'),
                    'amount': pac.get('amount', 0),
                    'date': None,  # Date not available from this source
                    'industry': 'financial'  # All are financial sector PACs
                }
                for pac in official.get('top_financial_pacs', [])
            ]
            official['contributions_count'] = len(official['contributions_list'])

        # Add website URL (with overrides for non-standard URLs like juliejohnson.house.gov)
        if not official.get('website_url'):
            official['website_url'] = get_website_url(
                official.get('name', ''),
                official.get('chamber', 'house')
            )

        # Add bioguide_id from mapping if missing
        if not official.get('bioguide_id') and official.get('name') in MISSING_BIOGUIDE_IDS:
            official['bioguide_id'] = MISSING_BIOGUIDE_IDS[official.get('name')]

        # Correct years in Congress using lookup table
        official['years_in_congress'] = get_years_in_congress(
            official.get('name', ''),
            official.get('years_in_congress')
        )

    return officials


def get_official(official_id: str) -> Optional[Dict]:
    """Get a specific official by ID (handles both original and normalized IDs)."""
    # First try get_officials which has all the normalization applied
    officials = get_officials()
    for official in officials:
        if official.get('id') == official_id:
            return official

    # Fall back to by_id index (try original and normalized keys)
    data = load_json('officials.json')
    if not data:
        return None

    officials_by_id = data.get('by_id', {})

    # Try direct match
    if official_id in officials_by_id:
        return officials_by_id.get(official_id)

    # Try matching by normalized ID
    for stored_id, official in officials_by_id.items():
        normalized_id = normalize_to_public_name(official.get('name', '')).lower().replace(' ', '_')
        if normalized_id == official_id:
            return official

    return None


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




def get_firms_with_stats() -> List[Dict]:
    """
    Get all firms data with computed statistics from officials' trades.
    
    Returns firms with the following fields expected by the frontend:
    - name: Company name
    - ticker: Stock ticker symbol
    - industry: Industry/sector code (lowercase)
    - total: Total trade value (using midpoint of ranges)
    - officials: Count of officials who traded this firm
    - stock_trades: Total number of stock trades for this firm
    """
    # Get raw firms data
    firms_data = load_json('firms.json')
    raw_firms = firms_data.get('firms', []) if firms_data else []
    
    # Get officials data to aggregate trades by firm
    officials = get_officials()
    
    # Build aggregated stats by ticker
    firm_stats = {}
    for official in officials:
        trades = official.get('trades', [])
        for trade in trades:
            ticker = trade.get('ticker', '')
            if not ticker:
                continue
            
            if ticker not in firm_stats:
                firm_stats[ticker] = {
                    'trade_count': 0,
                    'officials': set(),
                    'total_value': 0,
                    'company_name': trade.get('company', ''),
                }
            
            firm_stats[ticker]['trade_count'] += 1
            firm_stats[ticker]['officials'].add(official.get('name', ''))
            
            # Calculate trade value using midpoint of range
            amount = trade.get('amount', {})
            if isinstance(amount, dict):
                min_val = amount.get('min', 0)
                max_val = amount.get('max', 0)
                midpoint = (min_val + max_val) / 2
                firm_stats[ticker]['total_value'] += midpoint
    
    # Industry mapping (lowercase for consistent matching)
    industry_map = {
        'Banking': 'banking',
        'Investment': 'investment',
        'Insurance': 'insurance',
        'Crypto': 'crypto',
        'Fintech': 'fintech',
        'Mortgage': 'mortgage',
        'Consumer': 'consumer_lending',
        'Consumer Lending': 'consumer_lending',
    }
    
    # Merge raw firm data with aggregated stats
    result = []
    processed_tickers = set()
    
    # First, process firms from firms.json that have trade activity
    for firm in raw_firms:
        ticker = firm.get('ticker', '')
        stats = firm_stats.get(ticker, {})
        
        industry = firm.get('industry', '')
        industry_lower = industry_map.get(industry, industry.lower()) if industry else 'other'
        
        result.append({
            'name': firm.get('name', ''),
            'ticker': ticker,
            'industry': industry_lower,
            'total': stats.get('total_value', 0),
            'officials': len(stats.get('officials', set())),
            'stock_trades': stats.get('trade_count', 0),
            'quote': firm.get('quote'),
            'news': firm.get('news', [])[:3] if firm.get('news') else [],  # Limit news items
        })
        processed_tickers.add(ticker)
    
    # Add any firms from trades that aren't in firms.json
    for ticker, stats in firm_stats.items():
        if ticker not in processed_tickers:
            result.append({
                'name': stats.get('company_name', ticker),
                'ticker': ticker,
                'industry': 'other',
                'total': stats.get('total_value', 0),
                'officials': len(stats.get('officials', set())),
                'stock_trades': stats.get('trade_count', 0),
                'quote': None,
                'news': [],
            })
    
    # Sort by total trade value (descending)
    result.sort(key=lambda x: x.get('total', 0), reverse=True)
    
    return result


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


def save_insights(insights: List[Dict[str, Any]], weekly_dir: Optional[Path] = None):
    """Save AI-generated pattern insights."""
    data = {
        'insights': insights,
        'generated_at': datetime.now().isoformat(),
        'version': '1.0'
    }
    save_json('insights.json', data, weekly_dir)


def get_insights() -> List[Dict[str, Any]]:
    """Get AI-generated pattern insights from storage."""
    data = load_json('insights.json')
    if data and 'insights' in data:
        return data['insights']
    return []


def get_insights_metadata() -> Dict[str, Any]:
    """Get metadata about when insights were generated."""
    data = load_json('insights.json')
    if data:
        return {
            'generated_at': data.get('generated_at'),
            'version': data.get('version'),
            'count': len(data.get('insights', []))
        }
    return {}


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
