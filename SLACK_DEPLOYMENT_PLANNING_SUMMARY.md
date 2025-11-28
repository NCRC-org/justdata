# Just Data Platform - Slack Deployment Planning Summary

## Platform Overview

**Just Data** (also referred to as **NCRC JustData Platform**) is a comprehensive financial data analysis platform developed by the National Community Reinvestment Coalition (NCRC). The platform provides web-based tools for analyzing banking, mortgage lending, and small business lending data to support fair lending compliance, community reinvestment assessment, and market analysis.

### Platform Architecture
- **Technology Stack**: Python 3.11+, Flask web framework, Google BigQuery for data storage
- **AI Integration**: Anthropic Claude 4 Sonnet for narrative report generation
- **Deployment**: Currently runs locally on multiple ports; designed for cloud deployment
- **Data Sources**: FDIC Summary of Deposits (SOD), HMDA mortgage data, Small Business lending data (Section 1071), U.S. Census Bureau demographics

### Key Platform Features
- Interactive web-based interfaces for all applications
- Real-time progress tracking with server-sent events
- AI-powered narrative report generation
- Multiple export formats (Excel, CSV, JSON, PDF, ZIP)
- Responsive design for mobile and desktop
- BigQuery integration for large-scale data analysis

---

## Landing Page

**Status**: Currently, applications run independently on separate ports. A unified landing page is recommended but not yet fully implemented.

**Recommended Landing Page Structure**:
- **Header**: "NCRC JustData Platform"
- **Main Section**: Grid of application cards (6-7 applications)
- **Each Card Should Include**:
  - Application name and icon
  - Brief description (1-2 sentences)
  - Key features (3-4 bullet points)
  - Status badge (Ready/In Development)
  - "Launch" button linking to the app

**Current Access Pattern**: Each application runs on its own port and can be accessed directly via URL.

---

## Application Suite

### 1. **BranchSeeker** - Bank Branch Location Analysis
**Port**: 8080  
**URL**: http://127.0.0.1:8080  
**Status**: ✅ Fully Functional

**Description**:  
Analyzes FDIC Summary of Deposits (SOD) data to track bank branch locations, market concentration, and branch network changes over time. Essential for understanding banking access patterns and market competition.

**Key Features**:
- County, state, and metro area analysis
- Market concentration analysis (HHI - Herfindahl-Hirschman Index calculations)
- Year-over-year trend analysis (2017-2025)
- LMI (Low-to-Moderate Income) and MMCT (Majority-Minority Census Tract) analysis
- AI-powered insights and narrative summaries using Claude 4 Sonnet
- Excel, CSV, JSON, and ZIP export options
- Interactive web reports with collapsible tables
- Real-time progress tracking with detailed substeps

**Data Sources**:
- FDIC Summary of Deposits (SOD) - 2017-2025
- Branch locations, deposits, service types
- Census tract demographics for LMI/MMCT analysis

**Use Cases**:
- Assessing banking access in underserved communities
- Analyzing branch network changes over time
- Market concentration analysis for merger reviews
- CRA (Community Reinvestment Act) compliance assessment

**Target Users**: Community advocates, bank analysts, CRA officers, researchers

---

### 2. **LendSight** - Mortgage Lending Analysis
**Port**: 8082  
**URL**: http://127.0.0.1:8082  
**Status**: ✅ Fully Functional (Version 0.9.0)

**Description**:  
Analyzes Home Mortgage Disclosure Act (HMDA) mortgage lending data to assess lending patterns, disparities, and fair lending compliance. Generates comprehensive written reports with demographic context and AI-generated insights.

**Key Features**:
- Multi-county analysis (up to 3 counties simultaneously)
- HMDA data analysis (2018-2024)
- Census demographic integration (2010, 2020, 2024 ACS)
- Loan purpose filtering (home purchase, refinance, home equity)
- AI-generated narrative reports with multiple sections:
  - Executive Summary
  - Population Demographics
  - Lending Trends
  - Demographic Analysis
  - Lender-Specific Analysis
- Analysis by demographic group (race/ethnicity, income, neighborhood)
- Analysis by individual bank/lender
- Excel and PDF export options
- Weighted average aggregation for multi-county analysis

**Data Sources**:
- HMDA mortgage lending data (BigQuery)
- U.S. Census Bureau demographic data (Decennial Census and ACS)
- FIPS code integration for geographic accuracy

