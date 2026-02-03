#!/usr/bin/env python3
"""
BigQuery Writer for ElectWatch

Writes data to BigQuery tables during the weekly update process.
Replaces the JSON file storage with BigQuery as the primary data store.

Usage:
    from justdata.apps.electwatch.services.bq_writer import ElectWatchBQWriter
    
    writer = ElectWatchBQWriter()
    writer.write_officials(officials_data)
    writer.write_firms(firms_data)
    # ... etc
"""

import logging
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional
from google.cloud import bigquery

from justdata.shared.utils.bigquery_client import get_bigquery_client
from justdata.apps.electwatch.config import ElectWatchConfig

logger = logging.getLogger(__name__)

# Constants
PROJECT_ID = ElectWatchConfig.GCP_PROJECT_ID
DATASET_ID = 'electwatch'
APP_NAME = 'ELECTWATCH'


def _generate_id(*args) -> str:
    """Generate a deterministic ID from multiple values."""
    combined = '|'.join(str(a) for a in args if a)
    return hashlib.md5(combined.encode()).hexdigest()[:16]


def _now() -> str:
    """Get current timestamp in ISO format."""
    return datetime.utcnow().isoformat()


class ElectWatchBQWriter:
    """
    Writes ElectWatch data to BigQuery tables.
    
    Each write method:
    1. Transforms data from the current JSON format to BigQuery schema
    2. Deletes existing data (full refresh approach)
    3. Inserts new data
    """
    
    def __init__(self):
        """Initialize BigQuery client."""
        self.client = get_bigquery_client(PROJECT_ID, app_name=APP_NAME)
        self.dataset_ref = f"{PROJECT_ID}.{DATASET_ID}"
        
    def _table_ref(self, table_name: str) -> str:
        """Get full table reference."""
        return f"{self.dataset_ref}.{table_name}"
    
    def _truncate_table(self, table_name: str):
        """Delete all rows from a table."""
        query = f"DELETE FROM `{self._table_ref(table_name)}` WHERE TRUE"
        try:
            job = self.client.query(query)
            job.result()
            logger.info(f"Truncated table {table_name}")
        except Exception as e:
            logger.warning(f"Could not truncate {table_name}: {e}")
    
    def _insert_rows(self, table_name: str, rows: List[Dict]) -> int:
        """Insert rows into a table."""
        if not rows:
            logger.info(f"No rows to insert into {table_name}")
            return 0
            
        table_ref = self.client.dataset(DATASET_ID).table(table_name)
        errors = self.client.insert_rows_json(table_ref, rows)
        
        if errors:
            logger.error(f"Errors inserting into {table_name}: {errors[:5]}")
            raise Exception(f"BigQuery insert errors: {errors[:5]}")
        
        logger.info(f"Inserted {len(rows)} rows into {table_name}")
        return len(rows)
    
    # =========================================================================
    # OFFICIALS
    # =========================================================================
    
    def write_officials(self, officials: List[Dict]) -> int:
        """
        Write officials to BigQuery.
        
        Args:
            officials: List of official dicts from the weekly update
            
        Returns:
            Number of rows inserted
        """
        logger.info(f"Writing {len(officials)} officials to BigQuery")
        
        rows = []
        for official in officials:
            row = self._transform_official(official)
            rows.append(row)
        
        self._truncate_table('officials')
        return self._insert_rows('officials', rows)
    
    def _transform_official(self, official: Dict) -> Dict:
        """Transform official dict to BigQuery row format."""
        # Top financial PACs
        top_pacs = []
        for pac in official.get('top_financial_pacs', [])[:10]:
            top_pacs.append({
                'name': pac.get('name', ''),
                'amount': float(pac.get('amount', 0)),
                'sector': pac.get('sector', '')
            })
        
        # Top individual financial contributors
        top_individual = []
        for contrib in official.get('top_individual_financial', [])[:10]:
            top_individual.append({
                'name': contrib.get('name', ''),
                'employer': contrib.get('employer', ''),
                'occupation': contrib.get('occupation', ''),
                'amount': float(contrib.get('amount', 0)),
                'date': contrib.get('date', ''),
                'city': contrib.get('city', ''),
                'state': contrib.get('state', '')
            })
        
        # Top industries
        top_industries = []
        for ind in official.get('top_industries', [])[:10]:
            top_industries.append({
                'name': ind.get('name', ''),
                'amount': float(ind.get('amount', 0))
            })
        
        # Net worth
        net_worth = official.get('net_worth')
        net_worth_struct = None
        if net_worth and isinstance(net_worth, dict):
            net_worth_struct = {
                'min': float(net_worth.get('min', 0) or 0),
                'max': float(net_worth.get('max', 0) or 0),
                'source': net_worth.get('source', ''),
                'year': int(net_worth.get('year', 0) or 0)
            }
        
        return {
            'bioguide_id': official.get('bioguide_id', ''),
            'name': official.get('name', ''),
            'party': official.get('party', ''),
            'state': official.get('state', ''),
            'district': official.get('district'),
            'chamber': official.get('chamber', ''),
            'photo_url': official.get('photo_url', ''),
            'website_url': official.get('website_url', ''),
            'years_in_congress': official.get('years_in_congress'),
            'first_elected': official.get('first_elected'),
            
            # External identifiers
            'fec_candidate_id': official.get('fec_candidate_id'),
            'fec_committee_id': official.get('fec_committee_id'),
            'opensecrets_id': official.get('opensecrets_id'),
            'govtrack_id': official.get('govtrack_id'),
            
            # Trading summary
            'total_trades': official.get('total_trades', 0),
            'purchase_count': official.get('purchase_count', 0),
            'sale_count': official.get('sale_count', 0),
            'stock_trades_min': float(official.get('stock_trades_min', 0) or 0),
            'stock_trades_max': float(official.get('stock_trades_max', 0) or 0),
            'stock_trades_display': official.get('stock_trades_display', ''),
            'purchases_display': official.get('purchases_display', ''),
            'sales_display': official.get('sales_display', ''),
            'trade_score': float(official.get('trade_score', 0) or 0),
            'symbols_traded': official.get('symbols_traded', []),
            
            # PAC contributions
            'contributions': float(official.get('contributions', 0) or 0),
            'pac_contributions': float(official.get('pac_contributions', 0) or 0),
            'financial_sector_pac': float(official.get('financial_sector_pac', 0) or 0),
            'financial_pac_pct': float(official.get('financial_pac_pct', 0) or 0),
            
            # Individual contributions
            'individual_contributions_total': float(official.get('individual_contributions_total', 0) or 0),
            'individual_financial_total': float(official.get('individual_financial_total', 0) or 0),
            'individual_financial_pct': float(official.get('individual_financial_pct', 0) or 0),
            
            # Scoring
            'involvement_score': float(official.get('involvement_score', 0) or 0),
            'financial_sector_score': float(official.get('financial_sector_score', 0) or 0),
            
            # Committees
            'committees': official.get('committees', []),
            'is_finance_committee': official.get('is_finance_committee', False),
            
            # Top donors/PACs (denormalized)
            'top_financial_pacs': top_pacs,
            'top_individual_financial': top_individual,
            'top_industries': top_industries,
            
            # Wealth
            'net_worth': net_worth_struct,
            'wealth_tier': official.get('wealth_tier', ''),
            
            # Activity
            'has_financial_activity': official.get('has_financial_activity', False),
            
            # Metadata
            'updated_at': _now()
        }
    
    # =========================================================================
    # OFFICIAL TRADES
    # =========================================================================
    
    def write_official_trades(self, officials: List[Dict]) -> int:
        """
        Extract and write trades from all officials.
        
        Args:
            officials: List of official dicts containing trades
            
        Returns:
            Number of trades inserted
        """
        rows = []
        for official in officials:
            bioguide_id = official.get('bioguide_id', '')
            for trade in official.get('trades', []):
                row = self._transform_trade(bioguide_id, trade)
                rows.append(row)
        
        logger.info(f"Writing {len(rows)} trades to BigQuery")
        self._truncate_table('official_trades')
        return self._insert_rows('official_trades', rows)
    
    def _transform_trade(self, bioguide_id: str, trade: Dict) -> Dict:
        """Transform trade dict to BigQuery row format."""
        amount = trade.get('amount', {})
        if isinstance(amount, dict):
            amount_min = amount.get('min', 0)
            amount_max = amount.get('max', 0)
            amount_display = amount.get('display', '')
        else:
            amount_min = 0
            amount_max = 0
            amount_display = ''
        
        # Generate deterministic ID
        trade_id = _generate_id(
            bioguide_id,
            trade.get('ticker'),
            trade.get('transaction_date'),
            trade.get('type'),
            amount_min
        )
        
        return {
            'id': trade_id,
            'bioguide_id': bioguide_id,
            'ticker': trade.get('ticker', ''),
            'company': trade.get('company', ''),
            'trade_type': trade.get('type', ''),
            'amount_min': float(amount_min or 0),
            'amount_max': float(amount_max or 0),
            'amount_display': amount_display,
            'transaction_date': trade.get('transaction_date'),
            'disclosure_date': trade.get('disclosure_date'),
            'owner': trade.get('owner', ''),
            'asset_type': trade.get('asset_type', ''),
            'capital_gains': trade.get('capital_gains', False),
            'filing_url': trade.get('filing_url', ''),
            'source': trade.get('source', ''),
            'updated_at': _now()
        }
    
    # =========================================================================
    # PAC CONTRIBUTIONS
    # =========================================================================
    
    def write_pac_contributions(self, officials: List[Dict]) -> int:
        """
        Extract and write PAC contributions from all officials.
        
        Args:
            officials: List of official dicts containing contributions
            
        Returns:
            Number of contributions inserted
        """
        rows = []
        for official in officials:
            bioguide_id = official.get('bioguide_id', '')
            # Use top_financial_pacs as the source
            for pac in official.get('top_financial_pacs', []):
                row = {
                    'id': _generate_id(bioguide_id, pac.get('name', '')),
                    'bioguide_id': bioguide_id,
                    'committee_id': '',  # Not always available
                    'committee_name': pac.get('name', ''),
                    'amount': float(pac.get('amount', 0)),
                    'contribution_date': None,  # Aggregated, no specific date
                    'sector': pac.get('sector', ''),
                    'sub_sector': pac.get('sub_sector', ''),
                    'is_financial': True,  # These are financial PACs
                    'updated_at': _now()
                }
                rows.append(row)
        
        logger.info(f"Writing {len(rows)} PAC contributions to BigQuery")
        self._truncate_table('official_pac_contributions')
        return self._insert_rows('official_pac_contributions', rows)
    
    # =========================================================================
    # INDIVIDUAL CONTRIBUTIONS
    # =========================================================================
    
    def write_individual_contributions(self, officials: List[Dict]) -> int:
        """
        Extract and write individual contributions from all officials.
        
        Args:
            officials: List of official dicts containing individual contributions
            
        Returns:
            Number of contributions inserted
        """
        rows = []
        for official in officials:
            bioguide_id = official.get('bioguide_id', '')
            for contrib in official.get('top_individual_financial', []):
                row = {
                    'id': _generate_id(
                        bioguide_id,
                        contrib.get('name', ''),
                        contrib.get('date', ''),
                        contrib.get('amount', 0)
                    ),
                    'bioguide_id': bioguide_id,
                    'contributor_name': contrib.get('name', ''),
                    'employer': contrib.get('employer', ''),
                    'occupation': contrib.get('occupation', ''),
                    'city': contrib.get('city', ''),
                    'state': contrib.get('state', ''),
                    'amount': float(contrib.get('amount', 0)),
                    'contribution_date': contrib.get('date'),
                    'sector': contrib.get('sector', ''),
                    'is_financial': True,
                    'match_reason': contrib.get('match_reason', ''),
                    'updated_at': _now()
                }
                rows.append(row)
        
        logger.info(f"Writing {len(rows)} individual contributions to BigQuery")
        self._truncate_table('official_individual_contributions')
        return self._insert_rows('official_individual_contributions', rows)
    
    # =========================================================================
    # FIRMS
    # =========================================================================
    
    def write_firms(self, firms: List[Dict]) -> int:
        """
        Write firms to BigQuery.
        
        Args:
            firms: List of firm dicts
            
        Returns:
            Number of firms inserted
        """
        logger.info(f"Writing {len(firms)} firms to BigQuery")
        
        rows = []
        for firm in firms:
            row = self._transform_firm(firm)
            rows.append(row)
        
        self._truncate_table('firms')
        return self._insert_rows('firms', rows)
    
    def _transform_firm(self, firm: Dict) -> Dict:
        """Transform firm dict to BigQuery row format."""
        # Quote data
        quote = firm.get('quote', {})
        quote_struct = None
        if quote and isinstance(quote, dict):
            quote_struct = {
                'current_price': float(quote.get('c', 0) or 0),
                'change': float(quote.get('d', 0) or 0),
                'change_percent': float(quote.get('dp', 0) or 0),
                'high': float(quote.get('h', 0) or 0),
                'low': float(quote.get('l', 0) or 0),
                'open': float(quote.get('o', 0) or 0),
                'previous_close': float(quote.get('pc', 0) or 0),
                'timestamp': quote.get('t')
            }
        
        # Officials who traded this firm
        officials = []
        for off in firm.get('officials', [])[:50]:  # Limit to 50
            officials.append({
                'bioguide_id': off.get('id', ''),
                'name': off.get('name', ''),
                'party': off.get('party', ''),
                'state': off.get('state', ''),
                'chamber': off.get('chamber', ''),
                'photo_url': off.get('photo_url', '')
            })
        
        return {
            'ticker': firm.get('ticker', ''),
            'name': firm.get('name', ''),
            'sector': firm.get('sector', ''),
            'industry': firm.get('industry', ''),
            'officials_count': len(firm.get('officials', [])),
            'trade_count': firm.get('trade_count', 0),
            'total_value_min': float(firm.get('total_value', {}).get('min', 0) or 0),
            'total_value_max': float(firm.get('total_value', {}).get('max', 0) or 0),
            'purchase_count': firm.get('purchase_count', 0),
            'sale_count': firm.get('sale_count', 0),
            'quote': quote_struct,
            'officials': officials,
            'updated_at': _now()
        }
    
    # =========================================================================
    # INDUSTRIES
    # =========================================================================
    
    def write_industries(self, industries: List[Dict]) -> int:
        """
        Write industries to BigQuery.
        
        Args:
            industries: List of industry dicts
            
        Returns:
            Number of industries inserted
        """
        logger.info(f"Writing {len(industries)} industries to BigQuery")
        
        rows = []
        for industry in industries:
            row = self._transform_industry(industry)
            rows.append(row)
        
        self._truncate_table('industries')
        return self._insert_rows('industries', rows)
    
    def _transform_industry(self, industry: Dict) -> Dict:
        """Transform industry dict to BigQuery row format."""
        # Top firms
        top_firms = []
        for firm in industry.get('firms', [])[:20]:
            top_firms.append({
                'ticker': firm.get('ticker', ''),
                'name': firm.get('name', ''),
                'total': float(firm.get('total', 0) or 0),
                'officials_count': firm.get('officials_count', 0),
                'trade_count': firm.get('trade_count', 0)
            })
        
        return {
            'sector': industry.get('sector', ''),
            'name': industry.get('name', ''),
            'description': industry.get('description', ''),
            'color': industry.get('color', ''),
            'firms_count': industry.get('firms_count', len(industry.get('firms', []))),
            'officials_count': industry.get('officials_count', 0),
            'total_trades': industry.get('total_trades', 0),
            'total_value_min': float(industry.get('total_value', {}).get('min', 0) or 0),
            'total_value_max': float(industry.get('total_value', {}).get('max', 0) or 0),
            'top_firms': top_firms,
            'updated_at': _now()
        }
    
    # =========================================================================
    # COMMITTEES
    # =========================================================================
    
    def write_committees(self, committees: List[Dict]) -> int:
        """
        Write committees to BigQuery.
        
        Args:
            committees: List of committee dicts
            
        Returns:
            Number of committees inserted
        """
        logger.info(f"Writing {len(committees)} committees to BigQuery")
        
        rows = []
        for committee in committees:
            rows.append({
                'id': committee.get('id', ''),
                'name': committee.get('name', ''),
                'full_name': committee.get('full_name', ''),
                'chamber': committee.get('chamber', ''),
                'chair': committee.get('chair', ''),
                'ranking_member': committee.get('ranking_member', ''),
                'members_count': committee.get('members_count', 0),
                'jurisdiction': committee.get('jurisdiction', ''),
                'updated_at': _now()
            })
        
        self._truncate_table('committees')
        return self._insert_rows('committees', rows)
    
    # =========================================================================
    # NEWS
    # =========================================================================
    
    def write_news(self, articles: List[Dict]) -> int:
        """
        Write news articles to BigQuery.
        
        Args:
            articles: List of article dicts
            
        Returns:
            Number of articles inserted
        """
        logger.info(f"Writing {len(articles)} news articles to BigQuery")
        
        rows = []
        for article in articles:
            rows.append({
                'id': _generate_id(article.get('url', ''), article.get('title', '')),
                'title': article.get('title', ''),
                'url': article.get('url', ''),
                'source': article.get('source', ''),
                'published_date': article.get('date'),
                'summary': article.get('summary', ''),
                'tickers': article.get('tickers', []),
                'officials': article.get('officials', []),
                'fetched_at': _now()
            })
        
        self._truncate_table('news')
        return self._insert_rows('news', rows)
    
    # =========================================================================
    # INSIGHTS
    # =========================================================================
    
    def write_insights(self, insights: List[Dict]) -> int:
        """
        Write AI-generated insights to BigQuery.
        
        Args:
            insights: List of insight dicts
            
        Returns:
            Number of insights inserted
        """
        logger.info(f"Writing {len(insights)} insights to BigQuery")
        
        rows = []
        for i, insight in enumerate(insights):
            # Transform officials
            officials = []
            for off in insight.get('officials', []):
                officials.append({
                    'id': off.get('id', ''),
                    'name': off.get('name', ''),
                    'party': off.get('party', ''),
                    'state': off.get('state', ''),
                    'amount': float(off.get('amount', 0) or 0),
                    'detail': off.get('detail', '')
                })
            
            # Transform industries
            industries = []
            for ind in insight.get('industries', []):
                industries.append({
                    'code': ind.get('code', ''),
                    'name': ind.get('name', ''),
                    'amount': float(ind.get('amount', 0) or 0),
                    'detail': ind.get('detail', '')
                })
            
            # Transform firms
            firms = []
            for firm in insight.get('firms', []):
                firms.append({
                    'ticker': firm.get('ticker', ''),
                    'name': firm.get('name', ''),
                    'amount': float(firm.get('amount', 0) or 0),
                    'detail': firm.get('detail', '')
                })
            
            # Transform committees
            committees = []
            for comm in insight.get('committees', []):
                committees.append({
                    'id': comm.get('id', ''),
                    'name': comm.get('name', ''),
                    'detail': comm.get('detail', '')
                })
            
            # Transform sources
            sources = []
            for src in insight.get('sources', []):
                sources.append({
                    'title': src.get('title', ''),
                    'url': src.get('url', ''),
                    'source': src.get('source', ''),
                    'date': src.get('date', '')
                })
            
            rows.append({
                'id': _generate_id(insight.get('title', ''), i),
                'title': insight.get('title', ''),
                'summary': insight.get('summary', ''),
                'detailed_summary': insight.get('detailed_summary', ''),
                'evidence': insight.get('evidence', ''),
                'category': insight.get('category', ''),
                'severity': insight.get('severity', ''),
                'officials': officials,
                'industries': industries,
                'firms': firms,
                'committees': committees,
                'sources': sources,
                'generated_at': _now()
            })
        
        self._truncate_table('insights')
        return self._insert_rows('insights', rows)
    
    # =========================================================================
    # SUMMARIES
    # =========================================================================
    
    def write_summaries(self, summaries: Dict) -> int:
        """
        Write AI-generated summaries to BigQuery.
        
        Args:
            summaries: Dict containing summary texts
            
        Returns:
            Number of rows inserted (1)
        """
        logger.info("Writing summaries to BigQuery")
        
        row = {
            'id': 'current',
            'weekly_overview': summaries.get('weekly_overview', ''),
            'top_movers': summaries.get('top_movers', ''),
            'industry_highlights': summaries.get('industry_highlights', ''),
            'status': summaries.get('status', 'success'),
            'generated_at': _now()
        }
        
        self._truncate_table('summaries')
        return self._insert_rows('summaries', [row])
    
    # =========================================================================
    # METADATA
    # =========================================================================
    
    def write_metadata(self, metadata: Dict) -> int:
        """
        Write update metadata to BigQuery.
        
        Args:
            metadata: Dict containing update metadata
            
        Returns:
            Number of rows inserted (1)
        """
        logger.info("Writing metadata to BigQuery")
        
        import json
        from dateutil import parser as date_parser
        
        def parse_date(val):
            """Parse date from various formats to YYYY-MM-DD."""
            if not val:
                return None
            if isinstance(val, str):
                # If already ISO format, return as-is
                if len(val) == 10 and val[4] == '-' and val[7] == '-':
                    return val
                try:
                    # Parse human-readable dates like "January 21, 2026"
                    parsed = date_parser.parse(val)
                    return parsed.strftime('%Y-%m-%d')
                except:
                    return None
            return None
        
        # Get dates from data_window, preferring ISO format if available
        data_window = metadata.get('data_window', {})
        stock_window = metadata.get('stock_data_window', {})
        fec_window = metadata.get('fec_data_window', {})
        
        row = {
            'id': 'current',
            'status': metadata.get('status', ''),
            'last_updated': metadata.get('last_updated'),
            'last_updated_display': metadata.get('last_updated_display', ''),
            'data_window_start': parse_date(data_window.get('start_iso') or data_window.get('start')),
            'data_window_end': parse_date(data_window.get('end_iso') or data_window.get('end')),
            'stock_data_window_start': parse_date(stock_window.get('start_iso') or stock_window.get('start')),
            'stock_data_window_end': parse_date(stock_window.get('end_iso') or stock_window.get('end')),
            'fec_data_window_start': parse_date(fec_window.get('start_iso') or fec_window.get('start')),
            'fec_data_window_end': parse_date(fec_window.get('end_iso') or fec_window.get('end')),
            'next_update': metadata.get('next_update'),
            'next_update_display': metadata.get('next_update_display', ''),
            'data_sources': json.dumps(metadata.get('data_sources', {})),
            'officials_count': metadata.get('counts', {}).get('officials', 0),
            'firms_count': metadata.get('counts', {}).get('firms', 0),
            'industries_count': metadata.get('counts', {}).get('industries', 0),
            'committees_count': metadata.get('counts', {}).get('committees', 0),
            'news_count': metadata.get('counts', {}).get('news_articles', 0),
            'errors': metadata.get('errors', []),
            'warnings': metadata.get('warnings', [])
        }
        
        self._truncate_table('metadata')
        return self._insert_rows('metadata', [row])
    
    # =========================================================================
    # TREND SNAPSHOTS
    # =========================================================================
    
    def write_trend_snapshot(self, snapshot_date: str, officials: Dict[str, Dict]) -> int:
        """
        Write a trend snapshot to BigQuery.
        
        Args:
            snapshot_date: Date string (YYYY-MM-DD)
            officials: Dict mapping bioguide_id to metrics
            
        Returns:
            Number of rows inserted
        """
        logger.info(f"Writing trend snapshot for {snapshot_date} to BigQuery")
        
        rows = []
        for bioguide_id, metrics in officials.items():
            rows.append({
                'snapshot_date': snapshot_date,
                'bioguide_id': bioguide_id,
                'name': metrics.get('name', ''),
                'finance_pct': float(metrics.get('finance_pct', 0) or 0),
                'total_contributions': float(metrics.get('total_contributions', 0) or 0),
                'finance_contributions': float(metrics.get('finance_contributions', 0) or 0),
                'stock_buys': float(metrics.get('stock_buys', 0) or 0),
                'stock_sells': float(metrics.get('stock_sells', 0) or 0),
                'created_at': _now()
            })
        
        # Don't truncate - append new snapshots
        return self._insert_rows('trend_snapshots', rows)
    
    # =========================================================================
    # CONVENIENCE METHOD - WRITE ALL
    # =========================================================================
    
    def write_all(
        self,
        officials: List[Dict],
        firms: List[Dict],
        industries: List[Dict],
        committees: List[Dict],
        news: List[Dict],
        insights: List[Dict],
        summaries: Dict,
        metadata: Dict
    ) -> Dict[str, int]:
        """
        Write all data to BigQuery.
        
        Returns:
            Dict mapping table names to row counts
        """
        results = {}
        
        # Write in dependency order
        results['officials'] = self.write_officials(officials)
        results['official_trades'] = self.write_official_trades(officials)
        results['official_pac_contributions'] = self.write_pac_contributions(officials)
        results['official_individual_contributions'] = self.write_individual_contributions(officials)
        results['firms'] = self.write_firms(firms)
        results['industries'] = self.write_industries(industries)
        results['committees'] = self.write_committees(committees)
        results['news'] = self.write_news(news)
        results['insights'] = self.write_insights(insights)
        results['summaries'] = self.write_summaries(summaries)
        results['metadata'] = self.write_metadata(metadata)
        
        logger.info(f"BigQuery write complete: {results}")
        return results
