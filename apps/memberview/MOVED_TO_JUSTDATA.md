# MemberView Moved to JustData_Repo

## New Location

MemberView has been moved from:
- **Old**: `#Cursor Agent Backups/MemberView_Standalone/`
- **New**: `#JustData_Repo/apps/memberview/`

## Structure

The app now follows the same structure as other apps in JustData_Repo:
- `apps/memberview/app.py` - Main Flask application
- `apps/memberview/data_utils.py` - Data loading utilities
- `apps/memberview/map_routes.py` - Map API routes
- `apps/memberview/templates/` - HTML templates
- `apps/memberview/static/` - CSS and JavaScript files
- `apps/memberview/utils/` - Utility modules
- `apps/memberview/scripts/` - Helper scripts

## Running the App

From the JustData_Repo root:
```bash
python apps/memberview/run_memberview.py
```

Or from the memberview directory:
```bash
cd apps/memberview
python run_memberview.py
```

## Imports Updated

All imports have been updated to use the new structure:
- `from apps.memberview.app import create_app`
- `from apps.memberview.data_utils import MemberDataLoader`
- `from apps.memberview.utils.geocoder import Geocoder`

## Date

Moved: 2025-01-27

