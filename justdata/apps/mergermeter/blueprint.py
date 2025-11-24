"""
MergerMeter Blueprint for main JustData app.
Converts the standalone MergerMeter app into a blueprint.
"""

from flask import Blueprint, render_template, request, jsonify, send_file, session, Response
import os
import tempfile
import zipfile
from datetime import datetime
import uuid
import threading
import time
import json
from typing import List, Dict

from justdata.main.auth import require_access, get_user_permissions, get_user_type
from justdata.shared.utils.analysis_cache import get_cached_result, store_cached_result, log_usage, generate_cache_key
from justdata.shared.utils.progress_tracker import get_progress, update_progress, create_progress_tracker
from .config import TEMPLATES_DIR, STATIC_DIR, OUTPUT_DIR, PROJECT_ID
from .version import __version__
# Import functions from mergermeter modules
from .branch_assessment_area_generator import generate_assessment_areas_from_branches as _generate_assessment_areas

# Create blueprint
mergermeter_bp = Blueprint(
    'mergermeter',
    __name__,
    template_folder=TEMPLATES_DIR,
    static_folder=STATIC_DIR,
    static_url_path='/mergermeter/static'
)

# Set maximum file upload size to 10MB
mergermeter_bp.config = {'MAX_CONTENT_LENGTH': 10 * 1024 * 1024}


@mergermeter_bp.route('/')
@require_access('mergermeter', 'full')
def index():
    """Main page with the analysis form"""
    user_permissions = get_user_permissions()
    return render_template('analysis_template.html', 
                         version=__version__,
                         permissions=user_permissions)


@mergermeter_bp.route('/report')
@require_access('mergermeter', 'full')
def report():
    """Report display page"""
    job_id_from_url = request.args.get('job_id')
    if job_id_from_url and not session.get('job_id'):
        session['job_id'] = job_id_from_url
    return render_template('report_template.html', version=__version__)


@mergermeter_bp.route('/progress/<job_id>')
def progress_handler(job_id):
    """Progress tracking endpoint using Server-Sent Events"""
    def event_stream():
        last_percent = -1
        last_step = ""
        keepalive_counter = 0
        max_keepalive = 20
        
        try:
            yield f": connected\n\n"
            
            while True:
                try:
                    progress = get_progress(job_id)
                    if not progress:
                        progress = {'percent': 0, 'step': 'Starting...', 'done': False, 'error': None}
                    
                    percent = progress.get("percent", 0)
                    step = progress.get("step", "Starting...")
                    done = progress.get("done", False)
                    error = progress.get("error", None)
                    
                    step_escaped = step.replace('"', '\\"').replace('\n', '\\n').replace('\r', '')
                    
                    if percent != last_percent or step != last_step or done or error:
                        yield f"data: {{\"percent\": {percent}, \"step\": \"{step_escaped}\", \"done\": {str(done).lower()}, \"error\": {json.dumps(error) if error else 'null'}}}\n\n"
                        last_percent = percent
                        last_step = step
                        keepalive_counter = 0
                    
                    if done or error:
                        break
                    
                    keepalive_counter += 1
                    if keepalive_counter >= max_keepalive:
                        yield f": keepalive\n\n"
                        keepalive_counter = 0
                    
                    time.sleep(0.5)
                    
                except GeneratorExit:
                    break
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    time.sleep(1)
        except GeneratorExit:
            pass
        except Exception as e:
            import traceback
            traceback.print_exc()
            try:
                yield f"data: {{\"percent\": 0, \"step\": \"Connection error\", \"done\": true, \"error\": \"Progress tracking error: {str(e)}\"}}\n\n"
            except:
                pass
    
    response = Response(event_stream(), mimetype="text/event-stream")
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    response.headers['Connection'] = 'keep-alive'
    return response


