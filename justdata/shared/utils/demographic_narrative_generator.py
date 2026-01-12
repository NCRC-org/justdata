#!/usr/bin/env python3
"""
Demographic Narrative Generator
Generates AI-powered narratives analyzing demographic trends across time periods.
"""

import os
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


def format_demographic_data_for_prompt(historical_census_data: Dict[str, Dict[str, Any]]) -> str:
    """
    Format historical census data into a structured format for the AI prompt.
    
    Args:
        historical_census_data: Dictionary mapping geoid5 to census data with time_periods
    
    Returns:
        Formatted string with demographic data for all time periods
    """
    if not historical_census_data:
        return "No demographic data available."
    
    # Aggregate data across counties for each time period
    time_periods_data = {
        'acs': {},
        'census2020': {},
        'census2010': {}
    }
    
    total_adult_pop = {'acs': 0, 'census2020': 0, 'census2010': 0}
    
    for geoid5, county_data in historical_census_data.items():
        time_periods = county_data.get('time_periods', {})
        
        for period_key in ['acs', 'census2020', 'census2010']:
            period_data = time_periods.get(period_key)
            if period_data and period_data.get('demographics'):
                demo = period_data['demographics']
                pop = demo.get('total_population', 0)  # This is adult pop for ACS, adult pop for 2020/2010
                
                if pop > 0:
                    total_adult_pop[period_key] += pop
                    
                    # Aggregate percentages (weighted by population)
                    if not time_periods_data[period_key]:
                        time_periods_data[period_key] = {
                            'white': 0, 'black': 0, 'asian': 0, 'native_american': 0,
                            'hopi': 0, 'multi_racial': 0, 'hispanic': 0
                        }
                    
                    time_periods_data[period_key]['white'] += (demo.get('white_percentage', 0) * pop) / 100
                    time_periods_data[period_key]['black'] += (demo.get('black_percentage', 0) * pop) / 100
                    time_periods_data[period_key]['asian'] += (demo.get('asian_percentage', 0) * pop) / 100
                    time_periods_data[period_key]['native_american'] += (demo.get('native_american_percentage', 0) * pop) / 100
                    time_periods_data[period_key]['hopi'] += (demo.get('hopi_percentage', 0) * pop) / 100
                    time_periods_data[period_key]['multi_racial'] += (demo.get('multi_racial_percentage', 0) * pop) / 100
                    time_periods_data[period_key]['hispanic'] += (demo.get('hispanic_percentage', 0) * pop) / 100
    
    # Calculate final percentages
    formatted_data = []
    
    for period_key, period_label in [('acs', 'Most Recent ACS'), ('census2020', '2020 Census'), ('census2010', '2010 Census')]:
        if time_periods_data[period_key] and total_adult_pop[period_key] > 0:
            pop = total_adult_pop[period_key]
            data = time_periods_data[period_key]
            
            formatted_data.append(f"\n{period_label} (Adult Population 18+):")
            formatted_data.append(f"  Total Adult Population: {int(pop):,}")
            formatted_data.append(f"  White: {(data['white'] / pop * 100):.1f}%")
            formatted_data.append(f"  Black: {(data['black'] / pop * 100):.1f}%")
            formatted_data.append(f"  Asian: {(data['asian'] / pop * 100):.1f}%")
            formatted_data.append(f"  Native American: {(data['native_american'] / pop * 100):.1f}%")
            formatted_data.append(f"  Native Hawaiian/Pacific Islander: {(data['hopi'] / pop * 100):.1f}%")
            formatted_data.append(f"  Multi-racial: {(data['multi_racial'] / pop * 100):.1f}%")
            formatted_data.append(f"  Hispanic: {(data['hispanic'] / pop * 100):.1f}%")
    
    return '\n'.join(formatted_data) if formatted_data else "No demographic data available."


