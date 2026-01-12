#!/usr/bin/env python3
"""
SEC Filing Parser - Code-Based Section Extraction
Extracts specific sections from 10-K and DEF 14A filings using regex/text markers.
NO AI calls - pure code-based parsing.
"""

import re
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class SECFilingParser:
    """Parse SEC filings to extract structured data."""
    
    @staticmethod
    def extract_section(text: str, start_marker: str, end_marker: str) -> Optional[str]:
        """
        Extract a section between two markers.
        
        Args:
            text: Full filing text
            start_marker: Start marker (e.g., 'ITEM 1')
            end_marker: End marker (e.g., 'ITEM 1A')
            
        Returns:
            Extracted section text or None
        """
        if not text:
            return None
        
        # Try exact match first
        pattern = rf'{re.escape(start_marker)}(.*?){re.escape(end_marker)}'
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        
        if match:
            return match.group(1).strip()
        
        # Try with variations (ITEM 1. vs ITEM 1, etc.)
        start_variations = [
            start_marker,
            start_marker.replace('ITEM', 'Item'),
            start_marker + '.',
            start_marker + ' ',
        ]
        
        end_variations = [
            end_marker,
            end_marker.replace('ITEM', 'Item'),
            end_marker + '.',
            end_marker + ' ',
        ]
        
        for start_var in start_variations:
            for end_var in end_variations:
                pattern = rf'{re.escape(start_var)}(.*?){re.escape(end_var)}'
                match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if match:
                    return match.group(1).strip()
        
        return None
    
    @staticmethod
    def parse_10k(filing_text: str) -> Dict[str, Any]:
        """
        Parse a 10-K filing to extract key sections.
        
        Args:
            filing_text: Full 10-K filing text
            
        Returns:
            Dictionary with extracted sections
        """
        if not filing_text:
            return {'available': False}
        
        result = {
            'available': True,
            'sections': {},
            'subsidiaries': [],
            'business_combinations': []
        }
        
        # Extract Item 1 (Business Description)
        item1 = SECFilingParser.extract_section(filing_text, 'ITEM 1', 'ITEM 1A')
        if item1:
            result['sections']['item1_business'] = item1[:50000]  # Limit size
        
        # Extract Item 1A (Risk Factors)
        item1a = SECFilingParser.extract_section(filing_text, 'ITEM 1A', 'ITEM 1B')
        if not item1a:
            item1a = SECFilingParser.extract_section(filing_text, 'ITEM 1A', 'ITEM 2')
        if item1a:
            result['sections']['item1a_risks'] = item1a[:50000]  # Limit size
        
        # Extract Item 7 (MD&A)
        item7 = SECFilingParser.extract_section(filing_text, 'ITEM 7', 'ITEM 7A')
        if not item7:
            item7 = SECFilingParser.extract_section(filing_text, 'ITEM 7', 'ITEM 8')
        if item7:
            result['sections']['item7_mda'] = item7[:50000]  # Limit size
        
        # Extract Exhibit 21 (Subsidiaries)
        exhibit21 = SECFilingParser.extract_exhibit21(filing_text)
        if exhibit21:
            result['subsidiaries'] = exhibit21
        
        # Extract Business Combinations note
        business_combinations = SECFilingParser.extract_business_combinations(filing_text)
        if business_combinations:
            result['business_combinations'] = business_combinations
        
        # Extract Community Investment / CRA data
        community_investment = SECFilingParser.extract_community_investment(filing_text)
        if community_investment:
            result['community_investment'] = community_investment

        # Extract filing metadata
        filing_date = SECFilingParser.extract_filing_date(filing_text)
        fiscal_year_end = SECFilingParser.extract_fiscal_year_end(filing_text)

        result['metadata'] = {
            'filing_date': filing_date,
            'fiscal_year_end': fiscal_year_end
        }

        return result
    
    @staticmethod
    def extract_exhibit21(text: str) -> List[Dict[str, Any]]:
        """
        Extract Exhibit 21 subsidiary list.
        
        Args:
            text: Filing text
            
        Returns:
            List of subsidiary dictionaries
        """
        # Find Exhibit 21 section
        exhibit21_section = SECFilingParser.extract_section(text, 'EXHIBIT 21', 'EXHIBIT 22')
        if not exhibit21_section:
            exhibit21_section = SECFilingParser.extract_section(text, 'Exhibit 21', 'Exhibit 22')
        
        if not exhibit21_section:
            return []
        
        subsidiaries = []
        lines = exhibit21_section.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 5:
                continue
            
            # Try to match: Name | State | Ownership %
            # Pattern: Company name, state code, percentage
            match = re.match(r'^(.+?)\s+([A-Z]{2})\s+(\d+(?:\.\d+)?%)', line)
            if match:
                subsidiaries.append({
                    'name': match.group(1).strip(),
                    'state': match.group(2),
                    'ownership': match.group(3)
                })
            else:
                # Try simpler pattern: Name, State
                match = re.match(r'^(.+?),\s*([A-Z]{2})', line)
                if match:
                    subsidiaries.append({
                        'name': match.group(1).strip(),
                        'state': match.group(2),
                        'ownership': None
                    })
        
        return subsidiaries
    
    @staticmethod
    def extract_business_combinations(text: str) -> List[Dict[str, Any]]:
        """
        Extract business combination/acquisition information from notes.
        
        Args:
            text: Filing text
            
        Returns:
            List of business combination records
        """
        # Look for "Business Combinations" or "Acquisitions" note
        note_section = SECFilingParser.extract_section(text, 'Business Combinations', 'Note')
        if not note_section:
            note_section = SECFilingParser.extract_section(text, 'Acquisitions', 'Note')
        
        if not note_section:
            return []
        
        # Extract acquisition details (simplified - would need more sophisticated parsing)
        acquisitions = []
        
        # Look for year patterns and company names
        year_pattern = r'(20\d{2})'
        company_pattern = r'([A-Z][a-zA-Z\s&,\.]+(?:Bank|Corporation|Inc|LLC|Ltd))'
        
        lines = note_section.split('\n')
        current_year = None
        
        for line in lines:
            # Extract year
            year_match = re.search(year_pattern, line)
            if year_match:
                current_year = year_match.group(1)
            
            # Extract company name
            company_match = re.search(company_pattern, line)
            if company_match and current_year:
                company_name = company_match.group(1).strip()
                acquisitions.append({
                    'year': current_year,
                    'target': company_name,
                    'details': line.strip()[:200]  # First 200 chars of line
                })
        
        return acquisitions
    
    @staticmethod
    def extract_community_investment(text: str) -> Dict[str, Any]:
        """
        Extract community investment, CRA, and philanthropy data from 10-K.

        Banks disclose CRA activities, community development loans/investments,
        charitable contributions, and foundation activities in their 10-K filings.

        Args:
            text: Filing text

        Returns:
            Dictionary with community investment data
        """
        result = {
            'cra_rating': None,
            'community_development': {
                'loans': None,
                'investments': None,
                'services': None
            },
            'charitable_contributions': None,
            'foundation': None,
            'commitments': [],
            'has_data': False
        }

        if not text:
            return result

        text_lower = text.lower()

        # Extract CRA Rating
        cra_patterns = [
            r'cra\s+rating[:\s]+["\']?(outstanding|satisfactory|needs to improve|substantial noncompliance)["\']?',
            r'community reinvestment act[^.]*rating[:\s]+["\']?(outstanding|satisfactory)["\']?',
            r'received\s+(?:a|an)\s+["\']?(outstanding|satisfactory)["\']?\s+(?:cra|community reinvestment)',
        ]
        for pattern in cra_patterns:
            match = re.search(pattern, text_lower)
            if match:
                result['cra_rating'] = match.group(1).capitalize()
                result['has_data'] = True
                break

        # Extract Community Development Loans amount
        cd_loan_patterns = [
            r'community\s+development\s+loans?[^$]*\$\s*([\d,.]+)\s*(million|billion|thousand)?',
            r'cd\s+loans?[^$]*\$\s*([\d,.]+)\s*(million|billion|thousand)?',
            r'\$\s*([\d,.]+)\s*(million|billion)?\s+(?:in\s+)?community\s+development\s+loans?',
        ]
        for pattern in cd_loan_patterns:
            match = re.search(pattern, text_lower)
            if match:
                amount = SECFilingParser._parse_currency_amount(match.group(1), match.group(2) if len(match.groups()) > 1 else None)
                if amount:
                    result['community_development']['loans'] = amount
                    result['has_data'] = True
                break

        # Extract Community Development Investments
        cd_invest_patterns = [
            r'community\s+development\s+investments?[^$]*\$\s*([\d,.]+)\s*(million|billion|thousand)?',
            r'qualified\s+investments?[^$]*\$\s*([\d,.]+)\s*(million|billion|thousand)?',
            r'\$\s*([\d,.]+)\s*(million|billion)?\s+(?:in\s+)?(?:cd|community\s+development)\s+investments?',
        ]
        for pattern in cd_invest_patterns:
            match = re.search(pattern, text_lower)
            if match:
                amount = SECFilingParser._parse_currency_amount(match.group(1), match.group(2) if len(match.groups()) > 1 else None)
                if amount:
                    result['community_development']['investments'] = amount
                    result['has_data'] = True
                break

        # Extract Charitable Contributions
        charity_patterns = [
            r'charitable\s+contributions?[^$]*\$\s*([\d,.]+)\s*(million|billion|thousand)?',
            r'philanthropic[^$]*\$\s*([\d,.]+)\s*(million|billion|thousand)?',
            r'donated[^$]*\$\s*([\d,.]+)\s*(million|billion|thousand)?',
            r'\$\s*([\d,.]+)\s*(million|billion)?\s+(?:in\s+)?charitable',
        ]
        for pattern in charity_patterns:
            match = re.search(pattern, text_lower)
            if match:
                amount = SECFilingParser._parse_currency_amount(match.group(1), match.group(2) if len(match.groups()) > 1 else None)
                if amount:
                    result['charitable_contributions'] = amount
                    result['has_data'] = True
                break

        # Extract Foundation information
        foundation_patterns = [
            r'([a-z\s]+foundation)[^$]*\$\s*([\d,.]+)\s*(million|billion)?',
            r'foundation[^$]*assets?[^$]*\$\s*([\d,.]+)\s*(million|billion)?',
        ]
        for pattern in foundation_patterns:
            match = re.search(pattern, text_lower)
            if match:
                result['foundation'] = {
                    'name': match.group(1).strip().title() if match.lastindex >= 1 else None,
                    'amount': SECFilingParser._parse_currency_amount(
                        match.group(2) if match.lastindex >= 2 else match.group(1),
                        match.group(3) if match.lastindex >= 3 else None
                    )
                }
                result['has_data'] = True
                break

        # Extract Community Commitments (e.g., "$10 billion affordable housing commitment")
        commitment_patterns = [
            r'\$\s*([\d,.]+)\s*(million|billion)\s+(?:commitment|pledge|investment)\s+(?:to|for|in)\s+([^.]{10,100})',
            r'committed\s+\$\s*([\d,.]+)\s*(million|billion)\s+(?:to|for)\s+([^.]{10,100})',
            r'pledged\s+\$\s*([\d,.]+)\s*(million|billion)\s+(?:to|for)\s+([^.]{10,100})',
        ]
        for pattern in commitment_patterns:
            for match in re.finditer(pattern, text_lower):
                amount = SECFilingParser._parse_currency_amount(match.group(1), match.group(2))
                purpose = match.group(3).strip()
                # Filter out generic business commitments
                if any(kw in purpose for kw in ['community', 'affordable', 'minority', 'small business', 'underserved', 'low-income', 'lmi']):
                    result['commitments'].append({
                        'amount': amount,
                        'purpose': purpose[:100]
                    })
                    result['has_data'] = True

        # Deduplicate commitments
        seen = set()
        unique_commitments = []
        for c in result['commitments']:
            key = (c['amount'], c['purpose'][:50])
            if key not in seen:
                seen.add(key)
                unique_commitments.append(c)
        result['commitments'] = unique_commitments[:5]  # Keep top 5

        return result

    @staticmethod
    def _parse_currency_amount(amount_str: str, unit: Optional[str] = None) -> Optional[float]:
        """Parse a currency amount string to float."""
        try:
            amount = float(amount_str.replace(',', ''))
            if unit:
                unit_lower = unit.lower()
                if 'billion' in unit_lower:
                    amount *= 1_000_000_000
                elif 'million' in unit_lower:
                    amount *= 1_000_000
                elif 'thousand' in unit_lower:
                    amount *= 1_000
            return amount
        except (ValueError, AttributeError):
            return None

    @staticmethod
    def extract_filing_date(text: str) -> Optional[str]:
        """Extract filing date from 10-K."""
        # Look for "Date of Report" or "Filing Date"
        patterns = [
            r'Date of Report[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'Filing Date[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'Date[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    @staticmethod
    def extract_fiscal_year_end(text: str) -> Optional[str]:
        """Extract fiscal year end date."""
        patterns = [
            r'Fiscal Year End[:\s]+(\d{1,2}[/-]\d{1,2})',
            r'Fiscal Year[:\s]+(\d{4})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    @staticmethod
    def parse_proxy_statement(filing_text: str) -> Dict[str, Any]:
        """
        Parse DEF 14A proxy statement for compensation and governance data.
        
        Args:
            filing_text: Full proxy statement text
            
        Returns:
            Dictionary with executive compensation and board data
        """
        if not filing_text:
            return {'available': False}
        
        result = {
            'available': True,
            'executive_compensation': [],
            'board_composition': [],
            'committees': []
        }
        
        # Extract Summary Compensation Table
        comp_table = SECFilingParser.extract_compensation_table(filing_text)
        if comp_table:
            result['executive_compensation'] = comp_table
        
        # Extract Director Table
        director_table = SECFilingParser.extract_director_table(filing_text)
        if director_table:
            result['board_composition'] = director_table
        
        return result
    
    @staticmethod
    def extract_compensation_table(text: str) -> List[Dict[str, Any]]:
        """
        Extract Summary Compensation Table from proxy statement.
        
        Args:
            text: Proxy statement text
            
        Returns:
            List of executive compensation records
        """
        # Find Summary Compensation Table section
        table_section = SECFilingParser.extract_section(
            text, 'SUMMARY COMPENSATION TABLE', 'GRANTS OF PLAN'
        )
        
        if not table_section:
            return []
        
        executives = []
        lines = table_section.split('\n')
        
        # Look for rows with dollar amounts
        for line in lines:
            # Check if line contains dollar signs (compensation data)
            if '$' not in line:
                continue
            
            # Try to parse: Name | Title | Year | Salary | Bonus | Stock | Options | Total
            # Split on multiple spaces or tabs
            parts = re.split(r'\s{2,}|\t', line.strip())
            
            if len(parts) >= 4:
                # Try to extract currency values
                currency_values = []
                name = parts[0] if parts else ''
                title = parts[1] if len(parts) > 1 else ''
                
                for part in parts[2:]:
                    # Extract dollar amounts
                    currency_match = re.search(r'\$?([\d,]+(?:\.\d{2})?)', part.replace(',', ''))
                    if currency_match:
                        try:
                            value = float(currency_match.group(1).replace(',', ''))
                            currency_values.append(value)
                        except ValueError:
                            pass
                
                if currency_values and name:
                    executives.append({
                        'name': name.strip(),
                        'title': title.strip(),
                        'salary': currency_values[0] if len(currency_values) > 0 else 0,
                        'bonus': currency_values[1] if len(currency_values) > 1 else 0,
                        'stock_awards': currency_values[2] if len(currency_values) > 2 else 0,
                        'option_awards': currency_values[3] if len(currency_values) > 3 else 0,
                        'total': sum(currency_values) if currency_values else 0
                    })
        
        return executives
    
    @staticmethod
    def extract_director_table(text: str) -> List[Dict[str, Any]]:
        """
        Extract director information from proxy statement.
        
        Args:
            text: Proxy statement text
            
        Returns:
            List of director records
        """
        # Find director table section
        director_section = SECFilingParser.extract_section(
            text, 'DIRECTORS', 'EXECUTIVE OFFICERS'
        )
        
        if not director_section:
            return []
        
        directors = []
        lines = director_section.split('\n')
        
        # Simple extraction - would need more sophisticated parsing for full details
        for line in lines:
            # Look for names (capitalized words, typically 2-3 words)
            name_match = re.match(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})', line)
            if name_match:
                directors.append({
                    'name': name_match.group(1).strip(),
                    'details': line.strip()[:200]
                })
        
        return directors

    @staticmethod
    def merge_with_xbrl_data(parsed_10k: Dict[str, Any], xbrl_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge text-parsed 10-K data with structured XBRL data from SEC API.

        XBRL data is preferred for numerical values because it's structured and reliable.
        Text-parsed data is still useful for qualitative information (CRA rating, commitments).

        Args:
            parsed_10k: Result from parse_10k()
            xbrl_data: Result from SECClient.get_comprehensive_xbrl_data()

        Returns:
            Merged dictionary with best available data
        """
        if not parsed_10k:
            parsed_10k = {'available': False}

        if not xbrl_data:
            # Return original parsed data if no XBRL available
            return parsed_10k

        # Create merged result
        result = parsed_10k.copy()
        result['xbrl_data'] = {}

        # Add core financials from XBRL
        core = xbrl_data.get('core_financials', {})
        if core:
            result['xbrl_data']['core_financials'] = {
                'assets': core.get('assets', {}).get('value'),
                'liabilities': core.get('liabilities', {}).get('value'),
                'stockholders_equity': core.get('stockholders_equity', {}).get('value'),
                'net_income': core.get('net_income', {}).get('value'),
                'interest_income_net': core.get('interest_income_expense_net', {}).get('value'),
                'as_of_date': core.get('assets', {}).get('end_date'),
            }

        # Add bank metrics from XBRL
        bank = xbrl_data.get('bank_metrics', {})
        if bank:
            result['xbrl_data']['bank_metrics'] = {
                'deposits': bank.get('deposits', {}).get('value'),
                'loans_net': bank.get('loans_net', {}).get('value'),
                'allowance_for_loan_losses': bank.get('allowance_for_loan_losses', {}).get('value'),
                'nonaccrual_loans': bank.get('financing_receivable_nonaccrual', {}).get('value'),
            }

        # Merge community investment - use XBRL for amounts, text for qualitative
        community_xbrl = xbrl_data.get('community_investment', {})
        community_text = result.get('community_investment', {})

        merged_community = {
            'has_data': False,
            # XBRL data (structured, reliable amounts)
            'affordable_housing_tax_credits': community_xbrl.get('affordable_housing_tax_credits', {}).get('value'),
            'affordable_housing_amortization': community_xbrl.get('affordable_housing_amortization', {}).get('value'),
            'equity_method_investments': community_xbrl.get('equity_method_investments', {}).get('value'),
            'investment_tax_credit': community_xbrl.get('investment_tax_credit', {}).get('value'),
            # Text-parsed data (qualitative info not in XBRL)
            'cra_rating': community_text.get('cra_rating') if community_text else None,
            'community_development': community_text.get('community_development', {}) if community_text else {},
            'charitable_contributions': community_text.get('charitable_contributions') if community_text else None,
            'foundation': community_text.get('foundation') if community_text else None,
            'commitments': community_text.get('commitments', []) if community_text else [],
        }

        # Check if we have any community data
        merged_community['has_data'] = any([
            merged_community['affordable_housing_tax_credits'],
            merged_community['affordable_housing_amortization'],
            merged_community['cra_rating'],
            merged_community.get('community_development', {}).get('loans'),
            merged_community.get('community_development', {}).get('investments'),
            merged_community['commitments'],
        ])

        result['community_investment'] = merged_community
        result['has_xbrl_data'] = True

        return result

