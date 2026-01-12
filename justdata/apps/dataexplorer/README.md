# DataExplorer 2.0

Interactive Financial Data Dashboard for analyzing HMDA mortgage lending, Small Business lending, and Bank Branch data.

## Overview

DataExplorer 2.0 is a comprehensive dashboard that provides full control over filtering and analyzing financial data. It supports two main modes:

1. **Area Analysis**: Analyze lending patterns by geography, year, and data type
2. **Lender Targeting**: Analyze specific lenders with peer comparison

## Features

### Data Types Supported
- **HMDA Mortgage Lending** (2018-2024)
- **Small Business Section 1071** (2019-2023)
- **Bank Branches FDIC SOD** (2017-2025)

### Key Improvements from v1

#### Critical Fixes ✅
- **Fixed Query Logic**: Action taken filter now correctly uses `= '1'` for originations only
- **Fixed Reverse Mortgage Filter**: Now excludes both '1' and '1111' codes
- **SQL Injection Protection**: All string values properly escaped using `escape_sql_string()`
- **Input Validation**: Maximum limits enforced (10 years, 100 GEOIDs per query)
- **Deterministic Queries**: All queries include ORDER BY clauses for consistent results
- **Fixed Branch Data**: Proper year filtering (not forced to 2025)

#### High Priority Fixes ✅
- **Peer Comparison**: Enabled by default, proper data structure
- **Error Handling**: User-friendly error messages (no stack traces)
- **Cross-platform Paths**: Uses `pathlib.Path` for compatibility

## Installation

### Requirements
- Python 3.8+
- BigQuery credentials configured
- See `requirements.txt` for dependencies

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables (see config.py)
export PROJECT_ID="hdma1-242116"
export DEBUG_MODE="false"
```

### Run Locally
```bash
python run.py
# Or
flask run --port 8085
```

## API Endpoints

### Area Analysis
- `POST /api/area/hmda/analysis` - HMDA area analysis
- `POST /api/area/sb/analysis` - Small Business area analysis
- `POST /api/area/branches/analysis` - Branch area analysis

### Lender Analysis
- `POST /api/lender/analysis` - Lender analysis with peer comparison
- `POST /api/lender/lookup` - Search for lenders by name

### Configuration
- `GET /api/config/data-types` - Get available data types and years

## Usage Examples

### Area Analysis Request
```json
{
  "geoids": ["24031", "24033"],
  "years": [2020, 2021, 2022, 2023, 2024],
  "filters": {
    "action_taken": ["1"],
    "loan_purpose": ["1"],
    "exclude_reverse_mortgages": true
  }
}
```

### Lender Analysis Request
```json
{
  "lender_id": "5493001KJTIIGC8Y5R12",
  "data_types": ["hmda", "sb", "branches"],
  "years": [2020, 2021, 2022, 2023, 2024],
  "enable_peer_comparison": true
}
```

## Configuration

Key settings in `config.py`:

- `MAX_YEARS = 10` - Maximum years per query
- `MAX_GEOIDS = 100` - Maximum counties/tracts per query
- `MAX_LENDERS = 50` - Maximum lenders for peer comparison
- `DEFAULT_ACTION_TAKEN = ['1']` - Only originations
- `PEER_VOLUME_MIN_PERCENT = 0.5` - 50% of subject volume
- `PEER_VOLUME_MAX_PERCENT = 2.0` - 200% of subject volume

## File Structure

```
apps/dataexplorer/
├── __init__.py
├── app.py                    # Main Flask application
├── config.py                 # Configuration settings
├── query_builders.py          # SQL query builders (FIXED)
├── data_utils.py              # Data utilities with validation
├── area_analysis_processor.py # Area analysis logic
├── lender_analysis_processor.py # Lender analysis logic
├── requirements.txt           # Python dependencies
├── run.py                     # Run script
├── version.py                 # Version information
├── templates/
│   └── dashboard.html         # Main dashboard template
└── static/
    ├── css/
    │   └── dashboard.css      # Dashboard styles
    └── js/
        └── dashboard.js       # Dashboard JavaScript
```

## Security Features

1. **SQL Injection Protection**: All user inputs escaped using `escape_sql_string()`
2. **Input Validation**: Limits on years, GEOIDs, and lenders
3. **Error Handling**: User-friendly messages without exposing internals
4. **Deterministic Queries**: Consistent results with ORDER BY clauses

## Testing Checklist

- [x] Area analysis with multiple counties
- [x] Area analysis with multiple years
- [x] Lender lookup and selection
- [x] Lender analysis with peer comparison
- [x] Input validation (max limits)
- [x] Error handling
- [ ] Export functionality (Excel, PDF, PowerPoint) - TODO

## Deployment

### Render.com (Testing Phase)
1. Set environment variables in Render dashboard
2. Ensure `gunicorn` is in requirements.txt
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `gunicorn apps.dataexplorer.app:application --bind 0.0.0.0:$PORT`

### Docker (Production)
After testing on Render, deploy using Docker:

**Build:**
```bash
# From repository root
docker build -f apps/dataexplorer/Dockerfile -t dataexplorer:2.0.0 .

# Or use the build script
cd apps/dataexplorer
./build-docker.sh 2.0.0
```

**Run:**
```bash
docker run -d \
  --name dataexplorer \
  -p 8085:8085 \
  -e GOOGLE_CLOUD_PROJECT=your-project-id \
  -e SECRET_KEY=your-secret-key \
  dataexplorer:2.0.0
```

**Docker Compose:**
```bash
cp docker-compose.example.yml docker-compose.yml
# Edit docker-compose.yml with your environment variables
docker-compose up -d
```

See `DOCKER_DEPLOYMENT.md` for complete Docker deployment guide.

## Version History

### 2.0.0 (Current)
- Complete rewrite with all v1 fixes
- Improved query logic
- Enhanced security
- Better error handling
- Input validation

### 1.0.0 (Removed)
- Initial version (had critical issues)

## License

Part of the JustData platform by National Community Reinvestment Coalition.
