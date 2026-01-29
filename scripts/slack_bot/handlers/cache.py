"""
Cache command handlers for JustData Slack bot.
"""

import logging
from utils.bigquery import get_client

logger = logging.getLogger(__name__)


def handle_cache(args: str, user_id: str) -> str:
    """
    Handle cache commands.
    
    Usage:
        /jd cache status        - Show cache statistics
        /jd cache clear <type>  - Clear specific cache type
        /jd cache stats         - Detailed cache statistics
    """
    if not args:
        return get_cache_status()
    
    parts = args.split()
    subcommand = parts[0].lower()
    
    if subcommand == "status":
        return get_cache_status()
    
    if subcommand == "stats":
        return get_cache_stats()
    
    if subcommand == "clear":
        cache_type = parts[1] if len(parts) > 1 else None
        return clear_cache(cache_type, user_id)
    
    if subcommand == "help":
        return get_cache_help()
    
    return f"Unknown cache command: `{subcommand}`. Try `/jd cache help`"


def get_cache_help() -> str:
    """Return help text for cache commands."""
    return """*Cache Commands*

`/jd cache status` - Show cache statistics
`/jd cache stats` - Detailed cache breakdown
`/jd cache clear analysis` - Clear analysis cache (AI narratives)
`/jd cache clear results` - Clear cached report results
`/jd cache clear all` - Clear all caches (caution!)

*Cache Tables:*
• `cache.analysis_cache` - Cached AI analysis narratives
• `cache.analysis_results` - Cached report results
• `cache.usage_log` - API usage history
"""


def get_cache_status() -> str:
    """Get cache status summary."""
    try:
        client = get_client()
        
        # Query cache table sizes
        query = """
        SELECT
            table_id,
            row_count,
            ROUND(size_bytes / (1024 * 1024), 2) as size_mb
        FROM `justdata-ncrc.cache.__TABLES__`
        ORDER BY size_bytes DESC
        """
        
        result = client.query(query).result()
        
        lines = [":file_cabinet: *Cache Status*\n"]
        total_rows = 0
        total_mb = 0
        
        for row in result:
            lines.append(f"• `{row.table_id}`: {row.row_count:,} rows ({row.size_mb:.2f} MB)")
            total_rows += row.row_count
            total_mb += row.size_mb
        
        lines.append(f"\n*Total:* {total_rows:,} cached items ({total_mb:.2f} MB)")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Error getting cache status: {e}")
        return f":x: Error getting cache status: {str(e)}"


def get_cache_stats() -> str:
    """Get detailed cache statistics."""
    try:
        client = get_client()
        
        # Get cache hit rate and age distribution
        query = """
        SELECT
            'analysis_cache' as cache_type,
            COUNT(*) as total_entries,
            COUNT(CASE WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), created_at, HOUR) < 24 THEN 1 END) as last_24h,
            COUNT(CASE WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), created_at, DAY) < 7 THEN 1 END) as last_7d,
            MIN(created_at) as oldest_entry,
            MAX(created_at) as newest_entry
        FROM `justdata-ncrc.cache.analysis_cache`
        """
        
        result = list(client.query(query).result())
        
        if not result:
            return ":information_source: No cache data found"
        
        row = result[0]
        
        return f""":bar_chart: *Cache Statistics*

*Analysis Cache:*
• Total entries: {row.total_entries:,}
• Added in last 24h: {row.last_24h:,}
• Added in last 7d: {row.last_7d:,}
• Oldest entry: {row.oldest_entry}
• Newest entry: {row.newest_entry}

_Use `/jd cache clear analysis` to clear stale entries._
"""
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return f":x: Error getting cache stats: {str(e)}"


def clear_cache(cache_type: str, user_id: str) -> str:
    """Clear specified cache type."""
    if not cache_type:
        return ":warning: Please specify cache type: `analysis`, `results`, or `all`"
    
    cache_type = cache_type.lower()
    
    if cache_type not in ["analysis", "results", "all"]:
        return f":x: Unknown cache type: `{cache_type}`. Valid types: `analysis`, `results`, `all`"
    
    # Require confirmation for destructive operations
    return f""":warning: *Cache Clear Confirmation*

This will delete all entries from the `{cache_type}` cache.

To confirm, run: `/jd cache clear {cache_type} --confirm`

_This action cannot be undone._
"""
