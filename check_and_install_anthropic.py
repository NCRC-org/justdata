#!/usr/bin/env python3
"""Check if anthropic module is installed, install if missing."""

import subprocess
import sys

def check_and_install():
    """Check for anthropic module and install if missing."""
    print("=" * 60)
    print("Checking anthropic module installation")
    print("=" * 60)
    print()
    
    # Try to import anthropic
    try:
        import anthropic
        print(f"✅ anthropic module is installed")
        try:
            version = anthropic.__version__
            print(f"   Version: {version}")
        except AttributeError:
            print("   Version: (unknown)")
        print()
        return True
    except ImportError:
        print("❌ anthropic module is NOT installed")
        print()
        print("Installing anthropic module...")
        print()
        
        # Install using pip
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "anthropic>=0.7.0"],
                stdout=sys.stdout,
                stderr=sys.stderr
            )
            print()
            print("✅ anthropic module installed successfully!")
            print()
            
            # Verify installation
            try:
                import anthropic
                print("✅ Verification: anthropic module can now be imported")
                return True
            except ImportError:
                print("❌ Verification failed: anthropic module still cannot be imported")
                return False
                
        except subprocess.CalledProcessError as e:
            print()
            print(f"❌ Failed to install anthropic module")
            print(f"   Error: {e}")
            return False
        except Exception as e:
            print()
            print(f"❌ Unexpected error during installation")
            print(f"   Error: {e}")
            return False

if __name__ == "__main__":
    success = check_and_install()
    sys.exit(0 if success else 1)

