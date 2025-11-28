#!/usr/bin/env python3
"""
MemberView Application Entry Point

Self-contained member management application for NCRC.
"""

import os
import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
BASE_DIR = Path(__file__).parent
JUSTDATA_BASE = BASE_DIR.parent.parent
sys.path.insert(0, str(JUSTDATA_BASE))
sys.path.insert(0, str(BASE_DIR))  # Also add current directory for relative imports

# Import app - try relative first (when running from memberview dir), then absolute
try:
    from app import create_app
except ImportError:
    from apps.memberview.app import create_app

def main():
    """Main entry point for MemberView."""
    parser = argparse.ArgumentParser(description='MemberView - NCRC Member Management')
    parser.add_argument('--port', type=int, default=None, help='Port to run on (default: from env or 8082)')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Host to bind to (default: 127.0.0.1)')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    
    args = parser.parse_args()
    
    # Create Flask app
    app = create_app()
    
    # Get port from args, env, or default
    port = args.port or int(os.getenv('PORT', 8082))
    debug = args.debug or os.getenv('DEBUG', 'False').lower() == 'true'
    
    print("=" * 60)
    print("MemberView - NCRC Member Management")
    print("=" * 60)
    print(f"Starting server on http://{args.host}:{port}")
    print(f"Debug mode: {debug}")
    print("=" * 60)
    print()
    
    try:
        app.run(host=args.host, port=port, debug=debug)
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)

if __name__ == "__main__":
    main()

