"""
Refresh command handlers for JustData Slack bot.
"""

import logging
from google.cloud import bigquery
from utils.bigquery import get_client, refresh_table
from utils.slack_formatting import format_table_status

logger = logging.getLogger(__name__)

# Valid tables for refresh
REFRESHABLE_TABLES = {
    "sb_lenders": "sb.lenders",
    "sb_county_summary": "sb.disclosure",
    "lenders18": "hmda.lenders18",
    "lender_names_gleif": "hmda.lender_names_gleif",
    "de_hmda": "hmda.hmda",
    "sod": "branches.sod",
    "cu_branches": "credit_unions.cu_branches",
    "cu_call_reports": "credit_unions.cu_call_reports",
}


def handle_refresh(args: str, user_id: str) -> str:
    """
    Handle refresh commands.
    
    Usage:
        /jd refresh <table>       - Refresh a specific table
        /jd refresh all           - Refresh all tables
        /jd refresh status        - Show refresh status
    """
    if not args:
        return get_refresh_help()
    
    parts = args.split()
    subcommand = parts[0].lower()
    
    if subcommand == "help":
        return get_refresh_help()
    
    if subcommand == "status":
        return get_refresh_status()
    
    if subcommand == "all":
        return start_full_refresh(user_id)
    
    # Refresh specific table
    table_name = subcommand.replace("-", "_")
    
    if table_name not in REFRESHABLE_TABLES:
        valid_tables = ", ".join(f"`{t}`" for t in REFRESHABLE_TABLES.keys())
        return f":x: Unknown table: `{table_name}`\n\nValid tables: {valid_tables}"
    
    return start_table_refresh(table_name, user_id)


def get_refresh_help() -> str:
    """Return help text for refresh commands."""
    return """*Refresh Commands*

`/jd refresh <table>` - Refresh a specific table
`/jd refresh all` - Refresh all tables (caution: expensive)
`/jd refresh status` - Show current refresh status

*Available Tables:*
• `sb_lenders` - Small business lenders
• `sb_county_summary` - SB lending by county (aggregated)
• `lenders18` - HMDA lenders
• `lender_names_gleif` - GLEIF-verified lender names
• `de_hmda` - Derived HMDA data (~130M rows, slow)
• `sod` - Bank branch data
• `cu_branches` - Credit union branches
• `cu_call_reports` - Credit union call reports

*Example:*
`/jd refresh sb_lenders`
"""


def get_refresh_status() -> str:
    """Get current refresh status of all tables."""
    try:
        client = get_client()
        
        lines = [":arrows_counterclockwise: *Refresh Status*\n"]
        
        for table_name, source in REFRESHABLE_TABLES.items():
            status = format_table_status(client, table_name)
            lines.append(f"• {status}")
        
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error getting refresh status: {e}")
        return f":x: Error getting refresh status: {str(e)}"


def start_table_refresh(table_name: str, user_id: str) -> str:
    """Start refreshing a specific table."""
    source_table = REFRESHABLE_TABLES[table_name]
    
    # For large tables, warn the user
    if table_name == "de_hmda":
        return f""":warning: *Large Table Warning*

`de_hmda` contains ~130M rows and takes several minutes to refresh.

Are you sure? Run `/jd refresh de_hmda --confirm` to proceed.

Consider using `/jd refresh de_hmda --incremental` for incremental updates only."""
    
    try:
        client = get_client()
        result = refresh_table(client, source_table)
        
        if result.get("status") == "success":
            return f""":white_check_mark: *Refresh Complete*

Table: `{table_name}`
Rows: {result.get('row_count', 'N/A'):,}
Duration: {result.get('duration_seconds', 0):.1f}s
"""
        else:
            return f":x: Refresh failed: {result.get('error', 'Unknown error')}"
            
    except Exception as e:
        logger.error(f"Error refreshing {table_name}: {e}")
        return f":x: Error refreshing `{table_name}`: {str(e)}"


def start_full_refresh(user_id: str) -> str:
    """Start refreshing all tables."""
    return """:warning: *Full Refresh*

This will refresh all tables and may take 10-15 minutes.
Estimated cost: ~$5-10 in BigQuery processing.

To proceed, run: `/jd refresh all --confirm`

For targeted refresh, specify a table: `/jd refresh sb_lenders`
"""
