# DataExplorer - Interactive Financial Data Dashboard

## Overview

DataExplorer is an interactive dashboard that provides full control over filtering and analyzing HMDA (mortgage lending), Small Business lending, and Branch (FDIC SOD) data. The application features two distinct modes:

1. **Area Analyses** - Analyze data by geography, years, and data type without focusing on specific lenders
2. **Lender Targeting** - Select a specific lender and compare their performance to peer lenders in the same market

## Features

### Area Analyses Tab
- **Data Type Selection**: Choose between HMDA, Small Business, or Branch data
- **Geography Selection**: Filter by counties, metro areas, or states
- **Year Selection**: Select specific years or use quick-select options (All, Last 3, Last 5)
- **HMDA-Specific Filters**: Loan purpose, action taken, occupancy type, total units
- **Area-Level Aggregation**: View aggregated statistics by geography without lender focus

### Lender Targeting Tab
- **Subject Lender Selection**: Choose a specific lender to analyze
- **Peer Comparison**: Automatically identifies peer lenders based on similar volume (50%-200% of subject lender)
- **Market Area Selection**: Define the geographic market for peer identification
- **Side-by-Side Comparison**: Compare subject lender metrics to peer averages
- **All Data Types Supported**: Works with HMDA, Small Business, and Branch data

## Technical Architecture

### Backend Components

- **`config.py`**: Application configuration including BigQuery settings, data source paths, and default filters
- **`query_builders.py`**: Flexible query builders for all three data types with comprehensive filtering options
- **`data_utils.py`**: Utilities for fetching available options (counties, lenders, etc.) and executing queries
- **`app.py`**: Flask application with RESTful API endpoints

### Frontend Components

- **`dashboard.html`**: Main dashboard template with tabbed interface
- **`dashboard.css`**: Styling for the dashboard interface
- **`dashboard.js`**: JavaScript for interactivity, API calls, and data visualization

## API Endpoints

### Geography Endpoints
- `GET /api/states` - Get available states
- `GET /api/counties?state_code=<code>` - Get available counties (optionally filtered by state)
- `GET /api/metros` - Get available metro areas

### Lender Endpoints
- `GET /api/lenders/hmda?geoids=<list>&years=<list>` - Get available HMDA lenders
- `GET /api/lenders/sb?geoids=<list>&years=<list>` - Get available Small Business lenders
- `GET /api/lenders/branches?geoids=<list>&years=<list>` - Get available banks with branches

### Data Endpoints
- `POST /api/data/hmda` - Get HMDA data with filters
- `POST /api/data/sb` - Get Small Business data with filters
- `POST /api/data/branches` - Get Branch data with filters

## Running the Application

### Prerequisites
- Python 3.8+
- Google Cloud credentials configured for BigQuery access
- Required Python packages (from main `requirements.txt`)

### Start the Server

```bash
python run_dataexplorer.py
```

The application will start on **http://127.0.0.1:8085**

### Configuration

Set environment variables in `.env` file:

```env
GCP_PROJECT_ID=hdma1-242116
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
SECRET_KEY=your-secret-key
PORT=8085
DEBUG=True
```

## Data Sources

### HMDA Data
- **Dataset**: `hmda.hmda`
- **Years Available**: 2018-2024
- **Key Identifiers**: LEI (Legal Entity Identifier)
- **Filters**: Loan purpose, action taken, occupancy type, total units

### Small Business Data
- **Dataset**: `sb.disclosure` and `sb.aggregate`
- **Years Available**: 2019-2023
- **Key Identifiers**: Respondent ID (Small Business)
- **Filters**: Income groups, business revenue thresholds

### Branch Data
- **Dataset**: `branches.sod25` (latest SOD table)
- **Years Available**: 2017-2025
- **Key Identifiers**: RSSD ID
- **Filters**: Branch characteristics, LMI/MMCT flags

## Peer Comparison Logic

Peer lenders are automatically identified using a volume-based approach:

1. Calculate subject lender's total volume (loans/branches) by year and CBSA
2. Find all other lenders in the same year and CBSA
3. Identify peers with volume between 50% and 200% of subject lender's volume
4. Aggregate peer data for comparison

This ensures meaningful peer comparisons based on similar market presence and scale.

## Usage Examples

### Area Analysis Example
1. Select "Area Analyses" tab
2. Choose "HMDA" data type
3. Select counties (e.g., "Cook County, IL", "Los Angeles County, CA")
4. Select years (e.g., 2020-2024)
5. Optionally filter by loan purpose (e.g., Home Purchase only)
6. Click "Analyze Area"
7. View aggregated statistics by geography

### Lender Targeting Example
1. Select "Lender Targeting" tab
2. Choose "HMDA" data type
3. Select market area (e.g., "Cook County, IL")
4. Select years (e.g., 2020-2024)
5. Select subject lender from dropdown
6. Enable peer comparison
7. Click "Analyze Lender"
8. View subject lender vs peer comparison metrics

## Future Enhancements

- [ ] Advanced data visualization (charts, graphs)
- [ ] Export functionality (Excel, CSV, PDF)
- [ ] Saved filter presets
- [ ] Multi-lender comparison
- [ ] Trend analysis over time
- [ ] Demographic breakdowns
- [ ] Map visualizations

## Notes

- The application uses the same BigQuery project and datasets as other JustData applications
- Peer comparison requires sufficient data volume to identify meaningful peers
- Large geographic areas or long year ranges may result in slower query times
- All queries are executed server-side for security and performance

