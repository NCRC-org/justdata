"""Mortgage / small-business / branch metric computation helpers used by the worksheet builders."""
import logging
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def _compute_mortgage_pct_diff(metric: str, bank_totals: Dict, peer_totals: Dict) -> float:
    """Compute bank_pct - peer_pct for a mortgage percentage metric.

    Both bank and peer values are percentages (ratios of metric_loans / total_loans).
    Returns the difference as a decimal (e.g., 0.05 for 5 percentage points).
    """
    if not bank_totals or not peer_totals:
        return 0

    total_bank = bank_totals.get('total_loans', 0)
    total_peer = peer_totals.get('total_loans', 0)

    metric_key_map = {
        'LMICT%': 'lmict_loans', 'LMIB%': 'lmib_loans', 'MMCT%': 'mmct_loans',
        'MINB%': 'minb_loans', 'Asian%': 'asian_loans', 'Black%': 'black_loans',
        'Native American%': 'native_american_loans', 'HoPI%': 'hopi_loans',
        'Hispanic%': 'hispanic_loans',
    }
    key = metric_key_map.get(metric)
    if not key:
        return 0

    bank_pct = (bank_totals.get(key, 0) / total_bank) if total_bank > 0 else 0
    peer_pct = (peer_totals.get(key, 0) / total_peer) if total_peer > 0 else 0
    return bank_pct - peer_pct


def _compute_sb_ratio_diff(metric: str, bank_totals: Dict, peer_totals: Dict) -> float:
    """Compute (bank_metric/bank_sb_loans) - (peer_metric/peer_sb_loans) for SB ratio metrics."""
    if not bank_totals or not peer_totals:
        return 0

    bank_sb = bank_totals.get('sb_loans_total', 0)
    peer_sb = peer_totals.get('sb_loans_total', 0)

    if metric == '#LMICT':
        bank_val = bank_totals.get('lmict_count', 0)
        peer_val = peer_totals.get('lmict_count', 0)
    elif metric == 'Loans Rev Under $1m':
        bank_val = bank_totals.get('loans_rev_under_1m_count', 0)
        peer_val = peer_totals.get('loans_rev_under_1m_count', 0)
    else:
        return 0

    bank_ratio = (bank_val / bank_sb) if bank_sb > 0 else 0
    peer_ratio = (peer_val / peer_sb) if peer_sb > 0 else 0
    return bank_ratio - peer_ratio


def _compute_sb_avg_diff(metric: str, bank_totals: Dict, peer_totals: Dict) -> float:
    """Compute bank_avg - peer_avg for SB average metrics."""
    if not bank_totals or not peer_totals:
        return 0

    if metric == 'Avg SB LMICT Loan Amount':
        bank_val = bank_totals.get('avg_sb_lmict_loan_amount', 0)
        peer_val = peer_totals.get('avg_sb_lmict_loan_amount', 0)
    elif metric == 'Avg Loan Amt for <$1M GAR SB':
        bank_val = bank_totals.get('avg_loan_amt_rum_sb', 0)
        peer_val = peer_totals.get('avg_loan_amt_rum_sb', 0)
    else:
        return 0

    return bank_val - peer_val


def _compute_branch_pct_diff(subj_count, subj_total, other_count, other_total) -> float:
    """Compute (subject_count/subject_total) - (other_count/other_total) for branch metrics."""
    subj_pct = (subj_count / subj_total) if subj_total > 0 else 0
    other_pct = (other_count / other_total) if other_total > 0 else 0
    return subj_pct - other_pct


