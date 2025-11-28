"""Test enrichment on 20 CURRENT members and create comparison document."""
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

# Add paths to sys.path
BASE_DIR = Path(__file__).parent.parent.parent.parent  # Go up to #JustData_Repo
JUSTDATA_BASE = BASE_DIR
sys.path.insert(0, str(JUSTDATA_BASE))

# Also add the memberview app directory
MEMBERVIEW_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(MEMBERVIEW_DIR))

from dotenv import load_dotenv
import os

# Load environment variables
env_path = JUSTDATA_BASE / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Import after path setup
try:
    from utils.website_enricher import WebsiteEnricher
    from data_utils import MemberDataLoader
    from utils.propublica_client import ProPublicaClient
except ImportError:
    from apps.memberview.utils.website_enricher import WebsiteEnricher
    from apps.memberview.data_utils import MemberDataLoader
    from apps.memberview.utils.propublica_client import ProPublicaClient

def get_downloads_folder():
    """Get the user's Downloads folder."""
    return Path.home() / "Downloads"

def create_comparison_document(members_data, enriched_data, output_file):
    """Create HTML document showing existing data (black) vs new data (red)."""
    
    # Use triple quotes and format with .replace() instead of .format() to avoid CSS brace issues
    html_template = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Member Enrichment Test Results - 20 CURRENT Members</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #333;
            border-bottom: 3px solid #0066cc;
            padding-bottom: 10px;
        }
        h2 {
            color: #0066cc;
            margin-top: 30px;
            border-bottom: 2px solid #ddd;
            padding-bottom: 5px;
        }
        .member-card {
            background: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .member-name {
            font-size: 1.3em;
            font-weight: bold;
            color: #0066cc;
            margin-bottom: 15px;
        }
        .data-section {
            margin: 15px 0;
        }
        .data-label {
            font-weight: bold;
            color: #666;
            display: inline-block;
            width: 150px;
        }
        .existing-data {
            color: #000;
        }
        .new-data {
            color: #cc0000;
            font-weight: bold;
        }
        .no-data {
            color: #999;
            font-style: italic;
        }
        .section-header {
            background-color: #e8f4f8;
            padding: 8px;
            font-weight: bold;
            margin-top: 15px;
            border-left: 4px solid #0066cc;
        }
        .summary {
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 5px;
            padding: 15px;
            margin: 20px 0;
        }
        .summary h3 {
            margin-top: 0;
            color: #856404;
        }
        .timestamp {
            color: #666;
            font-size: 0.9em;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <h1>Member Enrichment Test Results</h1>
    <div class="timestamp">Generated: {timestamp}</div>
    
    <div class="summary">
        <h3>Summary</h3>
        <p><strong>Total Members Tested:</strong> {total_members}</p>
        <p><strong>Members with Websites Found:</strong> {websites_found}</p>
        <p><strong>Members with Contact Info:</strong> {contacts_found}</p>
        <p><strong>Members with Staff Info:</strong> {staff_found}</p>
        <p><strong>Members with Form 990 Data:</strong> {form_990_found}</p>
    </div>
    
    {member_cards}
</body>
</html>
"""
    
    member_cards_html = []
    
    for idx, (member_id, member_info) in enumerate(members_data.items(), 1):
        enriched = enriched_data.get(member_id, {})
        
        # Get existing data
        existing_name = member_info.get('name', 'N/A')
        existing_city = member_info.get('city', 'N/A')
        existing_state = member_info.get('state', 'N/A')
        existing_phone = member_info.get('phone', 'N/A')
        existing_county = member_info.get('county', 'N/A')
        
        # Get enriched data
        new_website = enriched.get('website', None)
        new_website_confidence = enriched.get('website_confidence', 0)
        new_contacts = enriched.get('contacts', {})
        new_staff = enriched.get('staff', [])
        new_form_990 = enriched.get('form_990', {})
        
        # Build member card
        card_html = f"""
    <div class="member-card">
        <div class="member-name">{idx}. {existing_name}</div>
        
        <div class="section-header">Basic Information (Existing Data)</div>
        <div class="data-section">
            <span class="data-label">Name:</span>
            <span class="existing-data">{existing_name}</span>
        </div>
        <div class="data-section">
            <span class="data-label">Location:</span>
            <span class="existing-data">{existing_city}, {existing_state}</span>
        </div>
        <div class="data-section">
            <span class="data-label">County:</span>
            <span class="existing-data">{existing_county if existing_county != 'N/A' else 'Not available'}</span>
        </div>
        <div class="data-section">
            <span class="data-label">Phone:</span>
            <span class="existing-data">{existing_phone if existing_phone != 'N/A' else 'Not available'}</span>
        </div>
        
        <div class="section-header">Enriched Data (New - Shown in Red)</div>
"""
        
        # Website
        if new_website:
            card_html += f"""
        <div class="data-section">
            <span class="data-label">Website:</span>
            <span class="new-data">{new_website}</span>
            <span style="color: #666; font-size: 0.9em;"> (confidence: {new_website_confidence:.2f})</span>
        </div>
"""
        else:
            card_html += """
        <div class="data-section">
            <span class="data-label">Website:</span>
            <span class="no-data">Not found</span>
        </div>
"""
        
        # Contact Information
        if new_contacts:
            emails = new_contacts.get('emails', [])
            phones = new_contacts.get('phones', [])
            addresses = new_contacts.get('addresses', [])
            
            if emails:
                card_html += f"""
        <div class="data-section">
            <span class="data-label">Emails:</span>
            <span class="new-data">{', '.join(emails[:5])}</span>
        </div>
"""
            if phones:
                card_html += f"""
        <div class="data-section">
            <span class="data-label">Phone Numbers:</span>
            <span class="new-data">{', '.join(phones[:3])}</span>
        </div>
"""
            if addresses:
                card_html += f"""
        <div class="data-section">
            <span class="data-label">Addresses:</span>
            <span class="new-data">{addresses[0]}</span>
        </div>
"""
            if not emails and not phones and not addresses:
                card_html += """
        <div class="data-section">
            <span class="data-label">Contact Info:</span>
            <span class="no-data">No contact information extracted</span>
        </div>
"""
        else:
            card_html += """
        <div class="data-section">
            <span class="data-label">Contact Info:</span>
            <span class="no-data">Not available (website not found or not scraped)</span>
        </div>
"""
        
        # Staff Information
        if new_staff:
            card_html += """
        <div class="data-section">
            <span class="data-label">Staff/Leadership:</span>
            <div style="margin-left: 150px;">
"""
            for person in new_staff[:5]:  # Limit to 5
                name = person.get('name', 'N/A')
                title = person.get('title', 'N/A')
                card_html += f"""
                <div class="new-data" style="margin: 5px 0;">• {name} - {title}</div>
"""
            card_html += """
            </div>
        </div>
"""
        else:
            card_html += """
        <div class="data-section">
            <span class="data-label">Staff/Leadership:</span>
            <span class="no-data">No staff information extracted</span>
        </div>
"""
        
        # Form 990 Data
        if new_form_990 and new_form_990.get('found'):
            financials = new_form_990.get('financials', {})
            card_html += """
        <div class="section-header">Form 990 Data (New - Shown in Red)</div>
"""
            if financials.get('ein'):
                card_html += f"""
        <div class="data-section">
            <span class="data-label">EIN:</span>
            <span class="new-data">{financials.get('ein')}</span>
        </div>
"""
            if financials.get('tax_year'):
                card_html += f"""
        <div class="data-section">
            <span class="data-label">Tax Year (Most Current):</span>
            <span class="new-data">{financials.get('tax_year')}</span>
        </div>
"""
            if financials.get('total_revenue') is not None:
                revenue = financials.get('total_revenue')
                if revenue:
                    card_html += f"""
        <div class="data-section">
            <span class="data-label">Total Revenue ({financials.get('tax_year', 'N/A')}):</span>
            <span class="new-data">${revenue:,.2f}</span>
        </div>
"""
            if financials.get('total_expenses') is not None:
                expenses = financials.get('total_expenses')
                if expenses:
                    card_html += f"""
        <div class="data-section">
            <span class="data-label">Total Expenses ({financials.get('tax_year', 'N/A')}):</span>
            <span class="new-data">${expenses:,.2f}</span>
        </div>
"""
            # Show officers/executives with compensation
            officers = financials.get('officers', [])
            key_employees = financials.get('key_employees', [])
            
            if officers:
                card_html += """
        <div class="data-section">
            <span class="data-label">Chief Officers/Executives:</span>
            <div style="margin-left: 150px;">
"""
                for officer in officers[:10]:  # Show up to 10
                    name = officer.get('name', 'N/A')
                    title = officer.get('title', 'N/A')
                    comp = officer.get('compensation')
                    if comp is not None and comp > 0:
                        comp_str = f"${comp:,.2f}"
                    else:
                        comp_str = "Not reported"
                    card_html += f"""
                <div class="new-data" style="margin: 5px 0;">• <strong>{name}</strong> - {title} (Compensation: {comp_str})</div>
"""
                card_html += """
            </div>
        </div>
"""
            
            # Show key employees if available
            if key_employees:
                card_html += """
        <div class="data-section">
            <span class="data-label">Key Employees (Highly Compensated):</span>
            <div style="margin-left: 150px;">
"""
                for employee in key_employees[:5]:  # Show up to 5
                    name = employee.get('name', 'N/A')
                    title = employee.get('title', 'N/A')
                    comp = employee.get('compensation')
                    if comp is not None and comp > 0:
                        comp_str = f"${comp:,.2f}"
                    else:
                        comp_str = "Not reported"
                    card_html += f"""
                <div class="new-data" style="margin: 5px 0;">• <strong>{name}</strong> - {title} (Compensation: {comp_str})</div>
"""
                card_html += """
            </div>
        </div>
"""
        else:
            card_html += """
        <div class="section-header">Form 990 Data (New - Shown in Red)</div>
        <div class="data-section">
            <span class="data-label">Form 990:</span>
            <span class="no-data">No Form 990 data found (may be for-profit or not in database)</span>
        </div>
"""
        
        card_html += """
    </div>
"""
        member_cards_html.append(card_html)
    
    # Calculate summary stats
    websites_found = sum(1 for e in enriched_data.values() if e.get('website'))
    contacts_found = sum(1 for e in enriched_data.values() if e.get('contacts', {}).get('emails') or e.get('contacts', {}).get('phones'))
    staff_found = sum(1 for e in enriched_data.values() if e.get('staff'))
    form_990_found = sum(1 for e in enriched_data.values() if e.get('form_990', {}).get('found'))
    
    # Fill in template (using replace to avoid CSS brace conflicts)
    final_html = html_template.replace('{timestamp}', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    final_html = final_html.replace('{total_members}', str(len(members_data)))
    final_html = final_html.replace('{websites_found}', str(websites_found))
    final_html = final_html.replace('{contacts_found}', str(contacts_found))
    final_html = final_html.replace('{staff_found}', str(staff_found))
    final_html = final_html.replace('{form_990_found}', str(form_990_found))
    final_html = final_html.replace('{member_cards}', '\n'.join(member_cards_html))
    
    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(final_html)
    
    print(f"\nComparison document saved to: {output_file}")

def test_20_members():
    """Test enrichment on 20 CURRENT members."""
    print("=" * 80)
    print("TESTING ENRICHMENT ON 20 CURRENT MEMBERS")
    print("=" * 80)
    
    # Load member data
    print("\nLoading member data...")
    loader = MemberDataLoader()
    members_df = loader.get_members(status_filter=['CURRENT'])
    
    if len(members_df) == 0:
        print("No CURRENT members found!")
        return
    
    print(f"Found {len(members_df)} CURRENT members")
    
    # Select 20 members
    sample_size = min(20, len(members_df))
    sample_members = members_df.head(sample_size).copy()
    
    print(f"\nSelected {sample_size} members for testing")
    
    # Find columns
    record_id_col = None
    name_col = None
    city_col = None
    state_col = None
    phone_col = None
    county_col = None
    
    for col in sample_members.columns:
        col_lower = col.lower()
        if 'record id' in col_lower:
            record_id_col = col
        elif 'company' in col_lower and 'name' in col_lower:
            name_col = col
        elif col_lower == 'city':
            city_col = col
        elif col_lower == 'state/region' or (col_lower == 'state' and 'country' not in col_lower):
            state_col = col
        elif 'phone' in col_lower:
            phone_col = col
        elif col_lower == 'county':
            county_col = col
    
    if not record_id_col or not name_col:
        print("Error: Required columns not found")
        return
    
    # Initialize enricher and Form 990 client
    print("\nInitializing website enricher and Form 990 client...")
    enricher = WebsiteEnricher()
    propublica_client = ProPublicaClient()
    
    # Store data for comparison
    members_data = {}
    enriched_data = {}
    
    # Process each member
    print("\n" + "=" * 80)
    print("PROCESSING MEMBERS")
    print("=" * 80)
    
    for idx, row in sample_members.iterrows():
        member_id = str(row[record_id_col])
        company_name = str(row[name_col]) if name_col and pd.notna(row[name_col]) else ''
        city = str(row[city_col]) if city_col and pd.notna(row[city_col]) else None
        state = str(row[state_col]) if state_col and pd.notna(row[state_col]) else None
        phone = str(row[phone_col]) if phone_col and pd.notna(row[phone_col]) else None
        county = str(row[county_col]) if county_col and pd.notna(row[county_col]) else None
        
        if not company_name:
            continue
        
        print(f"\n[{idx+1}/{sample_size}] Processing: {company_name}")
        print(f"  Location: {city}, {state}")
        
        # Store existing data
        members_data[member_id] = {
            'name': company_name,
            'city': city or 'N/A',
            'state': state or 'N/A',
            'phone': phone or 'N/A',
            'county': county or 'N/A'
        }
        
        # Enrich
        try:
            enriched = enricher.enrich_member(company_name, city, state)
            
            # Add Form 990 data
            form_990_website = None
            try:
                form_990_data = propublica_client.enrich_member_with_form_990(
                    company_name=company_name,
                    state=state,
                    city=city
                )
                if form_990_data and form_990_data.get('found'):
                    enriched['form_990'] = form_990_data
                    # Check if Form 990 has website info
                    org = form_990_data.get('organization', {})
                    if isinstance(org, dict):
                        form_990_website = org.get('website') or org.get('url')
                    print(f"  [OK] Found Form 990 data (EIN: {form_990_data.get('financials', {}).get('ein', 'N/A')})")
                else:
                    enriched['form_990'] = {'found': False}
            except Exception as e:
                print(f"  [WARN] Form 990 lookup failed: {str(e)}")
                enriched['form_990'] = {'found': False}
            
            # Only use website if confidence >= 0.80 OR if found in Form 990 data
            website_confidence = enriched.get('website_confidence', 0)
            if enriched.get('website'):
                if website_confidence < 0.80:
                    # Reject low-confidence website
                    if form_990_website:
                        # Use Form 990 website as fallback
                        enriched['website'] = form_990_website
                        enriched['website_confidence'] = 0.85  # Give Form 990 websites good confidence
                        print(f"  [OK] Found website from Form 990 (search result rejected, confidence {website_confidence:.2f}): {form_990_website}")
                    else:
                        # No Form 990 fallback, reject
                        print(f"  [REJECT] Website confidence {website_confidence:.2f} below 0.80 threshold: {enriched['website']}")
                        enriched['website'] = None
                        enriched['website_confidence'] = 0
                else:
                    # Confidence >= 0.80, accept it
                    print(f"  [OK] Found website: {enriched['website']} (confidence: {website_confidence:.2f})")
            elif form_990_website:
                # No website from search, but found in Form 990
                enriched['website'] = form_990_website
                enriched['website_confidence'] = 0.85
                print(f"  [OK] Found website from Form 990: {form_990_website}")
            else:
                print(f"  [SKIP] No website found (confidence too low or not in Form 990)")
            
            enriched_data[member_id] = enriched
            
            # Rate limiting
            import time
            time.sleep(2)  # Be respectful to APIs
            
        except Exception as e:
            print(f"  [ERROR] {str(e)}")
            enriched_data[member_id] = {}
    
    # Create comparison document
    print("\n" + "=" * 80)
    print("CREATING COMPARISON DOCUMENT")
    print("=" * 80)
    
    downloads_folder = get_downloads_folder()
    output_file = downloads_folder / f"member_enrichment_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    
    create_comparison_document(members_data, enriched_data, output_file)
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print(f"\nResults saved to: {output_file}")
    print(f"\nSummary:")
    print(f"  - Members processed: {len(members_data)}")
    print(f"  - Websites found: {sum(1 for e in enriched_data.values() if e.get('website'))}")
    print(f"  - Contact info extracted: {sum(1 for e in enriched_data.values() if e.get('contacts', {}).get('emails') or e.get('contacts', {}).get('phones'))}")
    print(f"  - Staff info extracted: {sum(1 for e in enriched_data.values() if e.get('staff'))}")
    print(f"  - Form 990 data found: {sum(1 for e in enriched_data.values() if e.get('form_990', {}).get('found'))}")

if __name__ == "__main__":
    test_20_members()

