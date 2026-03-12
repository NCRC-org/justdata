"""
HubSpot User Activity Tracking

Track when members sign in and use JustData.
Members are already in HubSpot Lists - we just log their activity.
"""

import os
from typing import Dict, Optional, Any
from datetime import datetime
import structlog
import httpx

from .client import HubSpotClient

logger = structlog.get_logger(__name__)


class UserActivityTracker:
    """Track user activity in HubSpot."""

    def __init__(self, access_token: Optional[str] = None):
        self.client = HubSpotClient(access_token=access_token)

    async def log_user_signin(
        self,
        user_email: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Log when a user signs in to JustData."""
        logger.info("Logging user sign-in", email=user_email)

        try:
            contact = await self._find_contact_by_email(user_email)

            if not contact:
                logger.warning("User not found in HubSpot", email=user_email)
                return {"success": False, "error": "Contact not found in HubSpot"}

            contact_id = contact["id"]

            note_content = self._build_signin_note(
                user_email=user_email,
                user_id=user_id,
                session_id=session_id,
                metadata=metadata,
            )

            engagement = await self.client.create_note(contact_id, note_content)
            await self._update_last_activity(contact, user_id, session_id)

            logger.info(
                "User sign-in logged successfully",
                contact_id=contact_id,
                engagement_id=engagement.get("id"),
            )

            return {
                "success": True,
                "contact_id": contact_id,
                "engagement_id": engagement.get("id"),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error("Failed to log user sign-in", error=str(e), email=user_email)
            return {"success": False, "error": str(e)}

    async def log_tool_usage(
        self,
        user_email: str,
        tool_name: str,
        action: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Log when a user uses a specific tool/feature."""
        logger.info("Logging tool usage", email=user_email, tool=tool_name, action=action)

        try:
            contact = await self._find_contact_by_email(user_email)

            if not contact:
                logger.warning("User not found", email=user_email)
                return {"success": False, "error": "Contact not found"}

            contact_id = contact["id"]

            note_content = self._build_usage_note(
                tool_name=tool_name, action=action, details=details
            )

            engagement = await self.client.create_note(contact_id, note_content)
            await self._increment_usage_counter(contact, tool_name)

            logger.info("Tool usage logged successfully", contact_id=contact_id, tool=tool_name)

            return {
                "success": True,
                "contact_id": contact_id,
                "engagement_id": engagement.get("id"),
                "tool": tool_name,
                "action": action,
            }

        except Exception as e:
            logger.error(
                "Failed to log tool usage", error=str(e), email=user_email
            )
            return {"success": False, "error": str(e)}

    async def get_user_activity(
        self, user_email: str, limit: int = 50
    ) -> Dict[str, Any]:
        """Get activity history for a user."""
        try:
            contact = await self._find_contact_by_email(user_email)
            if not contact:
                return {"success": False, "error": "Contact not found"}

            properties = contact.get("properties", {})

            return {
                "success": True,
                "contact_id": contact["id"],
                "email": user_email,
                "last_signin": properties.get("justdata_last_signin"),
                "total_signins": properties.get("justdata_signin_count", 0),
                "last_tool_used": properties.get("justdata_last_tool"),
            }

        except Exception as e:
            logger.error("Failed to get user activity", error=str(e))
            return {"success": False, "error": str(e)}

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    async def _find_contact_by_email(self, email: str) -> Optional[Dict]:
        """Find contact by email address."""
        contacts = await self.client.search_contacts(
            [{"propertyName": "email", "operator": "EQ", "value": email}],
            limit=1,
        )
        return contacts[0] if contacts else None

    async def _update_last_activity(
        self,
        contact: Dict[str, Any],
        user_id: Optional[str],
        session_id: Optional[str],
    ) -> None:
        """Update contact with last activity timestamp (read-then-write for counters)."""
        contact_id = contact["id"]
        props = contact.get("properties", {})
        current_count = int(props.get("justdata_signin_count", 0) or 0)

        properties: Dict[str, Any] = {
            "justdata_last_signin": datetime.now().isoformat(),
            "justdata_signin_count": str(current_count + 1),
        }

        if user_id:
            properties["justdata_user_id"] = user_id
        if session_id:
            properties["justdata_last_session"] = session_id

        await self.client.update_contact(contact_id, properties)

    async def _increment_usage_counter(
        self, contact: Dict[str, Any], tool_name: str
    ) -> None:
        """Increment usage counter for a specific tool (read-then-write)."""
        contact_id = contact["id"]
        props = contact.get("properties", {})
        tool_count_field = f"justdata_{tool_name}_count"
        current_count = int(props.get(tool_count_field, 0) or 0)

        properties = {
            "justdata_last_tool": tool_name,
            "justdata_last_activity": datetime.now().isoformat(),
            tool_count_field: str(current_count + 1),
        }

        await self.client.update_contact(contact_id, properties)

    def _build_signin_note(
        self,
        user_email: str,
        user_id: Optional[str],
        session_id: Optional[str],
        metadata: Optional[Dict[str, Any]],
    ) -> str:
        lines = [
            "=== JustData Sign-In ===",
            f"Email: {user_email}",
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ]
        if user_id:
            lines.append(f"User ID: {user_id}")
        if session_id:
            lines.append(f"Session: {session_id}")
        if metadata:
            lines.append("\nAdditional Info:")
            for key, value in metadata.items():
                lines.append(f"  {key}: {value}")
        return "\n".join(lines)

    def _build_usage_note(
        self,
        tool_name: str,
        action: str,
        details: Optional[Dict[str, Any]],
    ) -> str:
        lines = [
            f"=== JustData Usage: {tool_name} ===",
            f"Action: {action}",
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ]
        if details:
            lines.append("\nDetails:")
            for key, value in details.items():
                lines.append(f"  {key}: {value}")
        return "\n".join(lines)
