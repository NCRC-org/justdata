"""Analysis-cache lookups and usage logging, shared by the report apps."""

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from flask import session

from justdata.main.auth import can_force_refresh, get_current_user, get_user_type
from justdata.shared.utils.analysis_cache import (
    generate_cache_key,
    get_cached_result,
    log_usage,
)
from justdata.shared.utils.progress_tracker import update_progress


@dataclass(frozen=True)
class Caller:
    """Who asked for the analysis, resolved while the request context exists."""
    user_type: str
    user_id: Optional[str] = None
    user_email: Optional[str] = None


@dataclass(frozen=True)
class CachedAnalysis:
    job_id: str
    cache_key: str
    result_data: Dict[str, Any]


def identify_caller() -> Caller:
    """Resolve the caller's tier and identity.

    Must be called inside the request context. Background workers get no request,
    so pass the returned Caller into them rather than calling this again.
    """
    user = get_current_user()
    user_id = user.get('uid') if user else None
    user_email = user.get('email') if user else None

    # Some sign-in paths populate the session without get_current_user seeing it.
    if not user_id and not user_email and 'firebase_user' in session:
        stored = session.get('firebase_user', {})
        user_id = stored.get('uid') or user_id
        user_email = stored.get('email') or user_email

    return Caller(user_type=get_user_type(), user_id=user_id, user_email=user_email)


def lookup_cached_analysis(app_name: str, params: Dict[str, Any], caller: Caller,
                           force_refresh_requested: bool = False) -> Optional[CachedAnalysis]:
    """Return a completed cached analysis, or None to run a fresh one.

    A cache bypass is honoured only for privileged users: regenerating costs a
    full BigQuery scan plus the AI narrative calls, so it stays staff-gated
    regardless of what the client sends.
    """
    if force_refresh_requested and can_force_refresh(caller.user_type):
        print(f"[INFO] {app_name}: force refresh requested, bypassing cache")
        return None

    cached = get_cached_result(app_name, params, caller.user_type)
    if not cached:
        return None

    return CachedAnalysis(
        job_id=cached['job_id'],
        cache_key=cached.get('cache_key') or generate_cache_key(app_name, params),
        result_data=cached.get('result_data') or {},
    )


def record_cache_hit(app_name: str, params: Dict[str, Any], caller: Caller,
                     cached: CachedAnalysis, started_at: float,
                     request_id: Optional[str] = None) -> None:
    """Mark the cached job complete and log the hit.

    The result already lives in BigQuery under this job_id, so /report-data
    resolves it without the analysis running again.
    """
    update_progress(cached.job_id, {
        'percent': 100,
        'step': 'Analysis complete (from cache)',
        'done': True,
        'cached': True,
    })

    _log(app_name, params, caller, cached.cache_key, True, cached.job_id,
         started_at, request_id, costs={'bigquery': 0.0, 'ai': 0.0, 'total': 0.0})


def record_completion(app_name: str, params: Dict[str, Any], caller: Caller,
                      job_id: str, started_at: float,
                      request_id: Optional[str] = None,
                      costs: Optional[Dict[str, float]] = None,
                      error_message: Optional[str] = None) -> None:
    """Log a freshly computed analysis, successful or failed.

    Safe to call from a worker thread. Pass error_message when the analysis
    failed, so the run still appears in usage reporting rather than vanishing.
    """
    _log(app_name, params, caller, generate_cache_key(app_name, params), False,
         job_id, started_at, request_id, costs=costs, error_message=error_message)


def _log(app_name, params, caller, cache_key, cache_hit, job_id, started_at,
         request_id, costs=None, error_message=None) -> None:
    # Usage logging is telemetry: a failure here must never surface as a failed
    # analysis to the user.
    try:
        log_usage(
            user_type=caller.user_type,
            app_name=app_name,
            params=params,
            cache_key=cache_key,
            cache_hit=cache_hit,
            job_id=job_id,
            response_time_ms=int((time.time() - started_at) * 1000),
            costs=costs,
            error_message=error_message,
            request_id=request_id,
            user_id=caller.user_id,
            user_email=caller.user_email,
        )
    except Exception as e:
        print(f"[WARN] {app_name}: failed to log usage for job {job_id}: {e}")
