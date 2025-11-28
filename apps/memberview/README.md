# MemberView - Self-Contained Member Management Application

## Overview

MemberView is a fully self-contained application for managing and analyzing NCRC member data from HubSpot. It provides a user-friendly interface for tracking membership, retention, contacts, engagement, donors, dues, and financial information.

## Features

- **Member Dashboard**: Overview of all members with status, financials, and engagement metrics
- **Member Details**: Detailed view of individual members with contacts, payment history, and activity
- **Financial Tracking**: Dues, donations, and payment history
- **Contact Management**: View and manage contacts associated with each member
- **Engagement Analytics**: Track member engagement and activity levels
- **Retention Analysis**: Member retention rates and churn analysis
- **Search & Filter**: Powerful search and filtering capabilities
- **Export**: Export member data to Excel/CSV

## Project Structure

```
MemberView_Standalone/
├── app/                    # Application code
│   ├── __init__.py
│   ├── app.py             # Main Flask application
│   ├── config.py          # Application configuration
│   ├── core.py            # Core member data processing
│   ├── data_utils.py      # Data loading and utilities
│   └── excel_export.py    # Excel export functionality
├── config/                 # Configuration files
│   ├── __init__.py
│   └── app_config.py      # App configuration class
├── utils/                  # Utility modules
│   ├── __init__.py
│   ├── hubspot_client.py  # HubSpot API client
│   └── data_processor.py  # Data processing utilities
├── web/                    # Web interface
│   ├── templates/         # HTML templates
│   └── static/           # CSS, JS, images
├── data/                   # Data storage
│   ├── reports/          # Generated reports
│   └── exports/         # Exported data
├── credentials/            # Credentials (not in git)
│   └── .gitkeep
├── docs/                  # Documentation
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── run_memberview.py      # Entry point script
└── README.md              # This file
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your values:
```env
# HubSpot API
HUBSPOT_ACCESS_TOKEN=your-hubspot-access-token-here

# Application Settings
SECRET_KEY=your-random-secret-key-here
PORT=8082
DEBUG=True

# Data Paths (optional - defaults to HubSpot folder)
HUBSPOT_DATA_PATH=../HubSpot/data/processed
```

### 3. Set Up HubSpot Data

MemberView reads from processed HubSpot data files:
- Contacts: `HubSpot/data/processed/*_all-contacts_processed.parquet`
- Deals: `HubSpot/data/processed/*_all-deals_processed.parquet`
- Companies: `HubSpot/data/raw/hubspot-crm-exports-all-companies-*.csv`

Ensure these files exist or update the data path in configuration.

### 4. Run the Application

```bash
python run_memberview.py
```

Then open: http://localhost:8082

## Configuration

### Application Configuration

Edit `config/app_config.py` to customize:
- Data file paths
- HubSpot API settings
- Default filters and views
- Export formats

### Port Configuration

Default port is 8082. Change via:
- Environment variable: `PORT=8083`
- Command line: `python run_memberview.py --port 8083`

## Data Sources

MemberView integrates with HubSpot data:

### Companies Table
- Source of truth for membership status
- Contains: Company name, membership status, dates
- Join key: `Record ID`

### Deals Table
- Financial transactions (dues, donations)
- Contains: Amount, dates, deal stage, company associations
- Join key: `Associated Company IDs (Primary)`

### Contacts Table
- Contact information and engagement
- Contains: Email, name, company associations
- Join key: `associated_company` or company ID

## Features in Detail

### Member Dashboard
- Total members count
- Status breakdown (CURRENT, LAPSED, GRACE, etc.)
- New members this year
- Renewals this year
- At-risk members (expiring soon)

### Member Details
- Basic information
- All associated contacts
- Complete payment history
- Status change timeline
- Engagement summary
- Notes and custom fields

### Financial Dashboard
- Total dues collected
- Dues by year/month
- Outstanding dues
- Donor information
- Revenue trends

### Contact Management
- Contacts per member
- Primary contact identification
- Contact roles (if available)
- Engagement scores

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main dashboard |
| `/members` | GET | Member list with filters |
| `/member/<id>` | GET | Member detail view |
| `/financial` | GET | Financial dashboard |
| `/contacts` | GET | Contact management |
| `/export` | GET | Export member data |
| `/api/members` | GET | Member data (JSON) |
| `/api/member/<id>` | GET | Single member data (JSON) |
| `/health` | GET | Health check |

## Development

### Running in Development Mode

```bash
export DEBUG=True
python run_memberview.py
```

### Project Dependencies

See `requirements.txt` for full list. Key dependencies:
- Flask 2.3.0+ (Web framework)
- pandas 2.0.0+ (Data manipulation)
- hubspot-api-client 7.0.0+ (HubSpot integration)
- pyarrow 12.0.0+ (Parquet file support)
- openpyxl 3.1.0+ (Excel export)

## Self-Contained Design

This application is **fully self-contained**:
- ✅ All dependencies bundled
- ✅ No external shared modules required
- ✅ All configuration in this folder
- ✅ All credentials in `credentials/` folder
- ✅ All data output in `data/` folder
- ✅ Reads from HubSpot data exports (no direct HubSpot dependency required)

## Security Notes

- Never commit `.env` file to version control
- Never commit `credentials/` folder contents
- Use environment variables for sensitive data
- Rotate API keys regularly

## Troubleshooting

### HubSpot Data Not Found
- Verify data file paths in configuration
- Ensure HubSpot data has been processed
- Check file permissions

### Port Already in Use
- Change `PORT` in `.env`
- Or kill the process using port 8082

### Missing Dependencies
- Run `pip install -r requirements.txt`
- Check Python version (3.8+ required)

## License

Internal NCRC tool - Not for public distribution

## Authors

NCRC - National Community Reinvestment Coalition

