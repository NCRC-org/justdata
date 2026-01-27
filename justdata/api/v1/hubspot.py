"""
HubSpot API Router

FastAPI endpoints for HubSpot CRM integration.
"""

from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, status, Query, Body
from pydantic import BaseModel, EmailStr
import structlog

from justdata.apps.hubspot.client import HubSpotClient
from justdata.apps.hubspot.services import HubSpotService
from justdata.apps.hubspot.sync import HubSpotSyncManager
from justdata.apps.hubspot.tracking import UserActivityTracker
from justdata.apps.hubspot.lists import HubSpotListsClient
from justdata.apps.hubspot.models import (
    HubSpotContact,
    HubSpotCompany,
    HubSpotDeal
)

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/hubspot",
    tags=["HubSpot Integration"],
    responses={404: {"description": "Not found"}},
)


# Request/Response Models
class ContactSyncRequest(BaseModel):
    """Request model for syncing a contact."""
    email: EmailStr
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    company: Optional[str] = None
    report_type: str = "branchsight"


class BatchContactSyncRequest(BaseModel):
    """Request model for batch contact sync."""
    contacts: List[Dict[str, Any]]
    batch_size: int = 100


class ReportRecipientsRequest(BaseModel):
    """Request model for syncing report recipients."""
    report_id: str
    recipients: List[Dict[str, str]]
    report_type: str = "branchsight"


class EngagementTrackingRequest(BaseModel):
    """Request model for tracking engagement."""
    contact_id: str
    report_name: str
    report_type: str
    engagement_type: str = "opened"


class DealCreateRequest(BaseModel):
    """Request model for creating a deal."""
    deal_name: str
    amount: float
    analysis_type: str
    company_id: Optional[str] = None
    contact_id: Optional[str] = None


class UserSignInRequest(BaseModel):
    """Request model for logging user sign-in."""
    user_email: EmailStr
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ToolUsageRequest(BaseModel):
    """Request model for logging tool usage."""
    user_email: EmailStr
    tool_name: str
    action: str
    details: Optional[Dict[str, Any]] = None


