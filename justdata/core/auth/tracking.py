"""
Authentication Tracking Middleware

Logs user sign-ins to HubSpot for member activity tracking.
"""

import os
from typing import Optional
from fastapi import Request
import structlog

from justdata.apps.hubspot.tracking import UserActivityTracker

logger = structlog.get_logger(__name__)


async def log_user_signin(
    request: Request,
    user_email: str,
    user_id: Optional[str] = None
) -> dict:
    """
    Log user sign-in to HubSpot.
    
    Call this after successful authentication.
    
    Args:
        request: FastAPI request object
        user_email: User's email address
        user_id: Optional user ID from your system
        
    Returns:
        Result of tracking operation
    """
    # Only track if HubSpot sync is enabled
    if not os.getenv("HUBSPOT_SYNC_ENABLED", "False").lower() == "true":
        logger.info("HubSpot tracking disabled, skipping sign-in log")
        return {"success": False, "reason": "tracking_disabled"}
    
    try:
        # Get metadata from request
        metadata = {
            "ip_address": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
            "path": str(request.url.path),
            "method": request.method
        }
        
        # Track the sign-in
        tracker = UserActivityTracker()
        result = await tracker.log_user_signin(
            user_email=user_email,
            user_id=user_id,
            session_id=request.headers.get("x-session-id"),
            metadata=metadata
        )
        
        logger.info(
            "User sign-in tracked",
            email=user_email,
            success=result.get("success")
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "Failed to track user sign-in",
            error=str(e),
            email=user_email
        )
        # Don't fail authentication if tracking fails
        return {"success": False, "error": str(e)}


async def log_tool_usage(
    user_email: str,
    tool_name: str,
    action: str,
    details: Optional[dict] = None
) -> dict:
    """
    Log tool usage to HubSpot.
    
    Call this when users perform actions in JustData.
    
    Args:
        user_email: User's email
        tool_name: Tool being used (branchsight, lendsight, bizsight)
        action: Action performed (generate_report, run_analysis, etc.)
        details: Optional additional details
        
    Returns:
        Result of tracking operation
    """
    # Only track if enabled
    if not os.getenv("HUBSPOT_SYNC_ENABLED", "False").lower() == "true":
        return {"success": False, "reason": "tracking_disabled"}
    
    try:
        tracker = UserActivityTracker()
        result = await tracker.log_tool_usage(
            user_email=user_email,
            tool_name=tool_name,
            action=action,
            details=details
        )
        
        logger.info(
            "Tool usage tracked",
            email=user_email,
            tool=tool_name,
            action=action,
            success=result.get("success")
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "Failed to track tool usage",
            error=str(e),
            email=user_email,
            tool=tool_name
        )
        return {"success": False, "error": str(e)}

