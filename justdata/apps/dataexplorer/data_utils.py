#!/usr/bin/env python3
"""
Data utilities for DataExplorer 2.0
Includes input validation, deterministic queries, and proper error handling.
"""

from typing import List, Dict, Any, Optional
from justdata.shared.utils.bigquery_client import get_bigquery_client, escape_sql_string, execute_query
from justdata.apps.dataexplorer.config import (
    PROJECT_ID, MAX_YEARS, MAX_GEOIDS, MAX_LENDERS
)
from justdata.apps.dataexplorer.query_builders import (
    build_hmda_query, build_sb_query, build_branch_query, build_lender_lookup_query
)
import logging
import time

logger = logging.getLogger(__name__)

# Cache for lenders list (with LAR count)
_lenders_cache = None
_lenders_cache_timestamp = None
_lenders_cache_ttl = 3600  # Cache for 1 hour (3600 seconds)


def validate_years(years: List[int]) -> List[int]:
    """
    Validate and normalize years list.
    
    Args:
        years: List of years
        
    Returns:
        Sorted list of unique years
        
    Raises:
        ValueError: If years exceed limit or are invalid
    """
    if not years:
        raise ValueError("Years list cannot be empty")
    
    if len(years) > MAX_YEARS:
        raise ValueError(f"Maximum {MAX_YEARS} years allowed. Received {len(years)} years.")
    
    # Normalize and validate
    normalized_years = sorted(set([int(year) for year in years]))
    
    # Validate year range (reasonable bounds)
    for year in normalized_years:
        if year < 2000 or year > 2030:
            raise ValueError(f"Invalid year: {year}. Years must be between 2000 and 2030.")
    
    return normalized_years


def validate_geoids(geoids: List[str]) -> List[str]:
    """
    Validate and normalize GEOIDs list.
    
    Args:
        geoids: List of GEOIDs (county FIPS codes)
        
    Returns:
        List of normalized GEOIDs
        
    Raises:
        ValueError: If GEOIDs exceed limit or are invalid
    """
    if not geoids:
        raise ValueError("GEOIDs list cannot be empty")
    
    if len(geoids) > MAX_GEOIDS:
        raise ValueError(f"Maximum {MAX_GEOIDS} GEOIDs allowed. Received {len(geoids)} GEOIDs.")
    
    # Normalize GEOIDs (ensure proper padding)
    normalized_geoids = []
    for geoid in geoids:
        geoid_str = str(geoid).strip()
        # County FIPS codes are 5 digits (state + county)
        if len(geoid_str) == 4:
            geoid_str = '0' + geoid_str  # Pad if missing leading zero
        elif len(geoid_str) == 3:
            geoid_str = '00' + geoid_str
        normalized_geoids.append(geoid_str)
    
    return normalized_geoids


def execute_hmda_query(
    geoids: List[str],
    years: List[int],
    **kwargs
) -> List[Dict[str, Any]]:
    """
    Execute HMDA query with validation.
    
    Args:
        geoids: List of GEOIDs
        years: List of years
        **kwargs: Additional query parameters
        
    Returns:
        List of query results
    """
    try:
        # Validate inputs
        validated_years = validate_years(years)
        validated_geoids = validate_geoids(geoids)
        
        # Build query
        query = build_hmda_query(validated_geoids, validated_years, **kwargs)
        
        # Execute query
        client = get_bigquery_client(PROJECT_ID)
        results = execute_query(client, query)
        
        logger.info(f"HMDA query executed: {len(results)} results for {len(validated_geoids)} GEOIDs, {len(validated_years)} years")
        
        return results
        
    except ValueError as e:
        logger.error(f"Validation error in HMDA query: {e}")
        raise
    except Exception as e:
        logger.error(f"Error executing HMDA query: {e}")
        raise Exception(f"Error executing HMDA query: {str(e)}")


def execute_sb_query(
    geoids: List[str],
    years: List[int],
    **kwargs
) -> List[Dict[str, Any]]:
    """
    Execute Small Business query with validation.
    
    Args:
        geoids: List of GEOIDs
        years: List of years
        **kwargs: Additional query parameters
        
    Returns:
        List of query results
    """
    try:
        # Validate inputs
        validated_years = validate_years(years)
        validated_geoids = validate_geoids(geoids)
        
        # Build query
        query = build_sb_query(validated_geoids, validated_years, **kwargs)
        
        # Execute query
        client = get_bigquery_client(PROJECT_ID)
        results = execute_query(client, query)
        
        logger.info(f"SB query executed: {len(results)} results for {len(validated_geoids)} GEOIDs, {len(validated_years)} years")
        
        return results
        
    except ValueError as e:
        logger.error(f"Validation error in SB query: {e}")
        raise
    except Exception as e:
        logger.error(f"Error executing SB query: {e}")
        raise Exception(f"Error executing SB query: {str(e)}")


def execute_branch_query(
    geoids: List[str] = None,
    years: List[int] = None,
    **kwargs
) -> List[Dict[str, Any]]:
    """
    Execute Branch query with validation.
    
    FIXED ISSUES FROM V1:
    - Proper year validation (not forced to 2025)
    - Consistent county count results
    
    Args:
        geoids: Optional list of GEOIDs
        years: Optional list of years
        **kwargs: Additional query parameters
        
    Returns:
        List of query results
    """
    try:
        # Validate inputs if provided
        validated_years = validate_years(years) if years else None
        validated_geoids = validate_geoids(geoids) if geoids else None
        
        # Build query
        query = build_branch_query(validated_geoids, validated_years, **kwargs)
        
        # Execute query
        client = get_bigquery_client(PROJECT_ID)
        results = execute_query(client, query)
        
        logger.info(f"Branch query executed: {len(results)} results")
        
        return results
        
    except ValueError as e:
        logger.error(f"Validation error in Branch query: {e}")
        raise
    except Exception as e:
        logger.error(f"Error executing Branch query: {e}")
        raise Exception(f"Error executing Branch query: {str(e)}")


