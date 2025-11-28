#!/usr/bin/env python3
"""
Extract and filter banking-related email addresses from the extracted emails.
"""

import csv
from pathlib import Path

# Banking-related domains
BANKING_DOMAINS = [
    'jpmorgan.com', 'jpmchase.com',
    'goldmansachs.com', 'gs.com',
    'morganstanley.com',
    'bofa.com', 'bankofamerica.com', 'ml.com', 'merrill.com',
    'citigroup.com', 'citi.com',
    'wellsfargo.com',
    'bny.com', 'bnymellon.com',
    'statestreet.com',
    'northerntrust.com',
    'deutsche-bank.com', 'db.com',
    'credit-suisse.com', 'credit-suisse.ch',
    'ubs.com',
    'barclays.com',
    'hsbc.com',
]

# Regulatory domains
REGULATORY_DOMAINS = [
    'federalreserve.gov', 'frb.gov',
    'fdic.gov',
    'occ.gov', 'occ.treas.gov',
    'sec.gov',
    'cfpb.gov', 'consumerfinance.gov',
    'treasury.gov',
]

def main():
    base_path = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Epstein")
    csv_file = base_path / "epstein_emails.csv"
    
    if not csv_file.exists():
        print(f"Error: {csv_file} not found. Run extract_emails.py first.")
        return
    
    banking_emails = []
    regulatory_emails = []
    
    print("Filtering banking-related emails...")
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = row['Email'].lower()
            domain = email.split('@')[1] if '@' in email else ''
            
            if any(bank_domain in domain for bank_domain in BANKING_DOMAINS):
                banking_emails.append(row)
            elif any(reg_domain in domain for reg_domain in REGULATORY_DOMAINS):
                regulatory_emails.append(row)
    
    # Export banking emails
    banking_file = base_path / "epstein_banking_emails.csv"
    with open(banking_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['Email', 'Original_Case', 'Files_Count', 'Files'])
        writer.writeheader()
        writer.writerows(banking_emails)
    
    # Export regulatory emails
    regulatory_file = base_path / "epstein_regulatory_emails.csv"
    with open(regulatory_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['Email', 'Original_Case', 'Files_Count', 'Files'])
        writer.writeheader()
        writer.writerows(regulatory_emails)
    
    print(f"\nResults:")
    print(f"  Banking-related emails: {len(banking_emails)}")
    print(f"  Regulatory emails: {len(regulatory_emails)}")
    print(f"\nFiles created:")
    print(f"  1. {banking_file}")
    print(f"  2. {regulatory_file}")
    
    # Print summary
    if banking_emails:
        print(f"\nBanking Emails Found:")
        for row in banking_emails[:20]:  # Show first 20
            print(f"  {row['Original_Case']} (in {row['Files_Count']} file(s))")
        if len(banking_emails) > 20:
            print(f"  ... and {len(banking_emails) - 20} more")

if __name__ == "__main__":
    main()

