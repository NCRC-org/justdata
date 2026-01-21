#!/usr/bin/env python3
"""
Photo Service for ElectWatch - Downloads and manages official photos locally.

LICENSING AND ATTRIBUTION:
--------------------------
Photos are sourced from two primary sources:

1. WIKIMEDIA COMMONS - Photos under Creative Commons / Public Domain licenses
   - Most Congressional portraits are Public Domain as U.S. government works
   - Citation format: "Title" by Creator (Year). Source: Wikimedia Commons. License.
   - See individual entries for specific attribution requirements.

2. U.S. HOUSE CLERK / BIOGUIDE - Official Congressional portraits
   - Source: https://clerk.house.gov and https://bioguide.congress.gov
   - These are Public Domain as official U.S. government works
   - Citation: Official Congressional portrait. Source: U.S. House Clerk / Bioguide.

Usage:
    python -m apps.electwatch.services.photo_service

All photos should display attribution on hover as per accessibility and licensing
best practices.
"""

import os
import sys
import json
import logging
import requests
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

# Setup paths
REPO_ROOT = Path(__file__).resolve().parents[3]
APP_DIR = Path(__file__).resolve().parents[1]
PHOTOS_DIR = APP_DIR / 'static' / 'img' / 'officials'

# Ensure photos directory exists
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)


# =============================================================================
# PHOTO SOURCES WITH FULL CITATION INFORMATION
# =============================================================================
#
# Each entry contains complete citation information:
#   - title: Image title/description
#   - creator: Photographer/creator (usually U.S. Government)
#   - year: Year photo was created
#   - license: License type (Public Domain, CC BY-SA 4.0, etc.)
#   - source: Source name (Wikimedia Commons, U.S. House Clerk, Bioguide)
#   - source_url: URL to the source page
#   - image_url: Direct URL to download the image
#   - local_filename: Local filename when downloaded
#
# Citation Format (on hover):
#   "Title" by Creator (Year). Source: [Source Name]. [License].
# =============================================================================

