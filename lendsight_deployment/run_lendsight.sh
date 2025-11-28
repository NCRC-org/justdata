#!/bin/bash
cd "$(dirname "$0")"
echo "Starting LendSight..."
echo "Access at: http://localhost:8082"
python3 -m apps.lendsight.app
