#!/usr/bin/env python3
"""
DataExplorer 2.0 Flask Application
Interactive dashboard for HMDA, Small Business, and Branch data analysis.

============================================================================
DATAEXPLORER WIZARD - LOCKED CODE
============================================================================
The wizard collects user choices and passes them to analysis apps via:
- POST /api/generate-area-report (for area analysis)
- POST /api/generate-lender-report (for lender analysis)

See api-client.js for the exact data structure being sent.
DO NOT MODIFY WITHOUT USER APPROVAL
============================================================================
"""

from flask import render_template, request, jsonify, send_from_directory
import os
import json
import logging
from pathlib import Path
from werkzeug.middleware.proxy_fix import ProxyFix

from shared.web.app_factory import create_app, register_standard_routes
from shared.utils.unified_env import ensure_unified_env_loaded, get_unified_config
from apps.dataexplorer.config import TEMPLATES_DIR, STATIC_DIR
from apps.dataexplorer.version import __version__
from apps.dataexplorer.data_utils import (
    validate_years, validate_geoids, lookup_lender
)
from apps.dataexplorer.cache_utils import clear_cache
from apps.dataexplorer.area_analysis_processor import (
    process_hmda_area_analysis, process_sb_area_analysis, process_branch_area_analysis
)
from apps.dataexplorer.lender_analysis_processor import process_lender_analysis

# Get repo root for shared static files
REPO_ROOT = Path(__file__).parent.parent.parent.absolute()

# Load unified environment configuration
ensure_unified_env_loaded(verbose=True)
config = get_unified_config(verbose=True)

# Configure logging - both console and file
log_dir = Path(__file__).parent / 'logs'
log_dir.mkdir(exist_ok=True)
log_file = log_dir / 'dataexplorer.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()  # Also log to console
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"Logging to file: {log_file}")

# Create the Flask app
app = create_app(
    'dataexplorer',
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(STATIC_DIR)
)

# Add ProxyFix for proper request handling behind Render's proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# Configure cache-busting
app.config['DEBUG'] = True
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.jinja_env.bytecode_cache = None


@app.before_request
def clear_template_cache():
    """Clear Jinja2 template cache before each request."""
    if hasattr(app, 'jinja_env'):
        app.jinja_env.bytecode_cache = None
        app.jinja_env.cache = {}
        app.jinja_env.auto_reload = True


# Serve shared logo
@app.route('/static/img/ncrc-logo.png')
def serve_shared_logo():
    """Serve the shared NCRC logo."""
    shared_logo_path = REPO_ROOT / 'shared' / 'web' / 'static' / 'img' / 'ncrc-logo.png'
    if shared_logo_path.exists():
        return send_from_directory(str(shared_logo_path.parent), shared_logo_path.name)
    return send_from_directory(app.static_folder, 'img/ncrc-logo.png'), 404

# Serve shared black logo
@app.route('/static/img/ncrc-logo-black.png')
def serve_shared_black_logo():
    """Serve the shared black NCRC logo."""
    shared_black_logo_path = REPO_ROOT / 'shared' / 'web' / 'static' / 'img' / 'ncrc-logo-black.png'
    if shared_black_logo_path.exists():
        return send_from_directory(str(shared_black_logo_path.parent), shared_black_logo_path.name)
    return send_from_directory(app.static_folder, 'img/ncrc-logo-black.png'), 404


# Serve shared population demographics JavaScript
@app.route('/shared/population_demographics.js')
def shared_population_demographics_js():
    """Serve shared population demographics JavaScript module."""
    shared_static_dir = REPO_ROOT / 'shared' / 'web' / 'static' / 'js'
    js_path = shared_static_dir / 'population_demographics.js'
    if js_path.exists():
        return send_from_directory(str(shared_static_dir), 'population_demographics.js', mimetype='application/javascript')
    return '', 404


@app.route('/')
def index():
    """Main dashboard page - redirects to wizard."""
    return render_template('wizard.html', version=__version__)


@app.route('/dashboard')
def dashboard():
    """Legacy dashboard page."""
    return render_template('dashboard.html', version=__version__)


@app.route('/wizard')
def wizard():
    """Wizard interface for DataExplorer."""
    return render_template('wizard.html', version=__version__)


# Area Analysis Endpoints
@app.route('/api/area/hmda/analysis', methods=['POST'])
def area_hmda_analysis():
    """Area analysis for HMDA data."""
    try:
        data = request.get_json()
        
        # Validate inputs
        geoids = data.get('geoids', [])
        years = data.get('years', [])
        filters = data.get('filters', {})
        
        if not geoids:
            return jsonify({'error': 'GEOIDs are required'}), 400
        
        if not years:
            return jsonify({'error': 'Years are required'}), 400
        
        # Validate inputs (will raise ValueError if invalid)
        try:
            validated_years = validate_years(years)
            validated_geoids = validate_geoids(geoids)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        
        # Process analysis
        results = process_hmda_area_analysis(
            geoids=validated_geoids,
            years=validated_years,
            filters=filters
        )
        
        return jsonify({
            'success': True,
            'data': results
        })
        
    except ValueError as e:
        logger.error(f"Validation error in HMDA area analysis: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error in HMDA area analysis: {e}", exc_info=True)
        return jsonify({'error': 'An error occurred processing your request. Please try again.'}), 500


@app.route('/api/area/sb/analysis', methods=['POST'])
def area_sb_analysis():
    """Area analysis for Small Business data."""
    try:
        data = request.get_json()
        
        geoids = data.get('geoids', [])
        years = data.get('years', [])
        filters = data.get('filters', {})
        
        if not geoids:
            return jsonify({'error': 'GEOIDs are required'}), 400
        
        if not years:
            return jsonify({'error': 'Years are required'}), 400
        
        try:
            validated_years = validate_years(years)
            validated_geoids = validate_geoids(geoids)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        
        results = process_sb_area_analysis(
            geoids=validated_geoids,
            years=validated_years,
            filters=filters
        )
        
        return jsonify({
            'success': True,
            'data': results
        })
        
    except ValueError as e:
        logger.error(f"Validation error in SB area analysis: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error in SB area analysis: {e}", exc_info=True)
        return jsonify({'error': 'An error occurred processing your request. Please try again.'}), 500


@app.route('/api/area/branches/analysis', methods=['POST'])
def area_branches_analysis():
    """Area analysis for Branch data."""
    try:
        data = request.get_json()
        
        geoids = data.get('geoids', [])
        years = data.get('years', [])
        filters = data.get('filters', {})
        
        # Branches can work without geoids (all branches)
        try:
            validated_years = validate_years(years) if years else None
            validated_geoids = validate_geoids(geoids) if geoids else None
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        
        results = process_branch_area_analysis(
            geoids=validated_geoids,
            years=validated_years,
            filters=filters
        )
        
        return jsonify({
            'success': True,
            'data': results
        })
        
    except ValueError as e:
        logger.error(f"Validation error in Branch area analysis: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error in Branch area analysis: {e}", exc_info=True)
        return jsonify({'error': 'An error occurred processing your request. Please try again.'}), 500


