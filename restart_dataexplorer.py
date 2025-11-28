#!/usr/bin/env python3
"""
Restart DataExplorer server with proper environment setup.
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def kill_existing_server(port=8085):
    """Kill any existing server on the port."""
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name', 'connections']):
            try:
                if proc.info['name'] and 'python' in proc.info['name'].lower():
                    for conn in proc.info['connections'] or []:
                        if conn.laddr.port == port:
                            print(f"Killing process {proc.info['pid']} on port {port}")
                            proc.kill()
                            time.sleep(1)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    except ImportError:
        print("psutil not available, skipping process kill")
    except Exception as e:
        print(f"Error killing processes: {e}")

def check_env_vars():
    """Check if required environment variables are set."""
    repo_root = Path(__file__).parent.absolute()
    
    # Try to load .env file
    try:
        from dotenv import load_dotenv
        # Try loading from parent DREAM Analysis directory
        dream_analysis_env = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\DREAM Analysis\.env")
        if dream_analysis_env.exists():
            load_dotenv(dream_analysis_env, override=False)
            print(f"✓ Loaded .env from: {dream_analysis_env}")
        else:
            # Try current directory
            env_file = repo_root / '.env'
            if env_file.exists():
                load_dotenv(env_file)
                print(f"✓ Loaded .env from: {env_file}")
    except ImportError:
        print("⚠ python-dotenv not available, skipping .env load")
    
    # Check CENSUS_API_KEY
    census_key = os.getenv('CENSUS_API_KEY')
    if census_key:
        print(f"✓ CENSUS_API_KEY is set (length: {len(census_key)})")
    else:
        print("⚠ CENSUS_API_KEY is NOT set - Census data will not be available")
        print("  Set it in your .env file or environment variables")
    
    # Check other important vars
    gcp_project = os.getenv('GCP_PROJECT_ID')
    if gcp_project:
        print(f"✓ GCP_PROJECT_ID is set: {gcp_project}")
    else:
        print("⚠ GCP_PROJECT_ID is not set")
    
    return census_key is not None

def start_server():
    """Start the DataExplorer server."""
    repo_root = Path(__file__).parent.absolute()
    
    print("\n" + "=" * 80)
    print("STARTING DATAEXPLORER SERVER")
    print("=" * 80)
    print(f"Working directory: {repo_root}")
    print(f"Python: {sys.executable}")
    print("=" * 80 + "\n")
    
    # Change to repo root
    os.chdir(repo_root)
    
    # Start server
    try:
        subprocess.run([sys.executable, 'run_dataexplorer.py'], check=False, cwd=repo_root)
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
    except Exception as e:
        print(f"\n✗ Error starting server: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=" * 80)
    print("RESTARTING DATAEXPLORER SERVER")
    print("=" * 80)
    
    # Kill existing server
    print("\n1. Checking for existing server...")
    kill_existing_server(8085)
    time.sleep(2)
    
    # Check environment
    print("\n2. Checking environment variables...")
    env_ok = check_env_vars()
    
    if not env_ok:
        print("\n⚠ WARNING: CENSUS_API_KEY is not set!")
        print("   Census tract data will not be available.")
        response = input("\nContinue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Exiting...")
            sys.exit(1)
    
    # Start server
    print("\n3. Starting server...")
    start_server()

