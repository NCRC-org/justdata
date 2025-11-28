"""
Excel report builder module for creating Excel reports from data.
Shared across BranchSeeker, BizSight, and LendSight.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any
import os
from openpyxl import load_workbook


def save_excel_report(report_data: Dict[str, pd.DataFrame], output_path: str, sheet_names: Dict[str, str] = None):
    """
    Save the report data to an Excel file with multiple sheets.
    
    Args:
        report_data: Dictionary containing dataframes for different report sections
        output_path: Path where the Excel file should be saved
        sheet_names: Optional custom sheet names mapping
    """
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Default sheet names
    default_sheet_names = {
        'summary': 'Summary',
        'by_entity': 'By Entity',
        'by_location': 'By Location',
        'trends': 'Trends',
        'raw_data': 'Raw Data'
    }
    
    # Use custom sheet names if provided
    if sheet_names:
        default_sheet_names.update(sheet_names)
    
    # Create Excel writer
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        
        # Write each dataframe to a separate sheet
        for key, df in report_data.items():
            if isinstance(df, pd.DataFrame) and not df.empty:
                sheet_name = default_sheet_names.get(key, key.replace('_', ' ').title())
                df.to_excel(writer, sheet_name=sheet_name[:31], index=False)  # Excel sheet name limit is 31 chars
        
        # Auto-adjust column widths
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width

