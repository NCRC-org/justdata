"""Mergermeter Excel utility helpers."""
import logging
from typing import Any, Dict, Optional

import pandas as pd

from justdata.apps.mergermeter.config import PROJECT_ID
from justdata.shared.utils.bigquery_client import execute_query, get_bigquery_client

logger = logging.getLogger(__name__)


def _get_cbsa_name_from_code(cbsa_code: str, cbsa_name_cache: Dict[str, str] = None) -> str:
    """Look up CBSA name from code, using cache if provided."""
    if cbsa_name_cache is None:
        cbsa_name_cache = {}
    
    cbsa_code_str = str(cbsa_code).strip()
    
    # Check cache first
    if cbsa_code_str in cbsa_name_cache:
        return cbsa_name_cache[cbsa_code_str]
    
    # If code is empty or invalid, return fallback
    if not cbsa_code_str or cbsa_code_str.lower() in ['nan', 'none', '']:
        return f"CBSA {cbsa_code_str}" if cbsa_code_str else "Non-MSA"
    
    # Try to look up from BigQuery
    try:
        client = get_bigquery_client(PROJECT_ID, app_name='MERGERMETER')
        query = f"""
        SELECT DISTINCT cbsa as cbsa_name
        FROM `{PROJECT_ID}.shared.cbsa_to_county`
        WHERE CAST(cbsa_code AS STRING) = '{cbsa_code_str}'
        LIMIT 1
        """
        results = execute_query(client, query)
        if results and len(results) > 0:
            cbsa_name = str(results[0].get('cbsa_name', '')).strip()
            if cbsa_name and cbsa_name.lower() not in ['nan', 'none', '']:
                cbsa_name_cache[cbsa_code_str] = cbsa_name
                return cbsa_name
    except Exception as e:
        print(f"    Warning: Could not look up CBSA name for {cbsa_code_str}: {e}")
    
    # Fallback
    if cbsa_code_str == '99999' or cbsa_code_str == '':
        return "Non-MSA"
    return f"CBSA {cbsa_code_str}"


def _transform_mortgage_goals_data(mortgage_goals_data: Optional[Dict]) -> Optional[Dict]:
    """
    Transform mortgage_goals_data from the query format to the expected Excel format.

    Input format (from app.py):
    {
        'home_purchase': DataFrame([{state_name, total_loans, lmict_loans, ...}]),
        'refinance': DataFrame([...]),
        'home_improvement': DataFrame([...])
    }

    Output format (expected by merger_excel_generator):
    {
        'by_state': {
            'Illinois': {
                'home_purchase': {'Loans': 100, '~LMICT': 50, ...},
                'refinance': {...},
                'home_improvement': {...}
            },
            ...
        },
        'grand_total': {
            'home_purchase': {'Loans': 1000, ...},
            'refinance': {...},
            'home_improvement': {...}
        }
    }
    """
    if not mortgage_goals_data:
        return None

    # Column mapping from DataFrame columns to expected metric names
    column_to_metric = {
        'total_loans': 'Loans',
        'lmict_loans': '~LMICT',
        'lmib_loans': '~LMIB',
        'lmib_amount': 'LMIB$',
        'mmct_loans': '~MMCT',
        'minb_loans': '~MINB',
        'asian_loans': '~Asian',
        'black_loans': '~Black',
        'native_american_loans': '~Native American',
        'hopi_loans': '~HoPI',
        'hispanic_loans': '~Hispanic'
    }

    # Loan type mapping
    loan_type_map = {
        'home_purchase': 'home_purchase',
        'refinance': 'refinance',
        'home_improvement': 'home_improvement',
        'home_equity': 'home_equity'  # Keep home_equity as home_equity (codes 2+4)
    }

    by_state = {}
    grand_total = {}

    for loan_type, df in mortgage_goals_data.items():
        mapped_loan_type = loan_type_map.get(loan_type, loan_type)

        if df is None or (hasattr(df, 'empty') and df.empty):
            continue

        if not isinstance(df, pd.DataFrame):
            continue

        # Calculate grand totals for this loan type
        loan_type_totals = {}
        for col, metric in column_to_metric.items():
            if col in df.columns:
                loan_type_totals[metric] = int(df[col].sum()) if pd.notna(df[col].sum()) else 0

        if loan_type_totals:
            grand_total[mapped_loan_type] = loan_type_totals

        # Process each state
        if 'state_name' in df.columns:
            for _, row in df.iterrows():
                state_name = row.get('state_name', '')
                if not state_name or pd.isna(state_name):
                    continue

                if state_name not in by_state:
                    by_state[state_name] = {}

                state_metrics = {}
                for col, metric in column_to_metric.items():
                    if col in df.columns:
                        val = row.get(col, 0)
                        state_metrics[metric] = int(val) if pd.notna(val) else 0

                if state_metrics:
                    by_state[state_name][mapped_loan_type] = state_metrics

    if not by_state and not grand_total:
        return None

    return {
        'by_state': by_state,
        'grand_total': grand_total
    }


