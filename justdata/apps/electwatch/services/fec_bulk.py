#!/usr/bin/env python3
"""
FEC Bulk Data Processor for ElectWatch

Downloads and processes FEC bulk data files instead of hitting the API.
This avoids rate limits and processes data much faster.

Bulk files used:
- pas224.txt: PAC/Committee contributions to candidates (2023-2024)
- indiv24.txt: Individual contributions (2023-2024)
- cm24.txt: Committee master file (PAC names, types)

Usage:
    from justdata.apps.electwatch.services.fec_bulk import FECBulkProcessor

    processor = FECBulkProcessor()
    processor.download_bulk_files()  # Downloads if not present
    processor.process_pac_contributions(officials_data)
    processor.process_individual_contributions(officials_data)
"""

import csv
import io
import json
import logging
import os
import zipfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import requests

logger = logging.getLogger(__name__)

# FEC Bulk Data URLs - both 2024 and 2026 cycles
# We need both because newly-elected 2024 members have contributions in the 2026 cycle
FEC_BULK_CYCLES = {
    '2024': {
        'base': "https://www.fec.gov/files/bulk-downloads/2024",
        'pas2': "pas224.zip",      # PAC to candidate contributions
        'indiv': "indiv24.zip",    # Individual contributions
        'cm': "cm24.zip",          # Committee master file
        'cn': "cn24.zip",          # Candidate master file
    },
    '2026': {
        'base': "https://www.fec.gov/files/bulk-downloads/2026",
        'pas2': "pas226.zip",      # PAC to candidate contributions for 2025-2026
        'indiv': "indiv26.zip",    # Individual contributions for 2025-2026
        'cm': "cm26.zip",          # Committee master file
        'cn': "cn26.zip",          # Candidate master file
    }
}

# Default to 2024 cycle for backward compatibility
FEC_BULK_BASE = "https://www.fec.gov/files/bulk-downloads/2024"
BULK_FILES = {
    'pas2': f"{FEC_BULK_BASE}/pas224.zip",
    'indiv': f"{FEC_BULK_BASE}/indiv24.zip",
    'cm': f"{FEC_BULK_BASE}/cm24.zip",
    'cn': f"{FEC_BULK_BASE}/cn24.zip",
}

# Column indices for cn file (candidate master)
CN_COLS = {
    'cand_id': 0,
    'cand_name': 1,
    'cand_pty_affiliation': 2,
    'cand_election_yr': 3,
    'cand_office_st': 4,
    'cand_office': 5,           # H=House, S=Senate, P=President
    'cand_office_district': 6,
    'cand_ici': 7,              # I=Incumbent, C=Challenger, O=Open
    'cand_status': 8,
    'cand_pcc': 9,              # Principal campaign committee ID
    'cand_st1': 10,
    'cand_st2': 11,
    'cand_city': 12,
    'cand_st': 13,
    'cand_zip': 14,
}

# Column indices for pas2 file (0-indexed)
PAS2_COLS = {
    'cmte_id': 0,
    'amndt_ind': 1,
    'rpt_tp': 2,
    'transaction_pgi': 3,
    'image_num': 4,
    'transaction_tp': 5,
    'entity_tp': 6,
    'name': 7,
    'city': 8,
    'state': 9,
    'zip_code': 10,
    'employer': 11,
    'occupation': 12,
    'transaction_dt': 13,
    'transaction_amt': 14,
    'other_id': 15,
    'cand_id': 16,
    'tran_id': 17,
    'file_num': 18,
    'memo_cd': 19,
    'memo_text': 20,
    'sub_id': 21,
}

# Column indices for indiv file (0-indexed)
INDIV_COLS = {
    'cmte_id': 0,
    'amndt_ind': 1,
    'rpt_tp': 2,
    'transaction_pgi': 3,
    'image_num': 4,
    'transaction_tp': 5,
    'entity_tp': 6,
    'name': 7,
    'city': 8,
    'state': 9,
    'zip_code': 10,
    'employer': 11,
    'occupation': 12,
    'transaction_dt': 13,
    'transaction_amt': 14,
    'other_id': 15,
    'tran_id': 16,
    'file_num': 17,
    'memo_cd': 18,
    'memo_text': 19,
    'sub_id': 20,
}

# Column indices for cm file (committee master)
CM_COLS = {
    'cmte_id': 0,
    'cmte_nm': 1,
    'tres_nm': 2,
    'cmte_st1': 3,
    'cmte_st2': 4,
    'cmte_city': 5,
    'cmte_st': 6,
    'cmte_zip': 7,
    'cmte_dsgn': 8,
    'cmte_tp': 9,
    'cmte_pty_affiliation': 10,
    'cmte_filing_freq': 11,
    'org_tp': 12,
    'connected_org_nm': 13,
    'cand_id': 14,
}


