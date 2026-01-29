"""
Alert configuration for JustData Slack bot.
"""

import os

# Slack configuration
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')
SLACK_ALERTS_CHANNEL = os.getenv('SLACK_ALERTS_CHANNEL', '#justdata-alerts')

# Sync alert settings
SYNC_ALERTS_ENABLED = True
SYNC_SLOW_THRESHOLD_SECONDS = 300  # 5 minutes

# Data quality alert settings
DATA_QUALITY_ALERTS_ENABLED = True
ROW_DROP_THRESHOLD_PERCENT = 5  # Alert if >5% drop
SYNC_MISMATCH_THRESHOLD_PERCENT = 1  # Alert if >1% mismatch
NULL_SPIKE_THRESHOLD_PERCENT = 10  # Alert if >10% nulls

# Usage alert settings
USAGE_ALERTS_ENABLED = True
HIGH_USAGE_THRESHOLD = 200  # Reports per day
OUTAGE_THRESHOLD_HOURS = 24  # Hours with no reports
ERROR_RATE_THRESHOLD_PERCENT = 10  # Error rate threshold

# Scheduled report settings
DAILY_SUMMARY_ENABLED = True
DAILY_SUMMARY_HOUR = 8  # 8 AM UTC
WEEKLY_REPORT_ENABLED = True
WEEKLY_REPORT_DAY = 0  # Monday
WEEKLY_REPORT_HOUR = 9  # 9 AM UTC
MONTHLY_REPORT_ENABLED = True
MONTHLY_REPORT_DAY = 1  # 1st of month

# Tables to monitor
MONITORED_TABLES = [
    ('sb_lenders', 'bizsight'),
    ('sb_county_summary', 'bizsight'),
    ('lenders18', 'lendsight'),
    ('lender_names_gleif', 'shared'),
    ('de_hmda', 'shared'),
    ('de_hmda_county_summary', 'lendsight'),
    ('de_hmda_tract_summary', 'lendsight'),
    ('sod', 'branchsight'),
    ('branch_hhi_summary', 'branchsight'),
    ('cu_branches', 'lenderprofile'),
    ('cu_call_reports', 'lenderprofile'),
]


def is_alert_muted() -> bool:
    """Check if alerts are currently muted."""
    # In a real implementation, this would check a database/cache
    return False


def get_mute_expiry():
    """Get when the current mute expires."""
    return None
