"""
Excel generator for MergerMeter analysis output.

This module provides the create_merger_excel function that generates
standardized Excel reports for bank merger analysis.
"""

from pathlib import Path
import pandas as pd
from typing import Dict, Optional, List
import logging
from collections import defaultdict
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

logger = logging.getLogger(__name__)

# NCRC brand colors
NCRC_BLUE = "034EA0"
HEADER_FILL = PatternFill(start_color=NCRC_BLUE, end_color=NCRC_BLUE, fill_type="solid")
HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
BORDER_THIN = Border(
    left=Side(style='thin'),
    right=Side(style='thin'),
    top=Side(style='thin'),
    bottom=Side(style='thin')
)


def create_merger_excel(
    output_path: Path,
    bank_a_name: str,
    bank_b_name: str,
    assessment_areas_data: Optional[Dict] = None,
    mortgage_goals_data: Optional[Dict] = None,
    sb_goals_data: Optional[pd.DataFrame] = None,
    bank_a_mortgage_data: Optional[pd.DataFrame] = None,
    bank_b_mortgage_data: Optional[pd.DataFrame] = None,
    bank_a_mortgage_peer_data: Optional[pd.DataFrame] = None,
    bank_b_mortgage_peer_data: Optional[pd.DataFrame] = None,
    bank_a_sb_data: Optional[pd.DataFrame] = None,
    bank_b_sb_data: Optional[pd.DataFrame] = None,
    bank_a_sb_peer_data: Optional[pd.DataFrame] = None,
    bank_b_sb_peer_data: Optional[pd.DataFrame] = None,
    bank_a_branch_data: Optional[pd.DataFrame] = None,
    bank_b_branch_data: Optional[pd.DataFrame] = None,
    years_hmda: Optional[List[int]] = None,
    years_sb: Optional[List[int]] = None,
    bank_a_lei: str = "",
    bank_b_lei: str = "",
    bank_a_rssd: str = "",
    bank_b_rssd: str = "",
    bank_a_sb_id: str = "",
    bank_b_sb_id: str = "",
    loan_purpose: str = "",
    action_taken: str = "",
    occupancy_type: str = "",
    total_units: str = "",
    construction_method: str = "",
    not_reverse: str = ""
):
    """
    Create Excel workbook with merger analysis data.

    Args:
        output_path: Path to save the Excel file
        bank_a_name: Name of the acquirer bank
        bank_b_name: Name of the target bank
        assessment_areas_data: Dict with 'acquirer' and 'target' keys containing counties
        mortgage_goals_data: Optional mortgage goals data
        sb_goals_data: Optional small business goals data
        bank_a_mortgage_data: Transformed mortgage data for acquirer
        bank_b_mortgage_data: Transformed mortgage data for target
        bank_a_mortgage_peer_data: Peer mortgage data for acquirer (if separate)
        bank_b_mortgage_peer_data: Peer mortgage data for target (if separate)
        bank_a_sb_data: Transformed SB data for acquirer
        bank_b_sb_data: Transformed SB data for target
        bank_a_sb_peer_data: Peer SB data for acquirer (if separate)
        bank_b_sb_peer_data: Peer SB data for target (if separate)
        bank_a_branch_data: Transformed branch data for acquirer
        bank_b_branch_data: Transformed branch data for target
        years_hmda: List of HMDA years included
        years_sb: List of SB years included
        bank_a_lei: LEI for acquirer
        bank_b_lei: LEI for target
        bank_a_rssd: RSSD ID for acquirer
        bank_b_rssd: RSSD ID for target
        bank_a_sb_id: SB ID for acquirer
        bank_b_sb_id: SB ID for target
        loan_purpose: HMDA loan purpose filter
        action_taken: HMDA action taken filter
        occupancy_type: HMDA occupancy type filter
        total_units: HMDA total units filter
        construction_method: HMDA construction method filter
        not_reverse: HMDA reverse mortgage filter
    """
    logger.info(f"Creating merger Excel report: {output_path}")

    # Create workbook
    wb = Workbook()

    # Remove default sheet
    if "Sheet" in wb.sheetnames:
        del wb["Sheet"]

    # Create Cover/Summary sheet
    _create_summary_sheet(
        wb, bank_a_name, bank_b_name,
        years_hmda, years_sb,
        bank_a_lei, bank_b_lei,
        bank_a_rssd, bank_b_rssd,
        loan_purpose, action_taken
    )

    # Create Assessment Areas sheet
    if assessment_areas_data:
        _create_assessment_areas_sheet(
            wb, bank_a_name, bank_b_name, assessment_areas_data
        )

    # Create Mortgage sheets
    if bank_a_mortgage_data is not None and not bank_a_mortgage_data.empty:
        _create_mortgage_sheet(
            wb, bank_a_name, bank_a_mortgage_data, bank_a_mortgage_peer_data
        )

    if bank_b_mortgage_data is not None and not bank_b_mortgage_data.empty:
        _create_mortgage_sheet(
            wb, bank_b_name, bank_b_mortgage_data, bank_b_mortgage_peer_data
        )

    # Create Small Business sheets
    if bank_a_sb_data is not None and not bank_a_sb_data.empty:
        _create_sb_sheet(
            wb, bank_a_name, bank_a_sb_data, bank_a_sb_peer_data
        )

    if bank_b_sb_data is not None and not bank_b_sb_data.empty:
        _create_sb_sheet(
            wb, bank_b_name, bank_b_sb_data, bank_b_sb_peer_data
        )

    # Create Branch sheets
    if bank_a_branch_data is not None and not bank_a_branch_data.empty:
        _create_branch_sheet(wb, bank_a_name, bank_a_branch_data)

    if bank_b_branch_data is not None and not bank_b_branch_data.empty:
        _create_branch_sheet(wb, bank_b_name, bank_b_branch_data)

    # Save workbook
    wb.save(output_path)
    logger.info(f"Merger Excel report saved to: {output_path}")


