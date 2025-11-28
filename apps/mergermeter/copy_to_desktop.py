#!/usr/bin/env python3
"""
Package MergerMeter and copy deployment files to desktop.
"""

import os
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

def get_project_root():
    """Get the project root directory."""
    script_path = Path(__file__).resolve()
    return script_path.parent.parent.parent

def create_deployment_package():
    """Create a deployment package ZIP file."""
    project_root = get_project_root()
    package_name = f"mergermeter-deployment-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    package_dir = project_root / package_name
    package_zip = project_root / f"{package_name}.zip"
    
    print(f"Creating deployment package: {package_name}")
    print(f"Project root: {project_root}")
    
    # Create package directory
    package_dir.mkdir(exist_ok=True)
    
    # Files and directories to include
    includes = {
        # Core application
        'apps/mergermeter/__init__.py': 'apps/mergermeter/',
        'apps/mergermeter/app.py': 'apps/mergermeter/',
        'apps/mergermeter/config.py': 'apps/mergermeter/',
        'apps/mergermeter/query_builders.py': 'apps/mergermeter/',
        'apps/mergermeter/excel_generator.py': 'apps/mergermeter/',
        'apps/mergermeter/hhi_calculator.py': 'apps/mergermeter/',
        'apps/mergermeter/branch_assessment_area_generator.py': 'apps/mergermeter/',
        'apps/mergermeter/county_mapper.py': 'apps/mergermeter/',
        'apps/mergermeter/statistical_analysis.py': 'apps/mergermeter/',
        'apps/mergermeter/version.py': 'apps/mergermeter/',
        'apps/mergermeter/setup_config.py': 'apps/mergermeter/',
        'apps/mergermeter/check_config.py': 'apps/mergermeter/',
        
        # Templates
        'apps/mergermeter/templates': 'apps/mergermeter/',
        'apps/mergermeter/static': 'apps/mergermeter/',
        
        # Shared dependencies
        'shared': 'shared/',
        
        # Entry point
        'run_mergermeter.py': '',
        
        # Documentation
        'apps/mergermeter/README.md': 'apps/mergermeter/',
        'apps/mergermeter/ASSESSMENT_AREA_FORMAT.md': 'apps/mergermeter/',
        'apps/mergermeter/BIGQUERY_DATASETS.md': 'apps/mergermeter/',
        'apps/mergermeter/HHI_CALCULATION_GUIDE.md': 'apps/mergermeter/',
        'apps/mergermeter/DEPLOYMENT_PACKAGE.md': 'apps/mergermeter/',
        'apps/mergermeter/DEPLOYMENT_README.md': 'apps/mergermeter/',
        'apps/mergermeter/DEPLOYMENT_SUMMARY.md': 'apps/mergermeter/',
        
        # Configuration templates
        'apps/mergermeter/requirements_mergermeter.txt': 'requirements.txt',
    }
    
    # Copy files
    copied_count = 0
    skipped_count = 0
    
    for source, dest_dir in includes.items():
        source_path = project_root / source
        if not source_path.exists():
            print(f"  [SKIP] Skipping (not found): {source}")
            skipped_count += 1
            continue
        
        dest_path = package_dir / dest_dir / source_path.name if dest_dir else package_dir / source_path.name
        
        # Create destination directory
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            if source_path.is_dir():
                # Copy directory
                shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
                print(f"  [OK] Copied directory: {source}")
            else:
                # Copy file
                shutil.copy2(source_path, dest_path)
                print(f"  [OK] Copied file: {source}")
            copied_count += 1
        except Exception as e:
            print(f"  [ERROR] Error copying {source}: {e}")
            skipped_count += 1
    
    # Create output directory
    output_dir = package_dir / 'apps' / 'mergermeter' / 'output'
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / '.gitkeep').touch()
    print(f"  [OK] Created output directory")
    
    # Create credentials directory placeholder
    creds_dir = package_dir / 'credentials'
    creds_dir.mkdir(exist_ok=True)
    (creds_dir / 'README.txt').write_text(
        "Place your GCP credentials JSON file here.\n"
        "Then update .env file with: GOOGLE_APPLICATION_CREDENTIALS=./credentials/your-file.json\n"
    )
    print(f"  [OK] Created credentials directory")
    
    # Create deployment README in root
    deployment_readme = package_dir / 'DEPLOYMENT_README.md'
    if not deployment_readme.exists():
        source_readme = project_root / 'apps' / 'mergermeter' / 'DEPLOYMENT_README.md'
        if source_readme.exists():
            shutil.copy2(source_readme, deployment_readme)
    
    # Create .gitignore
    gitignore = package_dir / '.gitignore'
    gitignore.write_text(
        "# Environment files\n"
        ".env\n"
        "\n"
        "# Credentials\n"
        "credentials/*.json\n"
        "credentials/*.key\n"
        "\n"
        "# Output files\n"
        "apps/mergermeter/output/*\n"
        "!apps/mergermeter/output/.gitkeep\n"
        "\n"
        "# Python\n"
        "__pycache__/\n"
        "*.pyc\n"
        "*.pyo\n"
        "*.pyd\n"
        ".Python\n"
        "venv/\n"
        "env/\n"
        ".venv/\n"
    )
    print(f"  [OK] Created .gitignore")
    
    # Create ZIP file
    print(f"\nCreating ZIP file...")
    with zipfile.ZipFile(package_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_dir):
            # Skip __pycache__ directories
            dirs[:] = [d for d in dirs if d != '__pycache__']
            
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(package_dir)
                zipf.write(file_path, arcname)
    
    # Clean up package directory
    print(f"\nCleaning up temporary directory...")
    shutil.rmtree(package_dir)
    
    print(f"\n[SUCCESS] Deployment package created: {package_zip}")
    return package_zip