def get_lender_target_counties(
    lender_id: str,
    year: int
) -> List[str]:
    """
    Get target counties for a lender in a given year.
    
    FIXED ISSUES FROM V1:
    - Deterministic ORDER BY clause
    - Proper year filtering (not forced to 2025)
    - Consistent results
    
    Args:
        lender_id: Lender RSSD ID
        year: Year
        
    Returns:
        List of county GEOIDs
    """
    try:
        # Validate inputs
        if not lender_id:
            raise ValueError("Lender ID is required")
        
        validated_years = validate_years([year])
        validated_year = validated_years[0]
        
        # RSSD in SOD25 is stored as STRING - try both padded and unpadded formats
        rssd_original = str(lender_id).strip()
        # Try unpadded (remove leading zeros)
        try:
            rssd_unpadded = str(int(rssd_original))
        except (ValueError, TypeError):
            rssd_unpadded = rssd_original
        
        # Try padded to 10 digits
        rssd_padded = rssd_original.zfill(10) if rssd_original.isdigit() else rssd_original
        
        escaped_rssd_unpadded = escape_sql_string(rssd_unpadded)
        escaped_rssd_padded = escape_sql_string(rssd_padded)
        
        # Build query with deterministic ORDER BY
        # Note: SOD25 uses 'geoid5' as the column name, not 'county_code'
        query = f"""
        SELECT DISTINCT
            geoid5 as geoid
        FROM `{PROJECT_ID}.branches.sod25`
        WHERE (rssd = '{escaped_rssd_unpadded}' OR rssd = '{escaped_rssd_padded}')
          AND CAST(year AS STRING) = '{validated_year}'
        ORDER BY geoid5
        """
        
        # Execute query
        client = get_bigquery_client(PROJECT_ID)
        results = execute_query(client, query)
        
        # Extract GEOIDs
        geoids = [row['geoid'] for row in results]
        
        logger.info(f"Found {len(geoids)} target counties for lender {lender_id} in year {validated_year}")
        
        return geoids
        
    except Exception as e:
        logger.error(f"Error getting lender target counties: {e}")
        raise Exception(f"Error getting lender target counties: {str(e)}")


def load_all_lenders18() -> List[Dict[str, Any]]:
    """
    Load all lenders from Lenders18 table with LAR count, sorted by LAR count descending.
    Results are cached for 1 hour to avoid expensive re-queries.
    
    Returns:
        List of all lenders with name (uppercase), city, state, LEI, RSSD, sorted by LAR count
    """
    global _lenders_cache, _lenders_cache_timestamp
    
    # Check cache first
    current_time = time.time()
    if (_lenders_cache is not None and 
        _lenders_cache_timestamp is not None and 
        (current_time - _lenders_cache_timestamp) < _lenders_cache_ttl):
        logger.info(f"Returning {len(_lenders_cache)} lenders from cache")
        return _lenders_cache
    
    try:
        # Query Lenders18 table for all lenders with LAR count
        # Join with lender_names_gleif to get cleaned/display names
        # Order by LAR count descending, then by name
        query = f"""
        SELECT 
            COALESCE(g.display_name, g.cleaned_name, UPPER(l.respondent_name)) as lender_name,
            l.lei as lender_id,
            l.respondent_rssd,
            COALESCE(g.headquarters_city, l.respondent_city) as respondent_city,
            COALESCE(
                CASE 
                    WHEN g.headquarters_state LIKE 'US-%%' THEN SUBSTR(g.headquarters_state, 4)
                    ELSE g.headquarters_state
                END,
                l.respondent_state
            ) as respondent_state,
            COUNT(h.lei) as lar_count
        FROM `{PROJECT_ID}.hmda.lenders18` l
        LEFT JOIN `{PROJECT_ID}.hmda.lender_names_gleif` g
            ON l.lei = g.lei
        LEFT JOIN `{PROJECT_ID}.hmda.hmda` h
            ON l.lei = h.lei
        WHERE l.respondent_name IS NOT NULL
          AND l.lei IS NOT NULL
        GROUP BY 
            lender_name,
            lender_id,
            l.respondent_rssd,
            respondent_city,
            respondent_state
        ORDER BY lar_count DESC, lender_name, lender_id
        """
        
        logger.info("Loading all lenders from Lenders18 table (with LAR count)")
        client = get_bigquery_client(PROJECT_ID)
        results = execute_query(client, query)
        logger.info(f"Loaded {len(results)} lenders from Lenders18")
        
        # Format results with proper field names
        formatted_results = []
        for row in results:
            formatted_results.append({
                'name': row.get('lender_name', '').upper(),
                'lender_name': row.get('lender_name', '').upper(),
                'lei': row.get('lender_id'),
                'lender_id': row.get('lender_id'),
                'rssd': row.get('respondent_rssd'),
                'rssd_id': row.get('respondent_rssd'),
                'city': row.get('respondent_city', ''),
                'respondent_city': row.get('respondent_city', ''),
                'state': row.get('respondent_state', ''),
                'respondent_state': row.get('respondent_state', ''),
                'lar_count': row.get('lar_count', 0)  # Include LAR count in response
            })
        
        # Cache the results
        _lenders_cache = formatted_results
        _lenders_cache_timestamp = current_time
        logger.info(f"Cached {len(formatted_results)} lenders for {_lenders_cache_ttl} seconds")
        
        return formatted_results
        
    except Exception as e:
        logger.error(f"Error loading all lenders from Lenders18: {e}", exc_info=True)
        raise Exception(f"Error loading lenders: {str(e)}")


