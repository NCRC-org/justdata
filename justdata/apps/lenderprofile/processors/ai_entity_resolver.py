#!/usr/bin/env python3
"""
AI Entity Resolver for LenderProfile

Uses AI to intelligently determine the optimal entity identifiers for each data source
and evaluate news relevance. This resolver runs early in the data collection pipeline
and its output informs all downstream processes.

Key responsibilities:
1. Map corporate hierarchy to optimal entity for each data source (SEC, HMDA, FDIC, CFPB)
2. Generate intelligent news search keywords and exclusions
3. Evaluate news article relevance to the institution and NCRC focus areas
4. Provide context that informs the AI summary generation
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from justdata.shared.analysis.ai_provider import ask_ai

logger = logging.getLogger(__name__)


class AIEntityResolver:
    """
    AI-powered entity resolver that determines the optimal entity identifiers
    for each data source based on corporate hierarchy analysis.
    """

    def __init__(self):
        self.resolution_cache = {}

    def resolve_entities(
        self,
        institution_name: str,
        corporate_family: Dict[str, Any],
        identifiers: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze corporate structure and determine optimal entity for each data source.

        Args:
            institution_name: The user's search query / institution name
            corporate_family: GLEIF corporate family data with parent/children
            identifiers: Known identifiers (fdic_cert, rssd_id, lei, etc.)

        Returns:
            Structured resolution with entity mappings, news strategy, and context
        """
        # Build context for AI
        queried_entity = corporate_family.get('queried_entity', {})
        ultimate_parent = corporate_family.get('ultimate_parent')
        all_entities = corporate_family.get('all_entities', [])

        # Extract entity names and LEIs for context
        entity_list = []
        for entity in all_entities[:20]:  # Limit to prevent token overflow
            entity_list.append({
                'name': entity.get('name', 'Unknown'),
                'lei': entity.get('lei', ''),
                'relationship': entity.get('relationship', 'unknown')
            })

        prompt = f"""You are a financial data expert. Analyze corporate structures and determine optimal data source mappings. Return ONLY valid JSON, no markdown or explanation.

Analyze this corporate structure and determine the optimal entity to query for each data source.

SEARCHED INSTITUTION: {institution_name}
SEARCHED ENTITY LEI: {queried_entity.get('lei', 'Unknown')}

KNOWN IDENTIFIERS:
- FDIC Cert: {identifiers.get('fdic_cert', 'Unknown')}
- RSSD ID: {identifiers.get('rssd_id', 'Unknown')}
- LEI: {identifiers.get('lei', 'Unknown')}
- CIK: {identifiers.get('sec_cik', 'Unknown')}

ULTIMATE PARENT: {ultimate_parent.get('name') if ultimate_parent else 'None identified'}
ULTIMATE PARENT LEI: {ultimate_parent.get('lei') if ultimate_parent else 'N/A'}

CORPORATE FAMILY ({len(entity_list)} entities):
{json.dumps(entity_list, indent=2)}

Based on this corporate structure, provide a JSON response with:

1. **entity_mapping**: Which entity to use for each data source
2. **news_strategy**: Keywords and exclusions for relevant news
3. **corporate_context**: Key facts about corporate structure
4. **data_quality_notes**: Any concerns about data availability

IMPORTANT DATA SOURCE RULES:
- SEC (10-K, DEF 14A): Usually filed by the ULTIMATE PARENT holding company
- HMDA (mortgage lending): Filed by the actual mortgage lending entity (usually the "National Association" bank)
- FDIC/Branch data: Uses the chartered bank entity (has FDIC cert)
- CFPB complaints: Search the consumer-facing brand name(s)
- CRA (small business lending): Uses the chartered bank's respondent ID

Return ONLY valid JSON in this exact format:
{{
    "entity_mapping": {{
        "sec": {{
            "name": "Company Name for SEC queries",
            "reason": "Brief explanation"
        }},
        "hmda": {{
            "lei": "LEI for HMDA queries",
            "name": "Entity name",
            "reason": "Brief explanation"
        }},
        "fdic": {{
            "name": "Entity name for FDIC",
            "reason": "Brief explanation"
        }},
        "cfpb": {{
            "names": ["Primary name", "Alternative name"],
            "reason": "Brief explanation"
        }}
    }},
    "news_strategy": {{
        "primary_keywords": ["Main company name", "Common abbreviation"],
        "secondary_keywords": ["CEO name if known", "Recent merger target"],
        "exclusion_terms": ["Subsidiary names that would pollute results"],
        "ncrc_focus_terms": ["CRA", "community reinvestment", "branch closure", "fair lending", "redlining"]
    }},
    "corporate_context": {{
        "is_holding_company": true/false,
        "is_operating_bank": true/false,
        "has_sec_filing_parent": true/false,
        "parent_files_sec": true/false,
        "institution_type": "National Bank/State Bank/Credit Union/Holding Company",
        "key_subsidiaries": ["Notable subsidiary names"],
        "consumer_brands": ["Consumer-facing brand names"]
    }},
    "data_quality_notes": {{
        "sec_availability": "Expected/Limited/Unlikely",
        "hmda_availability": "Expected/Limited/Unlikely",
        "concerns": ["Any data availability concerns"]
    }}
}}"""

        try:
            logger.info(f"AI Entity Resolution for: {institution_name}")

            response = ask_ai(
                prompt,
                max_tokens=2000
            )

            # Parse JSON response
            resolution = self._parse_ai_response(response)

            if resolution:
                # Add metadata
                resolution['_metadata'] = {
                    'resolved_at': datetime.now().isoformat(),
                    'institution_name': institution_name,
                    'queried_lei': queried_entity.get('lei'),
                    'entity_count': len(all_entities)
                }

                logger.info(f"AI Entity Resolution complete: {len(resolution.get('entity_mapping', {}))} mappings")
                return resolution
            else:
                logger.warning("AI Entity Resolution failed to parse, using fallback")
                return self._fallback_resolution(institution_name, corporate_family, identifiers)

        except Exception as e:
            logger.error(f"AI Entity Resolution error: {e}")
            return self._fallback_resolution(institution_name, corporate_family, identifiers)

    def _parse_ai_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse AI response, handling potential formatting issues."""
        if not response:
            return None

        # Try to extract JSON from response
        try:
            # Clean up common issues
            text = response.strip()

            # Remove markdown code blocks if present
            if text.startswith('```'):
                lines = text.split('\n')
                # Remove first and last lines if they're code block markers
                if lines[0].startswith('```'):
                    lines = lines[1:]
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                text = '\n'.join(lines)

            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}")

            # Try to find JSON object in response
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass

            return None

    def _fallback_resolution(
        self,
        institution_name: str,
        corporate_family: Dict[str, Any],
        identifiers: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fallback resolution when AI fails."""
        queried_entity = corporate_family.get('queried_entity', {})
        ultimate_parent = corporate_family.get('ultimate_parent')

        return {
            'entity_mapping': {
                'sec': {
                    'name': ultimate_parent.get('name', institution_name) if ultimate_parent else institution_name,
                    'reason': 'Using ultimate parent or queried entity (fallback)'
                },
                'hmda': {
                    'lei': queried_entity.get('lei') or identifiers.get('lei', ''),
                    'name': institution_name,
                    'reason': 'Using queried entity (fallback)'
                },
                'fdic': {
                    'name': institution_name,
                    'reason': 'Using queried entity (fallback)'
                },
                'cfpb': {
                    'names': [institution_name],
                    'reason': 'Using queried entity name (fallback)'
                }
            },
            'news_strategy': {
                'primary_keywords': [institution_name],
                'secondary_keywords': [],
                'exclusion_terms': [],
                'ncrc_focus_terms': ['CRA', 'community reinvestment', 'branch closure', 'fair lending']
            },
            'corporate_context': {
                'is_holding_company': False,
                'is_operating_bank': True,
                'has_sec_filing_parent': bool(ultimate_parent),
                'parent_files_sec': bool(ultimate_parent),
                'institution_type': 'Unknown',
                'key_subsidiaries': [],
                'consumer_brands': [institution_name]
            },
            'data_quality_notes': {
                'sec_availability': 'Unknown',
                'hmda_availability': 'Unknown',
                'concerns': ['AI resolution failed, using fallback mappings']
            },
            '_metadata': {
                'resolved_at': datetime.now().isoformat(),
                'institution_name': institution_name,
                'is_fallback': True
            }
        }

    def score_news_relevance(
        self,
        articles: List[Dict[str, Any]],
        resolution: Dict[str, Any],
        institution_name: str
    ) -> List[Dict[str, Any]]:
        """
        Use AI to score and filter news articles for relevance.

        Args:
            articles: List of news articles with title, description, source
            resolution: The entity resolution from resolve_entities()
            institution_name: The institution being profiled

        Returns:
            Articles with relevance scores and categorization
        """
        if not articles:
            return []

        # Limit articles for AI processing
        articles_to_score = articles[:30]

        news_strategy = resolution.get('news_strategy', {})
        primary_keywords = news_strategy.get('primary_keywords', [institution_name])
        exclusion_terms = news_strategy.get('exclusion_terms', [])

        # Build article summaries for AI
        article_summaries = []
        for i, article in enumerate(articles_to_score):
            article_summaries.append({
                'id': i,
                'title': article.get('title', '')[:200],
                'description': (article.get('description') or '')[:300],
                'source': article.get('source', {}).get('name', 'Unknown')
            })

        prompt = f"""You are a financial news analyst. Score articles for relevance. Return ONLY a valid JSON array.

Score these news articles for relevance to {institution_name}.

COMPANY CONTEXT:
- Primary search terms: {', '.join(primary_keywords)}
- Exclude articles about: {', '.join(exclusion_terms) if exclusion_terms else 'N/A'}
- NCRC focus areas: CRA compliance, fair lending, branch closures, mergers, executive changes, regulatory actions

ARTICLES TO SCORE:
{json.dumps(article_summaries, indent=2)}

For each article, provide:
1. relevance_score: 0-100 (100 = highly relevant to the institution)
2. category: "regulatory" | "merger" | "leadership" | "earnings" | "community" | "other"
3. ncrc_relevant: true/false (relevant to NCRC's fair lending/CRA mission)
4. include: true/false (should be included in report)
5. reason: Brief explanation (10 words max)

Return ONLY valid JSON array:
[
    {{"id": 0, "relevance_score": 85, "category": "regulatory", "ncrc_relevant": true, "include": true, "reason": "CRA exam results"}},
    ...
]"""

        try:
            response = ask_ai(
                prompt,
                max_tokens=2000
            )

            scores = self._parse_ai_response(response)

            if scores and isinstance(scores, list):
                # Merge scores back into articles
                score_map = {s['id']: s for s in scores if isinstance(s, dict) and 'id' in s}

                scored_articles = []
                for i, article in enumerate(articles_to_score):
                    score_data = score_map.get(i, {})
                    article['ai_relevance'] = {
                        'score': score_data.get('relevance_score', 50),
                        'category': score_data.get('category', 'other'),
                        'ncrc_relevant': score_data.get('ncrc_relevant', False),
                        'include': score_data.get('include', True),
                        'reason': score_data.get('reason', '')
                    }
                    scored_articles.append(article)

                # Sort by relevance and filter
                scored_articles.sort(key=lambda x: x.get('ai_relevance', {}).get('score', 0), reverse=True)

                # Keep only articles marked for inclusion
                included = [a for a in scored_articles if a.get('ai_relevance', {}).get('include', True)]

                logger.info(f"AI News Scoring: {len(included)}/{len(articles_to_score)} articles included")
                return included

        except Exception as e:
            logger.error(f"AI News Scoring error: {e}")

        # Fallback: return all articles without scoring
        return articles_to_score

    def generate_search_context(self, resolution: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate search context for downstream processes.

        Returns a simplified context object that can be used by:
        - Data collectors to choose the right entity
        - News fetchers to filter relevant articles
        - AI summarizer to understand corporate structure
        """
        entity_mapping = resolution.get('entity_mapping', {})
        news_strategy = resolution.get('news_strategy', {})
        corporate_context = resolution.get('corporate_context', {})

        return {
            # For SEC queries
            'sec_entity_name': entity_mapping.get('sec', {}).get('name'),
            'sec_search_names': [
                entity_mapping.get('sec', {}).get('name'),
                # Add variations
            ],

            # For HMDA queries
            'hmda_lei': entity_mapping.get('hmda', {}).get('lei'),
            'hmda_entity_name': entity_mapping.get('hmda', {}).get('name'),

            # For CFPB queries
            'cfpb_names': entity_mapping.get('cfpb', {}).get('names', []),

            # For news filtering
            'news_keywords': news_strategy.get('primary_keywords', []),
            'news_exclusions': news_strategy.get('exclusion_terms', []),
            'ncrc_focus_terms': news_strategy.get('ncrc_focus_terms', []),

            # Corporate structure context for AI summary
            'is_holding_company': corporate_context.get('is_holding_company', False),
            'is_operating_bank': corporate_context.get('is_operating_bank', True),
            'parent_files_sec': corporate_context.get('parent_files_sec', False),
            'institution_type': corporate_context.get('institution_type', 'Unknown'),
            'consumer_brands': corporate_context.get('consumer_brands', []),

            # Data quality expectations
            'expected_sec_data': resolution.get('data_quality_notes', {}).get('sec_availability') == 'Expected',
            'expected_hmda_data': resolution.get('data_quality_notes', {}).get('hmda_availability') == 'Expected',

            # Full resolution for reference
            '_full_resolution': resolution
        }
