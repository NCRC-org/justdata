# IRS Form 990 Public API Options

## Overview

IRS Form 990 is the annual information return that tax-exempt organizations must file. This document outlines public APIs and data sources for accessing Form 990 data, which could be useful for enriching MemberView with nonprofit financial information.

## Available APIs

### 1. ProPublica Nonprofit Explorer API ⭐ **RECOMMENDED**

**URL**: https://www.propublica.org/nerds/announcing-the-nonprofit-explorer-api

**Features**:
- Free public API
- Access to data behind ProPublica's Nonprofit Explorer
- Over 3 million tax returns from tax-exempt organizations
- Organization profiles and full-text search
- Returns comprehensive data including:
  - Financial information
  - Leadership information
  - Activities and mission
  - Links to available Form 990 PDF files

**API Endpoints** (example):
- Organization search
- Organization profile by EIN
- Full-text search

**Use Case**: Best for general nonprofit data lookup and search

---

### 2. CharityAPI.org

**URL**: https://www.charityapi.org/

**Features**:
- Data sourced directly from IRS
- Fast search across ~1.7 million nonprofits
- Retrieve nonprofit data by EIN
- Check if nonprofit is a public charity (tax-deductible donations)
- Verify charitable status

**Use Case**: Good for quick EIN lookups and charity verification

---

### 3. Candid APIs (formerly GuideStar)

**URL**: https://candid.org/data/explore-apis/

**Available APIs**:
- **Nonprofit Search API**: Search and retrieve nonprofit information
- **Premier API**: Comprehensive nonprofit and foundation data
- **Charity Check API**: Verify charitable status

**Features**:
- Organization names and mission statements
- IRS BMF (Business Master File) information
- Financial data
- Comprehensive nonprofit profiles

**Use Case**: Most comprehensive data, may require API key/registration

---

### 4. Cause IQ API

**URL**: https://www.causeiq.com/help/reports-and-data/cause-iq-api/

**Features**:
- Access to Form 990 data
- Nonprofit finances, operations, and activities
- Fields include:
  - Tax period
  - Date scanned
  - URLs to download Form 990 PDFs

**Use Case**: Form 990 specific data with PDF access

---

### 5. IRS Form 990 Data on AWS (Raw Data)

**URL**: AWS S3 Public Dataset

**Features**:
- Over 1 million electronic Form 990 filings
- Filings from 2011 to present
- New data added monthly
- Each filing available as unique XML file
- Machine-readable format

**Access**:
- Direct S3 access
- Requires XML parsing
- Python library available: `990-xml-reader` (https://github.com/jsfenfen/990-xml-reader)

**Use Case**: For bulk data processing and custom analysis

---

## Comparison Table

| API | Cost | Data Coverage | Ease of Use | Best For |
|-----|------|---------------|-------------|----------|
| **ProPublica** | Free | 3M+ returns | ⭐⭐⭐⭐⭐ | General lookup, search |
| **CharityAPI** | Free/Paid | 1.7M nonprofits | ⭐⭐⭐⭐ | Quick EIN lookup |
| **Candid** | Free/Paid | Comprehensive | ⭐⭐⭐⭐ | Full profiles, detailed data |
| **Cause IQ** | Paid | Form 990 focused | ⭐⭐⭐ | Form 990 PDFs |
| **IRS AWS** | Free | 1M+ filings | ⭐⭐ | Bulk processing, custom analysis |

## Recommended Approach for MemberView

### Option 1: ProPublica API (Quick Start)
- **Pros**: Free, easy to use, good documentation
- **Cons**: May have rate limits
- **Implementation**: Simple REST API calls
- **Use Case**: Enrich member profiles with nonprofit financial data

### Option 2: IRS AWS + 990-XML-Reader (Advanced)
- **Pros**: Complete data, no API limits, free
- **Cons**: Requires XML parsing, more complex
- **Implementation**: Download XML files, parse with library
- **Use Case**: Bulk financial analysis, historical trends

### Option 3: Hybrid Approach
- Use ProPublica API for quick lookups
- Use IRS AWS for detailed financial analysis
- Cache results in MemberView database

## Implementation Example

### ProPublica API (Python)

```python
import requests

def get_nonprofit_by_ein(ein):
    """Get nonprofit data from ProPublica API."""
    url = f"https://projects.propublica.org/nonprofits/api/v2/organizations/{ein}.json"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None

# Example usage
org_data = get_nonprofit_by_ein("123456789")
if org_data:
    print(f"Organization: {org_data['organization']['name']}")
    print(f"Total Revenue: ${org_data['organization'].get('total_revenue', 'N/A')}")
```

### IRS AWS + 990-XML-Reader

```python
from irs_990_xml_reader import IRS990XMLReader

# Download XML from AWS S3
# Parse with library
reader = IRS990XMLReader(xml_file_path)
data = reader.get_data()
print(f"Total Revenue: {data.get('total_revenue')}")
```

## Integration with MemberView

### Potential Features

1. **Auto-Enrichment**: When viewing a member company, automatically fetch Form 990 data if EIN is available
2. **Financial Comparison**: Compare member-reported financials with IRS Form 990 data
3. **Compliance Check**: Verify nonprofit status and tax-exempt status
4. **Historical Trends**: Track financial trends over multiple years
5. **Revenue Analysis**: Analyze revenue sources and expenses

### Data Fields to Extract

- Organization name and EIN
- Total revenue
- Total expenses
- Net assets
- Program expenses
- Administrative expenses
- Fundraising expenses
- Executive compensation
- Board member information
- Mission statement
- Activities description

## Next Steps

1. **Choose API**: Start with ProPublica API for simplicity
2. **Get API Key**: If required, register for API access
3. **Create Utility Module**: `utils/irs_990_client.py`
4. **Add to MemberView**: Integrate into member detail view
5. **Cache Results**: Store fetched data to reduce API calls

## Resources

- ProPublica API Docs: https://projects.propublica.org/nonprofits/api
- CharityAPI Docs: https://www.charityapi.org/docs
- Candid API Docs: https://candid.org/data/explore-apis/
- 990-XML-Reader: https://github.com/jsfenfen/990-xml-reader
- IRS AWS Dataset: https://registry.opendata.aws/irs-990/

## Notes

- Most APIs require EIN (Employer Identification Number) for lookups
- Consider rate limiting and caching strategies
- Some APIs may require registration or have usage limits
- IRS AWS data is free but requires processing XML files
- ProPublica API is free and easiest to start with

