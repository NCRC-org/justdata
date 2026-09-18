"""
MergerMeter Blueprint for main JustData app.
Converts the standalone MergerMeter app into a blueprint.
"""

from flask import Blueprint, render_template, request, jsonify, send_file, session, Response, url_for
from jinja2 import ChoiceLoader, FileSystemLoader
import os
import tempfile
import zipfile
from datetime import datetime
import uuid
import time
import json
from typing import List, Dict
from pathlib import Path

from justdata.main.auth import require_access, get_user_permissions, login_required
from justdata.backend import (
    new_job_id, run_in_background, sse_response,
    identify_caller, lookup_cached_analysis, record_cache_hit, record_completion,
)
from justdata.shared.utils.analysis_cache import store_cached_result, get_analysis_result_by_job_id
from justdata.shared.utils.progress_tracker import get_progress, update_progress, create_progress_tracker
from .config import TEMPLATES_DIR, STATIC_DIR, OUTPUT_DIR, PROJECT_ID
from .version import __version__
# Import functions from mergermeter modules
from .branch_assessment_area_generator import generate_assessment_areas_from_branches as _generate_assessment_areas

# Get shared templates directory
REPO_ROOT = Path(__file__).parent.parent.parent.absolute()
SHARED_TEMPLATES_DIR = REPO_ROOT / 'shared' / 'web' / 'templates'

# Create blueprint
mergermeter_bp = Blueprint(
    'mergermeter',
    __name__,
    template_folder=TEMPLATES_DIR,
    static_folder=STATIC_DIR,
    static_url_path='/mergermeter/static'
)


@mergermeter_bp.record_once
def configure_template_loader(state):
    """Configure Jinja2 to search blueprint templates first.

    IMPORTANT: Blueprint templates must come FIRST in the ChoiceLoader so that
    app-specific templates (like report_template.html) are found before shared
    templates or other blueprints' templates with the same name.

    NOTE: We do NOT add shared_loader here because the main app already includes
    shared templates. Adding it again would cause shared templates to be searched
    BEFORE other blueprint templates, leading to wrong template being rendered.
    """
    app = state.app
    blueprint_loader = FileSystemLoader(str(TEMPLATES_DIR))
    app.jinja_loader = ChoiceLoader([
        blueprint_loader,  # Blueprint templates first (highest priority)
        app.jinja_loader   # Main app loader (already includes shared templates)
    ])

# Set maximum file upload size to 10MB
mergermeter_bp.config = {'MAX_CONTENT_LENGTH': 10 * 1024 * 1024}


@mergermeter_bp.route('/')
@login_required
@require_access('mergermeter', 'full')
def index():
    """Main page with the analysis form"""
    user_permissions = get_user_permissions()
    app_base_url = url_for('mergermeter.index').rstrip('/')
    # HMDA year selector options/defaults from the platform-wide source of truth
    # (see justdata/shared/core/hmda_years.py). Bumping LATEST_HMDA_YEAR there adds
    # the new year to these dropdowns and shifts the default range automatically.
    from justdata.shared.core.hmda_years import available_hmda_years, default_hmda_year_range
    hmda_years = available_hmda_years()
    hmda_default_start, hmda_default_end = default_hmda_year_range()
    return render_template('mergermeter_analysis.html',
                         version=__version__,
                         permissions=user_permissions,
                         app_base_url=app_base_url,
                         app_name='MergerMeter',
                         hmda_years=hmda_years,
                         hmda_default_start=hmda_default_start,
                         hmda_default_end=hmda_default_end,
                         breadcrumb_items=[{'name': 'MergerMeter', 'url': '/mergermeter'}])


@mergermeter_bp.route('/report')
@login_required
@require_access('mergermeter', 'full')
def report():
    """Report display page - renders Goals Calculator directly"""
    try:
        from .mergermeter_ops import goals_calculator as goals_calc_func
        # Call the goals calculator function which handles all the data loading
        return goals_calc_func()
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@mergermeter_bp.route('/goals-calculator')
@login_required
@require_access('mergermeter', 'full')
def goals_calculator():
    """CBA Goals Calculator page - interactive tool for setting lending goals"""
    try:
        from .mergermeter_ops import goals_calculator as goals_calc_func
        return goals_calc_func()
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@mergermeter_bp.route('/progress/<job_id>')
@login_required
def progress_handler(job_id):
    """Progress tracking endpoint using Server-Sent Events"""
    return sse_response(job_id)


