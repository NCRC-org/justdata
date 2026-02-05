"""FEC Bulk Data Loader for ElectWatch.

This module loads FEC bulk data files and imports campaign finance data
into BigQuery, filtered to only current Congress members.

Bulk files:
- cm.txt - Committee Master (PAC/committee names)
- cn.txt - Candidate Master (candidate info + principal campaign committee)
- pas2.txt/itpas2.txt - PAC to Candidate contributions
- itcont.txt - Individual contributions

Usage:
    python -m justdata.apps.electwatch.services.fec_bulk_loader \
        --data-dir /path/to/unzipped/files \
        --cycles 2024 2026
"""

import argparse
import csv
import hashlib
import logging
import os
import re
import zipfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from google.cloud import bigquery

logger = logging.getLogger(__name__)

# =============================================================================
# FEC FILE COLUMN DEFINITIONS
# =============================================================================

# Committee Master File (cm.txt)
CM_COLUMNS = [
    'cmte_id', 'cmte_nm', 'tres_nm', 'cmte_st1', 'cmte_st2',
    'cmte_city', 'cmte_st', 'cmte_zip', 'cmte_dsgn', 'cmte_tp',
    'cmte_pty_affiliation', 'cmte_filing_freq', 'org_tp', 'connected_org_nm', 'cand_id'
]

# Candidate Master File (cn.txt)
CN_COLUMNS = [
    'cand_id', 'cand_name', 'cand_pty_affiliation', 'cand_election_yr',
    'cand_office_st', 'cand_office', 'cand_office_district', 'cand_ici',
    'cand_status', 'cand_pcc', 'cand_st1', 'cand_st2', 'cand_city',
    'cand_st', 'cand_zip'
]

# PAC to Candidate (itpas2.txt / pas2.txt)
PAS2_COLUMNS = [
    'cmte_id', 'amndt_ind', 'rpt_tp', 'transaction_pgi', 'image_num',
    'transaction_tp', 'entity_tp', 'name', 'city', 'state', 'zip_code',
    'employer', 'occupation', 'transaction_dt', 'transaction_amt',
    'other_id', 'cand_id', 'tran_id', 'file_num', 'memo_cd', 'memo_text', 'sub_id'
]

# Individual Contributions (itcont.txt)
ITCONT_COLUMNS = [
    'cmte_id', 'amndt_ind', 'rpt_tp', 'transaction_pgi', 'image_num',
    'transaction_tp', 'entity_tp', 'name', 'city', 'state', 'zip_code',
    'employer', 'occupation', 'transaction_dt', 'transaction_amt',
    'other_id', 'cand_id', 'tran_id', 'file_num', 'memo_cd', 'memo_text', 'sub_id'
]

# =============================================================================
# FINANCIAL SECTOR CLASSIFICATION
# =============================================================================

# Keywords to identify financial sector PACs/employers
FINANCIAL_KEYWORDS = [
    # Banks
    'bank', 'bancorp', 'bancshares', 'banking', 'banc',
    # Investment
    'investment', 'capital', 'asset', 'wealth', 'securities',
    'hedge fund', 'private equity', 'venture',
    # Insurance
    'insurance', 'insur', 'underwriter', 'actuar',
    # Real Estate
    'real estate', 'realty', 'mortgage', 'title',
    # Credit
    'credit', 'lending', 'loan', 'finance', 'financial',
    # Specific companies
    'goldman', 'morgan stanley', 'jpmorgan', 'jp morgan', 'citigroup', 'citi',
    'blackrock', 'blackstone', 'vanguard', 'fidelity', 'schwab',
    'wells fargo', 'bank of america', 'boa',
    'american express', 'amex', 'visa', 'mastercard',
    'prudential', 'metlife', 'aig', 'allstate', 'state farm',
    'berkshire', 'apollo', 'kkr', 'carlyle', 'tpg',
    'citadel', 'renaissance', 'two sigma', 'bridgewater',
    'pimco', 'invesco', 'franklin templeton', 't. rowe price',
]

# Occupation keywords for financial sector
FINANCIAL_OCCUPATIONS = [
    'banker', 'investment', 'trader', 'broker', 'analyst',
    'portfolio', 'fund manager', 'hedge fund', 'private equity',
    'venture capital', 'financial advisor', 'wealth manager',
    'insurance', 'underwriter', 'actuary', 'cfo', 'finance',
    'accountant', 'cpa', 'auditor',
]