WIKIMEDIA_PHOTOS: Dict[str, Dict] = {
    # =========================================================================
    # SENATE MEMBERS - From Wikimedia Commons
    # =========================================================================
    'Dave McCormick': {
        'title': 'McCormick Portrait',
        'creator': 'U.S. Senate',
        'year': '2025',
        'license': 'Public Domain',
        'source': 'Wikimedia Commons',
        'source_url': 'https://commons.wikimedia.org/wiki/File:McCormick_Portrait_(HR).jpg',
        'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c6/McCormick_Portrait_%28HR%29.jpg/330px-McCormick_Portrait_%28HR%29.jpg',
        'local_filename': 'mccormick_dave.jpg'
    },
    'David McCormick': {  # Alias
        'title': 'McCormick Portrait',
        'creator': 'U.S. Senate',
        'year': '2025',
        'license': 'Public Domain',
        'source': 'Wikimedia Commons',
        'source_url': 'https://commons.wikimedia.org/wiki/File:McCormick_Portrait_(HR).jpg',
        'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c6/McCormick_Portrait_%28HR%29.jpg/330px-McCormick_Portrait_%28HR%29.jpg',
        'local_filename': 'mccormick_dave.jpg'
    },
    'Angus King': {
        'title': 'Angus King, official portrait, 113th Congress',
        'creator': 'U.S. Senate',
        'year': '2013',
        'license': 'Public Domain',
        'source': 'Wikimedia Commons',
        'source_url': 'https://commons.wikimedia.org/wiki/File:Angus_King,_official_portrait,_113th_Congress.jpg',
        'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/Angus_King%2C_official_portrait%2C_113th_Congress.jpg/330px-Angus_King%2C_official_portrait%2C_113th_Congress.jpg',
        'local_filename': 'king_angus.jpg'
    },
    'Angus S. King': {  # Alias
        'title': 'Angus King, official portrait, 113th Congress',
        'creator': 'U.S. Senate',
        'year': '2013',
        'license': 'Public Domain',
        'source': 'Wikimedia Commons',
        'source_url': 'https://commons.wikimedia.org/wiki/File:Angus_King,_official_portrait,_113th_Congress.jpg',
        'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/Angus_King%2C_official_portrait%2C_113th_Congress.jpg/330px-Angus_King%2C_official_portrait%2C_113th_Congress.jpg',
        'local_filename': 'king_angus.jpg'
    },
    'Ted Cruz': {
        'title': 'Ted Cruz official 116th portrait',
        'creator': 'U.S. Senate',
        'year': '2019',
        'license': 'Public Domain',
        'source': 'Wikimedia Commons',
        'source_url': 'https://commons.wikimedia.org/wiki/File:Ted_Cruz_official_116th_portrait_(3x4_cropped_b).jpg',
        'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/Ted_Cruz_official_116th_portrait_%283x4_cropped_b%29.jpg/330px-Ted_Cruz_official_116th_portrait_%283x4_cropped_b%29.jpg',
        'local_filename': 'cruz_ted.jpg'
    },
    'Rafael Cruz': {  # Alias (formal name - Ted Cruz)
        'title': 'Ted Cruz official 116th portrait',
        'creator': 'U.S. Senate',
        'year': '2019',
        'license': 'Public Domain',
        'source': 'Wikimedia Commons',
        'source_url': 'https://commons.wikimedia.org/wiki/File:Ted_Cruz_official_116th_portrait_(3x4_cropped_b).jpg',
        'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/Ted_Cruz_official_116th_portrait_%283x4_cropped_b%29.jpg/330px-Ted_Cruz_official_116th_portrait_%283x4_cropped_b%29.jpg',
        'local_filename': 'cruz_ted.jpg'
    },
    'Markwayne Mullin': {
        'title': 'Markwayne Mullin official Senate photo',
        'creator': 'U.S. Senate',
        'year': '2023',
        'license': 'Public Domain',
        'source': 'Wikimedia Commons',
        'source_url': 'https://commons.wikimedia.org/wiki/File:Markwayne_Mullin_official_Senate_photo.jpg',
        'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c7/Markwayne_Mullin_official_Senate_photo.jpg/330px-Markwayne_Mullin_official_Senate_photo.jpg',
        'local_filename': 'mullin_markwayne.jpg'
    },
    'Shelley Moore Capito': {
        'title': 'Shelley Moore Capito official Senate photo',
        'creator': 'U.S. Senate',
        'year': '2015',
        'license': 'Public Domain',
        'source': 'Wikimedia Commons',
        'source_url': 'https://commons.wikimedia.org/wiki/File:Shelley_Moore_Capito_official_Senate_photo.jpg',
        'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/75/Shelley_Moore_Capito_official_Senate_photo.jpg/330px-Shelley_Moore_Capito_official_Senate_photo.jpg',
        'local_filename': 'capito_shelley.jpg'
    },
    'John Boozman': {
        'title': 'Senator John Boozman Official Portrait, 115th Congress',
        'creator': 'U.S. Senate',
        'year': '2017',
        'license': 'Public Domain',
        'source': 'Wikimedia Commons',
        'source_url': 'https://commons.wikimedia.org/wiki/File:Senator_John_Boozman_Official_Portrait_(115th_Congress).jpg',
        'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/30/Senator_John_Boozman_Official_Portrait_%28115th_Congress%29.jpg/330px-Senator_John_Boozman_Official_Portrait_%28115th_Congress%29.jpg',
        'local_filename': 'boozman_john.jpg'
    },
    'Tina Smith': {
        'title': 'Tina Smith, official portrait, 116th Congress',
        'creator': 'U.S. Senate',
        'year': '2019',
        'license': 'Public Domain',
        'source': 'Wikimedia Commons',
        'source_url': 'https://commons.wikimedia.org/wiki/File:Tina_Smith,_official_portrait,_116th_congress.jpg',
        'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/f/ff/Tina_Smith%2C_official_portrait%2C_116th_congress.jpg/330px-Tina_Smith%2C_official_portrait%2C_116th_congress.jpg',
        'local_filename': 'smith_tina.jpg'
    },
    'John Kennedy': {
        'title': 'John Kennedy, official portrait, 115th Congress',
        'creator': 'U.S. Senate',
        'year': '2017',
        'license': 'Public Domain',
        'source': 'Wikimedia Commons',
        'source_url': 'https://commons.wikimedia.org/wiki/File:John_Kennedy,_official_portrait,_115th_Congress_(cropped).jpg',
        'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/af/John_Kennedy%2C_official_portrait%2C_115th_Congress_%28cropped%29.jpg/330px-John_Kennedy%2C_official_portrait%2C_115th_Congress_%28cropped%29.jpg',
        'local_filename': 'kennedy_john.jpg'
    },
    'Tommy Tuberville': {
        'title': 'Tommy Tuberville official portrait',
        'creator': 'U.S. Senate',
        'year': '2021',
        'license': 'Public Domain',
        'source': 'Wikimedia Commons',
        'source_url': 'https://commons.wikimedia.org/wiki/File:Tommy_tuberville.jpg',
        'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/d/df/Tommy_tuberville.jpg/330px-Tommy_tuberville.jpg',
        'local_filename': 'tuberville_tommy.jpg'
    },
    'Thomas Tuberville': {  # Alias (formal name)
        'title': 'Tommy Tuberville official portrait',
        'creator': 'U.S. Senate',
        'year': '2021',
        'license': 'Public Domain',
        'source': 'Wikimedia Commons',
        'source_url': 'https://commons.wikimedia.org/wiki/File:Tommy_tuberville.jpg',
        'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/d/df/Tommy_tuberville.jpg/330px-Tommy_tuberville.jpg',
        'local_filename': 'tuberville_tommy.jpg'
    },
    'Sheldon Whitehouse': {
        'title': 'Sheldon Whitehouse, official portrait, 116th Congress',
        'creator': 'U.S. Senate',
        'year': '2019',
        'license': 'Public Domain',
        'source': 'Wikimedia Commons',
        'source_url': 'https://commons.wikimedia.org/wiki/File:Sheldon_Whitehouse,_official_portrait,_116th_congress.jpg',
        'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/Sheldon_Whitehouse%2C_official_portrait%2C_116th_congress.jpg/330px-Sheldon_Whitehouse%2C_official_portrait%2C_116th_congress.jpg',
        'local_filename': 'whitehouse_sheldon.jpg'
    },
    'Mitch McConnell': {
        'title': 'Mitch McConnell 2016 official photo',
        'creator': 'U.S. Senate',
        'year': '2016',
        'license': 'Public Domain',
        'source': 'Wikimedia Commons',
        'source_url': 'https://commons.wikimedia.org/wiki/File:Mitch_McConnell_2016_official_photo_(1).jpg',
        'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/0b/Mitch_McConnell_2016_official_photo_%281%29.jpg/330px-Mitch_McConnell_2016_official_photo_%281%29.jpg',
        'local_filename': 'mcconnell_mitch.jpg'
    },
    'John Fetterman': {
        'title': 'John Fetterman official portrait',
        'creator': 'U.S. Senate',
        'year': '2023',
        'license': 'Public Domain',
        'source': 'Wikimedia Commons',
        'source_url': 'https://commons.wikimedia.org/wiki/File:John_Fetterman_official_portrait.jpg',
        'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/John_Fetterman_official_portrait.jpg/330px-John_Fetterman_official_portrait.jpg',
        'local_filename': 'fetterman_john.jpg'
    },
    'Ashley Moody': {
        'title': 'Official Portrait of Senator Ashley Moody',
        'creator': 'U.S. Senate',
        'year': '2025',
        'license': 'Public Domain',
        'source': 'Wikimedia Commons',
        'source_url': 'https://commons.wikimedia.org/wiki/File:Official_Portrait_of_Senator_Ashley_Moody_(cropped).jpg',
        'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/b/b7/Official_Portrait_of_Senator_Ashley_Moody_%28cropped%29.jpg/330px-Official_Portrait_of_Senator_Ashley_Moody_%28cropped%29.jpg',
        'local_filename': 'moody_ashley.jpg'
    },

    # =========================================================================
    # HOUSE MEMBERS - From Wikimedia Commons (119th Congress freshmen)
    # =========================================================================
    'Richard McCormick': {
        'title': 'Rep. Rich McCormick official photo, 118th Congress',
        'creator': 'U.S. House of Representatives',
        'year': '2023',
        'license': 'Public Domain',
        'source': 'Wikimedia Commons',
        'source_url': 'https://commons.wikimedia.org/wiki/File:Rep._Rich_McCormick_official_photo,_118th_Congress_(1).jpg',
        'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/Rep._Rich_McCormick_official_photo%2C_118th_Congress_%281%29.jpg/330px-Rep._Rich_McCormick_official_photo%2C_118th_Congress_%281%29.jpg',
        'local_filename': 'mccormick_richard.jpg'
    },
    'Rich McCormick': {  # Alias
        'title': 'Rep. Rich McCormick official photo, 118th Congress',
        'creator': 'U.S. House of Representatives',
        'year': '2023',
        'license': 'Public Domain',
        'source': 'Wikimedia Commons',
        'source_url': 'https://commons.wikimedia.org/wiki/File:Rep._Rich_McCormick_official_photo,_118th_Congress_(1).jpg',
        'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/Rep._Rich_McCormick_official_photo%2C_118th_Congress_%281%29.jpg/330px-Rep._Rich_McCormick_official_photo%2C_118th_Congress_%281%29.jpg',
        'local_filename': 'mccormick_richard.jpg'
    },
    'April Delaney': {
        'title': 'Rep. April McClain Delaney Official Portrait',
        'creator': 'U.S. House of Representatives',
        'year': '2025',
        'license': 'Public Domain',
        'source': 'Wikimedia Commons',
        'source_url': 'https://commons.wikimedia.org/wiki/File:Rep._April_McClain_Delaney_Official_Portrait.jpg',
        'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/4a/Rep._April_McClain_Delaney_Official_Portrait.jpg/330px-Rep._April_McClain_Delaney_Official_Portrait.jpg',
        'local_filename': 'delaney_april.jpg'
    },
    'April McClain Delaney': {  # Alias
        'title': 'Rep. April McClain Delaney Official Portrait',
        'creator': 'U.S. House of Representatives',
        'year': '2025',
        'license': 'Public Domain',
        'source': 'Wikimedia Commons',
        'source_url': 'https://commons.wikimedia.org/wiki/File:Rep._April_McClain_Delaney_Official_Portrait.jpg',
        'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/4a/Rep._April_McClain_Delaney_Official_Portrait.jpg/330px-Rep._April_McClain_Delaney_Official_Portrait.jpg',
        'local_filename': 'delaney_april.jpg'
    },
    'David Taylor': {
        'title': 'Rep. Dave Taylor Official Portrait',
        'creator': 'U.S. House of Representatives',
        'year': '2025',
        'license': 'Public Domain',
        'source': 'Wikimedia Commons',
        'source_url': 'https://commons.wikimedia.org/wiki/File:Rep._Dave_Taylor_Official_Portrait.jpg',
        'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/82/Rep._Dave_Taylor_Official_Portrait.jpg/330px-Rep._Dave_Taylor_Official_Portrait.jpg',
        'local_filename': 'taylor_david.jpg'
    },
    'Dave Taylor': {  # Alias
        'title': 'Rep. Dave Taylor Official Portrait',
        'creator': 'U.S. House of Representatives',
        'year': '2025',
        'license': 'Public Domain',
        'source': 'Wikimedia Commons',
        'source_url': 'https://commons.wikimedia.org/wiki/File:Rep._Dave_Taylor_Official_Portrait.jpg',
        'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/82/Rep._Dave_Taylor_Official_Portrait.jpg/330px-Rep._Dave_Taylor_Official_Portrait.jpg',
        'local_filename': 'taylor_david.jpg'
    },
    'George Whitesides': {
        'title': 'Rep. George Whitesides Official Portrait',
        'creator': 'U.S. House of Representatives',
        'year': '2025',
        'license': 'Public Domain',
        'source': 'Wikimedia Commons',
        'source_url': 'https://commons.wikimedia.org/wiki/File:Rep._George_Whitesides_Official_Portrait.jpg',
        'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/ae/Rep._George_Whitesides_Official_Portrait.jpg/330px-Rep._George_Whitesides_Official_Portrait.jpg',
        'local_filename': 'whitesides_george.jpg'
    },
    'Julie Johnson': {
        'title': 'Rep. Julie Johnson Official Portrait',
        'creator': 'U.S. House of Representatives',
        'year': '2025',
        'license': 'Public Domain',
        'source': 'Wikimedia Commons',
        'source_url': 'https://commons.wikimedia.org/wiki/File:Rep._Julie_Johnson_Official_Portrait.jpg',
        'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/b/b0/Rep._Julie_Johnson_Official_Portrait.jpg/330px-Rep._Julie_Johnson_Official_Portrait.jpg',
        'local_filename': 'johnson_julie.jpg'
    },
    'Rob Bresnahan': {
        'title': 'Rep. Rob Bresnahan official photo, 119th Congress',
        'creator': 'U.S. House of Representatives',
        'year': '2025',
        'license': 'Public Domain',
        'source': 'Wikimedia Commons',
        'source_url': 'https://commons.wikimedia.org/wiki/File:Rep._Rob_Bresnahan_official_photo,_119th_Congress.jpg',
        'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/5d/Rep._Rob_Bresnahan_official_photo%2C_119th_Congress.jpg/330px-Rep._Rob_Bresnahan_official_photo%2C_119th_Congress.jpg',
        'local_filename': 'bresnahan_rob.jpg'
    },
    'Sheri Biggs': {
        'title': 'Rep. Sheri Biggs official photo, 119th Congress',
        'creator': 'U.S. House of Representatives',
        'year': '2025',
        'license': 'Public Domain',
        'source': 'Wikimedia Commons',
        'source_url': 'https://commons.wikimedia.org/wiki/File:Rep._Sheri_Biggs_official_photo,_119th_Congress_(3x4_full_crop).jpg',
        'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/71/Rep._Sheri_Biggs_official_photo%2C_119th_Congress_%283x4_full_crop%29.jpg/330px-Rep._Sheri_Biggs_official_photo%2C_119th_Congress_%283x4_full_crop%29.jpg',
        'local_filename': 'biggs_sheri.jpg'
    },
    'Tony Wied': {
        'title': 'Representative Tony Wied Official Portrait',
        'creator': 'U.S. House of Representatives',
        'year': '2025',
        'license': 'Public Domain',
        'source': 'Wikimedia Commons',
        'source_url': 'https://commons.wikimedia.org/wiki/File:Representative_Tony_Wied_Official_Portrait.jpg',
        'image_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/Representative_Tony_Wied_Official_Portrait.jpg/330px-Representative_Tony_Wied_Official_Portrait.jpg',
        'local_filename': 'wied_tony.jpg'
    },
}

