"""
DataExplorer Blueprint for main JustData app.
Converts the standalone DataExplorer app into a blueprint.
"""

from flask import Blueprint, render_template, request, jsonify, send_from_directory, Response
import os
import json
import logging
from pathlib import Path

from justdata.main.auth import require_access, get_user_permissions, get_user_type
from justdata.shared.utils.unified_env import ensure_unified_env_loaded, get_unified_config
from .config import TEMPLATES_DIR, STATIC_DIR
from .version import __version__
from .data_utils import validate_years, validate_geoids, lookup_lender
from .cache_utils import clear_cache
from .area_analysis_processor import (
    process_hmda_area_analysis, process_sb_area_analysis, process_branch_area_analysis
)
from .lender_analysis_processor import process_lender_analysis

# Get repo root for shared static files
REPO_ROOT = Path(__file__).parent.parent.parent.absolute()

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
dataexplorer_bp = Blueprint(
    'dataexplorer',
    __name__,
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(STATIC_DIR),
    static_url_path='/dataexplorer/static'
)


@dataexplorer_bp.route('/')
@require_access('dataexplorer', 'full')
def index():
    """Main DataExplorer page - renders wizard."""
    return render_template('wizard.html', version=__version__)


@dataexplorer_bp.route('/dashboard')
@require_access('dataexplorer', 'full')
def dashboard():
    """Dashboard page."""
    return render_template('dashboard.html', version=__version__)


@dataexplorer_bp.route('/wizard')
@require_access('dataexplorer', 'full')
def wizard():
    """Wizard page for guided analysis."""
    return render_template('wizard.html', version=__version__)


@dataexplorer_bp.route('/api/states', methods=['GET'])
@require_access('dataexplorer', 'full')
def api_states():
    """Get list of states."""
    from .data_utils import get_states
    try:
        states = get_states()
        return jsonify({'success': True, 'states': states})
    except Exception as e:
        logger.error(f"Error getting states: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dataexplorer_bp.route('/api/metros', methods=['GET'])
@require_access('dataexplorer', 'full')
def api_metros():
    """Get list of metro areas."""
    from .data_utils import get_metros
    try:
        metros = get_metros()
        return jsonify({'success': True, 'metros': metros})
    except Exception as e:
        logger.error(f"Error getting metros: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dataexplorer_bp.route('/api/get-counties', methods=['POST'])
@require_access('dataexplorer', 'full')
def api_get_counties():
    """Get counties for a state or metro."""
    from .data_utils import get_counties_for_state, get_counties_for_metro
    try:
        data = request.get_json()
        selection_type = data.get('type', 'state')
        
        if selection_type == 'state':
            state_fips = data.get('state_fips')
            counties = get_counties_for_state(state_fips)
        else:
            cbsa_code = data.get('cbsa_code')
            counties = get_counties_for_metro(cbsa_code)
            
        return jsonify({'success': True, 'counties': counties})
    except Exception as e:
        logger.error(f"Error getting counties: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dataexplorer_bp.route('/api/area/hmda/analysis', methods=['POST'])
@require_access('dataexplorer', 'full')
def api_hmda_analysis():
    """Run HMDA area analysis."""
    try:
        data = request.get_json()
        result = process_hmda_area_analysis(data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in HMDA analysis: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dataexplorer_bp.route('/api/area/sb/analysis', methods=['POST'])
@require_access('dataexplorer', 'full')
def api_sb_analysis():
    """Run Small Business area analysis."""
    try:
        data = request.get_json()
        result = process_sb_area_analysis(data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in SB analysis: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dataexplorer_bp.route('/api/area/branches/analysis', methods=['POST'])
@require_access('dataexplorer', 'full')
def api_branch_analysis():
    """Run Branch area analysis."""
    try:
        data = request.get_json()
        result = process_branch_area_analysis(data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in Branch analysis: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dataexplorer_bp.route('/api/lender/analysis', methods=['POST'])
@require_access('dataexplorer', 'full')
def api_lender_analysis():
    """Run lender analysis."""
    try:
        data = request.get_json()
        result = process_lender_analysis(data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in lender analysis: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dataexplorer_bp.route('/api/lender/lookup', methods=['POST'])
@require_access('dataexplorer', 'full')
def api_lender_lookup():
    """Lookup lender by name or LEI."""
    try:
        data = request.get_json()
        search_term = data.get('search_term', '')
        results = lookup_lender(search_term)
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        logger.error(f"Error in lender lookup: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dataexplorer_bp.route('/api/clear-cache', methods=['POST'])
@require_access('dataexplorer', 'full')
def api_clear_cache():
    """Clear analysis cache."""
    try:
        clear_cache()
        return jsonify({'success': True, 'message': 'Cache cleared'})
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# Health check is handled by main app
