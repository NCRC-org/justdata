#!/usr/bin/env python3
"""
Test script for Fifth Third Bank with file-based caching.
Collects all data once and caches to JSON files for offline iteration.

Usage:
    # First run - collects and caches all data
    python test_fifth_third_cached.py

    # Subsequent runs - uses cached data (fast)
    python test_fifth_third_cached.py

    # Force refresh - ignores cache
    python test_fifth_third_cached.py --refresh

    # Just show cached data summary
    python test_fifth_third_cached.py --summary
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add repo root to path
# test_fifth_third_cached.py is at apps/lenderprofile/ so parents[2] = JustData
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

# Load environment
from dotenv import load_dotenv
load_dotenv(REPO_ROOT / '.env')

from justdata.apps.lenderprofile.cache.file_cache import FileCache, CachingDataCollector


# Fifth Third Bank identifiers (pre-resolved)
FIFTH_THIRD_IDENTIFIERS = {
    'institution_name': 'Fifth Third Bank',
    'fdic_cert': '6672',
    'rssd_id': '723112',
    'lei': '5493008DL67Z4K2Y4E93',  # Fifth Third Bancorp
    'sec_cik': '35527',
    'ticker': 'FITB',
    'ncua_id': None,  # Not a credit union
}


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def show_cache_summary(cache: FileCache):
    """Display summary of cached data."""
    print_section("CACHED DATA SUMMARY")

    meta = cache.get_metadata()
    if meta:
        print(f"Institution: {meta.get('institution')}")
        print(f"Last Updated: {meta.get('last_updated')}")
        print(f"Cache Dir: {meta.get('cache_dir')}")

    print(f"\nCached Sources ({len(cache.get_cached_sources())}):")
    for source in cache.get_cached_sources():
        file_path = cache._get_file_path(source)
        size = file_path.stat().st_size / 1024  # KB
        print(f"  - {source}.json ({size:.1f} KB)")

    # Show sample of each source
    print("\n" + "-"*40)
    print("DATA PREVIEWS:")
    print("-"*40)

    for source in cache.get_cached_sources():
        data = cache.load(source)
        if data:
            preview = str(data)[:200]
            if len(str(data)) > 200:
                preview += "..."
            print(f"\n{source}:")
            if isinstance(data, dict):
                print(f"  Keys: {list(data.keys())[:8]}")
            elif isinstance(data, list):
                print(f"  Items: {len(data)}")
            else:
                print(f"  Type: {type(data).__name__}")


def collect_fifth_third_data(force_refresh: bool = False):
    """Collect all Fifth Third data with caching."""
    print_section("FIFTH THIRD BANK DATA COLLECTION")

    institution_name = FIFTH_THIRD_IDENTIFIERS['institution_name']
    cache = FileCache(institution_name)

    # Check existing cache
    existing = cache.get_cached_sources()
    if existing and not force_refresh:
        print(f"Found {len(existing)} cached sources")
        print("Use --refresh to force refresh")

        # Show what we have
        show_cache_summary(cache)

        # Ask if user wants to proceed with cached data
        print("\n" + "="*60)
        print("Cache is available. You can:")
        print("  1. Use cached data (default) - just start the server")
        print("  2. Force refresh with: python test_fifth_third_cached.py --refresh")
        return cache.load_all()

    # Collect fresh data
    print(f"\nCollecting data for: {institution_name}")
    print(f"Identifiers: {json.dumps(FIFTH_THIRD_IDENTIFIERS, indent=2)}")

    collector = CachingDataCollector(institution_name, use_cache=True)

    print("\nStarting data collection (this may take 1-2 minutes)...")
    start_time = datetime.now()

    try:
        data = collector.collect_with_cache(
            FIFTH_THIRD_IDENTIFIERS,
            force_refresh=force_refresh
        )

        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\nData collection completed in {elapsed:.1f} seconds")

        # Show summary
        show_cache_summary(cache)

        return data

    except Exception as e:
        print(f"\nError during data collection: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    parser = argparse.ArgumentParser(description='Fifth Third Bank data collection with caching')
    parser.add_argument('--refresh', action='store_true', help='Force refresh (ignore cache)')
    parser.add_argument('--summary', action='store_true', help='Just show cache summary')
    parser.add_argument('--clear', action='store_true', help='Clear cache')
    args = parser.parse_args()

    institution_name = FIFTH_THIRD_IDENTIFIERS['institution_name']
    cache = FileCache(institution_name)

    if args.clear:
        deleted = cache.clear()
        print(f"Cleared {deleted} cached files")
        return

    if args.summary:
        show_cache_summary(cache)
        return

    # Collect data
    data = collect_fifth_third_data(force_refresh=args.refresh)

    if data:
        print_section("COLLECTION COMPLETE")
        print(f"\nData cached at: {cache.cache_dir}")
        print(f"\nYou can now:")
        print(f"  1. Edit JSON files in the cache directory")
        print(f"  2. Run the server: python apps/lenderprofile/app.py")
        print(f"  3. The server will use cached data automatically")


if __name__ == '__main__':
    main()
