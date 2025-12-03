#!/usr/bin/env python3
"""
LendSight Flask web application.
Uses the same routing patterns as BranchSeeker and BizSight.
"""

from flask import render_template, request, jsonify
import os

from justdata.shared.web.app_factory import create_app, register_standard_routes
from justdata.core.config.app_config import LendSightConfig

# Template and static directories (shared)
TEMPLATES_DIR = os.path.join(LendSightConfig.BASE_DIR, 'shared', 'web', 'templates')
STATIC_DIR = os.path.join(LendSightConfig.BASE_DIR, 'shared', 'web', 'static')

# Create the Flask app
app = create_app(
    'lendsight',
    template_folder=TEMPLATES_DIR,
    static_folder=STATIC_DIR
)


def index():
    """Main page with the analysis form"""
    return render_template('lendsight_template.html')


def progress_handler(job_id):
    """Progress tracking endpoint"""
    # To be implemented
    return jsonify({'progress': 0})


def analyze():
    """Handle analysis request"""
    # To be implemented
    return jsonify({'success': False, 'error': 'Not yet implemented'})


def download():
    """Download the generated reports"""
    # To be implemented
    return jsonify({'error': 'Not yet implemented'}), 404


def data():
    """Return data for the application"""
    # To be implemented
    return jsonify([])


# Register standard routes
register_standard_routes(
    app,
    index_handler=index,
    analyze_handler=analyze,
    progress_handler=progress_handler,
    download_handler=download,
    data_handler=data
)


# Add data endpoints required by the frontend
@app.route('/counties')
def counties_route():
    """Return a list of available counties for lending analysis"""
    try:
        from justdata.shared.utils.bigquery_client import get_bigquery_client
        from justdata.core.config.app_config import LendSightConfig
        
        client = get_bigquery_client(LendSightConfig.PROJECT_ID)
        query = """
        SELECT DISTINCT county_state 
        FROM geo.cbsa_to_county 
        ORDER BY county_state
        """
        query_job = client.query(query)
        results = query_job.result()
        counties = [row.county_state for row in results]
        print(f"✅ Fetched {len(counties)} counties from BigQuery for LendSight")
        return jsonify(counties)
    except Exception as e:
        print(f"⚠️  Error fetching counties: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])


@app.route('/states')
def states_route():
    """Return a list of available states for lending analysis"""
    try:
        from justdata.shared.utils.bigquery_client import get_bigquery_client
        from justdata.core.config.app_config import LendSightConfig
        
        client = get_bigquery_client(LendSightConfig.PROJECT_ID)
        query = """
        SELECT DISTINCT 
            s.state_abbrv as code,
            s.state as name
        FROM geo.states s
        INNER JOIN geo.cbsa_to_county c ON s.state = c.state
        WHERE s.state_abbrv IS NOT NULL AND s.state IS NOT NULL
        ORDER BY s.state
        """
        query_job = client.query(query)
        results = query_job.result()
        states = [{"code": row.code, "name": row.name} for row in results if row.code and row.name]
        print(f"✅ Fetched {len(states)} states from BigQuery for LendSight")
        return jsonify(states)
    except Exception as e:
        print(f"⚠️  Error fetching states: {e}")
        import traceback
        traceback.print_exc()
        # Fallback to shared states
        from justdata.shared.utils.geo_data import get_us_states
        return jsonify(get_us_states())


@app.route('/metro-areas')
def metro_areas_route():
    """Return a list of available metro areas for lending analysis"""
    # TODO: Implement HMDA metro area data lookup
    # For now, return empty array - lending-specific metro data pending
    return jsonify([])


@app.route('/counties-by-state/<state_code>')
def counties_by_state_route(state_code):
    """Return a list of counties for a specific state"""
    try:
        from justdata.shared.utils.bigquery_client import get_bigquery_client
        from justdata.core.config.app_config import LendSightConfig
        
        client = get_bigquery_client(LendSightConfig.PROJECT_ID)
        
        # Resolve state_code to state name using geo.states
        if len(state_code) == 2:
            state_name_query = f"""
            SELECT state
            FROM geo.states
            WHERE LOWER(state_abbrv) = LOWER('{state_code}')
            LIMIT 1
            """
        else:
            state_name_query = f"""
            SELECT state
            FROM geo.states
            WHERE LOWER(state) = LOWER('{state_code}')
            LIMIT 1
            """
        
        state_job = client.query(state_name_query)
        state_result = list(state_job.result())
        
        if state_result:
            state_name = state_result[0].state
        else:
            state_name = state_code
        
        # Query counties by state name
        query = f"""
        SELECT DISTINCT county_state
        FROM geo.cbsa_to_county 
        WHERE LOWER(state) = LOWER('{state_name}')
        ORDER BY county_state
        """
        query_job = client.query(query)
        results = query_job.result()
        counties = [row.county_state for row in results]
        print(f"✅ Fetched {len(counties)} counties for state {state_code} ({state_name})")
        return jsonify(counties)
    except Exception as e:
        print(f"⚠️  Error fetching counties for state {state_code}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])


@app.route('/years')
def years_route():
    """Return available years dynamically from HMDA data"""
    try:
        from justdata.shared.utils.bigquery_client import get_bigquery_client
        from justdata.core.config.app_config import LendSightConfig
        
        client = get_bigquery_client(LendSightConfig.PROJECT_ID)
        # Query HMDA table for available years (using activity_year field)
        query = """
        SELECT DISTINCT CAST(activity_year AS INT64) as year
        FROM `hdma1-242116.hmda.hmda`
        WHERE activity_year IS NOT NULL
        ORDER BY year ASC
        """
        query_job = client.query(query)
        results = query_job.result()
        years = [row.year for row in results]
        if years:
            print(f"✅ Fetched {len(years)} years from HMDA: {min(years)}-{max(years)}")
        else:
            print("⚠️  No years found in HMDA, using fallback")
            years = list(range(2017, 2025))
        return jsonify(years)
    except Exception as e:
        print(f"⚠️  Error fetching years from HMDA: {e}")
        import traceback
        traceback.print_exc()
        # Fallback
        return jsonify(list(range(2017, 2025)))  # 2017-2024 for lending


# Add favicon routes to prevent 404 errors
@app.route('/favicon.ico')
@app.route('/assets/favicon.ico')
def favicon():
    """Serve favicon or return 204 No Content"""
    return '', 204


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8082))
    app.run(debug=True, host='0.0.0.0', port=port)

