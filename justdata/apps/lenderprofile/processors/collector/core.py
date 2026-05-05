#!/usr/bin/env python3
"""DataCollector class — orchestrates data collection from all APIs.

The class holds API client instances and exposes thin methods that
delegate to per-source modules under collector.sources.*. The
collect_all_data orchestrator runs the fetches concurrently.
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional

from justdata.apps.lenderprofile.cache.cache_manager import CacheManager
from justdata.apps.lenderprofile.processors.ai_entity_resolver import AIEntityResolver
from justdata.apps.lenderprofile.processors.corporate_hierarchy import CorporateHierarchy
from justdata.apps.lenderprofile.processors.data_analysts import (
    DataSourceAnalysts,
    compile_analyst_summaries,
)
from justdata.apps.lenderprofile.processors.ixbrl_parser import IXBRLParser
from justdata.apps.lenderprofile.services.bq_cra_client import BigQueryCRAClient
from justdata.apps.lenderprofile.services.bq_hmda_client import BigQueryHMDAClient
from justdata.apps.lenderprofile.services.cfpb_client import CFPBClient
from justdata.apps.lenderprofile.services.congress_trading_client import CongressTradingClient
from justdata.apps.lenderprofile.services.courtlistener_client import CourtListenerClient
from justdata.apps.lenderprofile.services.duckduckgo_client import DuckDuckGoClient
from justdata.apps.lenderprofile.services.fdic_client import FDICClient
from justdata.apps.lenderprofile.services.federal_register_client import FederalRegisterClient
from justdata.apps.lenderprofile.services.federal_reserve_client import FederalReserveClient
from justdata.apps.lenderprofile.services.gleif_client import GLEIFClient
from justdata.apps.lenderprofile.services.google_news_client import GoogleNewsClient
from justdata.apps.lenderprofile.services.ncua_client import NCUAClient
from justdata.apps.lenderprofile.services.newsapi_client import NewsAPIClient
from justdata.apps.lenderprofile.services.regulations_client import RegulationsGovClient
from justdata.apps.lenderprofile.services.sec_client import SECClient
from justdata.apps.lenderprofile.services.seeking_alpha_client import SeekingAlphaClient

from justdata.apps.lenderprofile.processors.collector.helpers import (
    _calculate_financial_trends_deprecated,
    _is_recent,
    _summarize_branches,
)
from justdata.apps.lenderprofile.processors.collector.sources import (
    cfpb,
    enforcement,
    fdic,
    federal_register,
    federal_reserve,
    gleif,
    hmda,
    litigation,
    news,
    regulations,
    sb_lending,
    sec,
    seeking_alpha,
    theorg,
)

logger = logging.getLogger(__name__)


class DataCollector:
    """Collects data from all APIs for a complete institution profile."""

    def __init__(self):
        """Initialize data collector with all API clients."""
        self.fdic_client = FDICClient()
        self.ncua_client = NCUAClient()
        self.sec_client = SECClient()
        self.gleif_client = GLEIFClient()
        self.courtlistener_client = CourtListenerClient()
        self.newsapi_client = NewsAPIClient()
        self.google_news_client = GoogleNewsClient()
        self.duckduckgo_client = DuckDuckGoClient()
        self.cfpb_client = CFPBClient()
        self.federal_register_client = FederalRegisterClient()
        self.regulations_client = RegulationsGovClient()
        self.federal_reserve_client = FederalReserveClient()
        self.seeking_alpha_client = SeekingAlphaClient()
        self.hmda_client = BigQueryHMDAClient()
        self.cra_client = BigQueryCRAClient()
        self.congress_trading_client = CongressTradingClient()
        self.cache = CacheManager()
        self.hierarchy = CorporateHierarchy()
        self.ai_resolver = AIEntityResolver()
        self.data_analysts = DataSourceAnalysts()

    # --------------------------------------------------------------
    # Per-source delegates (bodies live in collector.sources.<source>)
    # --------------------------------------------------------------

    def _get_corporate_family(self, lei: str, institution_name: str) -> Dict[str, Any]:
        return gleif._get_corporate_family(self, lei, institution_name)

    def _aggregate_news_by_keywords(self, news_keywords: List[str], institution_name: str) -> Dict[str, Any]:
        return news._aggregate_news_by_keywords(self, news_keywords, institution_name)

    def _aggregate_cfpb_by_names(self, brand_names: List[str], institution_name: str) -> Dict[str, Any]:
        return cfpb._aggregate_cfpb_by_names(self, brand_names, institution_name)

    def _aggregate_cfpb_all_entities(self, family: Dict[str, Any]) -> Dict[str, Any]:
        return cfpb._aggregate_cfpb_all_entities(self, family)

    def _aggregate_hmda_all_entities(self, family: Dict[str, Any], institution_name: str) -> Dict[str, Any]:
        return hmda._aggregate_hmda_all_entities(self, family, institution_name)

    def _get_fdic_institution(self, cert: str) -> Dict[str, Any]:
        return fdic._get_fdic_institution(self, cert)

    def _get_fdic_financials(self, cert: str) -> Dict[str, Any]:
        return fdic._get_fdic_financials(self, cert)

    def _get_gleif_data(self, lei: str) -> Dict[str, Any]:
        return gleif._get_gleif_data(self, lei)

    def _get_sec_data(self, name: str) -> Dict[str, Any]:
        return sec._get_sec_data(self, name)

    def _get_seeking_alpha_data(self, name: str) -> Dict[str, Any]:
        return seeking_alpha._get_seeking_alpha_data(self, name)

    def _get_litigation_data(self, name: str) -> Dict[str, Any]:
        return litigation._get_litigation_data(self, name)

    def _get_news_data(self, name: str) -> Dict[str, Any]:
        return news._get_news_data(self, name)

    def _get_theorg_data(self, name: str) -> Dict[str, Any]:
        return theorg._get_theorg_data(self, name)

    def _get_enforcement_data(self, name: str) -> Dict[str, Any]:
        return enforcement._get_enforcement_data(self, name)

    def _get_cfpb_complaints(self, company_name: str, limit: int = 1000) -> Dict[str, Any]:
        return cfpb._get_cfpb_complaints(self, company_name, limit)

    def _get_cfpb_metadata(self, rssd_id: Optional[str], lei: Optional[str], name: str) -> Dict[str, Any]:
        return cfpb._get_cfpb_metadata(self, rssd_id, lei, name)

    def _get_federal_register_data(self, name: str) -> Dict[str, Any]:
        return federal_register._get_federal_register_data(self, name)

    def _get_cra_data(self, cert: str) -> Dict[str, Any]:
        return federal_reserve._get_cra_data(self, cert)

    def _get_federal_reserve_data(self, rssd_id: str) -> Dict[str, Any]:
        return federal_reserve._get_federal_reserve_data(self, rssd_id)

    def _get_regulations_data(self, name: str) -> Dict[str, Any]:
        return regulations._get_regulations_data(self, name)

    def _get_hmda_footprint(self, leis: list, institution_name: str = None) -> Dict[str, Any]:
        return hmda._get_hmda_footprint(self, leis, institution_name)

    def _calculate_financial_trends_deprecated(self, financial_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        return _calculate_financial_trends_deprecated(self, financial_records)

    def _summarize_branches(self, branches: List[Dict[str, Any]]) -> Dict[str, Any]:
        return _summarize_branches(self, branches)

    def _get_sb_lending_data(self, lei: str, fdic_cert: str, institution_name: str) -> Dict[str, Any]:
        return sb_lending._get_sb_lending_data(self, lei, fdic_cert, institution_name)

    def _is_recent(self, date_str: str, days: int = 365) -> bool:
        return _is_recent(self, date_str, days)

    # --------------------------------------------------------------
    # Orchestrator
    # --------------------------------------------------------------

    def collect_all_data(self, identifiers: Dict[str, Any], institution_name: str) -> Dict[str, Any]:
        """
        Collect data from all APIs for the institution and its corporate family.

        Queries ALL entities in the corporate family (parent + subsidiaries)
        for each data source, then aggregates results with entity attribution.

        Args:
            identifiers: Resolved identifiers (fdic_cert, rssd_id, lei, etc.)
            institution_name: Institution name

        Returns:
            Complete institution data dictionary with aggregated family data
        """
        logger.info(f"Collecting data for {institution_name}")

        institution_data = {
            'institution': {
                'name': institution_name,
                'identifiers': identifiers
            },
            'identifiers': identifiers
        }

        fdic_cert = identifiers.get('fdic_cert')
        rssd_id = identifiers.get('rssd_id')
        lei = identifiers.get('lei')

        # STEP 1: Get complete corporate family (parent + all subsidiaries)
        corporate_family = self._get_corporate_family(lei, institution_name)
        institution_data['corporate_family'] = corporate_family

        # CRITICAL: Update lei if it was resolved via GLEIF search
        queried_lei = corporate_family.get('queried_entity', {}).get('lei')
        if queried_lei and not lei:
            lei = queried_lei
            identifiers['lei'] = lei
            institution_data['identifiers']['lei'] = lei
            logger.info(f"Updated identifiers with resolved LEI: {lei}")

        # STEP 2: AI Entity Resolution - determine optimal entity for each data source
        try:
            ai_entity_resolution = self.ai_resolver.resolve_entities(
                institution_name,
                corporate_family,
                identifiers
            )
            institution_data['ai_entity_resolution'] = ai_entity_resolution

            # Extract search context for downstream processes
            search_context = self.ai_resolver.generate_search_context(ai_entity_resolution)
            institution_data['search_context'] = search_context

            logger.info(f"AI Entity Resolution complete: {ai_entity_resolution.get('corporate_context', {}).get('institution_type', 'Unknown type')}")
        except Exception as e:
            logger.error(f"AI Entity Resolution failed: {e}")
            institution_data['ai_entity_resolution'] = {}
            institution_data['search_context'] = {}

        
        # Store key family info for easy access
        primary_lei = corporate_family.get('parent_lei') or lei
        primary_name = corporate_family.get('parent_name') or institution_name
        all_related_leis = corporate_family.get('all_leis', [lei] if lei else [])
        all_entity_names = corporate_family.get('all_names', [institution_name])

        logger.info(f"Corporate family: {len(all_entity_names)} entities to query")
        logger.info(f"Entity names: {all_entity_names[:5]}{'...' if len(all_entity_names) > 5 else ''}")

        # Check for corporate hierarchy (parent/child relationships) - legacy support
        hierarchy_info = None
        if lei:
            hierarchy_info = self.hierarchy.get_related_entities(lei)
            if hierarchy_info and hierarchy_info.get('hierarchy_type') != 'standalone':
                logger.info(f"Corporate hierarchy detected: {hierarchy_info.get('hierarchy_type')}")
        
        # Collect data in parallel where possible
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {}
            
            # Try to get FDIC cert from RSSD if not available (only for Call Reports API)
            # Note: We don't use FDIC Institution API - we use CFPB/GLEIF for institution data
            if not fdic_cert and rssd_id:
                logger.info(f"FDIC cert not available, trying to get it from RSSD: {rssd_id}")
                # Try to get just the cert number from FDIC API (minimal call)
                try:
                    # Use a minimal query to get just the cert number
                    fdic_results = self.fdic_client.get_institution_by_rssd(rssd_id)
                    if fdic_results and isinstance(fdic_results, dict) and fdic_results.get('CERT'):
                        fdic_cert = str(fdic_results.get('CERT'))
                        logger.info(f"Found FDIC cert {fdic_cert} from RSSD {rssd_id} (for Call Reports only)")
                except Exception as e:
                    logger.debug(f"Could not get FDIC cert from RSSD {rssd_id}: {e}")
                    # Continue without FDIC cert - Call Reports won't be available

            # Fallback: Try searching FDIC by institution name if RSSD lookup failed
            if not fdic_cert and institution_name:
                logger.info(f"Trying FDIC search by name: {institution_name}")
                try:
                    fdic_search = self.fdic_client.search_institutions(institution_name, limit=5)
                    if fdic_search:
                        # Find the best match (first result is sorted by assets)
                        for inst in fdic_search:
                            inst_data = inst.get('data', inst) if isinstance(inst, dict) else inst
                            if inst_data.get('CERT'):
                                fdic_cert = str(inst_data.get('CERT'))
                                # Also get RSSD ID for branch data if not already set
                                if not rssd_id and inst_data.get('FED_RSSD'):
                                    rssd_id = str(inst_data.get('FED_RSSD'))
                                    identifiers['rssd_id'] = rssd_id
                                    logger.info(f"Found RSSD {rssd_id} from FDIC search")
                                logger.info(f"Found FDIC cert {fdic_cert} by name search: {inst_data.get('NAME')}")
                                break
                except Exception as e:
                    logger.debug(f"Could not get FDIC cert by name search: {e}")

            # FDIC data - only use for call report (financials) API
            # Branch data comes from BigQuery SOD tables, not FDIC API
            if fdic_cert:
                # Only get financials (call report data) from FDIC
                futures['fdic_financials'] = executor.submit(
                    self._get_fdic_financials, fdic_cert
                )
                # Get basic institution info if needed (but prefer CFPB/GLEIF)
                # Note: We're not using FDIC branches - using BigQuery SOD instead
            
            # CFPB API for institution metadata (assets, type, location)
            if rssd_id or lei:
                futures['cfpb_metadata'] = executor.submit(
                    self._get_cfpb_metadata, rssd_id, lei, institution_name
                )
            
            # GLEIF data
            if lei:
                futures['gleif'] = executor.submit(
                    self._get_gleif_data, lei
                )
            
            # SEC data (if public company) - use AI-resolved SEC entity name
            # AI determines which entity files SEC reports (usually the holding company)
            sec_entity_name = ai_entity_resolution.get('entity_mapping', {}).get('sec', {}).get('name', primary_name)
            futures['sec'] = executor.submit(
                self._get_sec_data, sec_entity_name
            )

            # Seeking Alpha data (requires ticker symbol) - use SEC entity name
            futures['seeking_alpha'] = executor.submit(
                self._get_seeking_alpha_data, sec_entity_name
            )
            
            # CourtListener - query all entity names
            futures['litigation'] = executor.submit(
                self._get_litigation_data, institution_name
            )

            # NewsAPI - Use AI-resolved keywords (not all 24 subsidiaries)
            # AI determines primary keywords like "Bank of America", "BofA"
            news_keywords = ai_entity_resolution.get('news_strategy', {}).get('primary_keywords', [])
            if not news_keywords:
                news_keywords = [institution_name]
            futures['news'] = executor.submit(
                self._aggregate_news_by_keywords, news_keywords, institution_name
            )

            # TheOrg - REMOVED per user request

            # CFPB enforcement
            futures['enforcement'] = executor.submit(
                self._get_enforcement_data, institution_name
            )

            # CFPB consumer complaints - Use AI-resolved brand names (not all subsidiaries)
            # AI determines consumer-facing brand names like "Bank of America", "Merrill Lynch"
            cfpb_names = ai_entity_resolution.get('entity_mapping', {}).get('cfpb', {}).get('names', [])
            if not cfpb_names:
                # Fallback to institution name and parent name
                cfpb_names = [institution_name]
                if corporate_family.get('parent_name'):
                    cfpb_names.append(corporate_family.get('parent_name'))
            futures['cfpb_complaints'] = executor.submit(
                self._aggregate_cfpb_by_names, cfpb_names, institution_name
            )
            
            # Federal Register
            futures['federal_register'] = executor.submit(
                self._get_federal_register_data, institution_name
            )
            
            # FFIEC CRA - REMOVED per user request
            
            # Federal Reserve
            if rssd_id:
                futures['federal_reserve'] = executor.submit(
                    self._get_federal_reserve_data, rssd_id
                )
            
            # Regulations.gov
            futures['regulations'] = executor.submit(
                self._get_regulations_data, institution_name
            )

            # HMDA lending footprint data - AGGREGATE across all corporate family LEIs
            # Each entity's lending tagged with relationship (parent/subsidiary)
            futures['hmda_footprint'] = executor.submit(
                self._aggregate_hmda_all_entities, corporate_family, institution_name
            )

            # CRA Small Business Lending data
            futures['sb_lending'] = executor.submit(
                self._get_sb_lending_data, lei, fdic_cert, institution_name
            )

            # Collect results
            for key, future in futures.items():
                try:
                    # SEC data takes longer due to fetching multiple large filings
                    data_timeout = 120 if key == 'sec' else 30
                    result = future.result(timeout=data_timeout)
                    institution_data[key] = result
                    # Debug logging to verify data collection
                    if result:
                        if isinstance(result, dict):
                            result_size = len(str(result))
                            logger.info(f"Collected {key} data: {result_size} chars, keys: {list(result.keys())[:5]}")
                        elif isinstance(result, list):
                            logger.info(f"Collected {key} data: {len(result)} items")
                        else:
                            logger.info(f"Collected {key} data: {type(result).__name__}")
                    else:
                        logger.warning(f"Collected {key} data: empty/None")
                except Exception as e:
                    logger.error(f"Error collecting {key} data: {e}", exc_info=True)
                    institution_data[key] = {}
        
        # Get ticker from SEC or Seeking Alpha and add to identifiers
        ticker = None
        sec_data = institution_data.get('sec', {})
        if sec_data.get('ticker'):
            ticker = sec_data.get('ticker')
        elif institution_data.get('seeking_alpha', {}).get('ticker'):
            ticker = institution_data.get('seeking_alpha', {}).get('ticker')

        # IMPORTANT: Copy ticker and CIK to identifiers for report builder
        if ticker:
            identifiers['ticker'] = ticker
            institution_data['identifiers']['ticker'] = ticker
            if 'institution' in institution_data and 'identifiers' in institution_data['institution']:
                institution_data['institution']['identifiers']['ticker'] = ticker
        if sec_data.get('cik'):
            identifiers['sec_cik'] = sec_data.get('cik')
            institution_data['identifiers']['sec_cik'] = sec_data.get('cik')

        # Get congressional trading data (requires ticker)
        # Uses free public data from Senate/House Stock Watcher
        if ticker:
            try:
                # Use free Congress Trading Client (Senate/House Stock Watcher data)
                congressional_data = self.congress_trading_client.get_congressional_summary(ticker)
                institution_data['congressional_trading'] = congressional_data
                if congressional_data.get('has_data'):
                    logger.info(f"Collected congressional trading data for {ticker}: {congressional_data.get('total_trades')} trades (source: {congressional_data.get('data_source', 'free public data')})")
                else:
                    logger.info(f"No congressional trading data found for {ticker}")
            except Exception as e:
                logger.error(f"Error collecting congressional trading data for {ticker}: {e}")
                institution_data['congressional_trading'] = {'has_data': False, 'total_trades': 0}
        else:
            logger.info(f"No ticker symbol available for congressional trading lookup")
            institution_data['congressional_trading'] = {'has_data': False, 'total_trades': 0, 'no_ticker': True}
        
        # Add hierarchy information
        if hierarchy_info:
            institution_data['hierarchy'] = {
                'primary_lei': primary_lei,
                'primary_name': primary_name,
                'hierarchy_type': hierarchy_info.get('hierarchy_type'),
                'parent': hierarchy_info.get('parent'),
                'children': hierarchy_info.get('children', []),
                'all_entities': all_related_leis,
                'entity_map': self.hierarchy.get_all_entity_names(lei) if lei else {}
            }
            # Keep the original institution name - don't replace with parent holding company
            # Store parent info separately for context but report should focus on searched entity
            if primary_name != institution_name:
                institution_data['institution']['parent_name'] = primary_name
                institution_data['institution']['parent_lei'] = primary_lei
                institution_data['institution']['is_subsidiary'] = True
                logger.info(f"Entity '{institution_name}' is subsidiary of '{primary_name}' - keeping original name for report")
        
        # Process GLEIF data using code-based processor
        from justdata.apps.lenderprofile.processors.data_processors import GLEIFDataProcessor
        gleif_raw = institution_data.get('gleif', {})
        gleif_processed = GLEIFDataProcessor.build_corporate_structure(gleif_raw)
        institution_data['corporate_structure'] = gleif_processed
        
        # Process complaints using code-based processor
        from justdata.apps.lenderprofile.processors.data_processors import ComplaintDataProcessor
        complaints_raw = institution_data.get('cfpb_complaints', {}).get('complaints', [])
        complaints_processed = ComplaintDataProcessor.analyze_complaints(complaints_raw)
        institution_data['complaints_processed'] = complaints_processed
        
        # Process analyst ratings using code-based processor
        from justdata.apps.lenderprofile.processors.data_processors import AnalystRatingsProcessor
        seeking_alpha_raw = institution_data.get('seeking_alpha', {})
        ratings_processed = AnalystRatingsProcessor.process_analyst_ratings(seeking_alpha_raw)
        institution_data['analyst_ratings'] = ratings_processed
        
        # Process litigation using code-based processor
        from justdata.apps.lenderprofile.processors.data_processors import LitigationProcessor
        litigation_raw = institution_data.get('litigation', {}).get('cases', [])
        litigation_processed = LitigationProcessor.process_litigation(litigation_raw)
        institution_data['litigation_processed'] = litigation_processed
        
        # Process news using code-based processor
        # Filter to articles where company (or parent/subsidiaries) is primary subject
        from justdata.apps.lenderprofile.processors.data_processors import NewsProcessor
        newsapi_articles = institution_data.get('news', {}).get('articles', [])
        # Get leading story and news articles from Seeking Alpha
        seeking_alpha_news = seeking_alpha_raw.get('leading_story', []) if isinstance(seeking_alpha_raw.get('leading_story'), list) else []
        seeking_alpha_articles = seeking_alpha_raw.get('news', []) if isinstance(seeking_alpha_raw.get('news'), list) else []
        # Combine all Seeking Alpha news sources
        all_seeking_alpha = seeking_alpha_news + seeking_alpha_articles

        # Extract related company names (parent/subsidiaries) from GLEIF data
        gleif_data = institution_data.get('gleif', {})
        related_names = NewsProcessor.extract_related_names(gleif_data)
        logger.info(f"News filtering with {len(related_names)} related entities: {related_names[:3]}..." if related_names else "No related entities for news filtering")

        news_processed = NewsProcessor.process_news(
            newsapi_articles,
            all_seeking_alpha,
            company_name=institution_name,
            related_names=related_names
        )
        institution_data['news_processed'] = news_processed
        
        # Process SEC filings using code-based parser and XBRL API
        from justdata.apps.lenderprofile.processors.sec_parser import SECFilingParser
        from justdata.apps.lenderprofile.services.sec_client import SECClient
        sec_data = institution_data.get('sec', {})
        ten_k_content = sec_data.get('filings', {}).get('10k_content', [])
        sec_parsed = {}

        # Parse 10-K text content
        if ten_k_content:
            latest_10k = ten_k_content[0] if ten_k_content else None
            if latest_10k and latest_10k.get('content'):
                sec_parsed = SECFilingParser.parse_10k(latest_10k['content'])

        # Fetch structured XBRL data from SEC API (more reliable than text parsing)
        # Get CIK from sec_data (populated by _get_sec_data) or identifiers
        cik = sec_data.get('cik') or identifiers.get('sec_cik')
        if cik:
            try:
                sec_client = SECClient()
                xbrl_data = sec_client.get_comprehensive_xbrl_data(cik)
                if xbrl_data:
                    # Merge XBRL data with text-parsed data
                    sec_parsed = SECFilingParser.merge_with_xbrl_data(sec_parsed, xbrl_data)
                    logger.info(f"Merged SEC XBRL data with parsed 10-K data for CIK {cik}")
            except Exception as e:
                logger.warning(f"Could not fetch XBRL data for CIK {cik}: {e}")

        # Additionally, fetch and parse DEF 14A (proxy) statement for executive/board info
        # Use iXBRL parser for structured data extraction (more reliable than text parsing)
        try:
            def14a_list = sec_data.get('filings', {}).get('def14a', [])
            proxy_parsed = {}
            if def14a_list:
                latest_proxy = def14a_list[0]
                accession = latest_proxy.get('accession_number')

                if accession and cik:
                    # Use iXBRL parser for structured executive compensation data
                    ixbrl_parser = IXBRLParser()
                    cik_int = int(cik)
                    doc_url = ixbrl_parser.get_def14a_doc_url('https://www.sec.gov', cik_int, accession)

                    if doc_url:
                        proxy_parsed = ixbrl_parser.fetch_and_parse_def14a(doc_url)
                        logger.info(f"Parsed DEF 14A iXBRL for CIK {cik}: PEOs={len(proxy_parsed.get('peo_names', []))}, executives={len(proxy_parsed.get('executive_compensation', []))}")
                    else:
                        # Fallback to text-based parsing
                        proxy_content = SECClient().get_def14a_filing_content(cik, accession)
                        if proxy_content:
                            proxy_parsed = SECFilingParser.parse_proxy_statement(proxy_content)
                            logger.info(f"Parsed DEF 14A text for CIK {cik}: executives={len(proxy_parsed.get('executive_compensation', []))}")

            if proxy_parsed and proxy_parsed.get('available', True):
                if not sec_parsed:
                    sec_parsed = {}
                sec_parsed['proxy'] = proxy_parsed
        except Exception as e:
            logger.warning(f"Error fetching/parsing DEF 14A for CIK {cik}: {e}")

        if sec_parsed:
            institution_data['sec_parsed'] = sec_parsed

        # Check 8-K filings for pending mergers/acquisitions
        eight_k_filings = sec_data.get('filings', {}).get('8k', [])
        pending_mergers = []
        for filing in eight_k_filings[:10]:  # Check last 10 8-Ks
            desc = (filing.get('description', '') or '').lower()
            filing_type = (filing.get('type', '') or '').lower()
            # 8-K items that often contain merger info: Item 1.01 (entry into material agreement)
            if any(kw in desc for kw in ['merger', 'acquisition', 'agreement', 'combination']):
                pending_mergers.append({
                    'date': filing.get('date', ''),
                    'description': filing.get('description', '')[:200],
                    'url': filing.get('url', '')
                })
        if pending_mergers:
            if 'mergers' not in institution_data:
                institution_data['mergers'] = {}
            institution_data['mergers']['pending'] = pending_mergers
            logger.info(f"Found {len(pending_mergers)} potential merger announcements in 8-K filings")
        
        # Combine details
        details = institution_data.get('details', {})
        # Note: We don't store fdic_institution anymore - use CFPB/GLEIF for institution data
        details['gleif_data'] = gleif_raw
        details['cfpb_metadata'] = institution_data.get('cfpb_metadata', {})
        institution_data['details'] = details
        
        # Extract tax ID from GLEIF data if available
        gleif_data = institution_data.get('gleif', {})
        if isinstance(gleif_data, dict):
            entity = gleif_data.get('entity', {})
            if isinstance(entity, dict):
                tax_id = entity.get('tax_id') or entity.get('ein')
                if tax_id:
                    institution_data['institution']['tax_id'] = tax_id
                    identifiers['tax_id'] = tax_id
                    logger.info(f"Added tax ID {tax_id} to institution data from GLEIF")
        
        # Update institution info with CFPB metadata if available
        cfpb_meta = institution_data.get('cfpb_metadata', {})
        if cfpb_meta:
            # Get assets from CFPB or transmittal sheet
            assets = cfpb_meta.get('assets')
            if not assets and cfpb_meta.get('transmittal_sheet'):
                assets = cfpb_meta['transmittal_sheet'].get('assets')
            
            # Get type from CFPB
            institution_type = cfpb_meta.get('type')
            
            # Build location from GLEIF if CFPB doesn't have it
            location = cfpb_meta.get('location')
            if not location:
                # Try to get from GLEIF corporate structure
                corporate_structure = institution_data.get('corporate_structure', {})
                if corporate_structure:
                    hq = corporate_structure.get('headquarters', {})
                    if hq:
                        city = hq.get('city', '')
                        state = hq.get('state', '')
                        if city and state:
                            location = f"{city}, {state}"
            
            institution_data['institution'].update({
                'assets': assets,
                'type': institution_type,
                'location': location
            })
            
            logger.info(f"Updated institution data: assets={assets}, type={institution_type}, location={location}")
        
        # Process financial data using code-based processor
        from justdata.apps.lenderprofile.processors.data_processors import FinancialDataProcessor
        fdic_financials_raw = institution_data.get('fdic_financials', {}).get('data', [])
        financial_processed = FinancialDataProcessor.process_fdic_financials(fdic_financials_raw)
        
        # Organize financial data
        institution_data['financial'] = {
            'fdic_call_reports': fdic_financials_raw,
            'processed': financial_processed,  # Code-processed structured data
            'trends': financial_processed.get('trends', {}),
            'metrics': financial_processed.get('metrics', {}),
            'growth': financial_processed.get('growth', {})
        }
        
        # Analyze branch network using BigQuery SOD data
        from justdata.apps.lenderprofile.branch_network_analyzer import BranchNetworkAnalyzer
        branch_analysis = None
        
        # Determine institution type (bank vs credit union)
        institution_type = 'bank'  # Default to bank
        cfpb_meta = institution_data.get('cfpb_metadata', {})
        if cfpb_meta and 'credit union' in (cfpb_meta.get('type', '') or '').lower():
            institution_type = 'credit_union'
        
        # Get RSSD for branch analysis
        rssd_for_branches = rssd_id or identifiers.get('rssd_id')
        
        if rssd_for_branches:
            try:
                analyzer = BranchNetworkAnalyzer(use_bigquery=True, institution_type=institution_type)
                current_year = datetime.now().year
                years = list(range(current_year - 4, current_year + 1))  # Last 5 years
                
                # Get branch network history
                branch_history, branch_metadata = analyzer.get_branch_network_history(
                    rssd=rssd_for_branches,
                    cu_number=identifiers.get('cu_number') if institution_type == 'credit_union' else None,
                    years=years
                )
                
                # Analyze the branch network
                if branch_history:
                    # The analyze_network_changes method returns a dict with closures, openings, trends, etc.
                    branch_analysis_result = analyzer.analyze_network_changes(branch_history, branch_metadata)

                    # Find the most recent year that actually has data
                    years_with_data = sorted([y for y in branch_history.keys() if branch_history[y]], reverse=True)
                    most_recent_year = years_with_data[0] if years_with_data else max(years)

                    # Get all branches from most recent year with data for map visualization
                    all_branches = branch_history.get(most_recent_year, [])

                    # Get summary from the analysis
                    summary = {
                        'total_branches_current': len(all_branches),
                        'total_branches_by_year': branch_analysis_result.get('total_branches_by_year', {}),
                        'trends': branch_analysis_result.get('trends', {}),
                        'geographic_shifts': branch_analysis_result.get('geographic_shifts', {})
                    }

                    branch_analysis = {
                        'summary': summary,
                        'closures_by_year': branch_analysis_result.get('closures_by_year', {}),
                        'openings_by_year': branch_analysis_result.get('openings_by_year', {}),
                        'net_change_by_year': branch_analysis_result.get('net_change_by_year', {}),
                        'all_branches': all_branches,
                        'years_analyzed': years,
                        'most_recent_year': most_recent_year
                    }

                    logger.info(f"Branch network analysis complete: {len(all_branches)} branches in {most_recent_year}")
            except Exception as e:
                logger.error(f"Error analyzing branch network: {e}", exc_info=True)
                branch_analysis = None
        
        # Organize branch data
        institution_data['branches'] = {
            'analysis': branch_analysis if 'branch_analysis' in locals() else None,
            'history': branch_history if 'branch_history' in locals() else {},
            'metadata': branch_metadata if 'branch_metadata' in locals() else {},
            'locations': branch_analysis.get('all_branches', []) if 'branch_analysis' in locals() and branch_analysis else [],
            'summary': branch_analysis.get('summary', {}) if 'branch_analysis' in locals() and branch_analysis else {}
        }
        
        # Organize merger data
        institution_data['mergers'] = {
            'historical': institution_data.get('federal_reserve', {}).get('historical_mergers', []),
            'pending': institution_data.get('federal_register', {}).get('pending_mergers', [])
        }

        # STEP 3: Run Data Source Analysts (Haiku-powered parallel analysis)
        # Each analyst produces standardized findings that feed into the final synthesis
        try:
            ai_entity_resolution = institution_data.get('ai_entity_resolution', {})

            if ai_entity_resolution:
                logger.info("Running Tier 1 Data Source Analysts (Haiku)...")
                analyst_results = self.data_analysts.analyze_all(
                    institution_data,
                    ai_entity_resolution
                )

                # Compile summaries for Tier 2 synthesizer
                compiled_summaries = compile_analyst_summaries(analyst_results)
                institution_data['analyst_summaries'] = compiled_summaries

                # Store individual analyst results for detailed inspection
                institution_data['analyst_results'] = {
                    source: {
                        'has_data': result.has_data,
                        'data_quality': result.data_quality,
                        'key_findings': result.key_findings,
                        'ncrc_insights': result.ncrc_insights,
                        'risk_flags': result.risk_flags,
                        'positive_indicators': result.positive_indicators,
                        'talking_points': result.talking_points,
                        'metrics': result.metrics,
                        'raw_summary': result.raw_summary
                    }
                    for source, result in analyst_results.items()
                }

                # Log summary
                quality_summary = compiled_summaries.get('data_quality_summary', {})
                logger.info(f"Tier 1 analysis complete: {len(analyst_results)} sources analyzed")
                logger.info(f"Data quality: {quality_summary}")
                logger.info(f"Key findings: {len(compiled_summaries.get('all_key_findings', []))}, "
                           f"Risk flags: {len(compiled_summaries.get('all_risk_flags', []))}")
            else:
                logger.warning("Skipping Tier 1 analysts - no AI entity resolution available")
                institution_data['analyst_summaries'] = {}
                institution_data['analyst_results'] = {}
        except Exception as e:
            logger.error(f"Tier 1 Data Source Analysts failed: {e}", exc_info=True)
            institution_data['analyst_summaries'] = {}
            institution_data['analyst_results'] = {}

        logger.info(f"Data collection complete for {institution_name}")
        return institution_data
    
    # FDIC Institution API removed - we use CFPB/GLEIF for institution data
    # Only FDIC Financial API (Call Reports) is used