def search_lenders18(lender_name: str, limit: int = 20, include_verification: bool = True) -> List[Dict[str, Any]]:
    """
    Search lenders directly from Lenders18 table with respondent_city and respondent_state.
    Returns lenders with names in ALL CAPS and city/state information.
    
    Enhanced to include verification data from GLEIF and CFPB APIs to help users
    distinguish between similarly named lenders (e.g., multiple Citizens Banks).
    
    Args:
        lender_name: Lender name to search for
        limit: Maximum number of results to return
        include_verification: Whether to include GLEIF/CFPB verification data (default: True)
        
    Returns:
        List of matching lenders with name (uppercase), city, state, LEI, RSSD, and verification data
    """
    try:
        if not lender_name or len(lender_name.strip()) < 2:
            raise ValueError("Lender name must be at least 2 characters")
        
        escaped_name = escape_sql_string(lender_name.strip())
        
        # Query Lenders18 table directly
        query = f"""
        SELECT DISTINCT
            UPPER(respondent_name) as lender_name,
            lei as lender_id,
            respondent_rssd,
            respondent_city,
            respondent_state,
            type_name
        FROM `{PROJECT_ID}.hmda.lenders18`
        WHERE LOWER(respondent_name) LIKE LOWER('%{escaped_name}%')
          AND respondent_name IS NOT NULL
          AND lei IS NOT NULL
        ORDER BY lender_name, lender_id
        LIMIT {limit}
        """
        
        logger.info(f"Searching Lenders18 for: '{lender_name}' (escaped: '{escaped_name}')")
        client = get_bigquery_client(PROJECT_ID)
        
        try:
            results = execute_query(client, query)
            logger.info(f"Query executed successfully, returned {len(results)} results")
            
            if len(results) == 0:
                # Try a test query to see if table has any data
                test_query = f"SELECT COUNT(*) as cnt FROM `{PROJECT_ID}.hmda.lenders18` LIMIT 1"
                test_results = execute_query(client, test_query)
                if test_results:
                    logger.warning(f"Table exists but search returned 0 results. Table has {test_results[0].get('cnt', 'unknown')} total rows")
        except Exception as query_error:
            logger.error(f"Query execution failed: {query_error}", exc_info=True)
            raise
        
        if not results:
            logger.warning(f"No results found for search term: {lender_name}")
        
        # Format results with proper field names and add verification data
        formatted_results = []
        for row in results:
            lender_data = {
                'name': row.get('lender_name', '').upper(),
                'lender_name': row.get('lender_name', '').upper(),
                'lei': row.get('lender_id'),
                'lender_id': row.get('lender_id'),
                'rssd': row.get('respondent_rssd'),
                'rssd_id': row.get('respondent_rssd'),
                'city': row.get('respondent_city', ''),
                'respondent_city': row.get('respondent_city', ''),
                'state': row.get('respondent_state', ''),
                'respondent_state': row.get('respondent_state', ''),
                'type_name': row.get('type_name'),
                'type': row.get('type_name')  # Also include as 'type' for compatibility
            }
            
            # Add verification data if requested
            if include_verification and lender_data.get('lei'):
                try:
                    verification = verify_lender_with_external_sources(
                        lei=lender_data['lei'],
                        name=lender_data['name'],
                        city=lender_data.get('city'),
                        state=lender_data.get('state')
                    )
                    lender_data['verification'] = verification
                    
                    # Add summary fields for easy display
                    lender_data['verification_summary'] = {
                        'confidence': verification.get('confidence', 'low'),
                        'verified': verification.get('verified', False),
                        'has_warnings': len(verification.get('warnings', [])) > 0,
                        'warnings_count': len(verification.get('warnings', []))
                    }
                except Exception as e:
                    logger.debug(f"Verification failed for LEI {lender_data.get('lei')}: {e}")
                    # Continue without verification data
            
            formatted_results.append(lender_data)
        
        logger.info(f"Found {len(formatted_results)} lenders from Lenders18 for: {lender_name}")
        return formatted_results
        
    except Exception as e:
        logger.error(f"Error searching Lenders18: {e}", exc_info=True)
        raise Exception(f"Error searching lenders: {str(e)}")


def lookup_lender(lender_name: str, exact_match: bool = False) -> List[Dict[str, Any]]:
    """
    Lookup lender by name with deterministic results.
    
    Enhanced to optionally use CFPB API for institution metadata (name, LEI, RSSD),
    then link to BigQuery lenders/lenders18 tables.
    
    FIXED ISSUES FROM V1:
    - Deterministic ORDER BY clause
    - Proper SQL escaping
    
    Args:
        lender_name: Lender name to search for
        exact_match: Whether to use exact match
        
    Returns:
        List of matching lenders with name, LEI, RSSD, and other metadata
    """
    try:
        if not lender_name or len(lender_name.strip()) < 2:
            raise ValueError("Lender name must be at least 2 characters")
        
        results = []
        
        # Try CFPB API first to get authoritative institution data
        try:
            from justdata.apps.dataexplorer.utils.cfpb_client import CFPBClient
            cfpb_client = CFPBClient()
            
            if cfpb_client._is_enabled():
                institution = cfpb_client.get_institution_by_name(lender_name.strip())
                
                if institution:
                    # Enrich with BigQuery lenders table data
                    lei = institution.get('lei')
                    rssd = institution.get('rssd')
                    
                    # Query BigQuery lenders table for additional metadata
                    if lei or rssd:
                        lender_metadata = get_lender_from_bigquery_tables(lei=lei, rssd=rssd)
                        if lender_metadata:
                            # Merge CFPB data with BigQuery metadata
                            institution.update(lender_metadata)
                    
                    results.append(institution)
                    logger.info(f"Found lender via CFPB API: {institution.get('name')}")
        except Exception as cfpb_error:
            logger.debug(f"CFPB API unavailable or error: {cfpb_error}")
            # Continue to BigQuery fallback
        
        # Fallback to BigQuery-only lookup if CFPB didn't return results
        # Note: This requires the hmda.lenders or hmda.lenders18 tables to exist
        # If those tables don't exist, we'll skip BigQuery lookup
        if not results:
            try:
                # Build query
                query = build_lender_lookup_query(lender_name.strip(), exact_match)
                
                # Execute query
                client = get_bigquery_client(PROJECT_ID)
                bq_results = execute_query(client, query)
                
                # Add source indicator
                for result in bq_results:
                    result['source'] = 'bigquery'
                
                results = bq_results
                logger.info(f"Found {len(results)} lenders matching '{lender_name}' via BigQuery")
            except Exception as bq_error:
                logger.warning(f"BigQuery lender lookup failed (this is expected if lenders tables don't exist): {bq_error}")
                # Return empty results if BigQuery lookup fails
                # The CFPB API should be the primary method anyway
                results = []
        
        return results
        
    except Exception as e:
        logger.error(f"Error looking up lender: {e}")
        raise Exception(f"Error looking up lender: {str(e)}")


