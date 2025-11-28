#!/usr/bin/env python3
"""
Fast search using pre-extracted emails from Epstein documents.
Matches contacts by email first (fast), then searches for names in matching files.
"""

import csv
import re
from pathlib import Path
from collections import defaultdict

def load_epstein_emails():
    """Load emails from the pre-extracted CSV."""
    epstein_csv = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Epstein\epstein_emails.csv")
    
    email_to_files = defaultdict(set)
    
    if epstein_csv.exists():
        print(f"Loading emails from {epstein_csv.name}...")
        with open(epstein_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row['Email'].lower()
                files_str = row.get('Files', '')
                if files_str:
                    files = [f.strip() for f in files_str.split(';')]
                    email_to_files[email].update(files)
        
        print(f"Loaded {len(email_to_files)} unique emails")
    else:
        print(f"Warning: {epstein_csv} not found. Email matching will be limited.")
    
    return email_to_files

def search_names_in_files(first_name, last_name, file_paths, epstein_base):
    """Search for names in specific files."""
    if not first_name or not last_name:
        return set()
    
    full_name_pattern = rf'\b{re.escape(first_name)}\s+{re.escape(last_name)}\b'
    reverse_name_pattern = rf'\b{re.escape(last_name)},\s*{re.escape(first_name)}\b'
    
    matching_files = set()
    
    # Limit to first 50 files to keep it fast
    for file_path in list(file_paths)[:50]:
        full_path = epstein_base / file_path
        if not full_path.exists():
            continue
        
        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            if re.search(full_name_pattern, content, re.IGNORECASE) or \
               re.search(reverse_name_pattern, content, re.IGNORECASE):
                matching_files.add(file_path)
        except:
            continue
    
    return matching_files

def main():
    contacts_file = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\all-contacts.csv")
    epstein_base = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Epstein\TEXT")
    
    # Load Epstein email index
    email_to_files = load_epstein_emails()
    
    print(f"\nMatching contacts...")
    
    results = defaultdict(lambda: {
        'contact': None,
        'files': set(),
        'match_types': set()
    })
    
    with open(contacts_file, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        contact_count = 0
        email_matches = 0
        
        for contact in reader:
            contact_count += 1
            if contact_count % 10000 == 0:
                print(f"  Processed {contact_count} contacts, {email_matches} email matches, {len(results)} total matches...")
            
            contact_id = contact.get('Record ID', str(contact_count))
            first_name = contact.get('First Name', '').strip()
            last_name = contact.get('Last Name', '').strip()
            email = contact.get('Email', '').strip().lower()
            additional_emails = contact.get('Additional email addresses', '').strip()
            
            # Check email matches (fast lookup)
            matched_files = set()
            if email and email in email_to_files:
                matched_files.update(email_to_files[email])
                if results[contact_id]['contact'] is None:
                    results[contact_id]['contact'] = contact
                results[contact_id]['files'].update(matched_files)
                results[contact_id]['match_types'].add('email')
                email_matches += 1
            
            # Check additional emails
            if additional_emails:
                for add_email in additional_emails.split(';'):
                    add_email = add_email.strip().lower()
                    if add_email and add_email in email_to_files:
                        matched_files.update(email_to_files[add_email])
                        if results[contact_id]['contact'] is None:
                            results[contact_id]['contact'] = contact
                        results[contact_id]['files'].update(email_to_files[add_email])
                        results[contact_id]['match_types'].add('additional_email')
                        email_matches += 1
            
            # If we found files via email, search for names in those files
            if matched_files and first_name and last_name:
                name_matches = search_names_in_files(first_name, last_name, matched_files, epstein_base)
                if name_matches:
                    results[contact_id]['files'].update(name_matches)
                    results[contact_id]['match_types'].add('name_in_email_files')
    
    print(f"\n{'='*80}")
    print(f"Search complete!")
    print(f"  Total contacts processed: {contact_count}")
    print(f"  Email matches: {email_matches}")
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
        f.write(f"Total contacts searched: {contact_count}\n")
        f.write(f"Contacts found: {len(results)}\n")
        f.write(f"Email matches: {email_matches}\n\n")
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
            
            for file_path in files_list[:30]:
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

