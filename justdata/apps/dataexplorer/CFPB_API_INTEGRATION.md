# CFPB HMDA API Integration Guide

**Date:** January 27, 2025  
**Status:** Planning - APIs to be integrated with DataExplorer

---

## Overview

DataExplorer will integrate with the following CFPB HMDA APIs alongside existing BigQuery, Census, and Claude APIs:

1. **HMDA Auth API** - Authentication and user management
2. **HMDA Filing Platform API** - Filing and submission management

**Primary Use Case:** Get institution metadata (name, LEI, RSSD) from CFPB APIs, then use these identifiers to query BigQuery data sources (HMDA, SOD25, Disclosure, lenders/lenders18 tables).

**Data Flow:**
1. CFPB API → Get institution info (name, LEI, RSSD)
2. Use LEI/RSSD → Query BigQuery HMDA data
3. Use RSSD → Query BigQuery SOD25 (branch data)
4. Use LEI → Query BigQuery Disclosure (small business data)
5. Use identifiers → Link to lenders/lenders18 lookup tables

---

## API Endpoints

### 1. HMDA Auth API

**Base URL:** `https://ffiec.cfpb.gov/hmda-auth/`

**Authentication:**
- Requires Login.gov account (as of January 1, 2025)
- Bearer token obtained from HMDA Platform profile → Developer Settings
- Token used in `Authorization: Bearer {token}` header

**Key Endpoints:**

#### User Management
- `POST /users/` - Update user attributes (firstName, lastName, leis)
- `GET /users/` - Get current user information

**Example Request:**
```python
import requests

headers = {
    'Authorization': f'Bearer {bearer_token}',
    'Content-Type': 'application/json'
}

# Update user
response = requests.post(
    'https://ffiec.cfpb.gov/hmda-auth/users/',
    headers=headers,
    json={
        'firstName': 'John',
        'lastName': 'Doe',
        'leis': ['LEI123456789']
    }
)
```

#### Institution Lookup
- `GET /v2/public/institutions?domain={emailDomain}` - Get institutions by email domain

**Example:**
```python
response = requests.get(
    'https://ffiec.cfpb.gov/v2/public/institutions',
    params={'domain': 'example.com'}
)
```

---

### 2. HMDA Filing Platform API

**Base URL:** `https://ffiec.cfpb.gov/hmda-platform/`

**Authentication:**
- Same bearer token as Auth API
- Required for all endpoints

**Key Endpoints:**

#### Filing Management
- `POST /filings` - Create a new filing
- `GET /filings/{filingId}` - Get filing details
- `GET /filings` - List all filings

#### Submission Management
- `POST /filings/{filingId}/submissions` - Create a submission
- `GET /filings/{filingId}/submissions/{submissionId}` - Get submission details
- `POST /filings/{filingId}/submissions/{submissionId}/upload` - Upload HMDA file
- `GET /filings/{filingId}/submissions/{submissionId}/status` - Check submission status

#### Validation
- `GET /filings/{filingId}/submissions/{submissionId}/edits` - Get edit reports
- `POST /filings/{filingId}/submissions/{submissionId}/validate` - Validate submission

#### Signing
- `POST /filings/{filingId}/submissions/{submissionId}/sign` - Sign submission

---

## Integration Plan for DataExplorer

### Phase 1: Authentication Setup

**Create:** `apps/dataexplorer/utils/cfpb_client.py`

