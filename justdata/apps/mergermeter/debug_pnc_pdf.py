"""
Debug script to see the actual table structure of the PNC PDF.
"""

import pdfplumber
from pathlib import Path

pdf_path = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\PNC Bank Assessment Area 2022.pdf")

with pdfplumber.open(str(pdf_path)) as pdf:
    # Look at first few pages to understand structure
    for page_num in [1, 2, 3]:
        page = pdf.pages[page_num - 1]
        print(f"\n{'='*80}")
        print(f"PAGE {page_num}")
        print(f"{'='*80}\n")
        
        tables = page.extract_tables()
        print(f"Found {len(tables)} table(s)")
        
        for table_idx, table in enumerate(tables):
            print(f"\nTable {table_idx + 1}:")
            print(f"  Rows: {len(table)}")
            
            # Show first 10 rows
            for row_idx, row in enumerate(table[:10]):
                if row:
                    print(f"  Row {row_idx}: {row}")
            
            if len(table) > 10:
                print(f"  ... ({len(table) - 10} more rows)")