def _create_summary_sheet(
    wb: Workbook,
    bank_a_name: str,
    bank_b_name: str,
    years_hmda: Optional[List[int]],
    years_sb: Optional[List[int]],
    bank_a_lei: str,
    bank_b_lei: str,
    bank_a_rssd: str,
    bank_b_rssd: str,
    loan_purpose: str,
    action_taken: str
):
    """Create summary/cover sheet with analysis metadata."""
    ws = wb.create_sheet("Summary", 0)

    # Title
    ws.merge_cells('A1:D1')
    ws['A1'] = f"Merger Analysis: {bank_a_name} acquiring {bank_b_name}"
    ws['A1'].font = Font(bold=True, size=14)
    ws['A1'].alignment = Alignment(horizontal='center')

    # Metadata
    row = 3
    metadata = [
        ("Acquirer", bank_a_name),
        ("Target", bank_b_name),
        ("Acquirer LEI", bank_a_lei if bank_a_lei else "N/A"),
        ("Target LEI", bank_b_lei if bank_b_lei else "N/A"),
        ("Acquirer RSSD", bank_a_rssd if bank_a_rssd else "N/A"),
        ("Target RSSD", bank_b_rssd if bank_b_rssd else "N/A"),
        ("HMDA Years", ", ".join(map(str, years_hmda)) if years_hmda else "N/A"),
        ("SB Years", ", ".join(map(str, years_sb)) if years_sb else "N/A"),
        ("Loan Purpose", loan_purpose if loan_purpose else "All"),
        ("Action Taken", action_taken if action_taken else "All"),
    ]

    for label, value in metadata:
        ws.cell(row, 1, label).font = Font(bold=True)
        ws.cell(row, 2, value)
        row += 1

    # Adjust column widths
    ws.column_dimensions['A'].width = 20
    ws.column_dimensions['B'].width = 40