# Lender Analysis Endpoints
@app.route('/api/lender/analysis', methods=['POST'])
def lender_analysis():
    """Lender analysis with peer comparison."""
    try:
        data = request.get_json()
        
        lender_id = data.get('lender_id')
        data_types = data.get('data_types', ['hmda', 'sb', 'branches'])
        years = data.get('years', [])
        geoids = data.get('geoids', [])
        enable_peer_comparison = data.get('enable_peer_comparison', True)  # FIXED: Default to True
        custom_peers = data.get('custom_peers', [])
        
        if not lender_id:
            return jsonify({'error': 'Lender ID is required'}), 400
        
        # Validate inputs
        try:
            validated_years = validate_years(years) if years else None
            validated_geoids = validate_geoids(geoids) if geoids else None
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        
        # Process analysis
        results = process_lender_analysis(
            lender_id=lender_id,
            data_types=data_types,
            years=validated_years,
            geoids=validated_geoids,
            enable_peer_comparison=enable_peer_comparison,
            custom_peers=custom_peers
        )
        
        return jsonify({
            'success': True,
            'data': results
        })
        
    except ValueError as e:
        logger.error(f"Validation error in lender analysis: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error in lender analysis: {e}", exc_info=True)
        return jsonify({'error': 'An error occurred processing your request. Please try again.'}), 500


# Lender Lookup Endpoint
@app.route('/api/lender/lookup', methods=['POST'])
def lender_lookup():
    """Lookup lenders by name."""
    try:
        data = request.get_json()
        lender_name = data.get('lender_name', '').strip()
        exact_match = data.get('exact_match', False)
        
        if not lender_name or len(lender_name) < 2:
            return jsonify({'error': 'Lender name must be at least 2 characters'}), 400
        
        results = lookup_lender(lender_name, exact_match)
        
        return jsonify({
            'success': True,
            'data': results
        })
        
    except Exception as e:
        logger.error(f"Error in lender lookup: {e}", exc_info=True)
        return jsonify({'error': 'An error occurred looking up lenders. Please try again.'}), 500


# Lender Search Endpoint (matches frontend API client)
@app.route('/api/lenders', methods=['GET'])
def get_all_lenders():
    """Get all lenders from Lenders18 table."""
    try:
        from apps.dataexplorer.data_utils import load_all_lenders18
        lenders = load_all_lenders18()
        logger.info(f"Returning {len(lenders)} lenders")
        return jsonify({
            'success': True,
            'lenders': lenders
        })
    except Exception as e:
        logger.error(f"Error loading lenders: {e}", exc_info=True)
        return jsonify({'error': f'An error occurred loading lenders: {str(e)}'}), 500


@app.route('/api/lender/lookup-by-lei', methods=['POST'])
def lookup_lender_by_lei():
    """Look up lender RSSD and SB_RESID by LEI."""
    try:
        data = request.get_json()
        lei = data.get('lei', '').strip()
        
        if not lei:
            return jsonify({'error': 'LEI is required'}), 400
        
        from apps.dataexplorer.data_utils import get_lender_details_by_lei
        details = get_lender_details_by_lei(lei)
        
        if details:
            return jsonify({
                'success': True,
                'details': details
            })
        else:
            return jsonify({
                'success': True,
                'details': None
            })
            
    except Exception as e:
        logger.error(f"Error looking up lender by LEI: {e}", exc_info=True)
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500


@app.route('/api/lender/gleif-data', methods=['POST'])
def get_lender_gleif_data():
    """Get GLEIF data (legal/hq addresses, parent/child relationships) by LEI."""
    try:
        data = request.get_json()
        lei = data.get('lei', '').strip()
        
        if not lei:
            return jsonify({'error': 'LEI is required'}), 400
        
        from apps.dataexplorer.data_utils import get_gleif_data_by_lei
        gleif_data = get_gleif_data_by_lei(lei)
        
        if gleif_data:
            return jsonify({
                'success': True,
                'data': gleif_data
            })
        else:
            return jsonify({
                'success': True,
                'data': None
            })
            
    except Exception as e:
        logger.error(f"Error fetching GLEIF data by LEI: {e}", exc_info=True)
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500


@app.route('/api/lender/verify-gleif', methods=['POST'])
def verify_gleif():
    """Verify LEI with GLEIF API and return entity information."""
    try:
        data = request.get_json()
        lei = data.get('lei', '').strip()
        name = data.get('name', '').strip()
        
        if not lei:
            return jsonify({'error': 'LEI is required'}), 400
        
        # Import GLEIF client
        try:
            from apps.dataexplorer.utils.gleif_client import GLEIFClient
            gleif_client = GLEIFClient()
            result = gleif_client.verify_lei(lei, name)
            
            return jsonify({
                'success': True,
                'data': result
            })
        except ImportError:
            # GLEIF client not available, return placeholder
            logger.warning("GLEIF client not available, returning placeholder data")
            return jsonify({
                'success': True,
                'data': {
                    'entity': {
                        'lei': lei,
                        'legalName': name,
                        'status': 'ACTIVE',
                        'registrationStatus': 'ISSUED',
                        'legalAddress': {
                            'city': '',
                            'region': ''
                        }
                    },
                    'is_active': True,
                    'name_match': True,
                    'headquarters': {}
                }
            })
        except Exception as gleif_error:
            logger.error(f"GLEIF API error: {gleif_error}", exc_info=True)
            return jsonify({
                'success': False,
                'error': f'GLEIF verification failed: {str(gleif_error)}'
            }), 500
            
    except Exception as e:
        logger.error(f"Error verifying LEI with GLEIF: {e}", exc_info=True)
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500


@app.route('/api/search-lender', methods=['POST'])
def search_lender():
    """Search for lenders by name using BigQuery Lenders18 table."""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query or len(query) < 2:
            return jsonify({'error': 'Search query must be at least 2 characters'}), 400
        
        # Use Lenders18 table directly
        try:
            from apps.dataexplorer.data_utils import search_lenders18
            results = search_lenders18(query, limit=20)
            logger.info(f"Found {len(results)} lenders from Lenders18 for query: {query}")
        except Exception as bq_error:
            logger.error(f"BigQuery Lenders18 search failed: {bq_error}", exc_info=True)
            results = []
        
        return jsonify({
            'success': True,
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error searching lenders: {e}", exc_info=True)
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'An error occurred searching lenders: {str(e)}'}), 500


