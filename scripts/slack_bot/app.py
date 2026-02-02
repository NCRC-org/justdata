"""
JustData Slack Bot - Main Application

Handles slash commands for data operations, monitoring, and alerts.
Deployed as a Cloud Run service.
"""

import os
import logging
from flask import Flask, request, jsonify
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler

# Import handlers
from handlers.refresh import handle_refresh
from handlers.status import handle_status
from handlers.cache import handle_cache
from handlers.analytics import handle_analytics
from handlers.validate import handle_validate
from handlers.alerts_cmd import handle_alerts
from handlers.help import handle_help

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Slack Bolt app
slack_app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)

# Initialize Flask app
flask_app = Flask(__name__)
handler = SlackRequestHandler(slack_app)


# ============================================================================
# Slash Command: /jd
# ============================================================================

@slack_app.command("/jd")
def handle_jd_command(ack, respond, command):
    """Handle the /jd slash command with subcommands."""
    ack()  # Acknowledge immediately
    
    text = command.get("text", "").strip()
    user_id = command.get("user_id")
    
    # Parse subcommand
    parts = text.split(maxsplit=1)
    subcommand = parts[0].lower() if parts else "help"
    args = parts[1] if len(parts) > 1 else ""
    
    logger.info(f"User {user_id} executed: /jd {subcommand} {args}")
    
    # Commands that query BigQuery (slow) - show loading message
    slow_commands = ["status", "cache", "analytics", "usage", "validate", "refresh", "sync"]
    if subcommand in slow_commands:
        respond(f":hourglass_flowing_sand: _Querying data for `{subcommand}`..._")
    
    # Route to appropriate handler
    try:
        if subcommand in ["refresh", "sync"]:
            response = handle_refresh(args, user_id)
        elif subcommand == "status":
            response = handle_status(args, user_id)
        elif subcommand == "cache":
            response = handle_cache(args, user_id)
        elif subcommand in ["analytics", "usage"]:
            response = handle_analytics(args, user_id)
        elif subcommand == "validate":
            response = handle_validate(args, user_id)
        elif subcommand == "alerts":
            response = handle_alerts(args, user_id)
        elif subcommand in ["help", "?"]:
            response = handle_help(args, user_id)
        elif subcommand == "tables":
            response = get_tables_list()
        elif subcommand == "lineage":
            response = get_lineage(args)
        else:
            response = f"Unknown command: `{subcommand}`. Type `/jd help` for available commands."
    except Exception as e:
        logger.error(f"Error handling command: {e}")
        response = f":x: Error: {str(e)}"
    
    respond(response)


def get_tables_list():
    """List all tables and their sync status."""
    tables = [
        ("sb_lenders", "bizsight", "Full copy from hdma1-242116.sb.lenders"),
        ("sb_county_summary", "bizsight", "Aggregated from hdma1-242116.sb.disclosure"),
        ("lenders18", "lendsight", "Full copy from hmda.lenders18"),
        ("lender_names_gleif", "shared", "Full copy from hmda.lender_names_gleif"),
        ("de_hmda", "shared", "Derived from hmda.hmda + joins"),
        ("de_hmda_county_summary", "lendsight", "Aggregated from de_hmda"),
        ("de_hmda_tract_summary", "lendsight", "Aggregated from de_hmda"),
        ("sod", "branchsight", "Full copy from branches.sod"),
        ("branch_hhi_summary", "branchsight", "Aggregated from sod"),
        ("cu_branches", "lenderprofile", "Full copy from credit_unions.cu_branches"),
        ("cu_call_reports", "lenderprofile", "Full copy from credit_unions.cu_call_reports"),
        ("cbsa_to_county", "shared", "Static geographic mapping"),
        ("census", "shared", "Annual census tract data"),
        ("county_centroids", "shared", "County centroid coordinates"),
        ("cbsa_centroids", "shared", "CBSA centroid coordinates"),
    ]
    
    lines = [":card_file_box: *JustData Tables*\n"]
    for table, dataset, description in tables:
        lines.append(f"• `{dataset}.{table}` - {description}")
    
    return "\n".join(lines)


def get_lineage(table_name: str):
    """Show data lineage for a table."""
    lineage = {
        "de_hmda": {
            "sources": ["justdata-ncrc.hmda.hmda", "justdata-ncrc.hmda.lenders18", "justdata-ncrc.shared.census", "justdata-ncrc.shared.cbsa_to_county"],
            "dependents": ["lendsight.de_hmda_county_summary", "lendsight.de_hmda_tract_summary"],
            "refresh": "Manual or triggered by hmda.hmda changes"
        },
        "sb_county_summary": {
            "sources": ["hdma1-242116.sb.disclosure", "hdma1-242116.sb.lenders"],
            "dependents": [],
            "refresh": "Triggered by hdma1-242116.sb.disclosure changes"
        },
        "branch_hhi_summary": {
            "sources": ["justdata-ncrc.branchsight.sod"],
            "dependents": [],
            "refresh": "Cascaded from sod refresh"
        },
    }
    
    # Normalize table name
    table_key = table_name.replace("shared.", "").replace("lendsight.", "").replace("bizsight.", "").replace("branchsight.", "")
    
    if table_key not in lineage:
        return f"No lineage information for `{table_name}`. Use `/jd tables` to see all tables."
    
    info = lineage[table_key]
    lines = [f":link: *Data Lineage: {table_name}*\n"]
    lines.append(f"*Sources:*")
    for src in info["sources"]:
        lines.append(f"  • `{src}`")
    lines.append(f"\n*Dependents:*")
    for dep in info["dependents"]:
        lines.append(f"  • `{dep}`")
    lines.append(f"\n*Refresh:* {info['refresh']}")
    
    return "\n".join(lines)


# ============================================================================
# Flask Routes
# ============================================================================

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    """Handle Slack events including URL verification."""
    # Handle URL verification challenge (required for initial setup)
    data = request.get_json(silent=True)
    if data and data.get("type") == "url_verification":
        logger.info("Handling URL verification challenge")
        return jsonify({"challenge": data.get("challenge")}), 200
    
    # All other events go through Slack Bolt handler
    return handler.handle(request)


@flask_app.route("/slack/commands", methods=["POST"])
def slack_commands():
    """Handle Slack slash commands."""
    return handler.handle(request)


@flask_app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "justdata-slack-bot"})


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port, debug=True)