**Use Cases**:
- Fair lending compliance assessment
- Identifying lending disparities by demographic group
- Lender performance evaluation
- Community lending pattern analysis
- Regulatory compliance reporting

**Target Users**: Fair lending advocates, bank compliance officers, community organizations, researchers, regulators

---

### 3. **BranchMapper** - Interactive Branch Map
**Port**: 8084  
**URL**: http://127.0.0.1:8084  
**Status**: ✅ Fully Functional

**Description**:  
Interactive map visualization of bank branch locations with geographic filtering and detailed branch information. Provides visual representation of banking access patterns.

**Key Features**:
- Interactive map with Leaflet.js
- State and county selection filters
- Branch location markers with popup details
- Branch details including:
  - Bank name and branch name
  - Address and coordinates
  - Deposit amounts
  - Service types
- Export map and data functionality
- Real-time filtering by geography
- Visual representation of branch density

**Data Sources**:
- FDIC Summary of Deposits (SOD) data
- Branch coordinates and addresses
- Geographic boundary data

**Use Cases**:
- Visualizing banking access gaps
- Branch location planning
- Community banking access assessment
- Geographic market analysis

**Target Users**: Community advocates, bank analysts, urban planners, researchers

---

### 4. **MergerMeter** - Two-Bank Merger Impact Analysis
**Port**: 8083  
**URL**: http://127.0.0.1:8083  
**Status**: ✅ Fully Functional

**Description**:  
Analyzes two-bank mergers for CRA compliance and fair lending impact. Generates comprehensive reports with assessment area mapping, market concentration analysis, and goal-setting recommendations.

**Key Features**:
- Two-bank merger analysis
- Assessment area generation (CBSA-level logic)
- CRA (Community Reinvestment Act) compliance assessment
- Fair lending analysis
- Market concentration analysis (HHI calculations)
- Excel report generation with detailed tables
- Real-time progress tracking
- Interactive web interface
- Enhanced Excel filenames with bank names

**Data Sources**:
- FDIC Summary of Deposits (SOD)
- HMDA lending data
- Census demographic data
- BigQuery financial data

**Recent Updates**:
- Updated to CBSA-level deposit threshold logic
- Enhanced Excel filenames with bank names for better organization

**Use Cases**:
- Merger application analysis
- CRA compliance assessment for mergers
- Market concentration impact evaluation
- Regulatory comment preparation
- Community impact assessment

**Target Users**: Community advocates, bank merger analysts, CRA officers, regulatory commenters, researchers

---

### 5. **BizSight** - Small Business Lending Analysis
**Port**: 8081  
**URL**: http://127.0.0.1:8081  
**Status**: ✅ Fully Functional

**Description**:  
Analyzes small business lending data from HMDA Section 1071 to assess lending patterns, economic indicators, and small business access to credit. Supports fair lending analysis for small business loans.

**Key Features**:
- Tract-level and lender-level analysis
- Small business lending pattern analysis
- AI-powered insights and narrative summaries
- Interactive web reports
- Excel export functionality
- Benchmark comparisons
- Income group analysis
- Demographic breakdowns

**Data Sources**:
- HMDA Section 1071 small business lending data
- Census tract demographics
- National benchmarks for comparison

**Use Cases**:
- Small business lending disparity analysis
- CRA small business lending assessment
- Economic development analysis
- Fair lending compliance for small business loans
- Community economic impact assessment

**Target Users**: Small business advocates, CRA officers, economic development professionals, researchers, community organizations

---

### 6. **DataExplorer** - Interactive Financial Data Dashboard
**Port**: 8085  
**URL**: http://127.0.0.1:8085  
**Status**: ✅ Fully Functional

**Description**:  
Interactive dashboard providing full control over filtering and analyzing HMDA (mortgage lending), Small Business lending, and Branch (FDIC SOD) data. Features two distinct analysis modes: Area Analyses and Lender Targeting.

**Key Features**:

**Area Analyses Mode**:
- Data type selection (HMDA, Small Business, or Branch data)
- Geography selection (counties, metro areas, or states)
- Year selection with quick-select options (All, Last 3, Last 5)
- HMDA-specific filters (loan purpose, action taken, occupancy type, total units)
- Area-level aggregation without lender focus
- Summary tables, demographics, income/neighborhood indicators
- Top lenders table
- HHI calculations
- Trends analysis

