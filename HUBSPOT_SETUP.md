# HubSpot CLI Installation & Integration Guide

## Overview
This guide will help you install the HubSpot CLI and integrate it with your JustData platform for CRM and marketing automation capabilities.

## Prerequisites
- ✅ Node.js v20.15.1 (Installed)
- ✅ npm 10.7.0 (Installed)
- HubSpot account with API access

## Step 1: Fix npm Permissions (Required First)

Your npm cache has permission issues that need to be fixed. Run this command in your terminal:

```bash
sudo chown -R 501:20 "/Users/jadedlebi/.npm"
```

This will fix the npm cache folder permissions. You'll be prompted for your macOS password.

## Step 2: Install HubSpot CLI

After fixing the permissions, you have two installation options:

### Option A: Local Installation (Recommended for Project Integration)

Install HubSpot CLI as a project dependency:

```bash
cd /Users/jadedlebi/justdata
npm install --save-dev @hubspot/cli
```

To use the CLI when installed locally:
```bash
npx hs --version
npx hs init
```

### Option B: Global Installation

Install HubSpot CLI globally (available system-wide):

```bash
sudo npm install -g @hubspot/cli
```

To use the CLI when installed globally:
```bash
hs --version
hs init
```

## Step 3: Create HubSpot Developer Project

**IMPORTANT: Use Developer Projects (Not Legacy Apps)**

HubSpot is deprecating legacy apps in favor of developer projects. Developer projects provide:
- CI/CD integration with GitHub
- Better source control and deployment
- Modern development workflow
- Future-proof architecture

### Create a Developer Project

```bash
# If installed locally:
npx hs project create

# If installed globally:
hs project create
```

Follow the interactive prompts:
1. **Project name**: `justdata-hubspot` (or your preference)
2. **Template**: Choose "None" or "Blank" for API-only integration
3. **GitHub integration**: Yes (recommended for CI/CD)
4. **Authentication**: Follow the auth flow

This will:
1. Create a developer project structure
2. Create a `hubspot.config.yml` file in your project
3. Prompt you to authenticate with your HubSpot account
4. Set up your portal ID and access credentials
5. Optionally configure GitHub integration

### Alternative: Legacy Init (Not Recommended)

Only use this if you have a specific reason to avoid developer projects:

```bash
npx hs init  # Legacy approach
```

⚠️ **Warning**: Legacy apps are being deprecated. Use developer projects for new integrations.

## Step 4: Authenticate with HubSpot

You'll need to authenticate with your HubSpot account. You have two options:

### Personal Access Key (Recommended for Development)

1. Go to your HubSpot account
2. Navigate to Settings → Integrations → Private Apps
3. Create a new private app with required scopes
4. Copy the access token
5. When prompted by `hs init`, paste this token

### OAuth (For Production)

1. Create an OAuth app in HubSpot
2. Configure OAuth credentials in the CLI

## Step 5: Configure Environment Variables

Add these HubSpot-related environment variables to your `.env` file:

```env
# HubSpot Configuration
HUBSPOT_PORTAL_ID=your_portal_id
HUBSPOT_ACCESS_TOKEN=your_access_token
HUBSPOT_API_KEY=your_api_key  # For some API operations

# HubSpot Integration Settings
HUBSPOT_SYNC_ENABLED=True
HUBSPOT_WEBHOOK_SECRET=your_webhook_secret
```

## Step 6: Project Integration Structure

Create a HubSpot integration module in your JustData project:

```
justdata/
├── apps/
│   └── hubspot/              # NEW: HubSpot integration module
│       ├── __init__.py
│       ├── client.py         # HubSpot API client
│       ├── models.py         # HubSpot data models
│       ├── services.py       # Business logic
│       └── sync.py           # Data synchronization
```

## Useful HubSpot CLI Commands

### Portal Management
```bash
npx hs accounts list         # List connected accounts
npx hs accounts use [name]   # Switch between accounts
```

### File Operations
```bash
npx hs upload src dest       # Upload files to HubSpot
npx hs fetch dest src        # Download files from HubSpot
npx hs watch src dest        # Watch and sync files
```

### Development
```bash
npx hs create module         # Create a new module
npx hs create template       # Create a new template
npx hs lint                  # Lint HubSpot files
```

### API Testing
```bash
npx hs functions test        # Test serverless functions
npx hs logs                  # View function logs
```

