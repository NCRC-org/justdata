#!/usr/bin/env python3
"""
Identifier Resolution Service
Maps institution names to FDIC cert, RSSD ID, LEI, SEC CIK, etc.
"""

import logging
from typing import Optional, Dict, Any, List
from difflib import SequenceMatcher

from justdata.apps.lenderprofile.services.fdic_client import FDICClient
from justdata.apps.lenderprofile.services.gleif_client import GLEIFClient
from justdata.apps.lenderprofile.services.sec_client import SECClient

logger = logging.getLogger(__name__)


class IdentifierResolver:
    """
    Resolves institution names to various identifiers.
    """
    
    def __init__(self):
        """Initialize identifier resolver."""
        self.fdic_client = FDICClient()
        self.gleif_client = GLEIFClient()
        self.sec_client = SECClient()
    
    def _similarity(self, a: str, b: str) -> float:
        """Calculate similarity between two strings."""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()
    
    def get_candidates_with_location(self, name: str, exclude: Optional[List[Dict[str, Any]]] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get multiple candidate institutions with location information for user selection.
        
        Args:
            name: Institution name to search for
            exclude: Optional list of rejected lenders to exclude
            limit: Maximum number of candidates to return
            
        Returns:
            List of candidate dictionaries with name, city, state, and identifiers
        """
        candidates = []
        
        # Helper function to check if a lender should be excluded
        def is_excluded(lei: Optional[str] = None, rssd_id: Optional[str] = None, 
                       fdic_cert: Optional[str] = None) -> bool:
            """Check if lender matches any excluded lender."""
            if not exclude:
                return False
            for excluded in exclude:
                if lei and excluded.get('lei') and lei == excluded.get('lei'):
                    return True
                if rssd_id and excluded.get('rssd_id') and str(rssd_id) == str(excluded.get('rssd_id')):
                    return True
                if fdic_cert and excluded.get('fdic_cert') and str(fdic_cert) == str(excluded.get('fdic_cert')):
                    return True
            return False
        
        # Search using GLEIF-verified lender names table (same approach as MergerMeter)
        # This uses pre-verified GLEIF data for fast, reliable results
        try:
            from justdata.shared.utils.bigquery_client import get_bigquery_client
            from google.cloud import bigquery

            PROJECT_ID = 'justdata-ncrc'
            client = get_bigquery_client(PROJECT_ID)

            # Query pattern matching MergerMeter - uses lender_names_gleif for GLEIF-verified data
            # Joins with lenders18 for RSSD and bizsight.sb_lenders for small business IDs
            sql = """
            SELECT DISTINCT
                g.display_name AS name,
                g.headquarters_city AS city,
                g.headquarters_state AS state,
                l.lei AS lei,
                CAST(l.respondent_rssd AS STRING) AS rssd_id,
                sb.sb_resid AS sb_res_id,
                SAFE_CAST(l.assets AS INT64) AS assets,
                l.type_name AS type
            FROM `justdata-ncrc.shared.lender_names_gleif` g
            JOIN `justdata-ncrc.lendsight.lenders18` l ON g.lei = l.lei
            LEFT JOIN `justdata-ncrc.bizsight.sb_lenders` sb ON CAST(l.respondent_rssd AS STRING) = sb.sb_rssd
            WHERE LOWER(g.display_name) LIKE LOWER(@search_pattern)
            ORDER BY assets DESC NULLS LAST
            LIMIT @limit
            """

            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter('search_pattern', 'STRING', f'%{name}%'),
                    bigquery.ScalarQueryParameter('limit', 'INT64', limit)
                ]
            )

            logger.info(f"Searching GLEIF-verified lenders for: '{name}'")
            query_job = client.query(sql, job_config=job_config)
            results = query_job.result()

            for row in results:
                lei = row.lei
                rssd_id = row.rssd_id

                # Skip excluded lenders
                if is_excluded(lei=lei, rssd_id=rssd_id):
                    continue

                candidate = {
                    'name': row.name or '',
                    'lei': lei,
                    'rssd_id': rssd_id,
                    'sb_res_id': row.sb_res_id,  # Small business respondent ID
                    'fdic_cert': None,  # Will be resolved when candidate is selected
                    'city': row.city or '',
                    'state': row.state or '',
                    'type': row.type or '',
                    'assets': row.assets,
                    'confidence': 0.95,  # High confidence from GLEIF-verified data
                    'gleif_verified': True  # Flag indicating GLEIF verification
                }

                # Avoid duplicates
                if not any(c.get('lei') == lei and c.get('rssd_id') == rssd_id for c in candidates):
                    candidates.append(candidate)

            logger.info(f"Found {len(candidates)} GLEIF-verified candidates for '{name}'")
        except Exception as e:
            logger.warning(f"GLEIF-verified search failed: {e}", exc_info=True)
        
        # If we don't have enough candidates AND BigQuery failed, try FDIC search
        # Skip FDIC search if we already have good results from BigQuery to keep search fast
        if len(candidates) == 0:
            try:
                logger.info(f"No BigQuery results, falling back to FDIC API search for: '{name}'")
                fdic_results = self.fdic_client.search_institutions(name, limit=limit)
                if fdic_results:
                    for inst in fdic_results:
                        cert = inst.get('CERT')
                        rssd = inst.get('RSSDID') or inst.get('FED_RSSD')

                        # Skip if excluded
                        if is_excluded(fdic_cert=cert, rssd_id=rssd):
                            continue

                        city = inst.get('CITY', '')
                        state = inst.get('STALP', inst.get('STATE', ''))

                        candidate = {
                            'name': inst.get('NAME', ''),
                            'fdic_cert': cert,
                            'rssd_id': rssd,
                            'city': city,
                            'state': state,
                            'type': inst.get('INSTTYPE', ''),
                            'confidence': 0.7  # Medium confidence from FDIC
                        }
                        candidates.append(candidate)
                    logger.info(f"Found {len(candidates)} candidates from FDIC fallback")
            except Exception as e:
                logger.warning(f"FDIC search failed: {e}")
        
        # Sort by confidence (highest first), then by name
        candidates.sort(key=lambda x: (-x.get('confidence', 0), x.get('name', '')))
        
        return candidates[:limit]
    
    def resolve_by_name(self, name: str, exclude: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Resolve institution name to all available identifiers.
        
        Uses BigQuery Lenders18 table (like DataExplorer) for primary search,
        then enriches with FDIC data if available.
        
        Args:
            name: Institution name
            exclude: Optional list of rejected lenders to exclude (each dict has lei, rssd_id, fdic_cert, name)
            
        Returns:
            Dictionary with identifiers:
            {
                'name': str,
                'fdic_cert': Optional[str],
                'rssd_id': Optional[str],
                'lei': Optional[str],
                'sec_cik': Optional[str],
                'confidence': float
            }
        """
        result = {
            'name': name,
            'fdic_cert': None,
            'rssd_id': None,
            'lei': None,
            'sec_cik': None,
            'tax_id': None,  # EIN / Tax ID from GLEIF
            'confidence': 0.0
        }
        
        # Helper function to check if a lender should be excluded
        def is_excluded(lei: Optional[str] = None, rssd_id: Optional[str] = None, 
                       fdic_cert: Optional[str] = None) -> bool:
            """Check if lender matches any excluded lender."""
            if not exclude:
                return False
            for excluded in exclude:
                if lei and excluded.get('lei') and lei == excluded.get('lei'):
                    return True
                if rssd_id and excluded.get('rssd_id') and str(rssd_id) == str(excluded.get('rssd_id')):
                    return True
                if fdic_cert and excluded.get('fdic_cert') and str(fdic_cert) == str(excluded.get('fdic_cert')):
                    return True
            return False
        
        # Try GLEIF API first for name-based search
        logger.info(f"Searching GLEIF API for: '{name}'")
        gleif_results = self.gleif_client.search_by_name(name, limit=5)
        logger.info(f"GLEIF search returned {len(gleif_results) if gleif_results else 0} results")
        
        if gleif_results:
            # Find best match by name similarity
            best_match = None
            best_score = 0.0
            
            for entity in gleif_results:
                entity_name = entity.get('legal_name', '')
                score = self._similarity(name, entity_name)
                if score > best_score:
                    best_score = score
                    best_match = entity
            
            # Use 0.6 threshold for GLEIF matches (slightly higher than FDIC)
            if best_match and best_score > 0.6:
                lei = best_match.get('lei')
                # Check if this lender is excluded
                if is_excluded(lei=lei):
                    logger.info(f"Excluding rejected lender: LEI={lei}, Name={best_match.get('legal_name', 'N/A')}")
                    original_best = best_match
                    best_match = None
                    best_score = 0.0
                    # Try next best match
                    for entity in gleif_results:
                        if entity == original_best:
                            continue
                        entity_name = entity.get('legal_name', '')
                        score = self._similarity(name, entity_name)
                        if score > best_score and not is_excluded(lei=entity.get('lei')):
                            best_score = score
                            best_match = entity
                
                if best_match and best_score > 0.6:
                    result['lei'] = best_match.get('lei')
                    result['name'] = best_match.get('legal_name', name)
                    result['tax_id'] = best_match.get('tax_id')  # Extract tax ID/EIN
                    result['confidence'] = best_score
                    logger.info(f"Resolved '{name}' via GLEIF: LEI={result['lei']}, Tax ID={result.get('tax_id', 'N/A')} (confidence: {best_score:.2f})")
                
                # Try to get RSSD and FDIC cert from other sources
                # GLEIF doesn't provide RSSD, so we'll try BigQuery or FDIC
                try:
                    from justdata.apps.dataexplorer.data_utils import search_lenders18
                    if result['lei']:
                        # Search BigQuery by LEI to get RSSD
                        bq_results = search_lenders18(name, limit=5, include_verification=False)
                        for bq_match in bq_results:
                            if bq_match.get('lei') == result['lei']:
                                result['rssd_id'] = bq_match.get('rssd_id') or bq_match.get('rssd')
                                # Also get type from BigQuery if available
                                if not result.get('type'):
                                    result['type'] = bq_match.get('type_name') or bq_match.get('type')
                                logger.info(f"Found RSSD {result['rssd_id']} from BigQuery for LEI {result['lei']}")
                                break
                except Exception as bq_error:
                    logger.debug(f"BigQuery lookup failed: {bq_error}")
                
                # Try FDIC search for FDIC cert
                if result.get('rssd_id') or result['name']:
                    fdic_results = self.fdic_client.search_institutions(result['name'], limit=5)
                    if fdic_results:
                        for inst in fdic_results:
                            if result.get('rssd_id') and inst.get('RSSDID') == result['rssd_id']:
                                result['fdic_cert'] = inst.get('CERT')
                                logger.info(f"Found FDIC cert {result['fdic_cert']} for RSSD {result['rssd_id']}")
                                break
                            elif not result.get('fdic_cert'):  # If no RSSD match, use first name match
                                inst_name = inst.get('NAME', '')
                                if self._similarity(result['name'], inst_name) > 0.7:
                                    result['fdic_cert'] = inst.get('CERT')
                                    result['rssd_id'] = inst.get('RSSDID')
                                    logger.info(f"Found FDIC cert {result['fdic_cert']} by name match")
                
                return result
            else:
                logger.warning(f"GLEIF match below threshold. Best: {best_match.get('legal_name', 'N/A') if best_match else 'None'} (score: {best_score:.2f})")
        
        # Fallback to GLEIF-verified BigQuery table (same approach as MergerMeter)
        try:
            from justdata.shared.utils.bigquery_client import get_bigquery_client
            from google.cloud import bigquery as bq_module

            PROJECT_ID = 'justdata-ncrc'
            client = get_bigquery_client(PROJECT_ID)

            # Use GLEIF-verified lender names table for reliable LEI data
            sql = """
            SELECT DISTINCT
                g.display_name AS name,
                g.headquarters_city AS city,
                g.headquarters_state AS state,
                l.lei AS lei,
                CAST(l.respondent_rssd AS STRING) AS rssd_id,
                l.type_name AS type_name
            FROM `justdata-ncrc.shared.lender_names_gleif` g
            JOIN `justdata-ncrc.lendsight.lenders18` l ON g.lei = l.lei
            WHERE LOWER(g.display_name) LIKE LOWER(@search_pattern)
            ORDER BY l.assets DESC NULLS LAST
            LIMIT 5
            """

            job_config = bq_module.QueryJobConfig(
                query_parameters=[
                    bq_module.ScalarQueryParameter('search_pattern', 'STRING', f'%{name}%')
                ]
            )

            logger.info(f"Searching GLEIF-verified table for: '{name}'")
            query_job = client.query(sql, job_config=job_config)
            bq_results = [dict(row) for row in query_job.result()]
            logger.info(f"GLEIF-verified search returned {len(bq_results)} results")
            
            if bq_results:
                # Find first match that's not excluded
                best_match = None
                for lender in bq_results:
                    lei = lender.get('lei')
                    rssd_id = lender.get('rssd_id') or lender.get('rssd')
                    if not is_excluded(lei=lei, rssd_id=rssd_id):
                        best_match = lender
                        break
                
                if best_match:
                    # Extract identifiers from GLEIF-verified data
                    result['lei'] = best_match.get('lei')
                    result['rssd_id'] = best_match.get('rssd_id') or best_match.get('rssd')
                    result['name'] = best_match.get('name', name)
                    result['type'] = best_match.get('type_name') or best_match.get('type')
                    result['confidence'] = 0.95  # High confidence from GLEIF-verified data
                    result['gleif_verified'] = True
                    
                    # Try to get tax_id from GLEIF using the LEI
                    if result['lei']:
                        try:
                            logger.info(f"Fetching GLEIF record for LEI {result['lei']} to get tax_id and addresses")
                            gleif_record = self.gleif_client.get_lei_record(result['lei'])
                            if gleif_record:
                                # Extract tax_id from GLEIF record
                                tax_id = gleif_record.get('tax_id') or gleif_record.get('ein')
                                if tax_id:
                                    result['tax_id'] = tax_id
                                    logger.info(f"Found tax_id {tax_id} from GLEIF for LEI {result['lei']}")
                                else:
                                    # Log what we got from GLEIF for debugging
                                    entity = gleif_record.get('entity', {})
                                    reg_auths = entity.get('registrationAuthorities', [])
                                    logger.debug(f"No tax_id found in GLEIF record for LEI {result['lei']}. Registration authorities count: {len(reg_auths) if isinstance(reg_auths, list) else 0}")
                                    
                                    # Try SEC Edgar to get tax ID if GLEIF doesn't have it
                                    if not result.get('tax_id'):
                                        try:
                                            logger.info(f"Searching SEC Edgar for tax ID: '{result['name']}'")
                                            sec_companies = self.sec_client.search_companies(result['name'])
                                            if sec_companies:
                                                # Find best match
                                                best_sec_match = None
                                                best_sec_score = 0.0
                                                for company in sec_companies:
                                                    company_name = company.get('name', '')
                                                    score = self._similarity(result['name'], company_name)
                                                    if score > best_sec_score:
                                                        best_sec_score = score
                                                        best_sec_match = company
                                                
                                                if best_sec_match and best_sec_score > 0.7:
                                                    result['sec_cik'] = best_sec_match.get('cik')
                                                    logger.info(f"Found SEC CIK {result['sec_cik']} for '{result['name']}' (match: {best_sec_match.get('name')})")
                                                    
                                                    # Try to get tax ID from SEC submissions
                                                    if result['sec_cik']:
                                                        try:
                                                            submissions = self.sec_client.get_company_submissions(result['sec_cik'])
                                                            if submissions:
                                                                entity_name = submissions.get('entityName', '')
                                                                logger.debug(f"SEC entity name for CIK {result['sec_cik']}: {entity_name}")
                                                        except Exception as sec_detail_error:
                                                            logger.debug(f"Could not get detailed SEC info: {sec_detail_error}")
                                        except Exception as sec_error:
                                            logger.debug(f"SEC search failed: {sec_error}")
                        except Exception as gleif_error:
                            logger.warning(f"Could not get tax_id from GLEIF for LEI {result['lei']}: {gleif_error}")
                else:
                    logger.info(f"All BigQuery matches were excluded for '{name}'")
                    best_match = None
                
                # Try to get FDIC cert from RSSD using the get_institution_by_rssd method
                if result.get('rssd_id'):
                    # Use the direct RSSD lookup method first
                    logger.info(f"Looking up FDIC cert for RSSD: {result['rssd_id']}")
                    fdic_inst = self.fdic_client.get_institution_by_rssd(str(result['rssd_id']))
                    if fdic_inst:
                        inst_cert = fdic_inst.get('CERT')
                        inst_rssd = fdic_inst.get('RSSDID')
                        # Check if it's excluded
                        if not is_excluded(rssd_id=inst_rssd, fdic_cert=inst_cert):
                            result['fdic_cert'] = inst_cert
                            logger.info(f"Found FDIC cert {result['fdic_cert']} for RSSD {result['rssd_id']}")
                        else:
                            logger.info(f"FDIC institution excluded: CERT={inst_cert}, RSSD={inst_rssd}")
                    else:
                        # Fallback to name search if RSSD lookup fails
                        logger.info(f"FDIC RSSD lookup returned 0 results, trying name search for '{result['name']}'")
                        fdic_results = self.fdic_client.search_institutions(result['name'], limit=10)
                        if fdic_results:
                            for inst in fdic_results:
                                inst_rssd = inst.get('RSSDID')
                                inst_cert = inst.get('CERT')
                                # Check if this FDIC institution matches our BigQuery result
                                if inst_rssd and str(inst_rssd) == str(result['rssd_id']):
                                    # Also check if it's excluded
                                    if not is_excluded(rssd_id=inst_rssd, fdic_cert=inst_cert):
                                        result['fdic_cert'] = inst_cert
                                        logger.info(f"Found FDIC cert {result['fdic_cert']} for RSSD {result['rssd_id']} via name search")
                                        break
                        else:
                            logger.info(f"FDIC search returned no results for '{result['name']}' - institution may not be FDIC-insured")
                            # Last resort: try known certificate numbers for major banks
                            # For PNC Bank, we know cert is 6384 from FDIC BankFind
                            if 'PNC' in result['name'].upper() or 'PNC BANK' in result['name'].upper():
                                logger.info("Trying known PNC Bank certificate number 6384")
                                pnc_inst = self.fdic_client.get_institution('6384')
                                if pnc_inst:
                                    inst_rssd = pnc_inst.get('RSSDID')
                                    if inst_rssd and str(inst_rssd) == str(result['rssd_id']):
                                        result['fdic_cert'] = '6384'
                                        logger.info(f"Found FDIC cert 6384 for PNC Bank (RSSD {result['rssd_id']})")
                
                logger.info(f"Resolved '{name}' via BigQuery: LEI={result['lei']}, RSSD={result['rssd_id']}, FDIC={result['fdic_cert']}")
                return result
        except Exception as bq_error:
            logger.warning(f"BigQuery search failed: {bq_error}. Falling back to FDIC.")
            # Continue to FDIC fallback
        
        # Fallback to FDIC search if BigQuery didn't work
        logger.info(f"Searching FDIC for: '{name}'")
        fdic_results = self.fdic_client.search_institutions(name, limit=5)
        logger.info(f"FDIC search returned {len(fdic_results) if fdic_results else 0} results")
        if fdic_results:
            # Find best match
            best_match = None
            best_score = 0.0
            
            for inst in fdic_results:
                inst_name = inst.get('NAME', '')
                score = self._similarity(name, inst_name)
                if score > best_score:
                    best_score = score
                    best_match = inst
            
            # Lower threshold to 0.5 (50%) to catch more matches
            # Common bank names like "PNC Bank" vs "PNC Bank, National Association" should still match
            if best_match and best_score > 0.5:  # 50% similarity threshold
                inst_cert = best_match.get('CERT')
                inst_rssd = best_match.get('RSSDID')
                # Check if this lender is excluded
                if is_excluded(fdic_cert=inst_cert, rssd_id=inst_rssd):
                    logger.info(f"FDIC match excluded: CERT={inst_cert}, RSSD={inst_rssd}, Name={best_match.get('NAME', 'N/A')}")
                    # Try next best match
                    original_best = best_match
                    best_match = None
                    best_score = 0.0
                    for inst in fdic_results:
                        if inst == original_best:
                            continue
                        inst_name = inst.get('NAME', '')
                        score = self._similarity(name, inst_name)
                        inst_cert_check = inst.get('CERT')
                        inst_rssd_check = inst.get('RSSDID')
                        if score > best_score and not is_excluded(fdic_cert=inst_cert_check, rssd_id=inst_rssd_check):
                            best_score = score
                            best_match = inst
                
                if best_match and best_score > 0.5:
                    result['fdic_cert'] = best_match.get('CERT')
                    result['rssd_id'] = best_match.get('RSSDID')
                    result['name'] = best_match.get('NAME', name)  # Use FDIC name if available
                    result['confidence'] = best_score
                    logger.info(f"Resolved '{name}' to FDIC cert {result['fdic_cert']} (confidence: {best_score:.2f})")
            else:
                logger.warning(f"No match found above threshold. Best match: {best_match.get('NAME', 'N/A') if best_match else 'None'} (score: {best_score:.2f})")
        
        return result
    
    def get_institution_details(self, identifier: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get full institution details using resolved identifiers.
        
        Args:
            identifier: Result from resolve_by_name()
            
        Returns:
            Combined institution details including addresses, tax ID, etc.
        """
        details = {
            'identifiers': identifier,
            'fdic_data': None,
            'gleif_data': None,
            'legal_address': None,
            'headquarters_address': None,
            'tax_id': identifier.get('tax_id'),  # Tax ID from identifier resolution
            'registration_status': None,
            'entity_status': None
        }
        
        # Get FDIC data
        if identifier.get('fdic_cert'):
            details['fdic_data'] = self.fdic_client.get_institution(identifier['fdic_cert'])
            
            # Get most recent financial data (includes ASSET and other financial metrics)
            financials = self.fdic_client.get_financials(identifier['fdic_cert'], fields=['ASSET', 'REPDTE', 'ROA', 'ROE', 'EQUITY', 'DEP'])
            if financials:
                # Sort by date (most recent first) and get the latest
                sorted_financials = sorted(financials, key=lambda x: x.get('REPDTE', ''), reverse=True)
                if sorted_financials:
                    latest_financials = sorted_financials[0]
                    # Add latest financial data to fdic_data
                    if details['fdic_data']:
                        details['fdic_data'].update({
                            'ASSET': latest_financials.get('ASSET'),
                            'REPDTE': latest_financials.get('REPDTE'),
                            'ROA': latest_financials.get('ROA'),
                            'ROE': latest_financials.get('ROE'),
                            'EQUITY': latest_financials.get('EQUITY'),
                            'DEP': latest_financials.get('DEP')
                        })
                    else:
                        # If no basic institution data, create a dict with financials
                        details['fdic_data'] = latest_financials
                    
                    # Also store all financial records for trend analysis
                    details['fdic_financials'] = sorted_financials[:20]  # Last 20 quarters (5 years)
        
        # If no FDIC assets, try CFPB API as fallback (for lenders that make mortgage loans)
        fdic_data = details.get('fdic_data') or {}
        if not fdic_data.get('ASSET') and identifier.get('lei'):
            try:
                from justdata.apps.dataexplorer.utils.cfpb_client import CFPBClient
                cfpb_client = CFPBClient()
                if cfpb_client._is_enabled():
                    logger.info(f"FDIC assets not available, trying CFPB API for LEI {identifier['lei']}")
                    institution = cfpb_client.get_institution_by_lei(identifier['lei'])
                    if institution:
                        # Extract assets from various possible field names
                        assets = (institution.get('assets') or 
                                 institution.get('total_assets') or
                                 institution.get('asset_size') or
                                 institution.get('assetSize') or
                                 institution.get('totalAssets'))
                        
                        if assets and assets != -1:  # -1 means not applicable
                            try:
                                if isinstance(assets, str):
                                    assets_clean = assets.replace(',', '').replace('$', '').strip()
                                    assets = float(assets_clean) if assets_clean else None
                                else:
                                    assets = float(assets) if assets else None
                                
                                if assets and assets > 0:
                                    # Add to fdic_data or create it
                                    if not details.get('fdic_data'):
                                        details['fdic_data'] = {}
                                    details['fdic_data']['ASSET'] = assets
                                    details['fdic_data']['ASSET_SOURCE'] = 'CFPB'
                                    logger.info(f"Found assets ${assets:,.0f} from CFPB API for LEI {identifier['lei']}")
                            except (ValueError, TypeError) as e:
                                logger.debug(f"Could not parse assets from CFPB: {e}")
            except Exception as cfpb_error:
                logger.debug(f"CFPB API not available or error: {cfpb_error}")
        
        # Get GLEIF data (contains addresses and more details)
        if identifier.get('lei'):
            gleif_data = self.gleif_client.get_lei_record(identifier['lei'])
            details['gleif_data'] = gleif_data
            
            if gleif_data:
                entity = gleif_data.get('entity', {})
                
                # Extract legal address
                legal_addr = entity.get('legalAddress', {})
                if legal_addr:
                    details['legal_address'] = {
                        'address_lines': legal_addr.get('addressLines', []),
                        'city': legal_addr.get('city', ''),
                        'region': legal_addr.get('region', ''),
                        'country': legal_addr.get('country', ''),
                        'postal_code': legal_addr.get('postalCode', '')
                    }
                
                # Extract headquarters address
                hq_addr = entity.get('headquartersAddress', {})
                if hq_addr:
                    details['headquarters_address'] = {
                        'address_lines': hq_addr.get('addressLines', []),
                        'city': hq_addr.get('city', ''),
                        'region': hq_addr.get('region', ''),
                        'country': hq_addr.get('country', ''),
                        'postal_code': hq_addr.get('postalCode', '')
                    }
                
                # Extract tax ID from GLEIF if not already set
                if not details['tax_id']:
                    details['tax_id'] = gleif_data.get('tax_id') or gleif_data.get('ein')
                
                # Extract registration and entity status
                registration = gleif_data.get('registration', {})
                details['registration_status'] = registration.get('status', '')
                details['entity_status'] = entity.get('status', '')
        
        return details

