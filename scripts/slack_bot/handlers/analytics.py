"""
Analytics command handlers for JustData Slack bot.
"""

import logging
from datetime import datetime, timedelta
from utils.bigquery import get_client

logger = logging.getLogger(__name__)


def handle_analytics(args: str, user_id: str) -> str:
    """
    Handle analytics commands.
    
    Usage:
        /jd analytics today     - Today's usage stats
        /jd analytics week      - This week's stats
        /jd analytics apps      - Usage by app
        /jd analytics users     - Top users
        /jd analytics counties  - Top counties analyzed
    """
    if not args:
        return get_today_analytics()
    
    parts = args.split()
    subcommand = parts[0].lower()
    
    if subcommand in ["today", "daily"]:
        return get_today_analytics()
    
    if subcommand in ["week", "weekly"]:
        return get_week_analytics()
    
    if subcommand == "apps":
        return get_app_analytics()
    
    if subcommand == "users":
        return get_user_analytics()
    
    if subcommand == "counties":
        return get_county_analytics()
    
    if subcommand == "help":
        return get_analytics_help()
    
    return f"Unknown analytics command: `{subcommand}`. Try `/jd analytics help`"


def get_analytics_help() -> str:
    """Return help text for analytics commands."""
    return """*Analytics Commands*

`/jd analytics today` - Today's usage statistics
`/jd analytics week` - This week's statistics
`/jd analytics apps` - Usage breakdown by app
`/jd analytics users` - Top users (anonymized)
`/jd analytics counties` - Most analyzed counties

*Aliases:*
• `/jd usage` also works for analytics commands
"""


def get_today_analytics() -> str:
    """Get today's analytics."""
    try:
        client = get_client()
        
        query = """
        SELECT
            COUNT(*) as total_reports,
            COUNT(DISTINCT user_id) as unique_users,
            COUNTIF(event_name LIKE '%lendsight%') as lendsight_reports,
            COUNTIF(event_name LIKE '%bizsight%') as bizsight_reports,
            COUNTIF(event_name LIKE '%branchsight%') as branchsight_reports,
            COUNTIF(event_name LIKE '%mergermeter%') as mergermeter_reports
        FROM `justdata-ncrc.firebase_analytics.all_events`
        WHERE DATE(event_timestamp) = CURRENT_DATE()
          AND event_name LIKE '%_report'
        """
        
        result = list(client.query(query).result())
        
        if not result or result[0].total_reports == 0:
            return ":bar_chart: *Today's Usage*\n\nNo reports generated yet today."
        
        row = result[0]
        
        return f""":bar_chart: *Today's Usage* ({datetime.now().strftime('%Y-%m-%d')})

*Total Reports:* {row.total_reports}
*Unique Users:* {row.unique_users}

*By App:*
• LendSight: {row.lendsight_reports}
• BizSight: {row.bizsight_reports}
• BranchSight: {row.branchsight_reports}
• MergerMeter: {row.mergermeter_reports}
"""
        
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        return f":x: Error getting analytics: {str(e)}"


def get_week_analytics() -> str:
    """Get this week's analytics."""
    try:
        client = get_client()
        
        query = """
        SELECT
            COUNT(*) as total_reports,
            COUNT(DISTINCT user_id) as unique_users,
            COUNT(DISTINCT DATE(event_timestamp)) as active_days
        FROM `justdata-ncrc.firebase_analytics.all_events`
        WHERE DATE(event_timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
          AND event_name LIKE '%_report'
        """
        
        result = list(client.query(query).result())
        
        if not result:
            return ":bar_chart: *This Week's Usage*\n\nNo reports in the last 7 days."
        
        row = result[0]
        avg_daily = row.total_reports / max(row.active_days, 1)
        
        return f""":bar_chart: *This Week's Usage* (Last 7 days)

*Total Reports:* {row.total_reports}
*Unique Users:* {row.unique_users}
*Active Days:* {row.active_days}
*Avg Daily:* {avg_daily:.1f} reports/day
"""
        
    except Exception as e:
        logger.error(f"Error getting week analytics: {e}")
        return f":x: Error getting analytics: {str(e)}"


def get_app_analytics() -> str:
    """Get analytics by app."""
    try:
        client = get_client()
        
        query = """
        SELECT
            CASE
                WHEN event_name LIKE '%lendsight%' THEN 'LendSight'
                WHEN event_name LIKE '%bizsight%' THEN 'BizSight'
                WHEN event_name LIKE '%branchsight%' THEN 'BranchSight'
                WHEN event_name LIKE '%mergermeter%' THEN 'MergerMeter'
                WHEN event_name LIKE '%lenderprofile%' THEN 'LenderProfile'
                WHEN event_name LIKE '%dataexplorer%' THEN 'DataExplorer'
                ELSE 'Other'
            END as app_name,
            COUNT(*) as report_count
        FROM `justdata-ncrc.firebase_analytics.all_events`
        WHERE DATE(event_timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
          AND event_name LIKE '%_report'
        GROUP BY app_name
        ORDER BY report_count DESC
        """
        
        result = client.query(query).result()
        
        lines = [":bar_chart: *Reports by App* (Last 30 days)\n"]
        
        for row in result:
            bar_length = min(int(row.report_count / 10), 20)
            bar = "█" * bar_length
            lines.append(f"• *{row.app_name}*: {row.report_count} {bar}")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Error getting app analytics: {e}")
        return f":x: Error getting app analytics: {str(e)}"


def get_user_analytics() -> str:
    """Get top users (anonymized)."""
    return """:busts_in_silhouette: *Top Users* (Last 30 days)

_User analytics available in the Analytics dashboard._
Visit: https://justdata.org/analytics/users
"""


def get_county_analytics() -> str:
    """Get most analyzed counties."""
    try:
        client = get_client()
        
        query = """
        SELECT
            county_name,
            COUNT(*) as analysis_count
        FROM `justdata-ncrc.cache.analysis_results`
        WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
          AND county_name IS NOT NULL
        GROUP BY county_name
        ORDER BY analysis_count DESC
        LIMIT 10
        """
        
        result = client.query(query).result()
        
        lines = [":round_pushpin: *Top Counties Analyzed* (Last 30 days)\n"]
        
        for i, row in enumerate(result, 1):
            lines.append(f"{i}. {row.county_name}: {row.analysis_count} analyses")
        
        if len(lines) == 1:
            lines.append("_No county data available._")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Error getting county analytics: {e}")
        return f":x: Error getting county analytics: {str(e)}"
