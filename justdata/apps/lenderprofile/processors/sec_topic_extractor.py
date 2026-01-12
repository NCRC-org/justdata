#!/usr/bin/env python3
"""
SEC Topic Extractor for NCRC-Relevant Mentions

Extracts mentions of community reinvestment, regulatory issues,
strategy changes, and other NCRC-relevant topics from SEC filings.
"""

import re
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


@dataclass
class TopicMatch:
    """A single topic mention extracted from a filing."""
    topic: str
    category: str
    text: str  # The surrounding context (paragraph or sentence)
    filing_type: str  # 10-K or 10-Q
    filing_date: str
    section: str  # Which section of the filing (Item 1, Item 7, etc.)


# Topic categories with keywords and phrases to search for
NCRC_TOPICS = {
    'community_reinvestment': {
        'name': 'Community Reinvestment Act',
        'keywords': [
            'community reinvestment act', 'cra', 'cra rating', 'cra examination',
            'cra compliance', 'community development', 'low-to-moderate income',
            'low- and moderate-income', 'lmi communities', 'lmi areas',
            'community reinvestment', 'reinvestment act'
        ],
        'priority': 1
    },
    'community_benefits': {
        'name': 'Community Benefits Agreements',
        'keywords': [
            'community benefits agreement', 'community benefit agreement',
            'community commitment', 'community plan', 'community investment plan',
            'national community reinvestment coalition', 'ncrc',
            'community groups', 'community organizations'
        ],
        'priority': 1
    },
    'branches': {
        'name': 'Bank Branches',
        'keywords': [
            'branch network', 'branch closure', 'branch consolidation',
            'branch opening', 'new branch', 'branch expansion',
            'banking center', 'financial center', 'branch location',
            'branch rationalization', 'branch optimization', 'physical locations'
        ],
        'priority': 2
    },
    'mortgage_lending': {
        'name': 'Mortgage Lending',
        'keywords': [
            'mortgage lending', 'mortgage origination', 'home mortgage',
            'residential mortgage', 'mortgage portfolio', 'hmda',
            'home purchase', 'refinance', 'home equity', 'heloc',
            'fair lending', 'equal credit', 'redlining', 'mortgage discrimination'
        ],
        'priority': 2
    },
    'small_business_lending': {
        'name': 'Small Business Lending',
        'keywords': [
            'small business lending', 'small business loan', 'sba loan',
            'business lending', 'commercial lending', 'minority business',
            'women-owned business', 'small business administration',
            'paycheck protection', 'ppp loan', 'business credit'
        ],
        'priority': 2
    },
    'regulatory_issues': {
        'name': 'Regulatory Issues',
        'keywords': [
            'regulatory', 'regulator', 'examination', 'supervisory',
            'compliance', 'occ', 'fdic', 'federal reserve', 'cfpb',
            'consumer financial protection', 'regulatory requirement',
            'regulatory matter', 'regulatory action', 'regulatory concern'
        ],
        'priority': 1
    },
    'enforcement_actions': {
        'name': 'Enforcement Actions & Judgements',
        'keywords': [
            'enforcement action', 'consent order', 'cease and desist',
            'civil money penalty', 'fine', 'penalty', 'settlement',
            'judgement', 'judgment', 'litigation', 'lawsuit', 'legal action',
            'class action', 'regulatory sanction', 'memorandum of understanding',
            'mou', 'formal agreement', 'written agreement'
        ],
        'priority': 1
    },
    'leadership_changes': {
        'name': 'Senior Staff Transitions',
        'keywords': [
            'chief executive', 'ceo', 'president', 'chief financial',
            'cfo', 'chief operating', 'coo', 'chief risk', 'cro',
            'executive officer', 'board of directors', 'director',
            'appointed', 'resigned', 'retired', 'departure', 'transition',
            'succession', 'new leadership', 'management change'
        ],
        'priority': 2
    },
    'mergers_acquisitions': {
        'name': 'Mergers & Acquisitions',
        'keywords': [
            'merger', 'acquisition', 'acquire', 'acquired', 'acquiring',
            'business combination', 'consolidation', 'integration',
            'pending merger', 'proposed acquisition', 'merger agreement',
            'purchase agreement', 'definitive agreement', 'strategic transaction'
        ],
        'priority': 1
    },
    'strategy': {
        'name': 'Overall Strategy',
        'keywords': [
            'strategic plan', 'strategic initiative', 'business strategy',
            'growth strategy', 'transformation', 'strategic priority',
            'strategic direction', 'long-term strategy', 'strategic focus',
            'strategic objective', 'corporate strategy'
        ],
        'priority': 2
    },
    'strategy_changes': {
        'name': 'Strategy Changes',
        'keywords': [
            'strategic shift', 'change in strategy', 'revised strategy',
            'new direction', 'pivot', 'restructuring', 'reorganization',
            'strategic review', 'business model change', 'transformation initiative',
            'strategic realignment', 'refocusing'
        ],
        'priority': 1
    },
    'market_outlook': {
        'name': 'Market Predictions',
        'keywords': [
            'outlook', 'forecast', 'projection', 'expectation',
            'anticipate', 'expect', 'predict', 'guidance',
            'forward-looking', 'future', 'next year', 'coming year',
            'economic conditions', 'market conditions', 'interest rate environment'
        ],
        'priority': 3
    },
    'affordable_housing': {
        'name': 'Affordable Housing',
        'keywords': [
            'affordable housing', 'low-income housing', 'lihtc',
            'housing tax credit', 'community development financial',
            'cdfi', 'housing finance', 'housing assistance',
            'first-time homebuyer', 'down payment assistance'
        ],
        'priority': 1
    },
    'diversity_inclusion': {
        'name': 'Diversity & Inclusion',
        'keywords': [
            'diversity', 'inclusion', 'diverse supplier', 'minority',
            'underserved', 'underbanked', 'unbanked', 'financial inclusion',
            'equal opportunity', 'dei', 'diverse communities'
        ],
        'priority': 2
    }
}


