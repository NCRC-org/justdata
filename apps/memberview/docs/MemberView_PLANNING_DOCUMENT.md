# MemberView Application Planning Document

## Executive Summary

MemberView will be a user-friendly interface for extracting and analyzing NCRC member data from HubSpot. This document reviews the available HubSpot data schemas, identifies data gaps, and proposes features for tracking membership, retention, contacts, engagement, donors, dues, and financial information.

## Current HubSpot Data Structure

### 1. Contacts Table
- **Location**: `HubSpot/data/processed/20251114_123115_all-contacts_processed.parquet`
- **Records**: 108,403 contacts
- **Columns**: 12 columns (after processing)
- **Key Fields** (based on codebase analysis):
  - Email address
  - First name / Last name
  - Phone
  - Associated company (join key to companies)
  - Address fields (city, state, country)
  - Date fields (created, updated, last activity)
  - Engagement metrics

**Data Quality**: 
- Contacts have company associations but completeness varies
- Engagement data may be limited

### 2. Deals Table
- **Location**: `HubSpot/data/processed/20251114_123117_all-deals_processed.parquet`
- **Records**: 6,628 deals
- **Columns**: 617 columns (very wide dataset)
- **Key Fields** (identified from scripts):
  - `membership_status_when_renewing` - Membership status at renewal time
  - `membership_expiration_date` - When membership expires
  - `amount` - Deal amount (financial data)
  - `Associated Company IDs (Primary)` - Join key to companies
  - `Associated Contact IDs` - Join key to contacts
  - `Deal Name` - Contains membership/renewal information
  - `Deal Stage` - Status (e.g., "Closed won", "Closed Won & Paid")
  - `Close Date` - When deal was closed
  - Multiple date fields for tracking

**Data Quality**:
- 617 columns suggests many custom fields
- Financial data exists but may need standardization
- Membership deals can be identified by deal name patterns ("Renewal by", "New Membership by")
- Some deals are excluded: "Just Club", "Council Dues", individual donors

### 3. Companies Table
- **Location**: `HubSpot/data/raw/hubspot-crm-exports-all-companies-2025-11-14.csv`
- **Status**: Exists but not yet processed to parquet format
- **Key Fields** (from scripts):
  - `Record ID` - Primary key (join key)
  - `Company name` - Company name
  - `Membership Status` - Current membership status (CURRENT, LAPSED, GRACE, etc.)
  - `Create Date` - When company record created
  - `Last Activity Date` - Last engagement date

**Data Quality**:
- Companies table is the source of truth for membership status
- Needs to be processed and standardized
- Contains direct membership status field

## Join Relationships

### Primary Joins

1. **Companies ↔ Deals**
   - Join Key: `Companies['Record ID'] = Deals['Associated Company IDs (Primary)']`
   - Relationship: One company can have many deals
   - Use Case: Track all financial transactions per member

2. **Companies ↔ Contacts**
   - Join Key: `Companies['Record ID'] = Contacts['associated_company']` (or similar)
   - Relationship: One company can have many contacts
   - Use Case: See all contacts associated with each member organization

3. **Deals ↔ Contacts**
   - Join Key: `Deals['Associated Contact IDs'] = Contacts['id']`
   - Relationship: Deals can be associated with specific contacts
   - Use Case: Track which contacts are involved in transactions

4. **Contacts ↔ Companies** (via deals)
   - Indirect relationship through deals
   - Use Case: Find contacts who have been involved in member transactions

## Data Gaps and Limitations

### Missing or Incomplete Data

1. **Companies Data Processing**
   - Companies CSV exists but not processed to parquet
   - Need to standardize column names and data types
   - Action: Process companies data similar to contacts/deals

2. **Financial Data Standardization**
   - 617 columns in deals suggests many custom fields
   - Need to identify which fields contain:
     - Membership dues amounts
     - Donor contributions
     - Other financial transactions
   - Action: Analyze deals columns to map financial fields

3. **Engagement Metrics**
   - Contacts have engagement fields but completeness unknown
   - Need to identify:
     - Email opens/clicks
     - Meeting attendance
     - Event participation
     - Report downloads
   - Action: Review engagement fields in contacts and deals

4. **Historical Status Tracking**
   - Current status exists but historical changes may be limited
   - Deals contain `membership_status_when_renewing` but may not track all changes
   - Action: Use deal dates to reconstruct status history

5. **Contact-to-Member Association**
   - Contacts have company associations but may be incomplete
   - Some contacts may not be properly linked to member companies
   - Action: Improve contact-company matching

## Proposed MemberView Features

