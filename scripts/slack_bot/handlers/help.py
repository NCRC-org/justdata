"""
Help command handlers for JustData Slack bot.
"""


def handle_help(args: str, user_id: str) -> str:
    """
    Handle help commands.
    
    Usage:
        /jd help            - Show all commands
        /jd help <command>  - Show help for specific command
    """
    if not args:
        return get_main_help()
    
    command = args.split()[0].lower()
    
    help_map = {
        "refresh": get_refresh_help,
        "sync": get_refresh_help,
        "status": get_status_help,
        "cache": get_cache_help,
        "analytics": get_analytics_help,
        "usage": get_analytics_help,
        "validate": get_validate_help,
        "alerts": get_alerts_help,
        "tables": get_tables_help,
        "lineage": get_lineage_help,
    }
    
    if command in help_map:
        return help_map[command]()
    
    return f"No help available for `{command}`. Try `/jd help`"


def get_main_help() -> str:
    """Get main help text."""
    return """:robot_face: *JustData Slack Bot*

*Data Refresh:*
`/jd refresh <table>` - Refresh a table from source
`/jd refresh status` - Show sync status of all tables

*Monitoring:*
`/jd status` - Overall system status
`/jd status <table>` - Status of specific table

*Cache Management:*
`/jd cache status` - Cache statistics
`/jd cache clear <type>` - Clear specific cache

*Analytics:*
`/jd analytics today` - Today's usage
`/jd analytics week` - Weekly summary
`/jd analytics apps` - Usage by app

*Data Quality:*
`/jd validate counts` - Compare row counts
`/jd validate nulls` - Check null values

*Alerts:*
`/jd alerts` - Alert status
`/jd alerts mute 2h` - Mute temporarily

*Reference:*
`/jd tables` - List all tables
`/jd lineage <table>` - Show data lineage
`/jd help <command>` - Detailed help

:link: *Dashboard:* https://justdata.org/analytics
"""


def get_refresh_help() -> str:
    return """*Refresh Commands*

`/jd refresh <table>` - Refresh a specific table
`/jd refresh all` - Refresh all tables
`/jd refresh status` - Show refresh status

*Tables:* sb_lenders, sb_county_summary, lenders18, lender_names_gleif, de_hmda, sod, cu_branches, cu_call_reports
"""


def get_status_help() -> str:
    return """*Status Commands*

`/jd status` - Overall system status
`/jd status <table>` - Specific table status
`/jd status sync` - Recent sync activity
`/jd status errors` - Recent errors
`/jd status health` - Service health check
"""


def get_cache_help() -> str:
    return """*Cache Commands*

`/jd cache status` - Cache statistics
`/jd cache stats` - Detailed breakdown
`/jd cache clear analysis` - Clear AI cache
`/jd cache clear results` - Clear report cache
"""


def get_analytics_help() -> str:
    return """*Analytics Commands*

`/jd analytics today` - Today's stats
`/jd analytics week` - Weekly stats
`/jd analytics apps` - By app breakdown
`/jd analytics users` - Top users
`/jd analytics counties` - Top counties
"""


def get_validate_help() -> str:
    return """*Validate Commands*

`/jd validate counts` - Compare row counts
`/jd validate <table>` - Validate specific table
`/jd validate nulls` - Check null values
"""


def get_alerts_help() -> str:
    return """*Alerts Commands*

`/jd alerts` - Alert status
`/jd alerts history` - Recent alerts
`/jd alerts mute 2h` - Mute temporarily
`/jd alerts test` - Send test alert
`/jd alerts config` - View configuration
"""


def get_tables_help() -> str:
    return """*Tables Command*

`/jd tables` - List all JustData tables with descriptions

Shows all tables in justdata-ncrc project organized by dataset.
"""


def get_lineage_help() -> str:
    return """*Lineage Command*

`/jd lineage <table>` - Show data lineage

Shows the sources and dependents for a table.

*Example:*
`/jd lineage de_hmda`
"""
