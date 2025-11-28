# MergerMeter - Two-Bank Merger Impact Analyzer

MergerMeter analyzes the potential impact of bank mergers on Community Reinvestment Act (CRA) compliance and fair lending. The tool compares lending patterns, branch networks, and assessment area coverage for an acquiring bank and a target bank, generating goal-setting analysis reports in Excel format.

## Features

- **Two-Bank Comparison**: Analyze acquiring bank and target bank side-by-side
- **Assessment Area Analysis**: Compare assessment area coverage and overlap
- **Lending Pattern Analysis**: HMDA and Small Business lending comparisons
- **Branch Network Analysis**: Branch distribution and market concentration
- **HHI Calculations**: Herfindahl-Hirschman Index for market concentration
- **Excel Report Generation**: Professional goal-setting analysis reports
- **Interactive Web Interface**: User-friendly form-based input with real-time progress tracking

## Prerequisites

- Python 3.8 or higher
- Google Cloud Platform (GCP) credentials for BigQuery access
- Access to HMDA and Small Business lending data in BigQuery

## Installation

### 1. Install Dependencies

From the `#JustData_Repo` root directory:

```bash
pip install -r requirements.txt
```

Key dependencies include:
- Flask (web framework)
- pandas (data manipulation)
- google-cloud-bigquery (BigQuery access)
- openpyxl (Excel file generation)

### 2. Set Up Environment Variables

Create a `.env` file in the `#JustData_Repo` root directory (if it doesn't exist):

```bash
# Required
GCP_PROJECT_ID=your-gcp-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/gcp-credentials.json

# Optional - for enhanced Excel template support
MERGER_REPORT_BASE=/path/to/1_Merger_Report  # Only if you have the original merger report templates

# Optional - AI features (if using AI-powered insights)
AI_PROVIDER=claude
CLAUDE_API_KEY=your-claude-api-key
```

### 3. Verify Shared Dependencies

MergerMeter depends on shared modules in the `#JustData_Repo/shared` directory:

- `shared.web.app_factory` - Flask app creation
- `shared.utils.progress_tracker` - Progress tracking
- `shared.utils.bigquery_client` - BigQuery client wrapper
- `shared.analysis.ai_provider` - AI utilities (optional)

These should be included in the repository. If missing, ensure the `shared/` directory is present in the root.

## Running MergerMeter

### Start the Server

From the `#JustData_Repo` root directory:

```bash
python run_mergermeter.py
```

The application will start on **http://127.0.0.1:8083**

### Using the Web Interface

1. Open your browser to http://127.0.0.1:8083
2. Fill in the form with:
   - **Acquiring Bank**: LEI, RSSD ID, Small Business Respondent ID, Name
   - **Target Bank**: LEI, RSSD ID, Small Business Respondent ID, Name
   - **Assessment Areas**: Upload JSON files or paste JSON for each bank
   - **Analysis Parameters**: Loan purpose, years, filters, etc.
3. Click "Analyze" to start the analysis
4. Monitor progress in real-time
5. Download the Excel report when complete

## Assessment Area Format

MergerMeter supports multiple assessment area formats. See [ASSESSMENT_AREA_FORMAT.md](ASSESSMENT_AREA_FORMAT.md) for detailed documentation.

**Recommended format** (using FIPS codes):

```json
[
  {
    "cbsa_name": "Tampa-St. Petersburg-Clearwater, FL",
    "counties": [
      {
        "state_code": "12",
        "county_code": "057"
      },
      {
        "geoid5": "12103"
      }
    ]
  }
]
```

## Excel Template Support

MergerMeter can use Excel templates from the original merger report project for enhanced formatting. This is **optional** - the app works without them.

### With Templates (Enhanced Formatting)

If you have access to the original merger report templates:

1. Set the `MERGER_REPORT_BASE` environment variable to point to the `1_Merger_Report` directory
2. Or place the `1_Merger_Report` directory relative to the workspace root
3. The app will automatically detect and use templates if available

### Without Templates (Default)

If templates are not available (e.g., in GitHub/main branch), MergerMeter will:
- Generate Excel reports using its built-in formatting
- Create all required sheets and data
- Function fully without external dependencies

## Project Structure

```
apps/mergermeter/
├── __init__.py                    # Package initialization
├── app.py                         # Main Flask application
├── config.py                      # Configuration (paths, settings)
├── excel_generator.py             # Excel report generation
├── query_builders.py              # BigQuery query construction
├── hhi_calculator.py              # HHI concentration calculations
├── branch_assessment_area_generator.py  # Branch and AA analysis
├── county_mapper.py               # County/GEOID mapping utilities
├── templates/                     # HTML templates
│   ├── analysis_template.html     # Main analysis form
│   └── report_template.html       # Report display page
├── static/                        # Static assets (CSS, JS)
├── output/                        # Generated reports (created automatically)
└── README.md                      # This file
```

## Configuration

### Path Resolution

MergerMeter automatically resolves paths in this order:

1. **Environment Variable**: `MERGER_REPORT_BASE` (for CI/CD, Docker, etc.)
2. **Relative Path**: `../1_Merger_Report` (for GitHub/main branch)
3. **Absolute Path**: `C:\DREAM\1_Merger_Report` (for local development)

This ensures the app works across different environments without hard-coded paths.

### Output Directory

Reports are saved to `apps/mergermeter/output/` by default. The directory is created automatically if it doesn't exist.

## Troubleshooting

### "Cannot connect to BigQuery"

- Verify `GOOGLE_APPLICATION_CREDENTIALS` points to a valid credentials file
- Check that `GCP_PROJECT_ID` is set correctly
- Ensure your GCP account has BigQuery access

### "Template not found" warnings

This is **normal** if you don't have the original merger report templates. MergerMeter will use its built-in Excel generation instead.

### "Shared module not found"

- Ensure you're running from the `#JustData_Repo` root directory
- Verify the `shared/` directory exists in the root
- Check that `shared/__init__.py` exists

### Port 8083 already in use

Change the port by setting the `PORT` environment variable:

```bash
set PORT=8084
python run_mergermeter.py
```

## GitHub/Main Branch Compatibility

MergerMeter is designed to work in the main branch without external dependencies:

✅ **Works without:**
- Original merger report templates (uses built-in generation)
- External merger report utilities (gracefully falls back)
- Hard-coded Windows paths (uses environment variables and relative paths)

✅ **Requires:**
- `shared/` directory with web and utils modules
- `requirements.txt` dependencies installed
- GCP credentials for BigQuery access

## Development

### Adding New Features

1. Core logic: Modify `app.py` for new routes/endpoints
2. Excel generation: Update `excel_generator.py` for report changes
3. Queries: Modify `query_builders.py` for new data queries
4. UI: Update templates in `templates/` directory

### Testing

Run the application and test with sample bank data:

```bash
python run_mergermeter.py
```

Then access http://127.0.0.1:8083 and submit a test analysis.

## Support

For issues or questions:
1. Check this README and [ASSESSMENT_AREA_FORMAT.md](ASSESSMENT_AREA_FORMAT.md)
2. Review [CODE_REVIEW_FIXES.md](CODE_REVIEW_FIXES.md) for known issues
3. Check the main JustData README for platform-wide issues

## License

Part of the JustData platform. See main repository for license information.

