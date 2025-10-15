"""
HubSpot Lists API Integration

Work with HubSpot Lists to get member information.
"""

from typing import Dict, List, Optional, Any
import structlog
import httpx

logger = structlog.get_logger(__name__)


class HubSpotListsClient:
    """
    Client for working with HubSpot Lists API.
    
    Access member lists and get contact information.
    """
    
    def __init__(self, access_token: str):
        """Initialize Lists client."""
        self.access_token = access_token
        self.base_url = "https://api.hubapi.com"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    async def get_all_lists(self) -> List[Dict[str, Any]]:
        """
        Get all lists in the HubSpot account.
        
        Returns:
            List of all lists with their IDs and names
        """
        logger.info("Fetching all HubSpot lists")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/crm/v3/lists",
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            
            lists = data.get("lists", [])
            logger.info(f"Found {len(lists)} lists")
            
            return lists
    
    async def find_list_by_name(self, list_name: str) -> Optional[Dict[str, Any]]:
        """
        Find a list by its name.
        
        Args:
            list_name: Name of the list to find (case-insensitive)
            
        Returns:
            List details if found, None otherwise
        """
        logger.info(f"Searching for list: {list_name}")
        
        all_lists = await self.get_all_lists()
        
        for lst in all_lists:
            if lst.get("name", "").lower() == list_name.lower():
                logger.info(f"Found list: {lst['name']} (ID: {lst['listId']})")
                return lst
        
        logger.warning(f"List not found: {list_name}")
        return None
    
    async def get_list_contacts(
        self,
        list_id: str,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get contacts from a specific list.
        
        Args:
            list_id: HubSpot list ID
            limit: Maximum number of contacts to return
            
        Returns:
            List of contacts with their properties
        """
        logger.info(f"Fetching contacts from list {list_id}")
        
        async with httpx.AsyncClient() as client:
            # Get list memberships
            response = await client.get(
                f"{self.base_url}/crm/v3/lists/{list_id}/memberships",
                headers=self.headers,
                params={"limit": limit}
            )
            response.raise_for_status()
            memberships = response.json()
            
            contact_ids = [
                m.get("recordId") 
                for m in memberships.get("results", [])
            ]
            
            if not contact_ids:
                return {
                    "list_id": list_id,
                    "total_contacts": 0,
                    "contacts": []
                }
            
            # Get contact details
            contacts = []
            for contact_id in contact_ids:
                try:
                    contact_response = await client.get(
                        f"{self.base_url}/crm/v3/objects/contacts/{contact_id}",
                        headers=self.headers
                    )
                    contact_response.raise_for_status()
                    contacts.append(contact_response.json())
                except Exception as e:
                    logger.error(f"Failed to get contact {contact_id}: {e}")
            
            logger.info(f"Retrieved {len(contacts)} contacts from list {list_id}")
            
            return {
                "list_id": list_id,
                "total_contacts": len(contacts),
                "contacts": contacts
            }
    
    async def get_list_by_name_with_contacts(
        self,
        list_name: str,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get a list by name and retrieve its contacts.
        
        Args:
            list_name: Name of the list (e.g., "Member Map Base")
            limit: Maximum number of contacts to return
            
        Returns:
            List details and contacts
        """
        # Find the list
        list_info = await self.find_list_by_name(list_name)
        
        if not list_info:
            return {
                "success": False,
                "error": f"List '{list_name}' not found"
            }
        
        # Get contacts from the list
        contacts_data = await self.get_list_contacts(
            list_id=list_info["listId"],
            limit=limit
        )
        
        return {
            "success": True,
            "list_name": list_info["name"],
            "list_id": list_info["listId"],
            "total_contacts": contacts_data["total_contacts"],
            "contacts": contacts_data["contacts"]
        }

