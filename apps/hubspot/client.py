"""
HubSpot API Client

Provides async interface to HubSpot CRM API.
"""

import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import httpx
from hubspot import HubSpot
from hubspot.crm.contacts import ApiException as ContactsApiException
from hubspot.crm.companies import ApiException as CompaniesApiException

from .models import HubSpotContact, HubSpotCompany, HubSpotDeal


class HubSpotClient:
    """
    Async client for interacting with HubSpot CRM API.
    
    Provides methods for managing contacts, companies, deals, and engagements.
    """
    
    def __init__(self, access_token: Optional[str] = None):
        """
        Initialize HubSpot client.
        
        Args:
            access_token: HubSpot private app access token.
                         If not provided, reads from HUBSPOT_ACCESS_TOKEN env var.
        """
        self.access_token = access_token or os.getenv("HUBSPOT_ACCESS_TOKEN")
        if not self.access_token:
            raise ValueError(
                "HubSpot access token is required. "
                "Provide it via parameter or HUBSPOT_ACCESS_TOKEN env var."
            )
        
        # Initialize HubSpot SDK client
        self.client = HubSpot(access_token=self.access_token)
        
        # Base URL for direct API calls (when SDK doesn't cover endpoint)
        self.base_url = "https://api.hubapi.com"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    # =========================================================================
    # CONTACTS
    # =========================================================================
    
    async def get_contact(self, contact_id: str) -> Dict[str, Any]:
        """
        Get a contact by ID.
        
        Args:
            contact_id: HubSpot contact ID
            
        Returns:
            Contact data dictionary
        """
        try:
            api_response = self.client.crm.contacts.basic_api.get_by_id(
                contact_id=contact_id
            )
            return api_response.to_dict()
        except ContactsApiException as e:
            raise Exception(f"Failed to get contact {contact_id}: {e}")
    
    async def create_contact(self, contact: HubSpotContact) -> Dict[str, Any]:
        """
        Create a new contact.
        
        Args:
            contact: HubSpotContact model instance
            
        Returns:
            Created contact data
        """
        properties = contact.model_dump(exclude_none=True, exclude={"id"})
        
        try:
            api_response = self.client.crm.contacts.basic_api.create(
                simple_public_object_input_for_create={"properties": properties}
            )
            return api_response.to_dict()
        except ContactsApiException as e:
            raise Exception(f"Failed to create contact: {e}")
    
    async def update_contact(
        self, 
        contact_id: str, 
        properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an existing contact.
        
        Args:
            contact_id: HubSpot contact ID
            properties: Dictionary of properties to update
            
        Returns:
            Updated contact data
        """
        try:
            api_response = self.client.crm.contacts.basic_api.update(
                contact_id=contact_id,
                simple_public_object_input={"properties": properties}
            )
            return api_response.to_dict()
        except ContactsApiException as e:
            raise Exception(f"Failed to update contact {contact_id}: {e}")
    
    async def search_contacts(
        self, 
        filters: List[Dict[str, Any]],
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search contacts with filters.
        
        Args:
            filters: List of filter dictionaries
            limit: Maximum number of results
            
        Returns:
            List of matching contacts
        """
        search_request = {
            "filterGroups": [{"filters": filters}],
            "limit": limit
        }
        
        try:
            api_response = self.client.crm.contacts.search_api.do_search(
                public_object_search_request=search_request
            )
            return [result.to_dict() for result in api_response.results]
        except ContactsApiException as e:
            raise Exception(f"Failed to search contacts: {e}")
    
    # =========================================================================
    # COMPANIES
    # =========================================================================
    
    async def get_company(self, company_id: str) -> Dict[str, Any]:
        """
        Get a company by ID.
        
        Args:
            company_id: HubSpot company ID
            
        Returns:
            Company data dictionary
        """
        try:
            api_response = self.client.crm.companies.basic_api.get_by_id(
                company_id=company_id
            )
            return api_response.to_dict()
        except CompaniesApiException as e:
            raise Exception(f"Failed to get company {company_id}: {e}")
    
    async def create_company(self, company: HubSpotCompany) -> Dict[str, Any]:
        """
        Create a new company.
        
        Args:
            company: HubSpotCompany model instance
            
        Returns:
            Created company data
        """
        properties = company.model_dump(exclude_none=True, exclude={"id"})
        
        try:
            api_response = self.client.crm.companies.basic_api.create(
                simple_public_object_input_for_create={"properties": properties}
            )
            return api_response.to_dict()
        except CompaniesApiException as e:
            raise Exception(f"Failed to create company: {e}")
    
    async def update_company(
        self, 
        company_id: str, 
        properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an existing company.
        
        Args:
            company_id: HubSpot company ID
            properties: Dictionary of properties to update
            
        Returns:
            Updated company data
        """
        try:
            api_response = self.client.crm.companies.basic_api.update(
                company_id=company_id,
                simple_public_object_input={"properties": properties}
            )
            return api_response.to_dict()
        except CompaniesApiException as e:
            raise Exception(f"Failed to update company {company_id}: {e}")
    
    async def search_companies(
        self, 
        filters: List[Dict[str, Any]],
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search companies with filters.
        
        Args:
            filters: List of filter dictionaries
            limit: Maximum number of results
            
        Returns:
            List of matching companies
        """
        search_request = {
            "filterGroups": [{"filters": filters}],
            "limit": limit
        }
        
        try:
            api_response = self.client.crm.companies.search_api.do_search(
                public_object_search_request=search_request
            )
            return [result.to_dict() for result in api_response.results]
        except CompaniesApiException as e:
            raise Exception(f"Failed to search companies: {e}")
    
    # =========================================================================
    # ASSOCIATIONS
    # =========================================================================
    
    async def associate_contact_to_company(
        self, 
        contact_id: str, 
        company_id: str
    ) -> bool:
        """
        Associate a contact with a company.
        
        Args:
            contact_id: HubSpot contact ID
            company_id: HubSpot company ID
            
        Returns:
            True if successful
        """
        try:
            self.client.crm.contacts.associations_api.create(
                contact_id=contact_id,
                to_object_type="company",
                to_object_id=company_id,
                association_type="contact_to_company"
            )
            return True
        except Exception as e:
            raise Exception(f"Failed to associate contact to company: {e}")
    
    # =========================================================================
    # CUSTOM METHODS FOR JUSTDATA
    # =========================================================================
    
    async def track_report_sent(
        self, 
        contact_id: str, 
        report_type: str,
        report_name: str
    ) -> Dict[str, Any]:
        """
        Track when a report is sent to a contact.
        
        Args:
            contact_id: HubSpot contact ID
            report_type: Type of report (branchseeker, lendsight, bizsight)
            report_name: Name of the report
            
        Returns:
            Updated contact data
        """
        # Update contact properties
        properties = {
            "last_report_sent": datetime.now().isoformat(),
            "total_reports_received": "increment:1",  # HubSpot will increment
            "last_report_type": report_type
        }
        
        # Create a note about the report
        note_content = (
            f"Sent {report_type} report: {report_name}\n"
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        # Update contact and create note
        contact = await self.update_contact(contact_id, properties)
        await self.create_note(contact_id, note_content)
        
        return contact
    
    async def create_note(
        self, 
        contact_id: str, 
        content: str
    ) -> Dict[str, Any]:
        """
        Create a note associated with a contact.
        
        Args:
            contact_id: HubSpot contact ID
            content: Note content
            
        Returns:
            Created note data
        """
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(
                f"{self.base_url}/crm/v3/objects/notes",
                headers=self.headers,
                json={
                    "properties": {
                        "hs_note_body": content,
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
    
    async def get_portal_info(self) -> Dict[str, Any]:
        """
        Get information about the authenticated HubSpot portal.
        
        Returns:
            Portal information
        """
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(
                f"{self.base_url}/account-info/v3/details",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def test_connection(self) -> bool:
        """
        Test the connection to HubSpot API.
        
        Returns:
            True if connection is successful
        """
        try:
            await self.get_portal_info()
            return True
        except Exception:
            return False

