"""
Main API router for JustData v1.
"""

from fastapi import APIRouter

# Import application-specific routers
# from apps.branchseeker.api import router as branchseeker_router
# from apps.lendsight.api import router as lendsight_router
# from apps.bizsight.api import router as bizsight_router
from api.v1.hubspot import router as hubspot_router

# Create main API router
api_router = APIRouter()

# Include application routers
# api_router.include_router(
#     branchseeker_router,
#     prefix="/branchseeker",
#     tags=["branchseeker"]
# )

# api_router.include_router(
#     lendsight_router,
#     prefix="/lendsight",
#     tags=["lendsight"]
# )

# api_router.include_router(
#     bizsight_router,
#     prefix="/bizsight",
#     tags=["bizsight"]
# )

# Include HubSpot integration router
api_router.include_router(hubspot_router)

# Root API endpoint
@api_router.get("/")
async def api_root():
    """API root endpoint."""
    return {
        "message": "JustData API v1",
        "endpoints": {
            "branchseeker": "/branchseeker",
            "lendsight": "/lendsight",
            "bizsight": "/bizsight",
            "hubspot": "/hubspot"
        },
        "docs": "/docs",
        "integrations": {
            "hubspot": "HubSpot CRM Integration"
        }
    }
