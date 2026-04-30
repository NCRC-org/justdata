"""
ElectWatch Blueprint for main JustData app.
Self-contained blueprint that works within the unified platform.
"""

from flask import Blueprint, render_template, jsonify, request, session, Response
from pathlib import Path
from urllib.parse import unquote
import json
import logging
import threading
import uuid

from justdata.main.auth import get_user_type, login_required, require_access, admin_required, staff_required
from justdata.shared.utils.progress_tracker import (
    create_progress_tracker,
    get_progress,
    store_analysis_result,
    get_analysis_result,
)

from justdata.apps.electwatch.services import (
    admin,
    analysis,
    bills,
    committees,
    firms,
    industries,
    officials,
    search,
)

logger = logging.getLogger(__name__)

# Get directories
APP_DIR = Path(__file__).parent.absolute()
TEMPLATES_DIR = APP_DIR / 'templates'
STATIC_DIR = APP_DIR / 'static'

# Create blueprint
electwatch_bp = Blueprint(
    'electwatch',
    __name__,
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(STATIC_DIR),
    static_url_path='/electwatch/static'
)

# Import version
try:
    from justdata.apps.electwatch.version import __version__
except ImportError:
    __version__ = '0.9.0'


@electwatch_bp.route('/')
@login_required
def index():
    return industries.index()


@electwatch_bp.route('/official/<official_id>')
@login_required
@require_access('electwatch', 'full')
def official_profile(official_id):
    return officials.official_profile(official_id)


@electwatch_bp.route('/firm/<firm_id>')
@login_required
@require_access('electwatch', 'full')
def firm_view(firm_id):
    return firms.firm_view(firm_id)


@electwatch_bp.route('/industry/<industry_code>')
@login_required
@require_access('electwatch', 'full')
def industry_view(industry_code):
    return industries.industry_view(industry_code)


@electwatch_bp.route('/committee/<committee_id>')
@login_required
@require_access('electwatch', 'full')
def committee_view(committee_id):
    return committees.committee_view(committee_id)


@electwatch_bp.route('/bill/<bill_id>')
@login_required
@require_access('electwatch', 'full')
def bill_view(bill_id):
    return bills.bill_view(bill_id)


@electwatch_bp.route('/api/officials')
@login_required
@require_access('electwatch', 'full')
def api_officials():
    return officials.api_officials()


@electwatch_bp.route('/api/official/<official_id>')
@login_required
@require_access('electwatch', 'full')
def api_official(official_id):
    return officials.api_official(official_id)


@electwatch_bp.route('/api/official/<official_id>/trends')
@login_required
@require_access('electwatch', 'full')
def api_official_trends(official_id):
    return officials.api_official_trends(official_id)


@electwatch_bp.route('/api/firm/<firm_name>')
@login_required
@require_access('electwatch', 'full')
def api_firm(firm_name):
    return firms.api_firm(firm_name)


@electwatch_bp.route('/api/firms')
@login_required
@require_access('electwatch', 'full')
def api_firms():
    return firms.api_firms()


@electwatch_bp.route('/api/sectors')
@login_required
@require_access('electwatch', 'full')
def api_sectors():
    return industries.api_sectors()


@electwatch_bp.route('/api/industry/<industry_code>')
@login_required
@require_access('electwatch', 'full')
def api_industry(industry_code):
    return industries.api_industry(industry_code)


@electwatch_bp.route('/api/committees')
@login_required
@require_access('electwatch', 'full')
def api_committees():
    return committees.api_committees()


@electwatch_bp.route('/api/committee/<committee_id>')
@login_required
@require_access('electwatch', 'full')
def api_committee(committee_id):
    return committees.api_committee(committee_id)


@electwatch_bp.route('/api/freshness')
@login_required
@require_access('electwatch', 'full')
def api_freshness():
    return analysis.api_freshness()


@electwatch_bp.route('/api/trends/aggregate')
@login_required
@require_access('electwatch', 'full')
def api_aggregate_trends():
    return analysis.api_aggregate_trends()


@electwatch_bp.route('/api/insights')
@login_required
@require_access('electwatch', 'full')
def api_insights():
    return analysis.api_insights()


@electwatch_bp.route('/api/refresh-data', methods=['POST'])
@login_required
@staff_required
def api_refresh_data():
    return analysis.api_refresh_data()


@electwatch_bp.route('/api/search', methods=['GET'])
@login_required
@require_access('electwatch', 'full')
def api_search():
    return search.api_search()


@electwatch_bp.route('/api/bills/search', methods=['GET'])
@login_required
@require_access('electwatch', 'full')
def api_search_bills():
    return search.api_search_bills()


@electwatch_bp.route('/api/bills/<bill_id>', methods=['GET'])
@login_required
@require_access('electwatch', 'full')
def api_get_bill(bill_id: str):
    return search.api_get_bill(bill_id)