```python
import requests
import os
from typing import Optional, Dict, List

class CFPBClient:
    """Client for CFPB HMDA APIs"""
    
    def __init__(self, bearer_token: Optional[str] = None):
        self.bearer_token = bearer_token or os.getenv('CFPB_BEARER_TOKEN')
        self.auth_base = 'https://ffiec.cfpb.gov/hmda-auth'
        self.platform_base = 'https://ffiec.cfpb.gov/hmda-platform'
        
    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers"""
        if not self.bearer_token:
            raise ValueError("CFPB Bearer Token required")
        return {
            'Authorization': f'Bearer {self.bearer_token}',
            'Content-Type': 'application/json'
        }
    
    def get_user_info(self) -> Dict:
        """Get current user information"""
        response = requests.get(
            f'{self.auth_base}/users/',
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    def get_institutions_by_domain(self, email_domain: str) -> List[Dict]:
        """Get institutions associated with email domain"""
        response = requests.get(
            f'{self.auth_base}/v2/public/institutions',
            params={'domain': email_domain},
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    def get_institution_by_name(self, name: str) -> Optional[Dict]:
        """
        Get institution metadata (name, LEI, RSSD) by name.
        This is the primary method for DataExplorer lender lookup.
        
        Returns:
            {
                'name': 'Wells Fargo Bank, NA',
                'lei': 'INR2EJN1ERAN0W5ZP974',
                'rssd': '451965',
                'type': 'Bank',
                ...
            }
        """
        # Implementation depends on available CFPB API endpoints
        # May need to search institutions endpoint or use filing platform
        # For now, placeholder - actual implementation depends on API docs
        pass
    
    def get_institution_by_lei(self, lei: str) -> Optional[Dict]:
        """Get institution metadata by LEI"""
        # Implementation depends on available endpoints
        pass
    
    def get_institution_by_rssd(self, rssd: str) -> Optional[Dict]:
        """Get institution metadata by RSSD"""
        # Implementation depends on available endpoints
        pass
```

### Phase 2: Lender Lookup Enhancement

**Enhance:** `apps/dataexplorer/data_utils.py`

Use CFPB API to get institution metadata, then use identifiers to query BigQuery:

```python
from apps.dataexplorer.utils.cfpb_client import CFPBClient

def lookup_lender_enhanced(lender_name: str, exact_match: bool = False):
    """
    Enhanced lender lookup using CFPB API to get institution metadata,
    then linking to BigQuery data sources.
    
    Returns lender info with LEI and RSSD for querying:
    - HMDA data (using LEI)
    - SOD25 branch data (using RSSD)
    - Disclosure small business data (using LEI)
    - lenders/lenders18 lookup tables (using LEI/RSSD)
    """
    results = []
    
    # Try CFPB API first to get authoritative institution data
    try:
        cfpb_client = CFPBClient()
        # Get institution info: name, LEI, RSSD
        institution_data = cfpb_client.get_institution_by_name(lender_name)
        
        if institution_data:
            # Enrich with BigQuery data using identifiers
            lei = institution_data.get('lei')
            rssd = institution_data.get('rssd')
            
            # Query BigQuery lenders table to get additional info
            if lei or rssd:
                bq_lender_info = get_lender_from_bigquery(lei=lei, rssd=rssd)
                institution_data.update(bq_lender_info or {})
            
            results.append(institution_data)
    except Exception as e:
        logger.warning(f"CFPB API unavailable: {e}")
    
    # Fallback to BigQuery-only lookup if CFPB fails
    if not results:
        results = lookup_lender(lender_name, exact_match)
    
    return results

def get_lender_from_bigquery(lei: str = None, rssd: str = None):
    """
    Query BigQuery lenders/lenders18 tables using LEI or RSSD.
    Links CFPB institution data to BigQuery lender records.
    """
    client = get_bigquery_client(PROJECT_ID)
    
    if lei:
        query = f"""
        SELECT DISTINCT
            lei,
            lender_name,
            rssd_id,
            institution_type
        FROM `{PROJECT_ID}.hmda.lenders`
        WHERE lei = '{escape_sql_string(lei)}'
        ORDER BY lender_name
        LIMIT 1
        """
    elif rssd:
        query = f"""
        SELECT DISTINCT
            lei,
            lender_name,
            rssd_id,
            institution_type
        FROM `{PROJECT_ID}.hmda.lenders18`
        WHERE rssd_id = '{escape_sql_string(rssd)}'
        ORDER BY lender_name
        LIMIT 1
        """
    else:
        return None
    
    results = execute_query(client, query)
    return results[0] if results else None
```

### Phase 3: Filing Status Integration

**Add:** Filing status checking for lenders

```python
def get_lender_filing_status(lei: str, year: int) -> Dict:
    """
    Check HMDA filing status for a lender using CFPB API.
    Returns filing status, submission dates, validation status.
    """
    cfpb_client = CFPBClient()
    # Implementation to check filing status
    # This would require additional API endpoints or data
    pass
```