def _get_cbsa_name(group_data: pd.DataFrame) -> str:
    """Extract CBSA name from group data."""
    if 'cbsa_name' in group_data.columns and not group_data.empty:
        cbsa_name = group_data['cbsa_name'].iloc[0]
        if cbsa_name and str(cbsa_name).lower() not in ['nan', 'none', '']:
            return str(cbsa_name).strip()
    if 'cbsa_code' in group_data.columns and not group_data.empty:
        code = str(group_data['cbsa_code'].iloc[0])
        # CBSA 99999 = non-metro/rural — preserve state-specific name if available
        if code.startswith('99999_'):
            from justdata.shared.reporting.merger_data_transformer import STATE_FIPS_TO_NAME
            state_fips = code.split('_')[1] if '_' in code else ''
            state_name = STATE_FIPS_TO_NAME.get(state_fips, '')
            return f"{state_name} Non-MSA" if state_name else "Non-Metro Area"
        if code == '99999':
            return "Non-Metro Area"
        return f"CBSA {code}"
    return "Unknown CBSA"


def _calculate_mortgage_grand_total(df: pd.DataFrame) -> Dict:
    """Calculate grand totals for mortgage data."""
    if df is None or df.empty:
        return {}

    return {
        'total_loans': df['total_loans'].sum() if 'total_loans' in df.columns else 0,
        'lmict_loans': df['lmict_loans'].sum() if 'lmict_loans' in df.columns else 0,
        'lmib_loans': df['lmib_loans'].sum() if 'lmib_loans' in df.columns else 0,
        'lmib_amount': df['lmib_amount'].sum() if 'lmib_amount' in df.columns else 0,
        'mmct_loans': df['mmct_loans'].sum() if 'mmct_loans' in df.columns else 0,
        'minb_loans': df['minb_loans'].sum() if 'minb_loans' in df.columns else 0,
        'asian_loans': df['asian_loans'].sum() if 'asian_loans' in df.columns else 0,
        'black_loans': df['black_loans'].sum() if 'black_loans' in df.columns else 0,
        'native_american_loans': df['native_american_loans'].sum() if 'native_american_loans' in df.columns else 0,
        'hopi_loans': df['hopi_loans'].sum() if 'hopi_loans' in df.columns else 0,
        'hispanic_loans': df['hispanic_loans'].sum() if 'hispanic_loans' in df.columns else 0,
    }


def _calculate_mortgage_cbsa_total(group_data: pd.DataFrame) -> Dict:
    """Calculate totals for a single CBSA in mortgage data."""
    return _calculate_mortgage_grand_total(group_data)


def _write_mortgage_metric_new_format(ws, row: int, col: int, metric: str, totals: Dict):
    """Write a mortgage metric value to cell with proper number formatting."""
    if not totals:
        return

    total_loans = totals.get('total_loans', 0)
    cell = ws.cell(row, col)

    if metric == 'Loans':
        cell.value = int(total_loans)
        cell.number_format = '#,##0'  # Thousands with commas, no decimals
    elif metric == 'LMICT%':
        pct = (totals.get('lmict_loans', 0) / total_loans) if total_loans > 0 else 0
        cell.value = pct
        cell.number_format = '0.00%'  # Percentage with 2 decimals
    elif metric == 'LMIB%':
        pct = (totals.get('lmib_loans', 0) / total_loans) if total_loans > 0 else 0
        cell.value = pct
        cell.number_format = '0.00%'
    elif metric == 'LMIB$':
        cell.value = int(totals.get('lmib_amount', 0))
        cell.number_format = '$#,##0'  # Dollar format
    elif metric == 'MMCT%':
        pct = (totals.get('mmct_loans', 0) / total_loans) if total_loans > 0 else 0
        cell.value = pct
        cell.number_format = '0.00%'
    elif metric == 'MINB%':
        pct = (totals.get('minb_loans', 0) / total_loans) if total_loans > 0 else 0
        cell.value = pct
        cell.number_format = '0.00%'
    elif metric == 'Asian%':
        pct = (totals.get('asian_loans', 0) / total_loans) if total_loans > 0 else 0
        cell.value = pct
        cell.number_format = '0.00%'
    elif metric == 'Black%':
        pct = (totals.get('black_loans', 0) / total_loans) if total_loans > 0 else 0
        cell.value = pct
        cell.number_format = '0.00%'
    elif metric == 'Native American%':
        pct = (totals.get('native_american_loans', 0) / total_loans) if total_loans > 0 else 0
        cell.value = pct
        cell.number_format = '0.00%'
    elif metric == 'HoPI%':
        pct = (totals.get('hopi_loans', 0) / total_loans) if total_loans > 0 else 0
        cell.value = pct
        cell.number_format = '0.00%'
    elif metric == 'Hispanic%':
        pct = (totals.get('hispanic_loans', 0) / total_loans) if total_loans > 0 else 0
        cell.value = pct
        cell.number_format = '0.00%'