**Lender Targeting Mode**:
- Subject lender selection
- Peer comparison (automatically identifies peer lenders based on similar volume: 50%-200% of subject lender)
- Market area selection for peer identification
- Side-by-side comparison of subject lender vs. peer averages
- All data types supported (HMDA, Small Business, Branch)

**Data Sources**:
- HMDA Data: 2018-2024
- Small Business Data: 2019-2023
- Branch Data: 2017-2025

**Use Cases**:
- Flexible data exploration across all three data types
- Peer lender comparison analysis
- Custom geographic and temporal analysis
- Lender performance benchmarking
- Market analysis without pre-defined reports

**Target Users**: Data analysts, researchers, bank analysts, compliance officers, advanced users needing flexible analysis

---

### 7. **MemberView** - Member Management Application
**Port**: 8082 (when running standalone)  
**URL**: http://127.0.0.1:8082 (standalone mode)  
**Status**: 🏗️ In Development

**Description**:  
Self-contained application for managing and analyzing NCRC member data from HubSpot. Provides comprehensive member tracking, analytics, and engagement management.

**Key Features**:
- Member dashboard with status, financials, and engagement metrics
- Member details view with contacts and payment history
- Financial tracking (dues, donations)
- Contact management
- Engagement analytics
- Retention analysis
- Search and filter capabilities
- Excel/CSV export
- Interactive member map (planned)

**Data Sources**:
- HubSpot contacts, deals, and companies data
- Processed parquet/CSV files

**Note**: Can run standalone or integrated with main platform. Currently in development phase.

**Use Cases**:
- Member relationship management
- Membership analytics
- Financial tracking
- Engagement monitoring
- Retention analysis

**Target Users**: NCRC staff, membership coordinators, development team

---

## Application Summary Table

| Application | Port | Status | Primary Purpose | Data Types |
|------------|------|--------|----------------|------------|
| **BranchSeeker** | 8080 | ✅ Ready | Bank branch location analysis | FDIC SOD |
| **LendSight** | 8082 | ✅ Ready | Mortgage lending analysis | HMDA |
| **BranchMapper** | 8084 | ✅ Ready | Interactive branch map | FDIC SOD |
| **MergerMeter** | 8083 | ✅ Ready | Two-bank merger analysis | FDIC SOD, HMDA |
| **BizSight** | 8081 | ✅ Ready | Small business lending analysis | HMDA Section 1071 |
| **DataExplorer** | 8085 | ✅ Ready | Interactive data dashboard | HMDA, Small Business, Branch |
| **MemberView** | 8082* | 🏗️ Dev | Member management | HubSpot |

*MemberView uses port 8082 when running standalone, but can be configured differently

---

## Technical Infrastructure

### Environment Requirements
- **Python**: 3.11+
- **Web Framework**: Flask
- **Database**: Google BigQuery
- **AI Provider**: Anthropic Claude 4 Sonnet (primary), OpenAI GPT-4 (fallback)
- **Frontend**: HTML5/CSS3/JavaScript, jQuery, Select2, Leaflet.js (for maps)

### Required Environment Variables
```env
# AI Services
AI_PROVIDER=claude
CLAUDE_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx (optional)

# Data Sources
GCP_PROJECT_ID=hdma1-242116
GOOGLE_APPLICATION_CREDENTIALS=/path/to/gcp-credentials.json

# Application Settings
SECRET_KEY=your-random-secret-key
DEBUG=True (for development)
```

### Deployment Status
- **Current**: Applications run locally on individual ports
- **Recommended**: Cloud deployment (Railway, Google Cloud Platform, or similar)
- **Production Ready**: 6 of 7 applications fully functional

---

## User Access Tiers (For Slack Planning)

### Tier 1: Staff Testing (Phase 1)
- **Users**: NCRC staff members
- **Access**: Full access to all applications
- **Purpose**: Internal testing, feedback collection, bug identification
- **Channels Needed**: 
  - `#justdata-staff-testing` - General testing discussions
  - `#justdata-bug-reports` - Issue tracking
  - `#justdata-feedback` - Feature requests and improvements

### Tier 2: Non-Staff Testers (Phase 2)
- **Users**: Partner organizations, external researchers, community advocates
- **Access**: Limited to specific applications based on partnership agreements
- **Purpose**: Beta testing, real-world usage scenarios, external validation
- **Channels Needed**:
  - `#justdata-beta-testers` - Shared channel via Slack Connect
  - `#justdata-support` - User support and questions
  - `#justdata-feature-requests` - External feature suggestions

