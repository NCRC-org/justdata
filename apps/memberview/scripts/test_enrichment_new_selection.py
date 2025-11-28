"""Test enrichment on a NEW selection of 20 CURRENT members and create comparison document."""
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime
import random
import time

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
    <title>Member Enrichment Test Results - New Selection of 10 CURRENT Members</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .header {
            background-color: #2c3e50;
            color: white;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .member-card {
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .member-name {
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 10px;
        }
        .section-header {
            font-size: 18px;
            font-weight: bold;
            color: #34495e;
            margin-top: 20px;
            margin-bottom: 10px;
            border-bottom: 2px solid #3498db;
            padding-bottom: 5px;
        }
        .data-section {
            margin: 10px 0;
            padding: 8px;
            background-color: #f9f9f9;
            border-left: 3px solid #3498db;
        }
        .data-label {
            font-weight: bold;
            display: inline-block;
            width: 200px;
            color: #2c3e50;
        }
        .existing-data {
            color: #000000;
        }
        .new-data {
            color: #e74c3c;
            font-weight: bold;
        }
        .no-data {
            color: #95a5a6;
            font-style: italic;
        }
        .staff-member {
            margin: 5px 0;
            padding: 5px;
            background-color: #ecf0f1;
            border-left: 2px solid #3498db;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Member Enrichment Test Results</h1>
        <p>New Selection of 10 CURRENT Members - {timestamp}</p>
        <p>Existing data shown in <span style="color: #000000; font-weight: bold;">black</span>, 
           New data shown in <span style="color: #e74c3c; font-weight: bold;">red</span></p>
    </div>
    
    {member_cards}
</body>
</html>"""
    
    member_cards_html = []
    
    for member in members_data:
        member_id = member.get('id', 'N/A')
        member_name = member.get('name', 'N/A')
        enriched = enriched_data.get(member_id, {})
        
        # Get existing data
        existing_website = member.get('website', '')
        existing_city = member.get('city', '')
        existing_state = member.get('state', '')
        existing_address = member.get('address', '')
        
        # Get new data
        new_website = enriched.get('website', {})
        new_staff = enriched.get('staff', [])
        new_contacts = enriched.get('contacts', {})
        new_form_990 = enriched.get('form_990', {})
        
        # Build member card HTML
        card_html = f"""
    <div class="member-card">
        <div class="member-name">{member_name}</div>
        
        <div class="section-header">Basic Information</div>
        <div class="data-section">
            <span class="data-label">City:</span>
            <span class="existing-data">{existing_city if existing_city else 'N/A'}</span>
        </div>
        <div class="data-section">
            <span class="data-label">State:</span>
            <span class="existing-data">{existing_state if existing_state else 'N/A'}</span>
        </div>
        <div class="data-section">
            <span class="data-label">Address:</span>
            <span class="existing-data">{existing_address if existing_address else 'N/A'}</span>
        </div>
        
        <div class="section-header">Website</div>"""
        
        # Website comparison
        if new_website.get('url'):
            website_url = new_website.get('url')
            website_confidence = new_website.get('confidence', 0)
            if website_confidence >= 0.80:
                card_html += f"""
        <div class="data-section">
            <span class="data-label">Website (New):</span>
            <span class="new-data"><a href="{website_url}" target="_blank">{website_url}</a> (confidence: {website_confidence:.2f})</span>
        </div>"""
            else:
                card_html += f"""
        <div class="data-section">
            <span class="data-label">Website:</span>
            <span class="no-data">Found but confidence too low ({website_confidence:.2f} < 0.80)</span>
        </div>"""
        elif existing_website:
            card_html += f"""
        <div class="data-section">
            <span class="data-label">Website (Existing):</span>
            <span class="existing-data">{existing_website}</span>
        </div>"""
        else:
            card_html += """
        <div class="data-section">
            <span class="data-label">Website:</span>
            <span class="no-data">Not found</span>
        </div>"""
        
        # Staff Information
        card_html += """
        <div class="section-header">Staff/Leadership (New - Shown in Red)</div>"""
        
        if new_staff:
            card_html += """
        <div class="data-section">"""
            for staff in new_staff[:10]:  # Show up to 10
                name = staff.get('name', 'N/A')
                title = staff.get('title', 'N/A')
                email = staff.get('email', '')
                phone = staff.get('phone', '')
                staff_type = staff.get('type', 'staff')
                
                card_html += f"""
            <div class="staff-member">
                <strong class="new-data">{name}</strong> - {title} ({staff_type})
                {f'<br>Email: <span class="new-data">{email}</span>' if email else ''}
                {f'<br>Phone: <span class="new-data">{phone}</span>' if phone else ''}
            </div>"""
            card_html += """
        </div>"""
        else:
            card_html += """
        <div class="data-section">
            <span class="no-data">No staff information found</span>
        </div>"""
        
        # Contact Information
        if new_contacts.get('emails') or new_contacts.get('phones'):
            card_html += """
        <div class="section-header">Contact Information (New - Shown in Red)</div>"""
            if new_contacts.get('emails'):
                card_html += f"""
        <div class="data-section">
            <span class="data-label">Emails:</span>
            <span class="new-data">{', '.join(new_contacts['emails'][:5])}</span>
        </div>"""
            if new_contacts.get('phones'):
                card_html += f"""
        <div class="data-section">
            <span class="data-label">Phones:</span>
            <span class="new-data">{', '.join(new_contacts['phones'][:5])}</span>
        </div>"""
        
        # Organization Information (Funders, Partners, Major Areas of Work, etc.)
        new_org_info = enriched.get('organization_info', {})
        if new_org_info:
            has_org_data = False
            
            if new_org_info.get('funders_partners'):
                has_org_data = True
                card_html += """
        <div class="section-header">Funders/Partners/Supporters (New - Shown in Red)</div>
        <div class="data-section">
            <div style="margin-left: 150px;">
"""
                for fp in new_org_info['funders_partners'][:15]:  # Show up to 15
                    name = fp.get('name', 'N/A')
                    fp_type = fp.get('type', 'partner')
                    desc = fp.get('description', '')
                    card_html += f"""
                <div class="new-data" style="margin: 5px 0;">• <strong>{name}</strong> ({fp_type}){f' - {desc}' if desc else ''}</div>
"""
                card_html += """
            </div>
        </div>"""
            
            if new_org_info.get('major_areas_of_work'):
                has_org_data = True
                card_html += """
        <div class="section-header">Major Areas of Work (New - Shown in Red)</div>
        <div class="data-section">
            <div style="margin-left: 150px;">
"""
                for area in new_org_info['major_areas_of_work'][:15]:  # Show up to 15
                    card_html += f"""
                <div class="new-data" style="margin: 5px 0;">• {area}</div>
"""
                card_html += """
            </div>
        </div>"""
            
            if new_org_info.get('affiliations'):
                has_org_data = True
                card_html += """
        <div class="section-header">Affiliations/Memberships (New - Shown in Red)</div>
        <div class="data-section">
            <div style="margin-left: 150px;">
"""
                for aff in new_org_info['affiliations'][:15]:  # Show up to 15
                    name = aff.get('name', 'N/A') if isinstance(aff, dict) else aff
                    aff_type = aff.get('type', '') if isinstance(aff, dict) else ''
                    card_html += f"""
                <div class="new-data" style="margin: 5px 0;">• <strong>{name}</strong>{f' ({aff_type})' if aff_type else ''}</div>
"""
                card_html += """
            </div>
        </div>"""
            
            if new_org_info.get('mission'):
                has_org_data = True
                card_html += f"""
        <div class="section-header">Mission Statement (New - Shown in Red)</div>
        <div class="data-section">
            <span class="new-data">{new_org_info['mission']}</span>
        </div>"""
            
            if new_org_info.get('programs_services'):
                has_org_data = True
                card_html += """
        <div class="section-header">Programs/Services (New - Shown in Red)</div>
        <div class="data-section">
            <div style="margin-left: 150px;">
"""
                for prog in new_org_info['programs_services'][:15]:  # Show up to 15
                    card_html += f"""
                <div class="new-data" style="margin: 5px 0;">• {prog}</div>
"""
                card_html += """
            </div>
        </div>"""
        
        # Form 990 Data
        if new_form_990 and new_form_990.get('found'):
            financials = new_form_990.get('financials')
            org_data = new_form_990.get('organization', {})
            
            # Handle case where financials might be None
            if financials is None:
                financials = {}
            
            card_html += """
        <div class="section-header">Form 990 Data (New - Shown in Red)</div>"""
            
            # Always show EIN if available (from organization or financials)
            ein = None
            if financials:
                ein = financials.get('ein')
            if not ein and org_data:
                # Try to get EIN from organization data
                org_obj = org_data.get('organization', {}) if isinstance(org_data, dict) else org_data
                if isinstance(org_obj, dict):
                    ein = org_obj.get('ein')
                else:
                    ein = org_data.get('ein') if isinstance(org_data, dict) else None
            
            if ein:
                card_html += f"""
        <div class="data-section">
            <span class="data-label">EIN:</span>
            <span class="new-data">{ein}</span>
        </div>"""
            
            # Show organization name if available
            org_name = None
            if financials:
                org_name = financials.get('name')
            if not org_name and org_data:
                org_obj = org_data.get('organization', {}) if isinstance(org_data, dict) else org_data
                if isinstance(org_obj, dict):
                    org_name = org_obj.get('name')
                else:
                    org_name = org_data.get('name') if isinstance(org_data, dict) else None
            if org_name:
                card_html += f"""
        <div class="data-section">
            <span class="data-label">Organization Name (ProPublica):</span>
            <span class="new-data">{org_name}</span>
        </div>"""
            
            # Show comprehensive financial data if available
            if financials:
                # Tax year
                tax_year = financials.get('tax_year')
                if not tax_year:
                    tax_year = financials.get('tax_period')
                if tax_year:
                    card_html += f"""
        <div class="data-section">
            <span class="data-label">Tax Year (Most Current):</span>
            <span class="new-data">{tax_year}</span>
        </div>"""
                
                # Mission/Activities
                if financials.get('mission'):
                    card_html += f"""
        <div class="data-section">
            <span class="data-label">Mission (from Form 990):</span>
            <span class="new-data">{financials.get('mission')}</span>
        </div>"""
                
                if financials.get('activities'):
                    card_html += f"""
        <div class="data-section">
            <span class="data-label">Activities (from Form 990):</span>
            <span class="new-data">{financials.get('activities')}</span>
        </div>"""
                
                # Revenue Section
                card_html += """
        <div class="section-header">Revenue Breakdown (New - Shown in Red)</div>"""
                
                revenue = financials.get('total_revenue')
                if revenue is not None and revenue != 0:
                    card_html += f"""
        <div class="data-section">
            <span class="data-label">Total Revenue ({tax_year or 'N/A'}):</span>
            <span class="new-data">${revenue:,.2f}</span>
        </div>"""
                
                contributions = financials.get('contributions')
                if contributions is not None and contributions != 0:
                    card_html += f"""
        <div class="data-section">
            <span class="data-label">Contributions/Gifts/Grants:</span>
            <span class="new-data">${contributions:,.2f}</span>
        </div>"""
                
                program_revenue = financials.get('program_service_revenue')
                if program_revenue is not None and program_revenue != 0:
                    card_html += f"""
        <div class="data-section">
            <span class="data-label">Program Service Revenue:</span>
            <span class="new-data">${program_revenue:,.2f}</span>
        </div>"""
                
                investment_income = financials.get('investment_income')
                if investment_income is not None and investment_income != 0:
                    card_html += f"""
        <div class="data-section">
            <span class="data-label">Investment Income:</span>
            <span class="new-data">${investment_income:,.2f}</span>
        </div>"""
                
                other_revenue = financials.get('other_revenue')
                if other_revenue is not None and other_revenue != 0:
                    card_html += f"""
        <div class="data-section">
            <span class="data-label">Other Revenue:</span>
            <span class="new-data">${other_revenue:,.2f}</span>
        </div>"""
                
                # Expenses Section
                card_html += """
        <div class="section-header">Expense Breakdown (New - Shown in Red)</div>"""
                
                expenses = financials.get('total_expenses')
                if expenses is not None and expenses != 0:
                    card_html += f"""
        <div class="data-section">
            <span class="data-label">Total Expenses ({tax_year or 'N/A'}):</span>
            <span class="new-data">${expenses:,.2f}</span>
        </div>"""
                
                program_expenses = financials.get('program_expenses')
                if program_expenses is not None and program_expenses != 0:
                    card_html += f"""
        <div class="data-section">
            <span class="data-label">Program Expenses:</span>
            <span class="new-data">${program_expenses:,.2f}</span>
        </div>"""
                
                admin_expenses = financials.get('administrative_expenses')
                if admin_expenses is not None and admin_expenses != 0:
                    card_html += f"""
        <div class="data-section">
            <span class="data-label">Administrative Expenses:</span>
            <span class="new-data">${admin_expenses:,.2f}</span>
        </div>"""
                
                fundraising_expenses = financials.get('fundraising_expenses')
                if fundraising_expenses is not None and fundraising_expenses != 0:
                    card_html += f"""
        <div class="data-section">
            <span class="data-label">Fundraising Expenses:</span>
            <span class="new-data">${fundraising_expenses:,.2f}</span>
        </div>"""
                
                grants_paid = financials.get('grants_paid')
                if grants_paid is not None and grants_paid != 0:
                    card_html += f"""
        <div class="data-section">
            <span class="data-label">Grants Paid:</span>
            <span class="new-data">${grants_paid:,.2f}</span>
        </div>"""
                
                # Balance Sheet Section
                card_html += """
        <div class="section-header">Balance Sheet (New - Shown in Red)</div>"""
                
                assets = financials.get('total_assets')
                if assets is not None and assets != 0:
                    card_html += f"""
        <div class="data-section">
            <span class="data-label">Total Assets:</span>
            <span class="new-data">${assets:,.2f}</span>
        </div>"""
                
                liabilities = financials.get('total_liabilities')
                if liabilities is not None and liabilities != 0:
                    card_html += f"""
        <div class="data-section">
            <span class="data-label">Total Liabilities:</span>
            <span class="new-data">${liabilities:,.2f}</span>
        </div>"""
                
                net_assets = financials.get('net_assets')
                if net_assets is not None and net_assets != 0:
                    card_html += f"""
        <div class="data-section">
            <span class="data-label">Net Assets:</span>
            <span class="new-data">${net_assets:,.2f}</span>
        </div>"""
                
                cash = financials.get('cash_savings')
                if cash is not None and cash != 0:
                    card_html += f"""
        <div class="data-section">
            <span class="data-label">Cash & Savings:</span>
            <span class="new-data">${cash:,.2f}</span>
        </div>"""
                
                # Organization Classification
                if financials.get('ntee_code') or financials.get('ntee_classification'):
                    card_html += """
        <div class="section-header">Organization Classification (New - Shown in Red)</div>"""
                    if financials.get('ntee_code'):
                        card_html += f"""
        <div class="data-section">
            <span class="data-label">NTEE Code:</span>
            <span class="new-data">{financials.get('ntee_code')}</span>
        </div>"""
                    if financials.get('ntee_classification'):
                        card_html += f"""
        <div class="data-section">
            <span class="data-label">NTEE Classification:</span>
            <span class="new-data">{financials.get('ntee_classification')}</span>
        </div>"""
                    if financials.get('subsection'):
                        card_html += f"""
        <div class="data-section">
            <span class="data-label">Subsection:</span>
            <span class="new-data">{financials.get('subsection')}</span>
        </div>"""
                    if financials.get('ruling_date'):
                        card_html += f"""
        <div class="data-section">
            <span class="data-label">Ruling Date:</span>
            <span class="new-data">{financials.get('ruling_date')}</span>
        </div>"""
                
                # Show board members (if available)
                board_members = financials.get('board_members', []) or []
                if board_members:
                    card_html += """
        <div class="section-header">Board Members (New - Shown in Red)</div>
        <div class="data-section">
            <span class="data-label">Board Members:</span>
            <div style="margin-left: 150px;">
"""
                    for member in board_members[:15]:  # Show up to 15
                        name = member.get('name', 'N/A')
                        title = member.get('title', 'Board Member')
                        comp = member.get('compensation')
                        if comp is not None and comp > 0:
                            comp_str = f" (Compensation: ${comp:,.2f})"
                        else:
                            comp_str = " (Volunteer)"
                        card_html += f"""
                <div class="new-data" style="margin: 5px 0;">• <strong>{name}</strong> - {title}{comp_str}</div>
"""
                    card_html += """
            </div>
        </div>"""
                
                # Show officers/executives with compensation
                officers = financials.get('officers', []) or []
                key_employees = financials.get('key_employees', []) or []
            
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
        </div>"""
            
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
        </div>"""
                # Form 990 URL (if available in organization data)
                form_990_url = None
                if org_data:
                    org_obj = org_data.get('organization', {}) if isinstance(org_data, dict) else org_data
                    if isinstance(org_obj, dict):
                        form_990_url = org_obj.get('url')
                    else:
                        form_990_url = org_data.get('url') if isinstance(org_data, dict) else None
                
                if form_990_url:
                    card_html += f"""
        <div class="data-section">
            <span class="data-label">Form 990 URL:</span>
            <span class="new-data"><a href="{form_990_url}" target="_blank">View on ProPublica</a></span>
        </div>"""
            else:
                # Financials not available but organization found
                card_html += """
        <div class="data-section">
            <span class="data-label">Status:</span>
            <span class="new-data">Organization found in ProPublica but financial data not available</span>
        </div>"""
        else:
            card_html += """
        <div class="data-section">
            <span class="data-label">Form 990:</span>
            <span class="no-data">No Form 990 data found (may be for-profit or not in database)</span>
        </div>"""
        
        card_html += """
    </div>"""
        member_cards_html.append(card_html)
    
    # Combine and save
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html_content = html_template.replace("{timestamp}", timestamp).replace("{member_cards}", "\n".join(member_cards_html))
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\nComparison document saved to: {output_file}")

def main():
    """Main execution function."""
    print("=" * 80)
    print("Testing Enrichment on NEW Selection of 10 CURRENT Members")
    print("=" * 80)
    
    # Load member data
    print("\n1. Loading member data...")
    loader = MemberDataLoader()
    current_members = loader.get_members(status_filter=['CURRENT'])
    
    print(f"   Found {len(current_members)} CURRENT members")
    
    # Find column names
    record_id_col = None
    name_col = None
    status_col = None
    city_col = None
    state_col = None
    address_col = None
    website_col = None
    
    for col in current_members.columns:
        col_lower = col.lower()
        if 'record id' in col_lower:
            record_id_col = col
        elif 'company' in col_lower and 'name' in col_lower:
            name_col = col
        elif 'membership' in col_lower and 'status' in col_lower:
            status_col = col
        elif col_lower == 'city':
            city_col = col
        elif col_lower == 'state/region' or (col_lower == 'state' and 'country' not in col_lower):
            state_col = col
        elif 'address' in col_lower and 'street' in col_lower:
            address_col = col
        elif 'website' in col_lower:
            website_col = col
    
    if not record_id_col or not name_col:
        print("ERROR: Could not find required columns")
        return
    
    # Select a NEW set of 10 members (skip first 60, get next 10, or random)
    print("\n2. Selecting NEW set of 10 members...")
    total_members = len(current_members)
    
    # Strategy: Skip first 60, get next 10 (or random if less than 70 total)
    # This ensures we get a different batch than previous runs
    if total_members > 70:
        start_idx = 60
        end_idx = min(70, total_members)
        selected_members = current_members.iloc[start_idx:end_idx]
        print(f"   Selected members 61-{end_idx} (skipping first 60)")
    elif total_members > 60:
        # If we have 61-70 members, use random selection with different seed
        selected_members = current_members.sample(n=min(10, total_members), random_state=456)
        print(f"   Randomly selected {len(selected_members)} members (seed 456)")
    else:
        # Random selection if we don't have enough
        selected_members = current_members.sample(n=min(10, total_members), random_state=456)
        print(f"   Randomly selected {len(selected_members)} members (seed 456)")
    
    print(f"   Selected {len(selected_members)} members for testing")
    
    # Prepare member data
    members_data = []
    for _, row in selected_members.iterrows():
        member = {
            'id': str(row[record_id_col]),
            'name': str(row[name_col]) if pd.notna(row[name_col]) else 'N/A',
            'city': str(row[city_col]) if city_col and pd.notna(row[city_col]) else '',
            'state': str(row[state_col]) if state_col and pd.notna(row[state_col]) else '',
            'address': str(row[address_col]) if address_col and pd.notna(row[address_col]) else '',
            'website': str(row[website_col]) if website_col and pd.notna(row[website_col]) else '',
        }
        members_data.append(member)
    
    # Initialize enrichers
    print("\n3. Initializing enrichers...")
    website_enricher = WebsiteEnricher()
    propublica_client = ProPublicaClient()
    
    # Enrich each member
    print("\n4. Enriching member data...")
    enriched_data = {}
    
    for i, member in enumerate(members_data, 1):
        member_id = member['id']
        member_name = member['name']
        print(f"\n[{i}/{len(members_data)}] Processing: {member_name}")
        
        # Add delay between members to avoid rate limits
        if i > 1:
            delay = 2.0  # 2 seconds between members
            print(f"  [WAIT] Waiting {delay} seconds to avoid rate limits...")
            time.sleep(delay)
        
        enriched = {}
        
        # Find website
        company_name = member_name
        city = member.get('city', '')
        state = member.get('state', '')
        existing_website = member.get('website', '')
        
        website_result = None
        if existing_website:
            # Use existing website if available
            website_result = (existing_website, 1.0)
            print(f"  [OK] Using existing website: {existing_website}")
        else:
            # Try to find website
            print(f"  [SEARCH] Searching for website...")
            website_result = website_enricher.find_website(company_name, city, state)
        
        if website_result:
            url, confidence = website_result
            enriched['website'] = {'url': url, 'confidence': confidence}
            
            # Extract comprehensive information using Claude
            # Trust search engine results - use lower threshold (0.70) since Google/DuckDuckGo are reliable
            if confidence >= 0.70 or existing_website:
                print(f"  [EXTRACT] Extracting comprehensive info from {url}...")
                
                # Extract staff info
                try:
                    staff = website_enricher.extract_staff_info(url)
                    if staff:
                        enriched['staff'] = staff
                        print(f"  [OK] Found {len(staff)} staff/board members")
                    else:
                        print(f"  [INFO] No staff information found")
                except Exception as e:
                    print(f"  [ERROR] Error extracting staff: {e}")
                
                # Extract contact info
                try:
                    contacts = website_enricher.extract_contact_info(url)
                    if contacts and (contacts.get('emails') or contacts.get('phones')):
                        enriched['contacts'] = contacts
                        print(f"  [OK] Found contact information")
                except Exception as e:
                    print(f"  [ERROR] Error extracting contacts: {e}")
                
                # Extract organization info (funders, partners, major areas of work, etc.)
                try:
                    org_info = website_enricher.extract_organization_info(url)
                    if org_info:
                        enriched['organization_info'] = org_info
                        funders_count = len(org_info.get('funders_partners', []))
                        areas_count = len(org_info.get('major_areas_of_work', []))
                        affiliations_count = len(org_info.get('affiliations', []))
                        if funders_count > 0 or areas_count > 0 or affiliations_count > 0:
                            print(f"  [OK] Found org info: {funders_count} funders/partners, {areas_count} areas of work, {affiliations_count} affiliations")
                        else:
                            print(f"  [INFO] No additional organization info found")
                except Exception as e:
                    print(f"  [ERROR] Error extracting organization info: {e}")
        else:
            enriched['website'] = {'url': None, 'confidence': 0}
            print(f"  [MISSING] No website found")
        
        # Form 990 data
        print(f"  [SEARCH] Searching for Form 990 data...")
        form_990_data = propublica_client.enrich_member_with_form_990(
            company_name=company_name,
            city=city,
            state=state,
            ein=None  # We don't have EIN in HubSpot data
        )
        
        if form_990_data and form_990_data.get('found'):
            enriched['form_990'] = form_990_data
            financials = form_990_data.get('financials', {})
            if financials.get('ein'):
                print(f"  [OK] Found Form 990 data (EIN: {financials.get('ein')})")
            else:
                print(f"  [OK] Found Form 990 data")
        else:
            enriched['form_990'] = {'found': False}
            print(f"  [MISSING] No Form 990 data found")
        
        enriched_data[member_id] = enriched
    
    # Create comparison document
    print("\n5. Creating comparison document...")
    output_file = get_downloads_folder() / f"member_enrichment_test_10_members_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    create_comparison_document(members_data, enriched_data, output_file)
    
    # Summary
    print("\n" + "=" * 80)
    print("Summary:")
    print(f"  - Members processed: {len(members_data)}")
    websites_found = sum(1 for e in enriched_data.values() if e.get('website', {}).get('url'))
    staff_found = sum(1 for e in enriched_data.values() if e.get('staff'))
    form_990_found = sum(1 for e in enriched_data.values() if e.get('form_990', {}).get('found'))
    print(f"  - Websites found: {websites_found}")
    print(f"  - Staff info extracted: {staff_found}")
    print(f"  - Form 990 data found: {form_990_found}")
    print("=" * 80)

if __name__ == "__main__":
    main()

