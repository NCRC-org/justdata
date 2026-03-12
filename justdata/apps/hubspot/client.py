"""
HubSpot API Client

Provides async interface to HubSpot CRM API using httpx.
"""

import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import httpx


class HubSpotClient:
    """
    Async client for interacting with HubSpot CRM API.

    Uses httpx for truly async HTTP calls (no SDK wrapper).
    """

    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token or os.getenv("HUBSPOT_ACCESS_TOKEN")
        if not self.access_token:
            raise ValueError(
                "HubSpot access token is required. "
                "Provide it via parameter or HUBSPOT_ACCESS_TOKEN env var."
            )

        self.base_url = "https://api.hubapi.com"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    # =========================================================================
    # CONTACTS
    # =========================================================================

    async def get_contact(self, contact_id: str) -> Dict[str, Any]:
        """Get a contact by ID."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self.base_url}/crm/v3/objects/contacts/{contact_id}",
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def create_contact(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new contact from a properties dict."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/crm/v3/objects/contacts",
                headers=self.headers,
                json={"properties": properties},
            )
            resp.raise_for_status()
            return resp.json()

    async def update_contact(
        self, contact_id: str, properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing contact."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.patch(
                f"{self.base_url}/crm/v3/objects/contacts/{contact_id}",
                headers=self.headers,
                json={"properties": properties},
            )
            resp.raise_for_status()
            return resp.json()

    async def search_contacts(
        self, filters: List[Dict[str, Any]], limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search contacts with filters."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/crm/v3/objects/contacts/search",
                headers=self.headers,
                json={
                    "filterGroups": [{"filters": filters}],
                    "limit": limit,
                },
            )
            resp.raise_for_status()
            return resp.json().get("results", [])

    # =========================================================================
    # COMPANIES
    # =========================================================================

    async def get_company(self, company_id: str) -> Dict[str, Any]:
        """Get a company by ID."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self.base_url}/crm/v3/objects/companies/{company_id}",
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def create_company(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new company from a properties dict."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/crm/v3/objects/companies",
                headers=self.headers,
                json={"properties": properties},
            )
            resp.raise_for_status()
            return resp.json()

    async def update_company(
        self, company_id: str, properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing company."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.patch(
                f"{self.base_url}/crm/v3/objects/companies/{company_id}",
                headers=self.headers,
                json={"properties": properties},
            )
            resp.raise_for_status()
            return resp.json()

    async def search_companies(
        self,
        filters: List[Dict[str, Any]],
        properties: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Search companies with filters."""
        body: Dict[str, Any] = {
            "filterGroups": [{"filters": filters}],
            "limit": limit,
        }
        if properties:
            body["properties"] = properties

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/crm/v3/objects/companies/search",
                headers=self.headers,
                json=body,
            )
            resp.raise_for_status()
            return resp.json().get("results", [])

    # =========================================================================
    # NOTES & ENGAGEMENT
    # =========================================================================

    async def create_note(self, contact_id: str, content: str) -> Dict[str, Any]:
        """Create a note associated with a contact."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/crm/v3/objects/notes",
                headers=self.headers,
                json={
                    "properties": {
                        "hs_note_body": content,
                        "hs_timestamp": datetime.now().isoformat(),
                    },
                    "associations": [
                        {
                            "to": {"id": contact_id},
                            "types": [
                                {
                                    "associationCategory": "HUBSPOT_DEFINED",
                                    "associationTypeId": 202,
                                }
                            ],
                        }
                    ],
                },
            )
            resp.raise_for_status()
            return resp.json()

    async def track_report_sent(
        self, contact_id: str, report_type: str, report_name: str
    ) -> Dict[str, Any]:
        """Track when a report is sent to a contact."""
        contact = await self.get_contact(contact_id)
        current_count = int(
            contact.get("properties", {}).get("total_reports_received", 0) or 0
        )

        properties = {
            "last_report_sent": datetime.now().isoformat(),
            "total_reports_received": str(current_count + 1),
            "last_report_type": report_type,
        }

        note_content = (
            f"Sent {report_type} report: {report_name}\n"
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        updated = await self.update_contact(contact_id, properties)
        await self.create_note(contact_id, note_content)
        return updated

    # =========================================================================
    # PORTAL
    # =========================================================================

    async def get_portal_info(self) -> Dict[str, Any]:
        """Get information about the authenticated HubSpot portal."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self.base_url}/account-info/v3/details",
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def test_connection(self) -> bool:
        """Test the connection to HubSpot API."""
        try:
            await self.get_portal_info()
            return True
        except Exception:
            return False
