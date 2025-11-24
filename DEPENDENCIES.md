# JustData Dependencies and Report Generation Guide

This document provides a comprehensive overview of dependencies, data sources, and report generation flows for each subproject in the JustData platform.

## Table of Contents

1. [Overview](#overview)
2. [Shared Dependencies](#shared-dependencies)
3. [Subproject Dependencies](#subproject-dependencies)
4. [Report Generation Flows](#report-generation-flows)
5. [Data Sources](#data-sources)
6. [Configuration Requirements](#configuration-requirements)

## Overview

JustData is a unified platform with multiple subprojects, each with specific dependencies and report generation capabilities. All subprojects share common infrastructure for web serving, data access, and AI analysis.

## Shared Dependencies

### Core Infrastructure

- **Flask** (>=2.3.0) - Web framework for all subprojects
- **Werkzeug** (>=2.3.0) - WSGI utilities for Flask
- **python-dotenv** (>=1.0.0) - Environment variable management

### Data Processing

- **pandas** (>=1.5.0) - Data manipulation and analysis
- **numpy** (>=1.21.0) - Numerical computing

### Google Cloud / BigQuery

- **google-cloud-bigquery** (>=3.0.0) - BigQuery client library
- **google-auth** (>=2.0.0) - Google authentication
- **google-auth-oauthlib** (>=1.0.0) - OAuth2 support
- **google-auth-httplib2** (>=0.1.0) - HTTP transport for auth

### AI Services

- **anthropic** (>=0.7.0) - Claude AI integration
- **openai** (>=1.0.0) - OpenAI GPT integration

### Reporting & Export

- **openpyxl** (>=3.0.0) - Excel file generation
- **reportlab** (>=3.6.0) - PDF generation
- **Pillow** (>=10.0.0) - Image processing for PDFs
- **playwright** (>=1.40.0) - Browser automation for PDF (BizSight)

### Utilities

- **requests** (>=2.31.0) - HTTP client
- **user-agents** (>=2.2.0) - User agent parsing

### Production

- **gunicorn** (>=21.2.0) - Production WSGI server

## Subproject Dependencies

### BranchSeeker

**Purpose**: Banking market intelligence and branch network analysis

**Data Sources**:
- FDIC Summary of Deposits (SOD) data in BigQuery
- Geographic mapping tables (CBSA to county)

**BigQuery Tables**:
- `fdic.sod_*` - Summary of Deposits data by year
- `geo.cbsa_to_county` - Geographic mapping

**Report Generation**:
- **Format**: Excel (.xlsx), CSV, JSON, ZIP
- **Components**:
  - County-level branch analysis
  - Market concentration metrics
  - LMI/MMCT analysis
  - Year-over-year trends
  - AI-generated insights (Executive Summary, Key Findings, Trends)

**Dependencies**:
- All shared dependencies
- Uses `justdata.shared.reporting.report_builder` for Excel generation
- Uses `justdata.shared.analysis.ai_provider` for AI insights

**Configuration**:
- `GCP_PROJECT_ID` - Google Cloud project ID
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to service account JSON
- `CLAUDE_API_KEY` or `ANTHROPIC_API_KEY` - For AI analysis

### BizSight

**Purpose**: Small business lending analysis using HMDA Section 1071 data

**Data Sources**:
- HMDA Section 1071 small business lending data in BigQuery
- Tract-level aggregate data
- Lender-level disclosure data

**BigQuery Tables**:
- `sb.disclosure` - Lender-level disclosure data (county level)
- `sb.lenders` - Lender information
- `geo.cbsa_to_county` - Geographic mapping

**Report Generation**:
- **Format**: Excel (.xlsx), PDF, PowerPoint (via Playwright)
- **Components**:
  - Top lenders analysis
  - County summary tables
  - Comparison tables across counties
  - HHI (Herfindahl-Hirschman Index) calculations
  - AI-generated analysis
  - Tract boundary visualizations

**Dependencies**:
- All shared dependencies
- **playwright** (>=1.40.0) - For PDF/PPT generation
- Uses `justdata.apps.bizsight.utils.bigquery_client` (app-specific)
- Uses `justdata.apps.bizsight.utils.progress_tracker` (app-specific)
- Uses `justdata.apps.bizsight.report_builder` (app-specific)
- Uses `justdata.apps.bizsight.ai_analysis` (app-specific)

**Configuration**:
- `GCP_PROJECT_ID` - Google Cloud project ID (default: 'hdma1-242116')
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to service account JSON
- `CLAUDE_API_KEY` or `ANTHROPIC_API_KEY` - For AI analysis
- `AI_PROVIDER` - 'claude' or 'openai' (default: 'claude')
- `CLAUDE_MODEL` - Claude model name (default: 'claude-sonnet-4-20250514')
- `GPT_MODEL` - GPT model name (default: 'gpt-4')

### MergerMeter

**Purpose**: Two-bank merger impact analysis for CRA compliance

**Data Sources**:
- FDIC Summary of Deposits data
- Branch location data
- Assessment area data
- Market concentration data

**BigQuery Tables**:
- `fdic.sod_*` - Summary of Deposits data
- Geographic and market data tables

**Report Generation**:
- **Format**: Excel (.xlsx)
- **Components**:
  - Pre-merger and post-merger analysis
  - Assessment area mapping
  - HHI calculations
  - Branch network analysis
  - Market concentration analysis
  - Statistical analysis
  - AI-generated merger impact summary

**Dependencies**:
- All shared dependencies
- Uses `justdata.shared.utils.bigquery_client` for data access
- Uses `justdata.shared.analysis.ai_provider` for AI analysis
- Uses `justdata.shared.reporting.excel_builder` for Excel generation

**Configuration**:
- `GCP_PROJECT_ID` - Google Cloud project ID
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to service account JSON
- `MERGER_REPORT_BASE` - (Optional) Path to merger report templates directory
- `CLAUDE_API_KEY` or `ANTHROPIC_API_KEY` - For AI analysis

### LendSight

**Purpose**: Mortgage lending patterns and fair lending analysis

**Data Sources**:
- HMDA mortgage lending data in BigQuery
- Demographic data

**BigQuery Tables**:
- HMDA mortgage data tables
- Demographic and geographic mapping tables

**Report Generation**:
- **Format**: Excel (.xlsx), PDF, PowerPoint
- **Components**:
  - Lending pattern analysis
  - Disparity analysis
  - Fair lending compliance metrics
  - AI-generated insights

**Dependencies**:
- All shared dependencies
- Uses shared reporting and analysis modules

**Configuration**:
- `GCP_PROJECT_ID` - Google Cloud project ID
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to service account JSON
- `CLAUDE_API_KEY` or `ANTHROPIC_API_KEY` - For AI analysis

### BranchMapper

**Purpose**: Interactive map visualization of bank branch locations

**Data Sources**:
- FDIC Summary of Deposits data
- Branch location coordinates

**BigQuery Tables**:
- `fdic.sod_*` - Summary of Deposits data with branch locations

**Report Generation**:
- **Format**: Interactive web map (HTML/JavaScript)
- **Components**:
  - Interactive map with branch markers
  - Branch detail popups
  - Geographic filtering

**Dependencies**:
- All shared dependencies
- Uses Leaflet.js for mapping (via CDN)
- Shares data utilities with BranchSeeker

**Configuration**:
- `GCP_PROJECT_ID` - Google Cloud project ID
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to service account JSON

## Report Generation Flows

### BranchSeeker Report Flow

1. **User Input**: County selection, year range, selection type (county/state/metro)
2. **Data Query**: Query BigQuery for FDIC SOD data
3. **Data Processing**: Process raw data into structured DataFrames
4. **Analysis**: Calculate market concentration, trends, LMI/MMCT metrics
5. **AI Analysis**: Generate insights using Claude AI
6. **Report Building**: Create Excel workbook with multiple sheets
7. **Export**: Generate Excel, CSV, JSON, or ZIP file

### BizSight Report Flow

1. **User Input**: County selection, year range
2. **Data Query**: Query BigQuery for HMDA Section 1071 data
3. **Data Processing**: Aggregate and process lending data
4. **Analysis**: Calculate top lenders, HHI, county summaries
5. **Tract Boundaries**: Generate GeoJSON for map visualization
6. **AI Analysis**: Generate business lending insights
7. **Report Building**: Create Excel workbook
8. **Export**: Generate Excel, PDF (via Playwright), or PowerPoint

### MergerMeter Report Flow

1. **User Input**: Two bank identifiers, assessment areas
2. **Data Query**: Query BigQuery for pre-merger and post-merger data
3. **Analysis**: Calculate HHI, market concentration, branch networks
4. **Assessment Area Mapping**: Generate assessment area visualizations
5. **Statistical Analysis**: Perform statistical tests
6. **AI Analysis**: Generate merger impact summary
7. **Report Building**: Create Excel workbook matching merger report format
8. **Export**: Generate Excel file

## Data Sources

### BigQuery Datasets

- **fdic** - FDIC Summary of Deposits data
- **sb** - Small Business lending data (HMDA Section 1071)
- **geo** - Geographic mapping data (CBSA to county, etc.)
- **hmda** - HMDA mortgage lending data

### External APIs

- **Anthropic Claude API** - For AI-generated insights
- **OpenAI API** - Alternative AI provider

## Configuration Requirements

### Required Environment Variables

All subprojects require:
- `GCP_PROJECT_ID` - Google Cloud project ID
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to GCP service account JSON file
- `SECRET_KEY` - Flask secret key for sessions

### Optional Environment Variables

- `CLAUDE_API_KEY` or `ANTHROPIC_API_KEY` - For AI features
- `OPENAI_API_KEY` - Alternative AI provider
- `AI_PROVIDER` - 'claude' or 'openai' (default: 'claude')
- `CLAUDE_MODEL` - Claude model name
- `GPT_MODEL` - GPT model name
- `DEBUG` - Enable debug mode (True/False)
- `PORT` - Application port (defaults: 8080-8083)
- `HOST` - Application host (default: '0.0.0.0')

### MergerMeter-Specific

- `MERGER_REPORT_BASE` - Path to merger report templates directory

## Shared Modules

### justdata.shared.analysis.ai_provider

Provides AI analysis capabilities using Claude or OpenAI:
- `ask_ai()` - Send prompts to AI providers
- `convert_numpy_types()` - Convert numpy types for JSON serialization
- `AIAnalyzer` - Class for structured AI analysis

### justdata.shared.reporting.report_builder

Provides Excel report generation:
- `build_report()` - Process raw data into report DataFrames
- `save_excel_report()` - Save report to Excel file
- `sanitize_sheet_name()` - Clean sheet names for Excel

### justdata.shared.reporting.excel_builder

Provides Excel formatting utilities:
- Excel styling and formatting functions
- Sheet creation helpers

### justdata.shared.utils.bigquery_client

Provides BigQuery access:
- `get_bigquery_client()` - Get authenticated BigQuery client
- `execute_query()` - Execute BigQuery queries

### justdata.shared.utils.progress_tracker

Provides progress tracking:
- `ProgressTracker` - Class for tracking analysis progress
- `get_progress()` - Get progress for a job ID
- `update_progress()` - Update progress for a job ID
- `create_progress_tracker()` - Create new progress tracker

### justdata.shared.web.app_factory

Provides Flask app creation:
- `create_app()` - Create Flask application with standard configuration
- `register_standard_routes()` - Register standard routes (index, analyze, progress, download)

## Dashboard Pages

### Landing Page (`justdata_landing_page.html`)

Main entry point showing all available applications with user type-based access control.

**Routes**: `/` or `/landing`

### Admin Dashboard (`admin-dashboard.html`)

User management and system administration interface.

**Routes**: `/admin`

**Features**:
- User management (create, edit, delete users)
- Integration link management (Memberful, HubSpot)

### Analytics Dashboard (`analytics-dashboard.html`)

User analytics and activity monitoring.

**Routes**: `/analytics`

**Features**:
- User activity statistics
- Interactive map showing user locations
- Application usage metrics
- User filtering and search

### Status Dashboard (`status-dashboard.html`)

Status monitoring dashboard (identical to analytics dashboard).

**Routes**: `/status`

## Integration Points

### Flask Routes

Dashboard routes are registered via `justdata.shared.web.dashboard_routes`:
- Import: `from justdata.shared.web.dashboard_routes import register_dashboard_routes`
- Usage: `register_dashboard_routes(app)`

### Static Assets

All dashboard pages use shared static assets:
- CSS: `justdata/shared/web/static/css/`
- JavaScript: `justdata/shared/web/static/js/`
- Images: `justdata/shared/web/static/img/`

### Templates

Dashboard HTML files are in:
- `justdata/shared/web/templates/`

## Notes

- All subprojects can be run independently via their respective `run_*.py` scripts
- Shared modules ensure consistency across subprojects
- BigQuery credentials can be provided via environment variable or file path
- AI features are optional but enhance report quality significantly
- Report generation is asynchronous with progress tracking for long-running analyses

