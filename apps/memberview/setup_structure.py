"""Create directory structure for MemberView application."""
import os
from pathlib import Path

def create_structure():
    """Create all necessary directories."""
    base = Path(__file__).parent
    
    directories = [
        "app",
        "config",
        "utils",
        "web/templates",
        "web/static/css",
        "web/static/js",
        "web/static/img",
        "data/reports",
        "data/exports",
        "credentials",
        "docs"
    ]
    
    for dir_path in directories:
        full_path = base / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        print(f"Created: {full_path}")
    
    # Create __init__.py files
    init_files = [
        "app/__init__.py",
        "config/__init__.py",
        "utils/__init__.py",
    ]
    
    for init_file in init_files:
        full_path = base / init_file
        full_path.touch()
        print(f"Created: {full_path}")
    
    # Create .gitkeep in credentials
    (base / "credentials" / ".gitkeep").touch()
    print(f"Created: {base / 'credentials' / '.gitkeep'}")
    
    print("\nDirectory structure created successfully!")

if __name__ == "__main__":
    create_structure()