@mergermeter_bp.route('/analyze', methods=['POST'])
@login_required
@require_access('mergermeter', 'full')
def analyze():
    """Handle analysis request with caching - returns immediately, runs analysis in background thread"""
    start_time = time.time()
    request_id = new_job_id()
    
    try:
        # Default HMDA analysis range from the platform-wide source of truth
        # (see justdata/shared/core/hmda_years.py). Bump LATEST_HMDA_YEAR to roll forward.
        from justdata.shared.core.hmda_years import default_hmda_year_range
        _hmda_default_start, _hmda_default_end = (str(y) for y in default_hmda_year_range())
        form_data = {
            'acquirer_lei': request.form.get('acquirer_lei', '').strip(),
            'acquirer_rssd': request.form.get('acquirer_rssd', '').strip(),
            'acquirer_sb_id': request.form.get('acquirer_sb_id', '').strip(),
            'target_lei': request.form.get('target_lei', '').strip(),
            'target_rssd': request.form.get('target_rssd', '').strip(),
            'target_sb_id': request.form.get('target_sb_id', '').strip(),
            'acquirer_name': request.form.get('acquirer_name', 'Bank A').strip(),
            'target_name': request.form.get('target_name', 'Bank B').strip(),
            'acquirer_assessment_areas': request.form.get('acquirer_assessment_areas', '[]'),
            'target_assessment_areas': request.form.get('target_assessment_areas', '[]'),
            'use_national_data': request.form.get('use_national_data', '0'),  # National level data flag
            'loan_purpose': request.form.get('loan_purpose', ''),
            'peer_group': request.form.get('peer_group', 'volume_50_200').strip(),  # Peer group selection
            # Analysis year ranges (HMDA defaults from shared source of truth; SB is a separate cadence)
            'hmda_start_year': request.form.get('hmda_start_year', _hmda_default_start).strip(),
            'hmda_end_year': request.form.get('hmda_end_year', _hmda_default_end).strip(),
            'sb_start_year': request.form.get('sb_start_year', '2023').strip(),
            'sb_end_year': request.form.get('sb_end_year', '2024').strip(),
            # Goal baseline year ranges
            'baseline_hmda_start_year': request.form.get('baseline_hmda_start_year', _hmda_default_start).strip(),
            'baseline_hmda_end_year': request.form.get('baseline_hmda_end_year', _hmda_default_end).strip(),
            'baseline_sb_start_year': request.form.get('baseline_sb_start_year', '2023').strip(),
            'baseline_sb_end_year': request.form.get('baseline_sb_end_year', '2024').strip(),
            'action_taken': request.form.get('action_taken', '1'),
            'occupancy_type': request.form.get('occupancy_type', '1'),
            'total_units': request.form.get('total_units', '1-4'),
            'construction_method': request.form.get('construction_method', '1'),
            'not_reverse': request.form.get('not_reverse', '1')
        }

        # Debug: Log the SB IDs received from form
        print(f"[DEBUG] Form received - acquirer_sb_id: '{form_data.get('acquirer_sb_id', 'NOT SET')}'")
        print(f"[DEBUG] Form received - target_sb_id: '{form_data.get('target_sb_id', 'NOT SET')}'")
        
        # Resolves tier, identity, IP and user agent while the request still exists
        caller = identify_caller()
        user_type = caller.user_type
        if not caller.user_id and not caller.user_email:
            print(f"[WARN] MergerMeter analyze: No user identity captured despite @login_required")
            print(f"[WARN] Session keys: {list(session.keys())}")

        # For cache key, normalize the year ranges
        cache_params = form_data.copy()
        # Cache key includes all year parameters (analysis + baseline)

        cached = lookup_cached_analysis(
            'mergermeter', cache_params, caller,
            force_refresh_requested=request.form.get('force_refresh', '0') == '1',
        )

        if cached:
            # Reuse the stored result instead of re-running BigQuery and Claude
            session['job_id'] = cached.job_id
            record_cache_hit('mergermeter', cache_params, caller, cached,
                             start_time, request_id)
            return jsonify({
                'success': True,
                'job_id': cached.job_id,
                'cached': True
            })

        # Cache miss - run new analysis
        job_id = request.form.get('job_id') or new_job_id()
        session['job_id'] = job_id
        
        update_progress(job_id, {'percent': 0, 'step': 'Initializing analysis...', 'done': False, 'error': None})
        
        def run_analysis():
            try:
                from .mergermeter_ops import _perform_analysis
                result = _perform_analysis(job_id, form_data)
                
                # Store in cache if successful
                if result and result.get('success'):
                    try:
                        metadata = {
                            'duration_seconds': time.time() - start_time
                        }
                        # Use cache_params for storing (with 'auto' for years)
                        store_cached_result(
                            app_name='mergermeter',
                            params=cache_params,
                            job_id=job_id,
                            result_data=result,
                            user_type=user_type,
                            metadata=metadata
                        )
                    except Exception as cache_error:
                        print(f"Warning: Failed to store in cache: {cache_error}")
                
                record_completion('mergermeter', cache_params, caller, job_id,
                                  start_time, request_id,
                                  costs={'bigquery': 3.0, 'ai': 0.5, 'total': 3.5})

            except Exception as e:
                import traceback
                error_msg = str(e)
                traceback.print_exc()
                update_progress(job_id, {'percent': 0, 'step': 'Error occurred', 'done': True, 'error': error_msg})
                record_completion('mergermeter', cache_params, caller, job_id,
                                  start_time, request_id, error_message=error_msg)

        run_in_background(run_analysis)
        
        return jsonify({'success': True, 'job_id': job_id})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        # The failure may predate caller/cache_params being set, so fall back.
        record_completion(
            'mergermeter',
            cache_params if 'cache_params' in locals() else (form_data if 'form_data' in locals() else {}),
            caller if 'caller' in locals() else identify_caller(),
            job_id if 'job_id' in locals() else new_job_id(),
            start_time, request_id, error_message=str(e),
        )
        return jsonify({'error': str(e)}), 500


