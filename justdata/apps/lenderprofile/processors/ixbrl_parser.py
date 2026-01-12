#!/usr/bin/env python3
"""
iXBRL Parser for SEC DEF 14A (Proxy Statement) filings.
Extracts executive compensation data from inline XBRL format.
"""

import requests
import logging
import re
from typing import Optional, Dict, Any, List
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class IXBRLParser:
    """
    Parser for iXBRL (inline XBRL) documents.
    Primarily used for DEF 14A proxy statements with ECD taxonomy.
    """

    def __init__(self):
        self.user_agent = 'NCRC Lender Intelligence Platform contact@ncrc.org'
        self.timeout = 120

    def _get_headers(self) -> Dict[str, str]:
        return {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml'
        }

    def _extract_peo_identifier(self, context_ref: str) -> List[str]:
        """
        Extract PEO identifier(s) from iXBRL contextRef.

        Args:
            context_ref: The contextRef attribute value

        Returns:
            List of identifiers found (e.g., ['Carmichael', 'Spence'])
        """
        identifiers = []
        # Common patterns in contextRef for PEO identification
        # e.g., "P01_01_2024To12_31_2024_GregDCarmichaelMemberecdIndividualAxis"

        # Extract name pattern before "Member"
        name_match = re.search(r'_([A-Z][a-z]+[A-Z][A-Za-z]+)Member', context_ref)
        if name_match:
            # Extract last name from camelCase (e.g., "GregDCarmichael" -> "Carmichael")
            full_name = name_match.group(1)
            # Find the last uppercase letter sequence that starts the last name
            parts = re.findall(r'[A-Z][a-z]+', full_name)
            if parts:
                last_name = parts[-1]
                identifiers.append(last_name)

        return identifiers

    def _resolve_short_name_to_full(self, first_name: str, html_content: str) -> Optional[str]:
        """
        Resolve a short first name to a full name by searching the HTML content.

        Some companies store only first names in ecd:PeoName tags. This method
        searches the document for patterns like "FirstName LastName" to find
        the complete name.

        Args:
            first_name: The first name to search for (e.g., "Jay")
            html_content: The full HTML content of the DEF 14A

        Returns:
            Full name if found (e.g., "Jay Farner"), or None
        """
        if not first_name or len(first_name.split()) > 1:
            # Already a full name
            return None

        # Search for patterns: FirstName LastName (with capital letters)
        # Pattern matches "Jay Farner", "Bill Emerson", etc.
        pattern = rf'\b{re.escape(first_name)}\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b'
        matches = re.findall(pattern, html_content)

        if matches:
            # Get the most common match (to filter out false positives like "Jay was")
            # Only consider matches where the second word is a proper name (not common words)
            common_words = {'was', 'is', 'has', 'had', 'were', 'are', 'will', 'can', 'may',
                          'should', 'would', 'could', 'joined', 'served', 'became', 'also',
                          'and', 'the', 'for', 'with', 'from', 'that', 'this', 'which'}

            valid_matches = [m for m in matches if m.split()[0].lower() not in common_words]

            if valid_matches:
                # Count occurrences to find the most likely correct name
                from collections import Counter
                name_counts = Counter(valid_matches)
                most_common = name_counts.most_common(1)[0][0]
                full_name = f"{first_name} {most_common}"
                logger.debug(f"Resolved short name '{first_name}' to '{full_name}'")
                return full_name

        return None

    def _extract_summary_compensation_table(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extract executive compensation from Summary Compensation Table in HTML.
        Handles complex SEC table formats with many cells per row.

        Args:
            soup: BeautifulSoup object of the document

        Returns:
            List of executive compensation dictionaries
        """
        executives = []

        # Find tables that might be the Summary Compensation Table
        tables = soup.find_all('table')

        for table in tables:
            # Check if this looks like a Summary Compensation Table
            table_text = table.get_text().lower()

            # Look for tables with salary data - check for actual compensation keywords
            has_salary = 'salary' in table_text
            has_compensation_context = (
                'name and principal' in table_text or
                'chairman' in table_text or
                'chief executive' in table_text or
                'ceo' in table_text
            )

            # Skip tables that don't have salary data with executive context
            if not has_salary or not has_compensation_context:
                continue

            rows = table.find_all('tr')

            # For complex tables, extract all text values from each row
            for row in rows:
                cells = row.find_all(['th', 'td'])
                if len(cells) < 3:  # Reduced from 5 - some tables have fewer columns
                    continue

                # Get all cell text values
                cell_texts = [c.get_text().strip() for c in cells]
                row_text = ' '.join(cell_texts).lower()

                # Skip header rows
                if 'name' in row_text and 'principal' in row_text and 'position' in row_text:
                    continue
                if 'salary' in row_text and 'bonus' in row_text and 'stock' in row_text:
                    continue

                # Look for executive name pattern in first non-empty cell
                first_cell = cell_texts[0] if cell_texts else ''
                if not first_cell:
                    continue

                # Enhanced pattern to handle names concatenated with titles
                # Pattern 1: "FirstName MiddleName LastNameTitle" (no space before title)
                # Pattern 2: "FirstName LastName" followed by title text
                # Common exec names have 2-3 name parts before the title

                # Try to match: FirstName [Middle] LastName followed by Title (with or without space)
                # Example: "James DimonChairman and CEO" or "Mary Callahan ErdoesCEO"
                name_match = re.match(
                    r'^([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)?(?:\s+[A-Z][a-z]+)?)'
                    r'(?=[A-Z][a-z]*(?:Chairman|CEO|CFO|COO|President|Chief|Officer|Executive|Director|Managing))',
                    first_cell
                )

                if not name_match:
                    # Fallback: standard name patterns with space before title
                    name_match = re.match(r'^([A-Z][a-z]+\s+(?:[A-Z]\.?\s+)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', first_cell)

                if not name_match:
                    # Last fallback: just FirstName LastName
                    name_match = re.match(r'^([A-Z][a-z]+\s+[A-Z][a-z]+)', first_cell)

                if name_match:
                    exec_name = name_match.group(1).strip()

                    # Extract title from the rest of first cell
                    title_part = first_cell[len(exec_name):].strip()
                    title_part = re.sub(r'^[,\s]+', '', title_part)
                    exec_title = title_part if title_part else ''

                    # Find year (usually 2024, 2023, 2022, 2025)
                    year_val = None
                    for ct in cell_texts:
                        year_match = re.search(r'\b(202[2345])\b', ct)
                        if year_match:
                            year_val = year_match.group(1)
                            break

                    # Skip if not recent year
                    if year_val and year_val not in ['2025', '2024', '2023']:
                        continue

                    # Extract numeric values - look for dollar amounts
                    numeric_values = []
                    for ct in cell_texts:
                        # Clean and extract numbers
                        ct_clean = re.sub(r'[,$\s\xa0]', '', ct)
                        if ct_clean.isdigit() and len(ct_clean) >= 5:
                            numeric_values.append(int(ct_clean))

                    # Parse compensation values
                    salary = 0
                    total = 0

                    if numeric_values:
                        # Total is usually the largest value
                        total = max(numeric_values)
                        # Salary is usually first significant value (500K-3M range)
                        for val in numeric_values:
                            if 500000 <= val <= 3000000 and val != total:
                                salary = val
                                break

                    # Only add if we have meaningful data (lower threshold for salary-only rows)
                    if total > 100000 or salary > 100000:
                        # Use total if available, otherwise use salary
                        final_total = total if total > 0 else salary

                        existing = next((e for e in executives
                                        if exec_name in e['name'] or e['name'] in exec_name), None)

                        if not existing:
                            executives.append({
                                'name': exec_name,
                                'title': exec_title,
                                'salary': salary,
                                'bonus': 0,
                                'stock_awards': 0,
                                'option_awards': 0,
                                'total': total,
                                'year': year_val,
                                'is_current': True
                            })
                        elif year_val == '2024' and existing.get('year') != '2024':
                            executives.remove(existing)
                            executives.append({
                                'name': exec_name,
                                'title': exec_title,
                                'salary': salary,
                                'bonus': 0,
                                'stock_awards': 0,
                                'option_awards': 0,
                                'total': total,
                                'year': year_val,
                                'is_current': True
                            })

            if executives:
                break

        return executives

    def fetch_and_parse_def14a(self, doc_url: str) -> Dict[str, Any]:
        """
        Fetch and parse a DEF 14A document in iXBRL format.

        Args:
            doc_url: Direct URL to the DEF 14A HTML document

        Returns:
            Dictionary with executive compensation data
        """
        try:
            response = requests.get(doc_url, headers=self._get_headers(), timeout=self.timeout)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch DEF 14A: {response.status_code}")
                return {'available': False}

            return self.parse_ixbrl(response.text)

        except Exception as e:
            logger.error(f"Error fetching DEF 14A from {doc_url}: {e}")
            return {'available': False}

    def parse_ixbrl(self, html_content: str) -> Dict[str, Any]:
        """
        Parse iXBRL content to extract executive compensation data.

        Args:
            html_content: Raw HTML/iXBRL content

        Returns:
            Dictionary with structured compensation data
        """
        result = {
            'available': True,
            'peo_names': [],  # Principal Executive Officers
            'peo_compensation': [],  # PEO compensation amounts
            'neo_avg_compensation': [],  # Non-PEO NEO average compensation
            'executive_compensation': [],  # Formatted for display
            'board_composition': [],
            'ceo_transition': None  # CEO transition info
        }

        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Find all iXBRL elements
            ix_elements = soup.find_all(['ix:nonnumeric', 'ix:nonfraction'])

            # First pass: collect all PEO names and compensation by context
            # Some companies use simple context IDs (c-1, c-2), others use name-based contexts
            peo_names_by_ctx = {}  # {context: name}
            peo_comp_by_ctx = {}   # {context: compensation amount}

            for el in ix_elements:
                name = el.get('name', '')
                ctx = el.get('contextref', '')

                if name == 'ecd:PeoName':
                    peo_name = el.get_text().strip()
                    peo_names_by_ctx[ctx] = peo_name
                    logger.debug(f"Found PEO name: {peo_name} in context {ctx}")

                if name == 'ecd:PeoTotalCompAmt':
                    try:
                        value = float(el.get_text().strip().replace(',', '').replace('$', ''))
                        peo_comp_by_ctx[ctx] = value
                        logger.debug(f"Found PEO comp: ${value:,.0f} in context {ctx}")
                    except (ValueError, AttributeError):
                        pass

            # Match names and compensation by context
            peo_data = {}  # {name: {'name': str, 'compensation': [], 'contexts': []}}

            # For each name, find matching compensation
            for ctx, peo_name in peo_names_by_ctx.items():
                if peo_name not in peo_data:
                    peo_data[peo_name] = {'name': peo_name, 'compensation': [], 'contexts': []}
                peo_data[peo_name]['contexts'].append(ctx)

                # Check if this context has compensation
                if ctx in peo_comp_by_ctx:
                    peo_data[peo_name]['compensation'].append(peo_comp_by_ctx[ctx])

            # Log what we found
            logger.info(f"Found {len(peo_data)} unique PEO(s): {list(peo_data.keys())}")

            # Resolve short names (first name only) to full names
            # Some companies store only first names in ecd:PeoName tags
            resolved_peo_data = {}
            for peo_name, data in peo_data.items():
                # Check if this is a short name (single word, no spaces)
                if ' ' not in peo_name and len(peo_name) < 15:
                    full_name = self._resolve_short_name_to_full(peo_name, html_content)
                    if full_name:
                        logger.info(f"Resolved PEO name '{peo_name}' to '{full_name}'")
                        resolved_peo_data[full_name] = data
                        resolved_peo_data[full_name]['name'] = full_name
                    else:
                        resolved_peo_data[peo_name] = data
                else:
                    resolved_peo_data[peo_name] = data

            peo_data = resolved_peo_data

            # Build executive compensation list from PEO data
            # Sort by highest compensation (most recent year typically has highest)
            executives = []
            peo_names = list(peo_data.keys())

            for peo_name, data in peo_data.items():
                compensation = data.get('compensation', [])
                # Use the most recent (highest) compensation amount
                latest_comp = max(compensation) if compensation else 0

                executives.append({
                    'name': peo_name,
                    'title': 'Chief Executive Officer',  # PEO = Principal Executive Officer
                    'salary': 0,
                    'bonus': 0,
                    'stock_awards': 0,
                    'option_awards': 0,
                    'total': latest_comp,
                    'is_current': True
                })

            # Sort by compensation (highest first)
            executives.sort(key=lambda x: x.get('total', 0), reverse=True)

            # If we have multiple PEOs, the first is likely current CEO
            if len(executives) > 1:
                executives[0]['title'] = 'Chief Executive Officer'
                for i, exec in enumerate(executives[1:], 1):
                    exec['title'] = 'Executive Officer'  # Other named executives

            result['peo_names'] = peo_names

            # Extract PEO compensation amounts (for backward compatibility)
            peo_comps = []
            for el in ix_elements:
                name = el.get('name', '')
                if name == 'ecd:PeoTotalCompAmt':
                    try:
                        value = el.get_text().strip().replace(',', '').replace('$', '')
                        if value:
                            peo_comps.append(float(value))
                    except (ValueError, AttributeError):
                        pass

            result['peo_compensation'] = peo_comps

            # Extract Non-PEO NEO average compensation
            neo_comps = []
            for el in ix_elements:
                name = el.get('name', '')
                if name == 'ecd:NonPeoNeoAvgTotalCompAmt':
                    try:
                        value = el.get_text().strip().replace(',', '').replace('$', '')
                        if value:
                            neo_comps.append(float(value))
                    except (ValueError, AttributeError):
                        pass

            result['neo_avg_compensation'] = neo_comps

            # If we have NEO average comp, add a placeholder entry
            if neo_comps and neo_comps[0] > 0:
                result['neo_avg_total'] = neo_comps[0]

            # Try to extract Summary Compensation Table for all NEOs (CFO, etc.)
            table_executives = self._extract_summary_compensation_table(soup)
            if table_executives:
                logger.info(f"Found {len(table_executives)} executives in Summary Compensation Table")
                # Merge table data with PEO data - table data has more detail
                for tex in table_executives:
                    # Check if this executive is already in our list
                    existing = next((e for e in executives if tex['name'] in e['name'] or e['name'] in tex['name']), None)
                    if existing:
                        # Update with table data if it has more info
                        if tex['salary'] > 0:
                            existing['salary'] = tex['salary']
                        if tex['bonus'] > 0:
                            existing['bonus'] = tex['bonus']
                        if tex['stock_awards'] > 0:
                            existing['stock_awards'] = tex['stock_awards']
                        if tex['option_awards'] > 0:
                            existing['option_awards'] = tex['option_awards']
                        if tex['title'] and not existing.get('title'):
                            existing['title'] = tex['title']
                    else:
                        # Add new executive from table
                        executives.append(tex)

            # Dedupe executives by name (case-insensitive)
            seen_names = set()
            deduped_executives = []
            for exec in executives:
                name_lower = exec.get('name', '').strip().lower()
                if name_lower and name_lower not in seen_names:
                    seen_names.add(name_lower)
                    deduped_executives.append(exec)

            result['executive_compensation'] = deduped_executives

            # Try to extract director names from ECD data
            directors = []
            for el in ix_elements:
                name = el.get('name', '')
                if 'IndependentDirector' in name or 'BoardMember' in name:
                    director_name = el.get_text().strip()
                    if director_name and len(director_name) < 50:
                        directors.append({
                            'name': director_name,
                            'independent': 'Independent' in name
                        })

            result['board_composition'] = directors

            logger.info(f"Parsed iXBRL: {len(peo_names)} PEO(s), {len(peo_comps)} compensation amounts")
            return result

        except Exception as e:
            logger.error(f"Error parsing iXBRL: {e}")
            return {'available': False}

    def get_def14a_doc_url(self, base_url: str, cik: int, accession: str) -> Optional[str]:
        """
        Get the direct document URL for a DEF 14A filing.

        Args:
            base_url: SEC base URL
            cik: Company CIK (integer)
            accession: Accession number

        Returns:
            Direct URL to the DEF 14A document or None
        """
        try:
            acc_clean = accession.replace('-', '')
            index_url = f"{base_url}/Archives/edgar/data/{cik}/{acc_clean}/{accession}-index.htm"

            response = requests.get(index_url, headers=self._get_headers(), timeout=30)
            if response.status_code != 200:
                logger.warning(f"DEF 14A index returned status {response.status_code}: {index_url}")
                return None

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find the main document link - usually in /ix?doc= format for iXBRL
            # or a direct .htm link. The document name varies (e.g., jpm-20250405.htm, proxy.htm)
            for link in soup.find_all('a'):
                href = link.get('href', '')

                # Skip non-document links
                if not '.htm' in href.lower():
                    continue
                # Skip index pages
                if 'index' in href.lower():
                    continue

                # Handle /ix?doc= format (iXBRL viewer)
                if '/ix?doc=' in href:
                    doc_path = href.split('/ix?doc=')[-1]
                    logger.info(f"Found DEF 14A document via iXBRL: {doc_path}")
                    return f"{base_url}{doc_path}"

                # Handle direct links starting with /Archives/
                if href.startswith('/Archives/'):
                    logger.info(f"Found DEF 14A document: {href}")
                    return f"{base_url}{href}"

                # Handle relative links
                if not href.startswith('/') and not href.startswith('http'):
                    full_url = f"{base_url}/Archives/edgar/data/{cik}/{acc_clean}/{href}"
                    logger.info(f"Found DEF 14A document (relative): {full_url}")
                    return full_url

            logger.warning(f"No DEF 14A document found in index: {index_url}")
            return None

        except Exception as e:
            logger.error(f"Error getting DEF 14A doc URL: {e}")
            return None