def get_lender_from_bigquery_tables(lei: str = None, rssd: str = None) -> Optional[Dict[str, Any]]:
    """
    Query BigQuery lenders/lenders18 tables using LEI or RSSD.
    Links CFPB institution data to BigQuery lender records.
    
    Args:
        lei: Legal Entity Identifier
        rssd: Federal Reserve System ID
        
    Returns:
        Lender metadata dictionary or None
    """
    try:
        client = get_bigquery_client(PROJECT_ID)
        
        if lei:
            # Query lenders table by LEI
            query = f"""
            SELECT DISTINCT
                lei as lender_id,
                lender_name,
                rssd_id,
                'HMDA' as source
            FROM `{PROJECT_ID}.hmda.lenders`
            WHERE lei = '{escape_sql_string(lei)}'
            ORDER BY lender_name
            LIMIT 1
            """
        elif rssd:
            # Query lenders18 table by RSSD
            query = f"""
            SELECT DISTINCT
                lei as lender_id,
                lender_name,
                rssd_id,
                'HMDA' as source
            FROM `{PROJECT_ID}.hmda.lenders18`
            WHERE rssd_id = '{escape_sql_string(rssd)}'
            ORDER BY lender_name
            LIMIT 1
            """
        else:
            return None
        
        results = execute_query(client, query)
        return results[0] if results else None
        
    except Exception as e:
        logger.warning(f"Error querying BigQuery lenders table: {e}")
        return None


def verify_lender_with_external_sources(
    lei: str,
    name: str,
    city: str = None,
    state: str = None
) -> Dict[str, Any]:
    """
    Verify lender using GLEIF and CFPB APIs to ensure correct identification.
    
    This function compares:
    1. GLEIF headquarters location with HMDA respondent city/state
    2. CFPB assets data
    3. Name matching between sources
    
    Args:
        lei: Legal Entity Identifier
        name: Lender name from HMDA
        city: City from HMDA (respondent_city)
        state: State from HMDA (respondent_state)
        
    Returns:
        Dictionary with verification results:
        {
            'verified': bool,
            'gleif': {
                'headquarters': {'city': ..., 'state': ..., 'country': ...},
                'name_match': bool,
                'is_active': bool
            },
            'cfpb': {
                'assets': ...,
                'name': ...,
                'found': bool
            },
            'location_match': bool,  # True if GLEIF HQ matches HMDA city/state
            'warnings': [list of warning messages],
            'confidence': 'high' | 'medium' | 'low'
        }
    """
    verification = {
        'verified': False,
        'gleif': None,
        'cfpb': None,
        'location_match': False,
        'warnings': [],
        'confidence': 'low'
    }
    
    # Verify with GLEIF
    try:
        from justdata.apps.dataexplorer.utils.gleif_client import GLEIFClient
        gleif_client = GLEIFClient()
        
        if gleif_client._is_enabled():
            gleif_result = gleif_client.verify_lei(lei, name)
            
            if gleif_result and gleif_result.get('entity'):
                verification['gleif'] = {
                    'headquarters': gleif_result.get('headquarters', {}),
                    'name_match': gleif_result.get('name_match', False),
                    'is_active': gleif_result.get('is_active', False),
                    'legal_name': gleif_result.get('entity', {}).get('legalName', '')
                }
                
                # Check location match
                gleif_hq = gleif_result.get('headquarters', {})
                gleif_city = (gleif_hq.get('city', '') or '').upper().strip()
                gleif_state = (gleif_hq.get('state', '') or '').upper().strip()
                hmda_city = (city or '').upper().strip()
                hmda_state = (state or '').upper().strip()
                
                # Location match if city matches (exact or partial) and state matches
                city_match = False
                if gleif_city and hmda_city:
                    city_match = (gleif_city == hmda_city or 
                                 gleif_city in hmda_city or 
                                 hmda_city in gleif_city)
                
                state_match = gleif_state == hmda_state if gleif_state and hmda_state else False
                verification['location_match'] = city_match and state_match
                
                # Add warnings
                if not gleif_result.get('is_active'):
                    verification['warnings'].append('LEI is not active in GLEIF')
                if not gleif_result.get('name_match'):
                    verification['warnings'].append('Name does not match GLEIF legal name')
                if not verification['location_match']:
                    verification['warnings'].append(
                        f'Headquarters location mismatch: GLEIF shows {gleif_city}, {gleif_state}, '
                        f'but HMDA shows {hmda_city}, {hmda_state}'
                    )
    except Exception as e:
        logger.debug(f"GLEIF verification failed: {e}")
        verification['warnings'].append('Could not verify with GLEIF')
    
    # Verify with CFPB API
    try:
        from justdata.apps.dataexplorer.utils.cfpb_client import CFPBClient
        cfpb_client = CFPBClient()
        
        if cfpb_client._is_enabled():
            cfpb_result = cfpb_client.get_institution_by_lei(lei)
            
            if cfpb_result:
                verification['cfpb'] = {
                    'assets': cfpb_result.get('assets'),
                    'name': cfpb_result.get('name'),
                    'found': True
                }
                
                # Check name match
                cfpb_name = (cfpb_result.get('name', '') or '').upper().strip()
                hmda_name = (name or '').upper().strip()
                name_match = (cfpb_name == hmda_name or 
                             cfpb_name in hmda_name or 
                             hmda_name in cfpb_name)
                
                if not name_match:
                    verification['warnings'].append(
                        f'Name mismatch: CFPB shows "{cfpb_result.get("name")}", '
                        f'but HMDA shows "{name}"'
                    )
            else:
                verification['cfpb'] = {'found': False}
                verification['warnings'].append('Lender not found in CFPB API')
    except Exception as e:
        logger.debug(f"CFPB verification failed: {e}")
        verification['warnings'].append('Could not verify with CFPB API')
    
    # Calculate confidence level
    confidence_score = 0
    if verification['gleif'] and verification['gleif'].get('is_active'):
        confidence_score += 2
    if verification['gleif'] and verification['gleif'].get('name_match'):
        confidence_score += 1
    if verification['location_match']:
        confidence_score += 2
    if verification['cfpb'] and verification['cfpb'].get('found'):
        confidence_score += 1
    
    if confidence_score >= 5:
        verification['confidence'] = 'high'
        verification['verified'] = True
    elif confidence_score >= 3:
        verification['confidence'] = 'medium'
        verification['verified'] = True
    else:
        verification['confidence'] = 'low'
        verification['verified'] = False
    
    return verification