class SECTopicExtractor:
    """
    Extracts NCRC-relevant topic mentions from SEC 10-K and 10-Q filings.
    """

    def __init__(self, sec_client=None):
        """
        Initialize the extractor.

        Args:
            sec_client: Optional SECClient instance (will create one if not provided)
        """
        if sec_client:
            self.sec_client = sec_client
        else:
            from justdata.apps.lenderprofile.services.sec_client import SECClient
            self.sec_client = SECClient()

    def get_last_4_quarters_filings(self, cik: str) -> List[Dict[str, Any]]:
        """
        Get the last 4 quarters of 10-K and 10-Q filings.

        Args:
            cik: Company CIK number

        Returns:
            List of filings with type, date, and accession number
        """
        filings = []

        # Get company submissions
        submissions = self.sec_client.get_company_submissions(cik)
        if not submissions or 'filings' not in submissions:
            logger.warning(f"No submissions found for CIK {cik}")
            return []

        recent = submissions.get('filings', {}).get('recent', {})
        if not recent:
            return []

        forms = recent.get('form', [])
        dates = recent.get('filingDate', [])
        accessions = recent.get('accessionNumber', [])

        # Collect 10-K and 10-Q filings (last 4 quarters = ~1 10-K + 3 10-Qs)
        count_10k = 0
        count_10q = 0

        for i, form in enumerate(forms):
            if form in ('10-K', '10-Q'):
                # Limit: 1 10-K and 3 10-Qs (or up to 4 10-Qs if no 10-K)
                if form == '10-K' and count_10k >= 1:
                    continue
                if form == '10-Q' and count_10q >= 3:
                    continue

                filings.append({
                    'type': form,
                    'date': dates[i] if i < len(dates) else None,
                    'accession_number': accessions[i] if i < len(accessions) else None
                })

                if form == '10-K':
                    count_10k += 1
                else:
                    count_10q += 1

                # Stop after 4 total filings
                if len(filings) >= 4:
                    break

        logger.info(f"Found {len(filings)} filings for CIK {cik}: {count_10k} 10-K, {count_10q} 10-Q")
        return filings

    def fetch_filing_content(self, cik: str, filing: Dict[str, Any]) -> Optional[str]:
        """
        Fetch the text content of a filing.

        Args:
            cik: Company CIK
            filing: Filing dict with type, date, accession_number

        Returns:
            Filing text content or None
        """
        accession = filing.get('accession_number')
        filing_type = filing.get('type')

        if not accession:
            logger.warning(f"No accession number for {filing_type} filing")
            return None

        try:
            if filing_type == '10-K':
                content = self.sec_client.get_10k_filing_content(cik, accession)
            else:  # 10-Q
                # Use same method - it works for 10-Q too
                content = self.sec_client.get_10k_filing_content(cik, accession)

            if content:
                logger.info(f"Fetched {filing_type} content: {len(content)} chars")
            return content
        except Exception as e:
            logger.error(f"Error fetching {filing_type} content: {e}")
            return None

    def extract_paragraph_context(self, text: str, match_start: int, match_end: int,
                                   context_chars: int = 500) -> str:
        """
        Extract the paragraph or surrounding context for a match.

        Args:
            text: Full text
            match_start: Start position of match
            match_end: End position of match
            context_chars: Number of chars to include before/after

        Returns:
            Context string with the match highlighted
        """
        # Find paragraph boundaries (double newline or significant whitespace)
        start = max(0, match_start - context_chars)
        end = min(len(text), match_end + context_chars)

        # Try to extend to sentence boundaries
        while start > 0 and text[start] not in '.!?\n':
            start -= 1
        start = min(start + 1, match_start)

        while end < len(text) and text[end] not in '.!?\n':
            end += 1
        end = min(end + 1, len(text))

        context = text[start:end].strip()

        # Clean up whitespace
        context = re.sub(r'\s+', ' ', context)

        return context

    def identify_section(self, text: str, position: int) -> str:
        """
        Identify which section of the filing a position is in.

        Args:
            text: Full filing text
            position: Character position

        Returns:
            Section name (e.g., "Item 1", "Item 7", "Risk Factors")
        """
        # Look backwards from position for section markers
        text_before = text[:position].lower()

        section_markers = [
            ('item 1a', 'Item 1A - Risk Factors'),
            ('item 1b', 'Item 1B - Unresolved Staff Comments'),
            ('item 1', 'Item 1 - Business'),
            ('item 2', 'Item 2 - Properties'),
            ('item 3', 'Item 3 - Legal Proceedings'),
            ('item 7a', 'Item 7A - Market Risk'),
            ('item 7', 'Item 7 - MD&A'),
            ('item 8', 'Item 8 - Financial Statements'),
            ('risk factor', 'Risk Factors'),
            ('management discussion', 'MD&A'),
            ('legal proceeding', 'Legal Proceedings'),
        ]

        for marker, section_name in section_markers:
            # Find the last occurrence of this marker before position
            last_pos = text_before.rfind(marker)
            if last_pos != -1 and (position - last_pos) < 100000:  # Within 100k chars
                return section_name

        return 'General'

    def extract_topics_from_text(self, text: str, filing_type: str,
                                  filing_date: str) -> List[TopicMatch]:
        """
        Extract all NCRC-relevant topic mentions from filing text.

        Args:
            text: Filing text content
            filing_type: "10-K" or "10-Q"
            filing_date: Filing date string

        Returns:
            List of TopicMatch objects
        """
        if not text:
            return []

        matches = []
        text_lower = text.lower()

        for topic_id, topic_config in NCRC_TOPICS.items():
            topic_name = topic_config['name']
            keywords = topic_config['keywords']

            # Find all keyword matches
            for keyword in keywords:
                # Use word boundary matching for short keywords
                if len(keyword) <= 4:
                    pattern = r'\b' + re.escape(keyword) + r'\b'
                else:
                    pattern = re.escape(keyword)

                for match in re.finditer(pattern, text_lower):
                    # Extract context
                    context = self.extract_paragraph_context(
                        text, match.start(), match.end()
                    )

                    # Identify section
                    section = self.identify_section(text, match.start())

                    matches.append(TopicMatch(
                        topic=topic_name,
                        category=topic_id,
                        text=context,
                        filing_type=filing_type,
                        filing_date=filing_date,
                        section=section
                    ))

        # Deduplicate by context (same paragraph shouldn't appear multiple times)
        seen_contexts = set()
        unique_matches = []
        for match in matches:
            # Create a short hash of the context
            context_hash = hash(match.text[:200] + match.category)
            if context_hash not in seen_contexts:
                seen_contexts.add(context_hash)
                unique_matches.append(match)

        logger.info(f"Found {len(unique_matches)} unique topic mentions in {filing_type}")
        return unique_matches

    def analyze_filings(self, cik: str, max_workers: int = 3) -> Dict[str, Any]:
        """
        Analyze the last 4 quarters of filings for NCRC-relevant topics.

        Args:
            cik: Company CIK number
            max_workers: Max parallel workers for fetching filings

        Returns:
            Dictionary with topic analysis results
        """
        # Get filings list
        filings = self.get_last_4_quarters_filings(cik)
        if not filings:
            return {
                'has_data': False,
                'error': 'No 10-K or 10-Q filings found',
                'filings_analyzed': 0
            }

        all_matches: List[TopicMatch] = []

        # Fetch and analyze each filing
        # Use sequential for now to respect SEC rate limits
        for filing in filings:
            content = self.fetch_filing_content(cik, filing)
            if content:
                matches = self.extract_topics_from_text(
                    content,
                    filing['type'],
                    filing['date']
                )
                all_matches.extend(matches)

        # Organize by topic
        by_topic = {}
        for match in all_matches:
            if match.category not in by_topic:
                by_topic[match.category] = {
                    'name': match.topic,
                    'mentions': [],
                    'count': 0,
                    'filings': set()
                }
            by_topic[match.category]['mentions'].append({
                'text': match.text,
                'filing': match.filing_type,
                'date': match.filing_date,
                'section': match.section
            })
            by_topic[match.category]['count'] += 1
            by_topic[match.category]['filings'].add(f"{match.filing_type} ({match.filing_date})")

        # Convert sets to lists for JSON serialization
        for topic_id in by_topic:
            by_topic[topic_id]['filings'] = list(by_topic[topic_id]['filings'])
            # Limit mentions to top 5 per topic to avoid huge output
            by_topic[topic_id]['mentions'] = by_topic[topic_id]['mentions'][:5]

        # Sort topics by priority and count
        sorted_topics = sorted(
            by_topic.items(),
            key=lambda x: (NCRC_TOPICS.get(x[0], {}).get('priority', 99), -x[1]['count'])
        )

        # Build summary
        total_mentions = sum(t['count'] for t in by_topic.values())
        high_priority_topics = [
            t['name'] for tid, t in sorted_topics
            if NCRC_TOPICS.get(tid, {}).get('priority', 99) == 1 and t['count'] > 0
        ]

        return {
            'has_data': True,
            'filings_analyzed': len(filings),
            'filings': [f"{f['type']} ({f['date']})" for f in filings],
            'total_mentions': total_mentions,
            'topics_found': len([t for t in by_topic.values() if t['count'] > 0]),
            'high_priority_topics': high_priority_topics,
            'by_topic': dict(sorted_topics),
            'summary': self._generate_summary(by_topic, filings)
        }

    def _generate_summary(self, by_topic: Dict[str, Any],
                          filings: List[Dict[str, Any]]) -> str:
        """Generate a natural language summary of findings."""
        if not by_topic:
            return "No NCRC-relevant topics found in the analyzed filings."

        parts = []
        filing_desc = f"{len(filings)} filings (last 4 quarters)"

        # High priority findings
        high_priority = [
            (tid, t) for tid, t in by_topic.items()
            if NCRC_TOPICS.get(tid, {}).get('priority', 99) == 1 and t['count'] > 0
        ]

        if high_priority:
            topics_list = ', '.join(t['name'] for _, t in high_priority[:3])
            parts.append(f"Key topics mentioned: {topics_list}")

        # CRA specific
        if 'community_reinvestment' in by_topic and by_topic['community_reinvestment']['count'] > 0:
            count = by_topic['community_reinvestment']['count']
            parts.append(f"CRA mentioned {count} times")

        # Regulatory/enforcement
        reg_count = by_topic.get('regulatory_issues', {}).get('count', 0)
        enf_count = by_topic.get('enforcement_actions', {}).get('count', 0)
        if reg_count > 0 or enf_count > 0:
            parts.append(f"Regulatory matters: {reg_count + enf_count} mentions")

        # M&A
        if 'mergers_acquisitions' in by_topic and by_topic['mergers_acquisitions']['count'] > 0:
            parts.append(f"M&A activity discussed")

        return f"Analysis of {filing_desc}: " + "; ".join(parts) if parts else f"Analyzed {filing_desc}."

    def generate_ai_narrative(self, analysis_results: Dict[str, Any],
                               company_name: str) -> str:
        """
        Generate a 2-paragraph AI narrative about SEC filing findings.

        The narrative is:
        - Written in plain English for educated non-specialists
        - Factual and based only on data in evidence
        - Professional and concise
        - Does not suggest policy or solutions

        Args:
            analysis_results: Results from analyze_filings()
            company_name: Name of the company

        Returns:
            2-paragraph narrative string
        """
        if not analysis_results.get('has_data'):
            return f"No SEC 10-K or 10-Q filings were available for analysis for {company_name}."

        # Build context for AI
        by_topic = analysis_results.get('by_topic', {})
        filings = analysis_results.get('filings', [])
        total_mentions = analysis_results.get('total_mentions', 0)

        # Collect sample excerpts for each topic (limit to avoid token overflow)
        topic_excerpts = []
        for topic_id, topic_data in by_topic.items():
            if topic_data.get('count', 0) > 0:
                topic_name = topic_data.get('name', topic_id)
                count = topic_data['count']
                # Get first mention as example
                mentions = topic_data.get('mentions', [])
                sample = mentions[0]['text'][:300] if mentions else ''
                topic_excerpts.append({
                    'topic': topic_name,
                    'count': count,
                    'sample': sample
                })

        # Sort by count
        topic_excerpts.sort(key=lambda x: -x['count'])

        # Build the prompt
        prompt = f"""Write exactly 2 paragraphs summarizing what {company_name} disclosed in their recent SEC filings about community-focused banking topics.

FILING DATA:
- Filings analyzed: {', '.join(filings)}
- Total topic mentions: {total_mentions}

TOPICS FOUND (with mention counts and sample excerpts):
"""
        for excerpt in topic_excerpts[:8]:  # Limit to top 8 topics
            prompt += f"\n{excerpt['topic']} ({excerpt['count']} mentions):"
            if excerpt['sample']:
                prompt += f"\n  Sample: \"{excerpt['sample']}...\""

        prompt += """

REQUIREMENTS:
- Write exactly 2 paragraphs
- Use plain English for an educated but non-specialist audience
- Be factual - only state what the data shows, do not assume or infer beyond the evidence
- Do not suggest policy changes or solutions
- Be professional and concise
- Focus on what the company disclosed about community reinvestment, regulatory matters, lending practices, and strategic direction
- If limited data exists, acknowledge that briefly

Write the 2-paragraph narrative now:"""

        try:
            from justdata.shared.analysis.ai_provider import ask_ai
            narrative = ask_ai(
                prompt,
                max_tokens=600,
                temperature=0.3  # Lower temperature for more factual output
            )
            return narrative.strip()
        except Exception as e:
            logger.error(f"Error generating AI narrative: {e}")
            # Fallback to basic summary
            return self._generate_fallback_narrative(analysis_results, company_name)

    def _generate_fallback_narrative(self, analysis_results: Dict[str, Any],
                                      company_name: str) -> str:
        """Generate a basic narrative without AI if the AI call fails."""
        by_topic = analysis_results.get('by_topic', {})
        filings = analysis_results.get('filings', [])

        # First paragraph - overview
        filing_count = len(filings)
        topics_found = [t['name'] for t in by_topic.values() if t.get('count', 0) > 0]

        para1 = f"Analysis of {company_name}'s last {filing_count} SEC filings reveals discussion of several community-focused topics. "
        if topics_found:
            para1 += f"The filings contain references to {', '.join(topics_found[:4])}."
        else:
            para1 += "No significant community-focused disclosures were identified."

        # Second paragraph - specifics
        para2_parts = []
        cra_count = by_topic.get('community_reinvestment', {}).get('count', 0)
        if cra_count > 0:
            para2_parts.append(f"Community Reinvestment Act compliance was mentioned {cra_count} times")

        reg_count = by_topic.get('regulatory_issues', {}).get('count', 0)
        enf_count = by_topic.get('enforcement_actions', {}).get('count', 0)
        if reg_count > 0 or enf_count > 0:
            para2_parts.append(f"regulatory and enforcement matters appeared {reg_count + enf_count} times")

        ma_count = by_topic.get('mergers_acquisitions', {}).get('count', 0)
        if ma_count > 0:
            para2_parts.append(f"merger and acquisition activity was discussed")

        para2 = "Specifically, " + ", and ".join(para2_parts) + "." if para2_parts else "The filings did not contain notable community-focused disclosures."

        return f"{para1}\n\n{para2}"
