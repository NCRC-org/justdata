#!/usr/bin/env python3
"""
BigQuery Client for ElectWatch

Provides read functions to query data from BigQuery tables.
Replaces the JSON file reading in data_store.py.

Usage:
    from justdata.apps.electwatch.services.bq_client import ElectWatchBQClient
    
    client = ElectWatchBQClient()
    officials = client.get_officials()
    official = client.get_official('P000197')
"""

import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from justdata.shared.utils.bigquery_client import get_bigquery_client, execute_query, escape_sql_string
from justdata.apps.electwatch.config import ElectWatchConfig

logger = logging.getLogger(__name__)

# Constants
PROJECT_ID = ElectWatchConfig.GCP_PROJECT_ID
DATASET_ID = ElectWatchConfig.DATASET_ID
APP_NAME = ElectWatchConfig.BQ_APP_NAME


class ElectWatchBQClient:
    """
    BigQuery client for reading ElectWatch data.
    
    All methods return data in the same format as the original JSON-based
    data_store.py to minimize changes to the rest of the application.
    """
    
    def __init__(self):
        """Initialize BigQuery client."""
        self.client = get_bigquery_client(PROJECT_ID, app_name=APP_NAME)
        self.dataset_ref = f"{PROJECT_ID}.{DATASET_ID}"
    
    def _table_ref(self, table_name: str) -> str:
        """Get full table reference."""
        return f"`{self.dataset_ref}.{table_name}`"
    
    def _execute_query(self, query: str, timeout: int = 60) -> List[Dict]:
        """Execute a query and return results as list of dicts."""
        try:
            return execute_query(self.client, query, timeout=timeout)
        except Exception as e:
            logger.error(f"BigQuery query error: {e}")
            raise
    
    def _row_to_dict(self, row) -> Dict:
        """Convert a BigQuery Row to a dict, handling nested structures."""
        if hasattr(row, 'items'):
            return dict(row.items())
        return dict(row)
    
    # =========================================================================
    # OFFICIALS
    # =========================================================================
    
    def get_officials(self) -> List[Dict]:
        """
        Get all officials.
        
        Returns:
            List of official dicts
        """
        query = f"""
        SELECT *
        FROM {self._table_ref('officials')}
        ORDER BY involvement_score DESC, name ASC
        """
        
        rows = self._execute_query(query)
        officials = [self._transform_official_row(row) for row in rows]
        logger.info(f"Loaded {len(officials)} officials from BigQuery")
        return officials
    
    def get_official(self, official_id: str) -> Optional[Dict]:
        """
        Get a single official by bioguide_id.
        
        Args:
            official_id: Bioguide ID or normalized ID
            
        Returns:
            Official dict or None if not found
        """
        # Normalize ID (handle various formats)
        normalized_id = official_id.upper().replace('_', '').replace('-', '')
        
        # Try exact match first
        query = f"""
        SELECT *
        FROM {self._table_ref('officials')}
        WHERE bioguide_id = '{escape_sql_string(official_id)}'
        LIMIT 1
        """
        
        rows = self._execute_query(query)
        if rows:
            return self._transform_official_row(rows[0])
        
        # Try case-insensitive match
        query = f"""
        SELECT *
        FROM {self._table_ref('officials')}
        WHERE UPPER(REPLACE(REPLACE(bioguide_id, '_', ''), '-', '')) = '{escape_sql_string(normalized_id)}'
        LIMIT 1
        """
        
        rows = self._execute_query(query)
        if rows:
            return self._transform_official_row(rows[0])
        
        return None
    
    def get_official_by_name(self, name: str) -> Optional[Dict]:
        """
        Get an official by name (partial match).
        
        Args:
            name: Official name to search for
            
        Returns:
            Official dict or None if not found
        """
        escaped_name = escape_sql_string(name)
        query = f"""
        SELECT *
        FROM {self._table_ref('officials')}
        WHERE LOWER(name) LIKE LOWER('%{escaped_name}%')
        ORDER BY involvement_score DESC
        LIMIT 1
        """
        
        rows = self._execute_query(query)
        if rows:
            return self._transform_official_row(rows[0])
        return None
    
    def _transform_official_row(self, row: Dict) -> Dict:
        """Transform BigQuery row to match expected format."""
        # BigQuery returns nested structures as dicts, arrays as lists
        # Most fields should already be in correct format
        official = dict(row)
        
        # Ensure trades are loaded separately if needed
        if 'trades' not in official:
            official['trades'] = []
        
        # Build contributions_display object expected by frontend
        # Frontend expects: contributions_display.total and contributions_display.financial
        pac_total = float(official.get('pac_contributions') or official.get('contributions') or 0)
        individual_total = float(official.get('individual_contributions_total') or 0)
        financial_pac = float(official.get('financial_sector_pac') or 0)
        financial_individual = float(official.get('individual_financial_total') or 0)
        
        official['contributions_display'] = {
            'total': pac_total + individual_total,
            'financial': financial_pac + financial_individual,
            'pac': pac_total,
            'individual': individual_total,
            'financial_pac': financial_pac,
            'financial_individual': financial_individual
        }
        
        # Frontend expects top_financial_employers but BQ stores top_individual_financial
        if 'top_individual_financial' in official and 'top_financial_employers' not in official:
            official['top_financial_employers'] = official.get('top_individual_financial', [])
        
        return official
    
    # =========================================================================
    # OFFICIAL TRADES
    # =========================================================================
    
    def get_official_trades(self, bioguide_id: str) -> List[Dict]:
        """
        Get all trades for an official.
        
        Args:
            bioguide_id: Official's bioguide ID
            
        Returns:
            List of trade dicts
        """
        query = f"""
        SELECT *
        FROM {self._table_ref('official_trades')}
        WHERE bioguide_id = '{escape_sql_string(bioguide_id)}'
        ORDER BY transaction_date DESC
        """
        
        rows = self._execute_query(query)
        
        # Transform to match expected format
        trades = []
        for row in rows:
            trade = dict(row)
            # Reconstruct amount dict
            trade['amount'] = {
                'min': trade.get('amount_min', 0),
                'max': trade.get('amount_max', 0),
                'display': trade.get('amount_display', '')
            }
            trade['type'] = trade.get('trade_type', '')
            trades.append(trade)
        
        return trades
    
    def get_recent_trades(self, days: int = 90) -> List[Dict]:
        """
        Get recent trades across all officials.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of trade dicts with official info
        """
        query = f"""
        SELECT 
            t.*,
            o.name AS official_name,
            o.party,
            o.state,
            o.chamber,
            o.photo_url
        FROM {self._table_ref('official_trades')} t
        JOIN {self._table_ref('officials')} o ON t.bioguide_id = o.bioguide_id
        WHERE t.transaction_date >= DATE_SUB(CURRENT_DATE(), INTERVAL {days} DAY)
        ORDER BY t.transaction_date DESC
        LIMIT 1000
        """
        
        return self._execute_query(query)
    
    # =========================================================================
    # FIRMS
    # =========================================================================
    
    def get_firms(self) -> List[Dict]:
        """
        Get all firms.
        
        Returns:
            List of firm dicts
        """
        query = f"""
        SELECT *
        FROM {self._table_ref('firms')}
        ORDER BY officials_count DESC, ticker ASC
        """
        
        rows = self._execute_query(query)
        logger.info(f"Loaded {len(rows)} firms from BigQuery")
        return [dict(row) for row in rows]
    
    def get_firm(self, ticker_or_name: str) -> Optional[Dict]:
        """
        Get a firm by ticker or name.
        
        Args:
            ticker_or_name: Ticker symbol or company name
            
        Returns:
            Firm dict or None if not found
        """
        escaped = escape_sql_string(ticker_or_name)
        query = f"""
        SELECT *
        FROM {self._table_ref('firms')}
        WHERE UPPER(ticker) = UPPER('{escaped}')
           OR LOWER(name) LIKE LOWER('%{escaped}%')
        LIMIT 1
        """
        
        rows = self._execute_query(query)
        if rows:
            return dict(rows[0])
        return None
    
    # =========================================================================
    # INDUSTRIES
    # =========================================================================
    
    def get_industries(self) -> List[Dict]:
        """
        Get all industries.
        
        Returns:
            List of industry dicts
        """
        query = f"""
        SELECT *
        FROM {self._table_ref('industries')}
        ORDER BY officials_count DESC, sector ASC
        """
        
        rows = self._execute_query(query)
        logger.info(f"Loaded {len(rows)} industries from BigQuery")
        return [dict(row) for row in rows]
    
    def get_industry(self, sector: str) -> Optional[Dict]:
        """
        Get an industry by sector code.
        
        Args:
            sector: Sector code (e.g., 'banking')
            
        Returns:
            Industry dict or None if not found
        """
        escaped = escape_sql_string(sector)
        query = f"""
        SELECT *
        FROM {self._table_ref('industries')}
        WHERE LOWER(sector) = LOWER('{escaped}')
        LIMIT 1
        """
        
        rows = self._execute_query(query)
        if rows:
            return dict(rows[0])
        return None
    
    # =========================================================================
    # COMMITTEES
    # =========================================================================
    
    def get_committees(self) -> List[Dict]:
        """
        Get all committees.
        
        Returns:
            List of committee dicts
        """
        query = f"""
        SELECT *
        FROM {self._table_ref('committees')}
        ORDER BY chamber, name
        """
        
        rows = self._execute_query(query)
        logger.info(f"Loaded {len(rows)} committees from BigQuery")
        return [dict(row) for row in rows]
    
    def get_committee(self, committee_id: str) -> Optional[Dict]:
        """
        Get a committee by ID.
        
        Args:
            committee_id: Committee ID
            
        Returns:
            Committee dict or None if not found
        """
        escaped = escape_sql_string(committee_id)
        query = f"""
        SELECT *
        FROM {self._table_ref('committees')}
        WHERE id = '{escaped}'
        LIMIT 1
        """
        
        rows = self._execute_query(query)
        if rows:
            return dict(rows[0])
        return None
    
    # =========================================================================
    # NEWS
    # =========================================================================
    
    def get_news(self, limit: int = 100) -> List[Dict]:
        """
        Get recent news articles.
        
        Args:
            limit: Maximum number of articles to return
            
        Returns:
            List of article dicts
        """
        query = f"""
        SELECT *
        FROM {self._table_ref('news')}
        ORDER BY published_date DESC, fetched_at DESC
        LIMIT {limit}
        """
        
        rows = self._execute_query(query)
        return [dict(row) for row in rows]
    
    # =========================================================================
    # INSIGHTS
    # =========================================================================
    
    def get_insights(self) -> List[Dict]:
        """
        Get AI-generated insights.
        
        Returns:
            List of insight dicts
        """
        query = f"""
        SELECT *
        FROM {self._table_ref('insights')}
        ORDER BY 
            CASE severity 
                WHEN 'high' THEN 1 
                WHEN 'medium' THEN 2 
                WHEN 'low' THEN 3 
                ELSE 4 
            END,
            generated_at DESC
        """
        
        rows = self._execute_query(query)
        return [dict(row) for row in rows]
    
    # =========================================================================
    # SUMMARIES
    # =========================================================================
    
    def get_summaries(self) -> Dict:
        """
        Get AI-generated summaries.
        
        Returns:
            Dict containing summary texts
        """
        query = f"""
        SELECT *
        FROM {self._table_ref('summaries')}
        WHERE id = 'current'
        LIMIT 1
        """
        
        rows = self._execute_query(query)
        if rows:
            return dict(rows[0])
        return {
            'weekly_overview': '',
            'top_movers': '',
            'industry_highlights': '',
            'status': 'no_data'
        }
    
    # =========================================================================
    # METADATA
    # =========================================================================
    
    def get_metadata(self) -> Dict:
        """
        Get update metadata.
        
        Returns:
            Dict containing metadata
        """
        query = f"""
        SELECT *
        FROM {self._table_ref('metadata')}
        WHERE id = 'current'
        LIMIT 1
        """
        
        rows = self._execute_query(query)
        if rows:
            metadata = dict(rows[0])
            # Parse data_sources JSON if present
            if metadata.get('data_sources'):
                try:
                    if isinstance(metadata['data_sources'], str):
                        metadata['data_sources'] = json.loads(metadata['data_sources'])
                except:
                    pass
            return metadata
        
        return {
            'status': 'no_data',
            'last_updated': None,
            'officials_count': 0,
            'firms_count': 0
        }
    
    def get_freshness(self) -> Dict:
        """
        Get data freshness info.
        
        Returns:
            Dict with freshness information
        """
        metadata = self.get_metadata()
        return {
            'status': metadata.get('status', 'unknown'),
            'last_updated': metadata.get('last_updated'),
            'last_updated_display': metadata.get('last_updated_display', ''),
            'next_update': metadata.get('next_update'),
            'next_update_display': metadata.get('next_update_display', '')
        }
    
    # =========================================================================
    # TREND SNAPSHOTS
    # =========================================================================
    
    def get_trend_history(self, bioguide_id: str, periods: int = 12) -> List[Dict]:
        """
        Get historical trend data for an official.
        
        Args:
            bioguide_id: Official's bioguide ID
            periods: Number of periods (weeks) to return
            
        Returns:
            List of snapshot dicts ordered by date
        """
        escaped = escape_sql_string(bioguide_id)
        query = f"""
        SELECT *
        FROM {self._table_ref('trend_snapshots')}
        WHERE bioguide_id = '{escaped}'
        ORDER BY snapshot_date DESC
        LIMIT {periods}
        """
        
        rows = self._execute_query(query)
        # Return in chronological order
        return [dict(row) for row in reversed(rows)]
    
    def get_all_trend_snapshots(self) -> List[Dict]:
        """
        Get all trend snapshots (for migration/backup).
        
        Returns:
            List of all snapshot rows
        """
        query = f"""
        SELECT *
        FROM {self._table_ref('trend_snapshots')}
        ORDER BY snapshot_date, bioguide_id
        """
        
        return self._execute_query(query)
    
    # =========================================================================
    # AGGREGATIONS
    # =========================================================================
    
    def get_top_pac_recipients(self, limit: int = 100) -> List[Dict]:
        """
        Get officials with highest financial PAC contributions.
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of official dicts with PAC stats
        """
        query = f"""
        SELECT 
            bioguide_id,
            name,
            party,
            state,
            chamber,
            photo_url,
            financial_sector_pac,
            financial_pac_pct,
            pac_contributions
        FROM {self._table_ref('officials')}
        WHERE financial_sector_pac > 0
        ORDER BY financial_sector_pac DESC
        LIMIT {limit}
        """
        
        return self._execute_query(query)
    
    def get_top_traders(self, limit: int = 100) -> List[Dict]:
        """
        Get officials with most trading activity.
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of official dicts with trading stats
        """
        query = f"""
        SELECT 
            bioguide_id,
            name,
            party,
            state,
            chamber,
            photo_url,
            total_trades,
            stock_trades_min,
            stock_trades_max,
            stock_trades_display,
            trade_score
        FROM {self._table_ref('officials')}
        WHERE total_trades > 0
        ORDER BY trade_score DESC
        LIMIT {limit}
        """
        
        return self._execute_query(query)
    
    def get_stats(self) -> Dict:
        """
        Get aggregate statistics.
        
        Returns:
            Dict with various counts and aggregations
        """
        query = f"""
        SELECT
            (SELECT COUNT(*) FROM {self._table_ref('officials')}) as total_officials,
            (SELECT COUNT(*) FROM {self._table_ref('officials')} WHERE has_financial_activity = TRUE) as active_officials,
            (SELECT COUNT(*) FROM {self._table_ref('official_trades')}) as total_trades,
            (SELECT COUNT(*) FROM {self._table_ref('firms')}) as total_firms,
            (SELECT COUNT(*) FROM {self._table_ref('industries')}) as total_industries,
            (SELECT SUM(financial_sector_pac) FROM {self._table_ref('officials')}) as total_financial_pac,
            (SELECT SUM(stock_trades_min) FROM {self._table_ref('officials')}) as total_trades_min,
            (SELECT SUM(stock_trades_max) FROM {self._table_ref('officials')}) as total_trades_max
        """
        
        rows = self._execute_query(query)
        if rows:
            return dict(rows[0])
        return {}


# Singleton instance for convenience
_client_instance = None

def get_client() -> ElectWatchBQClient:
    """Get or create singleton BQ client instance."""
    global _client_instance
    if _client_instance is None:
        _client_instance = ElectWatchBQClient()
    return _client_instance
