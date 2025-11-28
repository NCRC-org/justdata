# MemberView Setup Guide

## Initial Setup

### 1. Install Dependencies

```bash
cd "#Cursor Agent Backups/MemberView_Standalone"
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and set:
- `HUBSPOT_ACCESS_TOKEN` - Your HubSpot private app access token
- `SECRET_KEY` - A random secret key for Flask sessions
- `PORT` - Port to run on (default: 8082)

### 3. Verify HubSpot Data

MemberView reads from processed HubSpot data. Ensure these files exist:

- **Contacts**: `../HubSpot/data/processed/*_all-contacts_processed.parquet`
- **Deals**: `../HubSpot/data/processed/*_all-deals_processed.parquet`
- **Companies**: `../HubSpot/data/raw/hubspot-crm-exports-all-companies-*.csv`

If your data is in a different location, update the paths in `.env`:
```
HUBSPOT_DATA_PATH=/path/to/processed/data
HUBSPOT_RAW_PATH=/path/to/raw/data
```

### 4. Run the Application

```bash
python run_memberview.py
```

Or use the launcher:
```bash
python start_memberview.py
```

Then open: http://localhost:8082

## Getting HubSpot Access Token

1. Log in to your HubSpot account
2. Go to **Settings** → **Integrations** → **Private Apps**
3. Create a new private app (or use existing)
4. Configure scopes:
   - `crm.objects.contacts.read`
   - `crm.objects.companies.read`
   - `crm.objects.deals.read`
5. Copy the **Access Token**
6. Add it to your `.env` file as `HUBSPOT_ACCESS_TOKEN`

## Troubleshooting

### Port Already in Use
Change the port in `.env` or use:
```bash
python run_memberview.py --port 8083
```

### Data Files Not Found
- Verify the data paths in `.env`
- Ensure HubSpot data has been processed
- Check file permissions

### Missing Dependencies
```bash
pip install -r requirements.txt
```

### Import Errors
Ensure you're running from the MemberView_Standalone directory:
```bash
cd "#Cursor Agent Backups/MemberView_Standalone"
python run_memberview.py
```

## Next Steps

After setup, see:
- `README.md` for feature documentation
- `docs/MemberView_PLANNING_DOCUMENT.md` for detailed planning
- `config/app_config.py` for configuration options

