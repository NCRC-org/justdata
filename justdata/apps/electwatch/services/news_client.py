#!/usr/bin/env python3
"""
News Client for ElectWatch

Fetches and filters news from multiple sources with:
- Source quality filtering (reliability, reputation, credibility)
- Story deduplication (avoid showing same story from multiple outlets)
- Primary source identification (link to original, not reposts)
- Authority scoring (stories covered by multiple reliable sources rank higher)

Sources are tiered by reliability:
- Tier 1: Major wire services and newspapers of record
- Tier 2: Respected financial/political publications
- Tier 3: Established news outlets
- Tier 4: Specialty/niche sources (used but lower weight)
"""

import logging
import os
import re
import requests
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from collections import defaultdict

logger = logging.getLogger(__name__)


# =============================================================================
# SOURCE QUALITY TIERS
# =============================================================================

# Tier 1: Wire services and newspapers of record (highest authority)
TIER_1_SOURCES = {
    'reuters': {'name': 'Reuters', 'score': 100, 'type': 'wire'},
    'associated press': {'name': 'Associated Press', 'score': 100, 'type': 'wire'},
    'ap news': {'name': 'AP News', 'score': 100, 'type': 'wire'},
    'the wall street journal': {'name': 'Wall Street Journal', 'score': 98, 'type': 'newspaper'},
    'wsj': {'name': 'Wall Street Journal', 'score': 98, 'type': 'newspaper'},
    'the new york times': {'name': 'New York Times', 'score': 97, 'type': 'newspaper'},
    'the washington post': {'name': 'Washington Post', 'score': 96, 'type': 'newspaper'},
    'financial times': {'name': 'Financial Times', 'score': 97, 'type': 'newspaper'},
    'bloomberg': {'name': 'Bloomberg', 'score': 95, 'type': 'financial'},
}

# Tier 2: Respected financial and political publications
TIER_2_SOURCES = {
    'cnbc': {'name': 'CNBC', 'score': 85, 'type': 'financial'},
    'the economist': {'name': 'The Economist', 'score': 90, 'type': 'magazine'},
    'politico': {'name': 'Politico', 'score': 88, 'type': 'political'},
    'the hill': {'name': 'The Hill', 'score': 85, 'type': 'political'},
    'axios': {'name': 'Axios', 'score': 84, 'type': 'news'},
    'npr': {'name': 'NPR', 'score': 88, 'type': 'public'},
    'bbc news': {'name': 'BBC News', 'score': 90, 'type': 'international'},
    'forbes': {'name': 'Forbes', 'score': 82, 'type': 'business'},
    'barrons': {'name': "Barron's", 'score': 85, 'type': 'financial'},
    "barron's": {'name': "Barron's", 'score': 85, 'type': 'financial'},
    'marketwatch': {'name': 'MarketWatch', 'score': 80, 'type': 'financial'},
    'fortune': {'name': 'Fortune', 'score': 82, 'type': 'business'},
}

# Tier 3: Established news outlets
TIER_3_SOURCES = {
    'cnn': {'name': 'CNN', 'score': 75, 'type': 'news'},
    'abc news': {'name': 'ABC News', 'score': 78, 'type': 'news'},
    'cbs news': {'name': 'CBS News', 'score': 78, 'type': 'news'},
    'nbc news': {'name': 'NBC News', 'score': 78, 'type': 'news'},
    'usa today': {'name': 'USA Today', 'score': 72, 'type': 'newspaper'},
    'los angeles times': {'name': 'Los Angeles Times', 'score': 80, 'type': 'newspaper'},
    'chicago tribune': {'name': 'Chicago Tribune', 'score': 78, 'type': 'newspaper'},
    'the guardian': {'name': 'The Guardian', 'score': 82, 'type': 'international'},
    'business insider': {'name': 'Business Insider', 'score': 70, 'type': 'business'},
    'insider': {'name': 'Insider', 'score': 70, 'type': 'business'},
    'yahoo finance': {'name': 'Yahoo Finance', 'score': 68, 'type': 'aggregator'},
    'yahoo': {'name': 'Yahoo', 'score': 65, 'type': 'aggregator'},
    'thefly.com': {'name': 'The Fly', 'score': 72, 'type': 'financial'},
    'seeking alpha': {'name': 'Seeking Alpha', 'score': 65, 'type': 'financial'},
    'seekingalpha': {'name': 'Seeking Alpha', 'score': 65, 'type': 'financial'},
}

