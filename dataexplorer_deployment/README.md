# DataExplorer Deployment Package

## Quick Start

1. **Extract this package** to your desired location

2. **Install Python dependencies**:
   ```bash
   pip install -r apps/dataexplorer/requirements.txt
   ```

3. **Set up credentials**:
   - Place `bigquery_service_account.json` in `credentials/` directory
   - Copy `.env.example` to `.env` and fill in your values
   - Add your Census API key to `.env` for ACS data features

4. **Run the application**:
   ```bash
   python run_dataexplorer.py
   ```
   Or:
   ```bash
   python -m apps.dataexplorer.app
   ```

5. **Open your browser** to `http://localhost:8085`

## Features

- **Area Analysis**: Analyze mortgage, small business, and branch data by geography
- **Lender Analysis**: Compare lenders against peers across multiple data types
- **Excel Export**: Export comprehensive reports with multiple sheets
- **Interactive Dashboards**: Dynamic charts and tables with filtering

## Required Credentials

- **BigQuery Service Account JSON**: Place in `credentials/bigquery_service_account.json`
- **Census API Key**: Set `CENSUS_API_KEY` in `.env` file (for ACS demographic data)

## Configuration

The application uses the following default settings:
- **Port**: 8085
- **Project ID**: hdma1-242116
- **BigQuery Datasets**: hmda, sb, branches, geo

See `apps/dataexplorer/config.py` for all configuration options.

## Support

For issues or questions, refer to the documentation files in `apps/dataexplorer/` or contact the development team.