### 1. Membership Management Dashboard

#### Current Membership Overview
- **Total Members**: Count of companies with CURRENT status
- **Status Breakdown**: CURRENT, LAPSED, GRACE, PENDING, etc.
- **New Members This Year**: Companies with first membership deal in current year
- **Renewals This Year**: Companies with renewal deals in current year
- **At-Risk Members**: Members approaching expiration (within 90 days)

**Data Sources**:
- Companies table: `Membership Status` field
- Deals table: Filter by deal name patterns and deal stage
- Join: Companies + Deals to get complete picture

#### Membership Retention Analysis
- **Retention Rate**: % of members who renewed vs. lapsed
- **Churn Analysis**: Members who lapsed in last 12 months
- **Retention by Cohort**: Track retention by year joined
- **Time to Renewal**: Average days between renewals

**Data Sources**:
- Deals table: Deal dates and amounts
- Companies table: Status changes
- Calculate: Time between renewal deals per company

### 2. Member Financial Dashboard

#### Dues and Payments
- **Total Dues Collected**: Sum of membership deal amounts
- **Dues by Year**: Annual dues revenue
- **Outstanding Dues**: Members with unpaid deals
- **Payment History**: Timeline of all payments per member

**Data Sources**:
- Deals table: `amount` field filtered to membership deals
- Deal stage: "Closed Won & Paid" for confirmed payments
- Deal dates: For time-series analysis

#### Donor Information
- **Total Donations**: Sum of donor deal amounts
- **Donors by Year**: Annual donor contributions
- **Top Donors**: Highest contributing organizations/individuals
- **Donor Retention**: Repeat donors vs. one-time

**Data Sources**:
- Deals table: Filter by deal name/type for donations
- Exclude: Membership dues deals
- May need to identify donor-specific deal types

#### Financial Trends
- **Revenue Trends**: Monthly/quarterly revenue from dues and donations
- **Average Dues**: Average membership dues amount
- **Dues by Tier**: If membership tiers exist, revenue by tier

**Data Sources**:
- Deals table: Amount and date fields
- Group by: Deal type, date, company

### 3. Contact Management

#### Contacts per Member
- **Total Contacts**: Count of contacts associated with each member company
- **Primary Contacts**: Identify main contact per member (e.g., most recent deal contact)
- **Contact Roles**: If available, show contact roles/titles
- **Contact Engagement**: Activity level per contact

**Data Sources**:
- Contacts table: Company associations
- Deals table: Contact associations
- Join: Companies → Contacts (via associated_company)

#### Engagement Tracking
- **Email Engagement**: Opens, clicks (if available in HubSpot)
- **Meeting Attendance**: Track meetings/events attended
- **Report Access**: Track which members accessed reports
- **Engagement Score**: Composite score based on activities

**Data Sources**:
- Contacts table: Engagement fields
- Deals table: Activity dates
- May need HubSpot API for real-time engagement data

### 4. Member Details View

#### Individual Member Profile
For each member company, show:
- **Basic Info**: Company name, status, join date
- **Contact Information**: All associated contacts
- **Payment History**: All deals/transactions
- **Status History**: Timeline of status changes
- **Engagement Summary**: Recent activities
- **Notes**: Any notes or custom fields

**Data Sources**:
- Companies table: Core member info
- Contacts table: Associated contacts
- Deals table: Transaction history
- Join all three tables

### 5. Reporting and Analytics

#### Custom Reports
- **Member List Export**: Export member data with selected fields
- **Financial Reports**: Revenue, dues, donations by time period
- **Retention Reports**: Churn analysis, retention rates
- **Engagement Reports**: Member activity summaries

#### Visualizations
- **Membership Trends**: Line chart of member count over time
- **Revenue Trends**: Revenue by month/quarter
- **Status Distribution**: Pie chart of membership statuses
- **Geographic Distribution**: Map of members by location (if address data available)

## Technical Implementation Recommendations

### 1. Data Processing Pipeline

```
Raw HubSpot Exports
    ↓
Process to Standardized Format
    ↓
Create Unified Member View (Companies + Deals + Contacts)
    ↓
Calculate Derived Metrics (retention, engagement scores)
    ↓
Store in Queryable Format (Parquet/CSV/Database)
```

### 2. Data Model

#### Core Tables
1. **members** (from Companies)
   - member_id (Record ID)
   - company_name
   - membership_status
   - join_date
   - last_activity_date
   - address fields

2. **member_deals** (from Deals, filtered to membership)
   - deal_id
   - member_id
   - deal_type (membership, renewal, donation)
   - amount
   - deal_date
   - status
   - expiration_date