def get_gleif_data_by_lei(lei: str) -> Optional[Dict[str, Any]]:
    """
    Get GLEIF data (legal/hq addresses, parent/child relationships) by LEI.
    Fetches from lender_names_gleif table.
    
    Args:
        lei: Legal Entity Identifier
        
    Returns:
        Dictionary with GLEIF data or None if not found
    """
    try:
        if not lei:
            return None
        
        client = get_bigquery_client(PROJECT_ID)
        
        query = f"""
        SELECT 
            lei,
            gleif_legal_name,
            cleaned_name,
            display_name,
            legal_address_city,
            legal_address_state,
            headquarters_city,
            headquarters_state,
            direct_parent_lei,
            direct_parent_name,
            ultimate_parent_lei,
            ultimate_parent_name,
            direct_children,
            ultimate_children
        FROM `{PROJECT_ID}.hmda.lender_names_gleif`
        WHERE lei = '{escape_sql_string(lei.upper())}'
        LIMIT 1
        """
        
        results = execute_query(client, query)
        
        if not results:
            logger.debug(f"No GLEIF data found for LEI: {lei}")
            return None
        
        row = results[0]
        
        # Parse JSON fields for children (they're stored as JSON strings in BigQuery)
        direct_children = None
        ultimate_children = None
        try:
            import json
            if row.get('direct_children'):
                if isinstance(row['direct_children'], str):
                    direct_children = json.loads(row['direct_children'])
                else:
                    direct_children = row['direct_children']
            if row.get('ultimate_children'):
                if isinstance(row['ultimate_children'], str):
                    ultimate_children = json.loads(row['ultimate_children'])
                else:
                    ultimate_children = row['ultimate_children']
        except Exception as e:
            logger.warning(f"Error parsing children JSON for LEI {lei}: {e}")
        
        return {
            'lei': row.get('lei'),
            'gleif_legal_name': row.get('gleif_legal_name'),
            'cleaned_name': row.get('cleaned_name'),
            'display_name': row.get('display_name'),
            'legal_address': {
                'city': row.get('legal_address_city') or '',
                'state': row.get('legal_address_state') or ''
            },
            'headquarters_address': {
                'city': row.get('headquarters_city') or '',
                'state': row.get('headquarters_state') or ''
            },
            'direct_parent': {
                'lei': row.get('direct_parent_lei'),
                'name': row.get('direct_parent_name')
            } if row.get('direct_parent_lei') else None,
            'ultimate_parent': {
                'lei': row.get('ultimate_parent_lei'),
                'name': row.get('ultimate_parent_name')
            } if row.get('ultimate_parent_lei') else None,
            'direct_children': direct_children or [],
            'ultimate_children': ultimate_children or []
        }
        
    except Exception as e:
        logger.error(f"Error fetching GLEIF data for LEI {lei}: {e}", exc_info=True)
        return None


def get_lender_details_by_lei(lei: str) -> Optional[Dict[str, Any]]:
    """
    Get additional lender details (RSSD, SB_RESID) by LEI.
    Uses RSSD as a crosswalk to get SB_RESID from the lenders table.
    
    Process:
    1. Get RSSD from lenders18 table by LEI
    2. Use RSSD to get SB_RESID from lenders table
    """
    try:
        if not lei:
            return None
        
        client = get_bigquery_client(PROJECT_ID)
        
        # Step 1: Get RSSD and type_name from lenders18 table by LEI
        query_rssd = f"""
        SELECT DISTINCT
            respondent_rssd as rssd,
            type_name,
            respondent_name,
            respondent_city,
            respondent_state
        FROM `{PROJECT_ID}.hmda.lenders18`
        WHERE lei = '{escape_sql_string(lei)}'
        LIMIT 1
        """
        rssd_results = execute_query(client, query_rssd)
        
        if not rssd_results or not rssd_results[0].get('rssd'):
            logger.warning(f"No RSSD found for LEI: {lei}")
            return None
        
        result_row = rssd_results[0]
        rssd = result_row.get('rssd')
        type_name = result_row.get('type_name')
        respondent_name = result_row.get('respondent_name')
        respondent_city = result_row.get('respondent_city')
        respondent_state = result_row.get('respondent_state')
        # Pad RSSD to 10 digits
        rssd_padded = str(rssd).strip().zfill(10) if rssd else None
        
        # Step 2: Use RSSD to get SB_RESID from sb.lenders table
        # The sb.lenders table has sb_resid and sb_rssd columns
        sb_resid = None
        if rssd_padded:
            try:
                # Query sb.lenders table for sb_resid using RSSD
                # Note: sb_rssd in sb.lenders may not be padded, so try both padded and unpadded
                rssd_unpadded = str(int(rssd_padded)) if rssd_padded.isdigit() else rssd_padded
                
                query_sb_resid = f"""
                SELECT DISTINCT
                    sb_resid
                FROM `{PROJECT_ID}.sb.lenders`
                WHERE sb_rssd = '{escape_sql_string(rssd_unpadded)}'
                   OR sb_rssd = '{escape_sql_string(rssd_padded)}'
                LIMIT 1
                """
                logger.info(f"Querying sb.lenders for SB_RESID with RSSD: {rssd_padded} (also trying {rssd_unpadded})")
                sb_results = execute_query(client, query_sb_resid)
                logger.info(f"Query returned {len(sb_results) if sb_results else 0} results")
                
                if sb_results and len(sb_results) > 0:
                    result = sb_results[0]
                    sb_resid = result.get('sb_resid')
                    if sb_resid:
                        logger.info(f"Found SB_RESID in sb.lenders: {sb_resid} for RSSD: {rssd_padded}")
                    else:
                        logger.warning(f"SB_RESID column found but value is None in result: {result}")
                else:
                    logger.warning(f"No results returned from sb.lenders query for RSSD: {rssd_padded}")
            except Exception as e:
                logger.error(f"Error querying sb.lenders for SB_RESID: {e}", exc_info=True)
            
            if not sb_resid:
                logger.warning(f"No SB_RESID found in sb.lenders for RSSD: {rssd_padded}")
        
        return {
            'rssd': rssd_padded,
            'sb_resid': sb_resid,
            'type_name': type_name,
            'type': type_name,  # Also include as 'type' for compatibility
            'name': respondent_name,
            'city': respondent_city,
            'state': respondent_state
        }
    except Exception as e:
        logger.error(f"Error getting lender details by LEI: {e}", exc_info=True)
        return None


