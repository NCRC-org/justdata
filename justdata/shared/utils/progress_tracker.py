#!/usr/bin/env python3
"""
Progress tracking utility for real-time progress updates during analysis.
Shared across BranchSight, BizSight, and LendSight.
"""

from typing import Dict, Any, Optional
import time
import json
import os
from pathlib import Path


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
# Store with timestamps for cleanup: {job_id: {'data': {...}, 'timestamp': float}}
progress_store = {}
analysis_results_store = {}

# File-based persistent storage for progress (survives gunicorn restarts)
# Use environment variable or default to /tmp/progress on Render
_progress_storage_dir = None
def _get_progress_storage_dir() -> Path:
    """Get or create progress storage directory."""
    global _progress_storage_dir
    if _progress_storage_dir is None:
        try:
            storage_dir = Path(os.getenv('PROGRESS_STORAGE_DIR', '/tmp/progress'))
            storage_dir.mkdir(parents=True, exist_ok=True)
            _progress_storage_dir = storage_dir
        except Exception as e:
            # If we can't create the directory, disable file storage
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Could not create progress storage directory: {e}. File-based persistence disabled.")
            _progress_storage_dir = None
    return _progress_storage_dir

PROGRESS_STORAGE_DIR = _get_progress_storage_dir()

# Maximum age for job data in seconds (1 hour)
MAX_JOB_AGE = 3600
# Maximum number of jobs to keep in memory
MAX_JOBS = 100

def _get_progress_file_path(job_id: str) -> Optional[Path]:
    """Get file path for storing progress data."""
    storage_dir = _get_progress_storage_dir()
    if storage_dir is None:
        return None
    return storage_dir / f"progress_{job_id}.json"

def _get_result_file_path(job_id: str) -> Optional[Path]:
    """Get file path for storing analysis result."""
    storage_dir = _get_progress_storage_dir()
    if storage_dir is None:
        return None
    # Use .pkl extension for pickle format (preserves complex nested structures)
    return storage_dir / f"result_{job_id}.pkl"

def _load_progress_from_file(job_id: str) -> Optional[Dict[str, Any]]:
    """Load progress data from file."""
    try:
        file_path = _get_progress_file_path(job_id)
        if file_path is None:
            return None
        if file_path.exists():
            with open(file_path, 'r') as f:
                data = json.load(f)
                # Check if data is expired
                if 'timestamp' in data:
                    age = time.time() - data['timestamp']
                    if age > MAX_JOB_AGE:
                        # Expired, delete file
                        file_path.unlink()
                        return None
                return data
    except Exception as e:
        # Log but don't fail - file might be corrupted or locked
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error loading progress from file for {job_id}: {e}")
    return None

