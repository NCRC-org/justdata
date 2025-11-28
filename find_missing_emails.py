"""
Script to find missing email addresses for contacts using DuckDuckGo search.
Identifies contacts without emails and searches for: "[First Name] [Last Name] [Company Name]"
"""
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging
import pandas as pd

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('email_search.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False
    DDGS = None  # Type placeholder
    logger.warning("duckduckgo_search not installed. Install with: pip install duckduckgo-search")


def load_contacts(json_file: Path) -> Dict:
    """Load contacts from JSON file."""
    logger.info(f"Loading contacts from {json_file}")
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    logger.info(f"Loaded {data['total_contacts']:,} total contacts")
    return data


def identify_contacts_without_emails(contacts: List[Dict]) -> List[Dict]:
    """
    Identify contacts that lack email addresses.
    Skips contacts that already have valid email addresses.
    
    Returns list of contacts with missing emails, including their company info.
    """
    missing_email_contacts = []
    skipped_with_emails = 0
    
    for contact in contacts:
        email = contact.get('Email', '')
        
        # Handle different data types (string, float/NaN, None)
        if email is None or (isinstance(email, float) and pd.isna(email)):
            email = ''
        else:
            email = str(email).strip()
        
        # Check if email is missing or empty
        if not email or email.lower() in ['', 'nan', 'none', 'null']:
            missing_email_contacts.append(contact)
        else:
            # Contact already has an email - skip it
            skipped_with_emails += 1
    
    logger.info(f"Found {len(missing_email_contacts):,} contacts without email addresses")
    logger.info(f"Skipped {skipped_with_emails:,} contacts that already have emails")
    return missing_email_contacts


def extract_email_from_text(text: str) -> Optional[str]:
    """Extract email address from text using regex."""
    # Common email pattern
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    
    if emails:
        # Return the first valid email, prefer common domains
        for email in emails:
            email_lower = email.lower()
            # Filter out common non-personal email patterns
            if not any(skip in email_lower for skip in ['example.com', 'test.com', 'domain.com', 'email.com']):
                return email
        return emails[0] if emails else None
    return None


def extract_all_emails_from_text(text: str) -> List[str]:
    """Extract all email addresses from text using regex."""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    
    # Filter out invalid emails
    valid_emails = []
    for email in emails:
        email_lower = email.lower()
        # Filter out common non-personal email patterns
        if not any(skip in email_lower for skip in ['example.com', 'test.com', 'domain.com', 'email.com', 'noreply', 'no-reply']):
            valid_emails.append(email)
    
    return valid_emails


def extract_name_email_pairs(text: str) -> List[Dict[str, str]]:
    """
    Extract name-email pairs from text.
    Looks for patterns like "Name <email@domain.com>" or "Name (email@domain.com)" or "Name email@domain.com"
    """
    pairs = []
    
    # Pattern 1: Name <email@domain.com>
    pattern1 = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s*<([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})>'
    matches = re.findall(pattern1, text)
    for name, email in matches:
        pairs.append({'name': name.strip(), 'email': email.lower()})
    
    # Pattern 2: Name (email@domain.com)
    pattern2 = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s*\(([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\)'
    matches = re.findall(pattern2, text)
    for name, email in matches:
        pairs.append({'name': name.strip(), 'email': email.lower()})
    
    # Pattern 3: Name followed by email on same line
    pattern3 = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s+([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})'
    matches = re.findall(pattern3, text)
    for name, email in matches:
        # Verify it's not already captured
        if not any(p['email'] == email.lower() for p in pairs):
            pairs.append({'name': name.strip(), 'email': email.lower()})
    
    return pairs


def get_company_domain(company: str) -> Optional[str]:
    """
    Extract company domain from company name.
    Returns base domain (e.g., 'abchousing' from 'ABC Housing' or 'ABC Housing Inc')
    """
    if not company or str(company).lower() in ['nan', 'none', 'null', '']:
        return None
    
    # Remove common suffixes
    company_clean = str(company).strip()
    suffixes = ['inc', 'llc', 'corp', 'corporation', 'company', 'co', 'ltd', 'limited', 'the']
    
    words = company_clean.lower().split()
    # Remove 'the' if first word
    if words and words[0] == 'the':
        words = words[1:]
    
    # Remove common suffixes
    words = [w for w in words if w not in suffixes]
    
    if words:
        # Use first meaningful word as domain base
        return words[0]
    
    return None


def email_matches_company_domain(email: str, company: str) -> bool:
    """
    Check if email domain matches company domain.
    Matches @company.org, @company.com, @company.net, etc.
    """
    if not email or not company:
        return False
    
    company_domain = get_company_domain(company)
    if not company_domain:
        return False
    
    # Extract domain from email
    if '@' not in email:
        return False
    
    email_domain = email.split('@')[1].lower()
    
    # Check if domain starts with company domain
    # e.g., abchousing.org, abchousing.com, www.abchousing.org
    domain_base = email_domain.replace('www.', '').split('.')[0]
    
    return domain_base == company_domain.lower()


def is_name_unique(first_name: str, last_name: str, all_contacts: List[Dict]) -> bool:
    """
    Determine if a name is unique enough to search without company context.
    A name is considered unique if:
    1. The full name (first + last) appears only once in the database
    2. The last name is uncommon (appears < 3 times)
    3. The first name is uncommon (appears < 5 times)
    
    Args:
        first_name: First name
        last_name: Last name
        all_contacts: All contacts in database
    
    Returns:
        True if name is unique enough to search without company
    """
    if not first_name or not last_name:
        return False
    
    first_lower = first_name.lower().strip()
    last_lower = last_name.lower().strip()
    full_name = f"{first_lower} {last_lower}"
    
    # Count occurrences of this exact full name
    full_name_count = 0
    last_name_count = 0
    first_name_count = 0
    
    for contact in all_contacts:
        contact_first = str(contact.get('First Name', '')).lower().strip()
        contact_last = str(contact.get('Last Name', '')).lower().strip()
        
        if contact_first and contact_last:
            contact_full = f"{contact_first} {contact_last}"
            if contact_full == full_name:
                full_name_count += 1
            if contact_last == last_lower:
                last_name_count += 1
            if contact_first == first_lower:
                first_name_count += 1
    
    # Name is unique if:
    # - Full name appears only once (very unique)
    # - OR last name appears < 3 times AND first name appears < 5 times (relatively unique)
    is_unique = (
        full_name_count <= 1 or
        (last_name_count < 3 and first_name_count < 5)
    )
    
    return is_unique


def contact_exists(contact_list: List[Dict], first_name: str, last_name: str, email: str) -> bool:
    """
    Check if a contact already exists in the list.
    Matches by name or email.
    """
    first_lower = first_name.lower().strip() if first_name else ''
    last_lower = last_name.lower().strip() if last_name else ''
    email_lower = email.lower().strip() if email else ''
    
    for contact in contact_list:
        # Check by email
        contact_email = contact.get('Email', '')
        if contact_email:
            contact_email = str(contact_email).lower().strip()
            if contact_email == email_lower:
                return True
        
        # Check by name
        contact_first = str(contact.get('First Name', '')).lower().strip()
        contact_last = str(contact.get('Last Name', '')).lower().strip()
        
        if first_lower and last_lower:
            if contact_first == first_lower and contact_last == last_lower:
                return True
    
    return False


def generate_email_patterns(first_name: str, last_name: str, company: str) -> List[str]:
    """
    Generate common email format patterns based on name and company.
    
    Formats:
    - firstname.lastname@company.org
    - firstinitiallastname@company.org
    - lastname@company.org
    - firstnamelastinitial@company.org
    
    Returns list of potential email addresses to try.
    """
    patterns = []
    
    # Clean inputs
    first_name = first_name.strip().lower() if first_name else ''
    last_name = last_name.strip().lower() if last_name else ''
    company = company.strip().lower() if company else ''
    
    if not first_name and not last_name:
        return patterns
    
    # Extract company domain (remove common words, get first meaningful word)
    if company:
        # Remove common words
        company_words = [w for w in company.split() if w.lower() not in ['the', 'of', 'and', 'inc', 'llc', 'corp', 'corporation', 'company', 'co']]
        if company_words:
            company_domain = company_words[0]
        else:
            # Fallback: use first word
            company_domain = company.split()[0] if company.split() else ''
        
        # Common domain extensions to try
        domain_extensions = ['org', 'com', 'net', 'edu']
        
        for ext in domain_extensions:
            domain = f"{company_domain}.{ext}"
            
            # Pattern 1: firstname.lastname@company.org
            if first_name and last_name:
                patterns.append(f"{first_name}.{last_name}@{domain}")
            
            # Pattern 2: firstinitiallastname@company.org
            if first_name and last_name:
                first_initial = first_name[0] if first_name else ''
                patterns.append(f"{first_initial}{last_name}@{domain}")
            
            # Pattern 3: lastname@company.org
            if last_name:
                patterns.append(f"{last_name}@{domain}")
            
            # Pattern 4: firstnamelastinitial@company.org
            if first_name and last_name:
                last_initial = last_name[0] if last_name else ''
                patterns.append(f"{first_name}{last_initial}@{domain}")
            
            # Additional common patterns
            if first_name and last_name:
                # firstname_lastname
                patterns.append(f"{first_name}_{last_name}@{domain}")
                # firstnamelastname (no separator)
                patterns.append(f"{first_name}{last_name}@{domain}")
    
    return patterns


def search_for_unique_name_email(first_name: str, last_name: str, ddgs) -> Tuple[Optional[str], Optional[str]]:
    """
    Search for email for a unique name without company context.
    Uses more conservative search strategies.
    
    Args:
        first_name: First name
        last_name: Last name
        ddgs: DuckDuckGo search instance
    
    Returns:
        Tuple of (found_email, source_url) or (None, None)
    """
    if not ddgs:
        return None, None
    
    name = f"{first_name} {last_name}".strip()
    if not name:
        return None, None
    
    # Conservative queries for unique names
    queries = [
        f'"{name}" email contact',
        f'"{name}" professional email',
        f'{name} email address'
    ]
    
    for query in queries:
        try:
            logger.debug(f"Searching unique name: {query}")
            results = list(ddgs.text(query, max_results=3))
            
            for result in results:
                text = result.get('body', '') + ' ' + result.get('title', '')
                url = result.get('href', '')
                email = extract_email_from_text(text)
                
                if email:
                    # Verify email matches the name
                    if verify_email_format(email, first_name, last_name):
                        logger.info(f"Found email for unique name {name}: {email} (from: {url})")
                        return email, url if url else None
            
            time.sleep(1)
        except Exception as e:
            logger.warning(f"Error searching unique name '{query}': {e}")
            time.sleep(2)
            continue
    
    return None, None


def verify_email_format(email: str, first_name: str, last_name: str) -> bool:
    """
    Verify if an email address matches common patterns for the given name.
    """
    email_lower = email.lower()
    first_lower = first_name.lower() if first_name else ''
    last_lower = last_name.lower() if last_name else ''
    
    # Check if email contains name components
    if first_lower and last_lower:
        # Check for firstname.lastname or similar
        if (first_lower in email_lower and last_lower in email_lower) or \
           (first_lower[0] in email_lower and last_lower in email_lower) or \
           (first_lower in email_lower and last_lower[0] in email_lower):
            return True
    elif last_lower and last_lower in email_lower:
        return True
    
    return False


def search_for_email_and_discover_contacts(
    first_name: str, 
    last_name: str, 
    company: str, 
    ddgs,
    existing_contacts: List[Dict],
    has_company: bool = True
) -> Tuple[Optional[str], List[Dict]]:
    """
    Search broadly for email address and discover additional contacts at the company.
    Searches event pages, conference sites, company websites, etc.
    Only includes contacts with emails matching the company domain (if company provided).
    
    Args:
        first_name: Contact's first name
        last_name: Contact's last name
        company: Associated company name (can be empty for unique names)
        ddgs: DuckDuckGo search instance
        existing_contacts: List of existing contacts to check against
        has_company: Whether company name is available (affects discovery logic)
    
    Returns:
        Tuple of (found_email_for_target, source_url, list_of_new_contacts_discovered)
    """
    # Build search query
    name = f"{first_name} {last_name}".strip()
    if not name or name == ' ':
        return None, []
    
    # Clean company name
    company_clean = company.strip() if company and str(company).lower() not in ['nan', 'none', 'null', ''] else None
    
    if not company_clean and not has_company:
        # For unique names without company, search more broadly but don't discover new contacts
        # (can't verify company domain)
        unique_email, unique_source_url = search_for_unique_name_email(first_name, last_name, ddgs)
        return unique_email, unique_source_url, []  # Return email, source_url, discovered_contacts
    
    # Step 1: Search DuckDuckGo broadly
    if not ddgs:
        logger.warning("DuckDuckGo search not available")
        return None, []
    
    # Build broad search queries (not limited to company website)
    queries = []
    
    # Search for the person at the company (broad search)
    queries.append(f'"{name}" "{company_clean}"')
    queries.append(f'{name} {company_clean} contact')
    queries.append(f'"{name}" "{company_clean}" email')
    queries.append(f'{name} {company_clean} staff team')
    
    # Search for company staff/team pages
    queries.append(f'"{company_clean}" staff team email')
    queries.append(f'"{company_clean}" contact directory')
    
    # Search for event/conference mentions
    queries.append(f'"{name}" "{company_clean}" speaker event')
    queries.append(f'"{name}" "{company_clean}" conference')
    
    target_email = None
    target_email_source_url = None
    discovered_contacts = []
    all_company_emails = set()  # Track all emails we've seen
    
    # Search and extract emails
    for query in queries:
        try:
            logger.debug(f"Searching broadly: {query}")
            results = list(ddgs.text(query, max_results=10))  # Get more results for discovery
            
            # Process each result
            for result in results:
                text = result.get('body', '') + ' ' + result.get('title', '') + ' ' + result.get('href', '')
                url = result.get('href', '')
                
                # Extract all emails from this result
                all_emails = extract_all_emails_from_text(text)
                
                # Filter emails by company domain
                company_emails = [
                    email for email in all_emails 
                    if email_matches_company_domain(email, company_clean)
                ]
                
                # Extract name-email pairs
                name_email_pairs = extract_name_email_pairs(text)
                
                # Process each company email
                for email in company_emails:
                    if email.lower() in all_company_emails:
                        continue  # Already processed
                    
                    all_company_emails.add(email.lower())
                    
                    # Check if this is the target person's email
                    if verify_email_format(email, first_name, last_name):
                        if not target_email:
                            target_email = email
                            target_email_source_url = url if url else None
                            logger.info(f"Found target email for {name}: {email} (from: {url})")
                    
                    # Try to find name associated with this email
                    associated_name = None
                    for pair in name_email_pairs:
                        if pair['email'].lower() == email.lower():
                            associated_name = pair['name']
                            break
                    
                    # If no name found, try to extract from context around email
                    if not associated_name:
                        # Look for name patterns near the email in text
                        email_index = text.lower().find(email.lower())
                        if email_index > 0:
                            # Look backwards for name patterns
                            context = text[max(0, email_index-100):email_index+100]
                            name_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)'
                            name_matches = re.findall(name_pattern, context)
                            if name_matches:
                                # Use the name closest to the email
                                associated_name = name_matches[-1] if name_matches else None
                    
                    # If we have a name, create a contact
                    if associated_name:
                        name_parts = associated_name.split()
                        if len(name_parts) >= 2:
                            new_first = name_parts[0]
                            new_last = ' '.join(name_parts[1:])
                            
                            # Check if this contact already exists
                            if not contact_exists(existing_contacts, new_first, new_last, email):
                                # Check if we already discovered this contact in this search
                                if not any(
                                    c.get('Email', '').lower() == email.lower() 
                                    for c in discovered_contacts
                                ):
                                    new_contact = {
                                        'First Name': new_first,
                                        'Last Name': new_last,
                                        'Email': email,
                                        'Associated Company': company_clean,
                                        'Email_Source': 'Discovered_via_Search',
                                        'Discovered_Date': datetime.now().isoformat(),
                                        'Discovered_While_Searching_For': name,
                                        'Source_URL': url if url else None
                                    }
                                    discovered_contacts.append(new_contact)
                                    logger.info(f"  Discovered new contact: {new_first} {new_last} ({email})")
                    elif email and not target_email:
                        # If no name but email matches target, it might be the target
                        if verify_email_format(email, first_name, last_name):
                            target_email = email
                            target_email_source_url = url if url else None
            
            # Small delay between searches
            time.sleep(1)
            
        except Exception as e:
            logger.warning(f"Error searching with query '{query}': {e}")
            time.sleep(2)  # Longer delay on error
            continue
    
    # Remove duplicates from discovered contacts
    unique_contacts = []
    seen_emails = set()
    for contact in discovered_contacts:
        email = contact.get('Email', '').lower()
        if email and email not in seen_emails:
            seen_emails.add(email)
            unique_contacts.append(contact)
    
    logger.info(f"Discovered {len(unique_contacts)} new contacts at {company_clean}")
    
    return target_email, target_email_source_url, unique_contacts


def enrich_contacts_with_emails(
    contacts_data: Dict,
    output_file: Path,
    start_from: int = 0,
    limit: Optional[int] = None,
    delay_between_searches: float = 2.0
) -> Dict:
    """
    Enrich contacts by searching for missing email addresses.
    
    Args:
        contacts_data: Original contacts data dictionary
        output_file: Path to save enriched data
        start_from: Start from this index (for resuming)
        limit: Maximum number of contacts to process (None for all)
        delay_between_searches: Delay in seconds between searches
    
    Returns:
        Enriched contacts data
    """
    if not DDGS_AVAILABLE:
        logger.error("duckduckgo_search library not available. Install with: pip install duckduckgo-search")
        return contacts_data
    
    # Identify contacts without emails
    all_contacts = contacts_data['contacts']
    missing_email_contacts = identify_contacts_without_emails(all_contacts)
    
    if not missing_email_contacts:
        logger.info("All contacts have email addresses!")
        return contacts_data
    
    # Determine which contacts to process
    total_to_process = len(missing_email_contacts)
    if limit:
        end_idx = min(start_from + limit, total_to_process)
    else:
        end_idx = total_to_process
    
    contacts_to_process = missing_email_contacts[start_from:end_idx]
    logger.info(f"Processing {len(contacts_to_process)} contacts (indices {start_from} to {end_idx-1} of {total_to_process})")
    
    # Create a mapping of Record ID to contact for quick lookup
    contact_map = {str(contact.get('Record ID', '')): contact for contact in all_contacts}
    
    # Initialize DuckDuckGo search
    ddgs = DDGS()
    
    # Statistics
    stats = {
        'total_searched': 0,
        'emails_found': 0,
        'emails_not_found': 0,
        'new_contacts_discovered': 0,
        'errors': 0
    }
    
    # Collect all newly discovered contacts
    all_discovered_contacts = []
    
    # Process each contact
    enriched_count = 0
    
    for idx, contact in enumerate(contacts_to_process, start=start_from):
        record_id = str(contact.get('Record ID', ''))
        first_name = contact.get('First Name', '')
        first_name = first_name.strip() if first_name and not (isinstance(first_name, float) and pd.isna(first_name)) else ''
        
        last_name = contact.get('Last Name', '')
        last_name = last_name.strip() if last_name and not (isinstance(last_name, float) and pd.isna(last_name)) else ''
        
        company = contact.get('Associated Company', '')
        if company is None or (isinstance(company, float) and pd.isna(company)):
            company = ''
        else:
            company = str(company).strip()
        
        if not first_name and not last_name:
            logger.warning(f"[{idx+1}/{len(contacts_to_process)}] Skipping contact {record_id} (no name)")
            continue
        
        # Skip contacts without company names unless name is very unique
        has_company = bool(company and company.lower() not in ['nan', 'none', 'null', ''])
        
        if not has_company:
            if is_name_unique(first_name, last_name, all_contacts):
                logger.info(f"[{idx+1}/{len(contacts_to_process)}] Searching for: {first_name} {last_name} (unique name, no company)")
            else:
                logger.info(f"[{idx+1}/{len(contacts_to_process)}] Skipping: {first_name} {last_name} (no company name, name not unique enough)")
                stats['total_searched'] += 1
                stats['emails_not_found'] += 1
                contact_map[record_id]['Email_Search_Status'] = 'Skipped_No_Company_Not_Unique'
                continue
        
        logger.info(f"[{idx+1}/{len(contacts_to_process)}] Searching for: {first_name} {last_name} at {company or 'N/A'}")
        
        try:
            # Search for email AND discover new contacts
            found_email, source_url, discovered_contacts = search_for_email_and_discover_contacts(
                first_name, last_name, company, ddgs, all_contacts, has_company=has_company
            )
            
            if found_email:
                # Update the contact in the original data
                contact_map[record_id]['Email'] = found_email
                contact_map[record_id]['Email_Source'] = 'DuckDuckGo_Search'
                contact_map[record_id]['Email_Found_Date'] = datetime.now().isoformat()
                # Store the source URL where the email was found
                if source_url:
                    contact_map[record_id]['Source_URL'] = source_url
                    contact_map[record_id]['Email_Source_URL'] = source_url
                stats['emails_found'] += 1
                enriched_count += 1
                logger.info(f"  [FOUND] {found_email} (from: {source_url or 'URL not available'})")
            else:
                contact_map[record_id]['Email_Search_Attempted'] = datetime.now().isoformat()
                contact_map[record_id]['Email_Search_Status'] = 'Not_Found'
                stats['emails_not_found'] += 1
                logger.info(f"  [NOT FOUND]")
            
            # Add discovered contacts (check for duplicates)
            for new_contact in discovered_contacts:
                new_email = new_contact.get('Email', '').lower()
                # Check if already in discovered list
                if not any(c.get('Email', '').lower() == new_email for c in all_discovered_contacts):
                    # Check if already exists in original contacts
                    if not contact_exists(all_contacts, 
                                        new_contact.get('First Name', ''),
                                        new_contact.get('Last Name', ''),
                                        new_contact.get('Email', '')):
                        all_discovered_contacts.append(new_contact)
                        stats['new_contacts_discovered'] += 1
            
            stats['total_searched'] += 1
            
        except Exception as e:
            logger.error(f"  Error processing contact {record_id}: {e}")
            stats['errors'] += 1
            contact_map[record_id]['Email_Search_Error'] = str(e)
        
        # Delay between searches to avoid rate limiting
        if idx < len(contacts_to_process) - 1:  # Don't delay after last contact
            time.sleep(delay_between_searches)
    
    # Update contacts list
    contacts_data['contacts'] = list(contact_map.values())
    
    # Add discovered contacts to the contacts list
    if all_discovered_contacts:
        logger.info(f"\nAdding {len(all_discovered_contacts)} newly discovered contacts to database...")
        # Generate Record IDs for new contacts (use negative numbers to distinguish)
        next_id = -1
        for new_contact in all_discovered_contacts:
            new_contact['Record ID'] = str(next_id)
            new_contact['Create Date'] = datetime.now().isoformat()
            contacts_data['contacts'].append(new_contact)
            next_id -= 1
        
        # Update total count
        contacts_data['total_contacts'] = len(contacts_data['contacts'])
    
    # Add enrichment metadata
    if 'enrichment_history' not in contacts_data:
        contacts_data['enrichment_history'] = []
    
    contacts_data['enrichment_history'].append({
        'date': datetime.now().isoformat(),
        'emails_found': stats['emails_found'],
        'contacts_searched': stats['total_searched'],
        'new_contacts_discovered': stats['new_contacts_discovered'],
        'start_index': start_from,
        'end_index': end_idx
    })
    
    # Add discovered contacts section
    if all_discovered_contacts:
        contacts_data['discovered_contacts'] = all_discovered_contacts
    
    # Save enriched data
    logger.info(f"Saving enriched data to {output_file}...")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(contacts_data, f, indent=2, ensure_ascii=False, default=str)
    
    # Print summary
    logger.info("=" * 80)
    logger.info("EMAIL SEARCH & CONTACT DISCOVERY SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total contacts searched: {stats['total_searched']}")
    logger.info(f"Emails found: {stats['emails_found']}")
    logger.info(f"Emails not found: {stats['emails_not_found']}")
    logger.info(f"New contacts discovered: {stats['new_contacts_discovered']}")
    logger.info(f"Errors: {stats['errors']}")
    logger.info(f"Success rate: {(stats['emails_found']/stats['total_searched']*100):.1f}%" if stats['total_searched'] > 0 else "N/A")
    logger.info(f"Total contacts in database now: {len(contacts_data['contacts']):,}")
    logger.info(f"Enriched data saved to: {output_file}")
    logger.info("=" * 80)
    
    return contacts_data


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Find missing email addresses using DuckDuckGo search"
    )
    parser.add_argument(
        "--input",
        type=str,
        default=r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\DREAM Analysis\#Cursor Agent Backups\all_contacts.json",
        help="Input JSON file with contacts"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSON file (default: adds '_enriched' to input filename)"
    )
    parser.add_argument(
        "--start-from",
        type=int,
        default=0,
        help="Start from this index (for resuming)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of contacts to process (None for all)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay in seconds between searches (default: 2.0)"
    )
    
    args = parser.parse_args()
    
    # Setup paths
    input_file = Path(args.input)
    if not input_file.exists():
        logger.error(f"Input file not found: {input_file}")
        return
    
    if args.output:
        output_file = Path(args.output)
    else:
        # Add _enriched before .json
        output_file = input_file.parent / f"{input_file.stem}_enriched{input_file.suffix}"
    
    # Load contacts
    contacts_data = load_contacts(input_file)
    
    # First, identify contacts without emails
    missing_emails = identify_contacts_without_emails(contacts_data['contacts'])
    logger.info(f"\nFound {len(missing_emails):,} contacts without email addresses")
    
    if not missing_emails:
        logger.info("All contacts already have email addresses!")
        return
    
    # Show sample of contacts without emails
    logger.info("\nSample of contacts without emails:")
    for i, contact in enumerate(missing_emails[:5], 1):
        name = f"{contact.get('First Name', '')} {contact.get('Last Name', '')}".strip()
        company = contact.get('Associated Company', 'N/A')
        logger.info(f"  {i}. {name} - {company}")
    
    if len(missing_emails) > 5:
        logger.info(f"  ... and {len(missing_emails) - 5} more")
    
    # Confirm before proceeding
    logger.info(f"\nReady to search for emails for {len(missing_emails)} contacts")
    logger.info(f"Output will be saved to: {output_file}")
    
    # Enrich contacts
    enrich_contacts_with_emails(
        contacts_data=contacts_data,
        output_file=output_file,
        start_from=args.start_from,
        limit=args.limit,
        delay_between_searches=args.delay
    )


if __name__ == "__main__":
    main()