def is_financial_sector(name: str, employer: str = '', occupation: str = '') -> Tuple[bool, str]:
    """
    Determine if a contributor/PAC is in the financial sector.
    
    Returns:
        Tuple of (is_financial, match_reason)
    """
    name_lower = (name or '').lower()
    employer_lower = (employer or '').lower()
    occupation_lower = (occupation or '').lower()
    
    # Check PAC/committee name
    for keyword in FINANCIAL_KEYWORDS:
        if keyword in name_lower:
            return True, f'name:{keyword}'
    
    # Check employer
    for keyword in FINANCIAL_KEYWORDS:
        if keyword in employer_lower:
            return True, f'employer:{keyword}'
    
    # Check occupation
    for keyword in FINANCIAL_OCCUPATIONS:
        if keyword in occupation_lower:
            return True, f'occupation:{keyword}'
    
    return False, ''


def _generate_id(*parts) -> str:
    """Generate a deterministic ID from parts."""
    combined = '|'.join(str(p) for p in parts if p)
    return hashlib.md5(combined.encode()).hexdigest()[:16]


def _parse_fec_date(date_str: str) -> Optional[str]:
    """Parse FEC date format (MMDDYYYY) to ISO format."""
    if not date_str or len(date_str) != 8:
        return None
    try:
        dt = datetime.strptime(date_str, '%m%d%Y')
        return dt.strftime('%Y-%m-%d')
    except ValueError:
        return None


# =============================================================================
# BULK LOADER CLASS
# =============================================================================

