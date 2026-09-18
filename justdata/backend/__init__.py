"""Shared backend for the report apps.

LendSight, BizSight, BranchSight and MergerMeter were each built separately and
grew their own copies of the same plumbing: background job handling, SSE progress
streaming, analysis-cache lookups and usage logging. This package owns that once
so the blueprints are left with routing and their own analysis.

Blueprints should import from here rather than from shared.utils.analysis_cache
or shared.utils.progress_tracker directly.
"""

from justdata.backend.jobs import new_job_id, run_in_background, sse_response
from justdata.backend.reports import (
    Caller,
    CachedAnalysis,
    identify_caller,
    lookup_cached_analysis,
    record_cache_hit,
    record_completion,
)

__all__ = [
    'new_job_id',
    'run_in_background',
    'sse_response',
    'Caller',
    'CachedAnalysis',
    'identify_caller',
    'lookup_cached_analysis',
    'record_cache_hit',
    'record_completion',
]
