# Email Search Script Guide

## Overview
This script:
1. **Finds Missing Emails**: Identifies contacts in the JSON file that lack email addresses and uses DuckDuckGo search to find their email addresses
2. **Discovers New Contacts**: While searching, discovers additional contacts at the same company that aren't in your database
3. **Broad Search**: Searches event pages, conference sites, company websites, and other sources (not limited to company websites)
4. **Domain Verification**: Only includes contacts with emails matching the company domain (e.g., @abchousing.org, @abchousing.com)

## Installation

First, install the required library:
```bash
pip install duckduckgo-search
```

Or use the batch file:
```bash
run_email_search.bat
```

## Usage

### Basic Usage (Process all contacts without emails)
```bash
python find_missing_emails.py
```

### Process a limited number (for testing)
```bash
python find_missing_emails.py --limit 10
```

### Resume from a specific index
```bash
python find_missing_emails.py --start-from 100
```

### Custom input/output files
```bash
python find_missing_emails.py --input "path/to/contacts.json" --output "path/to/enriched.json"
```

### Adjust delay between searches (to avoid rate limiting)
```bash
python find_missing_emails.py --delay 3.0
```

## Command Line Options

- `--input`: Path to input JSON file (default: Cursor Agent Backups/all_contacts.json)
- `--output`: Path to output JSON file (default: adds '_enriched' to input filename)
- `--start-from`: Start from this index (useful for resuming)
- `--limit`: Maximum number of contacts to process (None for all)
- `--delay`: Delay in seconds between searches (default: 2.0)

## How It Works

1. **Identifies Missing Emails**: Scans all contacts and finds those without email addresses
2. **Broad Search Strategy**: Searches multiple sources:
   - Company websites and staff pages
   - Event/conference pages where contacts are mentioned
   - Professional directories
   - News articles and press releases
3. **Extracts All Company Emails**: From search results, extracts ALL emails matching the company domain
4. **Discovers New Contacts**: When finding emails, also extracts associated names to discover new contacts:
   - Example: Searching for "John Smith at ABC Housing" finds "Michael Jones (michael@abchousing.org)" → adds Michael Jones to database
5. **Domain Verification**: Only includes contacts with emails matching company domain:
   - `@abchousing.org` ✓
   - `@abchousing.com` ✓
   - `@gmail.com` ✗ (filtered out)
6. **Duplicate Prevention**: Checks if discovered contacts already exist in database before adding
7. **Updates JSON**: 
   - Adds found emails to existing contacts
   - Adds newly discovered contacts to the database
   - Includes metadata: source, discovery date, search context

## Output

The script creates an enriched JSON file with:
- All original contact data (with found emails added)
- **Newly discovered contacts** added to the contacts list
- Enrichment metadata and history
- Search attempt records for contacts where email wasn't found
- `discovered_contacts` section listing all new contacts found

### New Contact Format
Newly discovered contacts include:
- `First Name`, `Last Name`, `Email`
- `Associated Company`: Company name
- `Email_Source`: "Discovered_via_Search"
- `Discovered_Date`: When the contact was found
- `Discovered_While_Searching_For`: Original contact being searched
- `Source_URL`: URL where contact was found (if available)

## Logging

The script creates `email_search.log` with detailed information about:
- Contacts processed
- Emails found
- Search queries used
- Errors encountered

## Example Output

```
Found 2,192 contacts without email addresses

Sample of contacts without emails:
  1. John Smith - ABC Corporation
  2. Jane Doe - XYZ Inc
  ... and 2,187 more

Processing 2,192 contacts...
[1/2192] Searching for: John Smith at ABC Corporation
  ✓ Found: john.smith@abccorp.com
[2/2192] Searching for: Jane Doe at XYZ Inc
  ✗ Not found
...

EMAIL SEARCH & CONTACT DISCOVERY SUMMARY
================================================================================
Total contacts searched: 252
Emails found: 50
Emails not found: 202
New contacts discovered: 15
Errors: 0
Success rate: 19.8%
Total contacts in database now: 108,418
```

### Example: Contact Discovery
When searching for "John Smith at ABC Housing":
- Finds: `john.smith@abchousing.org` ✓ (target contact)
- Also finds: `michael.jones@abchousing.org` with name "Michael Jones" → **Added to database**
- Also finds: `sarah.williams@abchousing.org` with name "Sarah Williams" → **Added to database**
- Filters out: `john.smith@gmail.com` (doesn't match company domain)

## Tips

1. **Start Small**: Test with `--limit 10` first to verify it works
2. **Resume Capability**: Use `--start-from` to resume if the script stops
3. **Rate Limiting**: Increase `--delay` if you encounter rate limiting
4. **Check Logs**: Review `email_search.log` for detailed information
5. **Backup First**: The script creates a new file, but always backup your original data

## Notes

- The script respects rate limits with delays between searches
- Search results are parsed to find email addresses
- Found emails are validated against the contact name and company
- The original JSON file is not modified; a new enriched file is created