@mergermeter_bp.route('/excel-data')
@login_required
@require_access('mergermeter', 'full')
def excel_data():
    """Serve the generated Excel file inline (for SheetJS preview rendering)"""
    try:
        from .mergermeter_ops import get_excel_filename

        job_id = request.args.get('job_id') or session.get('job_id')
        if not job_id:
            return jsonify({'error': 'Job ID required'}), 400

        excel_filename = get_excel_filename(job_id)
        excel_file = OUTPUT_DIR / excel_filename
        if not excel_file.exists():
            return jsonify({'error': 'Report file not found.'}), 404

        return send_file(
            str(excel_file),
            as_attachment=False,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@mergermeter_bp.route('/download')
@login_required
@require_access('mergermeter', 'full')
def download():
    """Download the generated Excel file"""
    try:
        from .mergermeter_ops import get_excel_filename, generate_filename
        
        job_id = request.args.get('job_id') or session.get('job_id')
        if not job_id:
            return jsonify({'error': 'Job ID required'}), 400
        
        excel_filename = get_excel_filename(job_id)
        excel_file = OUTPUT_DIR / excel_filename
        if not excel_file.exists():
            return jsonify({'error': 'Report file not found. The analysis may not have completed yet.'}), 404
        
        # Try to load metadata for filename generation
        metadata = {}
        metadata_file = OUTPUT_DIR / f'merger_metadata_{job_id}.json'
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
        
        # Generate filename with NCRC, MergerMeter, bank names, and timestamp
        filename = generate_filename(metadata, '.xlsx')
        
        # Check user permissions for export
        user_permissions = get_user_permissions()
        if not user_permissions.get('can_export', False):
            return jsonify({
                'error': 'Export functionality is not available for your account type.'
            }), 403
        
        return send_file(
            str(excel_file),
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@mergermeter_bp.route('/api/load-bank-names', methods=['POST'])
@require_access('mergermeter', 'full')
def api_load_bank_names():
    """Load bank names from identifiers (LEI, RSSD, or SB Respondent ID)"""
    try:
        from justdata.shared.utils.bigquery_client import get_bigquery_client
        from .mergermeter_ops import clean_bank_name, get_bank_name_from_lei

        data = request.get_json()
        acquirer = data.get('acquirer', {})
        target = data.get('target', {})
        single_bank_mode = data.get('single_bank_mode', False)

        result = {
            'success': True,
            'acquirer_name': None,
            'target_name': None,
            'single_bank_mode': single_bank_mode
        }
        
        client = get_bigquery_client(PROJECT_ID, app_name='MERGERMETER')

        # Look up acquirer bank name using LEI
        if acquirer.get('name'):
            result['acquirer_name'] = acquirer.get('name').strip()
        elif acquirer.get('lei'):
            acquirer_lei = acquirer.get('lei').strip()
            if len(acquirer_lei) == 20:
                acquirer_name = get_bank_name_from_lei(client, acquirer_lei)
                if acquirer_name:
                    result['acquirer_name'] = acquirer_name
                else:
                    return jsonify({
                        'success': False,
                        'error': f'Could not find bank name for LEI: {acquirer_lei}. Please verify the LEI number is correct.'
                    }), 404
        
        # Look up target bank name using LEI
        if target.get('name'):
            result['target_name'] = target.get('name').strip()
        elif target.get('lei'):
            target_lei = target.get('lei').strip()
            if len(target_lei) == 20:
                target_name = get_bank_name_from_lei(client, target_lei)
                if target_name:
                    result['target_name'] = target_name
                else:
                    return jsonify({
                        'success': False,
                        'error': f'Could not find bank name for LEI: {target_lei}. Please verify the LEI number is correct.'
                    }), 404
        
        # Validate that required bank names were found
        # In single bank mode, only acquirer is required
        # In merger mode, both acquirer and target are required
        if single_bank_mode:
            if not result['acquirer_name']:
                return jsonify({
                    'success': False,
                    'error': 'Please provide a valid LEI number for the bank. Bank name is looked up using the LEI number.'
                }), 400
        else:
            if not result['acquirer_name'] or not result['target_name']:
                return jsonify({
                    'success': False,
                    'error': 'Please provide LEI numbers for both banks. Bank names are looked up using the LEI number.'
                }), 400
        
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@mergermeter_bp.route('/api/generate-assessment-areas-from-branches', methods=['POST'])
@require_access('mergermeter', 'full')
def api_generate_assessment_areas():
    """Generate assessment areas from branch locations for a bank"""
    try:
        data = request.get_json()
        rssd = data.get('rssd', '').strip()
        bank_type = data.get('bank_type', 'acquirer')
        year = int(data.get('year', 2025))
        
        if not rssd:
            return jsonify({
                'success': False,
                'error': 'RSSD number is required to generate assessment areas from branches.'
            }), 400
        
        # Generate assessment areas based on branch locations
        assessment_areas = _generate_assessment_areas(
            rssd=rssd,
            year=year,
            min_share=0.01  # 1% threshold for deposits/loans methods
        )
        
        if not assessment_areas:
            return jsonify({
                'success': False,
                'error': f'No branches found for RSSD {rssd} as of {year}. This may indicate the bank has merged, been acquired, or changed its charter. Try searching for the bank under its new name, or manually enter the assessment areas.'
            }), 404
        
        return jsonify({
            'success': True,
            'assessment_areas': assessment_areas,
            'bank_type': bank_type,
            'count': len(assessment_areas)
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Error: {str(e)}'}), 500


@mergermeter_bp.route('/api/download-assessment-area-template', methods=['GET'])
@require_access('mergermeter', 'full')
def api_download_assessment_area_template():
    """Download CSV template for assessment areas"""
    from flask import Response
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        'Assessment Area Name',
        'State Code',
        'County Code',
        'County Name',
        'State Name'
    ])
    
    examples = [
        ['Tampa-St. Petersburg-Clearwater FL', '12', '057', 'Hillsborough', 'Florida'],
        ['Tampa-St. Petersburg-Clearwater FL', '12', '103', 'Pinellas', 'Florida'],
        ['Tampa-St. Petersburg-Clearwater FL', '12', '101', 'Pasco', 'Florida'],
    ]
    
    for row in examples:
        writer.writerow(row)
    
    output.seek(0)
    response = Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename=assessment_area_template.csv'
        }
    )
    return response