## Integration Use Cases for JustData

### 1. CRM Data Sync
- Sync financial analysis reports to HubSpot contacts/companies
- Track customer engagement with reports
- Automate follow-up workflows

### 2. Lead Scoring
- Import leads from HubSpot for analysis
- Score leads based on financial data
- Push scores back to HubSpot

### 3. Automated Reporting
- Trigger JustData reports from HubSpot workflows
- Email reports to contacts via HubSpot
- Track report delivery and opens

### 4. Marketing Analytics
- Analyze marketing campaign effectiveness
- Integrate financial metrics with marketing data
- Create custom dashboards

## Example Python Integration

Here's a basic example of how to integrate HubSpot with your Python backend:

```python
# justdata/apps/hubspot/client.py
import os
from typing import Dict, List, Optional
import httpx
from pydantic import BaseModel


class HubSpotClient:
    """Client for interacting with HubSpot API."""
    
    def __init__(self, access_token: str = None):
        self.access_token = access_token or os.getenv("HUBSPOT_ACCESS_TOKEN")
        self.base_url = "https://api.hubapi.com"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    async def get_contact(self, contact_id: str) -> Dict:
        """Get a contact by ID."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/crm/v3/objects/contacts/{contact_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def create_contact(self, properties: Dict) -> Dict:
        """Create a new contact."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/crm/v3/objects/contacts",
                headers=self.headers,
                json={"properties": properties}
            )
            response.raise_for_status()
            return response.json()
    
    async def update_contact(self, contact_id: str, properties: Dict) -> Dict:
        """Update an existing contact."""
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.base_url}/crm/v3/objects/contacts/{contact_id}",
                headers=self.headers,
                json={"properties": properties}
            )
            response.raise_for_status()
            return response.json()
```

## Adding HubSpot to Your Requirements

Add the HubSpot Python SDK to your `requirements.txt`:

```
# HubSpot Integration
hubspot-api-client>=8.0.0
```

## API Endpoints for HubSpot Integration

Add these to your FastAPI router:

```python
# justdata/api/v1/hubspot.py
from fastapi import APIRouter, HTTPException
from justdata.apps.hubspot.client import HubSpotClient

router = APIRouter(prefix="/hubspot", tags=["hubspot"])

@router.get("/contacts/{contact_id}")
async def get_contact(contact_id: str):
    """Get HubSpot contact."""
    client = HubSpotClient()
    return await client.get_contact(contact_id)

@router.post("/sync/financial-data")
async def sync_financial_data(contact_id: str, data: dict):
    """Sync financial analysis data to HubSpot."""
    # Your integration logic here
    pass
```

## Next Steps

1. ✅ Fix npm permissions (Step 1)
2. ✅ Install HubSpot CLI (Step 2)
3. ✅ Initialize and authenticate (Steps 3-4)
4. ✅ Configure environment variables (Step 5)
5. 🔄 Create HubSpot integration module
6. 🔄 Install HubSpot Python SDK
7. 🔄 Implement API endpoints
8. 🔄 Test integration

## Troubleshooting

### Permission Errors
If you continue to see permission errors after fixing npm cache:
```bash
# Clear npm cache
npm cache clean --force

# Try installation again
npm install --save-dev @hubspot/cli
```

### Authentication Issues
If authentication fails:
1. Verify your access token is correct
2. Check token has necessary scopes
3. Ensure portal ID matches your account

### API Rate Limits
HubSpot has API rate limits:
- Free/Starter: 100 requests per 10 seconds
- Professional/Enterprise: 150-200 requests per 10 seconds

Implement rate limiting in your integration code.

## Resources

- [HubSpot CLI Documentation](https://developers.hubspot.com/docs/cms/guides/cli)
- [HubSpot API Reference](https://developers.hubspot.com/docs/api/overview)
- [HubSpot Python SDK](https://github.com/HubSpot/hubspot-api-python)
- [HubSpot Developer Community](https://community.hubspot.com/t5/APIs-Integrations/ct-p/APIs-Integrations)

## Support

For HubSpot-specific issues:
- HubSpot Developer Documentation
- HubSpot Developer Community
- HubSpot Support

For JustData integration issues:
- Contact: jedlebi@ncrc.org
- Project Repository: https://github.com/jadedlebi/justdata

