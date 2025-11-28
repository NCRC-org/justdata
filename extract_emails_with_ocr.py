#!/usr/bin/env python3
"""
Extract emails from PDFs using OCR (for scanned PDFs) and re-extract from Excel files.
This supplements the main extraction script.
"""

import re
from pathlib import Path
import csv
from collections import defaultdict

EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

def extract_emails_from_text(content):
    """Extract email addresses from text content."""
    emails = re.findall(EMAIL_PATTERN, content, re.IGNORECASE)
    filtered = []
    for email in emails:
        email_lower = email.lower()
        if not any(skip in email_lower for skip in ['example.com', 'test.com', 'domain.com', 'xxx']):
            filtered.append(email)
    return filtered

def ocr_pdf(filepath):
    """Extract text from PDF using OCR."""
    emails = []
    try:
        # Try pytesseract with pdf2image
        try:
            from pdf2image import convert_from_path
            import pytesseract
            
            print(f"  Performing OCR on {filepath.name}...")
            images = convert_from_path(str(filepath))
            
            for i, image in enumerate(images):
                print(f"    Processing page {i+1}/{len(images)}...")
                text = pytesseract.image_to_string(image)
                emails.extend(extract_emails_from_text(text))
                
        except ImportError:
            print(f"  Warning: pytesseract or pdf2image not installed. Install with: pip install pytesseract pdf2image")
            print(f"  Also need: poppler (https://github.com/oschwartz10612/poppler-windows/releases)")
            return []
    except Exception as e:
        print(f"  Error during OCR: {e}")
        return []
    
    return emails

def extract_from_excel_xls(filepath):
    """Extract emails from old .xls format files."""
    emails = []
    try:
        import xlrd
        workbook = xlrd.open_workbook(filepath)
        for sheet in workbook.sheets():
            for row in range(sheet.nrows):
                for col in range(sheet.ncols):
                    cell_value = sheet.cell_value(row, col)
                    if cell_value and isinstance(cell_value, str):
                        emails.extend(extract_emails_from_text(cell_value))
    except ImportError:
        print(f"  Warning: xlrd not installed. Install with: pip install xlrd")
        return []
    except Exception as e:
        print(f"  Error reading {filepath.name}: {e}")
        return []
    
    return emails

def main():
    base_path = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Epstein")
    
    # Load existing emails to avoid duplicates
    existing_emails = set()
    csv_file = base_path / "epstein_emails.csv"
    if csv_file.exists():
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_emails.add(row['Email'].lower())
    
    print("Extracting additional emails from PDFs (OCR) and Excel files...")
    print("=" * 80)
    
    new_emails = defaultdict(lambda: {
        'emails': set(),
        'files': []
    })
    
    # Process PDFs with OCR
    print("\nProcessing PDF files with OCR...")
    pdf_files = list(base_path.rglob("*.pdf"))
    if pdf_files:
        print(f"  Found {len(pdf_files)} PDF files")
        for pdf_file in pdf_files:
            emails = ocr_pdf(pdf_file)
            if emails:
                for email in emails:
                    email_lower = email.lower()
                    if email_lower not in existing_emails:
                        new_emails[email_lower]['emails'].add(email)
                        new_emails[email_lower]['files'].append(str(pdf_file.relative_to(base_path)))
    
    # Process .xls files
    print("\nProcessing .xls Excel files...")
    natives_dir = base_path / "NATIVES"
    if natives_dir.exists():
        xls_files = list(natives_dir.rglob("*.xls"))
        if xls_files:
            print(f"  Found {len(xls_files)} .xls files")
            for xls_file in xls_files:
                print(f"  Processing {xls_file.name}...")
                emails = extract_from_excel_xls(xls_file)
                if emails:
                    for email in emails:
                        email_lower = email.lower()
                        if email_lower not in existing_emails:
                            new_emails[email_lower]['emails'].add(email)
                            new_emails[email_lower]['files'].append(str(xls_file.relative_to(base_path)))
    
    if new_emails:
        print(f"\nFound {len(new_emails)} new unique email addresses")
        
        # Append to existing CSV
        with open(csv_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            for email_lower, data in sorted(new_emails.items()):
                original_email = list(data['emails'])[0] if data['emails'] else email_lower
                files_list = list(set(data['files']))
                files_str = '; '.join(files_list[:10])
                if len(files_list) > 10:
                    files_str += f" ... and {len(files_list) - 10} more"
                
                writer.writerow([
                    email_lower,
                    original_email,
                    len(files_list),
                    files_str
                ])
        
        print(f"Added {len(new_emails)} new emails to {csv_file}")
    else:
        print("\nNo new emails found.")

if __name__ == "__main__":
    main()

