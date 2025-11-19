"""
Script to parse PNC Bank Assessment Area PDF and generate JSON file.
"""

import pdfplumber
import json
import re
from pathlib import Path

def parse_pnc_assessment_areas(pdf_path):
    """
    Parse PNC Bank Assessment Area PDF and extract assessment areas with counties.
    
    Table structure:
    - Column 0: Assessment Area Name
    - Column 1: Type (Full, Limited, MD)
    - Column 2: Counties (format: "State: County1, County2" or "County1, County2")
    """
    assessment_areas = []
    found_start = False
    
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        print(f"Error: PDF file not found at {pdf_path}")
        return []
    
    print(f"Reading PDF: {pdf_path}")
    
    # State abbreviation to full name mapping
    state_abbrev_map = {
        'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California',
        'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia',
        'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa',
        'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
        'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri',
        'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey',
        'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio',
        'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
        'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
        'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming',
        'DC': 'District of Columbia'
    }
    
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            print(f"Processing page {page_num}...")
            
            tables = page.extract_tables()
            
            if not tables:
                continue
            
            for table_idx, table in enumerate(tables):
                if not table or len(table) == 0:
                    continue
                
                # Process each row
                current_aa_name = None  # Track current assessment area name across rows
                
                for row_idx, row in enumerate(table):
                    if not row or len(row) < 3:
                        continue
                    
                    # Get columns
                    aa_name_col = str(row[0]).strip() if row[0] else ''
                    type_col = str(row[1]).strip() if row[1] else ''
                    counties_col = str(row[2]).strip() if row[2] else ''
                    
                    # Check if we've found the start
                    if 'List of Assessment Areas' in aa_name_col or 'Assessment Areas' in aa_name_col:
                        found_start = True
                        continue
                    
                    if not found_start:
                        continue
                    
                    # Skip header rows and empty rows
                    if not aa_name_col and not counties_col:
                        continue
                    
                    # Handle continuation rows (empty first column but has counties - continuation from previous page)
                    if not aa_name_col and counties_col:
                        # This is a continuation row - use the previous assessment area name
                        if current_aa_name:
                            aa_name_col = current_aa_name
                        else:
                            # Can't process without assessment area name
                            continue
                    
                    # Skip if it's clearly metadata
                    if aa_name_col and aa_name_col.lower() in ['assessment area', 'state', 'time period', 'bank products', 'affiliates']:
                        continue
                    
                    # Skip if it's a state header (just state name, no counties)
                    if aa_name_col in state_abbrev_map.values() and not counties_col:
                        continue
                    
                    # Skip if it's clearly metadata
                    skip_patterns = ['charter number', 'appendix', 'time period', 'bank products', 'affiliate']
                    if any(pattern in aa_name_col.lower() for pattern in skip_patterns):
                        continue
                    
                    # Clean up assessment area name (remove newlines, extra spaces)
                    aa_name = ' '.join(aa_name_col.split())
                    
                    if not aa_name:
                        continue
                    
                    # Update current assessment area name
                    current_aa_name = aa_name
                    
                    # Parse counties from column 2
                    counties = []
                    
                    if counties_col:
                        # Handle sub-assessment areas (like "Elgin, IL MD" within a larger area)
                        # Split by patterns that indicate sub-areas, but also handle regular county lists
                        
                        # First, check if this contains sub-assessment area markers (like "MD" at end of line)
                        # Pattern: "Area Name MD\nState: Counties" indicates a sub-area
                        sub_area_pattern = r'([^,\n]+(?:,\s*[A-Z]{2})?\s*MD)\n'
                        
                        # Split by newlines first (some entries have multiple states or sub-areas)
                        county_lines = counties_col.split('\n')
                        
                        for line in county_lines:
                            line = line.strip()
                            if not line:
                                continue
                            
                            # Skip sub-assessment area headers (like "Elgin, IL MD" or "New Brunswick-Lakewood, NJ MD")
                            if re.match(r'^[^:]+MD$', line):
                                continue
                            
                            # Pattern 1: "State: County1, County2" (e.g., "PA: Allegheny, Bucks")
                            state_county_match = re.match(r'^([A-Z]{2}|District of Columbia):\s*(.+)$', line)
                            if state_county_match:
                                state_abbrev = state_county_match.group(1)
                                county_list_str = state_county_match.group(2)
                                
                                # Get full state name
                                if state_abbrev == 'District of Columbia':
                                    state_name = 'District of Columbia'
                                else:
                                    state_name = state_abbrev_map.get(state_abbrev, state_abbrev)
                                
                                # Split counties by comma
                                county_names = [c.strip() for c in county_list_str.split(',')]
                                
                                for county_name in county_names:
                                    # Clean up county name
                                    county_name = county_name.strip()
                                    
                                    # Add "County" suffix if not present (unless it's a city)
                                    if not county_name.endswith(('County', 'Parish', 'Borough', 'City')):
                                        # Check if it's a city (like "Norfolk City" or "Alexandria City")
                                        if 'City' in county_name:
                                            full_county = f"{county_name}, {state_name}"
                                        else:
                                            full_county = f"{county_name} County, {state_name}"
                                    else:
                                        full_county = f"{county_name}, {state_name}"
                                    
                                    if full_county not in counties:
                                        counties.append(full_county)
                            
                            # Pattern 2: Just county names (for single-state MSAs, state is implied from MSA name)
                            elif ',' in line and not ':' in line:
                                # Multiple counties, no state prefix - need to infer state from MSA name
                                # Extract state from assessment area name if possible
                                state_from_aa = None
                                
                                # Look for state abbreviation in AA name (e.g., "Pittsburgh, PA MSA")
                                state_match = re.search(r',\s*([A-Z]{2})\s*(?:MSA|MD)?', aa_name)
                                if state_match:
                                    state_abbrev = state_match.group(1)
                                    state_from_aa = state_abbrev_map.get(state_abbrev, state_abbrev)
                                
                                if state_from_aa:
                                    county_names = [c.strip() for c in line.split(',')]
                                    for county_name in county_names:
                                        if not county_name.endswith(('County', 'Parish', 'Borough', 'City')):
                                            full_county = f"{county_name} County, {state_from_aa}"
                                        else:
                                            full_county = f"{county_name}, {state_from_aa}"
                                        
                                        if full_county not in counties:
                                            counties.append(full_county)
                            
                            # Pattern 3: Single county name (no state prefix, no comma)
                            elif line and not ':' in line and ',' not in line:
                                # Single county, need to infer state
                                state_from_aa = None
                                state_match = re.search(r',\s*([A-Z]{2})\s*(?:MSA|MD)?', aa_name)
                                if state_match:
                                    state_abbrev = state_match.group(1)
                                    state_from_aa = state_abbrev_map.get(state_abbrev, state_abbrev)
                                
                                if state_from_aa:
                                    if not line.endswith(('County', 'Parish', 'Borough', 'City')):
                                        full_county = f"{line} County, {state_from_aa}"
                                    else:
                                        full_county = f"{line}, {state_from_aa}"
                                    
                                    if full_county not in counties:
                                        counties.append(full_county)
                    
                    # Only add assessment area if it has counties
                    if counties:
                        assessment_areas.append({
                            'cbsa_name': aa_name,
                            'counties': counties
                        })
                        print(f"  {aa_name}: {len(counties)} counties")
    
    return assessment_areas


def main():
    pdf_path = r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\PNC Bank Assessment Area 2022.pdf"
    output_path = r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\PNC_Bank_Assessment_Areas.json"
    
    print("=" * 80)
    print("PNC Bank Assessment Area PDF Parser")
    print("=" * 80)
    print()
    
    assessment_areas = parse_pnc_assessment_areas(pdf_path)
    
    print()
    print(f"Found {len(assessment_areas)} assessment areas")
    print()
    
    # Print summary
    for i, aa in enumerate(assessment_areas[:10], 1):
        print(f"{i}. {aa['cbsa_name']}: {len(aa['counties'])} counties")
    
    if len(assessment_areas) > 10:
        print(f"... and {len(assessment_areas) - 10} more")
    
    # Save to JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(assessment_areas, f, indent=2, ensure_ascii=False)
    
    print()
    print(f"JSON file saved to: {output_path}")
    print(f"Total assessment areas: {len(assessment_areas)}")
    total_counties = sum(len(aa['counties']) for aa in assessment_areas)
    print(f"Total counties: {total_counties}")


if __name__ == '__main__':
    main()
