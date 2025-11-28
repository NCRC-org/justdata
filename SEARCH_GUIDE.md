# Guide: Searching for Banking-Related Individuals in Epstein Documents

## Quick Search Commands

### 1. Search for Bank Email Addresses

Search for emails from major banks:

```bash
# J.P. Morgan
grep -r "@jpmorgan\|@jpmchase" "C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Epstein\TEXT"

# Goldman Sachs
grep -r "@goldmansachs\|@gs\.com" "C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Epstein\TEXT"

# Morgan Stanley
grep -r "@morganstanley" "C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Epstein\TEXT"

# Bank of America
grep -r "@bofa\|@bankofamerica\|@ml\.com" "C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Epstein\TEXT"

# Citigroup
grep -r "@citigroup\|@citi\.com" "C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Epstein\TEXT"

# Wells Fargo
grep -r "@wellsfargo" "C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Epstein\TEXT"
```

### 2. Search for Bank Names with Context

To find names near bank mentions, search for bank names and review surrounding lines:

```bash
# Find files mentioning major banks
grep -l -i "JP Morgan\|JPMorgan\|Goldman Sachs\|Bank of America\|Citigroup\|Wells Fargo\|Morgan Stanley" "C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Epstein\TEXT\*\*.txt"

# Then read those files to extract names in context
```

### 3. Search for Banking Titles

```bash
# Search for executive titles in banking context
grep -ri "Chief Investment Officer\|Chief Executive Officer\|Managing Director\|Vice President.*bank\|investment banker" "C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Epstein\TEXT"
```

### 4. Search for Regulatory Agency Names

```bash
# Federal Reserve
grep -ri "Federal Reserve\|FRB" "C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Epstein\TEXT"

# FDIC
grep -ri "FDIC\|Federal Deposit Insurance" "C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Epstein\TEXT"

# Treasury Secretary
grep -ri "Treasury Secretary\|Secretary of the Treasury" "C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Epstein\TEXT"

# SEC
grep -ri "SEC\|Securities and Exchange Commission" "C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Epstein\TEXT"
```

## Using Python for Advanced Searches

### Simple Python Script

Create a file `search_banking_names.py`:

```python
import os
import re
from pathlib import Path

base_path = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Epstein\TEXT")

# Bank email patterns
bank_emails = {
    'JP Morgan': r'@jpmorgan\.com|@jpmchase\.com',
    'Goldman Sachs': r'@goldmansachs\.com|@gs\.com',
    'Morgan Stanley': r'@morganstanley\.com',
    'Bank of America': r'@bofa\.com|@bankofamerica\.com|@ml\.com',
    'Citigroup': r'@citigroup\.com|@citi\.com',
    'Wells Fargo': r'@wellsfargo\.com',
}

results = {}

for txt_file in base_path.rglob("*.txt"):
    try:
        with open(txt_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        # Check for bank emails
        for bank, pattern in bank_emails.items():
            matches = re.findall(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*' + pattern, content, re.IGNORECASE)
            if matches:
                if bank not in results:
                    results[bank] = []
                results[bank].append({
                    'file': txt_file.name,
                    'names': matches
                })
    except:
        continue

# Print results
for bank, entries in results.items():
    print(f"\n{bank}:")
    for entry in entries:
        print(f"  File: {entry['file']}")
        print(f"  Names: {', '.join(set(entry['names']))}")
```

Run with: `python search_banking_names.py`

## Manual Search Strategy

### Step 1: Identify Files with Bank References
Use grep to find all files mentioning banks, then review those files manually.

### Step 2: Extract Email Headers
Look for "From:" and "To:" lines in email documents - these often contain names and email addresses.

### Step 3: Contextual Name Extraction
When you find a bank mention, read 10-20 lines before and after to find associated names.

### Step 4: Cross-Reference
Check if names appear in multiple documents or contexts.

## Key Files Already Identified

Based on initial searches, these files contain banking-related content:

1. **HOUSE_OVERSIGHT_031165.txt** - J.P. Morgan newsletter (Michael Cembalest)
2. **HOUSE_OVERSIGHT_025551.txt** - Morgan Stanley research (Michael Cyprys, Alex Combs)
3. **HOUSE_OVERSIGHT_014972.txt** - Bank of America Merrill Lynch research
4. **HOUSE_OVERSIGHT_029042.txt** - Discussion of Hank Paulson (Goldman Sachs)
5. **HOUSE_OVERSIGHT_022673.txt** - References to Larry Summers (Treasury Secretary)

## Excel Files to Check

The NATIVES folder contains Excel files that might have contact lists:
- HOUSE_OVERSIGHT_016552.xls
- HOUSE_OVERSIGHT_016599.xls
- HOUSE_OVERSIGHT_016600.xls
- HOUSE_OVERSIGHT_016601.xls
- HOUSE_OVERSIGHT_016694.xlsx
- HOUSE_OVERSIGHT_016695.xls
- HOUSE_OVERSIGHT_016696.xls
- HOUSE_OVERSIGHT_016697.xls
- HOUSE_OVERSIGHT_016698.xls
- HOUSE_OVERSIGHT_026582.xlsx

These might contain contact information or lists of individuals.

## Tips

1. **Use case-insensitive searches** - Names and bank names may have inconsistent capitalization
2. **Look for variations** - "JP Morgan", "JPMorgan", "J.P. Morgan" are all the same
3. **Check email signatures** - Many banking emails have signatures with names and titles
4. **Review disclaimers** - Bank research reports often list analysts and their contact info
5. **Search for common banking terms** - "wealth management", "private banking", "investment banking"