def _calculate_sb_grand_total(df: pd.DataFrame, sb_col: str, lmict_col: str, rev_col: str) -> Dict:
    """Calculate grand totals for SB data."""
    if df is None or df.empty:
        return {}

    sb_total = df[sb_col].sum() if sb_col in df.columns else 0
    lmict_total = df[lmict_col].sum() if lmict_col in df.columns else 0
    rev_total = df[rev_col].sum() if rev_col in df.columns else 0

    # Calculate averages
    avg_lmict = 0
    if lmict_total > 0:
        if 'lmict_loans_amount' in df.columns:
            avg_lmict = df['lmict_loans_amount'].sum() / lmict_total
        elif 'avg_sb_lmict_loan_amount' in df.columns:
            avg_lmict = (df[lmict_col] * df['avg_sb_lmict_loan_amount'].fillna(0)).sum() / lmict_total

    avg_rev = 0
    if rev_total > 0:
        if 'amount_rev_under_1m' in df.columns:
            avg_rev = df['amount_rev_under_1m'].sum() / rev_total
        elif 'avg_loan_amt_rum_sb' in df.columns:
            avg_rev = (df[rev_col] * df['avg_loan_amt_rum_sb'].fillna(0)).sum() / rev_total

    return {
        'sb_loans_total': sb_total,
        'lmict_count': lmict_total,
        'loans_rev_under_1m_count': rev_total,
        'avg_sb_lmict_loan_amount': avg_lmict,
        'avg_loan_amt_rum_sb': avg_rev,
    }


def _calculate_sb_cbsa_total(group_data: pd.DataFrame, sb_col: str, lmict_col: str, rev_col: str) -> Dict:
    """Calculate totals for a single CBSA in SB data."""
    return _calculate_sb_grand_total(group_data, sb_col, lmict_col, rev_col)


def _write_sb_metric_new_format(ws, row: int, col: int, metric: str, totals: Dict):
    """Write a SB metric value to cell with proper number formatting."""
    if not totals:
        return

    cell = ws.cell(row, col)

    if metric == 'SB Loans':
        cell.value = int(totals.get('sb_loans_total', 0))
        cell.number_format = '#,##0'  # Thousands with commas
    elif metric == '#LMICT':
        cell.value = int(totals.get('lmict_count', 0))
        cell.number_format = '#,##0'  # Thousands with commas
    elif metric == 'Avg SB LMICT Loan Amount':
        cell.value = float(totals.get('avg_sb_lmict_loan_amount', 0))
        cell.number_format = '$#,##0'  # Dollar format
    elif metric == 'Loans Rev Under $1m':
        cell.value = int(totals.get('loans_rev_under_1m_count', 0))
        cell.number_format = '#,##0'  # Thousands with commas
    elif metric == 'Avg Loan Amt for <$1M GAR SB':
        cell.value = float(totals.get('avg_loan_amt_rum_sb', 0))
        cell.number_format = '$#,##0'  # Dollar format


# Keep old function signatures for backward compatibility
def _write_mortgage_metric(ws, row: int, col: int, metric: str, totals: Dict):
    """Write a mortgage metric value to cell - backward compatible version."""
    _write_mortgage_metric_new_format(ws, row, col, metric, totals)


def _write_sb_metric(ws, row: int, col: int, metric: str, totals: Dict):
    """Write a SB metric value to cell - backward compatible version."""
    _write_sb_metric_new_format(ws, row, col, metric, totals)