def _save_progress_to_file(job_id: str, progress_data: Dict[str, Any]):
    """Save progress data to file."""
    try:
        file_path = _get_progress_file_path(job_id)
        if file_path is None:
            return  # File storage disabled
        data = {
            'data': progress_data,
            'timestamp': time.time()
        }
        with open(file_path, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        # Log but don't fail - file write might fail
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error saving progress to file for {job_id}: {e}")

def _load_result_from_file(job_id: str) -> Optional[Dict[str, Any]]:
    """Load analysis result from file."""
    try:
        file_path = _get_result_file_path(job_id)
        if file_path is None:
            return None
        
        # Try pickle format first (new format)
        if file_path.exists():
            import pickle
            try:
                with open(file_path, 'rb') as f:
                    data = pickle.load(f)
            except (pickle.UnpicklingError, UnicodeDecodeError, FileNotFoundError):
                # Fall back to JSON for old format files (backward compatibility)
                json_path = file_path.parent / f"result_{job_id}.json"
                if json_path.exists():
                    with open(json_path, 'r') as f:
                        data = json.load(f)
                else:
                    return None
            
            # Check if data is expired
            if 'timestamp' in data:
                age = time.time() - data['timestamp']
                if age > MAX_JOB_AGE:
                    # Expired, delete file
                    file_path.unlink()
                    return None
            return data
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error loading result from file for {job_id}: {e}")
    return None

def _save_result_to_file(job_id: str, result: Dict[str, Any]):
    """Save analysis result to file."""
    try:
        file_path = _get_result_file_path(job_id)
        if file_path is None:
            return  # File storage disabled
        data = {
            'data': result,
            'timestamp': time.time()
        }
        # Use pickle instead of JSON to preserve complex nested structures (like historical_census_data)
        import pickle
        with open(file_path, 'wb') as f:
            pickle.dump(data, f)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error saving result to file for {job_id}: {e}")

def _cleanup_old_jobs():
    """Remove old jobs from stores to prevent memory leaks."""
    current_time = time.time()
    jobs_to_remove = []
    
    # Clean up progress_store
    for job_id, job_data in list(progress_store.items()):
        if isinstance(job_data, dict) and 'timestamp' in job_data:
            # New format with timestamp
            if current_time - job_data['timestamp'] > MAX_JOB_AGE:
                jobs_to_remove.append(job_id)
        elif isinstance(job_data, dict) and 'done' in job_data:
            # Old format - check if done and older than 5 minutes
            if job_data.get('done', False):
                # Mark with timestamp if not already marked
                progress_store[job_id] = {'data': job_data, 'timestamp': current_time - MAX_JOB_AGE + 300}
    
    # Clean up analysis_results_store
    for job_id in jobs_to_remove:
        progress_store.pop(job_id, None)
        analysis_results_store.pop(job_id, None)
    
    # If we still have too many jobs, remove oldest ones
    if len(progress_store) > MAX_JOBS:
        # Sort by timestamp and remove oldest
        jobs_with_times = []
        for job_id, job_data in progress_store.items():
            if isinstance(job_data, dict) and 'timestamp' in job_data:
                jobs_with_times.append((job_id, job_data['timestamp']))
            else:
                # Old format - treat as very old
                jobs_with_times.append((job_id, 0))
        
        jobs_with_times.sort(key=lambda x: x[1])
        excess = len(progress_store) - MAX_JOBS
        for job_id, _ in jobs_with_times[:excess]:
            progress_store.pop(job_id, None)
            analysis_results_store.pop(job_id, None)

def get_progress(job_id: str) -> Dict[str, Any]:
    """Get current progress for a job."""
    # Periodically clean up old jobs (every 10th call)
    if len(progress_store) > 0 and hash(job_id) % 10 == 0:
        _cleanup_old_jobs()
    
    # First check in-memory store
    job_data = progress_store.get(job_id)
    
    # If not in memory, try loading from file (survives gunicorn restarts)
    if job_data is None:
        file_data = _load_progress_from_file(job_id)
        if file_data:
            # Restore to memory store
            progress_store[job_id] = file_data
            job_data = file_data
    
    if job_data is None:
        # Job not found - return a "processing" state instead of "initializing"
        # This indicates the job might be running but progress was lost
        return {
            'step': 'Processing...',
            'percent': 0,
            'done': False,
            'error': None
        }
    
    # Handle both old format (direct dict) and new format (with timestamp)
    if isinstance(job_data, dict) and 'data' in job_data:
        return job_data['data']
    else:
        return job_data

def update_progress(job_id: str, progress_data: Dict[str, Any]):
    """Update progress for a job."""
    # Store with timestamp for cleanup
    job_data = {
        'data': progress_data,
        'timestamp': time.time()
    }
    progress_store[job_id] = job_data
    
    # Also save to file for persistence across gunicorn restarts
    _save_progress_to_file(job_id, progress_data)
    
    # Clean up old jobs periodically
    if len(progress_store) > MAX_JOBS:
        _cleanup_old_jobs()

def create_progress_tracker(job_id: str, steps_config: Dict[str, Dict] = None) -> ProgressTracker:
    """Create a progress tracker for a job."""
    def progress_callback(job_id: str, data: Dict[str, Any]):
        update_progress(job_id, data)
    
    return ProgressTracker(job_id, progress_callback, steps_config)

def store_analysis_result(job_id: str, result: Dict[str, Any]):
    """Store analysis result for a job."""
    # Debug: Log historical_census_data structure before storing
    if 'historical_census_data' in result:
        import logging
        logger = logging.getLogger(__name__)
        hist_data = result['historical_census_data']
        if hist_data:
            logger.info(f"[DEBUG] Storing historical_census_data with {len(hist_data)} counties")
            if len(hist_data) > 0:
                first_geoid = list(hist_data.keys())[0]
                first_county = hist_data[first_geoid]
                logger.info(f"[DEBUG] Storing - Sample county ({first_geoid}) type: {type(first_county)}")
                logger.info(f"[DEBUG] Storing - Sample county ({first_geoid}) keys: {list(first_county.keys()) if isinstance(first_county, dict) else 'Not a dict'}")
                if isinstance(first_county, dict) and 'time_periods' in first_county:
                    logger.info(f"[DEBUG] Storing - time_periods keys: {list(first_county['time_periods'].keys())}")
                else:
                    logger.warning(f"[DEBUG] Storing - time_periods missing! County data: {first_county}")
    
    result_data = {
        'data': result,
        'timestamp': time.time()
    }
    analysis_results_store[job_id] = result_data
    
    # Also save to file for persistence across gunicorn restarts
    _save_result_to_file(job_id, result)
    
    # Clean up old jobs periodically
    if len(analysis_results_store) > MAX_JOBS:
        _cleanup_old_jobs()

def get_analysis_result(job_id: str) -> Optional[Dict[str, Any]]:
    """Get analysis result for a job."""
    import logging
    logger = logging.getLogger(__name__)
    
    # First check in-memory store
    job_data = analysis_results_store.get(job_id)
    
    # If not in memory, try loading from file (survives gunicorn restarts)
    if job_data is None:
        file_data = _load_result_from_file(job_id)
        if file_data:
            # Restore to memory store
            analysis_results_store[job_id] = file_data
            job_data = file_data
    
    if job_data is None:
        return None
    
    # Handle both old format (direct dict) and new format (with timestamp)
    if isinstance(job_data, dict) and 'data' in job_data:
        result = job_data['data']
    else:
        result = job_data
    
    # Debug: Log historical_census_data structure after loading
    if 'historical_census_data' in result:
        hist_data = result['historical_census_data']
        if hist_data:
            logger.info(f"[DEBUG] Loaded historical_census_data with {len(hist_data)} counties")
            if len(hist_data) > 0:
                first_geoid = list(hist_data.keys())[0]
                first_county = hist_data[first_geoid]
                logger.info(f"[DEBUG] Loaded - Sample county ({first_geoid}) type: {type(first_county)}")
                logger.info(f"[DEBUG] Loaded - Sample county ({first_geoid}) keys: {list(first_county.keys()) if isinstance(first_county, dict) else 'Not a dict'}")
                if isinstance(first_county, dict) and 'time_periods' in first_county:
                    logger.info(f"[DEBUG] Loaded - time_periods keys: {list(first_county['time_periods'].keys())}")
                else:
                    logger.warning(f"[DEBUG] Loaded - time_periods missing! County data: {first_county}")
    
    return result

def cleanup_job(job_id: str):
    """Explicitly remove a job from stores."""
    progress_store.pop(job_id, None)
    analysis_results_store.pop(job_id, None)
    
    # Also remove from file storage
    try:
        progress_file = _get_progress_file_path(job_id)
        if progress_file.exists():
            progress_file.unlink()
        result_file = _get_result_file_path(job_id)
        if result_file.exists():
            result_file.unlink()
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error cleaning up files for {job_id}: {e}")

