#!/usr/bin/env python3
"""
Simple script to search for banking-related individuals in Epstein documents.
"""

import re
from pathlib import Path
from collections import defaultdict

# Base path to Epstein documents
BASE_PATH = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Epstein\TEXT")

# Bank email patterns
BANK_EMAILS = {
    'JP Morgan': r'@jpmorgan\.com|@jpmchase\.com',
    'Goldman Sachs': r'@goldmansachs\.com|@gs\.com',
    'Morgan Stanley': r'@morganstanley\.com',
    'Bank of America': r'@bofa\.com|@bankofamerica\.com|@ml\.com',
    'Citigroup': r'@citigroup\.com|@citi\.com',
    'Wells Fargo': r'@wellsfargo\.com',
    'BNY Mellon': r'@bny\.com',
    'State Street': r'@statestreet\.com',
}

# Bank name patterns
BANK_NAMES = [
    r'JP\s*Morgan|JPMorgan|J\.P\.\s*Morgan',
    r'Goldman\s*Sachs',
    r'Bank\s*of\s*America|BofA|Merrill\s*Lynch',
    r'Citigroup|Citi',
    r'Wells\s*Fargo',
    r'Morgan\s*Stanley',
]

def extract_name_from_email_line(line):
    """Extract name from email header line."""
    # Pattern: From: Name <email> or Name <email>
    patterns = [
        r'From:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        r'To:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s*<.*@',
    ]
    for pattern in patterns:
        match = re.search(pattern, line)
        if match:
            return match.group(1)
    return None

def search_file(filepath):
    """Search a file for banking-related content."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            content = ''.join(lines)
    except Exception as e:
        return None
    
    results = {
        'bank_emails': defaultdict(list),
        'bank_mentions': [],
        'names_near_banks': set(),
    }
    
    # Search for bank email addresses
    for bank, pattern in BANK_EMAILS.items():
        email_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*' + pattern
        matches = re.findall(email_pattern, content, re.IGNORECASE)
        if matches:
            results['bank_emails'][bank].extend(matches)
    
    # Search for bank names and extract nearby names
    for i, line in enumerate(lines):
        for bank_pattern in BANK_NAMES:
            if re.search(bank_pattern, line, re.IGNORECASE):
                results['bank_mentions'].append((i, line.strip()[:100]))
                
                # Look for names in surrounding lines
                start = max(0, i - 5)
                end = min(len(lines), i + 5)
                context = '\n'.join(lines[start:end])
                
                # Extract names from context
                name_patterns = [
                    r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s+(?:was|is|worked|served|chairman|CEO|president|secretary)',
                    r'(?:Mr\.|Ms\.|Mrs\.|Dr\.|Prof\.)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
                ]
                for pattern in name_patterns:
                    names = re.findall(pattern, context)
                    results['names_near_banks'].update(names)
    
    # Extract names from email headers
    for i, line in enumerate(lines):
        if 'From:' in line or 'To:' in line:
            name = extract_name_from_email_line(line)
            if name:
                # Check if this email is from a bank
                for bank, pattern in BANK_EMAILS.items():
                    if re.search(pattern, line, re.IGNORECASE):
                        results['bank_emails'][bank].append(name)
    
    # Only return if we found something
    if results['bank_emails'] or results['bank_mentions']:
        return results
    return None

def main():
    print("Searching for banking-related individuals...")
    print("=" * 80)
    
    all_results = defaultdict(lambda: {
        'bank_emails': defaultdict(list),
        'bank_mentions': [],
        'names_near_banks': set(),
        'files': []
    })
    
    file_count = 0
    for txt_file in BASE_PATH.rglob("*.txt"):
        file_count += 1
        if file_count % 100 == 0:
            print(f"Processed {file_count} files...")
        
        result = search_file(txt_file)
        if result:
            for bank, names in result['bank_emails'].items():
                all_results[bank]['bank_emails'][bank].extend(names)
                all_results[bank]['files'].append(txt_file.name)
            
            if result['bank_mentions']:
                all_results['_MENTIONS']['bank_mentions'].extend(result['bank_mentions'])
                all_results['_MENTIONS']['files'].append(txt_file.name)
    
    print(f"\nProcessed {file_count} files total\n")
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    
    # Print results
    for bank, data in all_results.items():
        if bank == '_MENTIONS':
            continue
        
        if data['bank_emails'].get(bank):
            print(f"\n{bank}:")
            print("-" * 80)
            unique_names = set(data['bank_emails'][bank])
            for name in sorted(unique_names):
                print(f"  - {name}")
            print(f"\n  Found in {len(set(data['files']))} file(s)")
    
    # Save to file
    output_file = Path("banking_individuals_found.txt")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("BANKING-RELATED INDIVIDUALS FOUND\n")
        f.write("=" * 80 + "\n\n")
        
        for bank, data in all_results.items():
            if bank == '_MENTIONS':
                continue
            
            if data['bank_emails'].get(bank):
                f.write(f"\n{bank}:\n")
                f.write("-" * 80 + "\n")
                unique_names = set(data['bank_emails'][bank])
                for name in sorted(unique_names):
                    f.write(f"  - {name}\n")
                f.write(f"\n  Found in {len(set(data['files']))} file(s)\n")
                f.write(f"  Files: {', '.join(set(data['files'][:10]))}\n")
                if len(data['files']) > 10:
                    f.write(f"  ... and {len(data['files']) - 10} more\n")
    
    print(f"\n\nResults saved to: {output_file}")

if __name__ == "__main__":
    main()