# Name aliases for matching officials data to photo entries
NAME_ALIASES = {
    'Angus S. King': 'Angus King',
    'Rafael Cruz': 'Ted Cruz',
    'Thomas Tuberville': 'Tommy Tuberville',
    'David McCormick': 'Dave McCormick',
    'Rich McCormick': 'Richard McCormick',
    'April McClain Delaney': 'April Delaney',
    'Dave Taylor': 'David Taylor',
}


# =============================================================================
# BIOGUIDE / HOUSE CLERK PHOTO CITATIONS
# =============================================================================
# For House members using photos from clerk.house.gov or bioguide.congress.gov
# These are all Public Domain U.S. Government works

def get_photo_citation_for_api(name: str, photo_url: str = None, photo_source: str = None, bioguide_id: str = None) -> str:
    """
    Get a formatted citation string for an official's photo.

    This is the main function to call from the API to get attribution text.
    Works with both Wikimedia photos and Bioguide/House Clerk photos.

    Args:
        name: Official's name
        photo_url: Current photo URL (to determine source if not provided)
        photo_source: Source type ('wikipedia', 'house_clerk', etc.)
        bioguide_id: Bioguide ID for House Clerk photos

    Returns:
        Formatted citation string for display on hover
    """
    # First check if we have Wikimedia citation info
    photo_info = get_photo_info(name)
    if photo_info:
        return format_citation(photo_info)

    # Check for House Clerk / Bioguide photos
    if photo_source == 'house_clerk' or (photo_url and 'clerk.house.gov' in photo_url):
        return f'"Official Congressional portrait of {name}" by U.S. House of Representatives. Source: U.S. House Clerk. Public Domain.'

    if photo_source == 'bioguide' or (photo_url and 'bioguide.congress.gov' in photo_url):
        source_url = f'https://bioguide.congress.gov/search/bio/{bioguide_id}' if bioguide_id else 'https://bioguide.congress.gov'
        return f'"Official Congressional portrait of {name}" by U.S. Congress. Source: Bioguide ({source_url}). Public Domain.'

    # Generic fallback
    if photo_url:
        return f'Official portrait of {name}. Public Domain.'

    return None


