import subprocess
import sys
import os

# Change to script directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# Run the API test script
try:
    result = subprocess.run(
        [sys.executable, 'run_api_test.py'],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    print("STDOUT:")
    print(result.stdout)
    
    if result.stderr:
        print("\nSTDERR:")
        print(result.stderr)
    
    print(f"\nReturn code: {result.returncode}")
    
    # Also try to read the output file if it was created
    if os.path.exists('api_test_output.txt'):
        print("\n" + "="*80)
        print("READING FROM OUTPUT FILE:")
        print("="*80)
        with open('api_test_output.txt', 'r', encoding='utf-8') as f:
            print(f.read())
    
except Exception as e:
    print(f"Error running script: {e}")
    import traceback
    traceback.print_exc()

