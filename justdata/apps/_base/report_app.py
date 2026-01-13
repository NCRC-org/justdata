"""
Base class for report generator applications (LendSight, BizSight, BranchSight).
Provides shared infrastructure for:
- Flask app creation with standard routes
- Background job processing with progress tracking
- SSE (Server-Sent Events) progress streaming
- Report data serialization and download
"""

from abc import ABC, abstractmethod
from flask import Flask, request, jsonify, session, Response, render_template, send_file
import uuid
import threading
import time
import json
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from werkzeug.middleware.proxy_fix import ProxyFix

from justdata.shared.core.app_factory import create_app
from justdata.shared.utils.progress_tracker import (
    create_progress_tracker, get_progress, update_progress,
    store_analysis_result, get_analysis_result
)
from justdata.shared.utils.json_utils import ensure_json_serializable, serialize_dataframes


class BaseReportApp(ABC):
    """
    Abstract base class for report generator applications.

    Subclasses must implement:
    - run_analysis(): Core analysis logic
    - build_report(): Report data building
    - download_excel(): Excel export
    - get_template_vars(): Template variables for index page

    Provides:
    - Standard Flask routes (/, /analyze, /progress, /report, /download)
    - Background job management with progress tracking
    - SSE progress streaming
    - Report data serialization
    """

    def __init__(self, app_name: str, config: Any):
        """
        Initialize the report app.

        Args:
            app_name: Name of the application (e.g., 'lendsight')
            config: Application configuration object
        """
        self.app_name = app_name
        self.config = config
        self.app: Optional[Flask] = None

    def create_flask_app(self, template_folder: str = None, static_folder: str = None) -> Flask:
        """
        Create and configure the Flask application.

        Args:
            template_folder: Path to templates directory
            static_folder: Path to static files directory

        Returns:
            Configured Flask application
        """
        self.app = create_app(
            self.app_name,
            template_folder=template_folder,
            static_folder=static_folder
        )

        # Add ProxyFix for proper request handling behind proxies
        self.app.wsgi_app = ProxyFix(self.app.wsgi_app, x_for=1, x_proto=1)

        # Configure cache-busting for development
        self.app.config['DEBUG'] = getattr(self.config, 'debug', True)
        self.app.config['TEMPLATES_AUTO_RELOAD'] = True
        self.app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

        # Disable Jinja2 bytecode cache
        self.app.jinja_env.bytecode_cache = None

        # Register routes
        self._register_routes()

        return self.app

    def _register_routes(self):
        """Register all standard routes for the application."""
        self.app.add_url_rule('/', 'index', self.index, methods=['GET'])
        self.app.add_url_rule('/analyze', 'analyze', self.analyze, methods=['POST'])
        self.app.add_url_rule('/progress/<job_id>', 'progress', self.progress_handler, methods=['GET'])
        self.app.add_url_rule('/report', 'report', self.report, methods=['GET'])
        self.app.add_url_rule('/report-data', 'report_data', self.report_data, methods=['GET'])
        self.app.add_url_rule('/download', 'download', self.download, methods=['GET'])

        # Optional: Register app-specific data endpoints
        if hasattr(self, 'get_data_handler'):
            data_handler = self.get_data_handler()
            if data_handler:
                self.app.add_url_rule('/data', 'data', data_handler, methods=['GET'])

    # =========================================================================
    # Route Handlers
    # =========================================================================

    def index(self):
        """Main page with the analysis form."""
        template_vars = self.get_template_vars()
        template_name = getattr(self.config, 'index_template', 'analysis_template.html')
        return render_template(template_name, **template_vars)

    def analyze(self):
        """
        Handle analysis form submission.
        Starts a background thread for the analysis and returns job_id.
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400

            job_id = str(uuid.uuid4())
            progress_tracker = create_progress_tracker(job_id, self.get_progress_steps())

            # Store job_id in session
            session['job_id'] = job_id

            def run_job():
                try:
                    result = self.run_analysis(data, job_id, progress_tracker)
                    if result.get('success', True):
                        store_analysis_result(job_id, result)
                        progress_tracker.complete(success=True)
                    else:
                        progress_tracker.complete(success=False, error=result.get('error', 'Unknown error'))
                except Exception as e:
                    import traceback
                    error_msg = f"{str(e)}\n{traceback.format_exc()}"
                    progress_tracker.complete(success=False, error=error_msg)

            # Start background thread
            thread = threading.Thread(target=run_job, daemon=True)
            thread.start()

            return jsonify({'success': True, 'job_id': job_id})

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    def progress_handler(self, job_id: str):
        """
        Progress tracking endpoint using Server-Sent Events (SSE).
        Streams progress updates to the client.
        """
        def event_stream():
            last_percent = -1
            last_step = ""
            keepalive_counter = 0
            max_keepalive = 20  # Send keepalive every 10 seconds (20 * 0.5s)

            try:
                # Send initial connection message
                yield ": connected\n\n"

                while True:
                    try:
                        progress = get_progress(job_id)
                        if not progress:
                            progress = {'percent': 0, 'step': 'Starting...', 'done': False, 'error': None}

                        percent = progress.get('percent', 0)
                        step = progress.get('step', 'Starting...')
                        done = progress.get('done', False)
                        error = progress.get('error', None)

                        # Escape step message for JSON
                        step_escaped = step.replace('"', '\\"').replace('\n', '\\n').replace('\r', '')

                        # Send update if percent, step, done, or error changed
                        if percent != last_percent or step != last_step or done or error:
                            yield f'data: {{"percent": {percent}, "step": "{step_escaped}", "done": {str(done).lower()}, "error": {json.dumps(error) if error else "null"}}}\n\n'
                            last_percent = percent
                            last_step = step
                            keepalive_counter = 0

                        if done or error:
                            time.sleep(0.2)
                            break

                        # Send keepalive comment to prevent connection timeout
                        keepalive_counter += 1
                        if keepalive_counter >= max_keepalive:
                            yield ": keepalive\n\n"
                            keepalive_counter = 0

                        time.sleep(0.5)

                    except GeneratorExit:
                        break
                    except Exception as e:
                        yield f'data: {{"percent": 0, "step": "Error", "done": true, "error": "{str(e)}"}}\n\n'
                        break

            except Exception as e:
                yield f'data: {{"percent": 0, "step": "Connection error", "done": true, "error": "{str(e)}"}}\n\n'

        return Response(
            event_stream(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'
            }
        )

    def report(self):
        """Report display page."""
        template_vars = self.get_template_vars()
        template_name = getattr(self.config, 'report_template', 'report_template.html')
        return render_template(template_name, **template_vars)

    def report_data(self):
        """Return report data as JSON."""
        try:
            job_id = request.args.get('job_id') or session.get('job_id')
            if not job_id:
                return jsonify({'success': False, 'error': 'No job_id provided'}), 404

            analysis_result = get_analysis_result(job_id)
            if not analysis_result:
                return jsonify({'success': False, 'error': 'No analysis result found'}), 404

            # Serialize the report data
            report_data = analysis_result.get('report_data', {})
            metadata = analysis_result.get('metadata', {})
            ai_insights = analysis_result.get('ai_insights', {})

            return jsonify({
                'success': True,
                'data': ensure_json_serializable(serialize_dataframes(report_data)),
                'metadata': ensure_json_serializable(metadata),
                'ai_insights': ensure_json_serializable(ai_insights)
            })

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    def download(self):
        """Handle report downloads in various formats."""
        try:
            format_type = request.args.get('format', 'excel')
            job_id = request.args.get('job_id') or session.get('job_id')

            if not job_id:
                return jsonify({'success': False, 'error': 'No job_id provided'}), 404

            analysis_result = get_analysis_result(job_id)
            if not analysis_result:
                return jsonify({'success': False, 'error': 'No analysis result found'}), 404

            if format_type == 'excel':
                return self.download_excel(analysis_result)
            elif format_type == 'pdf':
                return self.download_pdf(analysis_result)
            elif format_type == 'csv':
                return self.download_csv(analysis_result)
            elif format_type == 'json':
                return self.download_json(analysis_result)
            else:
                return jsonify({'success': False, 'error': f'Unknown format: {format_type}'}), 400

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    # =========================================================================
    # Default Download Implementations
    # =========================================================================

    def download_pdf(self, analysis_result: Dict[str, Any]):
        """Default PDF download - subclasses can override."""
        return jsonify({'success': False, 'error': 'PDF download not implemented'}), 501

    def download_csv(self, analysis_result: Dict[str, Any]):
        """Default CSV download - exports first DataFrame."""
        try:
            import pandas as pd

            report_data = analysis_result.get('report_data', {})
            metadata = analysis_result.get('metadata', {})

            # Find the first DataFrame
            df = None
            for key, value in report_data.items():
                if isinstance(value, pd.DataFrame):
                    df = value
                    break
                elif isinstance(value, list) and len(value) > 0:
                    df = pd.DataFrame(value)
                    break

            if df is None:
                return jsonify({'success': False, 'error': 'No data to export'}), 404

            # Create temp file
            tmp_fd, tmp_path = tempfile.mkstemp(suffix='.csv')
            os.close(tmp_fd)
            df.to_csv(tmp_path, index=False)

            # Generate filename
            filename = self._generate_filename(metadata, '.csv')

            response = send_file(
                tmp_path,
                as_attachment=True,
                download_name=filename,
                mimetype='text/csv'
            )

            @response.call_on_close
            def cleanup():
                try:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                except:
                    pass

            return response

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    def download_json(self, analysis_result: Dict[str, Any]):
        """Default JSON download."""
        try:
            metadata = analysis_result.get('metadata', {})
            filename = self._generate_filename(metadata, '.json')

            # Serialize all data
            export_data = {
                'report_data': ensure_json_serializable(
                    serialize_dataframes(analysis_result.get('report_data', {}))
                ),
                'metadata': ensure_json_serializable(metadata),
                'ai_insights': ensure_json_serializable(
                    analysis_result.get('ai_insights', {})
                )
            }

            response = jsonify(export_data)
            response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    def _generate_filename(self, metadata: Dict[str, Any], extension: str) -> str:
        """Generate a filename from metadata."""
        from datetime import datetime

        parts = [self.app_name]

        # Add location info if available
        if metadata.get('county_name'):
            parts.append(metadata['county_name'].replace(' ', '_'))
        elif metadata.get('state_name'):
            parts.append(metadata['state_name'].replace(' ', '_'))

        # Add date
        parts.append(datetime.now().strftime('%Y%m%d'))

        return '_'.join(parts) + extension

    # =========================================================================
    # Abstract Methods - Must be implemented by subclasses
    # =========================================================================

    @abstractmethod
    def run_analysis(self, data: Dict[str, Any], job_id: str, progress_tracker: Any) -> Dict[str, Any]:
        """
        Execute the main analysis.

        Args:
            data: Form data from the request
            job_id: Unique job identifier
            progress_tracker: Progress tracker instance

        Returns:
            Dictionary with 'success', 'report_data', 'metadata', 'ai_insights'
        """
        pass

    @abstractmethod
    def download_excel(self, analysis_result: Dict[str, Any]):
        """
        Generate and return Excel download.

        Args:
            analysis_result: The analysis result dictionary

        Returns:
            Flask response with Excel file
        """
        pass

    @abstractmethod
    def get_template_vars(self) -> Dict[str, Any]:
        """
        Get template variables for rendering.

        Returns:
            Dictionary of template variables
        """
        pass

    def get_progress_steps(self) -> Dict[str, int]:
        """
        Get progress step configuration.
        Override to customize progress steps.

        Returns:
            Dictionary mapping step names to percentage weights
        """
        return {
            'initializing': 5,
            'fetching_data': 25,
            'processing': 20,
            'building_report': 25,
            'ai_analysis': 20,
            'finalizing': 5
        }
