#!/usr/bin/env python3
"""
Generate State, CBSA, and National Benchmark Files
Creates JSON files for all 50 states + DC + territories, all CBSAs, and national benchmarks.
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime

# Add repo root to path
REPO_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(REPO_ROOT))

from justdata.apps.bizsight.utils.bigquery_client import BigQueryClient

# Output directory: justdata/apps/bizsight/data/
OUTPUT_DIR = Path(__file__).parent / 'data'

# State FIPS codes (01-56, includes territories)
STATE_FIPS_CODES = [
    '01', '02', '04', '05', '06', '08', '09', '10', '11', '12', '13', '15', '16', '17', '18', '19',
    '20', '21', '22', '23', '24', '25', '26', '27', '28', '29', '30', '31', '32', '33', '34', '35',
    '36', '37', '38', '39', '40', '41', '42', '44', '45', '46', '47', '48', '49', '50', '51', '53',
    '54', '55', '56', '72'  # Includes DC (11), territories (72), etc.
]


def build_benchmark_dict(row, year=2024, geo_key=None, geo_value=None):
    """Build a benchmark dict from a query result row, using correct denominators."""
    total_loans = int(row.get('total_loans', 0))
    total_amount = float(row.get('total_amount', 0.0))
    num_under_100k = int(row.get('num_under_100k', 0))
    num_100k_250k = int(row.get('num_100k_250k', 0))
    num_250k_1m = int(row.get('num_250k_1m', 0))
    amt_under_100k = float(row.get('amt_under_100k', 0.0))
    amt_250k_1m = float(row.get('amt_250k_1m', 0.0))
    numsb_under_1m = int(row.get('numsb_under_1m', 0))
    amtsb_under_1m = float(row.get('amtsb_under_1m', 0.0))
    lmi_loans = int(row.get('lmi_tract_loans', 0))
    lmi_amount = float(row.get('lmi_tract_amount', 0.0))

    # Income category breakdowns
    low_income_loans = int(row.get('low_income_loans', 0))
    moderate_income_loans = int(row.get('moderate_income_loans', 0))
    middle_income_loans = int(row.get('middle_income_loans', 0))
    upper_income_loans = int(row.get('upper_income_loans', 0))
    low_income_amount = float(row.get('low_income_amount', 0.0))
    moderate_income_amount = float(row.get('moderate_income_amount', 0.0))
    middle_income_amount = float(row.get('middle_income_amount', 0.0))
    upper_income_amount = float(row.get('upper_income_amount', 0.0))
    unknown_income_loans = int(row.get('unknown_income_loans', 0))
    unknown_income_amount = float(row.get('unknown_income_amount', 0.0))

    # Known-income denominators (exclude unknown for income category percentages)
    known_income_loans = total_loans - unknown_income_loans
    known_income_amount = total_amount - unknown_income_amount

    benchmark = {
        'year': year,
        'total_loans': total_loans,
        'total_amount': total_amount,
        # Size category percentages (use total as denominator)
        'pct_loans_under_100k': (num_under_100k / total_loans * 100) if total_loans > 0 else 0.0,
        'pct_loans_100k_250k': (num_100k_250k / total_loans * 100) if total_loans > 0 else 0.0,
        'pct_loans_250k_1m': (num_250k_1m / total_loans * 100) if total_loans > 0 else 0.0,
        'pct_loans_sb_under_1m': (numsb_under_1m / total_loans * 100) if total_loans > 0 else 0.0,
        'pct_amount_under_100k': (amt_under_100k / total_amount * 100) if total_amount > 0 else 0.0,
        'pct_amount_250k_1m': (amt_250k_1m / total_amount * 100) if total_amount > 0 else 0.0,
        'pct_amount_sb_under_1m': (amtsb_under_1m / total_amount * 100) if total_amount > 0 else 0.0,
        # LMI percentages (use known-income denominator)
        'pct_loans_lmi_tract': (lmi_loans / known_income_loans * 100) if known_income_loans > 0 else 0.0,
        'pct_amount_lmi_tract': (lmi_amount / known_income_amount * 100) if known_income_amount > 0 else 0.0,
        # Income category percentages by loan count (use known-income denominator)
        'pct_loans_low_income': (low_income_loans / known_income_loans * 100) if known_income_loans > 0 else 0.0,
        'pct_loans_moderate_income': (moderate_income_loans / known_income_loans * 100) if known_income_loans > 0 else 0.0,
        'pct_loans_middle_income': (middle_income_loans / known_income_loans * 100) if known_income_loans > 0 else 0.0,
        'pct_loans_upper_income': (upper_income_loans / known_income_loans * 100) if known_income_loans > 0 else 0.0,
        # Income category percentages by loan amount (use known-income denominator)
        'pct_amount_low_income': (low_income_amount / known_income_amount * 100) if known_income_amount > 0 else 0.0,
        'pct_amount_moderate_income': (moderate_income_amount / known_income_amount * 100) if known_income_amount > 0 else 0.0,
        'pct_amount_middle_income': (middle_income_amount / known_income_amount * 100) if known_income_amount > 0 else 0.0,
        'pct_amount_upper_income': (upper_income_amount / known_income_amount * 100) if known_income_amount > 0 else 0.0,
        # Raw values
        'num_under_100k': num_under_100k,
        'num_100k_250k': num_100k_250k,
        'num_250k_1m': num_250k_1m,
        'amt_under_100k': amt_under_100k,
        'amt_250k_1m': amt_250k_1m,
        'numsb_under_1m': numsb_under_1m,
        'amtsb_under_1m': amtsb_under_1m,
        'lmi_tract_loans': lmi_loans,
        'lmi_tract_amount': lmi_amount,
        'low_income_loans': low_income_loans,
        'moderate_income_loans': moderate_income_loans,
        'middle_income_loans': middle_income_loans,
        'upper_income_loans': upper_income_loans,
        'low_income_amount': low_income_amount,
        'moderate_income_amount': moderate_income_amount,
        'middle_income_amount': middle_income_amount,
        'upper_income_amount': upper_income_amount,
        'unknown_income_loans': unknown_income_loans,
        'unknown_income_amount': unknown_income_amount,
    }

    if geo_key and geo_value:
        benchmark[geo_key] = geo_value

    return benchmark


def generate_state_benchmark(state_fips, year=2024, bq_client=None):
    """Generate benchmark data for a single state."""
    try:
        state_query = bq_client.get_state_benchmarks(state_fips, year=year)
        state_df = state_query.to_dataframe()
        if state_df.empty:
            return None
        row = state_df.iloc[0]
        return build_benchmark_dict(row, year=year, geo_key='state_fips', geo_value=state_fips)
    except Exception as e:
        print(f"    Error for state {state_fips}: {e}")
        return None


def generate_national_benchmark(year=2024, bq_client=None):
    """Generate national benchmark data."""
    try:
        national_query = bq_client.get_national_benchmarks(year=year)
        national_df = national_query.to_dataframe()
        if national_df.empty:
            return None
        row = national_df.iloc[0]
        return build_benchmark_dict(row, year=year)
    except Exception as e:
        print(f"    Error for national: {e}")
        return None


def generate_cbsa_benchmarks(year=2024, bq_client=None):
    """Generate benchmarks for all CBSAs using a single aggregated query."""
    project_id = bq_client.project_id
    sql = f"""
    SELECT
        CAST(g.cbsa AS STRING) as cbsa_code,
        g.cbsa_name,
        SUM(COALESCE(a.num_under_100k, 0) + COALESCE(a.num_100k_250k, 0) + COALESCE(a.num_250k_1m, 0)) as total_loans,
        SUM(COALESCE(a.amt_under_100k, 0) + COALESCE(a.amt_100k_250k, 0) + COALESCE(a.amt_250k_1m, 0)) as total_amount,
        SUM(COALESCE(a.low_income_loans, 0) + COALESCE(a.moderate_income_loans, 0)) as lmi_tract_loans,
        SUM(COALESCE(a.lmi_tract_amount, 0)) as lmi_tract_amount,
        SUM(COALESCE(a.low_income_loans, 0)) as low_income_loans,
        SUM(COALESCE(a.moderate_income_loans, 0)) as moderate_income_loans,
        0 as middle_income_loans,
        SUM(COALESCE(a.midu_income_loans, 0)) as upper_income_loans,
        SUM(COALESCE(a.low_income_amount, 0)) as low_income_amount,
        SUM(COALESCE(a.moderate_income_amount, 0)) as moderate_income_amount,
        0 as middle_income_amount,
        SUM(COALESCE(a.midu_income_amount, 0)) as upper_income_amount,
        SUM(COALESCE(a.num_under_100k, 0)) as num_under_100k,
        SUM(COALESCE(a.num_100k_250k, 0)) as num_100k_250k,
        SUM(COALESCE(a.num_250k_1m, 0)) as num_250k_1m,
        SUM(COALESCE(a.amt_under_100k, 0)) as amt_under_100k,
        SUM(COALESCE(a.amt_250k_1m, 0)) as amt_250k_1m,
        SUM(COALESCE(a.numsbrev_under_1m, 0)) as numsb_under_1m,
        SUM(COALESCE(a.amtsbrev_under_1m, 0)) as amtsb_under_1m,
        SUM(COALESCE(a.unknown_income_loans, 0)) as unknown_income_loans,
        SUM(COALESCE(a.unknown_income_amount, 0)) as unknown_income_amount
    FROM `{project_id}.bizsight.sb_county_summary` a
    JOIN `{project_id}.shared.cbsa_to_county` g
        ON LPAD(CAST(a.geoid5 AS STRING), 5, '0') = LPAD(CAST(g.geoid5 AS STRING), 5, '0')
    WHERE CAST(a.year AS INT64) = {year}
        AND g.cbsa IS NOT NULL
    GROUP BY g.cbsa, g.cbsa_name
    ORDER BY g.cbsa
    """
    try:
        result = bq_client.query(sql)
        df = result.to_dataframe()
        cbsa_benchmarks = {}
        for _, row in df.iterrows():
            cbsa_code = str(row['cbsa_code'])
            cbsa_name = str(row.get('cbsa_name', ''))
            benchmark = build_benchmark_dict(row, year=year, geo_key='cbsa_code', geo_value=cbsa_code)
            benchmark['cbsa_name'] = cbsa_name
            cbsa_benchmarks[cbsa_code] = benchmark
        return cbsa_benchmarks
    except Exception as e:
        print(f"    Error generating CBSA benchmarks: {e}")
        import traceback
        traceback.print_exc()
        return {}


def main():
    """Generate all benchmark files."""
    print("=" * 80)
    print("GENERATING STATE, CBSA, AND NATIONAL BENCHMARK FILES")
    print("=" * 80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Year: 2024")
    print()

    # Initialize BigQuery client
    print("Initializing BigQuery client...")
    try:
        bq_client = BigQueryClient()
        print("BigQuery client initialized")
    except Exception as e:
        print(f"ERROR: Failed to initialize BigQuery client: {e}")
        return

    output_dir = OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}")
    print()

    # ==================== STATE BENCHMARKS ====================
    print("=" * 80)
    print("GENERATING STATE BENCHMARKS")
    print("=" * 80)
    state_benchmarks = {}
    successful_states = 0
    failed_states = 0

    for state_fips in STATE_FIPS_CODES:
        print(f"  State {state_fips}...", end=" ")
        benchmark = generate_state_benchmark(state_fips, year=2024, bq_client=bq_client)
        if benchmark:
            state_benchmarks[state_fips] = benchmark
            state_file = output_dir / f"{state_fips}.json"
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(benchmark, f, indent=2, ensure_ascii=False)
            print(f"{benchmark['total_loans']:,} loans")
            successful_states += 1
        else:
            print("no data")
            failed_states += 1

    print(f"\nGenerated {successful_states} state benchmarks")
    if failed_states > 0:
        print(f"Failed: {failed_states}")

    # ==================== CBSA BENCHMARKS ====================
    print()
    print("=" * 80)
    print("GENERATING CBSA BENCHMARKS")
    print("=" * 80)
    cbsa_benchmarks = generate_cbsa_benchmarks(year=2024, bq_client=bq_client)
    cbsa_count = len(cbsa_benchmarks)
    print(f"Generated {cbsa_count} CBSA benchmarks")

    if cbsa_benchmarks:
        # Save individual CBSA files in a subdirectory
        cbsa_dir = output_dir / 'cbsa'
        cbsa_dir.mkdir(parents=True, exist_ok=True)
        for cbsa_code, benchmark in cbsa_benchmarks.items():
            cbsa_file = cbsa_dir / f"{cbsa_code}.json"
            with open(cbsa_file, 'w', encoding='utf-8') as f:
                json.dump(benchmark, f, indent=2, ensure_ascii=False)

    # ==================== NATIONAL BENCHMARK ====================
    print()
    print("=" * 80)
    print("GENERATING NATIONAL BENCHMARK")
    print("=" * 80)
    national_benchmark = generate_national_benchmark(year=2024, bq_client=bq_client)

    if national_benchmark:
        national_file = output_dir / "national.json"
        with open(national_file, 'w', encoding='utf-8') as f:
            json.dump(national_benchmark, f, indent=2, ensure_ascii=False)
        print(f"Saved national benchmark: {national_benchmark['total_loans']:,} loans")
    else:
        print("Failed to generate national benchmark")

    # ==================== CONSOLIDATED FILE ====================
    if state_benchmarks and national_benchmark:
        consolidated_data = {
            'generated_at': datetime.now().isoformat(),
            'year': 2024,
            'states': {
                fips: {'2024': bm} for fips, bm in state_benchmarks.items()
            },
            'cbsas': {
                code: {'2024': bm} for code, bm in cbsa_benchmarks.items()
            } if cbsa_benchmarks else {},
            'national': {
                '2024': national_benchmark
            }
        }

        consolidated_file = output_dir / "benchmarks.json"
        with open(consolidated_file, 'w', encoding='utf-8') as f:
            json.dump(consolidated_data, f, indent=2, ensure_ascii=False)
        print(f"\nSaved consolidated benchmarks to: {consolidated_file}")

    print()
    print("=" * 80)
    print("BENCHMARK GENERATION COMPLETE")
    print("=" * 80)
    print(f"States: {successful_states}")
    print(f"CBSAs: {cbsa_count}")
    print(f"National: {'yes' if national_benchmark else 'no'}")
    print(f"Output: {output_dir}")
    print()


if __name__ == '__main__':
    main()