def get_bioguide_citation(name: str, bioguide_id: str) -> Dict:
    """
    Generate citation info for a Bioguide/House Clerk photo.

    Photos from clerk.house.gov and bioguide.congress.gov are official
    U.S. Government works in the Public Domain.

    Args:
        name: Official's name
        bioguide_id: Bioguide identifier (e.g., 'P000197' for Nancy Pelosi)

    Returns:
        Dict with citation information
    """
    return {
        'title': f'Official Congressional portrait of {name}',
        'creator': 'U.S. House of Representatives',
        'year': 'Current',
        'license': 'Public Domain',
        'source': 'U.S. House Clerk / Bioguide',
        'source_url': f'https://bioguide.congress.gov/search/bio/{bioguide_id}',
        'image_url': f'https://clerk.house.gov/images/members/{bioguide_id}.jpg',
    }


def format_citation(photo_info: Dict) -> str:
    """
    Format a photo citation for display (e.g., on hover tooltip).

    Format: "Title" by Creator (Year). Source: [Source]. [License].

    Args:
        photo_info: Dict containing title, creator, year, source, license

    Returns:
        Formatted citation string
    """
    title = photo_info.get('title', 'Official portrait')
    creator = photo_info.get('creator', 'U.S. Government')
    year = photo_info.get('year', '')
    source = photo_info.get('source', 'Unknown')
    license_type = photo_info.get('license', 'Public Domain')

    year_str = f" ({year})" if year else ""
    return f'"{title}" by {creator}{year_str}. Source: {source}. {license_type}.'


