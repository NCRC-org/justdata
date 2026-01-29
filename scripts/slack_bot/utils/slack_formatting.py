"""
Slack message formatting utilities for JustData bot.
"""

from datetime import datetime


def format_table_status(client, table_name: str) -> str:
    """Format a table status line for Slack."""
    from utils.bigquery import get_table_info
    
    # Map short names to full table names
    table_mapping = {
        "sb_lenders": "justdata-ncrc.bizsight.sb_lenders",
        "sb_county_summary": "justdata-ncrc.bizsight.sb_county_summary",
        "lenders18": "justdata-ncrc.lendsight.lenders18",
        "de_hmda": "justdata-ncrc.shared.de_hmda",
        "sod": "justdata-ncrc.branchsight.sod",
        "cu_branches": "justdata-ncrc.lenderprofile.cu_branches",
    }
    
    full_name = table_mapping.get(table_name, f"justdata-ncrc.{table_name}")
    
    try:
        info = get_table_info(client, full_name)
        if info:
            status = ":white_check_mark:"
            return f"{status} `{table_name}`: {info['num_rows']:,} rows ({info['modified']})"
        else:
            return f":x: `{table_name}`: Table not found"
    except Exception as e:
        return f":warning: `{table_name}`: Error - {str(e)[:30]}"


def format_sync_result(result: dict) -> str:
    """Format a sync result for Slack notification."""
    if result.get('status') == 'success':
        return f"""✅ *Sync Complete*
• Table: `{result.get('dest_table')}`
• Rows: {result.get('row_count', 0):,}
• Duration: {result.get('duration_seconds', 0):.1f}s
"""
    else:
        return f"""❌ *Sync Failed*
• Table: `{result.get('dest_table')}`
• Error: {result.get('error', 'Unknown')[:200]}
"""


def format_alert(alert_type: str, message: str, status: str = 'info') -> dict:
    """Format an alert message for Slack."""
    emoji = {
        'info': ':information_source:',
        'success': ':white_check_mark:',
        'error': ':x:',
        'warning': ':warning:',
        'started': ':arrows_counterclockwise:'
    }.get(status, ':information_source:')
    
    color = {
        'info': '#36a64f',
        'success': '#36a64f',
        'error': '#ff0000',
        'warning': '#ffcc00',
        'started': '#439FE0'
    }.get(status, '#36a64f')
    
    return {
        'attachments': [{
            'color': color,
            'title': f"{emoji} [{alert_type.upper()}]",
            'text': message,
            'footer': 'JustData Sync Bot',
            'ts': int(datetime.now().timestamp())
        }]
    }


def format_daily_summary(stats: dict) -> str:
    """Format a daily summary message."""
    return f"""📊 *JustData Daily Status* - {datetime.now().strftime('%B %d, %Y')}

*SYNC STATUS*
{stats.get('sync_status', '✅ All tables in sync')}

*DATA FRESHNESS*
{stats.get('data_freshness', '• All tables current')}

*YESTERDAY'S USAGE*
• Total reports: {stats.get('total_reports', 0)}
• Top app: {stats.get('top_app', 'N/A')}
• Unique users: {stats.get('unique_users', 0)}
"""
