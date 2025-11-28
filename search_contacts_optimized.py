#!/usr/bin/env python3
"""
Optimized search: Index Epstein documents first, then match contacts.
Much faster than searching each file for each contact.
"""

import csv
import re
from pathlib import Path
from collections import defaultdict
import sys

def extract_names_and_emails_from_text(content):
    """Extract all names and emails from text for indexing."""
    # Email pattern
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = set(re.findall(email_pattern, content, re.IGNORECASE))
    
    # Name patterns (First Last, Last, First)
    # This is a simplified approach - we'll match against actual contact names
    names = set()
    
    return emails, names

def build_epstein_index(epstein_base):
    """Build an index of all emails and names from Epstein documents."""
    print("Building index of Epstein documents...")
    
    email_index = defaultdict(list)  # email -> list of files
    file_contents = {}  # file -> content (for later context extraction)
    
    text_files = list(epstein_base.rglob("*.txt"))
    print(f"Indexing {len(text_files)} files...")
    
    file_count = 0
    for txt_file in text_files:
        file_count += 1
        if file_count % 500 == 0:
            print(f"  Indexed {file_count}/{len(text_files)} files...")
        
        try:
            with open(txt_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except:
            continue
        
        file_path = str(txt_file.relative_to(epstein_base))
        file_contents[file_path] = content
        
        # Index emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, content, re.IGNORECASE)
        for email in emails:
            email_lower = email.lower()
            if email_lower not in email_index:
                email_index[email_lower] = []
            email_index[email_lower].append(file_path)
    
    print(f"Indexed {len(email_index)} unique emails")
    return email_index, file_contents

def normalize_name(name):
    """Normalize name for matching."""
    if not name:
        return None
    return " ".join(name.split()).lower().strip()

def search_contacts(contacts_file, email_index, file_contents):
    """Match contacts against the Epstein index."""
    print(f"\nMatching contacts against Epstein index...")
    
    results = defaultdict(lambda: {
        'contact': None,
        'files': set(),
        'match_types': set()
    })
    
    with open(contacts_file, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        contact_count = 0
        
        for contact in reader:
            contact_count += 1
            if contact_count % 10000 == 0:
                print(f"  Processed {contact_count} contacts, found {len(results)} matches so far...")
            
            contact_id = contact.get('Record ID', str(contact_count))
            first_name = contact.get('First Name', '').strip()
            last_name = contact.get('Last Name', '').strip()
            email = contact.get('Email', '').strip().lower()
            additional_emails = contact.get('Additional email addresses', '').strip()
            
            # Check email matches
            if email and email in email_index:
                if results[contact_id]['contact'] is None:
                    results[contact_id]['contact'] = contact
                results[contact_id]['files'].update(email_index[email])
                results[contact_id]['match_types'].add('email')
            
            # Check additional emails
            if additional_emails:
                for add_email in additional_emails.split(';'):
                    add_email = add_email.strip().lower()
                    if add_email and add_email in email_index:
                        if results[contact_id]['contact'] is None:
                            results[contact_id]['contact'] = contact
                        results[contact_id]['files'].update(email_index[add_email])
                        results[contact_id]['match_types'].add('additional_email')
            
            # Check name matches (search in files where email matched, or all files if no email)
            if first_name and last_name:
                full_name_pattern = rf'\b{re.escape(first_name)}\s+{re.escape(last_name)}\b'
                reverse_name_pattern = rf'\b{re.escape(last_name)},\s*{re.escape(first_name)}\b'
                
                # If we already found files via email, search those; otherwise search all
                files_to_search = list(results[contact_id]['files']) if results[contact_id]['files'] else list(file_contents.keys())
                
                for file_path in files_to_search[:100]:  # Limit to first 100 files to avoid slowdown
                    content = file_contents.get(file_path, '')
                    if re.search(full_name_pattern, content, re.IGNORECASE):
                        if results[contact_id]['contact'] is None:
                            results[contact_id]['contact'] = contact
                        results[contact_id]['files'].add(file_path)
                        results[contact_id]['match_types'].add('full_name')
                    elif re.search(reverse_name_pattern, content, re.IGNORECASE):
                        if results[contact_id]['contact'] is None:
                            results[contact_id]['contact'] = contact
                        results[contact_id]['files'].add(file_path)
                        results[contact_id]['match_types'].add('full_name_reverse')
    
    return results

def main():
    contacts_file = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\all-contacts.csv")
    epstein_base = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Epstein\TEXT")
    
    # Build index
    email_index, file_contents = build_epstein_index(epstein_base)
    
    # Match contacts
    results = search_contacts(contacts_file, email_index, file_contents)
    
    print(f"\n{'='*80}")
    print(f"Search complete!")
    print(f"  Contacts found: {len(results)}")
    print(f"{'='*80}\n")
    
    # Export results
    output_csv = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Epstein\contacts_found_in_epstein.csv")
    print(f"Exporting results to: {output_csv}")
    
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Record ID',
            'First Name',
            'Last Name',
            'Email',
            'Additional Emails',
            'Associated Company',
            'Files_Count',
            'Files',
            'Match_Types'
        ])
        
        for contact_id, data in sorted(results.items()):
            contact = data['contact']
            files_list = sorted(list(data['files']))
            
            files_str = '; '.join(files_list[:10])
            if len(files_list) > 10:
                files_str += f" ... and {len(files_list) - 10} more"
            
            writer.writerow([
                contact_id,
                contact.get('First Name', ''),
                contact.get('Last Name', ''),
                contact.get('Email', ''),
                contact.get('Additional email addresses', ''),
                contact.get('Associated Company', ''),
                len(files_list),
                files_str,
                ', '.join(sorted(data['match_types']))
            ])
    
    # Export detailed report
    output_report = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Epstein\contacts_found_in_epstein_report.txt")
    print(f"Exporting detailed report to: {output_report}")
    
    with open(output_report, 'w', encoding='utf-8') as f:
        f.write("CONTACTS FOUND IN EPSTEIN DOCUMENTS\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Contacts found: {len(results)}\n\n")
        f.write("=" * 80 + "\n\n")
        
        # Sort by number of files
        sorted_results = sorted(results.items(), key=lambda x: len(x[1]['files']), reverse=True)
        
        for contact_id, data in sorted_results:
            contact = data['contact']
            files_list = sorted(list(data['files']))
            
            name = f"{contact.get('First Name', '')} {contact.get('Last Name', '')}".strip()
            if not name:
                name = contact.get('Email', 'N/A')
            
            f.write(f"\n{name}\n")
            f.write(f"Record ID: {contact_id}\n")
            f.write(f"Email: {contact.get('Email', 'N/A')}\n")
            f.write(f"Company: {contact.get('Associated Company', 'N/A')}\n")
            f.write(f"Match Types: {', '.join(sorted(data['match_types']))}\n")
            f.write(f"Found in {len(files_list)} file(s):\n")
            f.write("-" * 80 + "\n")
            
            for file_path in files_list[:30]:  # Show first 30 files
                f.write(f"  {file_path}\n")
            
            if len(files_list) > 30:
                f.write(f"  ... and {len(files_list) - 30} more files\n")
            f.write("\n")
    
    print(f"\nExport complete!")
    print(f"\nSummary:")
    print(f"  Contacts found: {len(results)}")
    print(f"  CSV file: {output_csv}")
    print(f"  Detailed report: {output_report}")
    
    # Print top matches
    if results:
        print(f"\nTop 10 contacts by number of file matches:")
        sorted_results = sorted(results.items(), key=lambda x: len(x[1]['files']), reverse=True)[:10]
        for contact_id, data in sorted_results:
            contact = data['contact']
            name = f"{contact.get('First Name', '')} {contact.get('Last Name', '')}".strip()
            if not name:
                name = contact.get('Email', 'N/A')
            print(f"  {name}: {len(data['files'])} file(s)")

if __name__ == "__main__":
    main()