@app.route('/api/lender/assets', methods=['POST'])
def get_lender_assets():
    """Get lender assets from CFPB HMDA API by LEI."""
    try:
        data = request.get_json()
        lei = data.get('lei', '').strip()
        
        if not lei:
            return jsonify({'error': 'LEI is required'}), 400
        
        # Try to get assets from CFPB API
        assets = None
        try:
            from apps.dataexplorer.utils.cfpb_client import CFPBClient
            cfpb_client = CFPBClient()
            
            if cfpb_client._is_enabled():
                # Get institution by LEI to get detailed info including assets
                institution = cfpb_client.get_institution_by_lei(lei)
                
                if institution:
                    # Extract assets from various possible field names
                    assets = (institution.get('assets') or 
                             institution.get('total_assets') or
                             institution.get('asset_size') or
                             institution.get('assetSize') or
                             institution.get('totalAssets'))
                    
                    # Ensure assets is a number if it exists
                    # Note: CFPB API returns -1 for non-banks/credit unions
                    if assets is not None:
                        try:
                            if isinstance(assets, str):
                                # Remove commas and dollar signs
                                assets_clean = assets.replace(',', '').replace('$', '').strip()
                                assets = float(assets_clean) if assets_clean else None
                            else:
                                assets = float(assets) if assets else None
                            
                            # If assets is -1, it means not applicable for this institution type
                            # Return it as -1 so frontend can handle it appropriately
                            if assets == -1:
                                logger.debug(f"Assets is -1 for LEI {lei} (not applicable for institution type)")
                        except (ValueError, TypeError):
                            assets = None
        except Exception as e:
            logger.debug(f"Could not get assets from CFPB API: {e}", exc_info=True)
        
        return jsonify({
            'success': True,
            'assets': assets
        })
        
    except Exception as e:
        logger.error(f"Error getting lender assets: {e}", exc_info=True)
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500


# Geography Endpoints
@app.route('/api/states', methods=['GET'])
def get_states():
    """Get list of all US states."""
    try:
        from shared.utils.bigquery_client import get_bigquery_client, execute_query
        from apps.dataexplorer.config import PROJECT_ID
        
        # Query geo.cbsa_to_county table for distinct states
        query = f"""
        SELECT DISTINCT
            SUBSTR(LPAD(CAST(geoid5 AS STRING), 5, '0'), 1, 2) as code,
            State as name
        FROM `{PROJECT_ID}.geo.cbsa_to_county`
        WHERE geoid5 IS NOT NULL
          AND State IS NOT NULL
        ORDER BY State
        """
        
        client = get_bigquery_client(PROJECT_ID)
        results = execute_query(client, query)
        
        return jsonify({
            'success': True,
            'states': results
        })
        
    except Exception as e:
        logger.error(f"Error fetching states: {e}", exc_info=True)
        return jsonify({'error': 'An error occurred loading states. Please try again.'}), 500


@app.route('/api/metros', methods=['GET'])
def get_metros():
    """Get list of all metro areas (CBSAs).
    
    Handles duplicate CBSAs (e.g., Bridgeport) by preferring:
    1. CBSAs with more counties (more comprehensive)
    2. For Connecticut: CBSAs that include planning regions (09110-09190)
    3. Higher CBSA codes (typically newer definitions)
    """
    try:
        from shared.utils.bigquery_client import get_bigquery_client, execute_query
        from apps.dataexplorer.config import PROJECT_ID
        
        # Query to get distinct CBSAs, preferring current definitions
        # For duplicates (same CBSA code with different names), prefer names with more counties and CT planning regions
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
                        -- Prefer names with CT planning regions
                        ct_planning_region_count DESC,
                        -- Then prefer names with more counties
                        county_count DESC,
                        -- Finally prefer longer names (typically more complete)
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
        
        client = get_bigquery_client(PROJECT_ID)
        results = execute_query(client, query)
        
        return jsonify({
            'success': True,
            'metros': results
        })
        
    except Exception as e:
        logger.error(f"Error fetching metros: {e}", exc_info=True)
        return jsonify({'error': 'An error occurred loading metros. Please try again.'}), 500


@app.route('/api/metros/<cbsa_code>/counties', methods=['GET'])
def get_counties_by_metro(cbsa_code):
    """Get counties for a specific metro area (CBSA)."""
    try:
        from shared.utils.bigquery_client import get_bigquery_client, execute_query, escape_sql_string
        from apps.dataexplorer.config import PROJECT_ID
        
        # Escape CBSA code for SQL safety
        escaped_cbsa = escape_sql_string(cbsa_code)
        
        # Query geo.cbsa_to_county table for counties in the CBSA
        # For Connecticut: exclude old county codes (09001-09015), only include planning regions (09110-09190)
        query = f"""
        SELECT DISTINCT
            County as name,
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
        
        client = get_bigquery_client(PROJECT_ID)
        results = execute_query(client, query)
        
        return jsonify({
            'success': True,
            'counties': results
        })
        
    except Exception as e:
        logger.error(f"Error fetching counties for metro {cbsa_code}: {e}", exc_info=True)
        return jsonify({'error': 'An error occurred loading counties. Please try again.'}), 500


@app.route('/api/get-counties', methods=['POST'])
def get_counties():
    """Get counties for a state with CBSA information."""
    try:
        data = request.get_json()
        state_code = data.get('state', '').strip()
        
        if not state_code:
            return jsonify({'error': 'State code is required'}), 400
        
        from shared.utils.bigquery_client import get_bigquery_client, execute_query, escape_sql_string
        from apps.dataexplorer.config import PROJECT_ID
        
        # Escape state code for SQL safety
        escaped_state = escape_sql_string(state_code)
        
        # Query geo.cbsa_to_county table for counties in the state with CBSA info
        # For Connecticut: exclude old county codes (09001-09015), only include planning regions (09110-09190)
        query = f"""
        SELECT DISTINCT
            County as name,
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
        
        client = get_bigquery_client(PROJECT_ID)
        results = execute_query(client, query)
        
        return jsonify({
            'success': True,
            'counties': results
        })
        
    except Exception as e:
        logger.error(f"Error fetching counties: {e}", exc_info=True)
        return jsonify({'error': 'An error occurred loading counties. Please try again.'}), 500


# Data Type Configuration Endpoints
@app.route('/api/config/data-types', methods=['GET'])
def get_data_types():
    """Get available data types and their configurations."""
    from apps.dataexplorer.config import (
        HMDA_YEARS, SB_YEARS, BRANCH_YEARS
    )
    
    return jsonify({
        'success': True,
        'data': {
            'hmda': {
                'name': 'HMDA Mortgage Lending',
                'years': HMDA_YEARS,
                'description': 'Home Mortgage Disclosure Act mortgage lending data'
            },
            'sb': {
                'name': 'Small Business Lending',
                'years': SB_YEARS,
                'description': 'HMDA Section 1071 small business lending data'
            },
            'branches': {
                'name': 'Bank Branches',
                'years': BRANCH_YEARS,
                'description': 'FDIC Summary of Deposits branch data'
            }
        }
    })


@app.route('/test-lender-analysis', methods=['GET'])
def test_lender_analysis_page():
    """Simple test page to trigger lender analysis."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Lender Analysis</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 40px; }
            button { padding: 15px 30px; font-size: 16px; background: #552d87; color: white; border: none; cursor: pointer; border-radius: 5px; }
            button:hover { background: #034ea0; }
            #status { margin-top: 20px; padding: 10px; }
            .loading { color: #666; }
            .success { color: green; }
            .error { color: red; }
        </style>
    </head>
    <body>
        <h1>Test Lender Analysis - Wells Fargo Bank</h1>
        <p>Click the button below to generate a test lender analysis report with Wells Fargo Bank and peers.</p>
        <button onclick="runTest()">Generate Test Report</button>
        <div id="status"></div>
        <script>
            async function runTest() {
                const status = document.getElementById('status');
                status.innerHTML = '<p class="loading">Generating report... This may take a minute.</p>';
                
                try {
                    const response = await fetch('/api/test-lender-analysis', {method: 'POST'});
                    const data = await response.json();
                    
                    if (data.success && data.report_id) {
                        status.innerHTML = '<p class="success">Report generated! Redirecting...</p>';
                        window.location.href = '/report/' + data.report_id;
                    } else {
                        status.innerHTML = '<p class="error">Error: ' + (data.error || 'Unknown error') + '</p>';
                    }
                } catch (error) {
                    status.innerHTML = '<p class="error">Error: ' + error.message + '</p>';
                }
            }
        </script>
    </body>
    </html>
    """


