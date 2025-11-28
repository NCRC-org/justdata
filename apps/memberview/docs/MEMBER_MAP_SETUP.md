# Member Map Setup Guide

## Quick Start

1. **Geocode Member Locations** (one-time setup):
   ```bash
   python scripts/geocode_members.py
   ```
   This will:
   - Load all members from HubSpot data
   - Geocode unique city/state combinations
   - Save coordinates to `data/member_coordinates.json`
   - Cache results to avoid re-geocoding

2. **Start the Application**:
   ```bash
   python run_memberview.py
   ```

3. **Access the Map**:
   Navigate to: `http://localhost:8082/map`

## Features

### Filters
- **State Dropdown**: Filter members by US state
- **Member Status**: Filter by Current, Grace Period, or Lapsed

### Map Display
- **Markers**: Color-coded by member status
  - 🟢 Green: Current/Active members
  - 🟡 Yellow: Grace Period members
  - 🔴 Red: Lapsed members

### Member Popups
Click any marker to see:
- Company name and status
- Location (city, state)
- Last deal information (name, amount, date)
- Summary statistics (contacts count, deals count, total amount)
- Link to full member details

## Data Requirements

The map requires:
1. **HubSpot Data Files** (in `C:\DREAM\HubSpot\data\`):
   - Companies: `raw/hubspot-crm-exports-all-companies-2025-11-14.csv`
   - Contacts: `processed/20251114_123115_all-contacts_processed.parquet`
   - Deals: `processed/20251114_123117_all-deals_processed.parquet`

2. **Geocoded Coordinates** (after running geocoding script):
   - `data/member_coordinates.json` - Pre-geocoded coordinates
   - `data/geocoding_cache.json` - Geocoding cache (prevents re-querying)

## Troubleshooting

### No Markers Appearing
- **Check**: Did you run `geocode_members.py`?
- **Check**: Are coordinates in `data/member_coordinates.json`?
- **Check**: Do members have city and state data?

### Geocoding Fails
- **Rate Limits**: Nominatim allows 1 request/second
- **Solution**: Script handles rate limiting automatically
- **Cache**: Results are cached to avoid re-geocoding

### Missing Data
- **Contacts**: Check that contacts file exists and is processed
- **Deals**: Check that deals file exists and is processed
- **Companies**: Check that companies CSV exists in raw folder

## Next Steps

1. **Add Metro Filtering**: Implement MSA/CBSA filtering
2. **Enhance Popups**: Add contact list and deal history
3. **Add Clustering**: Cluster markers when zoomed out
4. **Add Member Detail Page**: Full profile view

