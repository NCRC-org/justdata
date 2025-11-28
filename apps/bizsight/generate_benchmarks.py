#!/usr/bin/env python3
"""
Generate State and National Benchmark Files
Creates JSON files for all 50 states + DC + territories (52 total) plus national benchmarks.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add repo root to path
REPO_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(REPO_ROOT))

from apps.bizsight.config import BizSightConfig
from apps.bizsight.utils.bigquery_client import BigQueryClient

# State FIPS codes (01-56, includes territories)
STATE_FIPS_CODES = [
    '01', '02', '04', '05', '06', '08', '09', '10', '11', '12', '13', '15', '16', '17', '18', '19',
    '20', '21', '22', '23', '24', '25', '26', '27', '28', '29', '30', '31', '32', '33', '34', '35',
    '36', '37', '38', '39', '40', '41', '42', '44', '45', '46', '47', '48', '49', '50', '51', '53',
    '54', '55', '56', '72'  # Includes DC (11), territories (72), etc.
]


def generate_state_benchmark(state_fips: str, year: int = 2024, bq_client: BigQueryClient = None):
    """Generate benchmark data for a single state."""
    if bq_client is None:
        bq_client = BigQueryClient()
    
    try:
        print(f"  Fetching data for state FIPS: {state_fips}...")
        state_query = bq_client.get_state_benchmarks(state_fips, year=year)
        state_df = state_query.to_dataframe()
        
        if state_df.empty:
            print(f"    ⚠ No data found for state {state_fips}")
            return None
        
        row = state_df.iloc[0]
        state_total = int(row.get('total_loans', 0))
        state_amount = float(row.get('total_amount', 0.0))
        state_num_under_100k = int(row.get('num_under_100k', 0))
        state_num_100k_250k = int(row.get('num_100k_250k', 0))
        state_num_250k_1m = int(row.get('num_250k_1m', 0))
        state_amt_under_100k = float(row.get('amt_under_100k', 0.0))
        state_amt_250k_1m = float(row.get('amt_250k_1m', 0.0))
        state_numsb_under_1m = int(row.get('numsb_under_1m', 0))
        state_amtsb_under_1m = float(row.get('amtsb_under_1m', 0.0))
        state_lmi_loans = int(row.get('lmi_tract_loans', 0))
        state_lmi_amount = float(row.get('lmi_tract_amount', 0.0))
        
        # Income category breakdowns
        state_low_income_loans = int(row.get('low_income_loans', 0))
        state_moderate_income_loans = int(row.get('moderate_income_loans', 0))
        state_middle_income_loans = int(row.get('middle_income_loans', 0))
        state_upper_income_loans = int(row.get('upper_income_loans', 0))
        state_low_income_amount = float(row.get('low_income_amount', 0.0))
        state_moderate_income_amount = float(row.get('moderate_income_amount', 0.0))
        state_middle_income_amount = float(row.get('middle_income_amount', 0.0))
        state_upper_income_amount = float(row.get('upper_income_amount', 0.0))
        
        benchmark = {
            'state_fips': state_fips,
            'year': year,
            'total_loans': state_total,
            'total_amount': state_amount,
            'pct_loans_under_100k': (state_num_under_100k / state_total * 100) if state_total > 0 else 0.0,
            'pct_loans_100k_250k': (state_num_100k_250k / state_total * 100) if state_total > 0 else 0.0,
            'pct_loans_250k_1m': (state_num_250k_1m / state_total * 100) if state_total > 0 else 0.0,
            'pct_loans_sb_under_1m': (state_numsb_under_1m / state_total * 100) if state_total > 0 else 0.0,
            'pct_loans_lmi_tract': (state_lmi_loans / state_total * 100) if state_total > 0 else 0.0,
            'pct_amount_under_100k': (state_amt_under_100k / state_amount * 100) if state_amount > 0 else 0.0,
            'pct_amount_250k_1m': (state_amt_250k_1m / state_amount * 100) if state_amount > 0 else 0.0,
            'pct_amount_sb_under_1m': (state_amtsb_under_1m / state_amount * 100) if state_amount > 0 else 0.0,
            'pct_amount_lmi_tract': (state_lmi_amount / state_amount * 100) if state_amount > 0 else 0.0,
            # Income category percentages (by loan count)
            'pct_loans_low_income': (state_low_income_loans / state_total * 100) if state_total > 0 else 0.0,
            'pct_loans_moderate_income': (state_moderate_income_loans / state_total * 100) if state_total > 0 else 0.0,
            'pct_loans_middle_income': (state_middle_income_loans / state_total * 100) if state_total > 0 else 0.0,
            'pct_loans_upper_income': (state_upper_income_loans / state_total * 100) if state_total > 0 else 0.0,
            # Income category percentages (by loan amount)
            'pct_amount_low_income': (state_low_income_amount / state_amount * 100) if state_amount > 0 else 0.0,
            'pct_amount_moderate_income': (state_moderate_income_amount / state_amount * 100) if state_amount > 0 else 0.0,
            'pct_amount_middle_income': (state_middle_income_amount / state_amount * 100) if state_amount > 0 else 0.0,
            'pct_amount_upper_income': (state_upper_income_amount / state_amount * 100) if state_amount > 0 else 0.0,
            # Raw values for reference
            'num_under_100k': state_num_under_100k,
            'num_100k_250k': state_num_100k_250k,
            'num_250k_1m': state_num_250k_1m,
            'amt_under_100k': state_amt_under_100k,
            'amt_250k_1m': state_amt_250k_1m,
            'numsb_under_1m': state_numsb_under_1m,
            'amtsb_under_1m': state_amtsb_under_1m,
            'lmi_tract_loans': state_lmi_loans,
            'lmi_tract_amount': state_lmi_amount,
            'low_income_loans': state_low_income_loans,
            'moderate_income_loans': state_moderate_income_loans,
            'middle_income_loans': state_middle_income_loans,
            'upper_income_loans': state_upper_income_loans,
            'low_income_amount': state_low_income_amount,
            'moderate_income_amount': state_moderate_income_amount,
            'middle_income_amount': state_middle_income_amount,
            'upper_income_amount': state_upper_income_amount
        }
        
        print(f"    ✓ Generated benchmark: {state_total:,} loans, ${state_amount:,.0f}")
        return benchmark
        
    except Exception as e:
        print(f"    ✗ Error generating benchmark for state {state_fips}: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_national_benchmark(year: int = 2024, bq_client: BigQueryClient = None):
    """Generate national benchmark data."""
    if bq_client is None:
        bq_client = BigQueryClient()
    
    try:
        print(f"  Fetching national data for year {year}...")
        national_query = bq_client.get_national_benchmarks(year=year)
        national_df = national_query.to_dataframe()
        
        if national_df.empty:
            print(f"    ⚠ No national data found for year {year}")
            return None
        
        row = national_df.iloc[0]
        national_total = int(row.get('total_loans', 0))
        national_amount = float(row.get('total_amount', 0.0))
        national_num_under_100k = int(row.get('num_under_100k', 0))
        national_num_100k_250k = int(row.get('num_100k_250k', 0))
        national_num_250k_1m = int(row.get('num_250k_1m', 0))
        national_amt_under_100k = float(row.get('amt_under_100k', 0.0))
        national_amt_250k_1m = float(row.get('amt_250k_1m', 0.0))
        national_numsb_under_1m = int(row.get('numsb_under_1m', 0))
        national_amtsb_under_1m = float(row.get('amtsb_under_1m', 0.0))
        national_lmi_loans = int(row.get('lmi_tract_loans', 0))
        national_lmi_amount = float(row.get('lmi_tract_amount', 0.0))
        
        # Income category breakdowns
        national_low_income_loans = int(row.get('low_income_loans', 0))
        national_moderate_income_loans = int(row.get('moderate_income_loans', 0))
        national_middle_income_loans = int(row.get('middle_income_loans', 0))
        national_upper_income_loans = int(row.get('upper_income_loans', 0))
        national_low_income_amount = float(row.get('low_income_amount', 0.0))
        national_moderate_income_amount = float(row.get('moderate_income_amount', 0.0))
        national_middle_income_amount = float(row.get('middle_income_amount', 0.0))
        national_upper_income_amount = float(row.get('upper_income_amount', 0.0))
        
        benchmark = {
            'year': year,
            'total_loans': national_total,
            'total_amount': national_amount,
            'pct_loans_under_100k': (national_num_under_100k / national_total * 100) if national_total > 0 else 0.0,
            'pct_loans_100k_250k': (national_num_100k_250k / national_total * 100) if national_total > 0 else 0.0,
            'pct_loans_250k_1m': (national_num_250k_1m / national_total * 100) if national_total > 0 else 0.0,
            'pct_loans_sb_under_1m': (national_numsb_under_1m / national_total * 100) if national_total > 0 else 0.0,
            'pct_loans_lmi_tract': (national_lmi_loans / national_total * 100) if national_total > 0 else 0.0,
            'pct_amount_under_100k': (national_amt_under_100k / national_amount * 100) if national_amount > 0 else 0.0,
            'pct_amount_250k_1m': (national_amt_250k_1m / national_amount * 100) if national_amount > 0 else 0.0,
            'pct_amount_sb_under_1m': (national_amtsb_under_1m / national_amount * 100) if national_amount > 0 else 0.0,
            'pct_amount_lmi_tract': (national_lmi_amount / national_amount * 100) if national_amount > 0 else 0.0,
            # Income category percentages (by loan count)
            'pct_loans_low_income': (national_low_income_loans / national_total * 100) if national_total > 0 else 0.0,
            'pct_loans_moderate_income': (national_moderate_income_loans / national_total * 100) if national_total > 0 else 0.0,
            'pct_loans_middle_income': (national_middle_income_loans / national_total * 100) if national_total > 0 else 0.0,
            'pct_loans_upper_income': (national_upper_income_loans / national_total * 100) if national_total > 0 else 0.0,
            # Income category percentages (by loan amount)
            'pct_amount_low_income': (national_low_income_amount / national_amount * 100) if national_amount > 0 else 0.0,
            'pct_amount_moderate_income': (national_moderate_income_amount / national_amount * 100) if national_amount > 0 else 0.0,
            'pct_amount_middle_income': (national_middle_income_amount / national_amount * 100) if national_amount > 0 else 0.0,
            'pct_amount_upper_income': (national_upper_income_amount / national_amount * 100) if national_amount > 0 else 0.0,
            # Raw values for reference
            'num_under_100k': national_num_under_100k,
            'num_100k_250k': national_num_100k_250k,
            'num_250k_1m': national_num_250k_1m,
            'amt_under_100k': national_amt_under_100k,
            'amt_250k_1m': national_amt_250k_1m,
            'numsb_under_1m': national_numsb_under_1m,
            'amtsb_under_1m': national_amtsb_under_1m,
            'lmi_tract_loans': national_lmi_loans,
            'lmi_tract_amount': national_lmi_amount,
            'low_income_loans': national_low_income_loans,
            'moderate_income_loans': national_moderate_income_loans,
            'middle_income_loans': national_middle_income_loans,
            'upper_income_loans': national_upper_income_loans,
            'low_income_amount': national_low_income_amount,
            'moderate_income_amount': national_moderate_income_amount,
            'middle_income_amount': national_middle_income_amount,
            'upper_income_amount': national_upper_income_amount
        }
        
        print(f"    ✓ Generated national benchmark: {national_total:,} loans, ${national_amount:,.0f}")
        return benchmark
        
    except Exception as e:
        print(f"    ✗ Error generating national benchmark: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Generate all benchmark files."""
    print("=" * 80)
    print("GENERATING STATE AND NATIONAL BENCHMARK FILES")
    print("=" * 80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Year: 2024")
    print()
    
    # Initialize BigQuery client
    print("Initializing BigQuery client...")
    try:
        bq_client = BigQueryClient()
        print("✓ BigQuery client initialized")
    except Exception as e:
        print(f"✗ ERROR: Failed to initialize BigQuery client: {e}")
        return
    
    # Determine output directory
    output_dir = Path(BizSightConfig.DATA_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nOutput directory: {output_dir}")
    print()
    
    # Generate state benchmarks
    print("=" * 80)
    print("GENERATING STATE BENCHMARKS")
    print("=" * 80)
    state_benchmarks = {}
    successful_states = 0
    failed_states = 0
    
    for state_fips in STATE_FIPS_CODES:
        benchmark = generate_state_benchmark(state_fips, year=2024, bq_client=bq_client)
        if benchmark:
            state_benchmarks[state_fips] = benchmark
            # Save individual state file
            state_file = output_dir / f"{state_fips}.json"
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(benchmark, f, indent=2, ensure_ascii=False)
            successful_states += 1
        else:
            failed_states += 1
    
    print()
    print(f"✓ Generated {successful_states} state benchmarks")
    if failed_states > 0:
        print(f"⚠ Failed to generate {failed_states} state benchmarks")
    
    # Generate national benchmark
    print()
    print("=" * 80)
    print("GENERATING NATIONAL BENCHMARK")
    print("=" * 80)
    national_benchmark = generate_national_benchmark(year=2024, bq_client=bq_client)
    
    if national_benchmark:
        # Save national file
        national_file = output_dir / "national.json"
        with open(national_file, 'w', encoding='utf-8') as f:
            json.dump(national_benchmark, f, indent=2, ensure_ascii=False)
        print(f"✓ Saved national benchmark to: {national_file}")
    else:
        print("✗ Failed to generate national benchmark")
    
    # Also create consolidated benchmarks.json file
    if state_benchmarks and national_benchmark:
        consolidated_data = {
            'generated_at': datetime.now().isoformat(),
            'year': 2024,
            'states': {
                state_fips: {'2024': benchmark} 
                for state_fips, benchmark in state_benchmarks.items()
            },
            'national': {
                '2024': national_benchmark
            }
        }
        
        consolidated_file = output_dir / "benchmarks.json"
        with open(consolidated_file, 'w', encoding='utf-8') as f:
            json.dump(consolidated_data, f, indent=2, ensure_ascii=False)
        print(f"✓ Saved consolidated benchmarks to: {consolidated_file}")
    
    print()
    print("=" * 80)
    print("BENCHMARK GENERATION COMPLETE")
    print("=" * 80)
    print(f"State benchmarks: {successful_states} files")
    print(f"National benchmark: {'✓' if national_benchmark else '✗'}")
    print(f"Output directory: {output_dir}")
    print()


if __name__ == '__main__':
    main()