@app.route('/api/test-lender-analysis', methods=['POST'])
def test_lender_analysis():
    """Test endpoint for lender analysis with Wells Fargo Bank and peers."""
    try:
        import uuid
        import threading
        import pandas as pd
        from shared.utils.progress_tracker import create_progress_tracker, store_analysis_result
        from apps.dataexplorer.lender_report_builder import build_lender_report
        from apps.lendsight.core import load_sql_template
        from apps.dataexplorer.data_utils import get_peer_lenders
        from shared.utils.bigquery_client import get_bigquery_client, execute_query, escape_sql_string
        from shared.utils.unified_env import get_unified_config
        from apps.lendsight.mortgage_report_builder import clean_mortgage_data
    except ImportError as e:
        logger.error(f"Import error in test_lender_analysis: {e}", exc_info=True)
        return jsonify({
            'success': False, 
            'error': f'Import error: {str(e)}',
            'error_type': 'ImportError'
        }), 500
    
    try:
        # Wells Fargo Bank test data
        wells_fargo_lei = "KB1H1DSPRFMYMCUFXT09"
        # Try to get assets from CFPB API if available
        assets = None
        try:
            from apps.dataexplorer.utils.cfpb_client import CFPBClient
            cfpb_client = CFPBClient()
            if cfpb_client and cfpb_client._is_enabled():
                # Get institution by LEI to get detailed info including assets
                institution = cfpb_client.get_institution_by_lei(wells_fargo_lei)
                if not institution:
                    # Fallback to name search
                    institution = cfpb_client.get_institution_by_name('WELLS FARGO BANK')
                if institution:
                    # Try various possible asset field names from CFPB API
                    assets = (institution.get('assets') or 
                             institution.get('total_assets') or
                             institution.get('asset_size') or
                             institution.get('assetSize') or
                             institution.get('totalAssets'))
                    # Ensure assets is a number if it exists
                    if assets is not None:
                        try:
                            assets = float(assets) if assets else None
                        except (ValueError, TypeError):
                            assets = None
        except Exception as e:
            logger.debug(f"Could not get assets from CFPB API: {e}", exc_info=True)
        
        wells_fargo_info = {
            'name': 'WELLS FARGO BANK',
            'lei': wells_fargo_lei,
            'rssd': '0000451965',
            'sb_resid': None,
            'type': 'Bank',
            'city': 'Sioux Falls',
            'state': 'SD',
            'assets': assets
        }
        
        # Test years - last 3 years
        test_years = [2022, 2023, 2024]
        
        # Create job ID
        job_id = str(uuid.uuid4())
        try:
            progress_tracker = create_progress_tracker(job_id)
        except Exception as e:
            logger.error(f"Error creating progress tracker: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': f'Failed to create progress tracker: {str(e)}',
                'error_type': type(e).__name__
            }), 500
        
        def run_job():
            try:
                config = get_unified_config(load_env=False, verbose=False)
                PROJECT_ID = config.get('GCP_PROJECT_ID')
                client = get_bigquery_client(PROJECT_ID)
                sql_template = load_sql_template()
                
                if progress_tracker:
                    progress_tracker.update_progress('querying_data', 20, 'Querying Wells Fargo HMDA data for Orange County, California...')
                
                # Use Orange County, California only
                target_county = "Orange County, California"
                from apps.lendsight.data_utils import find_exact_county_match, escape_sql_string as ls_escape_sql_string
                
                county_matches = find_exact_county_match(target_county)
                if not county_matches:
                    progress_tracker.complete(success=False, error=f'County not found: {target_county}')
                    return
                
                exact_county = county_matches[0]
                escaped_county = ls_escape_sql_string(exact_county)
                logger.info(f"Using county: {exact_county}")
                
                # Step 1: Query aggregated volumes by LEI to find peers (much more efficient)
                if progress_tracker:
                    progress_tracker.update_progress('querying_data', 25, 'Finding peer lenders in Orange County...')
                
                # Query aggregated volumes for all lenders in Orange County
                years_str = "', '".join(map(str, test_years))
                volume_query = f"""
                SELECT 
                    h.lei,
                    SUM(h.loan_amount) as total_volume
                FROM `{PROJECT_ID}.hmda.hmda` h
                -- For 2022-2023 Connecticut data, join to geo.census to get planning region from tract
                LEFT JOIN `{PROJECT_ID}.geo.census` ct_tract
                    ON CAST(h.county_code AS STRING) LIKE '09%'
                    AND CAST(h.county_code AS STRING) NOT LIKE '091%'
                    AND h.census_tract IS NOT NULL
                    AND SUBSTR(LPAD(CAST(h.census_tract AS STRING), 11, '0'), 6, 6) = SUBSTR(LPAD(CAST(ct_tract.geoid AS STRING), 11, '0'), 6, 6)
                LEFT JOIN `{PROJECT_ID}.geo.cbsa_to_county` c
                    ON COALESCE(
                        -- For 2022-2023: Use planning region from tract
                        CASE 
                            WHEN CAST(h.county_code AS STRING) LIKE '09%' 
                                 AND CAST(h.county_code AS STRING) NOT LIKE '091%'
                                 AND ct_tract.geoid IS NOT NULL THEN
                                SUBSTR(LPAD(CAST(ct_tract.geoid AS STRING), 11, '0'), 1, 5)
                            ELSE NULL
                        END,
                        -- For 2024: Use planning region code directly from county_code
                        CAST(h.county_code AS STRING)
                    ) = CAST(c.geoid5 AS STRING)
                WHERE c.county_state = '{escaped_county}'
                  AND h.activity_year IN ('{years_str}')
                  AND h.action_taken = '1'
                  AND h.occupancy_type = '1'
                  AND h.total_units IN ('1', '2', '3', '4')
                  AND h.construction_method = '1'
                  AND h.loan_type IN ('1', '2', '3', '4')
                  AND (h.reverse_mortgage IS NULL OR h.reverse_mortgage != '1')
                GROUP BY h.lei
                """
                
                lender_volumes_result = execute_query(client, volume_query)
                lender_volumes_df = pd.DataFrame(lender_volumes_result)
                
                if lender_volumes_df.empty:
                    progress_tracker.complete(success=False, error='No lenders found in Orange County')
                    return
                
                # Get Wells Fargo volume
                wells_fargo_volume_row = lender_volumes_df[lender_volumes_df['lei'] == wells_fargo_lei]
                if wells_fargo_volume_row.empty:
                    progress_tracker.complete(success=False, error='No HMDA data found for Wells Fargo Bank in Orange County')
                    return
                
                subject_volume = float(wells_fargo_volume_row['total_volume'].iloc[0])
                logger.info(f"Wells Fargo volume in Orange County: ${subject_volume:,.0f}")
                
                # Find peers (50% to 200% of subject volume, excluding Wells Fargo)
                min_volume = subject_volume * 0.5
                max_volume = subject_volume * 2.0
                
                peer_volumes_df = lender_volumes_df[
                    (lender_volumes_df['lei'] != wells_fargo_lei) &
                    (lender_volumes_df['total_volume'] >= min_volume) &
                    (lender_volumes_df['total_volume'] <= max_volume)
                ].sort_values('total_volume', ascending=False).head(10)
                
                peer_leis = peer_volumes_df['lei'].tolist()
                logger.info(f"Found {len(peer_leis)} peer lenders in Orange County")
                
                if not peer_leis:
                    progress_tracker.complete(success=False, error='No peer lenders found in Orange County')
                    return
                
                # Step 2: Query aggregated data for Wells Fargo only
                if progress_tracker:
                    progress_tracker.update_progress('querying_data', 30, 'Querying Wells Fargo aggregated data...')
                
                subject_results = []
                for year in test_years:
                    try:
                        # Replace WHERE clause FIRST before replacing @county parameter (if @county appears elsewhere)
                        sql = sql_template.replace("WHERE c.county_state = @county", f"WHERE c.county_state = '{escaped_county}' AND h.lei = '{escape_sql_string(wells_fargo_lei)}'")
                        # Replace any remaining @county references (shouldn't be any, but be safe)
                        sql = sql.replace('@county', f"'{escaped_county}'")
                        sql = sql.replace('@year', f"'{year}'")
                        sql = sql.replace('@loan_purpose', "'all'")
                        
                        results = execute_query(client, sql)
                        if results:
                            subject_results.extend(results)
                    except Exception as e:
                        logger.warning(f"Error querying Wells Fargo {year}: {e}")
                
                logger.info(f"Found {len(subject_results)} aggregated rows for Wells Fargo")
                
                # Step 3: Query aggregated data for peer lenders only
                if progress_tracker:
                    progress_tracker.update_progress('querying_data', 40, 'Querying peer lenders aggregated data...')
                
                peer_leis_str = "', '".join([escape_sql_string(lei) for lei in peer_leis])
                peer_results = []
                
                for year in test_years:
                    try:
                        # Replace WHERE clause FIRST before replacing @county parameter
                        sql = sql_template.replace("WHERE c.county_state = @county", f"WHERE c.county_state = '{escaped_county}' AND h.lei IN ('{peer_leis_str}')")
                        sql = sql.replace('@county', f"'{escaped_county}'")
                        sql = sql.replace('@year', f"'{year}'")
                        sql = sql.replace('@loan_purpose', "'all'")
                        
                        results = execute_query(client, sql)
                        if results:
                            peer_results.extend(results)
                    except Exception as e:
                        logger.warning(f"Error querying peers {year}: {e}")
                
                logger.info(f"Found {len(peer_results)} aggregated rows for {len(peer_leis)} peer lenders")
                
                # Get peer info for metadata
                peers = [{'lender_id': lei} for lei in peer_leis]
                
                # Build report
                report_data = build_lender_report(
                    subject_hmda_data=subject_results,
                    peer_hmda_data=peer_results,
                    lender_info=wells_fargo_info,
                    years=test_years,
                    census_data={},
                    historical_census_data={},
                    hud_data={},
                    progress_tracker=progress_tracker,
                    action_taken=['1']
                )
                
                store_analysis_result(job_id, {
                    'success': True,
                    'report_data': report_data,
                    'metadata': {
                        'lender': wells_fargo_info,
                        'years': test_years,
                        'peer_count': len(peers),
                        'report_type': 'lender',
                        'peer_selection_method': '50% to 200% of subject lender volume',
                        'peer_min_percent': 0.5,
                        'peer_max_percent': 2.0,
                        'geography': 'Orange County, California',
                        'geographic_selection_method': 'County',
                        'hmda_filters': {
                            'action_taken': ['1'],
                            'occupancy_type': ['1'],
                            'total_units': ['1', '2', '3', '4'],
                            'construction_method': ['1'],
                            'loan_type': ['1', '2', '3', '4'],
                            'reverse_mortgage': 'excluded'
                        }
                    }
                })
                progress_tracker.complete(success=True)
                
            except Exception as e:
                logger.error(f"Error in test lender analysis: {e}", exc_info=True)
                progress_tracker.complete(success=False, error=str(e))
        
        threading.Thread(target=run_job, daemon=True).start()
        return jsonify({'success': True, 'report_id': job_id})
        
    except Exception as e:
        logger.error(f"Error in test lender analysis: {e}", exc_info=True)
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Full traceback: {error_details}")
        return jsonify({
            'success': False, 
            'error': str(e),
            'error_type': type(e).__name__
        }), 500


