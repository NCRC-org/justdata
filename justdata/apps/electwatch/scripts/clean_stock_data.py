#!/usr/bin/env python3
"""
Script to clean existing STOCK Act data in ElectWatch.

This script:
1. Reprocesses the stock trades cache to clean company names
2. Reprocesses all weekly firms.json files
3. Reprocesses the current firms.json

Run from the JustData directory:
    python justdata/apps/electwatch/scripts/clean_stock_data.py

Author: Claude (Agent 4 - STOCK Act Data Cleaning)
Date: January 31, 2026
"""

import json
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
SCRIPT_DIR = Path(__file__).parent
ELECTWATCH_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(ELECTWATCH_DIR.parent.parent.parent))

from justdata.apps.electwatch.services.ticker_cleaner import (
    clean_company_name, classify_ticker_industry, is_transaction_text
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


DATA_DIR = ELECTWATCH_DIR / "data"


def clean_stock_trades_cache():
    """Clean the stock trades bulk cache."""
    cache_path = DATA_DIR / "cache" / "stock_trades_bulk_cache.json"

    if not cache_path.exists():
        logger.warning(f"Stock trades cache not found: {cache_path}")
        return

    logger.info(f"Processing {cache_path}")

    with open(cache_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    trades = data.get('data', [])
    if not trades:
        logger.warning("No trades found in cache")
        return

    stats = {
        'total': len(trades),
        'dirty_names_found': 0,
        'cleaned': 0
    }

    for trade in trades:
        ticker = trade.get('ticker', '')
        raw_company = trade.get('company')

        if raw_company and is_transaction_text(raw_company):
            stats['dirty_names_found'] += 1

        clean_name = clean_company_name(ticker, raw_company)
        if clean_name != raw_company:
            trade['company'] = clean_name
            stats['cleaned'] += 1

    # Save
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    logger.info(f"Stock trades cache: {stats['total']} trades, "
                f"{stats['dirty_names_found']} dirty names found, "
                f"{stats['cleaned']} cleaned")


def clean_firms_file(filepath: Path) -> dict:
    """Clean a single firms.json file."""
    if not filepath.exists():
        return {'error': 'file not found'}

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    firms = data.get('firms', [])
    if not firms:
        return {'total': 0, 'cleaned_names': 0, 'added_sectors': 0}

    stats = {
        'total': len(firms),
        'cleaned_names': 0,
        'added_sectors': 0
    }

    for firm in firms:
        ticker = firm.get('ticker', '')
        original_name = firm.get('name')
        original_sector = firm.get('sector')

        # Clean name
        new_name = clean_company_name(ticker, original_name)
        if new_name != original_name:
            firm['name'] = new_name
            stats['cleaned_names'] += 1

        # Add sector if missing
        if not original_sector or original_sector in ['', 'OTHER', None]:
            sector, sic_desc = classify_ticker_industry(ticker)
            if sector:
                firm['sector'] = sector
                firm['industry'] = sector
                firm['sic_description'] = sic_desc
                stats['added_sectors'] += 1

    # Rebuild by_name index
    data['firms'] = firms
    data['by_name'] = {f['name']: f for f in firms if f.get('name')}
    data['count'] = len(firms)
    data['cleaned_at'] = datetime.now().isoformat()

    # Save
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    return stats


def clean_all_weekly_firms():
    """Clean all weekly firms.json files."""
    weekly_dir = DATA_DIR / "weekly"

    if not weekly_dir.exists():
        logger.warning(f"Weekly directory not found: {weekly_dir}")
        return

    total_stats = {
        'files_processed': 0,
        'total_firms': 0,
        'cleaned_names': 0,
        'added_sectors': 0
    }

    for date_dir in sorted(weekly_dir.iterdir()):
        if not date_dir.is_dir():
            continue

        firms_file = date_dir / "firms.json"
        if not firms_file.exists():
            continue

        logger.info(f"Processing {firms_file}")
        stats = clean_firms_file(firms_file)

        if 'error' not in stats:
            total_stats['files_processed'] += 1
            total_stats['total_firms'] += stats['total']
            total_stats['cleaned_names'] += stats['cleaned_names']
            total_stats['added_sectors'] += stats['added_sectors']

    logger.info(f"Weekly firms: {total_stats['files_processed']} files, "
                f"{total_stats['total_firms']} total firms, "
                f"{total_stats['cleaned_names']} names cleaned, "
                f"{total_stats['added_sectors']} sectors added")


def clean_current_firms():
    """Clean the current firms.json file."""
    current_file = DATA_DIR / "current" / "firms.json"

    if not current_file.exists():
        logger.warning(f"Current firms file not found: {current_file}")
        return

    logger.info(f"Processing {current_file}")
    stats = clean_firms_file(current_file)

    if 'error' not in stats:
        logger.info(f"Current firms: {stats['total']} firms, "
                    f"{stats['cleaned_names']} names cleaned, "
                    f"{stats['added_sectors']} sectors added")


def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("STOCK Act Data Cleaning Script")
    logger.info("=" * 60)

    # Clean the source cache first
    logger.info("\n--- Cleaning Stock Trades Cache ---")
    clean_stock_trades_cache()

    # Clean weekly firms files
    logger.info("\n--- Cleaning Weekly Firms Files ---")
    clean_all_weekly_firms()

    # Clean current firms file
    logger.info("\n--- Cleaning Current Firms File ---")
    clean_current_firms()

    logger.info("\n" + "=" * 60)
    logger.info("Cleaning complete!")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
