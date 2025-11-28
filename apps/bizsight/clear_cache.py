#!/usr/bin/env python3
"""
Clear Flask and Python caches to force reload of templates and code.
"""

import os
import shutil
from pathlib import Path

def clear_pycache():
    """Remove all __pycache__ directories."""
    repo_root = Path(__file__).parent.parent.parent
    bizsight_dir = Path(__file__).parent
    
    print("=" * 80)
    print("CLEARING PYTHON BYTECODE CACHE")
    print("=" * 80)
    
    removed_count = 0
    for pycache_dir in bizsight_dir.rglob('__pycache__'):
        if pycache_dir.is_dir():
            print(f"  Removing: {pycache_dir}")
            shutil.rmtree(pycache_dir)
            removed_count += 1
    
    # Also check for .pyc files
    for pyc_file in bizsight_dir.rglob('*.pyc'):
        print(f"  Removing: {pyc_file}")
        pyc_file.unlink()
        removed_count += 1
    
    print(f"\n✓ Removed {removed_count} cache directories/files")
    return removed_count


def verify_debug_mode():
    """Verify DEBUG mode is enabled."""
    print("\n" + "=" * 80)
    print("VERIFYING DEBUG MODE")
    print("=" * 80)
    
    debug_env = os.getenv('DEBUG', 'False')
    debug_value = debug_env.lower() == 'true'
    
    print(f"DEBUG environment variable: {debug_env}")
    print(f"DEBUG mode enabled: {debug_value}")
    
    if not debug_value:
        print("\n⚠ WARNING: DEBUG mode is disabled!")
        print("  Flask will NOT auto-reload templates and code changes.")
        print("  To enable, set environment variable: DEBUG=True")
        print("  Or run: $env:DEBUG='True' (PowerShell)")
        print("  Or run: set DEBUG=True (CMD)")
    
    return debug_value


def main():
    """Main function."""
    print("\n" + "=" * 80)
    print("FLASK CACHE CLEARING UTILITY")
    print("=" * 80)
    print()
    
    # Clear Python cache
    cache_count = clear_pycache()
    
    # Verify DEBUG mode
    debug_enabled = verify_debug_mode()
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"✓ Cleared {cache_count} cache items")
    print(f"{'✓' if debug_enabled else '⚠'} DEBUG mode: {'ENABLED' if debug_enabled else 'DISABLED'}")
    
    if not debug_enabled:
        print("\n⚠ IMPORTANT: Enable DEBUG mode for development!")
        print("  PowerShell: $env:DEBUG='True'")
        print("  Then restart the Flask server.")
    
    print("\n✓ Cache clearing complete. Restart Flask server to apply changes.")
    print()


if __name__ == '__main__':
    main()