# Tier 4: Specialty sources (crypto, fintech, etc.)
TIER_4_SOURCES = {
    'coindesk': {'name': 'CoinDesk', 'score': 75, 'type': 'crypto'},
    'cointelegraph': {'name': 'Cointelegraph', 'score': 70, 'type': 'crypto'},
    'the block': {'name': 'The Block', 'score': 72, 'type': 'crypto'},
    'decrypt': {'name': 'Decrypt', 'score': 68, 'type': 'crypto'},
    'bitcoinist': {'name': 'Bitcoinist', 'score': 60, 'type': 'crypto'},
    'zycrypto': {'name': 'ZyCrypto', 'score': 55, 'type': 'crypto'},
    'american banker': {'name': 'American Banker', 'score': 80, 'type': 'banking'},
    'housing wire': {'name': 'HousingWire', 'score': 75, 'type': 'mortgage'},
    'national mortgage news': {'name': 'National Mortgage News', 'score': 75, 'type': 'mortgage'},
    'bankrate': {'name': 'Bankrate', 'score': 70, 'type': 'consumer'},
}

# Combine all sources
ALL_SOURCES = {**TIER_1_SOURCES, **TIER_2_SOURCES, **TIER_3_SOURCES, **TIER_4_SOURCES}

# Sources to exclude (low quality, clickbait, or unreliable)
EXCLUDED_SOURCES = {
    'dansdeals.com', 'dansdeals',  # Deal aggregator, not news
    'screen rant', 'screenrant',  # Entertainment
    'benzinga',  # Often low-quality aggregation
    'motley fool',  # Investment advice, not news
    'investorplace',  # Investment advice
    '247wallst',  # Listicles
}

# Minimum score to include (filters out unknown sources)
MIN_SOURCE_SCORE = 50


def get_source_info(source_name: str) -> Tuple[int, str, bool]:
    """
    Get source reliability score and info.

    Returns:
        Tuple of (score, canonical_name, is_verified)
    """
    if not source_name:
        return (0, 'Unknown', False)

    source_lower = source_name.lower().strip()

    # Check exclusion list
    if source_lower in EXCLUDED_SOURCES:
        return (0, source_name, False)

    # Check known sources
    if source_lower in ALL_SOURCES:
        info = ALL_SOURCES[source_lower]
        return (info['score'], info['name'], True)

    # Try partial matching for variations
    for key, info in ALL_SOURCES.items():
        if key in source_lower or source_lower in key:
            return (info['score'], info['name'], True)

    # Unknown source - give minimal score
    return (MIN_SOURCE_SCORE - 10, source_name, False)


def is_reliable_source(source_name: str, min_score: int = MIN_SOURCE_SCORE) -> bool:
    """Check if a source meets minimum reliability threshold."""
    score, _, _ = get_source_info(source_name)
    return score >= min_score


# =============================================================================
# DEDUPLICATION
# =============================================================================

def normalize_headline(headline: str) -> str:
    """Normalize headline for comparison."""
    if not headline:
        return ""
    # Lowercase, remove punctuation, extra spaces
    text = headline.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = ' '.join(text.split())
    return text


def headline_similarity(h1: str, h2: str) -> float:
    """Calculate similarity between two headlines (0.0 to 1.0)."""
    n1 = normalize_headline(h1)
    n2 = normalize_headline(h2)
    if not n1 or not n2:
        return 0.0
    return SequenceMatcher(None, n1, n2).ratio()