class FECBulkLoader:
    """Loads FEC bulk data into BigQuery for ElectWatch."""
    
    def __init__(
        self,
        project_id: str = 'justdata-ncrc',
        dataset_id: str = 'electwatch',
    ):
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.client = bigquery.Client(project=project_id)
        
        # Lookups built from reference files
        self.committees: Dict[str, Dict] = {}  # cmte_id -> committee info
        self.candidates: Dict[str, Dict] = {}  # cand_id -> candidate info
        self.committee_to_candidate: Dict[str, str] = {}  # cmte_id -> cand_id (principal committees)
        
        # Congress member lookups (from crosswalk)
        self.fec_to_bioguide: Dict[str, str] = {}  # fec_cand_id -> bioguide_id
        self.bioguide_to_fec: Dict[str, List[str]] = {}  # bioguide_id -> [fec_ids]
        self.congress_fec_ids: Set[str] = set()  # All FEC IDs for Congress members
        self.congress_committee_ids: Set[str] = set()  # Principal campaign committees
        
        # Statistics
        self.stats = {
            'committees_loaded': 0,
            'candidates_loaded': 0,
            'congress_members_mapped': 0,
            'pac_contributions_total': 0,
            'pac_contributions_congress': 0,
            'pac_contributions_financial': 0,
            'individual_contributions_total': 0,
            'individual_contributions_congress': 0,
            'individual_contributions_financial': 0,
        }
    
    def load_crosswalk(self):
        """Load Congress member crosswalk (bioguide_id <-> FEC ID mapping)."""
        logger.info("Loading Congress crosswalk...")
        
        try:
            from justdata.apps.electwatch.services.crosswalk import get_crosswalk
            crosswalk = get_crosswalk(include_historical=True)
            
            # Build lookups
            for bioguide_id, info in crosswalk._crosswalk.items():
                fec_ids = info.get('fec_ids', [])
                if fec_ids:
                    self.bioguide_to_fec[bioguide_id] = fec_ids
                    for fec_id in fec_ids:
                        self.fec_to_bioguide[fec_id] = bioguide_id
                        self.congress_fec_ids.add(fec_id)
            
            self.stats['congress_members_mapped'] = len(self.bioguide_to_fec)
            logger.info(f"Loaded crosswalk: {len(self.fec_to_bioguide)} FEC IDs for {len(self.bioguide_to_fec)} Congress members")
            
        except Exception as e:
            logger.error(f"Failed to load crosswalk: {e}")
            raise
    
    def load_committee_master(self, file_path: str):
        """Load committee master file (cm.txt)."""
        logger.info(f"Loading committee master from {file_path}...")
        
        count = 0
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                parts = line.strip().split('|')
                if len(parts) >= len(CM_COLUMNS):
                    row = dict(zip(CM_COLUMNS, parts))
                    cmte_id = row['cmte_id']
                    self.committees[cmte_id] = {
                        'cmte_id': cmte_id,
                        'name': row['cmte_nm'],
                        'connected_org': row['connected_org_nm'],
                        'type': row['cmte_tp'],
                        'party': row['cmte_pty_affiliation'],
                        'cand_id': row.get('cand_id', ''),
                    }
                    count += 1
        
        self.stats['committees_loaded'] = count
        logger.info(f"Loaded {count} committees")
    
    def load_candidate_master(self, file_path: str):
        """Load candidate master file (cn.txt)."""
        logger.info(f"Loading candidate master from {file_path}...")
        
        count = 0
        congress_count = 0
        
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                parts = line.strip().split('|')
                if len(parts) >= 10:  # At least through cand_pcc
                    row = dict(zip(CN_COLUMNS, parts[:len(CN_COLUMNS)]))
                    cand_id = row['cand_id']
                    pcc = row.get('cand_pcc', '')
                    
                    self.candidates[cand_id] = {
                        'cand_id': cand_id,
                        'name': row['cand_name'],
                        'party': row['cand_pty_affiliation'],
                        'office': row['cand_office'],
                        'state': row['cand_office_st'],
                        'district': row.get('cand_office_district', ''),
                        'pcc': pcc,
                    }
                    
                    # Map principal campaign committee -> candidate
                    if pcc:
                        self.committee_to_candidate[pcc] = cand_id
                        
                        # Track Congress member committees
                        if cand_id in self.congress_fec_ids:
                            self.congress_committee_ids.add(pcc)
                            congress_count += 1
                    
                    count += 1
        
        self.stats['candidates_loaded'] = count
        logger.info(f"Loaded {count} candidates, {congress_count} are Congress members with committees")
    
    def process_pac_contributions(
        self,
        file_path: str,
        batch_size: int = 10000,
    ) -> List[Dict]:
        """
        Process PAC to candidate contributions (pas2.txt/itpas2.txt).
        
        Only includes contributions to current Congress members.
        """
        logger.info(f"Processing PAC contributions from {file_path}...")
        
        contributions = []
        total_rows = 0
        congress_rows = 0
        financial_rows = 0
        
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                total_rows += 1
                parts = line.strip().split('|')
                
                if len(parts) < 17:
                    continue
                
                row = dict(zip(PAS2_COLUMNS, parts[:len(PAS2_COLUMNS)]))
                cand_id = row.get('cand_id', '')
                
                # Skip if not a Congress member
                if cand_id not in self.congress_fec_ids:
                    continue
                
                congress_rows += 1
                
                # Get bioguide_id
                bioguide_id = self.fec_to_bioguide.get(cand_id)
                if not bioguide_id:
                    continue
                
                # Parse amount
                try:
                    amount = float(row.get('transaction_amt', 0))
                except (ValueError, TypeError):
                    amount = 0
                
                if amount == 0:
                    continue
                
                # Get committee info
                cmte_id = row.get('cmte_id', '')
                cmte_info = self.committees.get(cmte_id, {})
                cmte_name = cmte_info.get('name', row.get('name', ''))
                connected_org = cmte_info.get('connected_org', '')
                
                # Check if financial sector
                is_financial, match_reason = is_financial_sector(
                    cmte_name,
                    connected_org,
                    ''
                )
                
                if is_financial:
                    financial_rows += 1
                
                # Build contribution record
                contribution = {
                    'id': _generate_id(bioguide_id, cmte_id, row.get('sub_id', '')),
                    'bioguide_id': bioguide_id,
                    'committee_id': cmte_id,
                    'committee_name': cmte_name,
                    'amount': amount,
                    'contribution_date': _parse_fec_date(row.get('transaction_dt', '')),
                    'sector': 'financial' if is_financial else '',
                    'sub_sector': match_reason if is_financial else '',
                    'is_financial': is_financial,
                    'transaction_type': row.get('transaction_tp', ''),
                    'fec_cand_id': cand_id,
                    'updated_at': datetime.now().isoformat(),
                }
                contributions.append(contribution)
                
                if total_rows % 500000 == 0:
                    logger.info(f"  Processed {total_rows:,} rows, {congress_rows:,} for Congress, {len(contributions):,} kept")
        
        self.stats['pac_contributions_total'] = total_rows
        self.stats['pac_contributions_congress'] = congress_rows
        self.stats['pac_contributions_financial'] = financial_rows
        
        logger.info(f"PAC contributions: {total_rows:,} total, {congress_rows:,} to Congress, {financial_rows:,} financial sector")
        return contributions
    
    def process_individual_contributions(
        self,
        file_path: str,
        financial_only: bool = True,
    ) -> List[Dict]:
        """
        Process individual contributions (itcont.txt).
        
        Only includes contributions to current Congress member committees,
        optionally filtered to financial sector contributors only.
        """
        logger.info(f"Processing individual contributions from {file_path}...")
        logger.info(f"  Financial sector filter: {financial_only}")
        logger.info(f"  Congress committees to match: {len(self.congress_committee_ids)}")
        
        contributions = []
        total_rows = 0
        congress_rows = 0
        financial_rows = 0
        
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                total_rows += 1
                parts = line.strip().split('|')
                
                if len(parts) < 15:
                    continue
                
                row = dict(zip(ITCONT_COLUMNS, parts[:len(ITCONT_COLUMNS)]))
                cmte_id = row.get('cmte_id', '')
                
                # Skip if not a Congress member's committee
                if cmte_id not in self.congress_committee_ids:
                    continue
                
                congress_rows += 1
                
                # Get candidate ID from committee
                cand_id = self.committee_to_candidate.get(cmte_id)
                if not cand_id:
                    continue
                
                # Get bioguide_id
                bioguide_id = self.fec_to_bioguide.get(cand_id)
                if not bioguide_id:
                    continue
                
                # Parse amount
                try:
                    amount = float(row.get('transaction_amt', 0))
                except (ValueError, TypeError):
                    amount = 0
                
                if amount == 0:
                    continue
                
                # Check if financial sector contributor
                contributor_name = row.get('name', '')
                employer = row.get('employer', '')
                occupation = row.get('occupation', '')
                
                is_financial, match_reason = is_financial_sector(
                    contributor_name,
                    employer,
                    occupation
                )
                
                if is_financial:
                    financial_rows += 1
                
                # Skip non-financial if filter is enabled
                if financial_only and not is_financial:
                    continue
                
                # Build contribution record
                contribution = {
                    'id': _generate_id(bioguide_id, row.get('sub_id', '')),
                    'bioguide_id': bioguide_id,
                    'contributor_name': contributor_name,
                    'employer': employer,
                    'occupation': occupation,
                    'city': row.get('city', ''),
                    'state': row.get('state', ''),
                    'amount': amount,
                    'contribution_date': _parse_fec_date(row.get('transaction_dt', '')),
                    'sector': 'financial' if is_financial else '',
                    'is_financial': is_financial,
                    'match_reason': match_reason,
                    'fec_cand_id': cand_id,
                    'updated_at': datetime.now().isoformat(),
                }
                contributions.append(contribution)
                
                if total_rows % 1000000 == 0:
                    logger.info(f"  Processed {total_rows:,} rows, {congress_rows:,} for Congress, {len(contributions):,} kept")
        
        self.stats['individual_contributions_total'] = total_rows
        self.stats['individual_contributions_congress'] = congress_rows
        self.stats['individual_contributions_financial'] = financial_rows
        
        logger.info(f"Individual contributions: {total_rows:,} total, {congress_rows:,} to Congress, {financial_rows:,} financial")
        return contributions
    
    def write_pac_contributions_to_bq(self, contributions: List[Dict]) -> int:
        """Write PAC contributions to BigQuery using load job."""
        if not contributions:
            logger.warning("No PAC contributions to write")
            return 0
        
        table_id = f"{self.project_id}.{self.dataset_id}.official_pac_contributions"
        logger.info(f"Writing {len(contributions):,} PAC contributions to {table_id}...")
        
        # Truncate existing data
        self.client.query(f"TRUNCATE TABLE `{table_id}`").result()
        
        # Write to temp file and load (faster than streaming for large data)
        import json
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            for row in contributions:
                # Remove fields not in schema
                clean_row = {k: v for k, v in row.items() 
                            if k in ['id', 'bioguide_id', 'committee_id', 'committee_name',
                                    'amount', 'contribution_date', 'sector', 'sub_sector',
                                    'is_financial', 'updated_at']}
                f.write(json.dumps(clean_row) + '\n')
            temp_path = f.name
        
        logger.info(f"Wrote temp file, loading to BigQuery...")
        
        # Configure load job
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        )
        
        with open(temp_path, 'rb') as f:
            job = self.client.load_table_from_file(f, table_id, job_config=job_config)
        
        job.result()  # Wait for job to complete
        
        # Clean up temp file
        os.unlink(temp_path)
        
        logger.info(f"Successfully wrote {len(contributions):,} PAC contributions")
        return len(contributions)
    
    def write_individual_contributions_to_bq(self, contributions: List[Dict]) -> int:
        """Write individual contributions to BigQuery using load job."""
        if not contributions:
            logger.warning("No individual contributions to write")
            return 0
        
        table_id = f"{self.project_id}.{self.dataset_id}.official_individual_contributions"
        logger.info(f"Writing {len(contributions):,} individual contributions to {table_id}...")
        
        # Truncate existing data
        self.client.query(f"TRUNCATE TABLE `{table_id}`").result()
        
        # Write to temp file and load (faster than streaming for large data)
        import json
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            for row in contributions:
                # Remove fields not in schema
                clean_row = {k: v for k, v in row.items() 
                            if k in ['id', 'bioguide_id', 'contributor_name', 'employer',
                                    'occupation', 'city', 'state', 'amount', 
                                    'contribution_date', 'sector', 'is_financial',
                                    'match_reason', 'updated_at']}
                f.write(json.dumps(clean_row) + '\n')
            temp_path = f.name
        
        logger.info(f"Wrote temp file, loading to BigQuery...")
        
        # Configure load job
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        )
        
        with open(temp_path, 'rb') as f:
            job = self.client.load_table_from_file(f, table_id, job_config=job_config)
        
        job.result()  # Wait for job to complete
        
        # Clean up temp file
        os.unlink(temp_path)
        
        logger.info(f"Successfully wrote {len(contributions):,} individual contributions")
        return len(contributions)
    
    def update_officials_aggregates(self):
        """Update officials table with aggregated contribution totals."""
        logger.info("Updating officials table with contribution aggregates...")
        
        # Aggregate PAC contributions - SUM by committee first, then pick top 10 financial
        pac_query = f"""
        UPDATE `{self.project_id}.{self.dataset_id}.officials` o
        SET 
            pac_contributions = COALESCE(agg.total_pac, 0),
            financial_sector_pac = COALESCE(agg.financial_pac, 0),
            financial_pac_pct = CASE 
                WHEN COALESCE(agg.total_pac, 0) > 0 
                THEN ROUND(COALESCE(agg.financial_pac, 0) / agg.total_pac * 100, 1)
                ELSE 0 
            END,
            top_financial_pacs = agg.top_pacs,
            has_financial_activity = CASE WHEN agg.financial_pac > 0 THEN TRUE ELSE o.has_financial_activity END
        FROM (
            SELECT 
                all_pacs.bioguide_id,
                all_pacs.total_pac,
                all_pacs.financial_pac,
                fin_pacs.top_pacs
            FROM (
                -- Get totals from ALL PACs (not just financial)
                SELECT 
                    bioguide_id,
                    SUM(total_amount) as total_pac,
                    SUM(CASE WHEN is_financial THEN total_amount ELSE 0 END) as financial_pac
                FROM (
                    SELECT 
                        bioguide_id,
                        committee_name,
                        SUM(amount) as total_amount,
                        MAX(is_financial) as is_financial
                    FROM `{self.project_id}.{self.dataset_id}.official_pac_contributions`
                    GROUP BY bioguide_id, committee_name
                )
                GROUP BY bioguide_id
            ) all_pacs
            LEFT JOIN (
                -- Get top 10 FINANCIAL PACs only
                SELECT 
                    bioguide_id,
                    ARRAY_AGG(
                        STRUCT(committee_name as name, total_amount as amount, sector)
                        ORDER BY total_amount DESC
                        LIMIT 10
                    ) as top_pacs
                FROM (
                    SELECT 
                        bioguide_id,
                        committee_name,
                        SUM(amount) as total_amount,
                        MAX(sector) as sector
                    FROM `{self.project_id}.{self.dataset_id}.official_pac_contributions`
                    WHERE is_financial = TRUE
                    GROUP BY bioguide_id, committee_name
                )
                GROUP BY bioguide_id
            ) fin_pacs ON all_pacs.bioguide_id = fin_pacs.bioguide_id
        ) agg
        WHERE o.bioguide_id = agg.bioguide_id
        """
        
        try:
            job = self.client.query(pac_query)
            job.result()  # Wait for completion
            logger.info(f"Updated PAC contribution aggregates: {job.num_dml_affected_rows} rows")
        except Exception as e:
            logger.error(f"Failed to update PAC aggregates: {e}")
        
        # Aggregate individual contributions - SUM by employer first, then pick top 10 financial
        individual_query = f"""
        UPDATE `{self.project_id}.{self.dataset_id}.officials` o
        SET 
            individual_contributions_total = COALESCE(agg.total_individual, 0),
            individual_financial_total = COALESCE(agg.financial_individual, 0),
            individual_financial_pct = CASE 
                WHEN COALESCE(agg.total_individual, 0) > 0 
                THEN ROUND(COALESCE(agg.financial_individual, 0) / agg.total_individual * 100, 1)
                ELSE 0 
            END,
            top_individual_financial = agg.top_employers
        FROM (
            SELECT 
                all_indiv.bioguide_id,
                all_indiv.total_individual,
                all_indiv.financial_individual,
                fin_indiv.top_employers
            FROM (
                -- Get totals from ALL individual contributions (not just financial)
                SELECT 
                    bioguide_id,
                    SUM(total_amount) as total_individual,
                    SUM(CASE WHEN is_financial THEN total_amount ELSE 0 END) as financial_individual
                FROM (
                    SELECT 
                        bioguide_id,
                        COALESCE(NULLIF(TRIM(employer), ''), 'Unknown') as employer,
                        SUM(amount) as total_amount,
                        MAX(is_financial) as is_financial
                    FROM `{self.project_id}.{self.dataset_id}.official_individual_contributions`
                    WHERE employer IS NOT NULL 
                      AND TRIM(employer) != ''
                      AND UPPER(employer) NOT IN ('SELF', 'SELF EMPLOYED', 'SELF-EMPLOYED', 'RETIRED', 'NOT EMPLOYED', 'N/A', 'NONE', 'HOMEMAKER')
                    GROUP BY bioguide_id, employer
                )
                GROUP BY bioguide_id
            ) all_indiv
            LEFT JOIN (
                -- Get top 10 FINANCIAL employers only
                SELECT 
                    bioguide_id,
                    ARRAY_AGG(
                        STRUCT(
                            employer as name,
                            employer as employer,
                            '' as occupation,
                            total_amount as amount,
                            '' as date,
                            '' as city,
                            '' as state
                        )
                        ORDER BY total_amount DESC
                        LIMIT 10
                    ) as top_employers
                FROM (
                    SELECT 
                        bioguide_id,
                        COALESCE(NULLIF(TRIM(employer), ''), 'Unknown') as employer,
                        SUM(amount) as total_amount
                    FROM `{self.project_id}.{self.dataset_id}.official_individual_contributions`
                    WHERE is_financial = TRUE
                      AND employer IS NOT NULL 
                      AND TRIM(employer) != ''
                      AND UPPER(employer) NOT IN ('SELF', 'SELF EMPLOYED', 'SELF-EMPLOYED', 'RETIRED', 'NOT EMPLOYED', 'N/A', 'NONE', 'HOMEMAKER')
                    GROUP BY bioguide_id, employer
                )
                GROUP BY bioguide_id
            ) fin_indiv ON all_indiv.bioguide_id = fin_indiv.bioguide_id
        ) agg
        WHERE o.bioguide_id = agg.bioguide_id
        """
        
        try:
            job = self.client.query(individual_query)
            job.result()  # Wait for completion
            logger.info(f"Updated individual contribution aggregates: {job.num_dml_affected_rows} rows")
        except Exception as e:
            logger.error(f"Failed to update individual aggregates: {e}")
    
    def run(
        self,
        data_dir: str,
        cycles: List[str] = None,
    ):
        """
        Run the full bulk load process.
        
        Args:
            data_dir: Directory containing unzipped FEC files
            cycles: Election cycles to load (e.g., ['2024', '2026'])
        """
        cycles = cycles or ['2024', '2026']
        data_path = Path(data_dir)
        
        logger.info("=" * 70)
        logger.info("FEC BULK DATA LOAD")
        logger.info(f"Data directory: {data_path}")
        logger.info(f"Cycles: {cycles}")
        logger.info("=" * 70)
        
        # Step 1: Load crosswalk
        self.load_crosswalk()
        
        # Step 2: Load reference files for each cycle
        for cycle in cycles:
            suffix = cycle[-2:]  # '24' or '26'
            
            # Committee master
            cm_file = data_path / f"cm{suffix}" / "cm.txt"
            if not cm_file.exists():
                cm_file = data_path / "cm.txt"
            if cm_file.exists():
                self.load_committee_master(str(cm_file))
            else:
                logger.warning(f"Committee file not found for cycle {cycle}")
            
            # Candidate master
            cn_file = data_path / f"cn{suffix}" / "cn.txt"
            if not cn_file.exists():
                cn_file = data_path / "cn.txt"
            if cn_file.exists():
                self.load_candidate_master(str(cn_file))
            else:
                logger.warning(f"Candidate file not found for cycle {cycle}")
        
        # Step 3: Process PAC contributions
        all_pac_contributions = []
        for cycle in cycles:
            suffix = cycle[-2:]
            pas2_file = data_path / f"pas2{suffix}" / "itpas2.txt"
            if not pas2_file.exists():
                pas2_file = data_path / "itpas2.txt"
            if pas2_file.exists():
                contributions = self.process_pac_contributions(str(pas2_file))
                all_pac_contributions.extend(contributions)
                logger.info(f"Cycle {cycle}: {len(contributions):,} PAC contributions")
        
        # Step 4: Process individual contributions  
        all_individual_contributions = []
        for cycle in cycles:
            suffix = cycle[-2:]
            itcont_file = data_path / f"indiv{suffix}" / "itcont.txt"
            if not itcont_file.exists():
                itcont_file = data_path / "itcont.txt"
            if itcont_file.exists():
                contributions = self.process_individual_contributions(
                    str(itcont_file),
                    financial_only=False  # Include ALL contributions for proper percentage calculation
                )
                all_individual_contributions.extend(contributions)
                logger.info(f"Cycle {cycle}: {len(contributions):,} individual contributions")
        
        # Step 5: Write to BigQuery
        logger.info("\n" + "=" * 70)
        logger.info("WRITING TO BIGQUERY")
        logger.info("=" * 70)
        
        pac_count = self.write_pac_contributions_to_bq(all_pac_contributions)
        indiv_count = self.write_individual_contributions_to_bq(all_individual_contributions)
        
        # Step 6: Update aggregates
        self.update_officials_aggregates()
        
        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("BULK LOAD COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Congress members mapped: {self.stats['congress_members_mapped']}")
        logger.info(f"Committees loaded: {self.stats['committees_loaded']}")
        logger.info(f"Candidates loaded: {self.stats['candidates_loaded']}")
        logger.info(f"PAC contributions written: {pac_count:,}")
        logger.info(f"Individual contributions written: {indiv_count:,}")
        
        return {
            'pac_contributions': pac_count,
            'individual_contributions': indiv_count,
            'stats': self.stats,
        }
    
    def reload_individual_contributions(
        self, 
        data_dir: str,
        cycles: List[str] = None,
        financial_only: bool = False,
    ):
        """
        Reload just individual contributions (faster than full bulk load).
        
        Args:
            data_dir: Directory containing extracted FEC files
            cycles: List of cycles to process (e.g., ['2024', '2026'])
            financial_only: If True, only load financial sector contributions
        """
        cycles = cycles or ['2024', '2026']
        data_path = Path(data_dir)
        
        logger.info("=" * 70)
        logger.info("RELOAD INDIVIDUAL CONTRIBUTIONS")
        logger.info(f"Data directory: {data_path}")
        logger.info(f"Cycles: {cycles}")
        logger.info(f"Financial only: {financial_only}")
        logger.info("=" * 70)
        
        # Step 1: Load crosswalk (needed for bioguide mapping)
        self.load_crosswalk()
        
        # Step 2: Load reference files for each cycle (needed for committee->candidate mapping)
        for cycle in cycles:
            suffix = cycle[-2:]
            
            # Committee master
            cm_file = data_path / f"cm{suffix}" / "cm.txt"
            if not cm_file.exists():
                cm_file = data_path / "cm.txt"
            if cm_file.exists():
                self.load_committee_master(str(cm_file))
            
            # Candidate master
            cn_file = data_path / f"cn{suffix}" / "cn.txt"
            if not cn_file.exists():
                cn_file = data_path / "cn.txt"
            if cn_file.exists():
                self.load_candidate_master(str(cn_file))
        
        # Step 3: Process individual contributions
        all_individual_contributions = []
        for cycle in cycles:
            suffix = cycle[-2:]
            itcont_file = data_path / f"indiv{suffix}" / "itcont.txt"
            if not itcont_file.exists():
                itcont_file = data_path / "itcont.txt"
            if itcont_file.exists():
                logger.info(f"\nProcessing cycle {cycle}...")
                contributions = self.process_individual_contributions(
                    str(itcont_file),
                    financial_only=financial_only
                )
                all_individual_contributions.extend(contributions)
                logger.info(f"Cycle {cycle}: {len(contributions):,} individual contributions")
            else:
                logger.warning(f"Individual contributions file not found for cycle {cycle}")
        
        # Step 4: Write to BigQuery
        logger.info("\n" + "=" * 70)
        logger.info("WRITING TO BIGQUERY")
        logger.info("=" * 70)
        
        indiv_count = self.write_individual_contributions_to_bq(all_individual_contributions)
        
        # Step 5: Update aggregates
        self.update_officials_aggregates()
        
        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("RELOAD COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Individual contributions written: {indiv_count:,}")
        
        return indiv_count


