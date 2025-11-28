# Live Development Environment for Map Testing

## Quick Start

### Option 1: Use the Batch File (Easiest)
1. Double-click `start_dev_server.bat` in the project root
2. A command window will open showing the server starting
3. Wait for: "Running on http://127.0.0.1:8080"
4. Open your browser to: **http://127.0.0.1:8080**

### Option 2: Manual Start
1. Open a terminal/command prompt
2. Navigate to the project: `cd C:\DREAM\justdata`
3. Run: `python run_branchseeker.py`
4. Open browser to: **http://127.0.0.1:8080**

## Testing the Map Feature

### Step 1: Generate a Report
1. On the main page, select **County** as selection type
2. Type: **Hillsborough County, Florida** (or just "Hillsborough")
3. Enter year: **2025**
4. Click **Run Analysis**
5. Wait for the report to generate

### Step 2: View the Map
1. Once the report loads, scroll down past "Latest Statistics"
2. You should see **"Branch Locations Map"** section
3. The map will show all branch locations with markers
4. Click any marker to see branch details

## Live Development Features

✅ **Auto-Reload Enabled**: The server is running in DEBUG mode
- When you edit HTML/CSS/JS files, Flask will detect changes
- **Refresh your browser** to see the changes
- No need to restart the server for template changes

### Making Changes

1. **Edit the template**: `justdata/shared/web/templates/report_template.html`
   - Find the map section (around line 535-545)
   - Make your changes
   - Save the file
   - **Refresh your browser** (F5 or Ctrl+R)

2. **Edit JavaScript**: The map JavaScript is in the same template file
   - Find `initializeBranchMap` function (around line 1248)
   - Make your changes
   - Save the file
   - **Refresh your browser**

3. **Edit CSS**: Map styles are inline in the template
   - Find the map section styles
   - Make your changes
   - Save the file
   - **Refresh your browser**

## Browser Developer Tools

For the best development experience:

1. **Open Developer Tools**: Press `F12` or right-click → Inspect
2. **Console Tab**: See any JavaScript errors
3. **Network Tab**: Check if map tiles are loading
4. **Elements Tab**: Inspect the map HTML structure

## Quick Test Data

To quickly test the map:
- **County**: Hillsborough County, Florida
- **Year**: 2025
- This should show multiple branch locations on the map

## Troubleshooting

### Map doesn't appear
- Check browser console (F12) for errors
- Verify the report has data with coordinates
- Look for: "No branches with valid coordinates found" in console

### Changes not showing
- Make sure you **saved the file**
- **Hard refresh** the browser: Ctrl+Shift+R (or Ctrl+F5)
- Check the server console for errors

### Server not starting
- Make sure Python is in your PATH
- Check if port 8080 is already in use
- Look for error messages in the command window

## Current Status

- ✅ Server: Running in DEBUG mode
- ✅ Map Library: Leaflet loaded from CDN
- ✅ Map Section: Added to report template
- ✅ Branch Markers: JavaScript ready to display branches

## Next Steps

Once you can see the map:
1. Test with Hillsborough County, FL 2025 data
2. Try different counties/years
3. Make styling adjustments as needed
4. Add features (clustering, filters, etc.)

---

**Note**: You're on the `map-experiment` branch, so all changes are isolated from your main app!

