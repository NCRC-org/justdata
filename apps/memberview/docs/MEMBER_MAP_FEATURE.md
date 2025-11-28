# Member Map Feature - Implementation Plan

## Overview

Interactive map visualization showing NCRC members with filtering by state/metro and member status. Each member appears as an icon on the map with a popup showing detailed information.

## Features

### 1. Map Visualization
- **Library**: Leaflet.js (same as BizSight for consistency)
- **Base Map**: OpenStreetMap tiles (free, no API key)
- **Zoom Levels**: 
  - State level: Zoom 5-6
  - Metro level: Zoom 8-10
  - City level: Zoom 11-13

### 2. Filters
- **State Dropdown**: Filter members by US state
- **Metro Dropdown**: Filter by MSA/CBSA (Metropolitan Statistical Area)
- **Member Status Dropdown**: 
  - All Members
  - Current Members
  - Grace Period
  - Lapsed Members

### 3. Member Icons
- Different icons/colors based on member status:
  - Current: Green marker
  - Grace Period: Yellow marker
  - Lapsed: Red marker
- Clickable markers that open popup

### 4. Member Popup Content
- **Company Information**:
  - Company name
  - Membership status
  - Create date
  - Last activity date
  - Address (city, state, country)
  - Phone number
  - Website (if available)
  - Industry (if available)

- **Associated Contacts**:
  - List of contacts (name, email, phone)
  - Marketing contact status
  - Last activity date
  - Limit to top 5-10 contacts

- **Last Deal**:
  - Deal name
  - Deal amount
  - Deal stage
  - Close date
  - Deal type (membership, renewal, etc.)

- **Additional Data**:
  - Total number of contacts
  - Total number of deals
  - Total deal amount (sum of all deals)
  - Years as member (if calculable)

## Data Requirements

### Required Data Points
1. **Company Location**: City, State (for geocoding)
2. **Member Status**: From companies table
3. **Contacts**: Associated contacts with basic info
4. **Deals**: Latest deal and aggregate deal data
5. **Geocoding**: Convert city/state to lat/lng coordinates

### Data Processing
- Join companies, contacts, and deals tables
- Geocode member locations (city + state)
- Calculate derived metrics (total deals, total amount, etc.)
- Cache geocoded coordinates to avoid repeated API calls

## Technical Implementation

### Backend (Flask)
- `/api/members` - Get filtered member data (JSON)
  - Query params: `state`, `metro`, `status`
  - Returns: Array of member objects with location and summary data
- `/api/member/<id>` - Get detailed member data (JSON)
  - Returns: Full member details including all contacts and deals

### Frontend (JavaScript)
- Leaflet map initialization
- Filter controls (dropdowns)
- Marker rendering based on filtered data
- Popup template rendering
- Geocoding service integration (Nominatim or similar)

### Data Structure
```json
{
  "id": "company_record_id",
  "name": "Company Name",
  "status": "CURRENT",
  "location": {
    "city": "Washington",
    "state": "DC",
    "lat": 38.9072,
    "lng": -77.0369
  },
  "contacts_count": 5,
  "deals_count": 3,
  "last_deal": {
    "name": "2024 Membership Renewal",
    "amount": 5000,
    "close_date": "2024-01-15"
  },
  "total_deal_amount": 15000
}
```

## Metro/MSA Data

### Options for Metro Filtering
1. **Use existing MSA data**: If available in HubSpot or external source
2. **City-based grouping**: Group by major cities (simpler)
3. **County-based**: Use county to determine metro area
4. **Manual mapping**: Create city-to-metro mapping table

### Recommendation
Start with state and city filtering, add metro later if MSA data is available.

## Geocoding Strategy

### Option 1: Nominatim (OpenStreetMap)
- **Free**: No API key
- **Rate Limit**: 1 request/second
- **Good for**: One-time geocoding, caching results

### Option 2: Batch Geocoding
- Pre-geocode all members during data processing
- Store lat/lng in processed data
- No runtime geocoding needed

### Recommendation
**Batch geocoding during data processing** - More reliable, faster, no rate limits.

## Implementation Phases

### Phase 1: Basic Map
- Load members with location data
- Display markers on map
- Basic popup with company name and status

### Phase 2: Filtering
- Add state dropdown filter
- Add member status filter
- Update map markers based on filters

### Phase 3: Enhanced Popup
- Add contacts list
- Add last deal information
- Add summary statistics

### Phase 4: Metro Filtering
- Add metro/MSA dropdown
- Group members by metro area
- Metro-level clustering (optional)

## Files to Create

1. `app/map_routes.py` - Flask routes for map data
2. `app/data_utils.py` - Member data aggregation with geocoding
3. `web/templates/member_map.html` - Map page template
4. `web/static/js/member_map.js` - Map JavaScript
5. `web/static/css/member_map.css` - Map styling
6. `utils/geocoder.py` - Geocoding utility

## Dependencies

- `leaflet` (via CDN)
- `flask` (backend)
- `pandas` (data processing)
- `geopy` or `requests` (geocoding)