def copy_to_desktop():
    """Copy deployment ZIP and all MD files to desktop."""
    project_root = get_project_root()
    desktop = Path.home() / 'Desktop'
    mergermeter_dir = project_root / 'apps' / 'mergermeter'
    
    print(f"\n{'='*70}")
    print(f"Copying files to desktop...")
    print(f"Desktop: {desktop}")
    print(f"{'='*70}")
    
    # Create deployment ZIP
    zip_file = create_deployment_package()
    
    # Copy ZIP to desktop
    desktop_zip = desktop / zip_file.name
    shutil.copy2(zip_file, desktop_zip)
    print(f"\n[OK] Copied ZIP to desktop: {desktop_zip.name}")
    
    # Copy all MD files from mergermeter directory
    md_files = list(mergermeter_dir.glob('*.md'))
    deployment_files = []
    
    for md_file in md_files:
        if 'DEPLOYMENT' in md_file.name.upper() or 'README' in md_file.name.upper():
            desktop_md = desktop / md_file.name
            shutil.copy2(md_file, desktop_md)
            deployment_files.append(md_file.name)
            print(f"[OK] Copied: {md_file.name}")
    
    # Copy requirements file
    req_file = mergermeter_dir / 'requirements_mergermeter.txt'
    if req_file.exists():
        desktop_req = desktop / req_file.name
        shutil.copy2(req_file, desktop_req)
        deployment_files.append(req_file.name)
        print(f"[OK] Copied: {req_file.name}")
    
    # Copy packaging script
    package_script = mergermeter_dir / 'package_deployment.py'
    if package_script.exists():
        desktop_script = desktop / package_script.name
        shutil.copy2(package_script, desktop_script)
        deployment_files.append(package_script.name)
        print(f"[OK] Copied: {package_script.name}")
    
    print(f"\n{'='*70}")
    print(f"[SUCCESS] All files copied to desktop!")
    print(f"{'='*70}")
    print(f"\nFiles on desktop:")
    print(f"  - {desktop_zip.name} ({desktop_zip.stat().st_size / 1024 / 1024:.2f} MB)")
    for f in deployment_files:
        print(f"  - {f}")
    print(f"\nTotal files: {len(deployment_files) + 1}")
    print(f"{'='*70}")

if __name__ == '__main__':
    try:
        copy_to_desktop()
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