def _create_assessment_areas_sheet(
    wb: Workbook,
    bank_a_name: str,
    bank_b_name: str,
    assessment_areas_data: Dict
):
    """Create assessment areas sheet showing counties for each bank."""
    ws = wb.create_sheet("Assessment Areas")

    # Headers for Bank A
    ws['A1'] = f'{bank_a_name} Assessment Areas'
    ws['A1'].font = Font(bold=True, size=12)

    headers = ['State', 'CBSA Name', 'CBSA Code', 'County', 'GEOID5']
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(2, col_idx)
        cell.value = header
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.border = BORDER_THIN

    # Headers for Bank B (offset by 6 columns)
    ws['G1'] = f'{bank_b_name} Assessment Areas'
    ws['G1'].font = Font(bold=True, size=12)

    for col_idx, header in enumerate(headers, 7):
        cell = ws.cell(2, col_idx)
        cell.value = header
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.border = BORDER_THIN

    # Get counties
    acquirer_counties = assessment_areas_data.get('acquirer', {}).get('counties', [])
    target_counties = assessment_areas_data.get('target', {}).get('counties', [])

    # Write Bank A counties
    row = 3
    for county in acquirer_counties:
        ws.cell(row, 1, county.get('state_name', ''))
        ws.cell(row, 2, county.get('cbsa_name', ''))
        ws.cell(row, 3, str(county.get('cbsa_code', '')))
        county_name = county.get('county_name', '')
        state_name = county.get('state_name', '')
        ws.cell(row, 4, f"{county_name}, {state_name}" if county_name else '')
        ws.cell(row, 5, str(county.get('geoid5', '')))
        row += 1

    # Write Bank B counties
    row = 3
    for county in target_counties:
        ws.cell(row, 7, county.get('state_name', ''))
        ws.cell(row, 8, county.get('cbsa_name', ''))
        ws.cell(row, 9, str(county.get('cbsa_code', '')))
        county_name = county.get('county_name', '')
        state_name = county.get('state_name', '')
        ws.cell(row, 10, f"{county_name}, {state_name}" if county_name else '')
        ws.cell(row, 11, str(county.get('geoid5', '')))
        row += 1

    # Adjust column widths
    for col in range(1, 12):
        ws.column_dimensions[get_column_letter(col)].width = 20

    logger.info(f"Created Assessment Areas sheet: {len(acquirer_counties)} acquirer, {len(target_counties)} target counties")


def _create_mortgage_sheet(
    wb: Workbook,
    bank_name: str,
    subject_data: pd.DataFrame,
    peer_data: Optional[pd.DataFrame] = None
):
    """Create mortgage data sheet with HMDA metrics."""
    sheet_name = f"{bank_name[:25]} Mortgage"
    ws = wb.create_sheet(sheet_name)

    # Headers
    headers = ['CBSA Name', 'Metric', 'Subject Bank', 'Peer/Other', 'Difference']
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(1, col_idx)
        cell.value = header
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.border = BORDER_THIN
        cell.alignment = Alignment(horizontal='center', vertical='center')

    if subject_data is None or subject_data.empty:
        logger.warning(f"No mortgage data for {bank_name}")
        return

    # Metrics
    metrics = [
        'Loans', 'LMICT%', 'LMIB%', 'LMIB$', 'MMCT%',
        'MINB%', 'Asian%', 'Black%', 'Native American%', 'HoPI%', 'Hispanic%'
    ]

    # Calculate Grand Total
    grand_total = _calculate_mortgage_grand_total(subject_data)
    peer_grand_total = _calculate_mortgage_grand_total(peer_data) if peer_data is not None else None

    # Write Grand Total section
    row = 2
    for metric in metrics:
        ws.cell(row, 1, 'Grand Total').font = Font(bold=True)
        ws.cell(row, 2, metric)
        _write_mortgage_metric(ws, row, 3, metric, grand_total)
        if peer_grand_total:
            _write_mortgage_metric(ws, row, 4, metric, peer_grand_total)
        if metric.endswith('%') and metric != 'LMIB$':
            ws.cell(row, 5, f'=IFERROR(C{row}-D{row},0)')
            ws.cell(row, 5).number_format = '0.00%'
        row += 1

    row += 1  # Blank row

    # Write CBSA-level data
    if 'cbsa_code' in subject_data.columns:
        grouped = subject_data.groupby('cbsa_code')
        for cbsa_code, group_data in grouped:
            cbsa_name = _get_cbsa_name(group_data)
            cbsa_total = _calculate_mortgage_cbsa_total(group_data)
            peer_cbsa_total = None
            if peer_data is not None and 'cbsa_code' in peer_data.columns:
                peer_group = peer_data[peer_data['cbsa_code'] == cbsa_code]
                if not peer_group.empty:
                    peer_cbsa_total = _calculate_mortgage_cbsa_total(peer_group)

            for metric in metrics:
                ws.cell(row, 1, cbsa_name)
                ws.cell(row, 2, metric)
                _write_mortgage_metric(ws, row, 3, metric, cbsa_total)
                if peer_cbsa_total:
                    _write_mortgage_metric(ws, row, 4, metric, peer_cbsa_total)
                if metric.endswith('%') and metric != 'LMIB$':
                    ws.cell(row, 5, f'=IFERROR(C{row}-D{row},0)')
                    ws.cell(row, 5).number_format = '0.00%'
                row += 1

    # Adjust column widths
    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 20
    for col in ['C', 'D', 'E']:
        ws.column_dimensions[col].width = 15

    logger.info(f"Created mortgage sheet for {bank_name}: {row - 2} rows")