# =========================================================================
# HEALTH & STATUS
# =========================================================================

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Check HubSpot integration health.
    
    Returns connection status and portal information.
    """
    try:
        service = HubSpotService()
        test_results = await service.test_integration()
        
        return {
            "status": "healthy" if test_results["connection"] else "unhealthy",
            "connection": test_results["connection"],
            "portal_info": test_results.get("portal_info"),
            "error": test_results.get("error")
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )


# =========================================================================
# CONTACTS
# =========================================================================

@router.get("/contacts/{contact_id}")
async def get_contact(contact_id: str) -> Dict[str, Any]:
    """
    Get a HubSpot contact by ID.
    
    Args:
        contact_id: HubSpot contact ID
        
    Returns:
        Contact data
    """
    try:
        client = HubSpotClient()
        contact = await client.get_contact(contact_id)
        return contact
    except Exception as e:
        logger.error("Failed to get contact", contact_id=contact_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contact not found: {str(e)}"
        )


@router.post("/contacts")
async def create_contact(contact: HubSpotContact) -> Dict[str, Any]:
    """
    Create a new HubSpot contact.
    
    Args:
        contact: Contact data
        
    Returns:
        Created contact
    """
    try:
        client = HubSpotClient()
        created = await client.create_contact(contact)
        return created
    except Exception as e:
        logger.error("Failed to create contact", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create contact: {str(e)}"
        )


@router.patch("/contacts/{contact_id}")
async def update_contact(
    contact_id: str,
    properties: Dict[str, Any] = Body(...)
) -> Dict[str, Any]:
    """
    Update an existing HubSpot contact.
    
    Args:
        contact_id: HubSpot contact ID
        properties: Properties to update
        
    Returns:
        Updated contact
    """
    try:
        client = HubSpotClient()
        updated = await client.update_contact(contact_id, properties)
        return updated
    except Exception as e:
        logger.error(
            "Failed to update contact",
            contact_id=contact_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update contact: {str(e)}"
        )


@router.post("/contacts/search")
async def search_contacts(
    filters: List[Dict[str, Any]] = Body(...),
    limit: int = Query(default=100, le=1000)
) -> List[Dict[str, Any]]:
    """
    Search HubSpot contacts with filters.
    
    Args:
        filters: List of search filters
        limit: Maximum number of results
        
    Returns:
        List of matching contacts
    """
    try:
        client = HubSpotClient()
        contacts = await client.search_contacts(filters, limit)
        return contacts
    except Exception as e:
        logger.error("Failed to search contacts", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to search contacts: {str(e)}"
        )


# =========================================================================
# COMPANIES
# =========================================================================

@router.get("/companies/{company_id}")
async def get_company(company_id: str) -> Dict[str, Any]:
    """
    Get a HubSpot company by ID.
    
    Args:
        company_id: HubSpot company ID
        
    Returns:
        Company data
    """
    try:
        client = HubSpotClient()
        company = await client.get_company(company_id)
        return company
    except Exception as e:
        logger.error("Failed to get company", company_id=company_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company not found: {str(e)}"
        )


@router.post("/companies")
async def create_company(company: HubSpotCompany) -> Dict[str, Any]:
    """
    Create a new HubSpot company.
    
    Args:
        company: Company data
        
    Returns:
        Created company
    """
    try:
        client = HubSpotClient()
        created = await client.create_company(company)
        return created
    except Exception as e:
        logger.error("Failed to create company", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create company: {str(e)}"
        )


# =========================================================================
# SYNC OPERATIONS
# =========================================================================

@router.post("/sync/contact")
async def sync_contact(request: ContactSyncRequest) -> Dict[str, Any]:
    """
    Sync a single contact from report delivery.
    
    Creates or updates contact and tracks report.
    
    Args:
        request: Contact sync request
        
    Returns:
        Synced contact data
    """
    try:
        service = HubSpotService()
        contact = await service.sync_contact_from_report(
            email=request.email,
            firstname=request.firstname,
            lastname=request.lastname,
            company_name=request.company,
            report_type=request.report_type
        )
        return contact
    except Exception as e:
        logger.error("Failed to sync contact", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to sync contact: {str(e)}"
        )


@router.post("/sync/contacts/batch")
async def sync_contacts_batch(request: BatchContactSyncRequest) -> Dict[str, Any]:
    """
    Sync multiple contacts in batch.
    
    Args:
        request: Batch sync request
        
    Returns:
        Sync results
    """
    try:
        sync_manager = HubSpotSyncManager()
        results = await sync_manager.sync_contacts_batch(
            contacts=request.contacts,
            batch_size=request.batch_size
        )
        return results
    except Exception as e:
        logger.error("Failed to batch sync contacts", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to batch sync: {str(e)}"
        )


@router.post("/sync/report-recipients")
async def sync_report_recipients(request: ReportRecipientsRequest) -> Dict[str, Any]:
    """
    Sync report recipients to HubSpot.
    
    Args:
        request: Report recipients request
        
    Returns:
        Sync results
    """
    try:
        sync_manager = HubSpotSyncManager()
        results = await sync_manager.sync_report_recipients(
            report_id=request.report_id,
            recipients=request.recipients,
            report_type=request.report_type
        )
        return results
    except Exception as e:
        logger.error("Failed to sync report recipients", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to sync recipients: {str(e)}"
        )


# =========================================================================
# ENGAGEMENT TRACKING
# =========================================================================

@router.post("/track/engagement")
async def track_engagement(request: EngagementTrackingRequest) -> Dict[str, Any]:
    """
    Track report engagement (opened, downloaded, shared).
    
    Args:
        request: Engagement tracking request
        
    Returns:
        Success status
    """
    try:
        service = HubSpotService()
        success = await service.track_report_engagement(
            contact_id=request.contact_id,
            report_name=request.report_name,
            report_type=request.report_type,
            engagement_type=request.engagement_type
        )
        return {
            "success": success,
            "contact_id": request.contact_id,
            "engagement_type": request.engagement_type
        }
    except Exception as e:
        logger.error("Failed to track engagement", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to track engagement: {str(e)}"
        )


@router.post("/track/report-sent")
async def track_report_sent(
    contact_id: str = Body(...),
    report_type: str = Body(...),
    report_name: str = Body(...)
) -> Dict[str, Any]:
    """
    Track when a report is sent to a contact.
    
    Args:
        contact_id: HubSpot contact ID
        report_type: Type of report
        report_name: Name of report
        
    Returns:
        Updated contact
    """
    try:
        client = HubSpotClient()
        contact = await client.track_report_sent(
            contact_id=contact_id,
            report_type=report_type,
            report_name=report_name
        )
        return contact
    except Exception as e:
        logger.error("Failed to track report sent", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to track report: {str(e)}"
        )


# =========================================================================
# ANALYTICS & REPORTING
# =========================================================================

@router.get("/analytics/industry/{industry_focus}")
async def get_contacts_by_industry(
    industry_focus: str,
    limit: int = Query(default=100, le=1000)
) -> List[Dict[str, Any]]:
    """
    Get contacts filtered by industry focus.
    
    Args:
        industry_focus: Industry to filter (banking, mortgage, small_business)
        limit: Maximum number of results
        
    Returns:
        List of contacts
    """
    try:
        service = HubSpotService()
        contacts = await service.get_contacts_by_industry(
            industry_focus=industry_focus,
            limit=limit
        )
        return contacts
    except Exception as e:
        logger.error("Failed to get contacts by industry", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch contacts: {str(e)}"
        )


# =========================================================================
# USER ACTIVITY TRACKING
# =========================================================================

@router.post("/track/signin")
async def track_user_signin(request: UserSignInRequest) -> Dict[str, Any]:
    """
    Log user sign-in to HubSpot.
    
    Tracks when members sign in to use JustData.
    
    Args:
        request: Sign-in tracking request
        
    Returns:
        Tracking result
    """
    try:
        tracker = UserActivityTracker()
        result = await tracker.log_user_signin(
            user_email=request.user_email,
            user_id=request.user_id,
            session_id=request.session_id,
            metadata=request.metadata
        )
        return result
    except Exception as e:
        logger.error("Failed to track sign-in", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to track sign-in: {str(e)}"
        )


@router.post("/track/tool-usage")
async def track_tool_usage(request: ToolUsageRequest) -> Dict[str, Any]:
    """
    Log tool usage to HubSpot.
    
    Tracks when members use specific tools/features.
    
    Args:
        request: Tool usage tracking request
        
    Returns:
        Tracking result
    """
    try:
        tracker = UserActivityTracker()
        result = await tracker.log_tool_usage(
            user_email=request.user_email,
            tool_name=request.tool_name,
            action=request.action,
            details=request.details
        )
        return result
    except Exception as e:
        logger.error("Failed to track tool usage", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to track usage: {str(e)}"
        )


@router.get("/activity/{email}")
async def get_user_activity(
    email: str,
    limit: int = Query(default=50, le=500)
) -> Dict[str, Any]:
    """
    Get activity history for a user.
    
    Returns sign-in and usage history for a member.
    
    Args:
        email: User's email address
        limit: Maximum number of activities to return
        
    Returns:
        User activity data including:
        - Last sign-in time
        - Total sign-ins
        - Last tool used
        - Recent activities
    """
    try:
        tracker = UserActivityTracker()
        activity = await tracker.get_user_activity(
            user_email=email,
            limit=limit
        )
        return activity
    except Exception as e:
        logger.error("Failed to get user activity", error=str(e), email=email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get activity: {str(e)}"
        )


# =========================================================================
# LISTS API
# =========================================================================

@router.get("/lists")
async def get_all_lists() -> List[Dict[str, Any]]:
    """
    Get all HubSpot lists.
    
    Returns:
        List of all lists in the HubSpot account
    """
    try:
        import os
        access_token = os.getenv("HUBSPOT_ACCESS_TOKEN")
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="HUBSPOT_ACCESS_TOKEN not configured"
            )
        
        lists_client = HubSpotListsClient(access_token=access_token)
        lists = await lists_client.get_all_lists()
        return lists
    except Exception as e:
        logger.error("Failed to get lists", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get lists: {str(e)}"
        )


@router.get("/lists/{list_name}/contacts")
async def get_list_contacts_by_name(
    list_name: str,
    limit: int = Query(default=100, le=500)
) -> Dict[str, Any]:
    """
    Get contacts from a HubSpot list by name.
    
    Args:
        list_name: Name of the list (e.g., "Member Map Base")
        limit: Maximum number of contacts to return
        
    Returns:
        List details and contacts
    """
    try:
        import os
        access_token = os.getenv("HUBSPOT_ACCESS_TOKEN")
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="HUBSPOT_ACCESS_TOKEN not configured"
            )
        
        lists_client = HubSpotListsClient(access_token=access_token)
        result = await lists_client.get_list_by_name_with_contacts(
            list_name=list_name,
            limit=limit
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result.get("error", "List not found")
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get list contacts", error=str(e), list_name=list_name)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get list contacts: {str(e)}"
        )


# =========================================================================
# UTILITIES
# =========================================================================

@router.post("/test")
async def test_integration() -> Dict[str, Any]:
    """
    Test HubSpot integration.
    
    Returns:
        Test results including connection status and portal info
    """
    try:
        service = HubSpotService()
        results = await service.test_integration()
        return results
    except Exception as e:
        logger.error("Integration test failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test failed: {str(e)}"
        )

