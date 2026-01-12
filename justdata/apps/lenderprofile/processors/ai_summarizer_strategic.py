#!/usr/bin/env python3
"""
Strategic AI Methods for LenderProfile - Code-First Architecture
These are the ONLY 5 AI calls made per report. All data processing happens
in code first, then AI synthesizes pre-processed structured data.
"""

import json
import re
from typing import Dict, Any, Optional, List
from shared.analysis.ai_provider import AIAnalyzer


class StrategicAICalls:
    """
    Strategic AI calls for narrative synthesis only.
    All data extraction and structuring happens in code processors.
    """
    
    def __init__(self, ai_analyzer: AIAnalyzer):
        """
        Initialize with an AI analyzer instance.
        
        Args:
            ai_analyzer: AIAnalyzer instance for making AI calls
        """
        self.ai = ai_analyzer
    
    def generate_strategy_analysis(self, item1_business: str, report_focus: Optional[str] = None) -> Dict[str, Any]:
        """
        AI Call #1: Extract strategic priorities from Item 1 business description.
        
        Args:
            item1_business: Item 1 business description text (from SEC parser)
            report_focus: Optional user-specified focus
            
        Returns:
            JSON object with strategic priorities, performance drivers, expansion plans
        """
        if not item1_business:
            return {'available': False}
        
        focus_context = ""
        if report_focus:
            focus_context = f"""
        
        USER REPORT FOCUS: {report_focus}
        Ensure strategy analysis addresses this focus appropriately.
        """
        
        prompt = f"""
        Analyze this Management Discussion & Analysis section from a 10-K filing.

        FILING TEXT:
        {item1_business[:8000]}

        {focus_context}

        Extract and structure:
        1. Strategic priorities mentioned by management (bullet list)
        2. Key performance drivers identified (bullet list)
        3. Geographic expansion plans (bullet list)
        4. Challenges or headwinds mentioned (bullet list)
        5. Forward-looking statements about growth areas (bullet list)

        Return ONLY a JSON object with these five arrays. No additional commentary.
        Format:
        {{
            "strategic_priorities": ["priority1", "priority2", ...],
            "performance_drivers": ["driver1", "driver2", ...],
            "geographic_expansion": ["plan1", "plan2", ...],
            "challenges": ["challenge1", "challenge2", ...],
            "growth_areas": ["area1", "area2", ...]
        }}
        """
        
        response = self.ai._call_ai(prompt, max_tokens=500, temperature=0.3)
        
        # Try to parse JSON from response
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
        except:
            pass
        
        return {'raw_response': response, 'available': True}
    
    def generate_risk_analysis(self, item1a_risks: str, report_focus: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        AI Call #2: Identify top 5 risk categories from Item 1A risk factors.
        
        Args:
            item1a_risks: Item 1A risk factors text (from SEC parser)
            report_focus: Optional user-specified focus
            
        Returns:
            JSON array with top 5 risk categories
        """
        if not item1a_risks:
            return []
        
        focus_context = ""
        if report_focus:
            focus_context = f"""
        
        USER REPORT FOCUS: {report_focus}
        Ensure risk analysis addresses this focus appropriately.
        """
        
        prompt = f"""
        Review these risk factors from Item 1A of a 10-K filing.

        RISK FACTORS:
        {item1a_risks[:12000]}

        {focus_context}

        Identify the top 5 most significant risk categories mentioned. For each category, provide:
        - Category name
        - Brief description (1 sentence)
        - Whether this is industry-standard or company-specific risk

        Return as JSON array. No preamble.
        Format:
        [
            {{
                "category": "Risk Category Name",
                "description": "Brief description",
                "type": "industry-standard" or "company-specific"
            }},
            ...
        ]
        """
        
        response = self.ai._call_ai(prompt, max_tokens=800, temperature=0.3)
        
        # Try to parse JSON from response
        try:
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
        except:
            pass
        
        return [{'raw_response': response}]
    
    def generate_mda_insights(self, item7_mda: str, report_focus: Optional[str] = None) -> Dict[str, Any]:
        """
        AI Call #3: Extract MD&A insights from Item 7 management discussion.
        
        Args:
            item7_mda: Item 7 MD&A section text (from SEC parser)
            report_focus: Optional user-specified focus
            
        Returns:
            JSON object with strategic priorities, challenges, forward-looking statements
        """
        if not item7_mda:
            return {'available': False}
        
        focus_context = ""
        if report_focus:
            focus_context = f"""
        
        USER REPORT FOCUS: {report_focus}
        Ensure MD&A insights address this focus appropriately.
        """
        
        prompt = f"""
        Analyze this Management Discussion & Analysis section from a 10-K filing.

        MD&A TEXT:
        {item7_mda[:15000]}

        {focus_context}

        Extract and structure:
        1. Strategic priorities mentioned by management (bullet list)
        2. Key performance drivers identified (bullet list)
        3. Challenges or headwinds mentioned (bullet list)
        4. Forward-looking statements about growth areas (bullet list)
        5. Notable financial trends or patterns discussed (bullet list)

        Return ONLY a JSON object with these five arrays. No additional commentary.
        Format:
        {{
            "strategic_priorities": ["priority1", "priority2", ...],
            "performance_drivers": ["driver1", "driver2", ...],
            "challenges": ["challenge1", "challenge2", ...],
            "growth_areas": ["area1", "area2", ...],
            "financial_trends": ["trend1", "trend2", ...]
        }}
        """
        
        response = self.ai._call_ai(prompt, max_tokens=800, temperature=0.3)
        
        # Try to parse JSON from response
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
        except:
            pass
        
        return {'raw_response': response, 'available': True}
    
    def generate_news_sentiment(self, news_processed: Dict[str, Any], report_focus: Optional[str] = None) -> Dict[str, Any]:
        """
        AI Call #4: Analyze sentiment and categorize news articles.
        
        Args:
            news_processed: Processed news data from NewsProcessor
            report_focus: Optional user-specified focus
            
        Returns:
            JSON object with sentiment analysis and key themes
        """
        if not news_processed or not news_processed.get('available'):
            return {'available': False}
        
        focus_context = ""
        if report_focus:
            focus_context = f"""
        
        USER REPORT FOCUS: {report_focus}
        Ensure news sentiment analysis addresses this focus appropriately.
        """
        
        # Prepare article summaries
        recent_articles = news_processed.get('recent', [])[:10]
        article_summaries = []
        for article in recent_articles:
            title = article.get('title', '')
            description = article.get('description', '')[:200]
            article_summaries.append(f"Title: {title}\nDescription: {description}")
        
        categorized = news_processed.get('categorized', {})
        
        prompt = f"""
        Analyze news articles about this financial institution and provide sentiment analysis.

        RECENT ARTICLES:
        {chr(10).join(article_summaries)[:3000]}

        CATEGORIZED ARTICLES:
        - Executive: {len(categorized.get('executive', []))} articles
        - Strategy: {len(categorized.get('strategy', []))} articles
        - Regulatory: {len(categorized.get('regulatory', []))} articles
        - Financial: {len(categorized.get('financial', []))} articles
        - Controversy: {len(categorized.get('controversy', []))} articles

        {focus_context}

        Provide sentiment analysis:
        1. Overall sentiment (positive/neutral/negative)
        2. Key themes (3-5 themes)
        3. Notable events or developments mentioned
        4. Regulatory or compliance concerns (if any)

        Return as JSON object. No preamble.
        Format:
        {{
            "overall_sentiment": "positive/neutral/negative",
            "key_themes": ["theme1", "theme2", ...],
            "notable_events": ["event1", "event2", ...],
            "regulatory_concerns": ["concern1", "concern2", ...]
        }}
        """
        
        response = self.ai._call_ai(prompt, max_tokens=400, temperature=0.3)
        
        # Try to parse JSON from response
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
        except:
            pass
        
        return {'raw_response': response, 'available': True}