3. **member_contacts** (from Contacts)
   - contact_id
   - member_id
   - email
   - name
   - role (if available)
   - engagement_score

4. **member_financial_summary** (calculated)
   - member_id
   - total_dues_paid
   - total_donations
   - last_payment_date
   - next_renewal_date
   - payment_frequency

### 3. Key Metrics to Calculate

#### Membership Metrics
- Current member count
- New members (last 30/90/365 days)
- Lapsed members (last 30/90/365 days)
- Renewal rate (%)
- Average membership duration
- Churn rate (%)

#### Financial Metrics
- Total revenue (dues + donations)
- Average dues amount
- Revenue by month/quarter/year
- Outstanding dues amount
- Payment completion rate

#### Engagement Metrics
- Active contacts per member
- Average engagement score
- Members with recent activity
- Email open/click rates (if available)

## Data Quality Improvements Needed

### Immediate Actions

1. **Process Companies Data**
   - Convert CSV to parquet format
   - Standardize column names
   - Validate membership status values

2. **Map Financial Fields**
   - Identify all financial-related columns in deals
   - Standardize field names
   - Validate data types (amounts as numeric)

3. **Improve Join Quality**
   - Verify join keys work correctly
   - Handle missing associations
   - Create fallback matching (name-based if ID missing)

4. **Enrich Engagement Data**
   - Identify engagement fields in contacts
   - Calculate engagement scores
   - Track activity timelines

### Future Enhancements

1. **Real-time Data Sync**
   - Connect to HubSpot API for live data
   - Update member view automatically
   - Track changes in real-time

2. **Data Validation Rules**
   - Validate membership status transitions
   - Flag data inconsistencies
   - Alert on missing required fields

3. **Historical Reconstruction**
   - Use deal dates to build status history
   - Track status changes over time
   - Create time-series datasets

## User Interface Recommendations

### Dashboard Layout

1. **Top Section**: Key Metrics Cards
   - Total Members
   - Current Members
   - Revenue (MTD, YTD)
   - Retention Rate

2. **Middle Section**: Charts
   - Membership Trend (line chart)
   - Status Distribution (pie chart)
   - Revenue Trend (bar chart)

3. **Bottom Section**: Tables
   - Recent Members
   - Upcoming Renewals
   - At-Risk Members

### Member Search and Filter

- Search by company name
- Filter by status
- Filter by date ranges
- Filter by financial criteria (dues amount, etc.)

### Member Detail Page

- Tabbed interface:
  - Overview (basic info, status)
  - Contacts (all associated contacts)
  - Financial (payment history, dues, donations)
  - Engagement (activity timeline)
  - History (status changes, notes)

## Next Steps

1. **Data Analysis Phase** (Week 1)
   - Run schema analysis script on all tables
   - Identify all financial fields in deals
   - Map engagement fields in contacts
   - Verify join keys work correctly

2. **Data Processing Phase** (Week 2)
   - Process companies data to parquet
   - Create unified member view
   - Calculate derived metrics
   - Validate data quality

3. **Prototype Development** (Week 3-4)
   - Build basic dashboard
   - Create member detail view
   - Implement search/filter
   - Add basic visualizations

4. **Enhancement Phase** (Ongoing)
   - Add advanced analytics
   - Improve engagement tracking
   - Add reporting features
   - Connect to HubSpot API for real-time updates

## Questions to Resolve

1. **Financial Data**:
   - Are donations tracked separately from dues in deals?
   - What fields contain membership dues amounts?
   - Are there different membership tiers with different dues?

2. **Engagement Data**:
   - What engagement metrics are available in HubSpot?
   - Can we track email opens/clicks?
   - Are event attendance records available?

3. **Status Management**:
   - How is membership status updated in HubSpot?
   - Are status changes logged/historical?
   - What triggers status changes?

4. **Contact Association**:
   - How are contacts linked to member companies?
   - Are there contact roles (primary, billing, etc.)?
   - How complete is the contact-company association?

## Conclusion

The HubSpot data contains a solid foundation for MemberView, with:
- ✅ Companies table with membership status
- ✅ Deals table with financial transactions
- ✅ Contacts table with engagement data
- ✅ Clear join relationships between tables

However, significant work is needed to:
- ⚠️ Process and standardize companies data
- ⚠️ Map and standardize financial fields
- ⚠️ Calculate derived metrics
- ⚠️ Build unified member view

With proper data processing and a well-designed interface, MemberView can provide comprehensive membership, financial, and engagement tracking that is much more user-friendly than navigating HubSpot directly.

