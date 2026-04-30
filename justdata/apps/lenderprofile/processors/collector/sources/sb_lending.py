"""Small business lending (CRA) data fetcher."""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

def _get_sb_lending_data(collector, lei: str, fdic_cert: str, institution_name: str) -> Dict[str, Any]:
    """
    Get CRA small business lending data for the institution.

    Args:
        lei: Legal Entity Identifier
        fdic_cert: FDIC Certificate Number
        institution_name: Institution name

    Returns:
        SB lending data with yearly volumes, national comparison, and state breakdown
    """
    try:
        sb_data = collector.cra_client.get_sb_lending_summary(
            lei=lei,
            fdic_cert=fdic_cert,
            institution_name=institution_name
        )
        if sb_data.get('has_data'):
            logger.info(f"Collected CRA SB lending data: {len(sb_data.get('yearly_lending', {}).get('years', []))} years")
        return sb_data
    except Exception as e:
        logger.error(f"Error getting CRA SB lending data: {e}")
        return {'has_data': False, 'error': str(e)}