### Tier 3: Public Launch (Phase 3)
- **Users**: General public, researchers, community organizations
- **Access**: Public applications with optional registration for premium features
- **Purpose**: Public access to financial data analysis tools
- **Channels Needed**:
  - `#justdata-announcements` - Public announcements
  - `#justdata-community` - General discussion
  - `#justdata-support-public` - Public support channel
  - `#justdata-feature-requests-public` - Public feature requests

---

## Testing Requirements

### Phase 1: Staff Testing
**Focus Areas**:
- Application functionality and usability
- Data accuracy validation
- Report generation quality
- Export functionality
- Performance with large datasets
- Error handling and edge cases

**Key Testing Scenarios**:
1. **BranchSeeker**: Multi-year county analysis, LMI/MMCT filtering
2. **LendSight**: Multi-county analysis, demographic breakdowns, lender-specific analysis
3. **MergerMeter**: Two-bank merger scenarios, assessment area generation
4. **BizSight**: Tract-level analysis, income group comparisons
5. **DataExplorer**: Area analyses and lender targeting across all data types
6. **BranchMapper**: Geographic filtering, map interactions

### Phase 2: Non-Staff Beta Testing
**Focus Areas**:
- Real-world use cases
- User experience from external perspective
- Documentation clarity
- Training needs
- Integration with existing workflows

### Phase 3: Public Launch
**Focus Areas**:
- Scalability
- Public documentation
- Support infrastructure
- Community engagement

---

## Integration Opportunities with Slack

### Automated Notifications
- **New Feature Announcements**: Post to announcement channels when new features are deployed
- **System Updates**: Notify users of maintenance windows or system changes
- **Report Completion**: Optional notifications when long-running analyses complete
- **Error Alerts**: Internal alerts for system errors or data issues

### Slash Commands
Potential slash commands for user interaction:
- `/justdata-status` - Check application status
- `/justdata-help` - Get help documentation
- `/justdata-report <app>` - Generate quick report
- `/justdata-export <job_id>` - Download completed report

### Workflow Integration
- Link to application URLs directly from Slack
- Share analysis results in channels
- Request analyses via Slack messages
- Track analysis requests and completions

---

## Additional Information for Slack Setup

### Key Contacts
- **Lead Developer**: Jad Edlebi (jedlebi@ncrc.org)
- **Project Lead**: Jason Richardson (jrichardson@ncrc.org)

### Documentation Resources
- **Main README**: `README.md` - Platform overview and quick start
- **Applications List**: `APPLICATIONS_LIST.md` - Complete application details
- **Application URLs**: `APPLICATION_URLS.md` - Access URLs and ports
- **Deployment Guide**: `DEPLOYMENT_GUIDE.md` - Deployment instructions
- **BigQuery Guide**: `BIGQUERY_QUERY_GUIDE.md` - Data query documentation

### Support Materials Needed
- User guides for each application
- Video tutorials (recommended)
- FAQ document
- Known issues and workarounds
- Data source documentation
- API documentation (if applicable)

### Channel Naming Conventions (Recommended)
- `#justdata-*` prefix for all channels
- Examples:
  - `#justdata-staff-testing`
  - `#justdata-beta-testers`
  - `#justdata-support`
  - `#justdata-announcements`
  - `#justdata-community`
  - `#justdata-bug-reports`
  - `#justdata-feature-requests`

### Pinned Messages (Recommended for Each Channel)
- Quick start guide
- Application URLs and access information
- Testing protocols
- Bug reporting template
- Feature request template
- Support contact information
- Documentation links

---

## Next Steps for Slack Deployment

1. **Create Workspace Channels** (Phase 1 - Staff Testing)
   - Set up initial channels for staff testing
   - Pin key documentation
   - Establish testing protocols

2. **Set Up Slack Connect** (Phase 2 - Non-Staff Testers)
   - Identify partner organizations
   - Create shared channels via Slack Connect
   - Set up single-channel guest access for individual testers

3. **Prepare Slack Community** (Phase 3 - Public Launch)
   - Plan community structure
   - Prepare moderation guidelines
   - Create public documentation
   - Set up community channels

4. **Integrate Slack API** (Ongoing)
   - Set up webhook integrations for notifications
   - Develop slash commands (if desired)
   - Create workflow automations

---

**Document Version**: 1.0  
**Last Updated**: Current session  
**Prepared For**: Slack Deployment Planning  
**Total Applications**: 7 (6 fully functional, 1 in development)




