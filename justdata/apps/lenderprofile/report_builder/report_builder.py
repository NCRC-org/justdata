#!/usr/bin/env python3
"""
Main Report Builder for LenderProfile
Orchestrates all section builders and generates complete intelligence report.
Uses two-column layout with intelligence-focused sections.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from justdata.apps.lenderprofile.processors.ai_summarizer import LenderProfileAnalyzer
from justdata.apps.lenderprofile.report_builder.section_builders_v2 import build_complete_report_v2

logger = logging.getLogger(__name__)


class ReportBuilder:
    """
    Main report builder that orchestrates all section builders.
    Uses two-column intelligence-focused layout.
    """

    def __init__(self, report_focus: Optional[str] = None):
        """
        Initialize report builder.

        Args:
            report_focus: Optional user-specified focus (max 250 chars)
        """
        self.report_focus = report_focus
        self.ai_analyzer = LenderProfileAnalyzer()

    def build_complete_report(self, institution_data: Dict[str, Any], progress_tracker=None) -> Dict[str, Any]:
        """
        Build complete lender intelligence report using two-column layout.

        Left Column:
        - Business Strategy (SEC 10-K)
        - Risk Factors
        - Financial Performance
        - M&A Activity
        - Regulatory Risk
        - Branch Network
        - Lending Footprint

        Right Column:
        - Leadership & Compensation
        - Congressional Trading
        - Corporate Structure
        - Recent News

        Full Width:
        - AI Intelligence Summary

        Args:
            institution_data: Complete institution data from all APIs
            progress_tracker: Optional progress tracker for progress updates

        Returns:
            Complete report dictionary with all sections
        """
        institution_name = institution_data.get('institution', {}).get('name', 'Unknown')
        logger.info(f"Building complete report for {institution_name}")

        if progress_tracker:
            progress_tracker.update_progress('building_report', 60, 'Building report sections...')

        try:
            # Build the complete report using the v2 section builder
            # Pass congressional trading data from data collector
            congressional_data = institution_data.get('congressional_trading', {})

            report = build_complete_report_v2(
                institution_data=institution_data,
                ai_analyzer=self.ai_analyzer,
                report_focus=self.report_focus,
                congressional_data=congressional_data
            )

            if progress_tracker:
                progress_tracker.update_progress('building_report', 95, 'Finalizing report...')

            # Add metadata
            report['metadata'] = {
                'generated_at': datetime.now().isoformat(),
                'institution': institution_data.get('institution', {}),
                'identifiers': institution_data.get('identifiers', {}),
                'report_focus': self.report_focus,
                'version': 'v2',
                'layout': 'two-column'
            }

            if progress_tracker:
                progress_tracker.update_progress('building_report', 100, 'Report complete!')

            logger.info("Report building complete")
            return report

        except Exception as e:
            logger.error(f"Error building report: {e}", exc_info=True)
            if progress_tracker:
                progress_tracker.update_progress('error', 100, f'Error: {str(e)}')
            return {
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'error': str(e)
                },
                'error': str(e)
            }
