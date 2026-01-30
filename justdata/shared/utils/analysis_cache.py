#!/usr/bin/env python3
"""
BigQuery-based analysis result caching system with section-based storage.
Stores each section (data tables, AI summaries, etc.) separately for better querying.
All results stored as JSON in BigQuery regardless of size.
"""

import hashlib
import json
import os
import uuid
from datetime import datetime
from typing import Dict, Optional, Any, List
from google.cloud import bigquery
from justdata.shared.utils.bigquery_client import get_bigquery_client

# Project and dataset
PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'justdata-ncrc')
DATASET_ID = 'cache'

# Table names
CACHE_TABLE = f'{PROJECT_ID}.{DATASET_ID}.analysis_cache'
USAGE_TABLE = f'{PROJECT_ID}.{DATASET_ID}.usage_log'
RESULTS_TABLE = f'{PROJECT_ID}.{DATASET_ID}.analysis_results'
SECTIONS_TABLE = f'{PROJECT_ID}.{DATASET_ID}.analysis_result_sections'


def sanitize_nan_values(data: Any, precision: int = 4) -> Any:
    """
    Recursively sanitize NaN, Infinity, and other non-JSON-serializable values in data.
    Converts float NaN/Inf to None for proper JSON serialization.
    Also rounds floats to specified precision to avoid BigQuery JSON parsing issues
    with numbers that can't round-trip through string representation.

    Args:
        data: The data to sanitize
        precision: Number of decimal places to round floats to (default: 4)
                   Using 4 instead of 6 to avoid BigQuery PARSE_JSON issues with
                   numbers like 37.181006 that can't round-trip through string representation
    """
    import math

    if isinstance(data, dict):
        return {k: sanitize_nan_values(v, precision) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_nan_values(item, precision) for item in data]
    elif isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            return None
        # Round to avoid BigQuery JSON parsing issues with long decimals
        return round(data, precision)
    elif data is None:
        return None
    else:
        # Check for numpy types if numpy is imported
        try:
            import numpy as np
            if isinstance(data, (np.floating, np.integer)):
                if np.isnan(data) or np.isinf(data):
                    return None
                if isinstance(data, np.floating):
                    return round(float(data), precision)
                return int(data)
            elif isinstance(data, np.ndarray):
                return sanitize_nan_values(data.tolist(), precision)
        except (ImportError, TypeError):
            pass
        return data