def get_peer_lenders(
    lender_id: str,
    data_type: str,
    volume: float,
    min_percent: float = 0.5,
    max_percent: float = 2.0,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get peer lenders based on volume.
    
    FIXED ISSUES FROM V1:
    - Deterministic ORDER BY clause
    - Proper volume filtering
    
    Args:
        lender_id: Subject lender ID
        data_type: Data type ('hmda', 'sb', 'branches')
        volume: Subject lender volume
        min_percent: Minimum peer volume as percent of subject (default 0.5 = 50%)
        max_percent: Maximum peer volume as percent of subject (default 2.0 = 200%)
        limit: Maximum number of peers to return
        
    Returns:
        List of peer lenders
    """
    try:
        if limit > MAX_LENDERS:
            raise ValueError(f"Maximum {MAX_LENDERS} lenders allowed. Received limit: {limit}.")
        
        # Calculate volume range
        min_volume = volume * min_percent
        max_volume = volume * max_percent
        
        # Escape lender ID
        escaped_lender_id = escape_sql_string(str(lender_id))
        
        # Build query based on data type
        if data_type == 'hmda':
            # Join with lenders18 table to get lender names
            query = f"""
            SELECT 
                h.lei as lender_id,
                COALESCE(l.respondent_name, h.lei) as lender_name,
                SUM(h.loan_amount) as total_volume,
                COUNT(*) as loan_count
            FROM `{PROJECT_ID}.hmda.hmda` h
            LEFT JOIN `{PROJECT_ID}.hmda.lenders18` l
                ON h.lei = l.lei
            WHERE h.lei != '{escaped_lender_id}'
              AND h.action_taken = '1'
            GROUP BY h.lei, l.respondent_name
            HAVING SUM(h.loan_amount) >= {min_volume}
               AND SUM(h.loan_amount) <= {max_volume}
            ORDER BY total_volume DESC, lender_name
            LIMIT {limit}
            """
        elif data_type == 'sb':
            # Join with lenders18 table to get lender names
            query = f"""
            SELECT 
                s.lei as lender_id,
                COALESCE(l.respondent_name, s.lei) as lender_name,
                SUM(s.loan_amount) as total_volume,
                SUM(s.number_of_loans) as loan_count
            FROM `{PROJECT_ID}.sb.disclosure` s
            LEFT JOIN `{PROJECT_ID}.hmda.lenders18` l
                ON s.lei = l.lei
            WHERE s.lei != '{escaped_lender_id}'
            GROUP BY s.lei, l.respondent_name
            HAVING SUM(s.loan_amount) >= {min_volume}
               AND SUM(s.loan_amount) <= {max_volume}
            ORDER BY total_volume DESC, lender_name
            LIMIT {limit}
            """
        else:
            raise ValueError(f"Unsupported data type: {data_type}")
        
        # Execute query
        client = get_bigquery_client(PROJECT_ID)
        results = execute_query(client, query)
        
        logger.info(f"Found {len(results)} peer lenders for {lender_id}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error getting peer lenders: {e}")
        raise Exception(f"Error getting peer lenders: {str(e)}")


def get_county_names_from_geoids(geoids: List[str]) -> List[str]:
    """
    Get county names from GEOID FIPS codes.
    
    Args:
        geoids: List of 5-digit county FIPS codes
        
    Returns:
        List of county names in format "County, State"
    """
    try:
        if not geoids:
            return []
        
        # Build query to get county names
        geoids_str = "', '".join([escape_sql_string(g) for g in geoids])
        query = f"""
        SELECT DISTINCT
            LPAD(CAST(geoid5 AS STRING), 5, '0') as geoid,
            County as county_name,
            State as state_name
        FROM `{PROJECT_ID}.geo.cbsa_to_county`
        WHERE LPAD(CAST(geoid5 AS STRING), 5, '0') IN ('{geoids_str}')
          AND County IS NOT NULL
          AND State IS NOT NULL
        ORDER BY State, County
        """
        
        client = get_bigquery_client(PROJECT_ID)
        results = execute_query(client, query)
        
        # Format as "County, State"
        county_names = [f"{row['county_name']}, {row['state_name']}" for row in results]
        
        return county_names
        
    except Exception as e:
        logger.error(f"Error getting county names: {e}")
        return []


def execute_mortgage_query_with_filters(
    sql_template: str,
    county: str,
    year: int,
    loan_purpose: list = None,
    action_taken: list = None,
    occupancy: list = None,
    total_units: list = None,
    construction: list = None,
    loan_type: list = None,
    exclude_reverse_mortgages: bool = True
) -> List[dict]:
    """
    Execute a BigQuery SQL query for mortgage data with parameter substitution and filter application.
    
    This function modifies the SQL template to apply filters from the wizard selector,
    including action_taken (originations vs applications), occupancy, total_units, etc.
    
    Args:
        sql_template: SQL query template with @county, @year, and @loan_purpose parameters
        county: County name in "County, State" format
        year: Year as integer
        loan_purpose: List of loan purpose filters (['purchase', 'refinance', 'equity']) or None for all
        action_taken: List of action_taken codes (['1'] for originations, ['1','2','3','4','5'] for applications)
        occupancy: List of occupancy codes (['1'] for owner-occupied, ['2'] for second-home, ['3'] for investor)
        total_units: List of property type codes (['1'] for 1-4 units, ['3'] for 5+ units)
        construction: List of construction codes (['1'] for site-built, ['2'] for manufactured)
        loan_type: List of loan type codes (['1'] for conventional, ['2'] for FHA, etc.)
        exclude_reverse_mortgages: Whether to exclude reverse mortgages (default True)
        
    Returns:
        List of dictionaries containing query results
    """
    try:
        from justdata.apps.lendsight.data_utils import find_exact_county_match, escape_sql_string as ls_escape_sql_string
        from justdata.shared.utils.bigquery_client import get_bigquery_client, execute_query
        from justdata.shared.utils.unified_env import get_unified_config
        
        config = get_unified_config(load_env=False, verbose=False)
        PROJECT_ID = config.get('GCP_PROJECT_ID')
        client = get_bigquery_client(PROJECT_ID)
        
        # Find the exact county match from the database
        county_matches = find_exact_county_match(county)
        
        if not county_matches:
            raise Exception(f"No matching counties found for: {county}")
        
        # Use the first match
        exact_county = county_matches[0]
        
        # Escape apostrophes in county name for SQL (double them)
        escaped_county = ls_escape_sql_string(exact_county)
        
        # Convert loan_purpose list to comma-separated string for SQL
        if loan_purpose is None or len(loan_purpose) == 0 or set(loan_purpose) == {'purchase', 'refinance', 'equity'}:
            loan_purpose_str = 'all'
        else:
            loan_purpose_str = ','.join(sorted(loan_purpose))
        
        # Start with base SQL template
        sql = sql_template
        
        # Log which table is being used (for debugging)
        if 'justdata.de_hmda' in sql:
            logger.info(f"[DEBUG] Using optimized de_hmda table for {county} {year}")
        elif 'hmda.hmda' in sql:
            logger.warning(f"[WARNING] Still using old hmda.hmda table for {county} {year}")
        
        # Replace basic parameters
        sql = sql.replace('@county', f"'{escaped_county}'")
        # Note: @year is used with activity_year (INT64) so it should be an integer, not a string
        sql = sql.replace('@year', str(year))
        sql = sql.replace('@loan_purpose', f"'{loan_purpose_str}'")
        
        # Apply action_taken filter (replace hardcoded '1' with filter)
        if action_taken:
            if len(action_taken) == 1:
                action_taken_clause = f"h.action_taken = '{action_taken[0]}'"
            else:
                action_taken_values = "', '".join(action_taken)
                action_taken_clause = f"h.action_taken IN ('{action_taken_values}')"
        else:
            # Default to originations only
            action_taken_clause = "h.action_taken = '1'"
        
        # Replace hardcoded action_taken filter
        sql = sql.replace("h.action_taken = '1'  -- Originated loans only", f"{action_taken_clause}  -- Action taken filter")
        
        # Apply occupancy filter
        if occupancy:
            if len(occupancy) == 1:
                occupancy_clause = f"h.occupancy_type = '{occupancy[0]}'"
            else:
                occupancy_values = "', '".join(occupancy)
                occupancy_clause = f"h.occupancy_type IN ('{occupancy_values}')"
            sql = sql.replace("h.occupancy_type = '1'  -- Owner-occupied", f"{occupancy_clause}  -- Occupancy filter")
        
        # Apply total_units filter
        if total_units:
            # Check if this is the special "5+" marker
            if total_units == ['5+']:
                # Handle 5+ units: anything that's not '1', '2', '3', or '4' (as strings)
                # Since total_units is stored as STRING in HMDA data:
                # - '1', '2', '3', '4' are 1-4 units
                # - Anything else ('5', '6', '7', '8', '9', '10', etc.) is 5+ units
                # Exclude NULL values to avoid including missing data
                total_units_clause = "(h.total_units IS NOT NULL AND h.total_units NOT IN ('1','2','3','4'))  -- 5+ units (anything other than 1-4)"
            elif len(total_units) == 1:
                total_units_clause = f"h.total_units = '{total_units[0]}'"
            else:
                total_units_values = "', '".join(total_units)
                total_units_clause = f"h.total_units IN ('{total_units_values}')"
            # Replace hardcoded 1-4 units filter
            sql = sql.replace("h.total_units IN ('1','2','3','4')  -- 1-4 units", f"{total_units_clause}  -- Total units filter")
        
        # Apply construction filter
        if construction:
            if len(construction) == 1:
                construction_clause = f"h.construction_method = '{construction[0]}'"
            else:
                construction_values = "', '".join(construction)
                construction_clause = f"h.construction_method IN ('{construction_values}')"
            sql = sql.replace("h.construction_method = '1'  -- Site-built", f"{construction_clause}  -- Construction filter")
        
        # Apply reverse mortgage filter
        if exclude_reverse_mortgages:
            reverse_clause = "(h.reverse_mortgage IS NULL OR h.reverse_mortgage != '1')  -- Not reverse mortgages"
        else:
            reverse_clause = "1=1  -- Include reverse mortgages"
        sql = sql.replace("(h.reverse_mortgage IS NULL OR h.reverse_mortgage != '1')  -- Not reverse mortgages", reverse_clause)
        
        # Execute query
        return execute_query(client, sql)
        
    except Exception as e:
        raise Exception(f"Error executing BigQuery query for {county} {year}: {e}")


def get_states() -> List[Dict[str, Any]]:
    """
    Get list of all US states from BigQuery.

    Returns:
        List of dictionaries with 'code' (state FIPS) and 'name' (state name)
    """
    try:
        client = get_bigquery_client(PROJECT_ID)

        query = f"""
        SELECT DISTINCT
            SUBSTR(LPAD(CAST(geoid5 AS STRING), 5, '0'), 1, 2) as code,
            State as name
        FROM `{PROJECT_ID}.geo.cbsa_to_county`
        WHERE geoid5 IS NOT NULL
          AND State IS NOT NULL
        ORDER BY State
        """

        results = execute_query(client, query)
        return results

    except Exception as e:
        logger.error(f"Error fetching states: {e}", exc_info=True)
        raise


def get_metros() -> List[Dict[str, Any]]:
    """
    Get list of all metro areas (CBSAs) from BigQuery.

    Handles duplicate CBSAs by preferring:
    1. CBSAs with more counties (more comprehensive)
    2. For Connecticut: CBSAs that include planning regions (09110-09190)
    3. Longer names (typically more complete)

    Returns:
        List of dictionaries with 'code' (CBSA code) and 'name' (CBSA name)
    """
    try:
        client = get_bigquery_client(PROJECT_ID)

        query = f"""
        WITH cbsa_counts AS (
            SELECT
                CAST(cbsa_code AS STRING) as code,
                CBSA as name,
                COUNT(DISTINCT geoid5) as county_count,
                -- Check if this CBSA includes CT planning regions (09110-09190)
                COUNTIF(CAST(geoid5 AS STRING) LIKE '091%'
                       AND CAST(geoid5 AS STRING) >= '09110'
                       AND CAST(geoid5 AS STRING) <= '09190') as ct_planning_region_count
            FROM `{PROJECT_ID}.geo.cbsa_to_county`
            WHERE cbsa_code IS NOT NULL
              AND CBSA IS NOT NULL
              AND TRIM(CBSA) != ''
            GROUP BY code, name
        ),
        ranked_cbsas AS (
            SELECT
                code,
                name,
                county_count,
                ct_planning_region_count,
                ROW_NUMBER() OVER (
                    PARTITION BY code
                    ORDER BY
                        ct_planning_region_count DESC,
                        county_count DESC,
                        LENGTH(name) DESC
                ) as rn
            FROM cbsa_counts
        )
        SELECT
            code,
            name
        FROM ranked_cbsas
        WHERE rn = 1
        ORDER BY name
        """

        results = execute_query(client, query)
        return results

    except Exception as e:
        logger.error(f"Error fetching metros: {e}", exc_info=True)
        raise


def get_counties_for_state(state_fips: str) -> List[Dict[str, Any]]:
    """
    Get counties for a specific state with CBSA information.

    Args:
        state_fips: 2-digit state FIPS code

    Returns:
        List of dictionaries with county information
    """
    try:
        if not state_fips:
            raise ValueError("State FIPS code is required")

        client = get_bigquery_client(PROJECT_ID)
        escaped_state = escape_sql_string(state_fips)

        query = f"""
        SELECT DISTINCT
            County as name,
            LPAD(CAST(geoid5 AS STRING), 5, '0') as geoid,
            SUBSTR(LPAD(CAST(geoid5 AS STRING), 5, '0'), 3, 3) as fips,
            CAST(cbsa_code AS STRING) as cbsa,
            CBSA as cbsa_name
        FROM `{PROJECT_ID}.geo.cbsa_to_county`
        WHERE SUBSTR(LPAD(CAST(geoid5 AS STRING), 5, '0'), 1, 2) = '{escaped_state}'
          AND geoid5 IS NOT NULL
          AND County IS NOT NULL
          -- For Connecticut (state code 09): exclude old county codes (09001-09015), only include planning regions (09110-09190)
          AND NOT (
            '{escaped_state}' = '09'
            AND CAST(geoid5 AS INT64) >= 9001
            AND CAST(geoid5 AS INT64) <= 9015
          )
        ORDER BY County
        """

        results = execute_query(client, query)
        return results

    except Exception as e:
        logger.error(f"Error fetching counties for state {state_fips}: {e}", exc_info=True)
        raise


def get_counties_for_metro(cbsa_code: str) -> List[Dict[str, Any]]:
    """
    Get counties for a specific metro area (CBSA).

    Args:
        cbsa_code: CBSA code

    Returns:
        List of dictionaries with county information
    """
    try:
        if not cbsa_code:
            raise ValueError("CBSA code is required")

        client = get_bigquery_client(PROJECT_ID)
        escaped_cbsa = escape_sql_string(cbsa_code)

        query = f"""
        SELECT DISTINCT
            County as name,
            LPAD(CAST(geoid5 AS STRING), 5, '0') as geoid,
            SUBSTR(LPAD(CAST(geoid5 AS STRING), 5, '0'), 3, 3) as fips,
            SUBSTR(LPAD(CAST(geoid5 AS STRING), 5, '0'), 1, 2) as state_fips,
            State as state_name,
            CAST(cbsa_code AS STRING) as cbsa,
            CBSA as cbsa_name
        FROM `{PROJECT_ID}.geo.cbsa_to_county`
        WHERE CAST(cbsa_code AS STRING) = '{escaped_cbsa}'
          AND geoid5 IS NOT NULL
          AND County IS NOT NULL
          -- For Connecticut (state code 09): exclude old county codes (09001-09015), only include planning regions (09110-09190)
          AND NOT (
            SUBSTR(LPAD(CAST(geoid5 AS STRING), 5, '0'), 1, 2) = '09'
            AND CAST(geoid5 AS INT64) >= 9001
            AND CAST(geoid5 AS INT64) <= 9015
          )
        ORDER BY State, County
        """

        results = execute_query(client, query)
        return results

    except Exception as e:
        logger.error(f"Error fetching counties for metro {cbsa_code}: {e}", exc_info=True)
        raise