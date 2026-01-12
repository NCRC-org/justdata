#!/usr/bin/env python3
"""
Build static site for LoanTrends.
Fetches all data from the HMDA Quarterly API and saves as JSON files.
Then generates a static HTML page.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from apps.loantrends.config import GRAPH_ENDPOINTS
from apps.loantrends.data_utils import fetch_multiple_graphs
from apps.loantrends.chart_builder import build_chart_data
from apps.loantrends.data_utils import get_recent_12_quarters

def build_static_site():
    """Build the static site by fetching data and generating HTML."""
    
    print("=" * 80)
    print("BUILDING STATIC LOANTRENDS SITE")
    print("=" * 80)
    print()
    
    # Create output directories
    static_dir = Path(__file__).parent / 'static_site'
    data_dir = static_dir / 'data'
    static_dir.mkdir(exist_ok=True)
    data_dir.mkdir(exist_ok=True)
    
    print(f"Output directory: {static_dir}")
    print()
    
    # Get all endpoints
    all_endpoints = []
    for category, endpoints in GRAPH_ENDPOINTS.items():
        all_endpoints.extend(endpoints)
    
    print(f"Fetching data for {len(all_endpoints)} endpoints...")
    print()
    
    # Fetch all graph data
    graph_data = fetch_multiple_graphs(all_endpoints)
    
    # Build chart data (quarterly)
    print("Building chart data...")
    chart_data = build_chart_data(graph_data, time_period="all")
    
    # Get time period info
    start_quarter, end_quarter = get_recent_12_quarters()
    
    # Save chart data as JSON
    chart_data_file = data_dir / 'chart_data.json'
    with open(chart_data_file, 'w') as f:
        json.dump(chart_data, f, indent=2)
    print(f"Saved chart data to {chart_data_file}")
    
    # Save metadata
    metadata = {
        'generated_at': datetime.now().isoformat(),
        'time_period': f"{start_quarter} to {end_quarter} (last 12 quarters)",
        'start_quarter': start_quarter,
        'end_quarter': end_quarter,
        'endpoints': all_endpoints,
        'categories': GRAPH_ENDPOINTS,
        'version': '1.0.0'
    }
    
    metadata_file = data_dir / 'metadata.json'
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved metadata to {metadata_file}")
    
    # Save raw graph data (for reference)
    graph_data_file = data_dir / 'graph_data.json'
    with open(graph_data_file, 'w') as f:
        json.dump(graph_data, f, indent=2)
    print(f"Saved raw graph data to {graph_data_file}")
    
    print()
    print("=" * 80)
    print("STATIC SITE DATA BUILD COMPLETE")
    print("=" * 80)
    print(f"\nData files saved to: {data_dir}")
    print(f"\nGenerating static HTML page...")
    print()
    
    # Generate static HTML
    from apps.loantrends.generate_static_html import generate_static_html
    generate_static_html()
    
    print()
    print("=" * 80)
    print("STATIC SITE BUILD COMPLETE")
    print("=" * 80)
    print(f"\nStatic site ready at: {static_dir}")
    print(f"\nTo view locally:")
    print(f"  cd {static_dir}")
    print(f"  python -m http.server 8000")
    print(f"  Then open: http://localhost:8000")
    print(f"\nTo deploy:")
    print(f"  Upload the 'static_site' folder to GitHub Pages, Netlify, or any static hosting")
    print()

if __name__ == '__main__':
    build_static_site()