def get_photo_info(name: str) -> Optional[Dict]:
    """
    Get photo information for an official by name.

    Checks both direct name match and aliases.
    Photos are sourced from Wikimedia Commons and are used under
    Creative Commons / Public Domain licenses.

    Args:
        name: Official's name

    Returns:
        Dict with photo info or None if not found
    """
    # Direct lookup
    if name in WIKIMEDIA_PHOTOS:
        return WIKIMEDIA_PHOTOS[name]

    # Check aliases
    canonical_name = NAME_ALIASES.get(name)
    if canonical_name and canonical_name in WIKIMEDIA_PHOTOS:
        return WIKIMEDIA_PHOTOS[canonical_name]

    return None


def download_photo(name: str, force: bool = False) -> Optional[str]:
    """
    Download a photo from Wikimedia Commons and save locally.

    Photos are sourced from Wikimedia Commons under Creative Commons licenses.
    See WIKIMEDIA_PHOTOS for full attribution information.

    Args:
        name: Official's name
        force: If True, re-download even if file exists

    Returns:
        Local file path if successful, None otherwise
    """
    photo_info = get_photo_info(name)
    if not photo_info:
        logger.warning(f"No Wikimedia photo configured for: {name}")
        return None

    local_path = PHOTOS_DIR / photo_info['local_filename']

    # Skip if already downloaded
    if local_path.exists() and not force:
        logger.info(f"Photo already exists: {local_path}")
        return str(local_path)

    try:
        url = photo_info['image_url']
        logger.info(f"Downloading photo for {name} from Wikimedia Commons...")

        # Download with proper headers (Wikimedia requires User-Agent)
        headers = {
            'User-Agent': 'ElectWatch/1.0 (https://ncrc.org; contact@ncrc.org) Python/3.x'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        # Save to file
        with open(local_path, 'wb') as f:
            f.write(response.content)

        logger.info(f"Successfully downloaded: {local_path}")
        return str(local_path)

    except requests.RequestException as e:
        logger.error(f"Failed to download photo for {name}: {e}")
        return None


def download_all_photos(force: bool = False) -> Dict[str, str]:
    """
    Download all configured Wikimedia photos.

    Photos are sourced from Wikimedia Commons. See individual entries
    in WIKIMEDIA_PHOTOS for license and attribution details.

    Args:
        force: If True, re-download even if files exist

    Returns:
        Dict mapping names to local file paths
    """
    results = {}

    # Get unique photos (skip aliases that point to same file)
    seen_files = set()

    for name, info in WIKIMEDIA_PHOTOS.items():
        filename = info['local_filename']
        if filename in seen_files:
            continue
        seen_files.add(filename)

        path = download_photo(name, force=force)
        if path:
            results[name] = path

    return results


def get_local_photo_url(name: str) -> Optional[str]:
    """
    Get the local static URL for an official's photo.

    Use this instead of the remote Wikimedia URL when photos are downloaded.

    Args:
        name: Official's name

    Returns:
        Flask static URL path (e.g., '/static/img/officials/king_angus.jpg')
        or None if photo not available locally
    """
    photo_info = get_photo_info(name)
    if not photo_info:
        return None

    local_path = PHOTOS_DIR / photo_info['local_filename']
    if local_path.exists():
        return f"/static/img/officials/{photo_info['local_filename']}"

    return None


def get_photo_attribution(name: str) -> Optional[Dict]:
    """
    Get attribution information for an official's photo.

    This should be displayed when showing the photo (e.g., on hover)
    to comply with licensing best practices.

    Args:
        name: Official's name

    Returns:
        Dict with citation info including formatted 'citation' string, or None
    """
    photo_info = get_photo_info(name)
    if not photo_info:
        return None

    return {
        'title': photo_info['title'],
        'creator': photo_info['creator'],
        'year': photo_info['year'],
        'license': photo_info['license'],
        'source': photo_info['source'],
        'source_url': photo_info['source_url'],
        'citation': format_citation(photo_info)
    }


def generate_attribution_file():
    """
    Generate a markdown file documenting photo sources and licenses.

    Creates PHOTO_ATTRIBUTIONS.md in the static/img/officials directory.
    """
    output_path = PHOTOS_DIR / 'PHOTO_ATTRIBUTIONS.md'

    seen_files = set()
    unique_photos = []

    for name, info in WIKIMEDIA_PHOTOS.items():
        if info['local_filename'] in seen_files:
            continue
        seen_files.add(info['local_filename'])
        unique_photos.append((name, info))

    content = f"""# Photo Attributions for ElectWatch

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This directory contains official portrait photos used in ElectWatch.
All photos are sourced from Wikimedia Commons and are used in accordance
with their respective licenses.

## License Summary

All official U.S. Congressional portraits are **Public Domain** as works
of the United States federal government. According to U.S. copyright law,
works created by officers or employees of the United States Government as
part of their official duties are not eligible for copyright protection.

## Citation Format

When displaying these photos, the following citation format is used:

> "Title" by Creator (Year). Source: [Source Name]. [License].

## Photo Sources

| Official | File | Year | License | Source |
|----------|------|------|---------|--------|
"""

    for name, info in sorted(unique_photos, key=lambda x: x[0]):
        source_link = f"[{info['source']}]({info['source_url']})"
        content += f"| {name} | {info['local_filename']} | {info['year']} | {info['license']} | {source_link} |\n"

    content += """

## Bioguide / House Clerk Photos

For House members whose photos come from the U.S. House Clerk or Bioguide:

- **Source**: https://clerk.house.gov and https://bioguide.congress.gov
- **License**: Public Domain (U.S. Government work)
- **Citation**: "Official Congressional portrait of [Name]" by U.S. House of Representatives. Source: U.S. House Clerk / Bioguide. Public Domain.

## Wikimedia Commons

Photos sourced from [Wikimedia Commons](https://commons.wikimedia.org),
a media repository of free-use images and other media files.

For the most up-to-date license information, visit the Wikimedia Commons
file page linked in the Source column above.
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Attribution file generated: {output_path}")
    return output_path


def get_all_configured_names() -> List[str]:
    """Get list of all names with configured photos (excluding aliases)."""
    seen = set()
    names = []
    for name, info in WIKIMEDIA_PHOTOS.items():
        if info['local_filename'] not in seen:
            seen.add(info['local_filename'])
            names.append(name)
    return sorted(names)


# =============================================================================
# CLI Interface
# =============================================================================

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    print("=" * 60)
    print("ElectWatch Photo Service")
    print("Downloads official photos from Wikimedia Commons")
    print("=" * 60)
    print()
    print("LICENSING: All photos are Public Domain (U.S. Government works)")
    print("           or Creative Commons licensed from Wikimedia Commons.")
    print()

    # Show configured photos
    print(f"Photos directory: {PHOTOS_DIR}")
    print(f"Configured officials: {len(get_all_configured_names())}")
    print()

    # Download all photos
    print("Downloading photos from Wikimedia Commons...")
    print()

    results = download_all_photos()

    print()
    print(f"Successfully downloaded: {len(results)} photos")

    # Generate attribution file
    print()
    generate_attribution_file()

    print()
    print("Done!")