@app.route('/api/generate-lender-report', methods=['POST'])
def generate_lender_report():
    """Generate lender analysis report from wizard data."""
    try:
        import uuid
        import threading
        from shared.utils.progress_tracker import create_progress_tracker, store_analysis_result
        from apps.dataexplorer.lender_analysis_core import run_lender_analysis
        
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Validate required fields
        lender = data.get('lender', {})
        if not lender.get('lei'):
            return jsonify({'success': False, 'error': 'Lender LEI is required'}), 400
        
        # Create job ID
        job_id = str(uuid.uuid4())
        try:
            progress_tracker = create_progress_tracker(job_id)
            # Set initial progress immediately so client sees it
            progress_tracker.update_progress('initializing', 0, 'Initializing lender analysis...')
        except Exception as e:
            logger.error(f"Error creating progress tracker: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': f'Failed to create progress tracker: {str(e)}',
                'error_type': type(e).__name__
            }), 500
        
        def run_job():
            try:
                result = run_lender_analysis(
                    wizard_data=data,
                    job_id=job_id,
                    progress_tracker=progress_tracker
                )
                
                if result.get('success'):
                    # Store the result (already stored by run_lender_analysis)
                    logger.info(f"Lender analysis completed successfully for job {job_id}")
                else:
                    logger.error(f"Lender analysis failed for job {job_id}: {result.get('error')}")
                    
            except Exception as e:
                logger.error(f"Error in lender analysis job {job_id}: {e}", exc_info=True)
                if progress_tracker:
                    progress_tracker.complete(success=False, error=str(e))
        
        threading.Thread(target=run_job, daemon=True).start()
        return jsonify({'success': True, 'report_id': job_id})
        
    except Exception as e:
        logger.error(f"Error in generate lender report: {e}", exc_info=True)
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Full traceback: {error_details}")
        return jsonify({
            'success': False, 
            'error': str(e),
            'error_type': type(e).__name__
        }), 500