def extract_zip_files(downloads_dir: str, output_dir: str, cycles: List[str] = None):
    """Extract FEC zip files to output directory."""
    cycles = cycles or ['24', '26']
    downloads = Path(downloads_dir)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    
    files_to_extract = []
    for cycle in cycles:
        files_to_extract.extend([
            f'cm{cycle}.zip',
            f'cn{cycle}.zip', 
            f'pas2{cycle}.zip',
            f'indiv{cycle}.zip',
        ])
    
    for zip_name in files_to_extract:
        zip_path = downloads / zip_name
        if zip_path.exists():
            logger.info(f"Extracting {zip_name}...")
            # Extract to subdirectory named after zip (without .zip)
            extract_dir = output / zip_name.replace('.zip', '')
            extract_dir.mkdir(exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(extract_dir)
            logger.info(f"  Extracted to {extract_dir}")
        else:
            logger.warning(f"File not found: {zip_path}")


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='Load FEC bulk data into BigQuery')
    parser.add_argument('--downloads-dir', default='/Users/jadedlebi/Downloads',
                        help='Directory containing FEC zip files')
    parser.add_argument('--data-dir', default='/tmp/fec_data',
                        help='Directory for extracted files')
    parser.add_argument('--cycles', nargs='+', default=['2024', '2026'],
                        help='Election cycles to load')
    parser.add_argument('--extract-only', action='store_true',
                        help='Only extract zip files, do not load')
    parser.add_argument('--skip-extract', action='store_true',
                        help='Skip extraction, assume files are already extracted')
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Convert cycles to 2-digit suffixes
    cycle_suffixes = [c[-2:] for c in args.cycles]
    
    # Extract zip files
    if not args.skip_extract:
        extract_zip_files(args.downloads_dir, args.data_dir, cycle_suffixes)
    
    if args.extract_only:
        logger.info("Extraction complete (--extract-only specified)")
        return
    
    # Run bulk load
    loader = FECBulkLoader()
    results = loader.run(args.data_dir, args.cycles)
    
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"PAC contributions loaded: {results['pac_contributions']:,}")
    print(f"Individual contributions loaded: {results['individual_contributions']:,}")


if __name__ == '__main__':
    main()
