"""Analysis, progress, refresh, freshness, insights, download route handlers.

Route-handler implementations extracted from blueprint.py. Each
function uses Flask's request context the same way it did inline
in the blueprint; the blueprint now contains thin wrappers that call
into here.
"""
import json
import logging
import threading
import uuid
from pathlib import Path
from urllib.parse import unquote

from flask import jsonify, render_template, request, Response, session

from justdata.main.auth import (
    admin_required,
    get_user_type,
    login_required,
    require_access,
    staff_required,
)
from justdata.shared.utils.progress_tracker import (
    create_progress_tracker,
    get_analysis_result,
    get_progress,
    store_analysis_result,
)

# Import version
try:
    from justdata.apps.electwatch.version import __version__
except ImportError:
    __version__ = '0.9.0'

logger = logging.getLogger(__name__)


def api_freshness():
    """Data freshness API endpoint."""
    try:
        from justdata.apps.electwatch.services.data_store import get_freshness
        freshness = get_freshness()
        return jsonify(freshness)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def api_aggregate_trends():
    """
    Get aggregate trend data across all officials for dashboard charts.

    Returns quarterly aggregated totals for all trading and contribution activity,
    plus breakdowns by party and chamber.

    Response:
    {
        "success": true,
        "total_trades_by_quarter": [...],
        "total_contributions_by_quarter": [...],
        "by_party": {"R": [...], "D": [...]},
        "by_chamber": {"house": [...], "senate": [...]}
    }
    """
    try:
        from collections import defaultdict
        from justdata.apps.electwatch.services.data_store import get_officials

        officials = get_officials()

        # Aggregate across all officials
        total_trades = defaultdict(lambda: {'purchases': 0, 'sales': 0, 'count': 0})
        total_contribs = defaultdict(lambda: {'amount': 0, 'count': 0})

        # By party and chamber breakdowns
        by_party_trades = {
            'R': defaultdict(lambda: {'purchases': 0, 'sales': 0, 'count': 0}),
            'D': defaultdict(lambda: {'purchases': 0, 'sales': 0, 'count': 0})
        }
        by_chamber_trades = {
            'house': defaultdict(lambda: {'purchases': 0, 'sales': 0, 'count': 0}),
            'senate': defaultdict(lambda: {'purchases': 0, 'sales': 0, 'count': 0})
        }

        for official in officials:
            party = official.get('party', '').upper()
            if party not in ('R', 'D'):
                party = 'R' if 'REP' in party else 'D' if 'DEM' in party else None

            chamber = official.get('chamber', '').lower()

            # Aggregate trades by quarter
            for q in official.get('trades_by_quarter', []):
                quarter = q.get('quarter', '')
                total_trades[quarter]['purchases'] += q.get('purchases', 0)
                total_trades[quarter]['sales'] += q.get('sales', 0)
                total_trades[quarter]['count'] += q.get('count', 0)

                if party and party in by_party_trades:
                    by_party_trades[party][quarter]['purchases'] += q.get('purchases', 0)
                    by_party_trades[party][quarter]['sales'] += q.get('sales', 0)
                    by_party_trades[party][quarter]['count'] += q.get('count', 0)

                if chamber in by_chamber_trades:
                    by_chamber_trades[chamber][quarter]['purchases'] += q.get('purchases', 0)
                    by_chamber_trades[chamber][quarter]['sales'] += q.get('sales', 0)
                    by_chamber_trades[chamber][quarter]['count'] += q.get('count', 0)

            # Aggregate contributions by quarter
            for q in official.get('contributions_by_quarter', []):
                quarter = q.get('quarter', '')
                total_contribs[quarter]['amount'] += q.get('amount', 0)
                total_contribs[quarter]['count'] += q.get('count', 0)

        # Convert to sorted lists
        def to_sorted_list(data_dict):
            result = []
            for quarter, data in sorted(data_dict.items(), key=lambda x: (
                int(x[0].split()[1]) if x[0] and len(x[0].split()) > 1 else 0,
                int(x[0][1]) if x[0] and len(x[0]) > 1 else 0
            )):
                result.append({'quarter': quarter, **data})
            return result

        return jsonify({
            'success': True,
            'total_trades_by_quarter': to_sorted_list(total_trades),
            'total_contributions_by_quarter': to_sorted_list(total_contribs),
            'by_party': {
                'R': to_sorted_list(by_party_trades['R']),
                'D': to_sorted_list(by_party_trades['D'])
            },
            'by_chamber': {
                'house': to_sorted_list(by_chamber_trades['house']),
                'senate': to_sorted_list(by_chamber_trades['senate'])
            }
        })

    except Exception as e:
        logger.error(f"Error getting aggregate trends: {e}")
        import traceback
        return jsonify({'success': False, 'error': str(e), 'traceback': traceback.format_exc()}), 500

