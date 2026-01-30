"""
Validate command handlers for JustData Slack bot.
"""

import logging
from utils.bigquery import get_client

logger = logging.getLogger(__name__)


def handle_validate(args: str, user_id: str) -> str:
    """
    Handle validate commands.
    
    Usage:
        /jd validate counts      - Compare row counts between projects
        /jd validate <table>     - Validate specific table
        /jd validate nulls       - Check for null values in key columns
    """
    if not args:
        return validate_row_counts()
    
    parts = args.split()
    subcommand = parts[0].lower()
    
    if subcommand == "counts":
        return validate_row_counts()
    
    if subcommand == "nulls":
        return validate_nulls()
    
    if subcommand == "help":
        return get_validate_help()
    
    # Assume it's a table name
    return validate_table(subcommand)


def get_validate_help() -> str:
    """Return help text for validate commands."""
    return """*Validate Commands*

`/jd validate counts` - Compare row counts hdma1 vs justdata-ncrc
`/jd validate <table>` - Validate specific table data
`/jd validate nulls` - Check for null values in key columns

*Examples:*
`/jd validate sb_lenders`
`/jd validate counts`
"""


def validate_row_counts() -> str:
    """Compare row counts between source and destination."""
    try:
        client = get_client()
        
        # Tables to compare (source -> destination)
        comparisons = [
            ("hdma1-242116.sb.lenders", "justdata-ncrc.bizsight.sb_lenders"),
            ("hdma1-242116.hmda.lenders18", "justdata-ncrc.lendsight.lenders18"),
            ("hdma1-242116.hmda.lender_names_gleif", "justdata-ncrc.shared.lender_names_gleif"),
            ("hdma1-242116.credit_unions.cu_branches", "justdata-ncrc.lenderprofile.cu_branches"),
        ]
        
        lines = [":mag: *Row Count Validation*\n"]
        all_match = True
        
        for source, dest in comparisons:
            try:
                source_count = get_row_count(client, source)
                dest_count = get_row_count(client, dest)
                
                if source_count == dest_count:
                    status = ":white_check_mark:"
                elif abs(source_count - dest_count) / max(source_count, 1) < 0.01:
                    status = ":warning:"  # Within 1%
                else:
                    status = ":x:"
                    all_match = False
                
                table_name = dest.split(".")[-1]
                lines.append(f"{status} `{table_name}`: {dest_count:,} (source: {source_count:,})")
                
            except Exception as e:
                lines.append(f":warning: Error comparing {source}: {str(e)[:50]}")
                all_match = False
        
        lines.append("")
        if all_match:
            lines.append(":white_check_mark: *All tables in sync*")
        else:
            lines.append(":x: *Some tables out of sync - run `/jd refresh <table>`*")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Error validating counts: {e}")
        return f":x: Error validating counts: {str(e)}"


def get_row_count(client, table: str) -> int:
    """Get row count for a table."""
    query = f"SELECT COUNT(*) as cnt FROM `{table}`"
    result = list(client.query(query).result())
    return result[0].cnt if result else 0


def validate_table(table_name: str) -> str:
    """Validate a specific table."""
    try:
        client = get_client()
        
        # Map table names
        table_mapping = {
            "sb_lenders": ("hdma1-242116.sb.lenders", "justdata-ncrc.bizsight.sb_lenders"),
            "lenders18": ("hdma1-242116.hmda.lenders18", "justdata-ncrc.lendsight.lenders18"),
            "de_hmda": ("hdma1-242116.justdata.de_hmda", "justdata-ncrc.shared.de_hmda"),
        }
        
        if table_name not in table_mapping:
            return f":x: Unknown table for validation: `{table_name}`"
        
        source, dest = table_mapping[table_name]
        source_count = get_row_count(client, source)
        dest_count = get_row_count(client, dest)
        
        diff = dest_count - source_count
        pct_diff = (diff / max(source_count, 1)) * 100
        
        status = ":white_check_mark:" if diff == 0 else (":warning:" if abs(pct_diff) < 1 else ":x:")
        
        return f""":mag: *Validation: {table_name}*

*Source:* `{source}`
*Rows:* {source_count:,}

*Destination:* `{dest}`
*Rows:* {dest_count:,}

*Difference:* {diff:+,} ({pct_diff:+.2f}%)
*Status:* {status}
"""
        
    except Exception as e:
        logger.error(f"Error validating table: {e}")
        return f":x: Error validating `{table_name}`: {str(e)}"


def validate_nulls() -> str:
    """Check for null values in key columns."""
    try:
        client = get_client()
        
        checks = [
            ("justdata-ncrc.shared.de_hmda", "lei", "LEI in de_hmda"),
            ("justdata-ncrc.shared.de_hmda", "county_code", "County code in de_hmda"),
            ("justdata-ncrc.bizsight.sb_lenders", "sb_resid", "Respondent ID in sb_lenders"),
        ]
        
        lines = [":mag: *Null Value Check*\n"]
        
        for table, column, description in checks:
            query = f"""
            SELECT 
                COUNT(*) as total,
                COUNTIF({column} IS NULL) as nulls
            FROM `{table}`
            """
            result = list(client.query(query).result())[0]
            pct_null = (result.nulls / max(result.total, 1)) * 100
            
            if pct_null == 0:
                status = ":white_check_mark:"
            elif pct_null < 1:
                status = ":warning:"
            else:
                status = ":x:"
            
            lines.append(f"{status} {description}: {result.nulls:,} nulls ({pct_null:.2f}%)")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Error checking nulls: {e}")
        return f":x: Error checking nulls: {str(e)}"