@app.route('/api/generate-area-report', methods=['POST'])
def generate_area_report():
    """Generate area analysis report from wizard data."""
    try:
        import uuid
        import threading
        from shared.utils.progress_tracker import create_progress_tracker, store_analysis_result
        from apps.dataexplorer.core import run_area_analysis
        
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Validate required fields
        geography = data.get('geography', {})
        counties = geography.get('counties', [])
        if not counties:
            return jsonify({'success': False, 'error': 'At least one county is required'}), 400
        
        # Create job ID
        job_id = str(uuid.uuid4())
        try:
            progress_tracker = create_progress_tracker(job_id)
            # Set initial progress immediately so client sees it
            progress_tracker.update_progress('initializing', 0, 'Initializing area analysis...')
        except Exception as e:
            logger.error(f"Error creating progress tracker: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': f'Failed to create progress tracker: {str(e)}',
                'error_type': type(e).__name__
            }), 500
        
        def run_job():
            try:
                result = run_area_analysis(
                    wizard_data=data,
                    job_id=job_id,
                    progress_tracker=progress_tracker
                )
                
                if result.get('success'):
                    # Store the result (metadata is already included in result)
                    store_analysis_result(job_id, result)
                    logger.info(f"Area analysis completed successfully for job {job_id}")
                else:
                    logger.error(f"Area analysis failed for job {job_id}: {result.get('error')}")
                    if progress_tracker:
                        progress_tracker.complete(success=False, error=result.get('error', 'Unknown error'))
                    
            except Exception as e:
                logger.error(f"Error in area analysis job {job_id}: {e}", exc_info=True)
                if progress_tracker:
                    progress_tracker.complete(success=False, error=str(e))
        
        threading.Thread(target=run_job, daemon=True).start()
        return jsonify({'success': True, 'report_id': job_id})
        
    except Exception as e:
        logger.error(f"Error in generate area report: {e}", exc_info=True)
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Full traceback: {error_details}")
        return jsonify({
            'success': False, 
            'error': str(e),
            'error_type': type(e).__name__
        }), 500


# Progress tracking endpoint (Server-Sent Events)
@app.route('/progress/<job_id>', methods=['GET'])
def progress_handler(job_id):
    """Progress tracking endpoint using Server-Sent Events."""
    from flask import Response
    from shared.utils.progress_tracker import get_progress
    import time
    import json
    import sys
    
    def event_stream():
        last_percent = -1
        last_step = ""
        keepalive_counter = 0
        max_keepalive = 4  # Send keepalive every 2 seconds (4 * 0.5s) to prevent timeout
        max_iterations = 3600  # Max 30 minutes (3600 * 0.5s)
        iteration_count = 0
        consecutive_errors = 0
        max_consecutive_errors = 10
        
        try:
            # Send initial progress data immediately so client sees current state
            try:
                initial_progress = get_progress(job_id)
                if not initial_progress:
                    # If job not found, return "processing" state (job might be running but progress lost)
                    initial_progress = {'percent': 0, 'step': 'Processing...', 'done': False, 'error': None}
                
                percent = initial_progress.get("percent", 0)
                step = initial_progress.get("step", "Processing...")
                done = initial_progress.get("done", False)
                error = initial_progress.get("error", None)
                
                # Escape step text for JSON
                try:
                    step_escaped = step.replace('"', '\\"').replace('\n', '\\n').replace('\r', '')
                except:
                    step_escaped = "Processing..."
                
                # Send initial data message
                initial_message = f"data: {{\"percent\": {percent}, \"step\": \"{step_escaped}\", \"done\": {str(done).lower()}, \"error\": {json.dumps(error) if error else 'null'}}}\n\n"
                yield initial_message
                sys.stdout.flush()
                
                # Update last values so we don't immediately send duplicate
                last_percent = percent
                last_step = step
                
                logger.info(f"Sent initial progress for {job_id}: {percent}% - {step}")
            except Exception as e:
                logger.error(f"Error sending initial progress message: {e}", exc_info=True)
                # Still continue - try to send default "processing" state
                try:
                    yield f"data: {{\"percent\": 0, \"step\": \"Processing...\", \"done\": false, \"error\": null}}\n\n"
                    sys.stdout.flush()
                except:
                    pass
            
            while iteration_count < max_iterations:
                try:
                    iteration_count += 1
                    
                    # Get progress
                    try:
                        progress = get_progress(job_id)
                        if not progress:
                            # Job not found - return "processing" state (job might be running but progress lost)
                            progress = {'percent': max(0, last_percent), 'step': 'Processing...', 'done': False, 'error': None}
                        consecutive_errors = 0  # Reset error counter on success
                    except Exception as e:
                        consecutive_errors += 1
                        logger.warning(f"Error getting progress for {job_id} (attempt {consecutive_errors}): {e}")
                        # Use last known progress or default to "processing"
                        progress = {'percent': max(0, last_percent), 'step': 'Processing...', 'done': False, 'error': None}
                        
                        # If too many consecutive errors, break to prevent infinite loop
                        if consecutive_errors >= max_consecutive_errors:
                            logger.error(f"Too many consecutive errors getting progress for {job_id}, closing stream")
                            yield f"data: {{\"percent\": {max(0, last_percent)}, \"step\": \"Connection issue - please refresh\", \"done\": false, \"error\": null}}\n\n"
                            sys.stdout.flush()
                            break
                    
                    percent = progress.get("percent", 0)
                    step = progress.get("step", "Processing...")
                    done = progress.get("done", False)
                    error = progress.get("error", None)
                    
                    # Escape step text for JSON
                    try:
                        step_escaped = step.replace('"', '\\"').replace('\n', '\\n').replace('\r', '')
                    except:
                        step_escaped = "Processing..."
                    
                    # Always send something to keep connection alive
                    # Send update if changed, or send keepalive if nothing changed
                    if percent != last_percent or step != last_step or done or error:
                        # Send actual update
                        try:
                            message = f"data: {{\"percent\": {percent}, \"step\": \"{step_escaped}\", \"done\": {str(done).lower()}, \"error\": {json.dumps(error) if error else 'null'}}}\n\n"
                            yield message
                            sys.stdout.flush()  # Force flush
                            last_percent = percent
                            last_step = step
                            keepalive_counter = 0
                        except Exception as e:
                            logger.error(f"Error sending progress update: {e}")
                            # Try to send a simple keepalive
                            try:
                                yield f": keepalive\n\n"
                                sys.stdout.flush()
                            except:
                                pass
                    elif keepalive_counter >= max_keepalive:
                        # Send keepalive comment to prevent timeout
                        try:
                            yield f": keepalive\n\n"
                            sys.stdout.flush()
                            keepalive_counter = 0
                        except Exception as e:
                            logger.warning(f"Error sending keepalive: {e}")
                    
                    # Check if done
                    if done or error:
                        time.sleep(0.1)
                        break
                    
                    keepalive_counter += 1
                    time.sleep(0.5)
                    
                except GeneratorExit:
                    logger.info(f"Progress stream closed by client for {job_id}")
                    break
                except Exception as e:
                    logger.error(f"Error in progress stream loop for {job_id}: {e}", exc_info=True)
                    try:
                        # Try to send error message
                        yield f"data: {{\"percent\": {last_percent}, \"step\": \"Processing...\", \"done\": false, \"error\": null}}\n\n"
                        sys.stdout.flush()
                    except:
                        pass
                    time.sleep(1)
            
            # If we hit max iterations, send a timeout message
            if iteration_count >= max_iterations:
                try:
                    yield f"data: {{\"percent\": {last_percent}, \"step\": \"Still processing...\", \"done\": false, \"error\": null}}\n\n"
                    sys.stdout.flush()
                except:
                    pass
                    
        except GeneratorExit:
            logger.info(f"Progress stream generator exited for {job_id}")
        except Exception as e:
            logger.error(f"Fatal error in progress stream for {job_id}: {e}", exc_info=True)
            try:
                yield f"data: {{\"percent\": 0, \"step\": \"Connection error\", \"done\": false, \"error\": \"Progress tracking error\"}}\n\n"
                sys.stdout.flush()
            except:
                pass
    
    try:
        response = Response(event_stream(), mimetype="text/event-stream")
        response.headers['Cache-Control'] = 'no-cache, no-transform'
        response.headers['X-Accel-Buffering'] = 'no'
        response.headers['Connection'] = 'keep-alive'
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        logger.error(f"Error creating SSE response for {job_id}: {e}", exc_info=True)
        # Return a JSON response with processing state instead of 500/503
        # This prevents the client from seeing 503 errors
        return jsonify({
            'percent': 0,
            'step': 'Processing...',
            'done': False,
            'error': None,
            'message': 'Progress tracking temporarily unavailable, but analysis may still be running'
        }), 200