def api_insights():
    """Insights API endpoint."""
    try:
        from justdata.apps.electwatch.services.data_store import get_insights
        insights = get_insights()
        return jsonify({"success": True, "insights": insights})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def api_refresh_data():
    """
    Trigger a refresh of the ElectWatch data store (staff/admin only).

    This runs the weekly update process to fetch fresh data from all sources.
    The update runs in a background thread to avoid blocking the request.
    """
    user_type = get_user_type()
    if user_type not in ('staff', 'admin'):
        return jsonify({
            'success': False,
            'error': 'Only staff/admin users can refresh data'
        }), 403

    try:
        # Run the weekly update in a background thread
        def run_update():
            try:
                from justdata.apps.electwatch.weekly_update import main as weekly_update_main
                logger.info("Starting ElectWatch data refresh (triggered by admin)")
                weekly_update_main()
                logger.info("ElectWatch data refresh completed successfully")
            except Exception as e:
                logger.error(f"ElectWatch data refresh failed: {e}")

        thread = threading.Thread(target=run_update, daemon=True)
        thread.start()

        return jsonify({
            'success': True,
            'message': 'Data refresh started. This may take several minutes to complete.',
            'status': 'in_progress'
        })
    except Exception as e:
        logger.error(f"Error starting data refresh: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# Search, bills API, analysis jobs, export (parity with former standalone app)
# =============================================================================

def api_analyze():
    """
    Run analysis for an official.

    Request body:
        {
            "official_id": "hill_j_french",
            "include_ai_insights": true
        }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data received'}), 400

        official_id = data.get('official_id')
        if not official_id:
            return jsonify({'success': False, 'error': 'official_id required'}), 400

        include_ai = data.get('include_ai_insights', True)

        job_id = str(uuid.uuid4())
        progress_tracker = create_progress_tracker(job_id)

        session['official_id'] = official_id
        session['job_id'] = job_id

        def run_analysis():
            try:
                from justdata.apps.electwatch.core import run_official_analysis
                result = run_official_analysis(
                    official_id=official_id,
                    include_ai=include_ai,
                    job_id=job_id,
                    progress_tracker=progress_tracker
                )

                if not result.get('success'):
                    error_msg = result.get('error', 'Unknown error')
                    progress_tracker.complete(success=False, error=error_msg)
                    return

                store_analysis_result(job_id, result)
                progress_tracker.complete(success=True)

            except Exception as e:
                progress_tracker.complete(success=False, error=str(e))

        thread = threading.Thread(target=run_analysis, daemon=True)
        thread.start()

        return jsonify({'success': True, 'job_id': job_id})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def electwatch_progress_stream(job_id: str):
    """Progress tracking endpoint using Server-Sent Events."""
    def event_stream():
        import time
        last_percent = -1
        while True:
            progress = get_progress(job_id)
            percent = progress.get("percent", 0)
            step = progress.get("step", "Starting...")
            done = progress.get("done", False)
            error = progress.get("error", None)

            if percent != last_percent or done or error:
                yield f"data: {json.dumps({'percent': percent, 'step': step, 'done': done, 'error': error})}\n\n"
                last_percent = percent

            if done or error:
                break

            time.sleep(0.5)

    return Response(event_stream(), mimetype="text/event-stream")

def api_get_analysis_result(job_id: str):
    """Get analysis result for a job."""
    result = get_analysis_result(job_id)
    if not result:
        return jsonify({'success': False, 'error': 'Result not found'}), 404

    return jsonify({'success': True, 'result': result})

def electwatch_download():
    """Download generated reports (export not yet implemented)."""
    try:
        _ = request.args.get('format', 'excel').lower()
        job_id = request.args.get('job_id') or session.get('job_id')

        if not job_id:
            return jsonify({'error': 'No analysis session found'}), 400

        analysis_result = get_analysis_result(job_id)
        if not analysis_result:
            return jsonify({'error': 'No analysis data found'}), 400

        return jsonify({'error': 'Export not yet implemented'}), 501

    except Exception as e:
        return jsonify({'error': str(e)}), 500


def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'app': 'electwatch',
        'version': __version__
    })

