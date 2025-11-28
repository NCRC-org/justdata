"""
Parse PNC Bank Assessment Area PDF and create JSON file.
"""
import pdfplumber
import json
import re
from pathlib import Path

def parse_counties_from_text(text):
    """Parse counties from text like 'IL: DeKalb, Kane' or 'Jefferson, Shelby'"""
    counties = []
    
    if not text:
        return counties
    
    # State abbreviation to full name mapping
    state_map = {
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
    
    # Split by newlines first to handle multi-line entries
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Pattern for "State: County1, County2" or "State: County"
        # Also handle cases like "District of Columbia" or special cases
        if ':' in line:
            # Has state abbreviation
            parts = line.split(':', 1)
            if len(parts) == 2:
                state_abbrev = parts[0].strip()
                counties_str = parts[1].strip()
                
                state_name = state_map.get(state_abbrev, state_abbrev)
                
                # Split counties by comma
                county_names = [c.strip() for c in counties_str.split(',')]
                
                for county_name in county_names:
                    county_name = county_name.strip()
                    if county_name:
                        # Handle special cases like "Chesapeake City", "Norfolk City", etc.
                        if ' City' in county_name:
                            full_county = f"{county_name}, {state_name}"
                        elif county_name.endswith((' County', ' Parish', ' Borough')):
                            full_county = f"{county_name}, {state_name}"
                        else:
                            full_county = f"{county_name} County, {state_name}"
                        counties.append(full_county)
        else:
            # No state abbreviation - might be a continuation or standalone
            # Try to parse as county names (comma-separated)
            county_names = [c.strip() for c in line.split(',')]
            for county_name in county_names:
                county_name = county_name.strip()
                if county_name and len(county_name) > 2:
                    # Without state context, we can't fully qualify these
                    # But we'll try to add them - they might be continuations
                    if not county_name.endswith((' County', ' Parish', ' Borough', ' City')):
                        county_name = f"{county_name} County"
                    # We'll need state context from previous entries
                    counties.append(county_name)
    
    return counties

def parse_pnc_pdf(pdf_path):
    """Parse PNC Bank assessment areas from PDF"""
    assessment_areas = []
    
    with pdfplumber.open(pdf_path) as pdf:
        print(f"Total pages: {len(pdf.pages)}")
        
        found_start = False
        
        for page_num, page in enumerate(pdf.pages, 1):
            tables = page.extract_tables()
            
            if not tables:
                continue
            
            for table in tables:
                for row_idx, row in enumerate(table):
                    if not row or len(row) < 3:
                        continue
                    
                    # Clean row cells
                    row = [str(cell).strip() if cell else '' for cell in row]
                    
                    # Check if this is the start marker
                    row_text = ' '.join(row).lower()
                    if "list of assessment areas" in row_text:
                        found_start = True
                        continue
                    
                    if not found_start:
                        continue
                    
                    # Skip header rows
                    if any(h in row_text for h in ['time period', 'bank products', 'affiliates', 'affiliate relationship']):
                        continue
                    
                    # Column 0: Assessment area name
                    # Column 1: Type (Full/Limited) or empty
                    # Column 2: Counties
                    
                    col0 = row[0] if len(row) > 0 else ''
                    col1 = row[1] if len(row) > 1 else ''
                    col2 = row[2] if len(row) > 2 else ''
                    
                    # Skip empty rows
                    if not col0 and not col1 and not col2:
                        continue
                    
                    # Skip state header rows (like "Alabama", "State", etc.)
                    if col0 and col0 not in ['State', ''] and not col1 and not col2:
                        # Check if it's actually a state name
                        state_names = ['Alabama', 'Florida', 'Kentucky', 'Maryland', 'Michigan', 
                                      'New Jersey', 'North Carolina', 'Ohio', 'Tennessee', 'Texas', 'Virginia']
                        if col0 in state_names:
                            continue
                    
                    # Main pattern: Assessment area name in col0, counties in col2
                    if col0 and col2 and (col0 != 'State'):
                        # Clean up assessment area name
                        assessment_area_name = col0.replace('\n', ' ').strip()
                        
                        # Skip if it's just a state name
                        if assessment_area_name in ['Alabama', 'Florida', 'Kentucky', 'Maryland', 'Michigan', 
                                                    'New Jersey', 'North Carolina', 'Ohio', 'Tennessee', 'Texas', 'Virginia']:
                            continue
                        
                        # Parse counties from col2
                        counties = parse_counties_from_text(col2)
                        
                        if counties:
                            assessment_areas.append({
                                'cbsa_name': assessment_area_name,
                                'counties': counties
                            })
                            print(f"  Found: {assessment_area_name} ({len(counties)} counties)")
                    
                    # Also check col2 for nested assessment areas (like MD entries)
                    elif col2 and ('MD' in col2 or 'MSA' in col2):
                        # This might contain nested assessment areas
                        lines = col2.split('\n')
                        current_aa_name = None
                        current_counties = []
                        
                        for line in lines:
                            line = line.strip()
                            if not line:
                                continue
                            
                            # Check if this line is an assessment area name
                            if 'MD' in line or ('MSA' in line and ',' not in line.split('MSA')[0][-10:]):
                                # This might be an assessment area name
                                # But it's tricky - let's look for patterns
                                if current_aa_name and current_counties:
                                    assessment_areas.append({
                                        'cbsa_name': current_aa_name,
                                        'counties': current_counties
                                    })
                                    print(f"  Found (nested): {current_aa_name} ({len(current_counties)} counties)")
                                
                                # Try to extract name
                                parts = line.split('\n')
                                if parts:
                                    current_aa_name = parts[0].strip()
                                    current_counties = []
                            else:
                                # This should be counties
                                counties = parse_counties_from_text(line)
                                if counties:
                                    if current_aa_name:
                                        current_counties.extend(counties)
                                    else:
                                        # No current AA name - might be continuation
                                        if assessment_areas:
                                            assessment_areas[-1]['counties'].extend(counties)
                        
                        # Don't forget the last one
                        if current_aa_name and current_counties:
                            assessment_areas.append({
                                'cbsa_name': current_aa_name,
                                'counties': current_counties
                            })
                            print(f"  Found (nested): {current_aa_name} ({len(current_counties)} counties)")
    
    return assessment_areas

if __name__ == "__main__":
    pdf_path = r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\PNC Bank Assessment Area 2022.pdf"
    
    print("Parsing PNC Bank Assessment Area PDF...")
    assessment_areas = parse_pnc_pdf(pdf_path)
    
    # Remove duplicates
    seen = set()
    unique_areas = []
    for aa in assessment_areas:
        key = (aa['cbsa_name'], tuple(sorted(aa['counties'])))
        if key not in seen:
            seen.add(key)
            unique_areas.append(aa)
    
    # Save to JSON
    output_path = Path(pdf_path).parent / "PNC_Bank_Assessment_Areas.json"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(unique_areas, f, indent=2, ensure_ascii=False)
    
    print(f"\nExtracted {len(unique_areas)} unique assessment areas")
    print(f"Saved to: {output_path}")
