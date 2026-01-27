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
    """
    Track user activity in HubSpot.
    
    Logs when users sign in and use the tool.
    """
    
    def __init__(self, access_token: Optional[str] = None):
        """Initialize activity tracker."""
        self.client = HubSpotClient(access_token=access_token)
    
    async def log_user_signin(
        self,
        user_email: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Log when a user signs in to JustData.
        
        Args:
            user_email: User's email address
            user_id: Optional user ID in your system
            session_id: Optional session identifier
            metadata: Additional metadata (IP, browser, etc.)
            
        Returns:
            Activity log result
        """
        logger.info(
            "Logging user sign-in",
            email=user_email,
            user_id=user_id,
            session_id=session_id
        )
        
        try:
            # Find contact by email
            contact = await self._find_contact_by_email(user_email)
            
            if not contact:
                logger.warning(
                    "User not found in HubSpot",
                    email=user_email
                )
                return {
                    "success": False,
                    "error": "Contact not found in HubSpot"
                }
            
            contact_id = contact["id"]
            
            # Create engagement note for sign-in
            note_content = self._build_signin_note(
                user_email=user_email,
                user_id=user_id,
                session_id=session_id,
                metadata=metadata
            )
            
            # Log the activity
            engagement = await self._create_engagement(
                contact_id=contact_id,
                engagement_type="NOTE",
                subject="JustData Sign-In",
                body=note_content
            )
            
            # Update contact properties with last activity
            await self._update_last_activity(contact_id, user_id, session_id)
            
            logger.info(
                "User sign-in logged successfully",
                contact_id=contact_id,
                engagement_id=engagement.get("id")
            )
            
            return {
                "success": True,
                "contact_id": contact_id,
                "engagement_id": engagement.get("id"),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(
                "Failed to log user sign-in",
                error=str(e),
                email=user_email
            )
            return {
                "success": False,
                "error": str(e)
            }
    
    async def log_tool_usage(
        self,
        user_email: str,
        tool_name: str,
        action: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Log when a user uses a specific tool/feature.
        
        Args:
            user_email: User's email
            tool_name: Name of tool used (branchsight, lendsight, bizsight)
            action: Action performed (generate_report, run_analysis, etc.)
            details: Additional details about the usage
            
        Returns:
            Usage log result
        """
        logger.info(
            "Logging tool usage",
            email=user_email,
            tool=tool_name,
            action=action
        )
        
        try:
            # Find contact
            contact = await self._find_contact_by_email(user_email)
            
            if not contact:
                logger.warning("User not found", email=user_email)
                return {"success": False, "error": "Contact not found"}
            
            contact_id = contact["id"]
            
            # Create usage note
            note_content = self._build_usage_note(
                tool_name=tool_name,
                action=action,
                details=details
            )
            
            # Log the activity
            engagement = await self._create_engagement(
                contact_id=contact_id,
                engagement_type="NOTE",
                subject=f"JustData Usage: {tool_name}",
                body=note_content
            )
            
            # Update usage counters
            await self._increment_usage_counter(contact_id, tool_name)
            
            logger.info(
                "Tool usage logged successfully",
                contact_id=contact_id,
                tool=tool_name
            )
            
            return {
                "success": True,
                "contact_id": contact_id,
                "engagement_id": engagement.get("id"),
                "tool": tool_name,
                "action": action
            }
            
        except Exception as e:
            logger.error(
                "Failed to log tool usage",
                error=str(e),
                email=user_email
            )
            return {"success": False, "error": str(e)}
    
    async def get_user_activity(
        self,
        user_email: str,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get activity history for a user.
        
        Args:
            user_email: User's email
            limit: Maximum number of activities to return
            
        Returns:
            User activity data
        """
        try:
            # Find contact
            contact = await self._find_contact_by_email(user_email)
            
            if not contact:
                return {"success": False, "error": "Contact not found"}
            
            contact_id = contact["id"]
            
            # Get engagements for this contact
            engagements = await self._get_contact_engagements(
                contact_id,
                limit=limit
            )
            
            # Get contact properties for usage stats
            properties = contact.get("properties", {})
            
            return {
                "success": True,
                "contact_id": contact_id,
                "email": user_email,
                "last_signin": properties.get("justdata_last_signin"),
                "total_signins": properties.get("justdata_signin_count", 0),
                "last_tool_used": properties.get("justdata_last_tool"),
                "recent_activities": engagements
            }
            
        except Exception as e:
            logger.error("Failed to get user activity", error=str(e))
            return {"success": False, "error": str(e)}
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    async def _find_contact_by_email(self, email: str) -> Optional[Dict]:
        """Find contact by email address."""
        filters = [
            {
                "propertyName": "email",
                "operator": "EQ",
                "value": email
            }
        ]
        
        contacts = await self.client.search_contacts(filters, limit=1)
        return contacts[0] if contacts else None
    
    async def _create_engagement(
        self,
        contact_id: str,
        engagement_type: str,
        subject: str,
        body: str
    ) -> Dict[str, Any]:
        """Create an engagement (note, email, etc.) for a contact."""
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(
                f"{self.client.base_url}/crm/v3/objects/notes",
                headers=self.client.headers,
                json={
                    "properties": {
                        "hs_note_body": body,
                        "hs_timestamp": datetime.now().isoformat()
                    },
                    "associations": [
                        {
                            "to": {"id": contact_id},
                            "types": [
                                {
                                    "associationCategory": "HUBSPOT_DEFINED",
                                    "associationTypeId": 202  # Note to Contact
                                }
                            ]
                        }
                    ]
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def _update_last_activity(
        self,
        contact_id: str,
        user_id: Optional[str],
        session_id: Optional[str]
    ) -> None:
        """Update contact with last activity timestamp."""
        properties = {
            "justdata_last_signin": datetime.now().isoformat(),
            "justdata_signin_count": "increment:1"
        }
        
        if user_id:
            properties["justdata_user_id"] = user_id
        
        if session_id:
            properties["justdata_last_session"] = session_id
        
        await self.client.update_contact(contact_id, properties)
    
    async def _increment_usage_counter(
        self,
        contact_id: str,
        tool_name: str
    ) -> None:
        """Increment usage counter for a specific tool."""
        properties = {
            "justdata_last_tool": tool_name,
            "justdata_last_activity": datetime.now().isoformat(),
            f"justdata_{tool_name}_count": "increment:1"
        }
        
        await self.client.update_contact(contact_id, properties)
    
    async def _get_contact_engagements(
        self,
        contact_id: str,
        limit: int = 50
    ) -> list:
        """Get engagements for a contact."""
        # This is a simplified version - actual implementation would query
        # the engagements API properly
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(
                f"{self.client.base_url}/crm/v3/objects/notes",
                headers=self.client.headers,
                params={"limit": limit}
            )
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
    
    def _build_signin_note(
        self,
        user_email: str,
        user_id: Optional[str],
        session_id: Optional[str],
        metadata: Optional[Dict[str, Any]]
    ) -> str:
        """Build formatted note content for sign-in."""
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
        details: Optional[Dict[str, Any]]
    ) -> str:
        """Build formatted note content for tool usage."""
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

