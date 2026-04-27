"""Coordinator for the all-lenders variant of the area report."""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from justdata.apps.dataexplorer.report_builder.sections.lender_borrower_income import (
    create_lender_borrower_income_table,
)
from justdata.apps.dataexplorer.report_builder.sections.lender_neighborhood_demographics import (
    create_lender_neighborhood_demographics_table,
)
from justdata.apps.dataexplorer.report_builder.sections.lender_neighborhood_income import (
    create_lender_neighborhood_income_table,
)
from justdata.apps.dataexplorer.report_builder.sections.lender_race_ethnicity import (
    create_lender_race_ethnicity_table,
)
from justdata.apps.dataexplorer.shared.filters import filter_df_by_loan_purpose

# Import LendSight's proven table building function
from justdata.apps.lendsight.report_builder import (
    calculate_mortgage_hhi_for_year,
)

logger = logging.getLogger(__name__)


def build_area_report_all_lenders(
    hmda_data: List[Dict[str, Any]],
    geoids: List[str],
    years: List[int],
    census_data: Dict = None,
    historical_census_data: Dict = None,
    hud_data: Dict = None,
    progress_tracker=None,
    action_taken: List[str] = None
) -> Dict[str, Any]:
    """
    Build area analysis report with ALL lenders (not just top 10) for Excel export.
    
    This is identical to build_area_report except Section 3 includes all lenders.
    """
    # Reuse the main build_area_report function but override Section 3
    report_data = build_area_report(
        hmda_data=hmda_data,
        geoids=geoids,
        years=years,
        census_data=census_data,
        historical_census_data=historical_census_data,
        progress_tracker=progress_tracker,
        action_taken=action_taken
    )
    
    # Now rebuild Section 3 with ALL lenders
    import pandas as pd
    from justdata.apps.lendsight.report_builder import clean_mortgage_data
    
    # Convert to DataFrame
    df = pd.DataFrame(hmda_data)
    if df.empty:
        return report_data
    
    # Clean data
    df = clean_mortgage_data(df)
    
    # Get HUD data if not provided
    if hud_data is None:
        from justdata.apps.lendsight.hud_processor import get_hud_data_for_counties
        from justdata.apps.dataexplorer.cache_utils import load_hud_data, save_hud_data
        hud_data = load_hud_data(geoids)
        if hud_data is None:
            try:
                hud_data = get_hud_data_for_counties(geoids)
                save_hud_data(geoids, hud_data)
            except Exception as e:
                logger.warning(f"Error fetching HUD data: {e}")
                hud_data = {}
    
    # Rebuild Section 3 with ALL lenders (not just top 10)
    logger.info(f"[DEBUG] Building Section 3 tables with ALL lenders for Excel export")
    latest_year = max(years)
    latest_year_df = df[df['year'] == latest_year].copy()
    
    # Check if lender_name column exists
    lender_col = None
    if 'lender_name' in latest_year_df.columns:
        lender_col = 'lender_name'
    else:
        for col in ['lender', 'name', 'respondent_name', 'respondent_name_clean']:
            if col in latest_year_df.columns:
                lender_col = col
                break
    
    if not lender_col:
        logger.error(f"[DEBUG] No lender column found. Cannot build Section 3 tables with all lenders.")
        return report_data
    
    # Generate tables for each loan purpose with ALL lenders
    loan_purposes = ['all', 'purchase', 'refinance', 'equity']
    section3_tables_all = {}
    
    for purpose in loan_purposes:
        logger.info(f"[DEBUG] Building Section 3 tables for loan purpose: {purpose} (ALL lenders)")
        
        # Filter latest year data by loan purpose
        purpose_latest_df = filter_df_by_loan_purpose(latest_year_df, purpose)
        
        if purpose_latest_df.empty or purpose_latest_df[lender_col].notna().sum() == 0:
            logger.warning(f"[DEBUG] No lender data for loan purpose: {purpose}")
            section3_tables_all[purpose] = {
                'top_lender_names': [],
                'loans_by_race_ethnicity': pd.DataFrame(),
                'loans_by_borrower_income': pd.DataFrame(),
                'loans_by_neighborhood_income': pd.DataFrame(),
                'loans_by_neighborhood_demographics': pd.DataFrame()
            }
            continue
        
        # Get ALL lenders for this loan purpose (not just top 10)
        purpose_latest_df_clean = purpose_latest_df[purpose_latest_df[lender_col].notna()].copy()
        lender_totals = purpose_latest_df_clean.groupby(lender_col)['total_originations'].sum().reset_index()
        lender_totals = lender_totals.sort_values('total_originations', ascending=False)
        all_lender_names = lender_totals[lender_col].tolist()  # ALL lenders, not just top 10
        logger.info(f"[DEBUG] Found {len(all_lender_names)} total lenders for {purpose}")
        
        # Filter full DataFrame (all years) for ALL lenders and this loan purpose
        purpose_df = filter_df_by_loan_purpose(df, purpose)
        if lender_col == 'lender_name':
            all_lenders_df = purpose_df[purpose_df['lender_name'].isin(all_lender_names)] if all_lender_names else pd.DataFrame()
        else:
            all_lenders_df = purpose_df[purpose_df[lender_col].isin(all_lender_names)] if all_lender_names else pd.DataFrame()
            if not all_lenders_df.empty and lender_col != 'lender_name':
                all_lenders_df = all_lenders_df.rename(columns={lender_col: 'lender_name'})
        
        # Create lender-focused tables with ALL lenders
        if all_lenders_df.empty:
            loans_by_race_ethnicity_lenders = pd.DataFrame()
            loans_by_borrower_income_lenders = pd.DataFrame()
            loans_by_neighborhood_income_lenders = pd.DataFrame()
            loans_by_neighborhood_demographics_lenders = pd.DataFrame()
        else:
            loans_by_race_ethnicity_lenders = create_lender_race_ethnicity_table(
                all_lenders_df, years, census_data=census_data
            )
            loans_by_borrower_income_lenders = create_lender_borrower_income_table(
                all_lenders_df, years, hud_data=hud_data
            )
            loans_by_neighborhood_income_lenders = create_lender_neighborhood_income_table(
                all_lenders_df, years, hud_data=hud_data, census_data=census_data
            )
            loans_by_neighborhood_demographics_lenders = create_lender_neighborhood_demographics_table(
                all_lenders_df, years, census_data=census_data
            )
        
        section3_tables_all[purpose] = {
            'top_lender_names': all_lender_names,  # All lender names
            'loans_by_race_ethnicity': loans_by_race_ethnicity_lenders,
            'loans_by_borrower_income': loans_by_borrower_income_lenders,
            'loans_by_neighborhood_income': loans_by_neighborhood_income_lenders,
            'loans_by_neighborhood_demographics': loans_by_neighborhood_demographics_lenders
        }
    
    # Replace Section 3 with all lenders data
    report_data['section3'] = {
        'years': years,
        'by_purpose': section3_tables_all
    }
    
    # Section 4: HHI Market Concentration by Loan Purpose
    # Calculate HHI separately for each loan purpose
    if progress_tracker:
        progress_tracker.update_progress('building_report', 90, 'Building Section 4 (HHI)...')
    
    hhi_by_year_purpose = []
    loan_purpose_map = {
        '1': 'Home Purchase',
        '31': 'Refinance',
        '32': 'Refinance',
        '2': 'Home Equity',
        '4': 'Home Equity'
    }
    
    for year in sorted(years):
        year_df = df[df['year'] == year].copy()
        year_data = {'year': year}
        
        # Calculate HHI for each loan purpose
        for purpose_code, purpose_name in loan_purpose_map.items():
            purpose_df = year_df[year_df['loan_purpose'] == purpose_code]
            if not purpose_df.empty:
                hhi_result = calculate_mortgage_hhi_for_year(purpose_df, year)
                year_data[purpose_name] = hhi_result['hhi'] if hhi_result['hhi'] is not None else None
            else:
                year_data[purpose_name] = None
        
        hhi_by_year_purpose.append(year_data)
    
    report_data['section4'] = {
        'hhi_by_year_purpose': hhi_by_year_purpose
    }
    
    logger.info(f"[DEBUG] Created section4 with {len(hhi_by_year_purpose)} years of HHI data")
    logger.info(f"[DEBUG] Section4 keys: {list(report_data['section4'].keys())}")
    logger.info(f"[DEBUG] Sample HHI data: {hhi_by_year_purpose[0] if hhi_by_year_purpose else 'None'}")
    
    return report_data
    
    # Convert DataFrames to JSON-serializable format for template rendering
    import numpy as np
    
    def convert_numpy_types(obj):
        """Convert numpy types to native Python types for JSON serialization."""
        if isinstance(obj, dict):
            return {k: convert_numpy_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy_types(item) for item in obj]
        elif isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32, np.float16)):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj):
            return None
        else:
            return obj
    
    # Convert Section 2 tables (nested by loan purpose)
    if 'section2' in report_data and 'by_purpose' in report_data['section2']:
        section2 = report_data['section2']
        for purpose, tables in section2['by_purpose'].items():
            for table_name in ['loans_by_race_ethnicity', 'loans_by_borrower_income',
                              'loans_by_neighborhood_income', 'loans_by_neighborhood_demographics']:
                if isinstance(tables.get(table_name), pd.DataFrame):
                    tables[table_name] = convert_numpy_types(
                        tables[table_name].to_dict('records')
                        if not tables[table_name].empty else []
                    )
    
    # Convert Section 3 tables (nested by loan purpose)
    if 'section3' in report_data and 'by_purpose' in report_data['section3']:
        section3 = report_data['section3']
        for purpose, tables in section3['by_purpose'].items():
            for table_name in ['loans_by_race_ethnicity', 'loans_by_borrower_income', 
                              'loans_by_neighborhood_income', 'loans_by_neighborhood_demographics']:
                if isinstance(tables.get(table_name), pd.DataFrame):
                    tables[table_name] = convert_numpy_types(
                        tables[table_name].to_dict('records')
                        if not tables[table_name].empty else []
                    )
    
    # Convert Section 4 HHI data
    if 'section4' in report_data and 'hhi_by_year_purpose' in report_data['section4']:
        report_data['section4']['hhi_by_year_purpose'] = convert_numpy_types(report_data['section4']['hhi_by_year_purpose'])
        logger.info(f"[DEBUG] Converted section4 HHI data, {len(report_data['section4']['hhi_by_year_purpose'])} years")
    else:
        logger.warning(f"[DEBUG] Section4 not found or missing hhi_by_year_purpose! report_data keys: {list(report_data.keys())}")
        if 'section4' in report_data:
            logger.warning(f"[DEBUG] Section4 keys: {list(report_data['section4'].keys())}")
    
    logger.info(f"[DEBUG] Final report_data keys before return: {list(report_data.keys())}")
    return report_data


