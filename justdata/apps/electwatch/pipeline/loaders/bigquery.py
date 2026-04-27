"""BigQuery write operations for the ElectWatch weekly pipeline.

Wraps the data_store service: trend snapshot, officials/firms/industries/
committees/news/summaries/insights/metadata writes plus the matching
report and post-write validation.
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

from justdata.apps.electwatch.weekly_update import ELECTION_CYCLE_START

logger = logging.getLogger(__name__)


def save_all_data(coordinator):
    """Save all processed data to storage."""
    from justdata.apps.electwatch.services.data_store import (
        save_officials, save_firms, save_industries,
        save_committees, save_news, save_summaries, save_insights, save_metadata,
        save_trend_snapshot, enrich_officials_with_trends,
        enrich_officials_with_time_series
    )

    # Save trend snapshot BEFORE enriching (captures raw current state)
    logger.info("Saving trend snapshot...")
    save_trend_snapshot(coordinator.officials_data)

    # Enrich officials with trend data for display (finance_pct trends)
    logger.info("Enriching officials with trend data...")
    enrich_officials_with_trends(coordinator.officials_data)

    # NEW: Enrich with time-series data for charts (trades/contributions by quarter)
    logger.info("Enriching officials with time-series data for trend charts...")
    enrich_officials_with_time_series(coordinator.officials_data)

    logger.info("Saving officials data...")
    save_officials(coordinator.officials_data, coordinator.weekly_dir)

    logger.info("Saving firms data...")
    save_firms(coordinator.firms_data, coordinator.weekly_dir)

    logger.info("Saving industries data...")
    save_industries(coordinator.industries_data, coordinator.weekly_dir)

    logger.info("Saving committees data...")
    save_committees(coordinator.committees_data, coordinator.weekly_dir)

    logger.info("Saving news data...")
    save_news(coordinator.news_data, coordinator.weekly_dir)

    logger.info("Saving AI summaries...")
    save_summaries(coordinator.summaries, coordinator.weekly_dir)

    logger.info("Generating AI pattern insights...")
    insights = coordinator._generate_pattern_insights()
    if insights:
        logger.info(f"Saving {len(insights)} AI insights...")
        save_insights(insights, coordinator.weekly_dir)
    else:
        logger.warning("No insights generated - using sample insights")
        from justdata.apps.electwatch.services.ai_pattern_insights import get_sample_insights
        save_insights(get_sample_insights(), coordinator.weekly_dir)

    # Calculate next update time (next Sunday midnight)
    now = datetime.now()
    days_until_sunday = (6 - now.weekday()) % 7
    if days_until_sunday == 0 and now.hour >= 1:  # If it's Sunday after 1am, next week
        days_until_sunday = 7
    next_sunday = (now + timedelta(days=days_until_sunday)).replace(hour=0, minute=0, second=0, microsecond=0)

    # All data uses election cycle start (2023-2024 and 2025-2026 cycles)
    cycle_start = datetime.strptime(ELECTION_CYCLE_START, '%Y-%m-%d')
    stock_start = cycle_start
    fec_start = cycle_start

    metadata = {
        'status': 'valid',
        'last_updated': coordinator.start_time.isoformat(),
        'last_updated_display': coordinator.start_time.strftime('%B %d, %Y at %I:%M %p'),
        'data_window': {
            'start': datetime.strptime(ELECTION_CYCLE_START, '%Y-%m-%d').strftime('%B %d, %Y'),
            'end': coordinator.start_time.strftime('%B %d, %Y')
        },
        'stock_data_window': {
            'start': stock_start.strftime('%B %d, %Y'),
            'end': coordinator.start_time.strftime('%B %d, %Y'),
            'start_iso': stock_start.strftime('%Y-%m-%d'),
            'end_iso': coordinator.start_time.strftime('%Y-%m-%d'),
            'description': '24-month rolling window of STOCK Act disclosures'
        },
        'fec_data_window': {
            'start': fec_start.strftime('%B %d, %Y'),
            'end': coordinator.start_time.strftime('%B %d, %Y'),
            'start_iso': fec_start.strftime('%Y-%m-%d'),
            'end_iso': coordinator.start_time.strftime('%Y-%m-%d'),
            'description': '24-month rolling window of FEC contributions'
        },
        'next_update': next_sunday.isoformat(),
        'next_update_display': next_sunday.strftime('%B %d, %Y at midnight'),
        'data_sources': coordinator.source_status,
        'counts': {
            'officials': len(coordinator.officials_data),
            'firms': len(coordinator.firms_data),
            'industries': len(coordinator.industries_data),
            'committees': len(coordinator.committees_data),
            'news_articles': len(coordinator.news_data)
        },
        'errors': coordinator.errors,
        'warnings': coordinator.warnings
    }

    logger.info("Saving metadata...")
    save_metadata(metadata, coordinator.weekly_dir)

    logger.info("All data saved to BigQuery")

    # Generate and save matching report
    logger.info("Generating matching report...")
    matching_report = _generate_matching_report(coordinator)
    _save_matching_report(matching_report)

    # Validate data consistency
    logger.info("Validating data consistency...")
    validation_errors = _validate_data_consistency(coordinator)
    if validation_errors:
        logger.warning(f"Data validation found {len(validation_errors)} issues")
        for err in validation_errors[:10]:
            logger.warning(f"  - {err}")


def _generate_matching_report(coordinator) -> Dict:
    """Generate report of matching success/failure rates."""
    total_officials = len(coordinator.officials_data)
    officials_with_fec = sum(1 for o in coordinator.officials_data if o.get('fec_candidate_id'))
    officials_with_trades = sum(1 for o in coordinator.officials_data if o.get('trades'))
    officials_with_contributions = sum(1 for o in coordinator.officials_data if o.get('contributions', 0) > 0)
    officials_with_financial_pac = sum(1 for o in coordinator.officials_data if o.get('financial_sector_pac', 0) > 0)

    # Get unmatched names from FMP processing
    unmatched_fmp = getattr(coordinator, '_unmatched_fmp_names', [])

    # Get officials without FEC match from source status
    fec_status = coordinator.source_status.get('fec', {})
    crosswalk_matches = fec_status.get('crosswalk_matches', 0)
    crosswalk_misses = fec_status.get('crosswalk_misses', 0)

    return {
        'generated_at': datetime.now().isoformat(),
        'total_officials': total_officials,
        'fec_enriched': officials_with_fec,
        'fec_enriched_pct': round(officials_with_fec / total_officials * 100, 1) if total_officials else 0,
        'fmp_enriched': officials_with_trades,
        'fmp_enriched_pct': round(officials_with_trades / total_officials * 100, 1) if total_officials else 0,
        'with_contributions': officials_with_contributions,
        'with_financial_pac': officials_with_financial_pac,
        'crosswalk_stats': {
            'matches': crosswalk_matches,
            'misses': crosswalk_misses,
            'match_rate_pct': round(crosswalk_matches / (crosswalk_matches + crosswalk_misses) * 100, 1) if (crosswalk_matches + crosswalk_misses) > 0 else 0
        },
        'unmatched_fmp_names': unmatched_fmp,
        'unmatched_fmp_count': len(unmatched_fmp),
        'source_status': coordinator.source_status,
        'summary': {
            'fec_rate': f"{officials_with_fec}/{total_officials} ({round(officials_with_fec / total_officials * 100, 1) if total_officials else 0}%)",
            'trade_rate': f"{officials_with_trades}/{total_officials} ({round(officials_with_trades / total_officials * 100, 1) if total_officials else 0}%)",
            'crosswalk_rate': f"{crosswalk_matches}/{crosswalk_matches + crosswalk_misses} ({round(crosswalk_matches / (crosswalk_matches + crosswalk_misses) * 100, 1) if (crosswalk_matches + crosswalk_misses) > 0 else 0}%)"
        }
    }


def _save_matching_report(report: Dict):
    """Save matching report to data/current/matching_report.json."""
    # Path is relative to the electwatch app dir; coordinator lives there.
    app_dir = Path(__file__).resolve().parents[2]
    report_path = app_dir / 'data' / 'current' / 'matching_report.json'
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    logger.info(f"Matching report saved to {report_path}")


def _validate_data_consistency(coordinator) -> List[str]:
    """Validate that all data is properly connected and consistent.

    Returns:
        List of validation error messages
    """
    errors = []

    for official in coordinator.officials_data:
        name = official.get('name', 'Unknown')

        # Check required fields
        if not official.get('bioguide_id'):
            # Only warn for officials with significant activity
            if official.get('contributions', 0) > 10000 or official.get('total_trades', 0) > 5:
                errors.append(f"{name}: Missing bioguide_id (has ${official.get('contributions', 0):,} contributions)")

        # Check contribution consistency
        pac_total = official.get('contributions', 0) or 0
        individual_total = official.get('individual_contributions_total', 0) or official.get('individual_contributions', 0) or 0

        # Get display totals if they exist
        display = official.get('contributions_display', {})
        display_total = display.get('total', 0) if isinstance(display, dict) else 0
        display_financial = display.get('financial', 0) if isinstance(display, dict) else 0

        # Only check if we have display data
        if display_total > 0:
            expected_total = pac_total + individual_total
            # Allow 1% tolerance for rounding
            if abs(expected_total - display_total) > display_total * 0.01 and abs(expected_total - display_total) > 1000:
                errors.append(f"{name}: Contribution mismatch - PAC({pac_total:,}) + Individual({individual_total:,}) = {expected_total:,} != Display({display_total:,})")

        # Check years in Congress vs first_elected
        years = official.get('years_in_congress', 0)
        first_elected = official.get('first_elected')
        if first_elected and years:
            current_year = datetime.now().year
            expected_years = current_year - first_elected
            # Allow 1 year tolerance
            if abs(years - expected_years) > 1:
                errors.append(f"{name}: Years mismatch - stored({years}) vs calculated({expected_years}) from first_elected({first_elected})")

        # Check for FEC ID without contributions (suspicious)
        if official.get('fec_candidate_id') and not official.get('contributions') and not official.get('pac_contributions'):
            # This might be normal for new members, just log as info
            logger.debug(f"{name}: Has FEC ID but no contribution data")

    return errors