@electwatch_bp.route('/api/analyze', methods=['POST'])
@login_required
@require_access('electwatch', 'full')
def api_analyze():
    return analysis.api_analyze()


@electwatch_bp.route('/progress/<job_id>')
@login_required
@require_access('electwatch', 'full')
def electwatch_progress_stream(job_id: str):
    return analysis.electwatch_progress_stream(job_id)


@electwatch_bp.route('/api/result/<job_id>')
@login_required
@require_access('electwatch', 'full')
def api_get_analysis_result(job_id: str):
    return analysis.api_get_analysis_result(job_id)


@electwatch_bp.route('/download')
@login_required
@require_access('electwatch', 'full')
def electwatch_download():
    return analysis.electwatch_download()


@electwatch_bp.route('/health')
def health():
    return analysis.health()


# =============================================================================
# BILL SEARCH AND KEY BILLS API
# =============================================================================


@electwatch_bp.route('/api/bill/search')
@login_required
@require_access('electwatch', 'full')
def api_bill_search():
    return search.api_bill_search()


@electwatch_bp.route('/api/key-bills')
@login_required
@require_access('electwatch', 'full')
def api_key_bills():
    return bills.api_key_bills()


@electwatch_bp.route('/api/bill/save-key-bill', methods=['POST'])
@login_required
@staff_required
def api_save_key_bill():
    return bills.api_save_key_bill()


@electwatch_bp.route('/api/bill/remove-key-bill', methods=['POST'])
@login_required
@staff_required
def api_remove_key_bill():
    return bills.api_remove_key_bill()


@electwatch_bp.route('/api/admin/mappings/officials')
@login_required
@admin_required
def api_admin_get_official_merges():
    return admin.api_admin_get_official_merges()


@electwatch_bp.route('/api/admin/mappings/officials/merge', methods=['POST'])
@login_required
@admin_required
def api_admin_merge_official():
    return admin.api_admin_merge_official()


@electwatch_bp.route('/api/admin/mappings/officials/unmerge', methods=['POST'])
@login_required
@admin_required
def api_admin_unmerge_official():
    return admin.api_admin_unmerge_official()


@electwatch_bp.route('/api/admin/mappings/officials/delete', methods=['POST'])
@login_required
@admin_required
def api_admin_delete_official_merge():
    return admin.api_admin_delete_official_merge()


@electwatch_bp.route('/api/admin/mappings/officials/potential-duplicates')
@login_required
@staff_required
def api_admin_potential_duplicate_officials():
    return admin.api_admin_potential_duplicate_officials()


@electwatch_bp.route('/api/admin/mappings/officials/mark-distinct', methods=['POST'])
@login_required
@staff_required
def api_admin_mark_officials_distinct():
    return admin.api_admin_mark_officials_distinct()


@electwatch_bp.route('/api/admin/mappings/firms')
@login_required
@admin_required
def api_admin_get_firms():
    return admin.api_admin_get_firms()


@electwatch_bp.route('/api/admin/mappings/firms/all')
@login_required
@admin_required
def api_admin_get_all_firms():
    return admin.api_admin_get_all_firms()


@electwatch_bp.route('/api/admin/mappings/firms', methods=['POST'])
@login_required
@admin_required
def api_admin_add_firm():
    return admin.api_admin_add_firm()


@electwatch_bp.route('/api/admin/mappings/firms/delete', methods=['POST'])
@login_required
@admin_required
def api_admin_delete_firm():
    return admin.api_admin_delete_firm()


@electwatch_bp.route('/api/admin/mappings/firms/<firm_id>/aliases')
@login_required
@admin_required
def api_admin_get_firm_aliases(firm_id):
    return admin.api_admin_get_firm_aliases(firm_id)


@electwatch_bp.route('/api/admin/mappings/employers', methods=['POST'])
@login_required
@admin_required
def api_admin_add_employer_alias():
    return admin.api_admin_add_employer_alias()


@electwatch_bp.route('/api/admin/mappings/employers/delete', methods=['POST'])
@login_required
@admin_required
def api_admin_remove_employer_alias():
    return admin.api_admin_remove_employer_alias()


@electwatch_bp.route('/api/admin/employers/unmatched')
@login_required
@admin_required
def api_admin_get_unmatched_employers():
    return admin.api_admin_get_unmatched_employers()


@electwatch_bp.route('/api/admin/employers/search')
@login_required
@admin_required
def api_admin_search_employers():
    return admin.api_admin_search_employers()


@electwatch_bp.route('/api/admin/unmatched/pacs')
@login_required
@admin_required
def api_admin_get_unmatched_pacs():
    return admin.api_admin_get_unmatched_pacs()


@electwatch_bp.route('/api/admin/unmatched/tickers')
@login_required
@admin_required
def api_admin_get_unmatched_tickers():
    return admin.api_admin_get_unmatched_tickers()