---

## Environment Variables

### Required
- `CFPB_BEARER_TOKEN` - Bearer token from HMDA Platform Developer Settings

### Optional
- `CFPB_API_ENABLED` - Enable/disable CFPB API integration (default: false)
- `CFPB_API_TIMEOUT` - Request timeout in seconds (default: 30)

---

## Authentication Flow

### Getting a Bearer Token

1. **Create Login.gov Account**
   - Navigate to HMDA Filing Platform
   - Click "Sign in with LOGIN.GOV"
   - Register with institution-associated business email
   - Complete MFA setup

2. **Obtain Bearer Token**
   - Log into HMDA Platform
   - Click profile (top-right corner)
   - Scroll to "Developer Settings"
   - Click "Copy Auth Token"

3. **Store Token**
   - Add to environment variables: `CFPB_BEARER_TOKEN`
   - Or store securely in secrets management system

---

## Use Cases for DataExplorer

### 1. Institution Metadata Lookup (Primary Use)
**Purpose:** Get authoritative institution identifiers (name, LEI, RSSD) from CFPB API

**Workflow:**
1. User searches for lender name (e.g., "Wells Fargo")
2. CFPB API returns: `{name: "Wells Fargo Bank, NA", lei: "INR2EJN1ERAN0W5ZP974", rssd: "451965"}`
3. Use LEI to query BigQuery HMDA data: `SELECT * FROM hmda.hmda WHERE lei = 'INR2EJN1ERAN0W5ZP974'`
4. Use RSSD to query BigQuery SOD25: `SELECT * FROM branches.sod25 WHERE rssd_id = '451965'`
5. Use LEI to query BigQuery Disclosure: `SELECT * FROM sb.disclosure WHERE lei = 'INR2EJN1ERAN0W5ZP974'`
6. Link to lenders/lenders18 tables for additional metadata

**Benefits:**
- Authoritative source for institution identifiers
- Ensures correct LEI/RSSD mapping
- Enables cross-dataset queries (HMDA + Branch + SB data)

### 2. Linking Multiple Data Sources
**Purpose:** Use CFPB identifiers to join data across BigQuery tables

**Example:**
```python
# Get institution from CFPB
institution = cfpb_client.get_institution("Wells Fargo")
lei = institution['lei']
rssd = institution['rssd']

# Query all data sources using identifiers
hmda_data = query_hmda_by_lei(lei)
branch_data = query_sod25_by_rssd(rssd)
sb_data = query_disclosure_by_lei(lei)
lender_metadata = query_lenders_table(lei, rssd)

# Combine for comprehensive analysis
combined_analysis = {
    'institution': institution,
    'hmda': hmda_data,
    'branches': branch_data,
    'small_business': sb_data,
    'metadata': lender_metadata
}
```

### 3. Data Validation & Verification
- Verify LEI/RSSD accuracy before querying BigQuery
- Cross-reference institution names across sources
- Identify data quality issues (missing LEI, incorrect RSSD)

### 4. Enhanced Lender Analysis
- Get complete institution profile (name, LEI, RSSD, type)
- Query all related data sources automatically
- Display comprehensive lender information in analysis

---

## Integration with Existing APIs

### Current Stack
- **BigQuery** - Primary data source (HMDA, SB, Branch data)
- **Census API** - Demographic data (via `CENSUS_API_KEY`)
- **Claude API** - AI analysis and narratives (via `CLAUDE_API_KEY`)

### New Addition
- **CFPB HMDA APIs** - Authentication, filing status, institution verification

### Combined Workflow Example

