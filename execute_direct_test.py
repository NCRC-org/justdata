"""Execute the API test directly"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and execute the test
try:
    # Read and execute the direct_api_test script
    with open('direct_api_test.py', 'r', encoding='utf-8') as f:
        code = f.read()
    
    # Execute it
    exec(code)
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

