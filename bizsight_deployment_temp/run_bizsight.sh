#!/bin/bash
cd "$(dirname "$0")"
echo "========================================"
echo "Starting BizSight Application"
echo "========================================"
echo ""
echo "Access the application at: http://localhost:8081"
echo "Press Ctrl+C to stop the server"
echo ""
python3 -m apps.bizsight.app