class FECBulkProcessor:
    """
    Processor for FEC bulk data files.

    Downloads and processes bulk files to enrich official records with
    PAC and individual contribution data.
    """

    # Default local storage path (outside OneDrive for large files)
    LOCAL_DATA_DIR = Path("C:/JustData-LocalData/fec_bulk")

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize the processor."""
        if data_dir is None:
            # Prefer local storage for large FEC files
            if self.LOCAL_DATA_DIR.exists():
                data_dir = self.LOCAL_DATA_DIR
            else:
                data_dir = Path(__file__).parent.parent / 'data' / 'fec_bulk'
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Cache for committee info
        self._committee_cache: Dict[str, Dict] = {}

        # Load financial sector keywords
        self._load_financial_keywords()

    def _load_financial_keywords(self):
        """Load financial sector keywords for PAC/employer classification."""
        # Keywords that indicate financial sector
        self.financial_keywords = {
            # Banking
            'BANK', 'BANKING', 'BANKERS', 'BANCORP', 'BANCSHARES',
            'WELLS FARGO', 'JPMORGAN', 'CHASE', 'CITIBANK', 'CITIGROUP',
            'BANK OF AMERICA', 'GOLDMAN', 'MORGAN STANLEY', 'PNC',
            'TRUIST', 'FIFTH THIRD', 'REGIONS', 'HUNTINGTON', 'KEYBANK',
            'U.S. BANK', 'USB', 'CITIZENS BANK', 'M&T BANK', 'ZIONS',

            # Credit/Lending
            'CREDIT', 'LENDING', 'LOAN', 'MORTGAGE', 'CAPITAL ONE',
            'DISCOVER', 'SYNCHRONY', 'ALLY FINANCIAL', 'SALLIE MAE',
            'NAVIENT', 'QUICKEN', 'ROCKET MORTGAGE', 'LOANDEPOT',

            # Insurance
            'INSURANCE', 'INSURER', 'UNDERWRITER', 'METLIFE', 'PRUDENTIAL',
            'AIG', 'ALLSTATE', 'PROGRESSIVE', 'AFLAC', 'CHUBB', 'TRAVELERS',
            'HARTFORD', 'LINCOLN NATIONAL', 'UNUM', 'CIGNA', 'AETNA',

            # Investment/Asset Management
            'INVESTMENT', 'INVESTOR', 'SECURITIES', 'ASSET MANAGEMENT',
            'BLACKROCK', 'VANGUARD', 'FIDELITY', 'SCHWAB', 'STATE STREET',
            'BLACKSTONE', 'KKR', 'CARLYLE', 'APOLLO', 'TPG',
            'HEDGE FUND', 'PRIVATE EQUITY', 'VENTURE CAPITAL',

            # Payments/Fintech
            'VISA', 'MASTERCARD', 'AMERICAN EXPRESS', 'AMEX', 'PAYPAL',
            'SQUARE', 'STRIPE', 'FISERV', 'FIS ', 'GLOBAL PAYMENTS',
            'WORLDPAY', 'PAYCHEX', 'ADP',

            # Real Estate Finance
            'FANNIE MAE', 'FREDDIE MAC', 'FNMA', 'FHLMC',
            'MORTGAGE BANKERS', 'REAL ESTATE FINANCE',

            # Crypto
            'CRYPTO', 'BITCOIN', 'COINBASE', 'BLOCKCHAIN',

            # Trade Associations
            'AMERICAN BANKERS', 'CREDIT UNION', 'SECURITIES INDUSTRY',
            'FINANCIAL SERVICES', 'CONSUMER BANKERS', 'MORTGAGE LENDERS',
            'INDEPENDENT COMMUNITY BANKERS', 'ICBA',
        }

        # Exclude keywords (not financial even if contains financial terms)
        self.exclude_keywords = {
            'FOOD BANK', 'BLOOD BANK', 'SPERM BANK', 'SEED BANK',
            'RIVER BANK', 'WEST BANK', 'BANK SHOT',
        }

    def is_financial_entity(self, name: str) -> bool:
        """Check if an entity name indicates financial sector."""
        if not name:
            return False

        name_upper = name.upper()

        # Check exclusions first
        for exclude in self.exclude_keywords:
            if exclude in name_upper:
                return False

        # Check for financial keywords
        for keyword in self.financial_keywords:
            if keyword in name_upper:
                return True

        return False

    def download_bulk_files(self, force: bool = False) -> Dict[str, Path]:
        """
        Download FEC bulk data files.

        Args:
            force: If True, re-download even if files exist

        Returns:
            Dict mapping file type to local path
        """
        downloaded = {}

        for file_type, url in BULK_FILES.items():
            zip_path = self.data_dir / f"{file_type}.zip"
            txt_path = self.data_dir / f"{file_type}.txt"

            # Skip if already extracted and not forcing
            if txt_path.exists() and not force:
                logger.info(f"  {file_type}: Using existing {txt_path.name}")
                downloaded[file_type] = txt_path
                continue

            # Download zip file
            logger.info(f"  {file_type}: Downloading from {url}...")
            try:
                response = requests.get(url, stream=True, timeout=300)
                response.raise_for_status()

                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0

                with open(zip_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        if total_size > 0:
                            pct = downloaded_size / total_size * 100
                            if downloaded_size % (10 * 1024 * 1024) < 8192:  # Log every 10MB
                                logger.info(f"    Progress: {pct:.1f}%")

                logger.info(f"  {file_type}: Downloaded {downloaded_size / 1024 / 1024:.1f}MB")

                # Extract
                logger.info(f"  {file_type}: Extracting...")
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    # Find the .txt file in the archive
                    txt_files = [n for n in zf.namelist() if n.endswith('.txt')]
                    if txt_files:
                        # Extract and rename
                        zf.extract(txt_files[0], self.data_dir)
                        extracted = self.data_dir / txt_files[0]
                        if extracted != txt_path:
                            extracted.rename(txt_path)

                # Clean up zip
                zip_path.unlink()

                downloaded[file_type] = txt_path
                logger.info(f"  {file_type}: Ready at {txt_path}")

            except Exception as e:
                logger.error(f"  {file_type}: Download failed: {e}")
                raise

        return downloaded

    def download_cycle_files(self, cycle: str, force: bool = False) -> Dict[str, Path]:
        """
        Download FEC bulk data files for a specific election cycle.

        Args:
            cycle: Election cycle year (e.g., "2024" or "2026")
            force: If True, re-download even if files exist

        Returns:
            Dict mapping file type to local path
        """
        if cycle not in FEC_BULK_CYCLES:
            raise ValueError(f"Unknown cycle {cycle}. Available: {list(FEC_BULK_CYCLES.keys())}")

        cycle_info = FEC_BULK_CYCLES[cycle]
        base_url = cycle_info['base']
        downloaded = {}

        # Create cycle-specific subdirectory
        cycle_dir = self.data_dir / cycle
        cycle_dir.mkdir(parents=True, exist_ok=True)

        for file_type in ['pas2', 'indiv', 'cm', 'cn']:
            filename = cycle_info.get(file_type)
            if not filename:
                continue

            url = f"{base_url}/{filename}"
            zip_path = cycle_dir / filename
            txt_path = cycle_dir / f"{file_type}.txt"

            # Skip if already extracted and not forcing
            if txt_path.exists() and not force:
                logger.info(f"  {cycle}/{file_type}: Using existing {txt_path.name}")
                downloaded[file_type] = txt_path
                continue

            # Download zip file
            logger.info(f"  {cycle}/{file_type}: Downloading from {url}...")
            try:
                response = requests.get(url, stream=True, timeout=300)
                response.raise_for_status()

                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0

                with open(zip_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        if total_size > 0:
                            pct = downloaded_size / total_size * 100
                            if downloaded_size % (10 * 1024 * 1024) < 8192:
                                logger.info(f"    Progress: {pct:.1f}%")

                logger.info(f"  {cycle}/{file_type}: Downloaded {downloaded_size / 1024 / 1024:.1f}MB")

                # Extract
                logger.info(f"  {cycle}/{file_type}: Extracting...")
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    txt_files = [n for n in zf.namelist() if n.endswith('.txt')]
                    if txt_files:
                        zf.extract(txt_files[0], cycle_dir)
                        extracted = cycle_dir / txt_files[0]
                        if extracted != txt_path:
                            extracted.rename(txt_path)

                # Clean up zip
                zip_path.unlink()

                downloaded[file_type] = txt_path
                logger.info(f"  {cycle}/{file_type}: Ready at {txt_path}")

            except Exception as e:
                logger.error(f"  {cycle}/{file_type}: Download failed: {e}")
                # Don't raise - continue with other files/cycles
                continue

        return downloaded

    def download_all_cycles(self, force: bool = False) -> Dict[str, Dict[str, Path]]:
        """
        Download FEC bulk data files for all configured cycles (2024 + 2026).

        Returns:
            Dict mapping cycle to file paths
        """
        all_downloaded = {}
        for cycle in FEC_BULK_CYCLES.keys():
            logger.info(f"Downloading FEC bulk files for cycle {cycle}...")
            all_downloaded[cycle] = self.download_cycle_files(cycle, force)
        return all_downloaded

    def get_pas2_files(self) -> List[Path]:
        """Get all available PAC contribution files from all cycles."""
        files = []
        # Check both legacy location and cycle-specific directories
        legacy_path = self.data_dir / 'pas2.txt'
        if legacy_path.exists():
            files.append(legacy_path)

        for cycle in FEC_BULK_CYCLES.keys():
            cycle_path = self.data_dir / cycle / 'pas2.txt'
            if cycle_path.exists():
                files.append(cycle_path)

        return files

    def get_indiv_files(self) -> List[Path]:
        """Get all available individual contribution files from all cycles."""
        files = []
        # Check both legacy location and cycle-specific directories
        legacy_path = self.data_dir / 'indiv.txt'
        if legacy_path.exists():
            files.append(legacy_path)

        for cycle in FEC_BULK_CYCLES.keys():
            cycle_path = self.data_dir / cycle / 'indiv.txt'
            if cycle_path.exists():
                files.append(cycle_path)

        return files

    def get_cm_files(self) -> List[Path]:
        """Get all available committee master files from all cycles."""
        files = []
        legacy_path = self.data_dir / 'cm.txt'
        if legacy_path.exists():
            files.append(legacy_path)

        for cycle in FEC_BULK_CYCLES.keys():
            cycle_path = self.data_dir / cycle / 'cm.txt'
            if cycle_path.exists():
                files.append(cycle_path)

        return files

    def load_committee_master(self) -> Dict[str, Dict]:
        """
        Load committee master files from all cycles to get PAC names and types.

        Returns:
            Dict mapping committee ID to committee info
        """
        if self._committee_cache:
            return self._committee_cache

        cm_files = self.get_cm_files()

        # If no files exist, try downloading from all cycles
        if not cm_files:
            logger.warning("No committee master files found, downloading...")
            self.download_all_cycles()
            cm_files = self.get_cm_files()

        if not cm_files:
            logger.error("Could not find or download committee master files")
            return {}

        logger.info(f"Loading committee master files from {len(cm_files)} file(s)...")
        committees = {}

        for cm_path in cm_files:
            logger.info(f"  Loading {cm_path}...")
            with open(cm_path, 'r', encoding='latin-1') as f:
                reader = csv.reader(f, delimiter='|')
                for row in reader:
                    if len(row) < 15:  # Need at least 15 columns for cand_id at index 14
                        continue

                    cmte_id = row[CM_COLS['cmte_id']]
                    # More recent files (later cycles) should take precedence
                    committees[cmte_id] = {
                        'id': cmte_id,
                        'name': row[CM_COLS['cmte_nm']],
                        'type': row[CM_COLS['cmte_tp']],
                        'designation': row[CM_COLS['cmte_dsgn']],
                        'party': row[CM_COLS['cmte_pty_affiliation']],
                        'connected_org': row[CM_COLS['connected_org_nm']] if len(row) > CM_COLS['connected_org_nm'] else '',
                        'cand_id': row[CM_COLS['cand_id']] if len(row) > CM_COLS['cand_id'] else '',
                    }

        self._committee_cache = committees
        logger.info(f"Loaded {len(committees)} committees from all cycles")
        return committees

    def _normalize_name(self, name: str, keep_comma: bool = False) -> str:
        """Normalize name for matching (uppercase, remove titles, etc)."""
        if not name:
            return ""
        # Uppercase
        name = name.upper()

        # Remove professional suffixes with comma (e.g., ", MD", ", FACS", ", PHD")
        import re
        name = re.sub(r',\s*(MD|PHD|FACS|ESQ|CPA|JD|MBA|DDS|DO|RN|LLP|LLC|INC)\b', '', name)

        # Remove titles (MR, MS, MRS, DR, HON, REV, etc.)
        name = re.sub(r'\b(MR|MS|MRS|DR|HON|REV|SEN|REP|SENATOR|REPRESENTATIVE)\b\.?', '', name)

        # Remove generational suffixes
        name = re.sub(r'\b(JR|SR|I|II|III|IV|V)\b\.?', '', name)

        # Remove punctuation (but optionally keep comma for format detection)
        for char in '."\'':
            name = name.replace(char, '')

        if not keep_comma:
            name = name.replace(',', '')

        # Normalize whitespace
        name = ' '.join(name.split())
        return name

    def _has_comma_format(self, name: str) -> bool:
        """Check if name is in 'LAST, FIRST' format."""
        # Check original name for comma before any letters that aren't suffix-related
        import re
        # Remove professional suffixes first
        cleaned = re.sub(r',\s*(MD|PHD|FACS|ESQ|CPA|JD|MBA|DDS|DO|RN|LLP|LLC|INC)\b', '', name.upper())
        # Check if there's still a comma (indicates LAST, FIRST format)
        return ',' in cleaned

    def _extract_last_name(self, name: str) -> str:
        """Extract last name from FEC format (LAST, FIRST MIDDLE) or normal (FIRST LAST)."""
        has_comma = self._has_comma_format(name)
        normalized = self._normalize_name(name, keep_comma=True)

        if has_comma and ',' in normalized:
            # FEC/Congress format: LASTNAME, FIRSTNAME
            return normalized.split(',')[0].strip()
        else:
            # Normal format: FIRST LAST - take last word
            normalized = normalized.replace(',', '')
            parts = normalized.split()
            return parts[-1] if parts else ''

    def _extract_first_name(self, name: str) -> str:
        """Extract first name from either format."""
        has_comma = self._has_comma_format(name)
        normalized = self._normalize_name(name, keep_comma=True)

        if has_comma and ',' in normalized:
            # FEC/Congress format: LASTNAME, FIRSTNAME MIDDLE
            parts_after_comma = normalized.split(',')[1].strip().split()
            return parts_after_comma[0] if parts_after_comma else ''
        else:
            # Normal format: FIRST LAST
            normalized = normalized.replace(',', '')
            parts = normalized.split()
            return parts[0] if parts else ''

    def _names_match(self, name1: str, name2: str) -> bool:
        """Check if two names match (handles different formats)."""
        n1 = self._normalize_name(name1)
        n2 = self._normalize_name(name2)

        # Direct match
        if n1 == n2:
            return True

        # Extract last names
        last1 = self._extract_last_name(name1)
        last2 = self._extract_last_name(name2)

        # Last names must match
        if last1 != last2:
            return False

        # Get first names
        first1 = self._extract_first_name(name1)
        first2 = self._extract_first_name(name2)

        if not first1 or not first2:
            return False

        # Check first name matching
        # Direct match
        if first1 == first2:
            return True

        # One is prefix of other (handles middle name initials like "JAMES" vs "JAMES C")
        # Also handles first initials
        if first1.startswith(first2) or first2.startswith(first1):
            return True

        # Same first letter (initial match)
        if first1[0] == first2[0]:
            return True

        return False

    def match_officials_to_candidates(
        self,
        officials_data: List[Dict]
    ) -> int:
        """
        Match officials to FEC candidates using name/state matching.

        Downloads the candidate master file if needed and matches officials
        by name, state, and chamber.

        Args:
            officials_data: List of official records

        Returns:
            Number of officials matched
        """
        cn_path = self.data_dir / 'cn.txt'
        if not cn_path.exists():
            logger.info("Candidate master file not found, downloading...")
            self.download_bulk_files()

        # State name to abbreviation mapping
        state_abbrevs = {
            'ALABAMA': 'AL', 'ALASKA': 'AK', 'ARIZONA': 'AZ', 'ARKANSAS': 'AR',
            'CALIFORNIA': 'CA', 'COLORADO': 'CO', 'CONNECTICUT': 'CT', 'DELAWARE': 'DE',
            'DISTRICT OF COLUMBIA': 'DC', 'FLORIDA': 'FL', 'GEORGIA': 'GA', 'HAWAII': 'HI',
            'IDAHO': 'ID', 'ILLINOIS': 'IL', 'INDIANA': 'IN', 'IOWA': 'IA',
            'KANSAS': 'KS', 'KENTUCKY': 'KY', 'LOUISIANA': 'LA', 'MAINE': 'ME',
            'MARYLAND': 'MD', 'MASSACHUSETTS': 'MA', 'MICHIGAN': 'MI', 'MINNESOTA': 'MN',
            'MISSISSIPPI': 'MS', 'MISSOURI': 'MO', 'MONTANA': 'MT', 'NEBRASKA': 'NE',
            'NEVADA': 'NV', 'NEW HAMPSHIRE': 'NH', 'NEW JERSEY': 'NJ', 'NEW MEXICO': 'NM',
            'NEW YORK': 'NY', 'NORTH CAROLINA': 'NC', 'NORTH DAKOTA': 'ND', 'OHIO': 'OH',
            'OKLAHOMA': 'OK', 'OREGON': 'OR', 'PENNSYLVANIA': 'PA', 'RHODE ISLAND': 'RI',
            'SOUTH CAROLINA': 'SC', 'SOUTH DAKOTA': 'SD', 'TENNESSEE': 'TN', 'TEXAS': 'TX',
            'UTAH': 'UT', 'VERMONT': 'VT', 'VIRGINIA': 'VA', 'WASHINGTON': 'WA',
            'WEST VIRGINIA': 'WV', 'WISCONSIN': 'WI', 'WYOMING': 'WY',
            'AMERICAN SAMOA': 'AS', 'GUAM': 'GU', 'NORTHERN MARIANA ISLANDS': 'MP',
            'PUERTO RICO': 'PR', 'US VIRGIN ISLANDS': 'VI',
        }

        logger.info("Loading FEC candidate master file...")

        # Load all candidates from FEC file
        # Group by state and office for faster matching
        candidates_by_state_office = defaultdict(list)

        with open(cn_path, 'r', encoding='latin-1') as f:
            reader = csv.reader(f, delimiter='|')
            for row in reader:
                if len(row) < 10:
                    continue

                cand_id = row[CN_COLS['cand_id']]
                cand_name = row[CN_COLS['cand_name']]
                cand_state = row[CN_COLS['cand_office_st']]
                cand_office = row[CN_COLS['cand_office']]  # H, S, or P
                cand_district = row[CN_COLS['cand_office_district']] if len(row) > CN_COLS['cand_office_district'] else ''
                cand_year = row[CN_COLS['cand_election_yr']]

                # Only care about recent candidates (2022-2026)
                try:
                    year = int(cand_year) if cand_year else 0
                    if year < 2022:
                        continue
                except:
                    continue

                # Only care about House and Senate
                if cand_office not in ('H', 'S'):
                    continue

                candidates_by_state_office[(cand_state, cand_office)].append({
                    'cand_id': cand_id,
                    'name': cand_name,
                    'state': cand_state,
                    'office': cand_office,
                    'district': cand_district,
                    'year': year,
                })

        total_candidates = sum(len(v) for v in candidates_by_state_office.values())
        logger.info(f"Loaded {total_candidates} House/Senate candidates from FEC file")

        # Match officials
        matched = 0
        for official in officials_data:
            if official.get('fec_candidate_id'):
                matched += 1
                continue  # Already has ID

            # Get state abbreviation
            state = official.get('state', '')
            state_abbrev = state_abbrevs.get(state.upper(), state.upper()[:2] if len(state) > 2 else state.upper())

            # Determine office type
            chamber = official.get('chamber', '')
            office = 'S' if chamber == 'senate' else 'H'

            # Get candidate list for this state/office
            candidates = candidates_by_state_office.get((state_abbrev, office), [])

            # Try to match by name
            official_name = official.get('name', '')
            best_match = None
            best_year = 0

            for cand in candidates:
                if self._names_match(official_name, cand['name']):
                    # For House, also check district if available
                    if office == 'H':
                        official_district = str(official.get('district', '')).zfill(2)
                        cand_district = str(cand.get('district', '')).zfill(2)
                        if official_district != cand_district:
                            continue

                    # Prefer most recent candidate record
                    if cand['year'] > best_year:
                        best_year = cand['year']
                        best_match = cand

            if best_match:
                official['fec_candidate_id'] = best_match['cand_id']
                matched += 1
                logger.debug(f"  Matched: {official_name} -> {best_match['cand_id']}")

        logger.info(f"Matched {matched}/{len(officials_data)} officials to FEC candidates")
        return matched

    # Traditional PAC types to include (exclude Super PACs, party committees, etc.)
    TRADITIONAL_PAC_TYPES = {'Q', 'N', 'V', 'W'}

    def process_pac_contributions(
        self,
        officials_data: List[Dict],
        min_date: str = "2023-01-01"
    ) -> Dict[str, Dict]:
        """
        Process PAC contributions from bulk files (all available cycles).

        Only includes traditional PACs (types Q, N, V, W).
        Excludes Super PACs, party committees, and candidate committees.

        Args:
            officials_data: List of official records with fec_candidate_id
            min_date: Minimum transaction date (YYYY-MM-DD)

        Returns:
            Dict mapping candidate_id to contribution summary
        """
        # Get all available PAC contribution files (from all cycles)
        pas2_files = self.get_pas2_files()

        # If no files exist, download from all cycles
        if not pas2_files:
            logger.info("No PAC contribution files found, downloading from all cycles...")
            self.download_all_cycles()
            pas2_files = self.get_pas2_files()

        if not pas2_files:
            logger.error("Could not download PAC contribution files")
            return {}

        logger.info(f"Processing PAC contributions from {len(pas2_files)} file(s): {[f.name for f in pas2_files]}")

        # Build lookup of candidate IDs we care about
        candidate_ids = set()
        for official in officials_data:
            cand_id = official.get('fec_candidate_id')
            if cand_id:
                candidate_ids.add(cand_id)

        logger.info(f"Processing PAC contributions for {len(candidate_ids)} candidates...")
        logger.info(f"Including only traditional PAC types: {self.TRADITIONAL_PAC_TYPES}")

        # Load committee info for PAC classification
        committees = self.load_committee_master()

        # Load PAC classifier for subsector tagging
        from justdata.apps.electwatch.services.pac_classifier import PACClassifier
        pac_classifier = PACClassifier()

        # Parse min_date
        min_date_parsed = datetime.strptime(min_date, "%Y-%m-%d")

        # Process contributions
        contributions = defaultdict(lambda: {
            'total_pac': 0,
            'financial_pac': 0,
            'financial_pac_count': 0,
            'total_pac_count': 0,
            'financial_pacs': [],
            'top_financial_pacs': [],
            'by_sector': defaultdict(float),  # Breakdown by sector
            'by_subsector': defaultdict(float),  # Breakdown by subsector
        })

        # Track PAC contributions per candidate with sector info
        pac_by_candidate = defaultdict(lambda: defaultdict(lambda: {
            'amount': 0, 'count': 0, 'sector': None, 'subsector': None
        }))

        row_count = 0
        matched_count = 0

        # Process all available PAC contribution files (from all cycles)
        for pas2_path in pas2_files:
            logger.info(f"  Processing {pas2_path}...")
            file_row_count = 0

            with open(pas2_path, 'r', encoding='latin-1') as f:
                reader = csv.reader(f, delimiter='|')
                for row in reader:
                    row_count += 1
                    file_row_count += 1
                    if file_row_count % 500000 == 0:
                        logger.info(f"    Processed {file_row_count:,} rows, {matched_count:,} matched...")

                    if len(row) < 17:
                        continue

                    cand_id = row[PAS2_COLS['cand_id']]
                    if cand_id not in candidate_ids:
                        continue

                    # Parse date
                    date_str = row[PAS2_COLS['transaction_dt']]
                    if date_str and len(date_str) == 8:
                        try:
                            trans_date = datetime.strptime(date_str, "%m%d%Y")
                            if trans_date < min_date_parsed:
                                continue
                        except:
                            pass

                    # Parse amount
                    try:
                        amount = float(row[PAS2_COLS['transaction_amt']])
                    except:
                        continue

                    if amount <= 0:
                        continue

                    cmte_id = row[PAS2_COLS['cmte_id']]

                    # Get committee info
                    cmte_info = committees.get(cmte_id, {})
                    cmte_type = cmte_info.get('type', '')

                    # Only include traditional PACs (exclude Super PACs, party committees, etc.)
                    if cmte_type not in self.TRADITIONAL_PAC_TYPES:
                        continue

                    matched_count += 1

                    # Get PAC name from committee master (NOT from pas2 'name' field,
                    # which is the recipient's name, not the contributing PAC)
                    pac_name = cmte_info.get('name', '')

                    # If not in committee master, use cmte_id as placeholder
                    if not pac_name:
                        pac_name = f"COMMITTEE {cmte_id}"

                    # Classify PAC using the PAC classifier (includes sector/subsector)
                    connected_org = cmte_info.get('connected_org', '')
                    pac_class = pac_classifier.classify_pac(pac_name, connected_org)
                    is_financial = pac_class.get('is_financial', False)
                    sector = pac_class.get('sector')
                    subsector = pac_class.get('subsector')

                    # Update totals
                    contributions[cand_id]['total_pac'] += amount
                    contributions[cand_id]['total_pac_count'] += 1

                    if is_financial:
                        contributions[cand_id]['financial_pac'] += amount
                        contributions[cand_id]['financial_pac_count'] += 1
                        pac_by_candidate[cand_id][pac_name]['amount'] += amount
                        pac_by_candidate[cand_id][pac_name]['count'] += 1
                        pac_by_candidate[cand_id][pac_name]['sector'] = sector
                        pac_by_candidate[cand_id][pac_name]['subsector'] = subsector

                        # Track by sector and subsector
                        if sector:
                            contributions[cand_id]['by_sector'][sector] += amount
                        if subsector:
                            contributions[cand_id]['by_subsector'][f"{sector}/{subsector}"] += amount

            logger.info(f"    File complete: {file_row_count:,} rows processed")

        logger.info(f"Processed {row_count:,} total rows, {matched_count:,} matched to our candidates")

        # Calculate top PACs and percentages
        for cand_id, data in contributions.items():
            if data['total_pac'] > 0:
                data['financial_pac_pct'] = round(data['financial_pac'] / data['total_pac'] * 100, 1)
            else:
                data['financial_pac_pct'] = 0.0

            # Get top financial PACs with sector info
            pacs = pac_by_candidate[cand_id]
            sorted_pacs = sorted(pacs.items(), key=lambda x: -x[1]['amount'])
            data['top_financial_pacs'] = [
                {
                    'name': name,
                    'amount': info['amount'],
                    'count': info['count'],
                    'sector': info.get('sector'),
                    'subsector': info.get('subsector'),
                }
                for name, info in sorted_pacs[:10]
            ]
            data['financial_pacs'] = [name for name, _ in sorted_pacs]

            # Convert defaultdicts to regular dicts for JSON serialization
            data['by_sector'] = dict(sorted(data['by_sector'].items(), key=lambda x: -x[1]))
            data['by_subsector'] = dict(sorted(data['by_subsector'].items(), key=lambda x: -x[1]))

        # Merge into officials data
        enriched = 0
        for official in officials_data:
            cand_id = official.get('fec_candidate_id')
            if cand_id and cand_id in contributions:
                data = contributions[cand_id]
                official['financial_pac_bulk'] = data['financial_pac']
                official['financial_pac_pct'] = data['financial_pac_pct']
                official['financial_pac_count'] = data['financial_pac_count']
                official['total_pac_bulk'] = data['total_pac']
                official['total_pac_count'] = data['total_pac_count']
                official['top_financial_pacs'] = data['top_financial_pacs']
                official['pac_by_sector'] = data['by_sector']
                official['pac_by_subsector'] = data['by_subsector']
                enriched += 1

        logger.info(f"Enriched {enriched} officials with PAC contribution data")

        # Save PAC classifier cache
        pac_classifier._save_cache()

        return dict(contributions)

    def process_individual_contributions(
        self,
        officials_data: List[Dict],
        min_date: str = "2023-01-01"
    ) -> Dict[str, Dict]:
        """
        Process individual contributions from bulk files (all available cycles).

        Identifies contributions from employees of financial firms.

        Args:
            officials_data: List of official records with fec_candidate_id
            min_date: Minimum transaction date (YYYY-MM-DD)

        Returns:
            Dict mapping candidate_id to contribution summary
        """
        # Get all available individual contribution files (from all cycles)
        indiv_files = self.get_indiv_files()

        # If no files exist, download from all cycles
        if not indiv_files:
            logger.info("No individual contribution files found, downloading from all cycles...")
            self.download_all_cycles()
            indiv_files = self.get_indiv_files()

        if not indiv_files:
            logger.error("Could not download individual contribution files")
            return {}

        logger.info(f"Processing individual contributions from {len(indiv_files)} file(s): {[f.name for f in indiv_files]}")

        # Build lookup: committee_id -> candidate_id
        # First load committee master to find principal campaign committees
        committees = self.load_committee_master()

        # Build lookup of committees that belong to our candidates
        committee_to_candidate = {}
        candidate_ids = set()
        for official in officials_data:
            cand_id = official.get('fec_candidate_id')
            if cand_id:
                candidate_ids.add(cand_id)

        # Find committees linked to our candidates
        for cmte_id, cmte_info in committees.items():
            linked_cand = cmte_info.get('cand_id', '')
            if linked_cand in candidate_ids:
                committee_to_candidate[cmte_id] = linked_cand

        logger.info(f"Processing individual contributions for {len(candidate_ids)} candidates...")
        logger.info(f"Found {len(committee_to_candidate)} committees linked to our candidates")

        # Parse min_date
        min_date_parsed = datetime.strptime(min_date, "%Y-%m-%d")

        # Load firm matcher for employer->firm matching (uses PAC connected orgs)
        from justdata.apps.electwatch.services.firm_matcher import FirmMatcher
        firm_matcher = FirmMatcher()
        firm_matcher.build_firm_list()

        # Process contributions
        contributions = defaultdict(lambda: {
            'total_individual': 0,
            'financial_individual': 0,
            'financial_individual_count': 0,
            'total_individual_count': 0,
            'financial_employers': defaultdict(lambda: {'amount': 0, 'count': 0, 'sector': None, 'subsector': None, 'matched_firm': None}),
            'by_sector': defaultdict(float),
            'by_subsector': defaultdict(float),
        })

        row_count = 0
        matched_count = 0

        # Process all available individual contribution files (from all cycles)
        for indiv_path in indiv_files:
            logger.info(f"  Processing {indiv_path}...")
            file_row_count = 0

            with open(indiv_path, 'r', encoding='latin-1') as f:
                reader = csv.reader(f, delimiter='|')
                for row in reader:
                    row_count += 1
                    file_row_count += 1
                    if file_row_count % 1000000 == 0:
                        logger.info(f"    Processed {file_row_count:,} rows, {matched_count:,} matched...")

                    if len(row) < 16:
                        continue

                    cmte_id = row[INDIV_COLS['cmte_id']]
                    cand_id = committee_to_candidate.get(cmte_id)
                    if not cand_id:
                        continue

                    # Parse date
                    date_str = row[INDIV_COLS['transaction_dt']]
                    if date_str and len(date_str) == 8:
                        try:
                            trans_date = datetime.strptime(date_str, "%m%d%Y")
                            if trans_date < min_date_parsed:
                                continue
                        except:
                            pass

                    # Parse amount
                    try:
                        amount = float(row[INDIV_COLS['transaction_amt']])
                    except:
                        continue

                    if amount <= 0:
                        continue

                    matched_count += 1
                    employer = row[INDIV_COLS['employer']] or ''
                    occupation = row[INDIV_COLS['occupation']] or ''

                    # Match employer against known financial firms (from PAC data)
                    match = firm_matcher.match_employer(employer)
                    is_financial = match is not None
                    sector = match.get('sector') if match else None
                    subsector = match.get('subsector') if match else None
                    matched_firm = match.get('matched_firm') if match else None

                    # If employer didn't match, try occupation (some list job title as employer)
                    if not is_financial and occupation:
                        occ_match = firm_matcher.match_employer(occupation)
                        if occ_match:
                            is_financial = True
                            sector = occ_match.get('sector')
                            subsector = occ_match.get('subsector')
                            matched_firm = occ_match.get('matched_firm')

                    # Update totals
                    contributions[cand_id]['total_individual'] += amount
                    contributions[cand_id]['total_individual_count'] += 1

                    if is_financial:
                        contributions[cand_id]['financial_individual'] += amount
                        contributions[cand_id]['financial_individual_count'] += 1
                        contributions[cand_id]['financial_employers'][employer]['amount'] += amount
                        contributions[cand_id]['financial_employers'][employer]['count'] += 1
                        contributions[cand_id]['financial_employers'][employer]['sector'] = sector
                        contributions[cand_id]['financial_employers'][employer]['subsector'] = subsector
                        contributions[cand_id]['financial_employers'][employer]['matched_firm'] = matched_firm

                        # Track by sector and subsector
                        if sector:
                            contributions[cand_id]['by_sector'][sector] += amount
                        if subsector:
                            contributions[cand_id]['by_subsector'][f"{sector}/{subsector}"] += amount

            logger.info(f"    File complete: {file_row_count:,} rows processed")

        logger.info(f"Processed {row_count:,} total rows, {matched_count:,} matched to our candidates")

        # Calculate percentages and top employers
        for cand_id, data in contributions.items():
            if data['total_individual'] > 0:
                data['financial_individual_pct'] = round(
                    data['financial_individual'] / data['total_individual'] * 100, 1
                )
            else:
                data['financial_individual_pct'] = 0.0

            # Get top financial employers with sector info
            employers = data['financial_employers']
            sorted_employers = sorted(employers.items(), key=lambda x: -x[1]['amount'])
            data['top_financial_employers'] = [
                {
                    'employer': name,
                    'amount': info['amount'],
                    'count': info['count'],
                    'sector': info.get('sector'),
                    'subsector': info.get('subsector'),
                    'matched_firm': info.get('matched_firm'),
                }
                for name, info in sorted_employers[:10]
            ]
            # Convert defaultdicts to regular dicts for JSON serialization
            data['financial_employers'] = dict(employers)
            data['by_sector'] = dict(sorted(data['by_sector'].items(), key=lambda x: -x[1]))
            data['by_subsector'] = dict(sorted(data['by_subsector'].items(), key=lambda x: -x[1]))

        # Merge into officials data
        enriched = 0
        for official in officials_data:
            cand_id = official.get('fec_candidate_id')
            if cand_id and cand_id in contributions:
                data = contributions[cand_id]
                official['financial_individual'] = data['financial_individual']
                official['financial_individual_pct'] = data['financial_individual_pct']
                official['financial_individual_count'] = data['financial_individual_count']
                official['total_individual'] = data['total_individual']
                official['total_individual_count'] = data['total_individual_count']
                official['top_financial_employers'] = data['top_financial_employers']
                official['indiv_by_sector'] = data['by_sector']
                official['indiv_by_subsector'] = data['by_subsector']
                enriched += 1

        logger.info(f"Enriched {enriched} officials with individual contribution data")

        # Save firm matcher cache
        firm_matcher.save_match_cache()

        return dict(contributions)

    def get_all_unique_pacs(self, officials_data: List[Dict]) -> Set[str]:
        """Extract all unique PAC names for review/classification."""
        pacs = set()
        for official in officials_data:
            for pac in official.get('top_financial_pacs', []):
                pacs.add(pac.get('name', ''))
        return pacs

    def get_all_unique_employers(self, officials_data: List[Dict]) -> Set[str]:
        """Extract all unique employer names for review/classification."""
        employers = set()
        for official in officials_data:
            for emp in official.get('top_financial_employers', []):
                employers.add(emp.get('employer', ''))
        return employers


def download_fec_bulk_files(data_dir: Optional[Path] = None) -> Dict[str, Path]:
    """Convenience function to download FEC bulk files."""
    processor = FECBulkProcessor(data_dir)
    return processor.download_bulk_files()


if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    processor = FECBulkProcessor()

    if len(sys.argv) > 1 and sys.argv[1] == 'download':
        print("Downloading FEC bulk files...")
        files = processor.download_bulk_files(force=True)
        print(f"Downloaded: {list(files.keys())}")
    else:
        print("FEC Bulk Processor")
        print("=" * 50)
        print("Usage:")
        print("  python fec_bulk.py download  - Download bulk files")
        print()
        print("Or use programmatically:")
        print("  from fec_bulk import FECBulkProcessor")
        print("  processor = FECBulkProcessor()")
        print("  processor.download_bulk_files()")
        print("  processor.process_pac_contributions(officials_data)")