def _create_sb_sheet(
    wb: Workbook,
    bank_name: str,
    subject_data: pd.DataFrame,
    peer_data: Optional[pd.DataFrame] = None
):
    """Create small business lending data sheet."""
    sheet_name = f"{bank_name[:25]} SB Lending"
    ws = wb.create_sheet(sheet_name)

    # Headers
    headers = ['CBSA Name', 'Metric', 'Subject Bank', 'Peer/Other', 'Difference']
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(1, col_idx)
        cell.value = header
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.border = BORDER_THIN
        cell.alignment = Alignment(horizontal='center', vertical='center')

    if subject_data is None or subject_data.empty:
        logger.warning(f"No SB data for {bank_name}")
        return

    # Metrics
    metrics = ['SB Loans', '#LMICT', 'Avg SB LMICT Loan Amount', 'Loans Rev Under $1m', 'Avg Loan Amt for <$1M GAR SB']

    # Determine column names
    sb_loans_col = 'sb_loans_total' if 'sb_loans_total' in subject_data.columns else 'sb_loans_count'
    lmict_col = 'lmict_count' if 'lmict_count' in subject_data.columns else 'lmict_loans_count'
    rev_col = 'loans_rev_under_1m_count' if 'loans_rev_under_1m_count' in subject_data.columns else 'loans_rev_under_1m'

    # Calculate Grand Total
    grand_total = _calculate_sb_grand_total(subject_data, sb_loans_col, lmict_col, rev_col)
    peer_grand_total = None
    if peer_data is not None and not peer_data.empty:
        peer_sb_col = 'sb_loans_total' if 'sb_loans_total' in peer_data.columns else 'sb_loans_count'
        peer_lmict_col = 'lmict_count' if 'lmict_count' in peer_data.columns else 'lmict_loans_count'
        peer_rev_col = 'loans_rev_under_1m_count' if 'loans_rev_under_1m_count' in peer_data.columns else 'loans_rev_under_1m'
        peer_grand_total = _calculate_sb_grand_total(peer_data, peer_sb_col, peer_lmict_col, peer_rev_col)

    # Write Grand Total section
    row = 2
    for metric in metrics:
        ws.cell(row, 1, 'Grand Total').font = Font(bold=True)
        ws.cell(row, 2, metric)
        _write_sb_metric(ws, row, 3, metric, grand_total)
        if peer_grand_total:
            _write_sb_metric(ws, row, 4, metric, peer_grand_total)
        row += 1

    row += 1  # Blank row

    # Write CBSA-level data
    if 'cbsa_code' in subject_data.columns:
        grouped = subject_data.groupby('cbsa_code')
        for cbsa_code, group_data in grouped:
            cbsa_name = _get_cbsa_name(group_data)
            cbsa_total = _calculate_sb_cbsa_total(group_data, sb_loans_col, lmict_col, rev_col)
            peer_cbsa_total = None
            if peer_data is not None and 'cbsa_code' in peer_data.columns:
                peer_group = peer_data[peer_data['cbsa_code'] == cbsa_code]
                if not peer_group.empty:
                    peer_sb_col = 'sb_loans_total' if 'sb_loans_total' in peer_group.columns else 'sb_loans_count'
                    peer_lmict_col = 'lmict_count' if 'lmict_count' in peer_group.columns else 'lmict_loans_count'
                    peer_rev_col = 'loans_rev_under_1m_count' if 'loans_rev_under_1m_count' in peer_group.columns else 'loans_rev_under_1m'
                    peer_cbsa_total = _calculate_sb_cbsa_total(peer_group, peer_sb_col, peer_lmict_col, peer_rev_col)

            for metric in metrics:
                ws.cell(row, 1, cbsa_name)
                ws.cell(row, 2, metric)
                _write_sb_metric(ws, row, 3, metric, cbsa_total)
                if peer_cbsa_total:
                    _write_sb_metric(ws, row, 4, metric, peer_cbsa_total)
                row += 1

    # Adjust column widths
    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 25
    for col in ['C', 'D', 'E']:
        ws.column_dimensions[col].width = 15

    logger.info(f"Created SB sheet for {bank_name}: {row - 2} rows")


