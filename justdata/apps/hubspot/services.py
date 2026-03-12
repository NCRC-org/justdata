"""
HubSpot Services

Business logic for HubSpot integration.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import structlog

from .client import HubSpotClient

logger = structlog.get_logger(__name__)


class HubSpotService:
    """
    Service layer for HubSpot integration.
    
    Provides business logic for common HubSpot operations.
    """
    
    def __init__(self, access_token: Optional[str] = None):
        """Initialize HubSpot service."""
        self.client = HubSpotClient(access_token=access_token)
    
    async def sync_contact_from_report(
        self,
        email: str,
        firstname: Optional[str] = None,
        lastname: Optional[str] = None,
        company_name: Optional[str] = None,
        report_type: str = "branchsight"
    ) -> Dict[str, Any]:
        """
        Sync a contact to HubSpot when they receive a report.
        
        Creates or updates contact and tracks report delivery.
        
        Args:
            email: Contact email
            firstname: Contact first name
            lastname: Contact last name
            company_name: Company name
            report_type: Type of report sent
            
        Returns:
            Contact data
        """
        logger.info(
            "Syncing contact to HubSpot",
            email=email,
            report_type=report_type
        )
        
        try:
            # Search for existing contact
            filters = [
                {
                    "propertyName": "email",
                    "operator": "EQ",
                    "value": email
                }
            ]
            existing_contacts = await self.client.search_contacts(filters, limit=1)
            
            if existing_contacts:
                contact_id = existing_contacts[0]["id"]
                logger.info("Found existing contact", contact_id=contact_id)

                existing_props = existing_contacts[0].get("properties", {})
                current_count = int(
                    existing_props.get("total_reports_received", 0) or 0
                )

                properties = {
                    "total_reports_received": str(current_count + 1),
                    "last_report_sent": datetime.now().isoformat(),
                    "industry_focus": report_type,
                }

                if firstname:
                    properties["firstname"] = firstname
                if lastname:
                    properties["lastname"] = lastname
                if company_name:
                    properties["company"] = company_name

                contact = await self.client.update_contact(contact_id, properties)
            else:
                logger.info("Creating new contact", email=email)

                properties = {
                    "email": email,
                    "total_reports_received": "1",
                    "last_report_sent": datetime.now().isoformat(),
                    "industry_focus": report_type,
                }
                if firstname:
                    properties["firstname"] = firstname
                if lastname:
                    properties["lastname"] = lastname
                if company_name:
                    properties["company"] = company_name

                contact = await self.client.create_contact(properties)
            
            logger.info("Contact synced successfully", contact_id=contact["id"])
            return contact
            
        except Exception as e:
            logger.error("Failed to sync contact", error=str(e), email=email)
            raise
    
    async def track_report_engagement(
        self,
        contact_id: str,
        report_name: str,
        report_type: str,
        engagement_type: str = "opened"
    ) -> bool:
        """
        Track when a contact engages with a report.
        
        Args:
            contact_id: HubSpot contact ID
            report_name: Name of the report
            report_type: Type of report
            engagement_type: Type of engagement (opened, downloaded, shared)
            
        Returns:
            True if tracking successful
        """
        logger.info(
            "Tracking report engagement",
            contact_id=contact_id,
            report_name=report_name,
            engagement_type=engagement_type
        )
        
        try:
            note_content = (
                f"Report Engagement: {engagement_type.upper()}\n"
                f"Report: {report_name}\n"
                f"Type: {report_type}\n"
                f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            await self.client.create_note(contact_id, note_content)
            
            score_increment = {
                "opened": 5,
                "downloaded": 10,
                "shared": 15,
            }.get(engagement_type, 0)

            if score_increment > 0:
                contact_data = await self.client.get_contact(contact_id)
                current_score = int(
                    contact_data.get("properties", {}).get("lead_score", 0) or 0
                )
                await self.client.update_contact(
                    contact_id, {"lead_score": str(current_score + score_increment)}
                )
            
            logger.info("Engagement tracked successfully", contact_id=contact_id)
            return True
            
        except Exception as e:
            logger.error(
                "Failed to track engagement",
                error=str(e),
                contact_id=contact_id
            )
            return False
    
    async def get_contacts_by_industry(
        self,
        industry_focus: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get contacts filtered by industry focus.
        
        Args:
            industry_focus: Industry to filter by (banking, mortgage, small_business)
            limit: Maximum number of results
            
        Returns:
            List of contacts
        """
        logger.info("Fetching contacts by industry", industry_focus=industry_focus)
        
        try:
            filters = [
                {
                    "propertyName": "industry_focus",
                    "operator": "EQ",
                    "value": industry_focus
                }
            ]
            
            contacts = await self.client.search_contacts(filters, limit=limit)
            logger.info(
                "Contacts fetched successfully",
                industry_focus=industry_focus,
                count=len(contacts)
            )
            
            return contacts
            
        except Exception as e:
            logger.error(
                "Failed to fetch contacts",
                error=str(e),
                industry_focus=industry_focus
            )
            raise
    
    async def test_integration(self) -> Dict[str, Any]:
        """
        Test the HubSpot integration.
        
        Returns:
            Test results
        """
        results = {
            "connection": False,
            "portal_info": None,
            "error": None
        }
        
        try:
            # Test connection
            results["connection"] = await self.client.test_connection()
            
            if results["connection"]:
                # Get portal info
                results["portal_info"] = await self.client.get_portal_info()
            
            logger.info("HubSpot integration test completed", results=results)
            
        except Exception as e:
            results["error"] = str(e)
            logger.error("HubSpot integration test failed", error=str(e))
        
        return results

