#!/usr/bin/env python3
"""
Search for contacts from all-contacts.csv in Epstein documents.
Searches by name and email address.
"""

import csv
import re
from pathlib import Path
from collections import defaultdict
import sys

def normalize_name(name):
    """Normalize name for searching (remove extra spaces, lowercase)."""
    if not name:
        return ""
    return " ".join(name.split()).lower()

def normalize_email(email):
    """Normalize email for searching."""
    if not email:
        return ""
    return email.strip().lower()

def create_search_patterns(contact):
    """Create search patterns for a contact."""
    patterns = []
    
    first_name = contact.get('First Name', '').strip()
    last_name = contact.get('Last Name', '').strip()
    email = contact.get('Email', '').strip()
    additional_emails = contact.get('Additional email addresses', '').strip()
    
    # Full name pattern
    if first_name and last_name:
        # Exact match
        patterns.append({
            'type': 'full_name',
            'pattern': rf'\b{re.escape(first_name)}\s+{re.escape(last_name)}\b',
            'case_sensitive': False
        })
        # Last, First format
        patterns.append({
            'type': 'full_name_reverse',
            'pattern': rf'\b{re.escape(last_name)},\s*{re.escape(first_name)}\b',
            'case_sensitive': False
        })
    
    # Email patterns
    if email:
        patterns.append({
            'type': 'email',
            'pattern': re.escape(email),
            'case_sensitive': False
        })
    
    # Additional emails
    if additional_emails:
        for add_email in additional_emails.split(';'):
            add_email = add_email.strip()
            if add_email:
                patterns.append({
                    'type': 'additional_email',
                    'pattern': re.escape(add_email),
                    'case_sensitive': False
                })
    
    return patterns

def search_file(filepath, contact_patterns, contact_id):
    """Search a file for contact patterns."""
    matches = []
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        return matches
    
    for pattern_info in contact_patterns:
        pattern = pattern_info['pattern']
        flags = 0 if pattern_info.get('case_sensitive', False) else re.IGNORECASE
        
        if re.search(pattern, content, flags):
            # Get context around the match
            matches_found = list(re.finditer(pattern, content, flags))
            for match in matches_found[:3]:  # Limit to first 3 matches per pattern type
                start = max(0, match.start() - 100)
                end = min(len(content), match.end() + 100)
                context = content[start:end].replace('\n', ' ').strip()
                
                matches.append({
                    'type': pattern_info['type'],
                    'context': context[:200]  # Limit context length
                })
    
    return matches

def main():
    contacts_file = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\all-contacts.csv")
    epstein_base = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Epstein\TEXT")
    
    print("Loading contacts...")
    contacts = []
    with open(contacts_file, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            contacts.append(row)
    
    print(f"Loaded {len(contacts)} contacts")
    print("Creating search patterns...")
    
    # Create search patterns for each contact
    contact_patterns = {}
    for i, contact in enumerate(contacts):
        contact_id = contact.get('Record ID', str(i))
        patterns = create_search_patterns(contact)
        if patterns:
            contact_patterns[contact_id] = {
                'contact': contact,
                'patterns': patterns
            }
    
    print(f"Created patterns for {len(contact_patterns)} contacts with searchable data")
    print(f"\nSearching Epstein documents...")
    print("=" * 80)
    
    # Get all text files
    text_files = list(epstein_base.rglob("*.txt"))
    print(f"Found {len(text_files)} text files to search")
    
    # Results: contact_id -> list of files where found
    results = defaultdict(lambda: {
        'contact': None,
        'files': defaultdict(list)
    })
    
    file_count = 0
    for txt_file in text_files:
        file_count += 1
        if file_count % 500 == 0:
            print(f"  Processed {file_count}/{len(text_files)} files, found {len(results)} matches so far...")
        
        for contact_id, contact_data in contact_patterns.items():
            matches = search_file(txt_file, contact_data['patterns'], contact_id)
            if matches:
                if results[contact_id]['contact'] is None:
                    results[contact_id]['contact'] = contact_data['contact']
                
                for match in matches:
                    results[contact_id]['files'][str(txt_file.relative_to(epstein_base))].append(match)
    
    print(f"\n{'='*80}")
    print(f"Search complete!")
    print(f"  Files searched: {len(text_files)}")
    print(f"  Contacts found: {len(results)}")
    print(f"{'='*80}\n")
    
    # Export results to CSV
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
            files_list = list(data['files'].keys())
            
            # Collect match types
            match_types = set()
            for file_matches in data['files'].values():
                for match in file_matches:
                    match_types.add(match['type'])
            
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
                ', '.join(sorted(match_types))
            ])
    
    # Export detailed report
    output_report = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Epstein\contacts_found_in_epstein_report.txt")
    print(f"Exporting detailed report to: {output_report}")
    
    with open(output_report, 'w', encoding='utf-8') as f:
        f.write("CONTACTS FOUND IN EPSTEIN DOCUMENTS\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Total contacts searched: {len(contacts)}\n")
        f.write(f"Contacts found in Epstein documents: {len(results)}\n")
        f.write(f"Files searched: {len(text_files)}\n\n")
        f.write("=" * 80 + "\n\n")
        
        for contact_id, data in sorted(results.items(), key=lambda x: len(x[1]['files']), reverse=True):
            contact = data['contact']
            files_list = list(data['files'].keys())
            
            f.write(f"\n{contact.get('First Name', '')} {contact.get('Last Name', '')}\n")
            f.write(f"Record ID: {contact_id}\n")
            f.write(f"Email: {contact.get('Email', 'N/A')}\n")
            f.write(f"Company: {contact.get('Associated Company', 'N/A')}\n")
            f.write(f"Found in {len(files_list)} file(s):\n")
            f.write("-" * 80 + "\n")
            
            for file_path in files_list[:20]:  # Limit to first 20 files
                matches = data['files'][file_path]
                match_types = ', '.join(set(m['type'] for m in matches))
                f.write(f"  {file_path} ({match_types})\n")
                
                # Show first match context
                if matches:
                    f.write(f"    Context: {matches[0]['context']}\n")
            
            if len(files_list) > 20:
                f.write(f"  ... and {len(files_list) - 20} more files\n")
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