@mergermeter_bp.route('/api/download-bank-identifiers-template', methods=['GET'])
@require_access('mergermeter', 'full')
def api_download_bank_identifiers_template():
    """Download CSV template for bank identifiers (LEI, RSSD, ResID)"""
    from flask import Response
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        'Bank Name',
        'LEI',
        'RSSD',
        'ResID'
    ])
    
    examples = [
        ['PNC BANK', '549300BJX7P13H14EN18', '451965', '123456789'],
        ['FIRSTBANK', '549300ABC123DEF456', '123456', '987654321'],
    ]
    
    for row in examples:
        writer.writerow(row)
    
    output.seek(0)
    response = Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename=bank_identifiers_template.csv'
        }
    )
    return response


@mergermeter_bp.route('/api/upload-assessment-areas', methods=['POST'])
@require_access('mergermeter', 'full')
def api_upload_assessment_areas():
    """Upload and parse assessment area JSON or CSV file"""
    try:
        from .mergermeter_ops import upload_assessment_areas as upload_func
        # Call the original function from app module
        return upload_func()
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@mergermeter_bp.route('/api/generate-ai-summary', methods=['POST'])
@require_access('mergermeter', 'full')
def api_generate_ai_summary():
    """Generate AI summary of analysis"""
    try:
        from .mergermeter_ops import generate_ai_summary as generate_func
        # Call the original function from app module
        return generate_func()
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@mergermeter_bp.route('/report-data')
@require_access('mergermeter', 'full')
def report_data():
    """Return the analysis report data for web display"""
    try:
        from .mergermeter_ops import report_data as get_report_data_func
        # Call the original function
        return get_report_data_func()
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@mergermeter_bp.route('/api/search-banks', methods=['GET'])
@require_access('mergermeter', 'full')
def api_search_banks():
    """Search for banks by name with autocomplete support.
    Returns bank name, location info, and identifiers (LEI, RSSD, Res ID).
    Used for bank selection dropdown in the analysis form.
    """
    try:
        from justdata.shared.utils.bigquery_client import get_bigquery_client

        query = request.args.get('q', '').strip()
        limit = min(int(request.args.get('limit', 20)), 50)  # Max 50 results

        if len(query) < 2:
            return jsonify({'success': True, 'banks': [], 'message': 'Enter at least 2 characters'})

        client = get_bigquery_client(PROJECT_ID, app_name='MERGERMETER')

        # Search query joining lender_names_gleif with lenders18 and bizsight.sb_lenders
        # Returns display name, location info, and identifiers (LEI, RSSD, SB Res ID)
        # Links: LEI -> lenders18 (RSSD) -> bizsight.sb_lenders (sb_rssd -> sb_resid)
        # Note: ORDER BY must use the alias 'assets' not 'l.assets' when using DISTINCT
        sql = """
        SELECT DISTINCT
            g.display_name AS name,
            g.headquarters_city AS city,
            g.headquarters_state AS state,
            l.lei AS lei,
            CAST(l.respondent_rssd AS STRING) AS rssd,
            sb.sb_resid AS res_id,
            SAFE_CAST(l.assets AS INT64) AS assets
        FROM `justdata-ncrc.shared.lender_names_gleif` g
        JOIN `justdata-ncrc.lendsight.lenders18` l ON g.lei = l.lei
        LEFT JOIN `justdata-ncrc.bizsight.sb_lenders` sb ON CAST(l.respondent_rssd AS STRING) = sb.sb_rssd
        WHERE LOWER(g.display_name) LIKE LOWER(@search_pattern)
        ORDER BY assets DESC NULLS LAST
        LIMIT @limit
        """

        # Execute query
        from google.cloud import bigquery
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter('search_pattern', 'STRING', f'%{query}%'),
                bigquery.ScalarQueryParameter('limit', 'INT64', limit)
            ]
        )

        query_job = client.query(sql, job_config=job_config)
        results = query_job.result()

        banks = []
        for row in results:
            # Format location string
            location = ''
            if row.city and row.state:
                location = f"{row.city}, {row.state}"
            elif row.state:
                location = row.state
            elif row.city:
                location = row.city

            banks.append({
                'name': row.name,
                'location': location,
                'city': row.city or '',
                'state': row.state or '',
                'lei': row.lei or '',
                'rssd': row.rssd or '',
                'res_id': row.res_id or '',  # From bizsight.sb_lenders via RSSD lookup
                'assets': row.assets
            })

        return jsonify({
            'success': True,
            'banks': banks,
            'count': len(banks)
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@mergermeter_bp.route('/api/export-goals', methods=['POST'])
@require_access('mergermeter', 'full')
def api_export_goals():
    """Export goals calculator configuration and data to Excel"""
    try:
        from .mergermeter_ops import export_goals as export_goals_func
        return export_goals_func()
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@mergermeter_bp.route('/api/search-banks-ext', methods=['GET'])
def api_search_banks_ext():
    """Bank search endpoint for external callers (API key auth).

    Same query as the web form's autocomplete: joins lender_names_gleif
    with lenders18 and sb_lenders to return the authoritative LEI, RSSD,
    and SB respondent ID that match HMDA/CRA filing data.

    Query params:
        q: search string (min 2 chars)
        api_key: shared secret
        limit: max results (default 10, max 50)
    """
    api_key = request.args.get('api_key', '')
    expected_key = os.environ.get('MERGERMETER_API_KEY', '')
    if not expected_key or api_key != expected_key:
        return jsonify({"error": "Invalid or missing API key"}), 401

    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({"banks": [], "message": "Enter at least 2 characters"})

    limit = min(int(request.args.get('limit', 10)), 50)

    try:
        from justdata.shared.utils.bigquery_client import get_bigquery_client
        from google.cloud import bigquery as bq_module

        client = get_bigquery_client(PROJECT_ID, app_name='MERGERMETER')

        sql = """
        WITH sb_latest AS (
            SELECT sb_rssd, sb_resid,
                ROW_NUMBER() OVER (PARTITION BY SAFE_CAST(sb_rssd AS INT64) ORDER BY sb_year DESC) AS rn
            FROM `justdata-ncrc.bizsight.sb_lenders`
        )
        SELECT DISTINCT
            g.display_name AS name,
            g.headquarters_city AS city,
            g.headquarters_state AS state,
            l.lei AS lei,
            CAST(l.respondent_rssd AS STRING) AS rssd,
            sb.sb_resid AS res_id,
            SAFE_CAST(l.assets AS INT64) AS assets
        FROM `justdata-ncrc.shared.lender_names_gleif` g
        JOIN `justdata-ncrc.lendsight.lenders18` l ON g.lei = l.lei
        LEFT JOIN sb_latest sb
            ON SAFE_CAST(l.respondent_rssd AS INT64) = SAFE_CAST(sb.sb_rssd AS INT64)
            AND sb.rn = 1
        WHERE LOWER(g.display_name) LIKE LOWER(@search_pattern)
        ORDER BY assets DESC NULLS LAST
        LIMIT @limit
        """

        job_config = bq_module.QueryJobConfig(query_parameters=[
            bq_module.ScalarQueryParameter('search_pattern', 'STRING', f'%{query}%'),
            bq_module.ScalarQueryParameter('limit', 'INT64', limit),
        ])

        banks = []
        for row in client.query(sql, job_config=job_config).result():
            location = ''
            if row.city and row.state:
                location = f"{row.city}, {row.state}"
            elif row.state:
                location = row.state

            banks.append({
                'name': row.name,
                'location': location,
                'lei': row.lei or '',
                'rssd': row.rssd or '',
                'res_id': row.res_id or '',
                'assets': row.assets,
            })

        return jsonify({"banks": banks, "count": len(banks)})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@mergermeter_bp.route('/api/generate', methods=['POST'])
def api_generate():
    """JSON API endpoint for programmatic Excel generation.

    Accepts bank identifiers and parameters as JSON, runs the same analysis
    pipeline as the web form, and returns the Excel file bytes directly.
    No login required — authenticated via shared API key.
    """
    import traceback

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    # Validate API key
    expected_key = os.environ.get('MERGERMETER_API_KEY', '')
    if not expected_key or data.get('api_key') != expected_key:
        return jsonify({"error": "Invalid or missing API key"}), 401

    try:
        from .mergermeter_ops import _perform_analysis, clean_bank_name

        bank_a = data.get('bank_a') or {}
        bank_b = data.get('bank_b')
        single_bank_mode = bank_b is None or not bank_b

        # Validate required fields
        if not bank_a.get('lei'):
            return jsonify({"error": "bank_a.lei is required"}), 422
        if not bank_a.get('name'):
            return jsonify({"error": "bank_a.name is required"}), 422

        # --- Derive assessment areas separately per bank ---
        acquirer_areas = []
        target_areas = []

        if data.get('assessment_areas'):
            # Custom AAs provided — use for both banks (user's explicit intent)
            acquirer_areas = data['assessment_areas']
            target_areas = data['assessment_areas']
        else:
            # Auto-derive from each bank's branches independently
            rssd_a = (bank_a.get('rssd') or '').strip()
            if rssd_a:
                try:
                    areas_a = _generate_assessment_areas(rssd=rssd_a, year=2025, method='deposits', min_share=0.01)
                    if areas_a:
                        acquirer_areas = areas_a
                except Exception as e:
                    print(f"[API] Warning: AA derivation failed for acquirer RSSD {rssd_a}: {e}")

            if bank_b:
                rssd_b = (bank_b.get('rssd') or '').strip()
                if rssd_b:
                    try:
                        areas_b = _generate_assessment_areas(rssd=rssd_b, year=2025, method='deposits', min_share=0.01)
                        if areas_b:
                            target_areas = areas_b
                    except Exception as e:
                        print(f"[API] Warning: AA derivation failed for target RSSD {rssd_b}: {e}")

            if not acquirer_areas and not target_areas:
                return jsonify({
                    "error": "No assessment areas provided and could not derive from branches. "
                             "Provide assessment_areas or ensure bank RSSD is correct."
                }), 422

        acquirer_areas_json = json.dumps(acquirer_areas)
        target_areas_json = json.dumps(target_areas)

        # --- Map loan_purposes strings to HMDA codes ---
        loan_purpose_codes = []
        for lp in (data.get('loan_purposes') or []):
            if lp == 'home_purchase':
                loan_purpose_codes.append('1')
            elif lp == 'refinance':
                loan_purpose_codes.extend(['31', '32'])
            elif lp in ('home_improvement', 'home_equity'):
                loan_purpose_codes.extend(['2', '4'])
        loan_purpose_str = ','.join(loan_purpose_codes) if loan_purpose_codes else ''

        # --- Map filter params ---
        action_taken_list = data.get('action_taken', [1])
        action_taken_str = ','.join(str(a) for a in action_taken_list)

        occupancy_list = data.get('occupancy', [1])
        occupancy_str = ','.join(str(o) for o in occupancy_list)

        total_units_list = data.get('total_units', ['1', '2', '3', '4'])
        total_units_str = ','.join(str(u) for u in total_units_list)

        construction_list = data.get('construction_method', [1, 2])
        construction_str = ','.join(str(c) for c in construction_list)

        reverse_mortgage = data.get('reverse_mortgage', False)
        not_reverse = '2' if reverse_mortgage else '1'

        # --- Build form_data dict matching _perform_analysis expectations ---
        job_id = str(uuid.uuid4())

        hmda_start = str(data.get('hmda_years_start', 2023))
        hmda_end = str(data.get('hmda_years_end', 2024))
        sb_start = str(data.get('sb_years_start', 2023))
        sb_end = str(data.get('sb_years_end', 2024))

        form_data = {
            'acquirer_lei': (bank_a.get('lei') or '').strip(),
            'acquirer_rssd': (bank_a.get('rssd') or '').strip(),
            'acquirer_sb_id': (bank_a.get('respondent_id') or bank_a.get('rssd') or '').strip(),
            'acquirer_name': (bank_a.get('name') or 'Bank A').strip(),
            'acquirer_assessment_areas': acquirer_areas_json,
            'target_lei': '',
            'target_rssd': '',
            'target_sb_id': '',
            'target_name': '',
            'target_assessment_areas': '[]',
            'single_bank_mode': '1' if single_bank_mode else '0',
            'use_national_data': '0',
            'loan_purpose': loan_purpose_str,
            'peer_group': data.get('peer_group', 'volume_50_200'),
            'hmda_start_year': hmda_start,
            'hmda_end_year': hmda_end,
            'sb_start_year': sb_start,
            'sb_end_year': sb_end,
            'baseline_hmda_start_year': hmda_start,
            'baseline_hmda_end_year': hmda_end,
            'baseline_sb_start_year': sb_start,
            'baseline_sb_end_year': sb_end,
            'action_taken': action_taken_str,
            'occupancy_type': occupancy_str,
            'total_units': total_units_str,
            'construction_method': construction_str,
            'not_reverse': not_reverse,
        }

        if not single_bank_mode and bank_b:
            form_data['target_lei'] = (bank_b.get('lei') or '').strip()
            form_data['target_rssd'] = (bank_b.get('rssd') or '').strip()
            form_data['target_sb_id'] = (bank_b.get('respondent_id') or bank_b.get('rssd') or '').strip()
            form_data['target_name'] = (bank_b.get('name') or 'Bank B').strip()
            form_data['target_assessment_areas'] = target_areas_json
            form_data['single_bank_mode'] = '0'

        # --- Run analysis synchronously ---
        _perform_analysis(job_id, form_data)

        # --- Check for errors via progress tracker ---
        progress = get_progress(job_id)
        if progress and progress.get('error'):
            return jsonify({
                "error": "Analysis failed",
                "details": progress['error']
            }), 500

        # --- Find and return the Excel file ---
        import re as re_mod
        acquirer_name_short = clean_bank_name(bank_a.get('name', 'Bank A'))
        acquirer_name_safe = re_mod.sub(r'[^\w\s-]', '', acquirer_name_short)
        acquirer_name_safe = re_mod.sub(r'[\s-]+', '_', acquirer_name_safe)
        acquirer_name_safe = re_mod.sub(r'__+', '_', acquirer_name_safe).strip('_')
        if len(acquirer_name_safe) > 50:
            acquirer_name_safe = acquirer_name_safe[:50]

        excel_file = OUTPUT_DIR / f'merger_analysis_{acquirer_name_safe}_{job_id}.xlsx'

        if not excel_file.exists():
            # Try checking metadata for the actual filename
            metadata_file = OUTPUT_DIR / f'merger_metadata_{job_id}.json'
            if metadata_file.exists():
                with open(metadata_file) as mf:
                    meta = json.load(mf)
                    actual_name = meta.get('excel_filename')
                    if actual_name:
                        excel_file = OUTPUT_DIR / actual_name

        if not excel_file.exists():
            return jsonify({
                "error": "Analysis completed but Excel file not found",
                "details": f"Expected at {excel_file}"
            }), 500

        # Build a friendly download filename
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        bank_a_short = clean_bank_name(bank_a.get('name', 'BANK')).upper().replace(' ', '_')[:25]
        bank_b_short = ''
        if not single_bank_mode and bank_b and bank_b.get('name'):
            bank_b_short = '_' + clean_bank_name(bank_b['name']).upper().replace(' ', '_')[:25]
        download_name = f'NCRC_MergerMeter_{bank_a_short}{bank_b_short}_{ts}.xlsx'

        return send_file(
            excel_file,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=download_name
        )

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@mergermeter_bp.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'app': 'mergermeter',
        'version': __version__
    })

