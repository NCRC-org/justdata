# Candid API Reference (Foundation Directory Online)

**Portal**: https://developer.candid.org/
**Status**: Free 30-day trial requested (Feb 2026). Expect credentials within 2 business days.
**Auth**: API subscription key (available on profile page after login)

## APIs Available

| API | Price/yr | Description |
|-----|----------|-------------|
| Grants API | $6,000 | Search/filter grants, funders, recipients, funding activity |
| Essentials API | $4,800 | 1.6M+ nonprofits, 40+ data fields |
| Premier API | $9,900 | 760+ fields, financials, personnel, IRS compliance |
| Charity Check API | $2,750 | IRS/state compliance verification |
| News API | $3,300 | Real-time social sector news from 65K+ sources |
| Nonprofit Eligibility API | $5,000 | Validates eligibility for payment donations |
| Demographics API | Free | Race, ethnicity, gender identity data |
| Taxonomy API | Free | Philanthropy Classification System (PCS) |

## Grants API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/transactions` | Granular grant details (funder, recipient, amounts) |
| `/funders` | Aggregated funder giving totals with dollar amounts and grant counts |
| `/recipients` | Nonprofit funding filtered by subject, location, demographics |
| `/summary` | Aggregate funding totals, funder/recipient counts, grant values |

### Search/Filter Capabilities
- PCS codes and keywords
- Funder and recipient information
- Geographic location
- Grant amount ranges
- Contemporary funding topics (e.g., Covid-19 relief, racial equity)
- Grant dates and update timestamps

### Data Sources
- IRS Forms 990 and 990-PF
- Direct reporting from foundations
- Foundation websites and annual reports
- 35+ monitored information sources
- Updated every business day (Mon-Fri)

## Key Notes

- **FDO account is separate from API access** — existing Foundation Directory Online membership does not include API keys
- Free trial: candid.org/api-free-trial
- Production subscriptions: candid.org/api-info-request
- Pre-built connectors exist for Salesforce; C#/.NET SDK available
- Formerly known as Foundation Center / GuideStar

## Links

- Developer Portal: https://developer.candid.org/
- Grants API Docs: https://developer.candid.org/reference/get-started-with-grants-api
- API Pricing: https://candid.org/use-our-data/apis
- Getting Access: https://developer.candid.org/reference/getting-access
- Grants API FAQs: https://developer.candid.org/reference/faqs-grants-api