def extract_key_terms(headline: str) -> Set[str]:
    """Extract key terms from headline for clustering."""
    # Remove common words
    stop_words = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
        'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as',
        'into', 'through', 'during', 'before', 'after', 'above', 'below',
        'and', 'but', 'or', 'nor', 'so', 'yet', 'both', 'either', 'neither',
        'not', 'only', 'own', 'same', 'than', 'too', 'very', 'just',
        'says', 'said', 'report', 'reports', 'news', 'update', 'latest',
        'new', 'what', 'why', 'how', 'when', 'where', 'who', 'which',
    }

    normalized = normalize_headline(headline)
    words = set(normalized.split())
    # Keep words with 3+ chars that aren't stop words
    return {w for w in words if len(w) >= 3 and w not in stop_words}


def cluster_similar_stories(articles: List[Dict]) -> List[List[Dict]]:
    """
    Cluster articles that are about the same story.

    Uses a combination of:
    - Headline similarity (SequenceMatcher)
    - Key term overlap
    - Time proximity (stories within 48 hours)
    """
    if not articles:
        return []

    # Sort by date (newest first)
    sorted_articles = sorted(
        articles,
        key=lambda x: x.get('published_at', ''),
        reverse=True
    )

    clusters = []
    used = set()

    for i, article in enumerate(sorted_articles):
        if i in used:
            continue

        cluster = [article]
        used.add(i)

        h1 = article.get('title', '')
        terms1 = extract_key_terms(h1)
        date1 = article.get('published_at', '')[:10]  # YYYY-MM-DD

        for j, other in enumerate(sorted_articles[i+1:], start=i+1):
            if j in used:
                continue

            h2 = other.get('title', '')
            terms2 = extract_key_terms(h2)
            date2 = other.get('published_at', '')[:10]

            # Check similarity
            sim = headline_similarity(h1, h2)

            # Check term overlap
            if terms1 and terms2:
                overlap = len(terms1 & terms2) / min(len(terms1), len(terms2))
            else:
                overlap = 0

            # Cluster if:
            # - Headlines are very similar (>0.7), OR
            # - Headlines share many key terms (>0.6) AND moderate similarity (>0.4)
            if sim > 0.7 or (overlap > 0.6 and sim > 0.4):
                cluster.append(other)
                used.add(j)

        clusters.append(cluster)

    return clusters


def select_primary_article(cluster: List[Dict]) -> Dict:
    """
    Select the best article from a cluster to show.

    Prioritizes:
    1. Highest source reliability score
    2. If tie, earliest publication (original source)
    3. If still tie, longest content (more detail)
    """
    if not cluster:
        return {}
    if len(cluster) == 1:
        article = cluster[0]
        article['authority_score'] = get_source_info(article.get('source', ''))[0]
        article['coverage_count'] = 1
        return article

    # Score each article
    scored = []
    for article in cluster:
        source = article.get('source', '')
        score, canonical_name, is_verified = get_source_info(source)
        scored.append({
            'article': article,
            'score': score,
            'canonical_name': canonical_name,
            'is_verified': is_verified,
            'date': article.get('published_at', ''),
            'content_len': len(article.get('description', '') or '')
        })

    # Sort by: score (desc), then date (asc for earliest), then content length (desc)
    scored.sort(key=lambda x: (-x['score'], x['date'], -x['content_len']))

    best = scored[0]['article']

    # Add metadata about coverage
    best['authority_score'] = scored[0]['score']
    best['coverage_count'] = len(cluster)
    best['covered_by'] = [s['canonical_name'] for s in scored if s['is_verified']][:5]
    best['is_verified_source'] = scored[0]['is_verified']

    return best


# =============================================================================
# NEWS CLIENT
# =============================================================================

