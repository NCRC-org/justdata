# Email Extraction Summary - Epstein Documents

## Extraction Complete

### Results
- **Total unique email addresses extracted: 664**
- **Total email occurrences: 12,321**
- **Total files processed: 2,911**
- **Banking-related emails: 160**

### Files Created

1. **epstein_emails.csv** - Complete list with file references
   - Columns: Email, Original_Case, Files_Count, Files
   - Location: `C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Epstein\epstein_emails.csv`

2. **epstein_emails.txt** - Simple list (one email per line)
   - Location: `C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Epstein\epstein_emails.txt`

3. **epstein_emails_report.txt** - Detailed report organized by domain
   - Location: `C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Epstein\epstein_emails_report.txt`

4. **epstein_banking_emails.csv** - Filtered banking-related emails only
   - Location: `C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Epstein\epstein_banking_emails.csv`

5. **epstein_regulatory_emails.csv** - Regulatory agency emails (none found)
   - Location: `C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Epstein\epstein_regulatory_emails.csv`

## Banking-Related Emails Found

### J.P. Morgan Chase (13 emails)
- us.gio@jpmorgan.com (13 files)
- jan.loeys@jpmorgan.com (5 files)
- john.normand@jpmorgan.com (5 files)
- nikolaos.panigirtzoglou@jpmorgan.com (5 files)
- seamus.macgorain@jpmorgan.com (5 files)
- matthew.m.lehmann@jpmorgan.com (5 files)
- leonard.a.evans@jpmorgan.com (5 files)
- research.disclosure.inquiries@jpmorgan.com (4 files)

### Morgan Stanley (5 emails)
- Michael.Cyprys@morganstanley.com
- Alex.Combs@morganstanley.com
- Andrew.Atlas@morganstanley.com
- ms-wmir@morganstanley.com
- mswmir-cie-feedback@morganstanley.com

### Bank of America / Merrill Lynch (BAML) (100+ emails)
- Multiple analysts and researchers
- Examples: amanda.ens@baml.com (14 files), abhinandan.deb@baml.com (4 files)

### UBS (20+ emails)
- Multiple analysts from UBS research
- Examples: achim.peijan@ubs.com, alexander.friedman@ubs.com

### Deutsche Bank (4 emails)
- blanche.christerson@db.com (4 files)

## PDF Files Status

**Note:** The 4 PDF files in the root directory appear to be scanned images:
- Request No. 1.pdf (238 pages) - No extractable text
- Request No. 2.pdf
- Request No. 4.pdf
- Request No. 8.pdf

These require OCR to extract text/emails. See `extract_emails_with_ocr.py` for OCR extraction (requires pytesseract and pdf2image).

## Excel Files Status

**Note:** Some .xls files couldn't be read initially. The script has been updated to use `xlrd` for .xls files. Re-run extraction to process these.

## Next Steps

1. **For PDF OCR:**
   ```bash
   pip install pytesseract pdf2image
   # Download poppler from: https://github.com/oschwartz10612/poppler-windows/releases
   python extract_emails_with_ocr.py
   ```

2. **Re-extract from Excel:**
   ```bash
   pip install xlrd
   python extract_emails.py  # Re-run to process .xls files
   ```

3. **Compare with your downloaded emails:**
   - Use the CSV files to cross-reference
   - Banking emails are in `epstein_banking_emails.csv`

## Scripts Available

1. **extract_emails.py** - Main extraction script (text, PDF, Excel)
2. **extract_emails_with_ocr.py** - OCR extraction for scanned PDFs
3. **extract_banking_emails.py** - Filter banking-related emails from extracted list

