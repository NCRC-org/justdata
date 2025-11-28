#!/usr/bin/env python3
"""
Cleanup script for #JustData_Repo
Removes old/unused files and archives files that might be needed later.
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

def get_repo_root():
    """Get the repository root directory."""
    return Path(__file__).parent.resolve()

def create_archive_dir():
    """Create archive directory with timestamp."""
    repo_root = get_repo_root()
    archive_name = f"archive_{datetime.now().strftime('%Y%m%d')}"
    archive_dir = repo_root / archive_name
    archive_dir.mkdir(exist_ok=True)
    
    # Create subdirectories
    (archive_dir / 'old_test_files').mkdir(exist_ok=True)
    (archive_dir / 'old_docs').mkdir(exist_ok=True)
    (archive_dir / 'old_scripts').mkdir(exist_ok=True)
    (archive_dir / 'old_deployment').mkdir(exist_ok=True)
    (archive_dir / 'legacy_files').mkdir(exist_ok=True)
    
    return archive_dir

def cleanup_files():
    """Clean up files in the repository."""
    repo_root = get_repo_root()
    archive_dir = create_archive_dir()
    
    print("="*70)
    print("JustData Repo Cleanup")
    print("="*70)
    print(f"Repository: {repo_root}")
    print(f"Archive: {archive_dir}")
    print()
    
    deleted_count = 0
    archived_count = 0
    
    # Files to DELETE (temporary/unnecessary)
    files_to_delete = [
        'Untitled-1',
        'env.template',  # Duplicate of env.example
        'copy_credentials.py',  # No longer needed
    ]
    
    # Files to ARCHIVE (might be needed later)
    files_to_archive = {
        # Old test files
        'old_test_files': [
            'test_api_direct_exec.py',
            'test_api_via_launcher.py',
            'test_api.bat',
            'test_census_api_direct.py',
            'test_claude_api_connection.py',
            'test_claude_api.py',
            'test_claude_now.bat',
            'test_claude_simple.py',
            'copy_and_test_claude.py',
            'quick_api_test.py',
            'execute_api_test.py',
            'execute_test_direct.py',
            'run_api_test_direct.py',
            'RUN_API_TEST.bat',
            'run_test_inline.py',
            'execute_lendsight.py',
        ],
        
        # Old documentation/analysis files
        'old_docs': [
            'CLAUDE_API_KEY_FOUND.md',
            'CLAUDE_API_TEST_FIXED.md',
            'CLAUDE_API_TEST_RESULTS.md',
            'CLAUDE_API_TEST_SUMMARY.md',
            'CLAUDE.md',
            'COMPREHENSIVE_APPLICATION_ANALYSIS.md',
            'CONFIG_FILE_ANALYSIS.md',
            'CONTACTS_SEARCH_SUMMARY.md',
            'EMAIL_EXTRACTION_SUMMARY.md',
            'ENV_FILES_FOUND.md',
            'FIX_MISSING_DEPENDENCIES.md',
            'FLATTEN_STRUCTURE_PLAN.md',
            'MERGERMETER_MIGRATION_STEPS.md',
            'SWITCH_TO_JASONEDITS.md',
            'TOOLS_SUMMARY.md',
            'banking_individuals_summary.md',
        ],
        
        # Old scripts
        'old_scripts': [
            '_run_lendsight_via_launcher.py',
            '_start_lendsight_direct.py',
            'check_and_install_anthropic.py',
            'extract_banking_emails.py',
            'extract_banking_names.py',
            'extract_emails_with_ocr.py',
            'extract_emails.py',
            'parse_pnc_assessment_areas.py',
            'search_banking_names.py',
            'search_contacts_fast.py',
            'search_contacts_in_epstein.py',
            'search_contacts_optimized.py',
            'move_mergermeter_to_jasonedits.bat',
            'move_mergermeter_to_jasonedits.py',
            'switch_to_jasonedits.bat',
            'switch_to_jasonedits.py',
            'verify_cleanup_start.bat',
            'verify_cleanup_start.py',
        ],
        
        # Old deployment files
        'old_deployment': [
            'mergermeter-deployment-20251121-140418',  # Old deployment directory
        ],
        
        # Legacy files from apps
        'legacy_files': [
            'apps/mergermeter/debug_pnc_pdf.py',
            'apps/mergermeter/parse_pnc_pdf.py',
            'apps/mergermeter/template_populator.py',
            'apps/mergermeter/template_populator_fixes.py',
            'apps/mergermeter/excel_postprocessor.py',  # Not used according to docs
            'apps/mergermeter/statistical_analysis.py',  # Not used according to docs
            'apps/mergermeter/CODE_REVIEW_FIXES.md',
            'apps/mergermeter/MIGRATION_TO_JASONEDITS.md',
            'apps/mergermeter/CURRENT_STATUS_REPORT.md',
            'apps/mergermeter/DEPLOYMENT_PREPARATION.md',  # Superseded by DEPLOYMENT_PACKAGE.md
        ],
    }
    
    # Delete files
    print("Deleting temporary/unnecessary files...")
    for filename in files_to_delete:
        file_path = repo_root / filename
        if file_path.exists():
            try:
                if file_path.is_dir():
                    shutil.rmtree(file_path)
                else:
                    file_path.unlink()
                print(f"  [DELETED] {filename}")
                deleted_count += 1
            except Exception as e:
                print(f"  [ERROR] Could not delete {filename}: {e}")
        else:
            print(f"  [SKIP] {filename} (not found)")
    
    print()
    
    # Archive files
    print("Archiving old files...")
    for archive_subdir, file_list in files_to_archive.items():
        archive_path = archive_dir / archive_subdir
        for filename in file_list:
            file_path = repo_root / filename
            if file_path.exists():
                try:
                    dest_path = archive_path / file_path.name
                    if file_path.is_dir():
                        shutil.copytree(file_path, dest_path, dirs_exist_ok=True)
                        shutil.rmtree(file_path)
                    else:
                        shutil.move(str(file_path), str(dest_path))
                    print(f"  [ARCHIVED] {filename} -> {archive_subdir}/")
                    archived_count += 1
                except Exception as e:
                    print(f"  [ERROR] Could not archive {filename}: {e}")
            else:
                print(f"  [SKIP] {filename} (not found)")
    
    print()
    
    # Create README in archive
    archive_readme = archive_dir / 'README.md'
    archive_readme.write_text(f"""# Archive - {datetime.now().strftime('%Y-%m-%d')}

This archive contains old files that were removed from the main repository but kept for reference.

## Contents

- **old_test_files/** - Old test scripts and API test files
- **old_docs/** - Old documentation and analysis files
- **old_scripts/** - Old utility scripts and migration scripts
- **old_deployment/** - Old deployment packages
- **legacy_files/** - Legacy application files

## When to Delete This Archive

This archive can be safely deleted after:
- Verifying no files are needed
- Checking that all important information has been migrated
- Confirming no dependencies on archived files

## Files Archived

- Total files archived: {archived_count}
- Total files deleted: {deleted_count}
- Archive date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""")
    
    print("="*70)
    print("Cleanup Summary")
    print("="*70)
    print(f"Files deleted: {deleted_count}")
    print(f"Files archived: {archived_count}")
    print(f"Archive location: {archive_dir}")
    print()
    print("Next steps:")
    print("1. Review the archive to ensure nothing important was removed")
    print("2. Test the applications to ensure everything still works")
    print("3. Delete the archive after confirming everything is OK")
    print("="*70)

if __name__ == '__main__':
    try:
        cleanup_files()
    except Exception as e:
        print(f"\n[ERROR] Cleanup failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

