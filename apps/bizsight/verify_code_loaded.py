#!/usr/bin/env python3
"""
Verify that the updated code is actually loaded by checking for the bytecode_cache fix.
"""

import sys
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(REPO_ROOT))

# Import the app module
try:
    from apps.bizsight import app as bizsight_app
    
    print("=" * 80)
    print("VERIFYING CODE IS LOADED")
    print("=" * 80)
    
    # Check if bytecode_cache is disabled
    if hasattr(bizsight_app.app, 'jinja_env'):
        bytecode_cache = bizsight_app.app.jinja_env.bytecode_cache
        print(f"\n✓ Jinja2 bytecode_cache: {bytecode_cache}")
        if bytecode_cache is None:
            print("  ✓ Bytecode cache is DISABLED (correct)")
        else:
            print("  ✗ Bytecode cache is ENABLED (incorrect - code not loaded)")
        
        auto_reload = bizsight_app.app.jinja_env.auto_reload
        print(f"✓ Jinja2 auto_reload: {auto_reload}")
        
        templates_auto_reload = bizsight_app.app.config.get('TEMPLATES_AUTO_RELOAD')
        print(f"✓ Flask TEMPLATES_AUTO_RELOAD: {templates_auto_reload}")
        
        debug_mode = bizsight_app.app.config.get('DEBUG')
        print(f"✓ Flask DEBUG mode: {debug_mode}")
    else:
        print("✗ jinja_env not found on app")
    
    print("\n" + "=" * 80)
    print("VERIFICATION COMPLETE")
    print("=" * 80)
    
except Exception as e:
    print(f"✗ Error importing app: {e}")
    import traceback
    traceback.print_exc()

