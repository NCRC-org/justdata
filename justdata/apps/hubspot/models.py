"""
HubSpot Data Models

Pydantic models for HubSpot CRM objects.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr


class HubSpotContact(BaseModel):
    """HubSpot Contact model."""
    
    id: Optional[str] = None
    email: EmailStr
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    website: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    
    # Custom properties for JustData
    lead_score: Optional[float] = None
    last_report_sent: Optional[datetime] = None
    total_reports_received: Optional[int] = 0
    industry_focus: Optional[str] = None
    
    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "john.doe@example.com",
                "firstname": "John",
                "lastname": "Doe",
                "company": "ACME Bank",
                "lead_score": 85.5,
                "industry_focus": "banking"
            }
        }


class HubSpotCompany(BaseModel):
    """HubSpot Company model."""
    
    id: Optional[str] = None
    name: str
    domain: Optional[str] = None
    industry: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    
    # Custom properties for JustData
    total_reports_generated: Optional[int] = 0
    subscription_level: Optional[str] = None
    last_analysis_date: Optional[datetime] = None
    primary_interest: Optional[str] = None  # banking, mortgage, small_business
    
    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "ACME Bank",
                "domain": "acmebank.com",
                "industry": "Banking",
                "subscription_level": "enterprise",
                "primary_interest": "banking"
            }
        }


class HubSpotDeal(BaseModel):
    """HubSpot Deal model."""
    
    id: Optional[str] = None
    dealname: str
    dealstage: Optional[str] = None
    amount: Optional[float] = None
    closedate: Optional[datetime] = None
    pipeline: Optional[str] = None
    
    # Associations
    company_id: Optional[str] = None
    contact_ids: Optional[List[str]] = []
    
    # Custom properties
    analysis_type: Optional[str] = None  # branchsight, lendsight, bizsight
    report_complexity: Optional[str] = None  # basic, standard, advanced, custom
    
    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "dealname": "Q4 Banking Analysis Report",
                "dealstage": "contractsent",
                "amount": 5000.00,
                "analysis_type": "branchsight",
                "report_complexity": "advanced"
            }
        }


class HubSpotEngagement(BaseModel):
    """HubSpot Engagement (Email, Call, Meeting, etc.)."""
    
    id: Optional[str] = None
    engagement_type: str  # EMAIL, CALL, MEETING, TASK, NOTE
    subject: Optional[str] = None
    body: Optional[str] = None
    status: Optional[str] = None
    timestamp: Optional[datetime] = None
    
    # Associations
    contact_ids: Optional[List[str]] = []
    company_ids: Optional[List[str]] = []
    deal_ids: Optional[List[str]] = []
    
    # Metadata
    created_at: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "engagement_type": "EMAIL",
                "subject": "Your BranchSight Analysis Report",
                "status": "SENT",
                "timestamp": "2024-10-15T10:30:00Z"
            }
        }


class HubSpotNote(BaseModel):
    """HubSpot Note model."""
    
    id: Optional[str] = None
    content: str
    timestamp: Optional[datetime] = None
    
    # Associations
    contact_ids: Optional[List[str]] = []
    company_ids: Optional[List[str]] = []
    deal_ids: Optional[List[str]] = []
    
    # Metadata
    created_at: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "Sent quarterly banking analysis report. Client interested in expanding to mortgage analysis.",
                "timestamp": "2024-10-15T10:30:00Z"
            }
        }