# Excel export endpoint for lender reports
@app.route('/api/export-lender-report-excel', methods=['POST'])
def export_lender_report_excel():
    """Export lender report to Excel with all data including all metros and peer details."""
    try:
        data = request.get_json()
        job_id = data.get('job_id')
        wizard_data = data.get('wizard_data', {})
        
        # Try to get cached data first
        from shared.utils.progress_tracker import get_analysis_result
        cached_result = None
        if job_id:
            cached_result = get_analysis_result(job_id)
        
        # If we have cached data, use it
        if cached_result and cached_result.get('success'):
            logger.info(f"Using cached data for Excel export (job_id: {job_id})")
            report_data = cached_result.get('report_data', {})
            metadata = cached_result.get('metadata', {})
            all_metros_data = cached_result.get('all_metros_data', [])
            peer_data = cached_result.get('peer_data', [])
        else:
            # Need to regenerate - use wizard_data to run analysis
            logger.info("No cached data found, running analysis for Excel export")
            from apps.dataexplorer.lender_analysis_core import run_lender_analysis
            
            # Run analysis to get all data
            result = run_lender_analysis(wizard_data, job_id=None, progress_tracker=None)
            
            if not result.get('success'):
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Failed to generate report data')
                }), 500
            
            report_data = result.get('report_data', {})
            metadata = result.get('metadata', {})
            all_metros_data = result.get('all_metros_data', [])
            peer_data = result.get('peer_data', [])
        
        # If all_metros_data or peer_data is missing, we already have it from the result above
        # No need to query again - the result from run_lender_analysis already includes these
        
        # Format all metros data for Excel (if not already formatted)
        if all_metros_data and len(all_metros_data) > 0:
            # Check if it's already in the right format (list of dicts)
            if isinstance(all_metros_data[0], dict):
                # Already in correct format
                formatted_metros = all_metros_data
            else:
                # Convert DataFrame to list of dicts
                import pandas as pd
                if isinstance(all_metros_data, pd.DataFrame):
                    formatted_metros = all_metros_data.to_dict('records')
                else:
                    formatted_metros = []
        else:
            formatted_metros = []
        
        return jsonify({
            'success': True,
            'report_data': report_data,
            'all_metros_data': formatted_metros,
            'peer_data': peer_data if peer_data else [],
            'metadata': metadata
        })
        
    except Exception as e:
        logger.error(f"Error exporting lender report to Excel: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Error generating Excel export: {str(e)}'
        }), 500


# Excel export endpoint for area reports
@app.route('/api/export-area-report-excel', methods=['POST'])
def export_area_report_excel():
    """Export area report to Excel with all data."""
    try:
        data = request.get_json()
        job_id = data.get('job_id')
        geography = data.get('geography', {})
        years = data.get('years', [])
        filters = data.get('filters', {})
        
        # Try to get cached data first
        from shared.utils.progress_tracker import get_analysis_result
        cached_result = None
        if job_id:
            cached_result = get_analysis_result(job_id)
        
        # If we have cached data, use it
        if cached_result and cached_result.get('success'):
            logger.info(f"Using cached data for Excel export (job_id: {job_id})")
            report_data = cached_result.get('report_data', {})
            metadata = cached_result.get('metadata', {})
            census_data = cached_result.get('census_data', {})
            historical_census_data = cached_result.get('historical_census_data', {})
        else:
            # Need to regenerate - reconstruct wizard_data from request
            logger.info("No cached data found, running analysis for Excel export")
            from apps.dataexplorer.core import run_area_analysis
            
            # Reconstruct wizard_data from the request
            wizard_data = {
                'geography': geography,
                'years': years,
                'filters': filters
            }
            
            # Run analysis to get all data
            result = run_area_analysis(wizard_data, job_id=None, progress_tracker=None)
            
            if not result.get('success'):
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Failed to generate report data')
                }), 500
            
            report_data = result.get('report_data', {})
            metadata = result.get('metadata', {})
            census_data = result.get('census_data', {})
            historical_census_data = result.get('historical_census_data', {})
        
        return jsonify({
            'success': True,
            'report_data': report_data,
            'metadata': metadata,
            'census_data': census_data,
            'historical_census_data': historical_census_data
        })
        
    except Exception as e:
        logger.error(f"Error exporting area report to Excel: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Error generating Excel export: {str(e)}'
        }), 500


