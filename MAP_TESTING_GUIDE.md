# Map Feature Testing Guide

## What Was Added

✅ **Leaflet Map Library** - Interactive mapping library loaded from CDN
✅ **Map Section** - New "Branch Locations Map" section in the report
✅ **Branch Markers** - Each branch with coordinates is displayed as a marker
✅ **Interactive Popups** - Click markers to see branch details
✅ **Auto-centering** - Map automatically centers on all branches

## How to Test

### 1. Start the Server
The server should already be running. If not:
```bash
python run_branchseeker.py
```

### 2. Access the Application
Open your browser and go to:
```
http://127.0.0.1:8080
```

### 3. Generate a Report with Hillsborough County, Florida
1. Select **County** as the selection type
2. Enter: **Hillsborough County, Florida** (or just "Hillsborough" if it autocompletes)
3. Enter year: **2025**
4. Click **Run Analysis**

### 4. View the Map
Once the report loads:
- Scroll down past the "Latest Statistics" section
- You should see a new **"Branch Locations Map"** section
- The map will show all branches with valid coordinates
- Click on any marker to see branch details (name, address, bank, LMI/Minority status)

## What the Map Shows

- **Markers**: One marker per branch location
- **Popup Info**: 
  - Branch name
  - Bank name
  - Full address (street, city, state, zip)
  - LMI/Minority status indicators
- **Auto-zoom**: Map automatically fits to show all branches
- **Latest Year Only**: Shows branches from the most recent year in your selection

## Technical Details

- **Map Library**: Leaflet 1.9.4 (free, open-source)
- **Tile Provider**: OpenStreetMap (free, no API key needed)
- **Data Source**: Coordinates from BigQuery (latitude/longitude columns)
- **Filtering**: Only branches with valid, non-zero coordinates are shown

## Troubleshooting

### Map doesn't appear
- Check browser console for errors (F12)
- Verify branches have coordinates in the database
- Check that `raw_data` includes `latitude` and `longitude` fields

### Map is empty
- The selected county/year might not have coordinate data
- Check the browser console for: "No branches with valid coordinates found"

### Map loads but no markers
- Verify the SQL query is returning latitude/longitude
- Check that coordinates are not null or zero

## Current Branch Status

You're on the `map-experiment` branch, so:
- ✅ Your main app (`JasonEdits` branch) is safe
- ✅ All changes are isolated to this branch
- ✅ You can switch back anytime with `git checkout JasonEdits`

## Next Steps (Optional Enhancements)

- Color-code markers by bank
- Add filters (LMI only, Minority only, etc.)
- Cluster markers when zoomed out
- Add legend
- Show branch counts by area


