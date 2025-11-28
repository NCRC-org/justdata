#!/usr/bin/env python3
"""
Script to extract names of people associated with major US banks, banking regulators,
or banking-related firms from the Epstein documents.
"""

import os
import re
from pathlib import Path

# Major US banks and banking-related terms
BANK_KEYWORDS = [
    # Major banks
    r'JP\s*Morgan|JPMorgan|J\.P\.\s*Morgan',
    r'Goldman\s*Sachs',
    r'Bank\s*of\s*America|BofA|Merrill\s*Lynch',
    r'Citigroup|Citi',
    r'Wells\s*Fargo',
    r'Morgan\s*Stanley',
    r'Bank\s*of\s*New\s*York|BNY\s*Mellon',
    r'State\s*Street',
    r'Northern\s*Trust',
    r'Deutsche\s*Bank',
    r'Credit\s*Suisse',
    r'UBS',
    r'Barclays',
    r'HSBC',
    
    # Regulatory agencies
    r'Federal\s*Reserve|FRB',
    r'FDIC|Federal\s*Deposit\s*Insurance',
    r'OCC|Office\s*of\s*the\s*Comptroller',
    r'SEC|Securities\s*and\s*Exchange\s*Commission',
    r'CFPB|Consumer\s*Financial\s*Protection',
    r'Treasury\s*Secretary|Secretary\s*of\s*the\s*Treasury',
    
    # Banking roles
    r'Chief\s*Investment\s*Officer|CIO',
    r'Chief\s*Executive\s*Officer|CEO',
    r'Managing\s*Director',
    r'Vice\s*President|VP\s+[A-Z]',
    r'investment\s*banker',
    r'bank\s*executive',
]

# Email patterns for banks
EMAIL_PATTERNS = [
    r'@jpmorgan\.com',
    r'@goldmansachs\.com',
    r'@bofa\.com|@bankofamerica\.com',
    r'@citigroup\.com|@citi\.com',
    r'@wellsfargo\.com',
    r'@morganstanley\.com',
    r'@bny\.com',
    r'@statestreet\.com',
]

def extract_names_near_keyword(text, keyword_match, context_lines=5):
    """Extract potential names near a keyword match."""
    lines = text.split('\n')
    matches = []
    
    for i, line in enumerate(lines):
        if re.search(keyword_match, line, re.IGNORECASE):
            # Get context around the match
            start = max(0, i - context_lines)
            end = min(len(lines), i + context_lines)
            context = '\n'.join(lines[start:end])
            
            # Look for name patterns (Title First Last or First Last)
            name_patterns = [
                r'(?:Mr\.|Ms\.|Mrs\.|Dr\.|Prof\.)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
                r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s+(?:was|is|worked|served|chairman|CEO|president)',
                r'From:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
                r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s+@',
            ]
            
            for pattern in name_patterns:
                name_matches = re.findall(pattern, context)
                matches.extend(name_matches)
    
    return matches

def search_file(filepath):
    """Search a single file for banking-related content."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        return []
    
    results = []
    
    # Search for bank keywords
    for keyword in BANK_KEYWORDS:
        if re.search(keyword, content, re.IGNORECASE):
            # Extract context and potential names
            names = extract_names_near_keyword(content, keyword)
            if names:
                results.append({
                    'file': str(filepath),
                    'keyword': keyword,
                    'names': list(set(names)),
                    'type': 'bank_keyword'
                })
    
    # Search for bank email addresses
    for email_pattern in EMAIL_PATTERNS:
        email_matches = re.findall(r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s*' + email_pattern, content, re.IGNORECASE)
        if email_matches:
            results.append({
                'file': str(filepath),
                'keyword': email_pattern,
                'names': list(set(email_matches)),
                'type': 'bank_email'
            })
    
    return results

def main():
    base_path = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Epstein")
    text_dir = base_path / "TEXT"
    
    all_results = []
    
    # Search all text files
    for txt_file in text_dir.rglob("*.txt"):
        results = search_file(txt_file)
        all_results.extend(results)
    
    # Print summary
    print("=" * 80)
    print("BANKING-RELATED INDIVIDUALS FOUND IN EPSTEIN DOCUMENTS")
    print("=" * 80)
    print()
    
    # Collect all unique names
    all_names = set()
    name_to_files = {}
    
    for result in all_results:
        for name in result['names']:
            all_names.add(name)
            if name not in name_to_files:
                name_to_files[name] = []
            name_to_files[name].append({
                'file': result['file'],
                'keyword': result['keyword'],
                'type': result['type']
            })
    
    print(f"Total unique names found: {len(all_names)}")
    print()
    
    # Print detailed results
    for name in sorted(all_names):
        print(f"\n{name}")
        print("-" * 80)
        for ref in name_to_files[name]:
            print(f"  File: {Path(ref['file']).name}")
            print(f"  Context: {ref['keyword']}")
            print(f"  Type: {ref['type']}")
            print()
    
    # Save to file
    output_file = base_path / "banking_individuals_report.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("BANKING-RELATED INDIVIDUALS FOUND IN EPSTEIN DOCUMENTS\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Total unique names found: {len(all_names)}\n\n")
        
        for name in sorted(all_names):
            f.write(f"\n{name}\n")
            f.write("-" * 80 + "\n")
            for ref in name_to_files[name]:
                f.write(f"  File: {Path(ref['file']).name}\n")
                f.write(f"  Context: {ref['keyword']}\n")
                f.write(f"  Type: {ref['type']}\n\n")
    
    print(f"\nReport saved to: {output_file}")

if __name__ == "__main__":
    main()