@app.route('/api/clear-cache', methods=['POST'])
def clear_cache_endpoint():
    """Clear cache files (admin/debug endpoint)."""
    try:
        data = request.get_json() or {}
        data_type = data.get('data_type')  # Optional: 'hmda', 'census', 'hud', 'historical_census'
        clear_results = data.get('clear_results', False)  # Also clear old analysis result files
        
        deleted_count = clear_cache(data_type=data_type)
        
        # Optionally clear old analysis result files
        if clear_results:
            from pathlib import Path
            from shared.utils.progress_tracker import _get_progress_storage_dir
            storage_dir = _get_progress_storage_dir()
            if storage_dir:
                result_files = list(storage_dir.glob("result_*.pkl")) + list(storage_dir.glob("result_*.json"))
                for result_file in result_files:
                    try:
                        result_file.unlink()
                        deleted_count += 1
                        logger.info(f"Deleted result file: {result_file.name}")
                    except Exception as e:
                        logger.warning(f"Error deleting result file {result_file.name}: {e}")
        
        return jsonify({
            'success': True,
            'message': f'Cleared {deleted_count} file(s)',
            'deleted_count': deleted_count
        }), 200
    except Exception as e:
        logger.error(f"Error clearing cache: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Report display endpoint
@app.route('/report/<job_id>', methods=['GET'])
def show_report(job_id):
    """Display the analysis report (area or lender)."""
    from shared.utils.progress_tracker import get_analysis_result, get_progress
    
    try:
        result = get_analysis_result(job_id)
        
        if not result:
            # Check if job is still in progress
            progress = get_progress(job_id)
            if progress and not progress.get('done', False):
                # Job is still running - show progress page
                # Determine which progress template to use based on metadata or default to area
                metadata = progress.get('metadata', {})
                if metadata.get('lender'):
                    # Lender analysis - use area progress template for now (we can create a lender-specific one later)
                    return render_template('area_report_progress.html', 
                                         job_id=job_id, 
                                         version=__version__)
                else:
                    # Area analysis
                    return render_template('area_report_progress.html', 
                                         job_id=job_id, 
                                         version=__version__)
            
            # Job not found and not in progress - show error
            return f"""
            <html><body style="font-family: Arial; padding: 40px; text-align: center;">
                <h2>Report Not Found</h2>
                <p>Report not found. The analysis may still be running or may have expired.</p>
                <p>Job ID: {job_id}</p>
                <a href="/">Return to Home</a>
            </body></html>
            """, 404
        
        if not result.get('success'):
            return render_template('error_template.html',
                                 error=result.get('error', 'Unknown error'),
                                 job_id=job_id), 500
        
        # Determine report type from metadata
        metadata = result.get('metadata', {})
        report_data = result.get('report_data', {})
        
        if metadata.get('lender'):
            # Lender analysis report
            return render_template('lender_report_template.html',
                                 report_data=report_data,
                                 metadata=metadata,
                                 version=__version__)
        else:
            # Area analysis report
            historical_census_data = result.get('historical_census_data', {})
            # Debug: Log structure of historical_census_data
            if historical_census_data:
                logger.info(f"[DEBUG] historical_census_data keys: {list(historical_census_data.keys())}")
                if len(historical_census_data) > 0:
                    first_geoid = list(historical_census_data.keys())[0]
                    first_county = historical_census_data[first_geoid]
                    logger.info(f"[DEBUG] Sample county ({first_geoid}) keys: {list(first_county.keys()) if isinstance(first_county, dict) else 'Not a dict'}")
                    if isinstance(first_county, dict) and 'time_periods' in first_county:
                        logger.info(f"[DEBUG] time_periods keys: {list(first_county['time_periods'].keys())}")
                    else:
                        logger.warning(f"[DEBUG] time_periods missing or county is not a dict!")
            else:
                logger.warning(f"[DEBUG] historical_census_data is empty or missing!")
            
            return render_template('area_report_template.html',
                                     report_data=report_data,
                                     metadata=metadata,
                                     census_data=result.get('census_data', {}),
                                     historical_census_data=historical_census_data,
                                     version=__version__)
        
    except Exception as e:
        logger.error(f"Error displaying report {job_id}: {e}", exc_info=True)
        import traceback
        logger.error(traceback.format_exc())
        return f"""
        <html><body style="font-family: Arial; padding: 40px; text-align: center;">
            <h2>Error</h2>
            <p>An error occurred displaying the report: {str(e)}</p>
            <a href="/">Return to Home</a>
        </body></html>
        """, 500


@app.route('/api/bigquery/job-history', methods=['GET'])
def get_bigquery_job_history():
    """Query BigQuery job history to see recent queries."""
    try:
        from shared.utils.bigquery_client import get_bigquery_client
        from google.cloud import bigquery
        from datetime import datetime, timedelta
        
        # Get query parameters
        max_results = request.args.get('max_results', 50, type=int)
        hours_back = request.args.get('hours_back', 24, type=int)
        lei_filter = request.args.get('lei', None)  # Optional LEI filter
        
        # Get BigQuery client
        client = get_bigquery_client()
        if not client:
            return jsonify({'success': False, 'error': 'BigQuery client not available'}), 500
        
        # Calculate time threshold
        time_threshold = datetime.utcnow() - timedelta(hours=hours_back)
        
        # List jobs
        jobs = []
        job_count = 0
        
        # Query the INFORMATION_SCHEMA for query history
        # This is more reliable than listing jobs
        project_id = config.get('GCP_PROJECT_ID', 'hdma1-242116')
        
        # Query job history from INFORMATION_SCHEMA
        query = f"""
        SELECT
            job_id,
            creation_time,
            start_time,
            end_time,
            state,
            total_bytes_processed,
            total_slot_ms,
            user_email,
            query,
            statement_type,
            error_result
        FROM `{project_id}`.`region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
        WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {hours_back} HOUR)
            AND job_type = 'QUERY'
            AND state = 'DONE'
        ORDER BY creation_time DESC
        LIMIT {max_results}
        """
        
        try:
            query_job = client.query(query)
            results = query_job.result()
            
            for row in results:
                job_data = {
                    'job_id': row.job_id,
                    'creation_time': row.creation_time.isoformat() if row.creation_time else None,
                    'start_time': row.start_time.isoformat() if row.start_time else None,
                    'end_time': row.end_time.isoformat() if row.end_time else None,
                    'state': row.state,
                    'total_bytes_processed': row.total_bytes_processed,
                    'total_slot_ms': row.total_slot_ms,
                    'user_email': row.user_email,
                    'query': row.query,
                    'statement_type': row.statement_type,
                    'error': str(row.error_result) if row.error_result else None
                }
                
                # Filter by LEI if provided
                if lei_filter and lei_filter.upper() in (job_data.get('query', '') or '').upper():
                    jobs.append(job_data)
                    job_count += 1
                elif not lei_filter:
                    jobs.append(job_data)
                    job_count += 1
                
                if job_count >= max_results:
                    break
        except Exception as e:
            logger.error(f"Error querying job history: {e}", exc_info=True)
            # Fallback: try listing jobs directly
            try:
                for job in client.list_jobs(max_results=max_results):
                    if job.created < time_threshold:
                        continue
                    
                    job.reload()  # Get full job details
                    
                    if job.job_type == 'query' and job.state == 'DONE':
                        job_data = {
                            'job_id': job.job_id,
                            'creation_time': job.created.isoformat() if job.created else None,
                            'start_time': job.started.isoformat() if job.started else None,
                            'end_time': job.ended.isoformat() if job.ended else None,
                            'state': job.state,
                            'total_bytes_processed': job.total_bytes_processed,
                            'user_email': job.user_email if hasattr(job, 'user_email') else None,
                            'query': job.query if hasattr(job, 'query') else None,
                            'error': str(job.errors[0]) if job.errors else None
                        }
                        
                        # Filter by LEI if provided
                        if lei_filter and lei_filter.upper() in (job_data.get('query', '') or '').upper():
                            jobs.append(job_data)
                        elif not lei_filter:
                            jobs.append(job_data)
            except Exception as e2:
                logger.error(f"Error in fallback job listing: {e2}", exc_info=True)
                return jsonify({
                    'success': False,
                    'error': f'Error querying job history: {str(e)}. Fallback also failed: {str(e2)}'
                }), 500
        
        return jsonify({
            'success': True,
            'jobs': jobs,
            'count': len(jobs),
            'hours_back': hours_back,
            'lei_filter': lei_filter
        })
        
    except Exception as e:
        logger.error(f"Error getting BigQuery job history: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# Export application for gunicorn (required for Docker/production)
application = app

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8085))
    debug = os.getenv('DEBUG', 'true').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
