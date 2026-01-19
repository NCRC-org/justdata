"""
Report generator module for LenderProfile blueprint.
Provides the generate_report function for creating lender intelligence reports.
"""

import uuid
import threading
import logging
from typing import Dict, Any

from justdata.shared.utils.progress_tracker import create_progress_tracker, store_analysis_result

logger = logging.getLogger(__name__)


def generate_report(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a comprehensive lender intelligence report with progress tracking.

    Args:
        data: Dictionary containing:
            - name: Institution name (required if no id)
            - id: Institution ID - FDIC cert, RSSD, LEI, etc. (required if no name)
            - identifiers: Dict of known identifiers (optional)
            - report_focus: Optional focus/emphasis for the report

    Returns:
        Dictionary with:
            - success: True if report generation started successfully
            - report_id: UUID for tracking progress and retrieving report
            - institution: Name of the institution
            - error: Error message if failed
    """
    from .processors.identifier_resolver import IdentifierResolver
    from .processors.data_collector import DataCollector
    from .report_builder.report_builder import ReportBuilder

    institution_name = data.get('name', '').strip()
    institution_id = data.get('id')
    identifiers = data.get('identifiers', {})
    report_focus = data.get('report_focus', '').strip()

    if not institution_name and not institution_id:
        raise ValueError('Institution name or ID is required')

    # If institution_id provided but identifiers is empty, try to use it
    if institution_id and not identifiers:
        institution_id = str(institution_id).strip()
        # Detect ID type and populate identifiers
        if len(institution_id) == 20 and institution_id.isalnum():
            # LEI is 20 alphanumeric characters
            identifiers = {'lei': institution_id}
            logger.info(f"Using provided ID as LEI: {institution_id}")
        elif institution_id.isdigit():
            # Numeric ID - could be RSSD or FDIC CERT
            identifiers = {'rssd_id': institution_id}
            logger.info(f"Using provided ID as RSSD: {institution_id}")
        else:
            # Try as generic ID
            identifiers = {'id': institution_id}
            logger.info(f"Using provided ID as generic: {institution_id}")

    # Validate report focus length
    if report_focus and len(report_focus) > 250:
        raise ValueError('Report focus must be 250 characters or less')

    # Create job ID
    job_id = str(uuid.uuid4())

    try:
        progress_tracker = create_progress_tracker(job_id)
        progress_tracker.update_progress('initializing', 0, 'Initializing lender intelligence report...')
    except Exception as e:
        logger.error(f"Error creating progress tracker: {e}", exc_info=True)
        raise RuntimeError(f'Failed to create progress tracker: {str(e)}')

    def run_job():
        """Run report generation in background thread."""
        nonlocal identifiers
        try:
            # Update progress
            progress_tracker.update_progress('parsing_params', 5, 'Preparing analysis...')

            # CRITICAL: Resolve LEI if not provided - required for HMDA and GLEIF lookups
            if not identifiers.get('lei'):
                logger.info(f"No LEI provided, resolving from name: {institution_name}")
                try:
                    resolver = IdentifierResolver()
                    candidates = resolver.get_candidates_with_location(institution_name, limit=1)
                    if candidates and candidates[0].get('lei'):
                        identifiers['lei'] = candidates[0]['lei']
                        logger.info(f"Resolved LEI: {identifiers['lei']}")
                        # Also fill in other identifiers if missing
                        if not identifiers.get('rssd_id') and candidates[0].get('rssd_id'):
                            identifiers['rssd_id'] = candidates[0]['rssd_id']
                        if not identifiers.get('fdic_cert') and candidates[0].get('fdic_cert'):
                            identifiers['fdic_cert'] = candidates[0]['fdic_cert']
                    else:
                        logger.warning(f"Could not resolve LEI for {institution_name}")
                except Exception as e:
                    logger.error(f"Error resolving LEI: {e}")

            # Collect all data from APIs
            logger.info(f"Starting data collection for {institution_name}")
            logger.info(f"Using identifiers: LEI={identifiers.get('lei')}, RSSD={identifiers.get('rssd_id')}, FDIC={identifiers.get('fdic_cert')}")
            progress_tracker.update_progress('preparing_data', 15, 'Collecting data from regulatory sources...')

            collector = DataCollector()
            institution_data = collector.collect_all_data(identifiers, institution_name)

            # Build complete report
            logger.info(f"Building report for {institution_name}")
            progress_tracker.update_progress('building_report', 60, 'Building report sections...')

            report_builder = ReportBuilder(report_focus=report_focus if report_focus else None)
            report = report_builder.build_complete_report(institution_data, progress_tracker=progress_tracker)

            progress_tracker.update_progress('finalizing', 95, 'Finalizing report...')

            # Store report result
            store_analysis_result(job_id, {
                'success': True,
                'report': report,
                'institution': institution_name,
                'metadata': {
                    'institution_name': institution_name,
                    'generated_at': report.get('metadata', {}).get('generated_at'),
                    'report_focus': report_focus
                }
            })

            progress_tracker.complete(success=True)
            logger.info(f"Report generation completed for {institution_name}")

        except Exception as e:
            logger.error(f"Error in report generation job: {e}", exc_info=True)
            progress_tracker.complete(success=False, error=str(e))
            store_analysis_result(job_id, {
                'success': False,
                'error': str(e)
            })

    # Start job in background thread
    thread = threading.Thread(target=run_job, daemon=True)
    thread.start()

    return {
        'success': True,
        'report_id': job_id,
        'institution': institution_name
    }
