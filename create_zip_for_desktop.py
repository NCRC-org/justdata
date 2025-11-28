#!/usr/bin/env python3
"""
Create MergerMeter deployment ZIP and copy to desktop with all MD files.
"""

import os
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

def main():
    """Create ZIP and copy to desktop."""
    repo_root = Path(__file__).parent.resolve()
    desktop = Path.home() / 'Desktop'
    mergermeter_dir = repo_root / 'apps' / 'mergermeter'
    
    print("Creating MergerMeter deployment package...")
    print(f"Repository: {repo_root}")
    print(f"Desktop: {desktop}")
    print()
    
    # Create temporary package directory
    package_name = f"mergermeter-deployment-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    temp_dir = repo_root / package_name
    temp_dir.mkdir(exist_ok=True)
    
    try:
        # Copy core application files
        print("Copying application files...")
        
        # Copy apps/mergermeter
        dest_mergermeter = temp_dir / 'apps' / 'mergermeter'
        dest_mergermeter.mkdir(parents=True, exist_ok=True)
        
        mergermeter_files = [
            '__init__.py', 'app.py', 'config.py', 'query_builders.py',
            'excel_generator.py', 'hhi_calculator.py', 'branch_assessment_area_generator.py',
            'county_mapper.py', 'statistical_analysis.py', 'version.py',
            'setup_config.py', 'check_config.py'
        ]
        
        for f in mergermeter_files:
            src = mergermeter_dir / f
            if src.exists():
                shutil.copy2(src, dest_mergermeter / f)
                print(f"  Copied: {f}")
        
        # Copy templates and static
        if (mergermeter_dir / 'templates').exists():
            shutil.copytree(mergermeter_dir / 'templates', dest_mergermeter / 'templates', dirs_exist_ok=True)
            print("  Copied: templates/")
        
        if (mergermeter_dir / 'static').exists():
            shutil.copytree(mergermeter_dir / 'static', dest_mergermeter / 'static', dirs_exist_ok=True)
            print("  Copied: static/")
        
        # Copy shared directory
        print("Copying shared dependencies...")
        if (repo_root / 'shared').exists():
            shutil.copytree(repo_root / 'shared', temp_dir / 'shared', dirs_exist_ok=True)
            print("  Copied: shared/")
        
        # Copy entry point
        if (repo_root / 'run_mergermeter.py').exists():
            shutil.copy2(repo_root / 'run_mergermeter.py', temp_dir / 'run_mergermeter.py')
            print("  Copied: run_mergermeter.py")
        
        # Copy requirements
        req_file = mergermeter_dir / 'requirements_mergermeter.txt'
        if req_file.exists():
            shutil.copy2(req_file, temp_dir / 'requirements.txt')
            print("  Copied: requirements.txt")
        
        # Copy all MD files from mergermeter
        print("Copying documentation...")
        for md_file in mergermeter_dir.glob('*.md'):
            if 'DEPLOYMENT' in md_file.name.upper() or 'README' in md_file.name.upper():
                shutil.copy2(md_file, dest_mergermeter / md_file.name)
                print(f"  Copied: {md_file.name}")
        
        # Create output directory
        (dest_mergermeter / 'output').mkdir(exist_ok=True)
        (dest_mergermeter / 'output' / '.gitkeep').touch()
        
        # Create credentials directory
        (temp_dir / 'credentials').mkdir(exist_ok=True)
        (temp_dir / 'credentials' / 'README.txt').write_text(
            "Place your GCP credentials JSON file here.\n"
            "Then update .env file with: GOOGLE_APPLICATION_CREDENTIALS=./credentials/your-file.json\n"
        )
        
        # Create ZIP file
        print("\nCreating ZIP file...")
        zip_path = repo_root / f"{package_name}.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_dir):
                dirs[:] = [d for d in dirs if d != '__pycache__']
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(temp_dir)
                    zipf.write(file_path, arcname)
        
        zip_size = zip_path.stat().st_size / 1024 / 1024
        print(f"  Created: {zip_path.name} ({zip_size:.2f} MB)")
        
        # Copy ZIP to desktop
        desktop_zip = desktop / zip_path.name
        shutil.copy2(zip_path, desktop_zip)
        print(f"\nCopied ZIP to desktop: {desktop_zip.name}")
        
        # Copy all MD files from mergermeter to desktop
        print("\nCopying MD files to desktop...")
        md_count = 0
        for md_file in mergermeter_dir.glob('*.md'):
            if 'DEPLOYMENT' in md_file.name.upper() or 'README' in md_file.name.upper() or 'SUMMARY' in md_file.name.upper():
                desktop_md = desktop / md_file.name
                shutil.copy2(md_file, desktop_md)
                print(f"  Copied: {md_file.name}")
                md_count += 1
        
        # Copy requirements file
        if req_file.exists():
            desktop_req = desktop / req_file.name
            shutil.copy2(req_file, desktop_req)
            print(f"  Copied: {req_file.name}")
        
        print(f"\n{'='*70}")
        print("SUCCESS!")
        print(f"{'='*70}")
        print(f"ZIP file: {desktop_zip.name} ({zip_size:.2f} MB)")
        print(f"MD files copied: {md_count + 1}")
        print(f"\nAll files are on your desktop!")
        print(f"{'='*70}")
        
    finally:
        # Clean up temp directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            print(f"\nCleaned up temporary directory")

if __name__ == '__main__':
    main()

