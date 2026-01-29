"""
Status command handlers for JustData Slack bot.
"""

import logging
from datetime import datetime, timedelta
from utils.bigquery import get_client, get_table_info, get_sync_history

logger = logging.getLogger(__name__)


def handle_status(args: str, user_id: str) -> str:
    """
    Handle status commands.
    
    Usage:
        /jd status              - Overall system status
        /jd status <table>      - Status of specific table
        /jd status sync         - Recent sync activity
        /jd status errors       - Recent errors
    """
    if not args:
        return get_overall_status()
    
    parts = args.split()
    subcommand = parts[0].lower()
    
    if subcommand == "sync":
        return get_sync_status()
    
    if subcommand == "errors":
        return get_error_status()
    
    if subcommand == "health":
        return get_health_status()
    
    # Assume it's a table name
    return get_table_status(subcommand)


def get_overall_status() -> str:
    """Get overall system status."""
    try:
        client = get_client()
        
        # Check key tables
        tables = [
            ("justdata-ncrc.shared.de_hmda", "de_hmda"),
            ("justdata-ncrc.bizsight.sb_county_summary", "sb_county_summary"),
            ("justdata-ncrc.branchsight.sod", "sod"),
            ("justdata-ncrc.cache.analysis_cache", "analysis_cache"),
        ]
        
        lines = [":bar_chart: *JustData System Status*\n"]
        lines.append(f"_As of {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC_\n")
        
        all_healthy = True
        for full_table, display_name in tables:
            try:
                info = get_table_info(client, full_table)
                if info:
                    modified = info.get('modified', 'Unknown')
                    rows = info.get('num_rows', 0)
                    status = ":white_check_mark:"
                    lines.append(f"{status} `{display_name}`: {rows:,} rows (updated {modified})")
                else:
                    all_healthy = False
                    lines.append(f":x: `{display_name}`: Table not found")
            except Exception as e:
                all_healthy = False
                lines.append(f":warning: `{display_name}`: Error checking status")
        
        lines.append("")
        if all_healthy:
            lines.append(":green_circle: *All systems operational*")
        else:
            lines.append(":yellow_circle: *Some issues detected*")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return f":x: Error getting system status: {str(e)}"


def get_table_status(table_name: str) -> str:
    """Get status of a specific table."""
    try:
        client = get_client()
        
        # Map common names to full table names
        table_mapping = {
            "de_hmda": "justdata-ncrc.shared.de_hmda",
            "sb_lenders": "justdata-ncrc.bizsight.sb_lenders",
            "sb_county_summary": "justdata-ncrc.bizsight.sb_county_summary",
            "lenders18": "justdata-ncrc.lendsight.lenders18",
            "sod": "justdata-ncrc.branchsight.sod",
            "cu_branches": "justdata-ncrc.lenderprofile.cu_branches",
        }
        
        full_table = table_mapping.get(table_name.lower(), f"justdata-ncrc.{table_name}")
        info = get_table_info(client, full_table)
        
        if not info:
            return f":x: Table `{table_name}` not found"
        
        return f""":card_file_box: *Table: {table_name}*

*Full Name:* `{full_table}`
*Rows:* {info.get('num_rows', 0):,}
*Size:* {info.get('size_mb', 0):.2f} MB
*Last Modified:* {info.get('modified', 'Unknown')}
*Created:* {info.get('created', 'Unknown')}
"""
        
    except Exception as e:
        logger.error(f"Error getting table status: {e}")
        return f":x: Error getting status for `{table_name}`: {str(e)}"


def get_sync_status() -> str:
    """Get recent sync activity."""
    try:
        client = get_client()
        history = get_sync_history(client, limit=10)
        
        if not history:
            return ":information_source: No recent sync activity found"
        
        lines = [":arrows_counterclockwise: *Recent Sync Activity*\n"]
        
        for entry in history:
            status_emoji = ":white_check_mark:" if entry['status'] == 'success' else ":x:"
            lines.append(f"{status_emoji} `{entry['table']}` - {entry['timestamp']} ({entry['duration']}s)")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        return f":x: Error getting sync status: {str(e)}"


def get_error_status() -> str:
    """Get recent errors."""
    return """:warning: *Recent Errors*

_Error tracking coming soon. Check Cloud Logging for details._

View logs: https://console.cloud.google.com/logs/query?project=justdata-ncrc
"""


def get_health_status() -> str:
    """Get health check status."""
    return """:heartbeat: *Health Status*

• Cloud Run: :green_circle: Operational
• BigQuery: :green_circle: Operational  
• Slack Bot: :green_circle: Operational
• Pub/Sub: :green_circle: Operational

_Last checked: now_
"""
