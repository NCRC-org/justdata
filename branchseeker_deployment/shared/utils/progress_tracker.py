#!/usr/bin/env python3
"""
Progress tracking utility for real-time progress updates during analysis.
Shared across BranchSeeker, BizSight, and LendSight.
"""

from typing import Dict, Any, Optional


class ProgressTracker:
    """Tracks and reports progress during analysis."""
    
    def __init__(self, job_id: str, progress_callback=None, steps_config: Dict[str, Dict] = None):
        """Initialize the progress tracker."""
        self.job_id = job_id
        self.progress_callback = progress_callback
        self.current_step = "Initializing..."
        self.current_percent = 0
        self.total_steps = 0
        self.completed_steps = 0
        
        # Define the analysis steps with their progress percentages
        self.steps = steps_config or {
            'initializing': {'name': 'Initializing analysis...', 'percent': 0},
            'parsing_params': {'name': 'Parsing parameters...', 'percent': 5},
            'preparing_data': {'name': 'Preparing data...', 'percent': 15},
            'connecting_db': {'name': 'Connecting to database...', 'percent': 20},
            'querying_data': {'name': 'Querying data...', 'percent': 35},
            'processing_data': {'name': 'Processing information...', 'percent': 50},
            'building_report': {'name': 'Building report...', 'percent': 65},
            'generating_ai': {'name': 'Generating AI insights...', 'percent': 80},
            'finalizing': {'name': 'Finalizing...', 'percent': 95},
            'completed': {'name': 'Analysis completed!', 'percent': 100}
        }
    
    def update_progress(self, step: str, percent: Optional[int] = None, message: Optional[str] = None):
        """Update progress for a specific step."""
        if step in self.steps:
            step_info = self.steps[step]
            self.current_step = message or step_info['name']
            self.current_percent = percent if percent is not None else step_info['percent']
            
            # Call the callback if provided
            if self.progress_callback:
                self.progress_callback(self.job_id, {
                    'step': self.current_step,
                    'percent': self.current_percent,
                    'done': False,
                    'error': None
                })
    
    def update_query_progress(self, current_query: int, total_queries: int):
        """Update progress during database queries."""
        # Query progress is between 35% and 50%
        query_percent = 35 + (current_query / total_queries) * 15
        self.update_progress('querying_data', int(query_percent), 
                           f"Querying data... ({current_query}/{total_queries})")
    
    def update_ai_progress(self, current_call: int, total_calls: int, insight_name: str = None):
        """Update progress during AI analysis."""
        # AI progress is between 80% and 95%
        ai_percent = 80 + (current_call / total_calls) * 15
        
        if insight_name:
            # Show just the section name with progress, e.g., "Trends Analysis (3/3)"
            message = f"{insight_name} ({current_call}/{total_calls})"
        else:
            message = f"Generating AI insights... ({current_call}/{total_calls})"
            
        self.update_progress('generating_ai', int(ai_percent), message)
    
    def update_section_progress(self, current_section: int, total_sections: int, section_name: str):
        """Update progress during report section building."""
        # Section building progress is between 60% and 80%
        section_percent = 60 + (current_section / total_sections) * 20
        message = f"{section_name} ({current_section}/{total_sections})"
        self.update_progress('building_report', int(section_percent), message)
    
    def complete(self, success: bool = True, error: Optional[str] = None):
        """Mark the analysis as completed."""
        if success:
            if self.progress_callback:
                self.progress_callback(self.job_id, {
                    'step': 'Analysis completed!',
                    'percent': 100,
                    'done': True,
                    'error': None
                })
        else:
            if self.progress_callback:
                self.progress_callback(self.job_id, {
                    'step': self.current_step,
                    'percent': self.current_percent,
                    'done': True,
                    'error': error
                })


# Global progress storage for web interface
progress_store = {}
analysis_results_store = {}

def get_progress(job_id: str) -> Dict[str, Any]:
    """Get current progress for a job."""
    return progress_store.get(job_id, {
        'step': 'Initializing...',
        'percent': 0,
        'done': False,
        'error': None
    })

def update_progress(job_id: str, progress_data: Dict[str, Any]):
    """Update progress for a job."""
    progress_store[job_id] = progress_data

def create_progress_tracker(job_id: str, steps_config: Dict[str, Dict] = None) -> ProgressTracker:
    """Create a progress tracker for a job."""
    def progress_callback(job_id: str, data: Dict[str, Any]):
        update_progress(job_id, data)
    
    return ProgressTracker(job_id, progress_callback, steps_config)

def store_analysis_result(job_id: str, result: Dict[str, Any]):
    """Store analysis result for a job."""
    analysis_results_store[job_id] = result

def get_analysis_result(job_id: str) -> Optional[Dict[str, Any]]:
    """Get analysis result for a job."""
    return analysis_results_store.get(job_id)