def normalize_parameters(app_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize parameters to ensure consistent cache keys.
    Handles different parameter formats across apps.
    """
    normalized = {
        'app': app_name.lower(),
    }
    
    if app_name.lower() == 'branchsight':
        counties = params.get('counties', '')
        if isinstance(counties, str):
            counties_list = [c.strip().lower() for c in counties.split(';') if c.strip()]
            normalized['counties'] = ';'.join(sorted(counties_list))
        else:
            normalized['counties'] = counties
        
        normalized['years'] = params.get('years', '').strip()
        normalized['selection_type'] = params.get('selection_type', 'county').lower()
        normalized['state_code'] = params.get('state_code', '').strip().upper() if params.get('state_code') else None
        normalized['metro_code'] = params.get('metro_code', '').strip() if params.get('metro_code') else None
    
    elif app_name.lower() == 'bizsight':
        county_data = params.get('county_data', {})
        if isinstance(county_data, dict):
            geoid5 = str(county_data.get('geoid5') or county_data.get('GEOID5', '')).zfill(5)
            normalized['geoid5'] = geoid5
        else:
            normalized['county_data'] = county_data
        
        start_year = params.get('startYear') or params.get('start_year')
        end_year = params.get('endYear') or params.get('end_year')
        if start_year and end_year:
            years = sorted(list(range(int(start_year), int(end_year) + 1)))
            normalized['years'] = ','.join(map(str, years))
        else:
            normalized['years'] = params.get('years', '').strip()
    
    elif app_name.lower() == 'mergermeter':
        normalized['acquirer_lei'] = (params.get('acquirer_lei') or '').strip().upper()
        normalized['acquirer_rssd'] = (params.get('acquirer_rssd') or '').strip()
        normalized['target_lei'] = (params.get('target_lei') or '').strip().upper()
        normalized['target_rssd'] = (params.get('target_rssd') or '').strip()
        
        acquirer_aa = params.get('acquirer_assessment_areas', '[]')
        target_aa = params.get('target_assessment_areas', '[]')
        try:
            if isinstance(acquirer_aa, str):
                acquirer_aa = json.loads(acquirer_aa)
            if isinstance(target_aa, str):
                target_aa = json.loads(target_aa)
            normalized['acquirer_aa'] = json.dumps(sorted(acquirer_aa, key=str), sort_keys=True)
            normalized['target_aa'] = json.dumps(sorted(target_aa, key=str), sort_keys=True)
        except:
            normalized['acquirer_aa'] = str(acquirer_aa)
            normalized['target_aa'] = str(target_aa)
        
        normalized['hmda_years'] = ','.join(sorted([y.strip() for y in (params.get('hmda_years') or '').split(',') if y.strip()]))
        normalized['sb_years'] = ','.join(sorted([y.strip() for y in (params.get('sb_years') or '').split(',') if y.strip()]))
        normalized['loan_purpose'] = (params.get('loan_purpose') or '1').strip()
        normalized['action_taken'] = (params.get('action_taken') or '1').strip()
        normalized['occupancy_type'] = (params.get('occupancy_type') or '1').strip()
        normalized['total_units'] = (params.get('total_units') or '1-4').strip()
        normalized['construction_method'] = (params.get('construction_method') or '1').strip()
        normalized['not_reverse'] = (params.get('not_reverse') or '1').strip()
    
    elif app_name.lower() == 'lendsight':
        counties = params.get('counties', '')
        if isinstance(counties, str):
            counties_list = [c.strip().lower() for c in counties.split(';') if c.strip()]
            normalized['counties'] = ';'.join(sorted(counties_list))
        normalized['years'] = params.get('years', '').strip()
    
    elif app_name.lower() == 'branchmapper':
        counties = params.get('counties', '')
        if isinstance(counties, str):
            counties_list = [c.strip().lower() for c in counties.split(';') if c.strip()]
            normalized['counties'] = ';'.join(sorted(counties_list))
        normalized['years'] = params.get('years', '').strip()
    
    return normalized


def generate_cache_key(app_name: str, params: Dict[str, Any]) -> str:
    """Generate a unique cache key from normalized parameters."""
    normalized = normalize_parameters(app_name, params)
    cache_string = json.dumps(normalized, sort_keys=True, default=str)
    cache_key = hashlib.sha256(cache_string.encode('utf-8')).hexdigest()
    return f"{app_name.lower()}_{cache_key}"


def extract_sections(app_name: str, result_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract sections from result data based on app structure.
    Returns list of section dictionaries ready for BigQuery insertion.
    """
    sections = []
    display_order = 1
    
    if app_name.lower() == 'branchsight':
        # Data tables
        report_data = result_data.get('report_data', {})
        import pandas as pd
        import numpy as np
        for table_name in ['by_county', 'by_bank', 'summary', 'trends']:
            if table_name in report_data:
                df = report_data[table_name]
                if hasattr(df, 'to_dict'):
                    # Replace all NaN types before converting to dict
                    df_cleaned = df.replace({pd.NA: None, pd.NaT: None})
                    df_cleaned = df_cleaned.replace({np.nan: None})
                    # Convert any remaining NaN values to None using where()
                    df_cleaned = df_cleaned.where(pd.notnull(df_cleaned), None)
                    sections.append({
                        'section_name': table_name,
                        'section_type': 'data_table',
                        'section_category': 'tables',
                        'section_data': df_cleaned.to_dict('records'),
                        'section_metadata': {
                            'columns': list(df.columns) if hasattr(df, 'columns') else [],
                            'row_count': len(df) if hasattr(df, '__len__') else 0
                        },
                        'display_order': display_order
                    })
                    display_order += 1
        
        # HHI data
        if 'hhi' in report_data:
            hhi_data = report_data['hhi']
            sections.append({
                'section_name': 'hhi',
                'section_type': 'data_table',
                'section_category': 'metrics',
                'section_data': hhi_data if isinstance(hhi_data, dict) else {'hhi': hhi_data},
                'section_metadata': {'data_type': 'hhi_metric'},
                'display_order': display_order
            })
            display_order += 1
        
        # Raw data (optional, can be large)
        if 'raw_data' in report_data:
            df = report_data['raw_data']
            if hasattr(df, 'to_dict'):
                sections.append({
                    'section_name': 'raw_data',
                    'section_type': 'raw_data',
                    'section_category': 'raw',
                    'section_data': df.to_dict('records'),
                    'section_metadata': {
                        'columns': list(df.columns) if hasattr(df, 'columns') else [],
                        'row_count': len(df) if hasattr(df, '__len__') else 0
                    },
                    'display_order': display_order
                })
                display_order += 1
        
        # AI insights
        ai_insights = result_data.get('ai_insights', {})
        for insight_name in ['executive_summary', 'key_findings']:
            if insight_name in ai_insights:
                sections.append({
                    'section_name': insight_name,
                    'section_type': 'ai_summary',
                    'section_category': 'ai_insights',
                    'section_data': {'text': ai_insights[insight_name]},
                    'section_metadata': {
                        'word_count': len(ai_insights[insight_name].split()) if isinstance(ai_insights[insight_name], str) else 0
                    },
                    'display_order': display_order
                })
                display_order += 1
        
        for insight_name in ['trends_analysis', 'bank_strategies', 'community_impact']:
            if insight_name in ai_insights:
                sections.append({
                    'section_name': insight_name,
                    'section_type': 'ai_narrative',
                    'section_category': 'ai_insights',
                    'section_data': {'text': ai_insights[insight_name]},
                    'section_metadata': {
                        'word_count': len(ai_insights[insight_name].split()) if isinstance(ai_insights[insight_name], str) else 0
                    },
                    'display_order': display_order
                })
                display_order += 1
        
        # Table introductions and narratives (nested)
        if 'table_introductions' in ai_insights:
            for table_name, intro_text in ai_insights['table_introductions'].items():
                sections.append({
                    'section_name': f'table_introduction_{table_name}',
                    'section_type': 'ai_narrative',
                    'section_category': 'ai_insights',
                    'section_data': {'text': intro_text, 'table': table_name},
                    'section_metadata': {'word_count': len(intro_text.split()) if isinstance(intro_text, str) else 0},
                    'display_order': display_order
                })
                display_order += 1
        
        if 'table_narratives' in ai_insights:
            for table_name, narrative_text in ai_insights['table_narratives'].items():
                sections.append({
                    'section_name': f'table_narrative_{table_name}',
                    'section_type': 'ai_narrative',
                    'section_category': 'ai_insights',
                    'section_data': {'text': narrative_text, 'table': table_name},
                    'section_metadata': {'word_count': len(narrative_text.split()) if isinstance(narrative_text, str) else 0},
                    'display_order': display_order
                })
                display_order += 1
    
    elif app_name.lower() == 'bizsight':
        # Data tables - sanitize NaN values before storing
        for table_name in ['county_summary_table', 'comparison_table', 'top_lenders_table']:
            if table_name in result_data:
                table_data = result_data[table_name]
                if isinstance(table_data, list):
                    # Sanitize NaN values to prevent JSON serialization errors
                    sanitized_data = sanitize_nan_values(table_data)
                    sections.append({
                        'section_name': table_name,
                        'section_type': 'data_table',
                        'section_category': 'tables',
                        'section_data': sanitized_data,
                        'section_metadata': {
                            'row_count': len(table_data),
                            'columns': list(table_data[0].keys()) if table_data else []
                        },
                        'display_order': display_order
                    })
                    display_order += 1

        # HHI data
        if 'hhi' in result_data and result_data['hhi']:
            sections.append({
                'section_name': 'hhi',
                'section_type': 'data_table',
                'section_category': 'metrics',
                'section_data': sanitize_nan_values(result_data['hhi']),
                'section_metadata': {'data_type': 'hhi_metric'},
                'display_order': display_order
            })
            display_order += 1

        if 'hhi_by_year' in result_data:
            sections.append({
                'section_name': 'hhi_by_year',
                'section_type': 'data_table',
                'section_category': 'metrics',
                'section_data': sanitize_nan_values(result_data['hhi_by_year']),
                'section_metadata': {'row_count': len(result_data['hhi_by_year'])},
                'display_order': display_order
            })
            display_order += 1

        # Geographic data
        if 'tract_data_for_map' in result_data:
            sections.append({
                'section_name': 'tract_data_for_map',
                'section_type': 'data_table',
                'section_category': 'geographic',
                'section_data': sanitize_nan_values(result_data['tract_data_for_map']),
                'section_metadata': {'row_count': len(result_data['tract_data_for_map'])},
                'display_order': display_order
            })
            display_order += 1

        # Summary table (displayed next to the map)
        if 'summary_table' in result_data:
            sections.append({
                'section_name': 'summary_table',
                'section_type': 'data_table',
                'section_category': 'summary',
                'section_data': sanitize_nan_values(result_data['summary_table']),
                'section_metadata': {'data_type': 'summary_statistics'},
                'display_order': display_order
            })
            display_order += 1

        # Metadata
        if 'metadata' in result_data:
            sections.append({
                'section_name': 'metadata',
                'section_type': 'metadata',
                'section_category': 'metadata',
                'section_data': sanitize_nan_values(result_data['metadata']),
                'section_metadata': {},
                'display_order': display_order
            })
            display_order += 1

        # AI insights - include both legacy and new split insight names
        ai_insights = result_data.get('ai_insights', {})
        ai_insight_names = [
            # Legacy names (combined discussions)
            'county_summary_discussion', 'comparison_discussion',
            'top_lenders_discussion', 'hhi_trends_discussion',
            # New split names (separate number and amount discussions)
            'county_summary_number_discussion', 'county_summary_amount_discussion',
            'comparison_number_discussion', 'comparison_amount_discussion',
            'top_lenders_number_discussion', 'top_lenders_amount_discussion',
            # Key findings
            'key_findings'
        ]
        for insight_name in ai_insight_names:
            if insight_name in ai_insights and ai_insights[insight_name]:
                sections.append({
                    'section_name': insight_name,
                    'section_type': 'ai_narrative',
                    'section_category': 'ai_insights',
                    'section_data': {'text': ai_insights[insight_name]},
                    'section_metadata': {
                        'word_count': len(ai_insights[insight_name].split()) if isinstance(ai_insights[insight_name], str) else 0
                    },
                    'display_order': display_order
                })
                display_order += 1
    
    elif app_name.lower() == 'mergermeter':
        # Excel sheets as data tables
        report_data = result_data.get('report_data', {})
        for sheet_name, sheet_data in report_data.items():
            if isinstance(sheet_data, dict) and 'data' in sheet_data:
                sections.append({
                    'section_name': sheet_name,
                    'section_type': 'data_table',
                    'section_category': 'tables',
                    'section_data': sheet_data['data'],
                    'section_metadata': {
                        'headers': sheet_data.get('headers', []),
                        'row_count': len(sheet_data['data'])
                    },
                    'display_order': display_order
                })
                display_order += 1
    
    elif app_name.lower() == 'lendsight':
        # LendSight structure - report_data contains pandas DataFrames
        report_data = result_data.get('report_data', {})
        if isinstance(report_data, dict):
            import pandas as pd

            # Handle hhi separately as a metrics section
            if 'hhi' in report_data and report_data['hhi']:
                hhi_data = report_data['hhi']
                sections.append({
                    'section_name': 'hhi',
                    'section_type': 'data_table',
                    'section_category': 'metrics',
                    'section_data': hhi_data if isinstance(hhi_data, dict) else {'hhi': hhi_data},
                    'section_metadata': {'data_type': 'hhi_metric'},
                    'display_order': display_order
                })
                display_order += 1

            # NOTE: raw_data is NOT stored - it's too large (can be 20k+ records)
            # Excel exports will need to regenerate data from original query
            # or use the stored summary tables instead

            for key, value in report_data.items():
                # Skip items we've already handled or that are stored elsewhere
                # Note: census_data is stored in result_summary
                if key in ['census_data', 'hhi', 'raw_data']:
                    continue
                
                # Convert DataFrame to list of dicts if needed
                if isinstance(value, pd.DataFrame):
                    if not value.empty:
                        import numpy as np
                        # Replace all NaN types before converting to dict
                        # This handles pd.NA, pd.NaT, np.nan, and any other NaN values
                        df_cleaned = value.replace({pd.NA: None, pd.NaT: None})
                        df_cleaned = df_cleaned.replace({np.nan: None})
                        # Convert any remaining NaN values to None using where()
                        df_cleaned = df_cleaned.where(pd.notnull(df_cleaned), None)
                        sections.append({
                            'section_name': key,
                            'section_type': 'data_table',
                            'section_category': 'tables',
                            'section_data': df_cleaned.to_dict('records'),
                            'section_metadata': {
                                'row_count': len(value),
                                'columns': list(value.columns)
                            },
                            'display_order': display_order
                        })
                        display_order += 1
                elif isinstance(value, list):
                    # Already a list
                    sections.append({
                        'section_name': key,
                        'section_type': 'data_table',
                        'section_category': 'tables',
                        'section_data': value,
                        'section_metadata': {'row_count': len(value)},
                        'display_order': display_order
                    })
                    display_order += 1
                elif isinstance(value, dict) and value:
                    # Dict data (like hhi) - but we skip hhi above, so this handles other dicts
                    sections.append({
                        'section_name': key,
                        'section_type': 'data_table',
                        'section_category': 'metrics',
                        'section_data': value,
                        'section_metadata': {},
                        'display_order': display_order
                    })
                    display_order += 1
        
        # AI insights for LendSight
        ai_insights = result_data.get('ai_insights', {})
        if isinstance(ai_insights, dict):
            # Extract all AI insights
            for insight_name, insight_value in ai_insights.items():
                if isinstance(insight_value, str):
                    # Simple text insights
                    sections.append({
                        'section_name': insight_name,
                        'section_type': 'ai_summary' if insight_name in ['executive_summary', 'key_findings'] else 'ai_narrative',
                        'section_category': 'ai_insights',
                        'section_data': {'text': insight_value},
                        'section_metadata': {
                            'word_count': len(insight_value.split()) if isinstance(insight_value, str) else 0
                        },
                        'display_order': display_order
                    })
                    display_order += 1
                elif isinstance(insight_value, dict):
                    # Nested structures like table_introductions, table_narratives
                    if insight_name in ['table_introductions', 'table_narratives']:
                        for table_name, text in insight_value.items():
                            section_type = 'ai_narrative'
                            prefix = 'table_introduction_' if insight_name == 'table_introductions' else 'table_narrative_'
                            sections.append({
                                'section_name': f'{prefix}{table_name}',
                                'section_type': section_type,
                                'section_category': 'ai_insights',
                                'section_data': {'text': text, 'table': table_name},
                                'section_metadata': {
                                    'word_count': len(text.split()) if isinstance(text, str) else 0
                                },
                                'display_order': display_order
                            })
                            display_order += 1
                    else:
                        # Other nested dicts - store as-is
                        sections.append({
                            'section_name': insight_name,
                            'section_type': 'ai_narrative',
                            'section_category': 'ai_insights',
                            'section_data': insight_value,
                            'section_metadata': {},
                            'display_order': display_order
                        })
                        display_order += 1
    
    elif app_name.lower() == 'branchmapper':
        # BranchMapper structure (to be implemented based on actual structure)
        report_data = result_data.get('report_data', {})
        if isinstance(report_data, dict):
            for key, value in report_data.items():
                if isinstance(value, list):
                    sections.append({
                        'section_name': key,
                        'section_type': 'data_table',
                        'section_category': 'tables',
                        'section_data': value,
                        'section_metadata': {'row_count': len(value)},
                        'display_order': display_order
                    })
                    display_order += 1
    
    return sections


def get_cached_result(app_name: str, params: Dict[str, Any], 
                     user_type: str = 'public') -> Optional[Dict[str, Any]]:
    """
    Check if a cached result exists and retrieve it with all sections.
    Returns None if cache miss, or dict with 'job_id', 'result_data', 'cache_key' if cache hit.
    """
    cache_key = generate_cache_key(app_name, params)
    client = get_bigquery_client(PROJECT_ID)
    
    # Check cache
    cache_query = f"""
    SELECT 
        c.job_id,
        c.cache_key,
        c.access_count,
        r.status
    FROM `{CACHE_TABLE}` c
    INNER JOIN `{RESULTS_TABLE}` r ON c.job_id = r.job_id
    WHERE c.cache_key = @cache_key
        AND (c.expires_at IS NULL OR c.expires_at > CURRENT_TIMESTAMP())
        AND r.status = 'completed'
    LIMIT 1
    """
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("cache_key", "STRING", cache_key)
        ]
    )
    
    try:
        query_job = client.query(cache_query, job_config=job_config)
        cache_results = list(query_job.result())
        
        if not cache_results:
            return None
        
        cache_row = cache_results[0]
        job_id = cache_row.job_id
        
        # Get all sections for this job
        sections_query = f"""
        SELECT 
            section_name,
            section_type,
            section_category,
            section_data,
            section_metadata,
            display_order
        FROM `{SECTIONS_TABLE}`
        WHERE job_id = @job_id
        ORDER BY display_order ASC
        """
        
        sections_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("job_id", "STRING", job_id)
            ]
        )
        
        sections_job = client.query(sections_query, job_config=sections_config)
        sections_rows = list(sections_job.result())

        # Validate that we have enough sections for a complete result
        # LendSight should have at least 5 sections (summary, demographic_overview, etc.)
        # If not, the cache entry is incomplete and should be ignored
        min_sections = {'lendsight': 5, 'branchsight': 3, 'bizsight': 3, 'mergermeter': 2}
        min_count = min_sections.get(app_name.lower(), 2)
        if len(sections_rows) < min_count:
            print(f"[WARNING] Cache entry has only {len(sections_rows)} sections, expected at least {min_count}. Ignoring incomplete cache.")
            return None
        
        # Reconstruct result_data from sections
        result_data = {}
        report_data = {}
        ai_insights = {}
        
        for row in sections_rows:
            section_name = row.section_name
            section_type = row.section_type
            section_data = json.loads(row.section_data) if isinstance(row.section_data, str) else row.section_data
            
            if section_type == 'data_table' or section_type == 'raw_data':
                # Store in report_data
                if app_name.lower() == 'mergermeter':
                    # MergerMeter stores sheets with headers
                    metadata = json.loads(row.section_metadata) if isinstance(row.section_metadata, str) else row.section_metadata
                    report_data[section_name] = {
                        'headers': metadata.get('headers', []),
                        'data': section_data
                    }
                else:
                    report_data[section_name] = section_data
            elif section_type in ['ai_summary', 'ai_narrative']:
                # Store in ai_insights
                if 'text' in section_data:
                    # Handle nested table introductions/narratives
                    if section_name.startswith('table_introduction_'):
                        table_name = section_name.replace('table_introduction_', '')
                        if 'table_introductions' not in ai_insights:
                            ai_insights['table_introductions'] = {}
                        ai_insights['table_introductions'][table_name] = section_data['text']
                    elif section_name.startswith('table_narrative_'):
                        table_name = section_name.replace('table_narrative_', '')
                        if 'table_narratives' not in ai_insights:
                            ai_insights['table_narratives'] = {}
                        ai_insights['table_narratives'][table_name] = section_data['text']
                    else:
                        ai_insights[section_name] = section_data['text']
                else:
                    ai_insights[section_name] = section_data
        
        result_data['report_data'] = report_data
        result_data['ai_insights'] = ai_insights
        
        # Update cache access stats
        update_query = f"""
        UPDATE `{CACHE_TABLE}`
        SET 
            last_accessed = CURRENT_TIMESTAMP(),
            access_count = access_count + 1
        WHERE cache_key = @cache_key
        """
        client.query(update_query, job_config=job_config).result()
        
        return {
            'job_id': job_id,
            'cache_key': cache_row.cache_key,
            'result_data': result_data,
            'cached': True,
            'access_count': cache_row.access_count
        }
        
    except Exception as e:
        print(f"Error checking cache: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_analysis_result_by_job_id(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve analysis result from BigQuery by job_id.
    Returns None if not found, or dict with 'report_data', 'ai_insights', 'metadata' if found.
    This is the primary method for retrieving results - BigQuery-only, no in-memory storage.
    """
    client = get_bigquery_client(PROJECT_ID)
    
    # Query BigQuery for this job_id
    query = f"""
    SELECT 
        r.result_summary,
        r.sections_summary,
        r.status,
        s.section_name,
        s.section_type,
        s.section_category,
        s.section_data,
        s.section_metadata,
        s.display_order
    FROM `{RESULTS_TABLE}` r
    LEFT JOIN `{SECTIONS_TABLE}` s ON r.job_id = s.job_id
    WHERE r.job_id = @job_id
        AND r.status = 'completed'
    ORDER BY s.display_order ASC
    """
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("job_id", "STRING", job_id)
        ]
    )
    
    try:
        query_job = client.query(query, job_config=job_config)
        rows = list(query_job.result())
        
        if not rows:
            return None
        
        # Reconstruct result from sections
        report_data = {}
        ai_insights = {}
        metadata = {}
        
        # Get metadata from first row's result_summary
        if rows[0].result_summary:
            summary = json.loads(rows[0].result_summary) if isinstance(rows[0].result_summary, str) else rows[0].result_summary
            census_data_retrieved = summary.get('census_data', None)
            # Only use census_data if it has actual content (not empty dict)
            if census_data_retrieved and (not isinstance(census_data_retrieved, dict) or len(census_data_retrieved) > 0):
                census_data_final = census_data_retrieved
            else:
                census_data_final = None
            
            print(f"[DEBUG] Retrieved census_data: type={type(census_data_final)}, value={census_data_final if not isinstance(census_data_final, dict) or len(census_data_final) <= 3 else f'dict with {len(census_data_final)} keys'}")
            
            # Extract county and year info
            counties_list = summary.get('counties', [])
            years_list = summary.get('years', [])

            # Construct county_name from counties list
            county_name = ''
            if counties_list:
                first_county = counties_list[0]
                if isinstance(first_county, dict):
                    county_name = first_county.get('name', '')
                elif isinstance(first_county, str):
                    county_name = first_county

            # Construct year_range from years list
            year_range = ''
            if years_list:
                sorted_years = sorted(years_list)
                if len(sorted_years) == 1:
                    year_range = str(sorted_years[0])
                else:
                    year_range = f"{sorted_years[0]}-{sorted_years[-1]}"

            metadata = {
                'counties': counties_list,
                'years': years_list,
                'county_name': county_name,
                'year_range': year_range,
                'generated_at': summary.get('created_at', ''),
                'app_name': summary.get('app_name', ''),
                'total_records': summary.get('total_records', 0),
                'loan_purpose': summary.get('loan_purpose', ['purchase']),
                'census_data': census_data_final
            }
        else:
            # Default metadata if result_summary is missing
            metadata = {
                'counties': [],
                'years': [],
                'county_name': '',
                'year_range': '',
                'generated_at': '',
                'app_name': '',
                'total_records': 0,
                'loan_purpose': ['purchase'],
                'census_data': None
            }
        
        # Reconstruct sections
        print(f"[DEBUG] Reconstructing from {len(rows)} rows...")
        for row in rows:
            if row.section_name:
                print(f"[DEBUG] Processing section: {row.section_name} (type: {row.section_type})")
                section_data = json.loads(row.section_data) if isinstance(row.section_data, str) else row.section_data
                
                if row.section_type in ['data_table', 'raw_data']:
                    # Handle MergerMeter format with headers
                    if isinstance(section_data, dict) and 'headers' in section_data:
                        report_data[row.section_name] = section_data
                    else:
                        report_data[row.section_name] = section_data
                    print(f"[DEBUG] Added to report_data: {row.section_name}")
                elif row.section_type in ['ai_summary', 'ai_narrative']:
                    print(f"[DEBUG] AI section - section_data type: {type(section_data)}, keys: {section_data.keys() if isinstance(section_data, dict) else 'N/A'}")
                    if isinstance(section_data, dict) and 'text' in section_data:
                        # Handle nested table introductions/narratives
                        if row.section_name.startswith('table_introduction_'):
                            table_name = row.section_name.replace('table_introduction_', '')
                            if 'table_introductions' not in ai_insights:
                                ai_insights['table_introductions'] = {}
                            ai_insights['table_introductions'][table_name] = section_data['text']
                            print(f"[DEBUG] Added table_introduction for {table_name}, length: {len(section_data['text']) if section_data['text'] else 0}")
                        elif row.section_name.startswith('table_narrative_'):
                            table_name = row.section_name.replace('table_narrative_', '')
                            if 'table_narratives' not in ai_insights:
                                ai_insights['table_narratives'] = {}
                            ai_insights['table_narratives'][table_name] = section_data['text']
                            print(f"[DEBUG] Added table_narrative for {table_name}, length: {len(section_data['text']) if section_data['text'] else 0}")
                        else:
                            ai_insights[row.section_name] = section_data['text']
                            print(f"[DEBUG] Added AI insight: {row.section_name}, length: {len(section_data['text']) if section_data['text'] else 0}")
                    else:
                        # Store as-is if not in expected format
                        ai_insights[row.section_name] = section_data
                        print(f"[DEBUG] Added AI insight (raw): {row.section_name}, type: {type(section_data)}")
                elif row.section_type == 'metadata':
                    # Merge stored metadata with default metadata
                    if isinstance(section_data, dict):
                        metadata.update(section_data)
                        print(f"[DEBUG] Merged metadata from section: {row.section_name}")
                else:
                    print(f"[DEBUG] Unknown section type: {row.section_type}, skipping")

        # Determine app name from metadata
        app_name = metadata.get('app_name', '').lower()

        # For BizSight, flatten the result to match frontend expectations
        # The frontend expects data.summary_table, data.hhi, etc. at the top level
        if app_name == 'bizsight':
            result = {
                'success': True,
                'report_data': report_data.get('report_data', {}),  # Nested report_data if present
                'ai_insights': ai_insights,
                'metadata': metadata,
                # Flatten BizSight-specific fields to top level
                'summary_table': report_data.get('summary_table', {}),
                'tract_data_for_map': report_data.get('tract_data_for_map', []),
                'county_summary_table': report_data.get('county_summary_table', []),
                'comparison_table': report_data.get('comparison_table', []),
                'top_lenders_table': report_data.get('top_lenders_table', []),
                'hhi': report_data.get('hhi', None),
                'hhi_by_year': report_data.get('hhi_by_year', []),
            }
        else:
            result = {
                'report_data': report_data,
                'ai_insights': ai_insights,
                'metadata': metadata
            }

        # Debug logging
        print(f"[DEBUG] get_analysis_result_by_job_id returning (app: {app_name}):")
        if app_name == 'bizsight':
            print(f"  - summary_table keys: {list(result.get('summary_table', {}).keys()) if isinstance(result.get('summary_table'), dict) else 'N/A'}")
            print(f"  - county_summary_table length: {len(result.get('county_summary_table', []))}")
            print(f"  - comparison_table length: {len(result.get('comparison_table', []))}")
            print(f"  - top_lenders_table length: {len(result.get('top_lenders_table', []))}")
            print(f"  - hhi: {result.get('hhi')}")
            print(f"  - hhi_by_year length: {len(result.get('hhi_by_year', []))}")
            print(f"  - tract_data_for_map length: {len(result.get('tract_data_for_map', []))}")
        else:
            print(f"  - report_data keys: {list(report_data.keys())}")
        print(f"  - ai_insights keys: {list(ai_insights.keys())}")
        print(f"  - metadata keys: {list(metadata.keys())}")

        return result
        
    except Exception as e:
        print(f"Error retrieving analysis result by job_id from BigQuery: {e}")
        import traceback
        traceback.print_exc()
        return None


def store_cached_result(app_name: str, params: Dict[str, Any],
                       job_id: str, result_data: Dict[str, Any],
                       user_type: str = 'public',
                       metadata: Optional[Dict[str, Any]] = None) -> None:
    """
    Store analysis result in BigQuery with section-based storage.
    If a cache entry with the same cache_key already exists (e.g., force_refresh),
    the old entry and its associated data are deleted first.
    """
    cache_key = generate_cache_key(app_name, params)
    normalized_params = normalize_parameters(app_name, params)
    client = get_bigquery_client(PROJECT_ID)

    # Delete any existing cache entry with the same cache_key (for force_refresh scenarios)
    # This also requires deleting associated results and sections to maintain referential integrity
    try:
        # First, get the old job_id if it exists
        old_job_query = f"""
        SELECT job_id FROM `{CACHE_TABLE}` WHERE cache_key = @cache_key
        """
        old_job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("cache_key", "STRING", cache_key)
            ]
        )
        old_job_result = list(client.query(old_job_query, job_config=old_job_config).result())

        if old_job_result:
            old_job_id = old_job_result[0].job_id
            print(f"[INFO] Found existing cache entry for cache_key {cache_key[:16]}... with job_id {old_job_id}. Deleting old data.")

            # Delete old sections
            delete_sections_query = f"""
            DELETE FROM `{SECTIONS_TABLE}` WHERE job_id = @old_job_id
            """
            sections_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("old_job_id", "STRING", old_job_id)
                ]
            )
            client.query(delete_sections_query, job_config=sections_config).result()

            # Delete old results
            delete_results_query = f"""
            DELETE FROM `{RESULTS_TABLE}` WHERE job_id = @old_job_id
            """
            client.query(delete_results_query, job_config=sections_config).result()

            # Delete old cache entry
            delete_cache_query = f"""
            DELETE FROM `{CACHE_TABLE}` WHERE cache_key = @cache_key
            """
            client.query(delete_cache_query, job_config=old_job_config).result()

            print(f"[OK] Deleted old cache entry and associated data for job_id {old_job_id}")
    except Exception as cleanup_error:
        print(f"[WARNING] Error during cache cleanup (non-fatal): {cleanup_error}")
    
    # Extract sections
    sections = extract_sections(app_name, result_data)
    
    # Prepare result summary - include all metadata fields
    census_data_value = metadata.get('census_data', None) if metadata else None
    # Only store census_data if it has actual content (not empty dict)
    if census_data_value and (not isinstance(census_data_value, dict) or len(census_data_value) > 0):
        census_data_to_store = census_data_value
    else:
        census_data_to_store = None
    
    print(f"[DEBUG] Storing census_data: type={type(census_data_to_store)}, is_empty={census_data_to_store == {} or census_data_to_store is None}, has_keys={list(census_data_to_store.keys()) if isinstance(census_data_to_store, dict) else 'N/A'}")
    
    result_summary = {
        'counties': metadata.get('counties', []) if metadata else [],
        'years': metadata.get('years', []) if metadata else [],
        'created_at': datetime.now().isoformat(),
        'app_name': app_name,
        'total_records': metadata.get('total_records', 0) if metadata else 0,
        'loan_purpose': metadata.get('loan_purpose', ['purchase']) if metadata else ['purchase'],
        'census_data': census_data_to_store
    }
    
    # Prepare sections summary (quick reference)
    sections_summary = [
        {
            'section_name': s['section_name'],
            'section_type': s['section_type'],
            'section_category': s.get('section_category'),
            'display_order': s.get('display_order', 0)
        }
        for s in sections
    ]
    
    params_hash = hashlib.sha256(json.dumps(normalized_params, sort_keys=True).encode()).hexdigest()
    
    # Calculate total result size
    total_size = len(json.dumps(result_data, default=str).encode('utf-8'))
    
    # Insert into cache table
    cache_insert = f"""
    INSERT INTO `{CACHE_TABLE}`
    (cache_key, app_name, job_id, parameters_hash, parameters_json, 
     created_at, created_by_user_type, last_accessed, access_count,
     result_size_bytes, cost_saved_usd, expires_at)
    VALUES
    (@cache_key, @app_name, @job_id, @params_hash, PARSE_JSON(@params_json),
     CURRENT_TIMESTAMP(), @user_type, CURRENT_TIMESTAMP(), 0,
     @result_size, 0.0, NULL)
    """
    
    # Insert into results table
    results_insert = f"""
    INSERT INTO `{RESULTS_TABLE}`
    (job_id, app_name, cache_key, result_summary, sections_summary,
     created_at, created_by_user_type, analysis_duration_seconds,
     bigquery_queries_count, ai_calls_count, status, error_message)
    VALUES
    (@job_id, @app_name, @cache_key, PARSE_JSON(@result_summary), PARSE_JSON(@sections_summary),
     CURRENT_TIMESTAMP(), @user_type, @duration,
     @bq_queries, @ai_calls, @status, @error)
    """
    
    job_config_cache = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("cache_key", "STRING", cache_key),
            bigquery.ScalarQueryParameter("app_name", "STRING", app_name.lower()),
            bigquery.ScalarQueryParameter("job_id", "STRING", job_id),
            bigquery.ScalarQueryParameter("params_hash", "STRING", params_hash),
            bigquery.ScalarQueryParameter("params_json", "STRING", json.dumps(normalized_params)),
            bigquery.ScalarQueryParameter("user_type", "STRING", user_type),
            bigquery.ScalarQueryParameter("result_size", "INT64", total_size),
        ]
    )
    
    job_config_results = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("job_id", "STRING", job_id),
            bigquery.ScalarQueryParameter("app_name", "STRING", app_name.lower()),
            bigquery.ScalarQueryParameter("cache_key", "STRING", cache_key),
            bigquery.ScalarQueryParameter("result_summary", "STRING", json.dumps(result_summary)),
            bigquery.ScalarQueryParameter("sections_summary", "STRING", json.dumps(sections_summary)),
            bigquery.ScalarQueryParameter("user_type", "STRING", user_type),
            bigquery.ScalarQueryParameter("duration", "FLOAT64", metadata.get('duration_seconds', 0.0) if metadata else 0.0),
            bigquery.ScalarQueryParameter("bq_queries", "INT64", metadata.get('bq_queries_count', 0) if metadata else 0),
            bigquery.ScalarQueryParameter("ai_calls", "INT64", metadata.get('ai_calls_count', 0) if metadata else 0),
            bigquery.ScalarQueryParameter("status", "STRING", "completed"),
            bigquery.ScalarQueryParameter("error", "STRING", None),
        ]
    )
    
    try:
        # Insert cache entry
        client.query(cache_insert, job_config=job_config_cache).result()
        
        # Insert result summary
        client.query(results_insert, job_config=job_config_results).result()
        
        # Insert each section
        print(f"[DEBUG] Storing {len(sections)} sections to BigQuery...")
        for idx, section in enumerate(sections):
            section_id = str(uuid.uuid4())
            section_insert = f"""
            INSERT INTO `{SECTIONS_TABLE}`
            (section_id, job_id, app_name, section_type, section_name, section_category,
             section_data, section_metadata, display_order, created_at, updated_at)
            VALUES
            (@section_id, @job_id, @app_name, @section_type, @section_name, @section_category,
             PARSE_JSON(@section_data), PARSE_JSON(@section_metadata), @display_order, 
             CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())
            """
            
            section_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("section_id", "STRING", section_id),
                    bigquery.ScalarQueryParameter("job_id", "STRING", job_id),
                    bigquery.ScalarQueryParameter("app_name", "STRING", app_name.lower()),
                    bigquery.ScalarQueryParameter("section_type", "STRING", section['section_type']),
                    bigquery.ScalarQueryParameter("section_name", "STRING", section['section_name']),
                    bigquery.ScalarQueryParameter("section_category", "STRING", section.get('section_category')),
                    bigquery.ScalarQueryParameter("section_data", "STRING", json.dumps(section['section_data'], default=str)),
                    bigquery.ScalarQueryParameter("section_metadata", "STRING", json.dumps(section.get('section_metadata', {}))),
                    bigquery.ScalarQueryParameter("display_order", "INT64", section.get('display_order', 0)),
                ]
            )
            
            try:
                client.query(section_insert, job_config=section_config).result()
                print(f"  [OK] Stored section {idx+1}/{len(sections)}: {section['section_name']}")
            except Exception as section_error:
                print(f"  [ERROR] Failed to store section {section['section_name']}: {section_error}")
                raise

        print(f"[OK] Stored cache entry, result summary, and {len(sections)} sections for job_id: {job_id}")

    except Exception as e:
        print(f"[ERROR] Error storing in BigQuery: {e}")
        import traceback
        traceback.print_exc()
        raise


def log_usage(user_type: str, app_name: str, params: Dict[str, Any],
             cache_key: str, cache_hit: bool, job_id: str,
             response_time_ms: int = 0,
             costs: Optional[Dict[str, float]] = None,
             error_message: Optional[str] = None,
             request_id: Optional[str] = None,
             user_id: Optional[str] = None,
             user_email: Optional[str] = None,
             ip_address: Optional[str] = None,
             user_agent: Optional[str] = None) -> None:
    """
    Log usage to BigQuery usage_log table.
    
    Args:
        user_type: Type of user (admin, staff, member, etc.)
        app_name: Name of the app (lendsight, bizsight, etc.)
        params: Analysis parameters
        cache_key: Cache key for the request
        cache_hit: Whether the result was served from cache
        job_id: Unique job identifier
        response_time_ms: Response time in milliseconds
        costs: Dict with 'bigquery', 'ai', 'total' costs
        error_message: Error message if request failed
        request_id: Unique request identifier
        user_id: Firebase Auth UID (for analytics tracking)
        user_email: User's email address (for analytics tracking)
        ip_address: Client IP address (for geolocation)
        user_agent: Client user agent string
    """
    if request_id is None:
        request_id = str(uuid.uuid4())
    
    client = get_bigquery_client(PROJECT_ID)
    
    costs = costs or {}
    
    insert_query = f"""
    INSERT INTO `{USAGE_TABLE}`
    (request_id, timestamp, user_type, app_name, parameters_json,
     cache_key, cache_hit, job_id, response_time_ms,
     bigquery_cost_usd, ai_cost_usd, total_cost_usd, error_message,
     user_id, user_email, ip_address, user_agent)
    VALUES
    (@request_id, CURRENT_TIMESTAMP(), @user_type, @app_name, PARSE_JSON(@params_json),
     @cache_key, @cache_hit, @job_id, @response_time,
     @bq_cost, @ai_cost, @total_cost, @error,
     @user_id, @user_email, @ip_address, @user_agent)
    """
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("request_id", "STRING", request_id),
            bigquery.ScalarQueryParameter("user_type", "STRING", user_type),
            bigquery.ScalarQueryParameter("app_name", "STRING", app_name.lower()),
            bigquery.ScalarQueryParameter("params_json", "STRING", json.dumps(params)),
            bigquery.ScalarQueryParameter("cache_key", "STRING", cache_key),
            bigquery.ScalarQueryParameter("cache_hit", "BOOL", cache_hit),
            bigquery.ScalarQueryParameter("job_id", "STRING", job_id),
            bigquery.ScalarQueryParameter("response_time", "INT64", response_time_ms),
            bigquery.ScalarQueryParameter("bq_cost", "FLOAT64", costs.get('bigquery', 0.0)),
            bigquery.ScalarQueryParameter("ai_cost", "FLOAT64", costs.get('ai', 0.0)),
            bigquery.ScalarQueryParameter("total_cost", "FLOAT64", costs.get('total', 0.0)),
            bigquery.ScalarQueryParameter("error", "STRING", error_message),
            bigquery.ScalarQueryParameter("user_id", "STRING", user_id),
            bigquery.ScalarQueryParameter("user_email", "STRING", user_email),
            bigquery.ScalarQueryParameter("ip_address", "STRING", ip_address),
            bigquery.ScalarQueryParameter("user_agent", "STRING", user_agent),
        ]
    )
    
    try:
        client.query(insert_query, job_config=job_config).result()
    except Exception as e:
        print(f"Warning: Failed to log usage: {e}")

