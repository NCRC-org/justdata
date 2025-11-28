import shutil
from pathlib import Path

src = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Headshots and Other Frequently Used Items\NCRC color FINAL.jpg")
dst_dir = Path('apps/bizsight/static/img')
dst_dir.mkdir(parents=True, exist_ok=True)
shutil.copy2(src, dst_dir / 'ncrc-logo.jpg')
shutil.copy2(src, dst_dir / 'ncrc-logo.png')
print('Logo copied successfully')