```python
# 1. Get institution metadata from CFPB API (name, LEI, RSSD)
institution = cfpb_client.get_institution_by_name("Wells Fargo")
lei = institution['lei']  # e.g., "INR2EJN1ERAN0W5ZP974"
rssd = institution['rssd']  # e.g., "451965"

# 2. Query BigQuery using identifiers
# HMDA data (using LEI)
hmda_data = execute_hmda_query(
    geoids=geoids, 
    years=years, 
    lender_id=lei  # Use LEI from CFPB
)

# Branch data (using RSSD)
branch_data = execute_branch_query(
    geoids=geoids,
    years=years,
    lender_id=rssd  # Use RSSD from CFPB
)

# Small Business data (using LEI)
sb_data = execute_sb_query(
    geoids=geoids,
    years=years,
    lender_id=lei  # Use LEI from CFPB
)

# Link to lenders/lenders18 tables
lender_metadata = query_lenders_table(lei=lei, rssd=rssd)

# 3. Get demographics (Census API)
demographics = get_census_data_for_geoids(geoids)

# 4. Generate AI analysis (Claude API)
ai_analysis = generate_ai_narrative(
    hmda_data=hmda_data,
    branch_data=branch_data,
    sb_data=sb_data,
    demographics=demographics
)

# 5. Combine all data for comprehensive lender analysis
lender_analysis = {
    'institution': institution,  # From CFPB API
    'hmda': hmda_data,  # From BigQuery using LEI
    'branches': branch_data,  # From BigQuery using RSSD
    'small_business': sb_data,  # From BigQuery using LEI
    'metadata': lender_metadata,  # From BigQuery lenders tables
    'demographics': demographics,  # From Census API
    'ai_analysis': ai_analysis  # From Claude API
}
```

---

## Error Handling

### CFPB API Errors
- **401 Unauthorized** - Invalid or expired token
- **403 Forbidden** - Insufficient permissions
- **404 Not Found** - Resource doesn't exist
- **429 Too Many Requests** - Rate limit exceeded
- **500 Server Error** - CFPB API issue

### Fallback Strategy
- Always fallback to BigQuery if CFPB API fails
- Log errors but don't block user workflow
- Show warning if CFPB data unavailable

---

## Rate Limiting

**CFPB API Limits:**
- Check API documentation for specific limits
- Implement rate limiting in client
- Cache responses when appropriate

**Implementation:**
```python
from time import time
from functools import wraps

class RateLimiter:
    def __init__(self, max_calls: int, period: int):
        self.max_calls = max_calls
        self.period = period
        self.calls = []
    
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time()
            self.calls = [c for c in self.calls if c > now - self.period]
            
            if len(self.calls) >= self.max_calls:
                raise RateLimitError("Rate limit exceeded")
            
            self.calls.append(now)
            return func(*args, **kwargs)
        return wrapper
```

---

## Testing

### Test Environment
- Use HMDA Beta Filing Platform for testing
- Sandbox environment without regulatory implications
- Test authentication and API calls

### Test Checklist
- [ ] Bearer token authentication works
- [ ] User info endpoint responds
- [ ] Institution lookup works
- [ ] Error handling works correctly
- [ ] Fallback to BigQuery works
- [ ] Rate limiting implemented

---

## Security Considerations

1. **Token Storage**
   - Never commit tokens to git
   - Use environment variables or secrets management
   - Rotate tokens regularly

2. **API Security**
   - Use HTTPS only
   - Validate all responses
   - Sanitize user inputs

3. **Error Messages**
   - Don't expose tokens in error messages
   - Log errors server-side only
   - User-friendly error messages

---

## Next Steps

1. **Create CFPB Client**
   - Implement `apps/dataexplorer/utils/cfpb_client.py`
   - Add authentication handling
   - Implement rate limiting

2. **Integrate with Lender Lookup**
   - Enhance `lookup_lender()` function
   - Add CFPB API as data source
   - Implement fallback logic

3. **Add Filing Status Feature**
   - Create endpoint to check filing status
   - Display in lender analysis
   - Add to report generation

4. **Update Documentation**
   - Add CFPB API to requirements
   - Update environment variable docs
   - Add API usage examples

---

## References

- **HMDA Auth API:** https://ffiec.cfpb.gov/documentation/api/hmda-auth/
- **HMDA Filing Platform API:** https://ffiec.cfpb.gov/documentation/api/filing/platform
- **Login.gov Setup:** https://ffiec.cfpb.gov/documentation/faq/login-gov-quick-reference

---

**Status:** Ready for implementation after Render testing phase.