def generate_demographic_analysis_prompt(historical_census_data: Dict[str, Dict[str, Any]]) -> str:
    """
    Generate the AI prompt for demographic trend analysis.
    
    Args:
        historical_census_data: Dictionary mapping geoid5 to census data with time_periods
    
    Returns:
        Complete prompt string for AI analysis
    """
    demographic_data_text = format_demographic_data_for_prompt(historical_census_data)
    
    prompt = f"""# Cursor Prompt: Demographic Trend Analysis

Analyze the demographic data comparing three time periods (most recent ACS, 2020 Census, 2010 Census) and write a 2-paragraph plain English discussion of trends. All data represents adult population (18+).

## Data to Analyze

{demographic_data_text}

## Analysis Instructions

For each demographic group:
1. Calculate the percentage point change between time periods (e.g., 15.2% - 14.4% = 0.8 points)
2. Calculate the relative change (e.g., 15.2% / 14.4% = 1.056, or 5.6% increase)
3. Use these thresholds to determine qualitative descriptors:
   - Relative change < 2%: "remained stable" or "changed minimally"
   - Relative change 2-5%: "increased/decreased slightly" or "saw a small increase/decrease"
   - Relative change 5-10%: "increased/decreased moderately" or "grew/declined modestly"
   - Relative change 10-20%: "increased/decreased substantially" or "experienced notable growth/decline"
   - Relative change > 20%: "increased/decreased significantly" or "grew/declined markedly"

## Writing Requirements

Write exactly 2 paragraphs:

**Paragraph 1**: Summarize the overall demographic composition and major shifts. Focus on which groups comprise the largest shares and whether the area is becoming more or less diverse. Identify the most significant changes.

**Paragraph 2**: Discuss specific trends for individual groups, highlighting notable patterns. Connect changes to broader demographic trends where relevant (aging population, migration patterns, etc.).

## Style Guidelines

- Use plain English suitable for general audiences
- NO raw percentages in the text (e.g., don't write "increased from 14.4% to 15.2%")
- Use contextual descriptions instead (e.g., "the Black population increased slightly")
- Focus on patterns and insights, not reciting numbers
- Write in active voice with brief sentences
- Avoid technical jargon
- Present findings objectively without speculating about causes

## Example Output Style

"The area remains predominantly White, though this majority has declined modestly over the past decade while the Hispanic and Asian populations have grown substantially. The Black population remained relatively stable across all three time periods, while the multi-racial population increased slightly."

"Native American and Pacific Islander populations remain small shares of the overall population with minimal change over time. The Asian population showed the most dramatic growth, nearly doubling its share since 2010. Hispanic residents also increased significantly, reflecting broader regional migration patterns. These shifts indicate the area is becoming more racially and ethnically diverse, though the pace of change varies considerably across groups."

Now analyze the provided data and write your 2-paragraph demographic trend analysis:"""
    
    return prompt


def generate_demographic_narrative(
    historical_census_data: Dict[str, Dict[str, Any]],
    use_ai: bool = True
) -> str:
    """
    Generate demographic trend narrative using AI.
    
    Args:
        historical_census_data: Dictionary mapping geoid5 to census data with time_periods
        use_ai: Whether to use AI service (default True)
    
    Returns:
        Generated narrative text (2 paragraphs)
    """
    if not historical_census_data:
        return "Demographic data is not available for analysis."
    
    if not use_ai:
        return "AI narrative generation is disabled."
    
    try:
        from shared.analysis.ai_provider import AIAnalyzer
        
        prompt = generate_demographic_analysis_prompt(historical_census_data)
        
        analyzer = AIAnalyzer()
        narrative = analyzer._call_ai(
            prompt=prompt,
            max_tokens=800,
            temperature=0.3
        )
        
        if narrative:
            # Clean up the response (remove any markdown formatting if present)
            narrative = narrative.strip()
            # Remove markdown code blocks if present
            if narrative.startswith('```'):
                lines = narrative.split('\n')
                narrative = '\n'.join(lines[1:-1]) if len(lines) > 2 else narrative
            narrative = narrative.strip()
            
            logger.info("Successfully generated demographic narrative")
            return narrative
        else:
            logger.warning("AI returned empty narrative")
            return "Unable to generate demographic analysis at this time."
            
    except ImportError:
        logger.warning("AI provider not available - cannot generate narrative")
        return "AI narrative generation is not available."
    except Exception as e:
        logger.error(f"Error generating demographic narrative: {e}")
        import traceback
        traceback.print_exc()
        return "An error occurred while generating the demographic analysis."