def _create_branch_sheet(wb: Workbook, bank_name: str, branch_data: pd.DataFrame):
    """Create branch data sheet."""
    sheet_name = f"{bank_name[:25]} Branches"
    ws = wb.create_sheet(sheet_name)

    # Headers
    headers = ['CBSA Name', 'Metric', 'Subject Bank', 'Other/Market', 'Difference']
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(1, col_idx)
        cell.value = header
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.border = BORDER_THIN
        cell.alignment = Alignment(horizontal='center', vertical='center')

    if branch_data is None or branch_data.empty:
        logger.warning(f"No branch data for {bank_name}")
        return

    metrics = ['Branches', 'LMICT', 'MMCT']

    # Determine column names
    total_col = 'total_branches' if 'total_branches' in branch_data.columns else 'subject_total_branches'
    lmict_col = 'branches_in_lmict' if 'branches_in_lmict' in branch_data.columns else None
    mmct_col = 'branches_in_mmct' if 'branches_in_mmct' in branch_data.columns else None
    other_total_col = 'other_total_branches' if 'other_total_branches' in branch_data.columns else 'market_total_branches'

    # Calculate Grand Total
    grand_total_subject = branch_data[total_col].sum() if total_col in branch_data.columns else 0
    grand_total_other = branch_data[other_total_col].sum() if other_total_col in branch_data.columns else 0
    grand_lmict = branch_data[lmict_col].sum() if lmict_col and lmict_col in branch_data.columns else 0
    grand_mmct = branch_data[mmct_col].sum() if mmct_col and mmct_col in branch_data.columns else 0
    other_lmict_col = 'other_branches_in_lmict' if 'other_branches_in_lmict' in branch_data.columns else 'market_branches_in_lmict'
    other_mmct_col = 'other_branches_in_mmct' if 'other_branches_in_mmct' in branch_data.columns else 'market_branches_in_mmct'
    grand_other_lmict = branch_data[other_lmict_col].sum() if other_lmict_col in branch_data.columns else 0
    grand_other_mmct = branch_data[other_mmct_col].sum() if other_mmct_col in branch_data.columns else 0

    # Write Grand Total section
    row = 2
    for metric in metrics:
        ws.cell(row, 1, 'Grand Total').font = Font(bold=True)
        ws.cell(row, 2, metric)

        if metric == 'Branches':
            ws.cell(row, 3, int(grand_total_subject)).number_format = '#,##0'
            ws.cell(row, 4, int(grand_total_other)).number_format = '#,##0'
        elif metric == 'LMICT':
            ws.cell(row, 3, int(grand_lmict)).number_format = '#,##0'
            ws.cell(row, 4, int(grand_other_lmict)).number_format = '#,##0'
            branches_row = row - 1
            ws.cell(row, 5, f'=IFERROR((C{row}/C{branches_row})-(D{row}/D{branches_row}),0)')
            ws.cell(row, 5).number_format = '0.00%'
        elif metric == 'MMCT':
            ws.cell(row, 3, int(grand_mmct)).number_format = '#,##0'
            ws.cell(row, 4, int(grand_other_mmct)).number_format = '#,##0'
            branches_row = row - 2
            ws.cell(row, 5, f'=IFERROR((C{row}/C{branches_row})-(D{row}/D{branches_row}),0)')
            ws.cell(row, 5).number_format = '0.00%'
        row += 1

    row += 1  # Blank row

    # Write CBSA-level data
    if 'cbsa_code' in branch_data.columns:
        grouped = branch_data.groupby('cbsa_code')
        for cbsa_code, group_data in grouped:
            cbsa_name = _get_cbsa_name(group_data)
            subject_total = group_data[total_col].sum() if total_col in group_data.columns else 0
            other_total = group_data[other_total_col].sum() if other_total_col in group_data.columns else 0
            subject_lmict = group_data[lmict_col].sum() if lmict_col and lmict_col in group_data.columns else 0
            subject_mmct = group_data[mmct_col].sum() if mmct_col and mmct_col in group_data.columns else 0
            other_lmict = group_data[other_lmict_col].sum() if other_lmict_col in group_data.columns else 0
            other_mmct = group_data[other_mmct_col].sum() if other_mmct_col in group_data.columns else 0

            for metric in metrics:
                ws.cell(row, 1, cbsa_name)
                ws.cell(row, 2, metric)

                if metric == 'Branches':
                    ws.cell(row, 3, int(subject_total)).number_format = '#,##0'
                    ws.cell(row, 4, int(other_total)).number_format = '#,##0'
                elif metric == 'LMICT':
                    ws.cell(row, 3, int(subject_lmict)).number_format = '#,##0'
                    ws.cell(row, 4, int(other_lmict)).number_format = '#,##0'
                    branches_row = row - 1
                    ws.cell(row, 5, f'=IFERROR((C{row}/C{branches_row})-(D{row}/D{branches_row}),0)')
                    ws.cell(row, 5).number_format = '0.00%'
                elif metric == 'MMCT':
                    ws.cell(row, 3, int(subject_mmct)).number_format = '#,##0'
                    ws.cell(row, 4, int(other_mmct)).number_format = '#,##0'
                    branches_row = row - 2
                    ws.cell(row, 5, f'=IFERROR((C{row}/C{branches_row})-(D{row}/D{branches_row}),0)')
                    ws.cell(row, 5).number_format = '0.00%'
                row += 1

    # Adjust column widths
    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 15
    for col in ['C', 'D', 'E']:
        ws.column_dimensions[col].width = 15

    logger.info(f"Created branch sheet for {bank_name}: {row - 2} rows")


