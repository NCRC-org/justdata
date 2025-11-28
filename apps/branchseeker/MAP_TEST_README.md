# Branch Map Test Page

## Overview

This is a standalone test page for experimenting with the branch map feature before integrating it into the BranchSeeker report. You can tweak the map styling, markers, popups, and functionality without affecting the main application.

## How to Use

### Option 1: Open Directly in Browser
1. Navigate to the file: `justdata/apps/branchseeker/map_test.html`
2. Double-click the file to open it in your default browser
3. Or right-click → "Open with" → Choose your browser

### Option 2: Serve via Local Server
If you have the BranchSeeker server running:
```
http://127.0.0.1:8080/static/map_test.html
```
(You may need to move the file to the static directory for this to work)

## Features

### Test Modes
- **Sample Data**: Uses mock Hillsborough County, Florida branch data (8 sample branches)
- **Load from API**: Attempts to load real data from your API (currently falls back to sample data)

### Controls
- **County Input**: Enter the county name to test with
- **Year Input**: Select the year for the data
- **Load Map**: Loads and displays branches on the map
- **Clear**: Clears all markers from the map

## Customization

### Styling
All CSS is embedded in the `<style>` section. You can modify:
- Map container size (`#branchMap` height)
- Popup styling (`.popup-content`, `.tag`)
- Colors and fonts
- Control panel layout

### Map Features
The JavaScript section contains:
- `initMap()`: Initializes the Leaflet map
- `addMarkersToMap()`: Adds branch markers with popups
- `sampleData`: Mock branch data (edit to test different scenarios)

### Marker Customization
You can customize markers by:
- Changing marker icons
- Adding custom colors based on LMI/Minority status
- Adjusting popup content and styling
- Adding clustering for many markers

## Example Customizations

### Color-code markers by LMI/Minority status:
```javascript
// In addMarkersToMap function, replace marker creation:
const markerColor = branch.lmict && branch.mmct ? 'red' : 
                    branch.lmict ? 'orange' : 
                    branch.mmct ? 'blue' : 'green';

const marker = L.marker([lat, lng], {
    icon: L.divIcon({
        className: 'custom-marker',
        html: `<div style="background: ${markerColor}; width: 20px; height: 20px; border-radius: 50%;"></div>`
    })
})
```

### Add marker clustering:
```html
<!-- Add to <head> -->
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" />
<script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
```

Then in JavaScript:
```javascript
const markers = L.markerClusterGroup();
// Add markers to cluster group instead of directly to map
markers.addLayer(marker);
branchMap.addLayer(markers);
```

## Integration

Once you're happy with the map:

1. Copy the map initialization code from `initMap()` and `addMarkersToMap()`
2. Copy the CSS styles for the map and popups
3. Integrate into `report_template.html` in the `initializeBranchMap()` function
4. Test in the full report context

## Notes

- The sample data includes realistic Hillsborough County coordinates
- All branches have valid lat/long coordinates
- Mix of LMI and Minority status for testing
- Popup styling matches the report design system

## Troubleshooting

- **Map doesn't load**: Check browser console for errors, ensure Leaflet CDN is accessible
- **Markers don't appear**: Check that coordinates are valid (not 0,0 or null)
- **Styling issues**: Check browser developer tools for CSS conflicts

