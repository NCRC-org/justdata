"""Cost summary query."""
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from justdata.apps.analytics.config import config
from justdata.apps.analytics.sql_loader import load_sql

from justdata.apps.analytics.bq.client import (
    QUERY_PROJECT,
    _cache_key,
    _get_cached,
    _set_cached,
    get_bigquery_client,
)


def get_cost_summary(days: int = 30, project_id: str = None, skip_cache: bool = False) -> Dict[str, Any]:
    """
    Get BigQuery cost summary from INFORMATION_SCHEMA.

    Queries job history to calculate estimated costs by app.
    Cost calculation: $6.25 per TB processed (BigQuery on-demand pricing).

    Args:
        days: Number of days to look back (default 30)
        project_id: GCP project to query (default from config)
        skip_cache: If True, bypass cache and re-query

    Returns:
        Dictionary with:
        - total_bytes_processed: Total bytes across all queries
        - total_tb_processed: Total terabytes processed
        - estimated_cost_usd: Estimated cost in USD
        - query_count: Number of queries
        - cost_by_app: Dict mapping app names to their costs
        - daily_costs: List of daily cost records
    """
    cache_key = _cache_key('get_cost_summary', days=days, project_id=project_id)
    # Check cache first (unless skip_cache)
    if not skip_cache:
        cached = _get_cached(cache_key)
        if cached is not None:
            return cached
    
    client = get_bigquery_client()
    if project_id is None:
        project_id = config.BIGQUERY_PROJECT
    
    # Cost per TB in USD (BigQuery on-demand pricing)
    COST_PER_TB = 6.25
    
    # JustData service accounts to track (hdma1 legacy + justdata-ncrc)
    SERVICE_ACCOUNTS = [
        'apiclient@hdma1-242116.iam.gserviceaccount.com',
        'justdata@hdma1-242116.iam.gserviceaccount.com',
        'lendsight@justdata-ncrc.iam.gserviceaccount.com',
        'bizsight@justdata-ncrc.iam.gserviceaccount.com',
        'branchsight@justdata-ncrc.iam.gserviceaccount.com',
        'branchmapper@justdata-ncrc.iam.gserviceaccount.com',
        'mergermeter@justdata-ncrc.iam.gserviceaccount.com',
        'dataexplorer@justdata-ncrc.iam.gserviceaccount.com',
        'lenderprofile@justdata-ncrc.iam.gserviceaccount.com',
        'analytics@justdata-ncrc.iam.gserviceaccount.com',
        'electwatch@justdata-ncrc.iam.gserviceaccount.com',
        
    ]
    service_accounts_str = "', '".join(SERVICE_ACCOUNTS)
    
    # Query both projects in PARALLEL for job metadata:
    # - justdata-ncrc: new project (Jan 2026+)
    # - hdma1-242116: historical project (older data)
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    def query_project_costs(project: str, region: str) -> tuple:
        """Query a single project for cost data. Returns (project, app_results, daily_results) or (project, None, None) on error."""
        app_query = load_sql("cost_summary_by_app.sql").format(days=days, project=project, region=region)
        daily_query = load_sql("cost_summary_daily.sql").format(days=days, project=project, region=region)
        try:
            app_results = list(client.query(app_query).result())
            daily_results = list(client.query(daily_query).result())
            return (project, app_results, daily_results)
        except Exception as e:
            print(f"[COST] {project} failed: {str(e)[:80]}")
            return (project, None, None)
    
    all_app_results = []
    all_daily_results = []
    successful_projects = []
    
    # Run both project queries in parallel
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(query_project_costs, 'justdata-ncrc', 'region-us'),
            executor.submit(query_project_costs, 'hdma1-242116', 'region-us'),
        ]
        for future in as_completed(futures):
            project, app_results, daily_results = future.result()
            if app_results is not None:
                all_app_results.extend(app_results)
                all_daily_results.extend(daily_results)
                successful_projects.append(project)

    # Use combined results from all successful projects
    if not successful_projects:
        print(f"BigQuery error in get_cost_summary: No projects succeeded")
        return {
            'error': "No projects returned data",
            'period_days': days,
            'total_bytes_processed': 0,
            'total_tb_processed': 0,
            'estimated_cost_usd': 0,
            'query_count': 0,
            'cost_by_app': {},
            'daily_costs': []
        }

    print(f"[COST] Combined results from {successful_projects}: {len(all_app_results)} app rows, {len(all_daily_results)} daily rows")
    
    # Categories to exclude from JustData costs (not attributable to apps)
    EXCLUDED_CATEGORIES = {'Other/Manual', 'Service Accounts', 'Metadata Queries', 'Public Data'}
    
    try:
        # Process cost by app results (aggregate across projects)
        cost_by_app = {}
        total_bytes = 0
        total_queries = 0
        
        for row in all_app_results:
            app_name = row.app_name
            
            # Skip non-JustData categories
            if app_name in EXCLUDED_CATEGORIES:
                continue
            
            bytes_processed = row.total_bytes or 0
            bytes_billed = row.total_bytes_billed or 0
            query_count = row.query_count or 0
            
            tb_processed = bytes_processed / (1024 ** 4)
            tb_billed = bytes_billed / (1024 ** 4)
            cost_usd = tb_billed * COST_PER_TB
            
            # Aggregate if app already exists (from multiple projects)
            if app_name in cost_by_app:
                cost_by_app[app_name]['query_count'] += query_count
                cost_by_app[app_name]['bytes_processed'] += bytes_processed
                cost_by_app[app_name]['tb_processed'] += round(tb_processed, 4)
                cost_by_app[app_name]['bytes_billed'] += bytes_billed
                cost_by_app[app_name]['tb_billed'] += round(tb_billed, 4)
                cost_by_app[app_name]['estimated_cost_usd'] += round(cost_usd, 2)
            else:
                cost_by_app[app_name] = {
                    'query_count': query_count,
                    'bytes_processed': bytes_processed,
                    'tb_processed': round(tb_processed, 4),
                    'bytes_billed': bytes_billed,
                    'tb_billed': round(tb_billed, 4),
                    'estimated_cost_usd': round(cost_usd, 2)
                }
            
            total_bytes += bytes_billed
            total_queries += query_count
        
        # Aggregate daily costs by date with app breakdown (across projects)
        daily_by_date = {}
        for row in all_daily_results:
            date_str = row.date.isoformat() if row.date else None
            if not date_str:
                continue
            
            app_name = row.app_name or 'Other/Manual'
            
            # Skip non-JustData categories from daily chart too
            if app_name in EXCLUDED_CATEGORIES:
                continue
            
            bytes_billed = row.total_bytes_billed or 0
            tb_billed = bytes_billed / (1024 ** 4)
            cost_usd = tb_billed * COST_PER_TB
            
            if date_str not in daily_by_date:
                daily_by_date[date_str] = {
                    'date': date_str,
                    'query_count': 0,
                    'bytes_processed': 0,
                    'bytes_billed': 0,
                    'tb_billed': 0,
                    'estimated_cost_usd': 0,
                    'by_app': {}
                }
            
            daily_by_date[date_str]['query_count'] += row.query_count or 0
            daily_by_date[date_str]['bytes_processed'] += row.total_bytes or 0
            daily_by_date[date_str]['bytes_billed'] += bytes_billed
            daily_by_date[date_str]['tb_billed'] += tb_billed
            daily_by_date[date_str]['estimated_cost_usd'] += cost_usd
            daily_by_date[date_str]['by_app'][app_name] = round(cost_usd, 4)
        
        # Convert to list and round values
        daily_costs = []
        for date_str in sorted(daily_by_date.keys(), reverse=True):
            day = daily_by_date[date_str]
            day['tb_billed'] = round(day['tb_billed'], 4)
            day['estimated_cost_usd'] = round(day['estimated_cost_usd'], 4)
            daily_costs.append(day)
        
        # Calculate totals
        total_tb = total_bytes / (1024 ** 4)
        total_cost = total_tb * COST_PER_TB
        
        result = {
            'period_days': days,
            'total_bytes_processed': total_bytes,
            'total_tb_processed': round(total_tb, 4),
            'estimated_cost_usd': round(total_cost, 2),
            'query_count': total_queries,
            'cost_per_tb_usd': COST_PER_TB,
            'cost_by_app': cost_by_app,
            'daily_costs': daily_costs
        }
        
        _set_cached(cache_key, result)
        return result
        
    except Exception as e:
        print(f"BigQuery error in get_cost_summary: {e}")
        import traceback
        traceback.print_exc()
        return {
            'error': str(e),
            'period_days': days,
            'total_bytes_processed': 0,
            'total_tb_processed': 0,
            'estimated_cost_usd': 0,
            'query_count': 0,
            'cost_by_app': {},
            'daily_costs': []
        }