# Helper functions

def _get_cbsa_name(group_data: pd.DataFrame) -> str:
    """Extract CBSA name from group data."""
    if 'cbsa_name' in group_data.columns and not group_data.empty:
        cbsa_name = group_data['cbsa_name'].iloc[0]
        if cbsa_name and str(cbsa_name).lower() not in ['nan', 'none', '']:
            return str(cbsa_name).strip()
    if 'cbsa_code' in group_data.columns and not group_data.empty:
        return f"CBSA {group_data['cbsa_code'].iloc[0]}"
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


def _write_mortgage_metric(ws, row: int, col: int, metric: str, totals: Dict):
    """Write a mortgage metric value to cell."""
    if not totals:
        return

    total_loans = totals.get('total_loans', 0)

    if metric == 'Loans':
        ws.cell(row, col, int(total_loans)).number_format = '#,##0'
    elif metric == 'LMICT%':
        pct = (totals.get('lmict_loans', 0) / total_loans) if total_loans > 0 else 0
        ws.cell(row, col, pct).number_format = '0.00%'
    elif metric == 'LMIB%':
        pct = (totals.get('lmib_loans', 0) / total_loans) if total_loans > 0 else 0
        ws.cell(row, col, pct).number_format = '0.00%'
    elif metric == 'LMIB$':
        ws.cell(row, col, float(totals.get('lmib_amount', 0))).number_format = '$#,##0'
    elif metric == 'MMCT%':
        pct = (totals.get('mmct_loans', 0) / total_loans) if total_loans > 0 else 0
        ws.cell(row, col, pct).number_format = '0.00%'
    elif metric == 'MINB%':
        pct = (totals.get('minb_loans', 0) / total_loans) if total_loans > 0 else 0
        ws.cell(row, col, pct).number_format = '0.00%'
    elif metric == 'Asian%':
        pct = (totals.get('asian_loans', 0) / total_loans) if total_loans > 0 else 0
        ws.cell(row, col, pct).number_format = '0.00%'
    elif metric == 'Black%':
        pct = (totals.get('black_loans', 0) / total_loans) if total_loans > 0 else 0
        ws.cell(row, col, pct).number_format = '0.00%'
    elif metric == 'Native American%':
        pct = (totals.get('native_american_loans', 0) / total_loans) if total_loans > 0 else 0
        ws.cell(row, col, pct).number_format = '0.00%'
    elif metric == 'HoPI%':
        pct = (totals.get('hopi_loans', 0) / total_loans) if total_loans > 0 else 0
        ws.cell(row, col, pct).number_format = '0.00%'
    elif metric == 'Hispanic%':
        pct = (totals.get('hispanic_loans', 0) / total_loans) if total_loans > 0 else 0
        ws.cell(row, col, pct).number_format = '0.00%'


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


def _write_sb_metric(ws, row: int, col: int, metric: str, totals: Dict):
    """Write a SB metric value to cell."""
    if not totals:
        return

    if metric == 'SB Loans':
        ws.cell(row, col, int(totals.get('sb_loans_total', 0))).number_format = '#,##0'
    elif metric == '#LMICT':
        ws.cell(row, col, int(totals.get('lmict_count', 0))).number_format = '#,##0'
    elif metric == 'Avg SB LMICT Loan Amount':
        ws.cell(row, col, float(totals.get('avg_sb_lmict_loan_amount', 0))).number_format = '#,##0'
    elif metric == 'Loans Rev Under $1m':
        ws.cell(row, col, int(totals.get('loans_rev_under_1m_count', 0))).number_format = '#,##0'
    elif metric == 'Avg Loan Amt for <$1M GAR SB':
        ws.cell(row, col, float(totals.get('avg_loan_amt_rum_sb', 0))).number_format = '#,##0'
