# LoanTrends Static Site

LoanTrends is now a **static site** that can be hosted anywhere (GitHub Pages, Netlify, etc.). The data is fetched quarterly and saved as JSON files.

## Building the Static Site

### Step 1: Fetch Data and Generate JSON Files

Run the build script to fetch all data from the HMDA Quarterly API and save it as JSON:

```bash
cd apps/loantrends
python build_static_site.py
```

This will:
- Fetch all endpoint data from the CFPB HMDA Quarterly API
- Process it into chart-ready format
- Save to `static_site/data/`:
  - `chart_data.json` - Processed chart data
  - `metadata.json` - Site metadata and time period info
  - `graph_data.json` - Raw API data (for reference)

### Step 2: Generate Static HTML

The build script automatically generates `static_site/index.html` which:
- Loads data from local JSON files (no API calls)
- Renders all charts using Chart.js
- Works completely offline

## Viewing Locally

```bash
cd apps/loantrends/static_site
python -m http.server 8000
```

Then open: http://localhost:8000

## Deploying

### Option 1: GitHub Pages

1. Create a new repository (or use existing)
2. Copy the `static_site` folder contents to the repository root
3. Enable GitHub Pages in repository settings
4. Site will be available at: `https://username.github.io/repository-name`

### Option 2: Netlify

1. Install Netlify CLI: `npm install -g netlify-cli`
2. Navigate to `static_site` folder
3. Run: `netlify deploy --prod`

### Option 3: Any Static Hosting

Upload the entire `static_site` folder to:
- AWS S3 + CloudFront
- Azure Static Web Apps
- Google Cloud Storage
- Any web server

## Updating Data

Since the data only updates quarterly, you only need to rebuild the site when new quarterly data is available:

1. Run `python build_static_site.py` to fetch latest data
2. Commit and push the updated `static_site` folder
3. Site will automatically update (or redeploy if needed)

## File Structure

```
apps/loantrends/
├── build_static_site.py      # Main build script
├── generate_static_html.py   # HTML generator
├── static_site/              # Output directory
│   ├── index.html            # Main HTML page
│   └── data/                 # JSON data files
│       ├── chart_data.json
│       ├── metadata.json
│       └── graph_data.json
└── STATIC_SITE_README.md     # This file
```

## Features

- ✅ No server required - pure static HTML/JS
- ✅ Fast loading - all data is local
- ✅ Works offline
- ✅ Can be hosted anywhere
- ✅ Quarterly updates only (data is national and updates quarterly)
- ✅ All charts render client-side with Chart.js

## Notes

- The site uses CDN resources for:
  - Chart.js (charting library)
  - jQuery (DOM manipulation)
  - Font Awesome (icons)
  - Google Fonts (typography)
- All data is embedded in the HTML or loaded from local JSON files
- No API calls are made when viewing the site
