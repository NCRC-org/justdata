"""
HubSpot Integration Module

This module provides integration with HubSpot CRM for:
- Contact and company management
- Lead tracking and scoring
- Report distribution and tracking
- Marketing automation
- Custom workflows
- User activity tracking
"""

from .client import HubSpotClient
from .models import HubSpotContact, HubSpotCompany, HubSpotDeal
from .tracking import UserActivityTracker

__all__ = [
    "HubSpotClient",
    "HubSpotContact",
    "HubSpotCompany",
    "HubSpotDeal",
    "UserActivityTracker",
]

