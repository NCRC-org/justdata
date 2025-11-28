#!/usr/bin/env python3
"""
Extract all email addresses from Epstein documents.
Handles text files, PDFs (with text extraction), and Excel files.
"""

import re
import csv
from pathlib import Path
from collections import defaultdict
import sys

# Email regex pattern (comprehensive)
EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

def extract_emails_from_text(content):
    """Extract email addresses from text content."""
    emails = re.findall(EMAIL_PATTERN, content, re.IGNORECASE)
    # Filter out common false positives
    filtered = []
    for email in emails:
        email_lower = email.lower()
        # Skip common false positives
        if not any(skip in email_lower for skip in ['example.com', 'test.com', 'domain.com', 'xxx']):
            filtered.append(email)
    return filtered

def extract_from_text_file(filepath):
    """Extract emails from a text file."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return extract_emails_from_text(content)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return []

def extract_from_pdf(filepath):
    """Extract emails from PDF file."""
    emails = []
    try:
        # Try pdfplumber first (better text extraction)
        try:
            import pdfplumber
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        emails.extend(extract_emails_from_text(text))
        except ImportError:
            # Fall back to PyPDF2
            try:
                import PyPDF2
                with open(filepath, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    for page in pdf_reader.pages:
                        text = page.extract_text()
                        if text:
                            emails.extend(extract_emails_from_text(text))
            except ImportError:
                # Try pymupdf (fitz)
                try:
                    import fitz  # PyMuPDF
                    doc = fitz.open(filepath)
                    for page in doc:
                        text = page.get_text()
                        if text:
                            emails.extend(extract_emails_from_text(text))
                    doc.close()
                except ImportError:
                    print(f"Warning: No PDF library available. Install pdfplumber, PyPDF2, or PyMuPDF")
                    return []
    except Exception as e:
        print(f"Error reading PDF {filepath}: {e}")
        return []
    
    return emails

def extract_from_excel(filepath):
    """Extract emails from Excel file."""
    emails = []
    file_ext = filepath.suffix.lower()
    
    # Handle old .xls format with xlrd
    if file_ext == '.xls':
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
            print(f"Warning: xlrd not installed. Cannot read .xls file: {filepath}")
            return []
        except Exception as e:
            print(f"Error reading .xls file {filepath}: {e}")
            return []
    else:
        # Handle .xlsx format with openpyxl
        try:
            import openpyxl
            wb = openpyxl.load_workbook(filepath, data_only=True)
            for sheet in wb.worksheets:
                for row in sheet.iter_rows(values_only=True):
                    for cell in row:
                        if cell and isinstance(cell, str):
                            emails.extend(extract_emails_from_text(cell))
        except ImportError:
            print(f"Warning: openpyxl not installed. Cannot read .xlsx file: {filepath}")
            return []
        except Exception as e:
            print(f"Error reading .xlsx file {filepath}: {e}")
            return []
    
    return emails

def main():
    base_path = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Epstein")
    
    print("Extracting email addresses from Epstein documents...")
    print("=" * 80)
    
    all_emails = defaultdict(lambda: {
        'emails': set(),
        'files': []
    })
    
    file_count = 0
    email_count = 0
    
    # Process text files
    print("\nProcessing text files...")
    text_dir = base_path / "TEXT"
    if text_dir.exists():
        for txt_file in text_dir.rglob("*.txt"):
            file_count += 1
            if file_count % 500 == 0:
                print(f"  Processed {file_count} text files, found {email_count} unique emails so far...")
            
            emails = extract_from_text_file(txt_file)
            if emails:
                for email in emails:
                    email_lower = email.lower()
                    all_emails[email_lower]['emails'].add(email)  # Preserve original case
                    all_emails[email_lower]['files'].append(str(txt_file.relative_to(base_path)))
                    email_count += 1
    
    # Process PDF files
    print("\nProcessing PDF files...")
    pdf_files = list(base_path.rglob("*.pdf"))
    if pdf_files:
        print(f"  Found {len(pdf_files)} PDF files")
        for pdf_file in pdf_files:
            file_count += 1
            print(f"  Processing {pdf_file.name}...")
            emails = extract_from_pdf(pdf_file)
            if emails:
                for email in emails:
                    email_lower = email.lower()
                    all_emails[email_lower]['emails'].add(email)
                    all_emails[email_lower]['files'].append(str(pdf_file.relative_to(base_path)))
                    email_count += 1
    
    # Process Excel files
    print("\nProcessing Excel files...")
    natives_dir = base_path / "NATIVES"
    if natives_dir.exists():
        excel_files = list(natives_dir.rglob("*.xls*"))
        if excel_files:
            print(f"  Found {len(excel_files)} Excel files")
            for excel_file in excel_files:
                file_count += 1
                print(f"  Processing {excel_file.name}...")
                emails = extract_from_excel(excel_file)
                if emails:
                    for email in emails:
                        email_lower = email.lower()
                        all_emails[email_lower]['emails'].add(email)
                        all_emails[email_lower]['files'].append(str(excel_file.relative_to(base_path)))
                        email_count += 1
    
    print(f"\n{'='*80}")
    print(f"Processing complete!")
    print(f"  Total files processed: {file_count}")
    print(f"  Total unique email addresses: {len(all_emails)}")
    print(f"  Total email occurrences: {email_count}")
    print(f"{'='*80}\n")
    
    # Export to CSV
    csv_file = base_path / "epstein_emails.csv"
    print(f"Exporting to CSV: {csv_file}")
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Email', 'Original_Case', 'Files_Count', 'Files'])
        
        for email_lower, data in sorted(all_emails.items()):
            # Use the first original case version found
            original_email = list(data['emails'])[0] if data['emails'] else email_lower
            files_list = list(set(data['files']))  # Deduplicate files
            files_str = '; '.join(files_list[:10])  # Limit to first 10 files
            if len(files_list) > 10:
                files_str += f" ... and {len(files_list) - 10} more"
            
            writer.writerow([
                email_lower,
                original_email,
                len(files_list),
                files_str
            ])
    
    # Export to simple text file (one email per line)
    txt_file = base_path / "epstein_emails.txt"
    print(f"Exporting to text file: {txt_file}")
    with open(txt_file, 'w', encoding='utf-8') as f:
        for email_lower in sorted(all_emails.keys()):
            f.write(f"{email_lower}\n")
    
    # Export detailed report
    report_file = base_path / "epstein_emails_report.txt"
    print(f"Exporting detailed report: {report_file}")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("EPSTEIN DOCUMENTS - EMAIL ADDRESSES EXTRACTION REPORT\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Total unique email addresses: {len(all_emails)}\n")
        f.write(f"Total email occurrences: {email_count}\n")
        f.write(f"Total files processed: {file_count}\n\n")
        f.write("=" * 80 + "\n\n")
        
        # Group by domain
        by_domain = defaultdict(list)
        for email_lower, data in all_emails.items():
            domain = email_lower.split('@')[1] if '@' in email_lower else 'unknown'
            by_domain[domain].append((email_lower, data))
        
        f.write("EMAILS BY DOMAIN\n")
        f.write("=" * 80 + "\n\n")
        for domain in sorted(by_domain.keys()):
            f.write(f"\n{domain} ({len(by_domain[domain])} emails)\n")
            f.write("-" * 80 + "\n")
            for email_lower, data in sorted(by_domain[domain]):
                original_email = list(data['emails'])[0] if data['emails'] else email_lower
                files_list = list(set(data['files']))
                f.write(f"  {original_email}\n")
                f.write(f"    Found in {len(files_list)} file(s)\n")
                if len(files_list) <= 5:
                    for file_path in files_list:
                        f.write(f"      - {file_path}\n")
                else:
                    for file_path in files_list[:3]:
                        f.write(f"      - {file_path}\n")
                    f.write(f"      ... and {len(files_list) - 3} more files\n")
            f.write("\n")
    
    print("\nExport complete!")
    print(f"\nFiles created:")
    print(f"  1. {csv_file} - CSV format with file references")
    print(f"  2. {txt_file} - Simple text file (one email per line)")
    print(f"  3. {report_file} - Detailed report organized by domain")

if __name__ == "__main__":
    main()

