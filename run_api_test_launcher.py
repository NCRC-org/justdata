"""Launcher for API test - uses subprocess with shell=False to bypass PowerShell"""
import subprocess
import sys
from pathlib import Path

def run_api_test():
    """Run the API test script using subprocess with shell=False to bypass PowerShell."""
    # Get the script path
    script_path = Path(__file__).parent / "execute_inline.py"
    
    if not script_path.exists():
        print(f"ERROR: Script not found: {script_path}")
        sys.exit(1)
    
    # Get the Python executable
    python_exe = sys.executable
    
    # Build command list - use list, not string, to avoid shell interpretation
    cmd = [python_exe, str(script_path)]
    
    print("="*80)
    print("Running ProPublica API Test")
    print("="*80)
    print(f"Python: {python_exe}")
    print(f"Script: {script_path}")
    print("="*80)
    print()
    
    try:
        # Use subprocess with shell=False to bypass PowerShell entirely
        result = subprocess.run(
            cmd,
            shell=False,  # Critical: shell=False bypasses PowerShell wrapper
            check=False,
            capture_output=False,  # Show output in real-time
            text=True
        )
        
        print()
        print("="*80)
        print(f"Script completed with exit code: {result.returncode}")
        print("="*80)
        
        if result.returncode != 0:
            sys.exit(result.returncode)
            
    except Exception as e:
        print(f"ERROR: Could not execute script: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_api_test()