@mergermeter_bp.route('/analyze', methods=['POST'])
@require_access('mergermeter', 'full')
def analyze():
    """Handle analysis request with caching - returns immediately, runs analysis in background thread"""
    import time as time_module
    start_time = time_module.time()
    request_id = str(uuid.uuid4())
    
    try:
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
            'loan_purpose': request.form.get('loan_purpose', ''),
            'hmda_years': request.form.get('hmda_years', '').strip(),  # Will be auto-determined if empty
            'sb_years': request.form.get('sb_years', '').strip(),  # Will be auto-determined if empty
            'action_taken': request.form.get('action_taken', '1'),
            'occupancy_type': request.form.get('occupancy_type', '1'),
            'total_units': request.form.get('total_units', '1-4'),
            'construction_method': request.form.get('construction_method', '1'),
            'not_reverse': request.form.get('not_reverse', '1')
        }
        
        # Get user type for logging
        user_type = get_user_type()
        
        # For cache key, use 'auto' if years are empty (will be normalized)
        cache_params = form_data.copy()
        if not cache_params.get('hmda_years'):
            cache_params['hmda_years'] = 'auto'
        if not cache_params.get('sb_years'):
            cache_params['sb_years'] = 'auto'
        
        # Check cache first
        cached_result = get_cached_result('mergermeter', cache_params, user_type)
        
        if cached_result:
            # Cache hit - use cached result
            job_id = cached_result['job_id']
            session['job_id'] = job_id
            
            # Store result in progress tracker
            from justdata.shared.utils.progress_tracker import store_analysis_result
            store_analysis_result(job_id, cached_result['result_data'])
            update_progress(job_id, {
                'percent': 100,
                'step': 'Analysis complete (from cache)',
                'done': True,
                'cached': True
            })
            
            # Log usage (cache hit)
            response_time_ms = int((time_module.time() - start_time) * 1000)
            cache_key = cached_result.get('cache_key') or generate_cache_key('mergermeter', cache_params)
            log_usage(
                user_type=user_type,
                app_name='mergermeter',
                params=cache_params,
                cache_key=cache_key,
                cache_hit=True,
                job_id=job_id,
                response_time_ms=response_time_ms,
                costs={'bigquery': 0.01, 'ai': 0.0, 'total': 0.01},
                request_id=request_id
            )
            
            return jsonify({
                'success': True,
                'job_id': job_id,
                'cached': True
            })
        
        # Cache miss - run new analysis
        job_id = request.form.get('job_id') or str(uuid.uuid4())
        session['job_id'] = job_id
        
        update_progress(job_id, {'percent': 0, 'step': 'Initializing analysis...', 'done': False, 'error': None})
        
        def run_analysis():
            try:
                from .app import _perform_analysis
                result = _perform_analysis(job_id, form_data)
                
                # Store in cache if successful
                if result and result.get('success'):
                    try:
                        metadata = {
                            'duration_seconds': time_module.time() - start_time
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
                
                # Log usage (cache miss, new analysis)
                response_time_ms = int((time_module.time() - start_time) * 1000)
                cache_key = generate_cache_key('mergermeter', cache_params)
                log_usage(
                    user_type=user_type,
                    app_name='mergermeter',
                    params=cache_params,
                    cache_key=cache_key,
                    cache_hit=False,
                    job_id=job_id,
                    response_time_ms=response_time_ms,
                    costs={'bigquery': 3.0, 'ai': 0.5, 'total': 3.5},  # Estimated costs
                    request_id=request_id
                )
                
            except Exception as e:
                import traceback
                error_msg = str(e)
                traceback.print_exc()
                update_progress(job_id, {'percent': 0, 'step': 'Error occurred', 'done': True, 'error': error_msg})
                
                # Log failed request
                response_time_ms = int((time_module.time() - start_time) * 1000)
                cache_key = generate_cache_key('mergermeter', form_data)
                log_usage(
                    user_type=user_type,
                    app_name='mergermeter',
                    params=cache_params if 'cache_params' in locals() else form_data,
                    cache_key=cache_key,
                    cache_hit=False,
                    job_id=job_id,
                    response_time_ms=response_time_ms,
                    error_message=error_msg,
                    request_id=request_id
                )
        
        thread = threading.Thread(target=run_analysis, daemon=True)
        thread.start()
        
        return jsonify({'success': True, 'job_id': job_id})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Log error
        try:
            response_time_ms = int((time_module.time() - start_time) * 1000)
            log_usage(
                user_type=get_user_type(),
                app_name='mergermeter',
                params=cache_params if 'cache_params' in locals() else (form_data if 'form_data' in locals() else {}),
                cache_key=generate_cache_key('mergermeter', cache_params if 'cache_params' in locals() else (form_data if 'form_data' in locals() else {})),
                cache_hit=False,
                job_id=job_id if 'job_id' in locals() else str(uuid.uuid4()),
                response_time_ms=response_time_ms,
                error_message=str(e),
                request_id=request_id
            )
        except:
            pass
        return jsonify({'error': str(e)}), 500


@mergermeter_bp.route('/download')
@require_access('mergermeter', 'full')
def download():
    """Download the generated Excel file"""
    try:
        from .app import get_excel_filename, generate_filename
        
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
        from .app import clean_bank_name
        
        data = request.get_json()
        acquirer = data.get('acquirer', {})
        target = data.get('target', {})
        
        result = {
            'success': True,
            'acquirer_name': None,
            'target_name': None
        }
        
        client = get_bigquery_client(PROJECT_ID)
        
        # Import bank name lookup function
        from .app import get_bank_name_from_lei, clean_bank_name
        
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
        
        # Validate that at least one bank name was found
        if not result['acquirer_name'] and not result['target_name']:
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
        
        # Generate assessment areas based on CBSA deposit share (>1% of bank's national deposits)
        assessment_areas = _generate_assessment_areas(
            rssd=rssd,
            year=year,
            min_deposit_share=0.01  # 1% of bank's national deposits
        )
        
        if not assessment_areas:
            return jsonify({
                'success': False,
                'error': f'No branches found for RSSD {rssd} in year {year}. Please verify the RSSD number and year.'
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
        from .app import upload_assessment_areas as upload_func
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
        from .app import generate_ai_summary as generate_func
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
        from .app import report_data as get_report_data_func
        # Call the original function
        return get_report_data_func()
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@mergermeter_bp.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'app': 'mergermeter',
        'version': __version__
    })