class NewsClient:
    """
    Unified news client with quality filtering and deduplication.

    Usage:
        client = NewsClient()

        # Get deduplicated, quality-filtered news
        news = client.search_news('cryptocurrency regulation', days=7)

        # Get news for a specific company
        news = client.get_company_news('Wells Fargo', days=30)
    """

    NEWSAPI_BASE = "https://newsapi.org/v2"

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the news client."""
        self.api_key = api_key or os.getenv('NEWSAPI_API_KEY')
        if not self.api_key:
            logger.warning("NEWSAPI_API_KEY not set - news features will be limited")

        self.timeout = 30
        self._cache = {}
        self._cache_time = {}
        self._cache_duration = timedelta(minutes=30)

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache is valid."""
        if key not in self._cache_time:
            return False
        return datetime.now() - self._cache_time[key] < self._cache_duration

    def _fetch_from_newsapi(
        self,
        query: str,
        days: int = 7,
        page_size: int = 100,
        sort_by: str = 'publishedAt'
    ) -> List[Dict]:
        """Fetch raw articles from NewsAPI."""
        if not self.api_key:
            return []

        from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        try:
            response = requests.get(
                f"{self.NEWSAPI_BASE}/everything",
                params={
                    'apiKey': self.api_key,
                    'q': query,
                    'from': from_date,
                    'language': 'en',
                    'sortBy': sort_by,
                    'pageSize': min(page_size, 100)
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            return data.get('articles', [])
        except Exception as e:
            logger.error(f"NewsAPI error: {e}")
            return []

    def _normalize_article(self, article: Dict) -> Dict:
        """Normalize NewsAPI article to standard format."""
        source = article.get('source', {})
        source_name = source.get('name', '') if isinstance(source, dict) else str(source)

        return {
            'title': article.get('title', ''),
            'description': article.get('description', ''),
            'url': article.get('url', ''),
            'source': source_name,
            'published_at': article.get('publishedAt', ''),
            'image_url': article.get('urlToImage', ''),
            'author': article.get('author', ''),
        }

    def search_news(
        self,
        query: str,
        days: int = 7,
        limit: int = 20,
        min_source_score: int = MIN_SOURCE_SCORE,
        deduplicate: bool = True
    ) -> List[Dict]:
        """
        Search for news with quality filtering and deduplication.

        Args:
            query: Search query
            days: Number of days to look back
            limit: Maximum articles to return
            min_source_score: Minimum source reliability score (0-100)
            deduplicate: Whether to deduplicate similar stories

        Returns:
            List of articles, deduplicated with primary sources prioritized
        """
        cache_key = f"search_{query}_{days}_{min_source_score}"
        if cache_key in self._cache and self._is_cache_valid(cache_key):
            return self._cache[cache_key][:limit]

        # Fetch raw articles
        raw_articles = self._fetch_from_newsapi(query, days, page_size=100)

        # Normalize and filter by source quality
        filtered = []
        for article in raw_articles:
            normalized = self._normalize_article(article)
            source = normalized['source']

            # Skip excluded sources
            if source.lower() in EXCLUDED_SOURCES:
                continue

            # Check source score
            score, canonical_name, is_verified = get_source_info(source)
            if score < min_source_score:
                continue

            normalized['source_score'] = score
            normalized['source_canonical'] = canonical_name
            normalized['is_verified_source'] = is_verified
            filtered.append(normalized)

        if not filtered:
            return []

        # Deduplicate
        if deduplicate:
            clusters = cluster_similar_stories(filtered)
            results = [select_primary_article(cluster) for cluster in clusters]
        else:
            results = filtered

        # Sort by authority (coverage count * source score)
        results.sort(
            key=lambda x: (
                x.get('coverage_count', 1) * x.get('authority_score', 50),
                x.get('published_at', '')
            ),
            reverse=True
        )

        self._cache[cache_key] = results
        self._cache_time[cache_key] = datetime.now()

        return results[:limit]

    def get_company_news(
        self,
        company_name: str,
        days: int = 30,
        limit: int = 15
    ) -> List[Dict]:
        """Get news for a specific company."""
        return self.search_news(
            query=f'"{company_name}"',
            days=days,
            limit=limit
        )

    def get_industry_news(
        self,
        industry: str,
        days: int = 7,
        limit: int = 15
    ) -> List[Dict]:
        """Get news for an industry sector."""
        # Map industry codes to search queries
        industry_queries = {
            'banking': 'banking regulation OR "bank earnings" OR FDIC OR "commercial bank"',
            'crypto': 'cryptocurrency regulation OR bitcoin OR "digital assets" OR SEC crypto',
            'mortgage': 'mortgage rates OR housing market OR "home loans" OR Fannie Mae',
            'fintech': 'fintech OR "digital payments" OR "financial technology"',
            'investment': 'investment banking OR "asset management" OR hedge fund',
            'insurance': 'insurance regulation OR "insurance company"',
            'consumer_lending': 'credit cards OR "consumer lending" OR CFPB',
        }

        query = industry_queries.get(industry.lower(), industry)
        return self.search_news(query=query, days=days, limit=limit)

    def get_political_finance_news(
        self,
        days: int = 7,
        limit: int = 20
    ) -> List[Dict]:
        """Get news about political finance, lobbying, campaign contributions."""
        queries = [
            'congress stock trading OR "congressional trading"',
            'campaign contributions OR PAC donations',
            'financial regulation congress',
            'lobbying disclosure',
        ]

        all_articles = []
        for query in queries:
            articles = self.search_news(query=query, days=days, limit=30, deduplicate=False)
            all_articles.extend(articles)

        # Deduplicate across all queries
        clusters = cluster_similar_stories(all_articles)
        results = [select_primary_article(cluster) for cluster in clusters]

        # Sort by authority
        results.sort(
            key=lambda x: (
                x.get('coverage_count', 1) * x.get('authority_score', 50),
                x.get('published_at', '')
            ),
            reverse=True
        )

        return results[:limit]

    def test_connection(self) -> bool:
        """Test API connection."""
        if not self.api_key:
            return False
        articles = self._fetch_from_newsapi('test', days=1, page_size=1)
        return len(articles) > 0


# =============================================================================
# MODULE-LEVEL CONVENIENCE FUNCTIONS
# =============================================================================

_client = None


def get_news_client() -> NewsClient:
    """Get singleton NewsClient instance."""
    global _client
    if _client is None:
        _client = NewsClient()
    return _client


def search_news(query: str, **kwargs) -> List[Dict]:
    """Convenience function to search news."""
    return get_news_client().search_news(query, **kwargs)


def get_company_news(company_name: str, **kwargs) -> List[Dict]:
    """Convenience function to get company news."""
    return get_news_client().get_company_news(company_name, **kwargs)


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent.parent / '.env')

    client = NewsClient()

    if not client.api_key:
        print("ERROR: NEWSAPI_API_KEY not set")
    else:
        print("Testing News Client with Quality Filtering...")
        print("=" * 60)

        # Test 1: Search with deduplication
        print("\n=== Crypto Regulation News (deduplicated) ===")
        news = client.search_news('cryptocurrency regulation congress', days=7, limit=5)
        for article in news:
            coverage = article.get('coverage_count', 1)
            score = article.get('authority_score', 0)
            verified = "[V]" if article.get('is_verified_source') else "[?]"
            covered_by = article.get('covered_by', [])

            print(f"\n{verified} [{score}] {article['title'][:70]}...")
            print(f"   Source: {article.get('source_canonical', article['source'])} | Coverage: {coverage} outlets")
            if len(covered_by) > 1:
                print(f"   Also covered by: {', '.join(covered_by[1:4])}")
            print(f"   URL: {article['url'][:60]}...")

        # Test 2: Company news
        print("\n\n=== Wells Fargo News ===")
        news = client.get_company_news('Wells Fargo', days=7, limit=3)
        for article in news:
            verified = "[V]" if article.get('is_verified_source') else "[?]"
            print(f"{verified} {article['title'][:60]}... ({article['source']})")

        # Test 3: Show source filtering
        print("\n\n=== Source Quality Demo ===")
        test_sources = ['Reuters', 'Wall Street Journal', 'Yahoo', 'ZyCrypto', 'DansDeals.com', 'Unknown Blog']
        for source in test_sources:
            score, canonical, verified = get_source_info(source)
            status = "Verified" if verified else "Unverified"
            print(f"  {source}: Score={score}, Canonical='{canonical}', {status}")
