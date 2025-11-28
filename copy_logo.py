"""Copy NCRC logo to BizSight static directory."""
import shutil
from pathlib import Path

# Use absolute paths to avoid PowerShell issues
source = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Headshots and Other Frequently Used Items\NCRC color FINAL.jpg")
dest_dir = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\DREAM Analysis\#JustData_Repo\apps\bizsight\static\img")

dest_dir.mkdir(parents=True, exist_ok=True)
shutil.copy2(source, dest_dir / 'ncrc-logo.jpg')
shutil.copy2(source, dest_dir / 'ncrc-logo.png')
print(f'✓ Logo copied to {dest_dir}')

