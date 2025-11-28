#!/usr/bin/env python3
"""
Verify and Backup Benchmark Files
Verifies benchmark data exists and copies to multiple safe locations.
"""

import sys
import json
import shutil
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(REPO_ROOT))

from apps.bizsight.config import BizSightConfig

def verify_benchmark_file(file_path: Path) -> dict:
    """Verify a benchmark file exists and contains valid data."""
    if not file_path.exists():
        return {'exists': False, 'valid': False, 'error': 'File does not exist'}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check for required fields
        required_fields = ['total_loans', 'total_amount']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return {
                'exists': True,
                'valid': False,
                'error': f'Missing required fields: {missing_fields}',
                'data': data
            }
        
        return {
            'exists': True,
            'valid': True,
            'data': data,
            'total_loans': data.get('total_loans', 0),
            'total_amount': data.get('total_amount', 0.0)
        }
    except json.JSONDecodeError as e:
        return {'exists': True, 'valid': False, 'error': f'Invalid JSON: {e}'}
    except Exception as e:
        return {'exists': True, 'valid': False, 'error': f'Error reading file: {e}'}


def main():
    """Verify and backup benchmark files."""
    print("=" * 80)
    print("VERIFYING AND BACKING UP BENCHMARK FILES")
    print("=" * 80)
    print()
    
    # Source directory (where files were generated)
    source_dir = Path(BizSightConfig.DATA_DIR)
    print(f"Source directory: {source_dir}")
    
    # Backup locations
    backup_locations = [
        Path(BizSightConfig.BASE_DIR) / 'data',  # #JustData_Repo/data
        Path(BizSightConfig.BASE_DIR) / 'data' / 'benchmarks',  # #JustData_Repo/data/benchmarks
        Path(__file__).parent / 'data',  # apps/bizsight/data
    ]
    
    print(f"\nBackup locations:")
    for loc in backup_locations:
        print(f"  - {loc}")
    
    # Verify national benchmark
    print("\n" + "=" * 80)
    print("VERIFYING NATIONAL BENCHMARK")
    print("=" * 80)
    national_file = source_dir / "national.json"
    national_status = verify_benchmark_file(national_file)
    
    if national_status['exists'] and national_status['valid']:
        print(f"✓ National benchmark file exists and is valid")
        print(f"  Total loans: {national_status['total_loans']:,}")
        print(f"  Total amount: ${national_status['total_amount']:,.0f}")
        
        # Copy to backup locations
        for backup_dir in backup_locations:
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_file = backup_dir / "national.json"
            shutil.copy2(national_file, backup_file)
            print(f"  ✓ Copied to: {backup_file}")
    else:
        print(f"✗ National benchmark file issue: {national_status.get('error', 'Unknown error')}")
        return
    
    # Verify state benchmarks
    print("\n" + "=" * 80)
    print("VERIFYING STATE BENCHMARKS")
    print("=" * 80)
    
    state_fips_codes = [
        '01', '02', '04', '05', '06', '08', '09', '10', '11', '12', '13', '15', '16', '17', '18', '19',
        '20', '21', '22', '23', '24', '25', '26', '27', '28', '29', '30', '31', '32', '33', '34', '35',
        '36', '37', '38', '39', '40', '41', '42', '44', '45', '46', '47', '48', '49', '50', '51', '53',
        '54', '55', '56', '72'
    ]
    
    valid_states = 0
    invalid_states = 0
    missing_states = []
    
    for state_fips in state_fips_codes:
        state_file = source_dir / f"{state_fips}.json"
        state_status = verify_benchmark_file(state_file)
        
        if state_status['exists'] and state_status['valid']:
            valid_states += 1
            # Copy to backup locations
            for backup_dir in backup_locations:
                backup_dir.mkdir(parents=True, exist_ok=True)
                backup_file = backup_dir / f"{state_fips}.json"
                shutil.copy2(state_file, backup_file)
        elif state_status['exists']:
            invalid_states += 1
            print(f"  ⚠ State {state_fips}: {state_status.get('error', 'Invalid')}")
        else:
            missing_states.append(state_fips)
    
    print(f"\n✓ Valid state benchmarks: {valid_states}/52")
    if invalid_states > 0:
        print(f"⚠ Invalid state benchmarks: {invalid_states}")
    if missing_states:
        print(f"✗ Missing state benchmarks: {len(missing_states)} ({', '.join(missing_states[:10])}{'...' if len(missing_states) > 10 else ''})")
    
    # Verify consolidated benchmarks.json
    print("\n" + "=" * 80)
    print("VERIFYING CONSOLIDATED BENCHMARKS")
    print("=" * 80)
    consolidated_file = source_dir / "benchmarks.json"
    if consolidated_file.exists():
        try:
            with open(consolidated_file, 'r', encoding='utf-8') as f:
                consolidated_data = json.load(f)
            
            state_count = len(consolidated_data.get('states', {}))
            has_national = 'national' in consolidated_data
            
            print(f"✓ Consolidated benchmarks file exists")
            print(f"  States: {state_count}")
            print(f"  National: {'✓' if has_national else '✗'}")
            
            # Copy to backup locations
            for backup_dir in backup_locations:
                backup_dir.mkdir(parents=True, exist_ok=True)
                backup_file = backup_dir / "benchmarks.json"
                shutil.copy2(consolidated_file, backup_file)
                print(f"  ✓ Copied to: {backup_file}")
        except Exception as e:
            print(f"✗ Error reading consolidated file: {e}")
    else:
        print("⚠ Consolidated benchmarks.json not found")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"National benchmark: {'✓' if national_status['valid'] else '✗'}")
    print(f"State benchmarks: {valid_states}/52 valid")
    print(f"Files backed up to {len(backup_locations)} locations")
    print()
    print("Benchmark files are now available in:")
    for backup_dir in backup_locations:
        if (backup_dir / "national.json").exists():
            print(f"  ✓ {backup_dir}")
    print()


if __name__ == '__main__':
    main()

