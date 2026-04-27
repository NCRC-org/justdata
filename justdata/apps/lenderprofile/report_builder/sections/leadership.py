"""Leadership and compensation section."""
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

import json
from justdata.apps.lenderprofile.report_builder.helpers import (
    _format_currency,
    _truncate_text,
)

def _verify_executive_names_with_ai(
    executives: List[Dict[str, Any]],
    institution_name: str
) -> List[Dict[str, Any]]:
    """
    Use AI to verify and correct executive names that appear incomplete.

    Some iXBRL filings only contain first names (e.g., "Jay" instead of "Jay Farner").
    This function uses AI to identify and correct incomplete names.

    Args:
        executives: List of executive dicts with name, title, compensation
        institution_name: Company name for context

    Returns:
        List of executives with corrected names
    """
    # Check if any executives have incomplete names (single word, no spaces)
    incomplete_names = [e for e in executives if e.get('name') and ' ' not in e.get('name', '').strip()]

    if not incomplete_names:
        # All names appear complete, no AI verification needed
        return executives

    logger.info(f"Found {len(incomplete_names)} potentially incomplete executive names, using AI to verify")

    try:
        from justdata.shared.analysis.ai_provider import ask_ai

        # Build prompt with executive data
        exec_list = []
        for e in executives:
            exec_list.append({
                'name': e.get('name', ''),
                'title': e.get('title', ''),
                'compensation': e.get('total', 0)
            })

        prompt = f"""You are verifying executive names for {institution_name}.

The following executives were extracted from SEC filings, but some names may be incomplete (first name only):

{json.dumps(exec_list, indent=2)}

For each executive, provide the FULL NAME if you know it. Use your knowledge of {institution_name}'s leadership.

Return ONLY a JSON array with corrected names in this exact format:
[
    {{"original_name": "Jay", "full_name": "Jay Farner", "title": "CEO"}},
    {{"original_name": "Bill", "full_name": "Bill Emerson", "title": "Vice Chairman"}}
]

If you don't know an executive's full name, use the original name.
Return ONLY valid JSON, no markdown or explanation."""

        response = ask_ai(
            prompt,
            model="claude-3-5-haiku-20241022",
            max_tokens=1000,
            temperature=0
        )

        # Parse AI response
        # Clean response of markdown if present
        clean_response = response.strip()
        if clean_response.startswith('```'):
            clean_response = re.sub(r'^```(?:json)?\s*', '', clean_response)
            clean_response = re.sub(r'\s*```$', '', clean_response)

        corrections = json.loads(clean_response)

        # Build correction map
        name_corrections = {}
        for correction in corrections:
            original = correction.get('original_name', '').lower().strip()
            full_name = correction.get('full_name', '')
            if original and full_name and original != full_name.lower():
                name_corrections[original] = full_name

        if name_corrections:
            logger.info(f"AI corrected {len(name_corrections)} executive names: {name_corrections}")

        # Apply corrections
        corrected_executives = []
        for exec in executives:
            exec_copy = exec.copy()
            original_name = exec.get('name', '').strip()
            original_lower = original_name.lower()

            if original_lower in name_corrections:
                exec_copy['name'] = name_corrections[original_lower]
                logger.debug(f"Corrected '{original_name}' to '{exec_copy['name']}'")

            corrected_executives.append(exec_copy)

        return corrected_executives

    except Exception as e:
        logger.warning(f"AI executive name verification failed: {e}")
        return executives  # Return original on error



def build_leadership_section(
    institution_data: Dict[str, Any],
    sec_parsed: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build leadership and compensation section from SEC proxy (DEF 14A).

    Includes:
    - CEO and top executives
    - Compensation details
    - Recent leadership changes
    """
    sec_data = institution_data.get('sec', {})

    if not sec_parsed:
        sec_parsed = sec_data.get('parsed', {})

    proxy_data = sec_parsed.get('proxy', {}) if sec_parsed else {}
    executives = proxy_data.get('executive_compensation', [])
    board = proxy_data.get('board_composition', [])

    # Get institution name for AI verification
    institution_name = institution_data.get('institution', {}).get('name', '')

    # Verify executive names with AI if any appear incomplete (single word only)
    if executives and institution_name:
        executives = _verify_executive_names_with_ai(executives, institution_name)

    # Find CEO
    ceo = None
    for exec in executives:
        title = (exec.get('title') or '').lower()
        if 'chief executive' in title or 'ceo' in title or 'president' in title:
            ceo = exec
            break

    if not ceo and executives:
        ceo = executives[0]

    # Format top 5 executives (excluding CEO who is shown separately)
    # Dedupe by name (case-insensitive)
    top_executives = []
    seen_names = set()
    ceo_name = ceo.get('name', '').lower() if ceo else ''
    if ceo_name:
        seen_names.add(ceo_name)  # Mark CEO as seen to skip duplicates

    for exec in executives:
        exec_name = exec.get('name', 'Unknown')
        exec_name_lower = exec_name.lower()

        # Skip the CEO - they're shown separately in the CEO profile section
        # Skip duplicates
        if exec_name_lower in seen_names:
            continue
        seen_names.add(exec_name_lower)

        top_executives.append({
            'name': exec_name,
            'title': exec.get('title', ''),
            'salary': _format_currency(exec.get('salary')),
            'bonus': _format_currency(exec.get('bonus')),
            'stock_awards': _format_currency(exec.get('stock_awards')),
            'total': _format_currency(exec.get('total', 0))
        })
        if len(top_executives) >= 5:  # Limit to top 5 non-CEO executives
            break

    return {
        'ceo': {
            'name': ceo.get('name', '--') if ceo else '--',
            'title': ceo.get('title', 'Chief Executive Officer') if ceo else 'CEO',
            'total_compensation': _format_currency(ceo.get('total', 0)) if ceo else '--'
        },
        'top_executives': top_executives,
        'board_size': len(board),
        'board_members': board[:10],
        'has_data': bool(ceo or executives)
    }


