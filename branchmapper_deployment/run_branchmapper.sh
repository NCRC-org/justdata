#!/bin/bash
cd "$(dirname "$0")"
echo "Starting BranchMapper..."
echo "Access at: http://localhost:8084"
python3 -m apps.branchmapper.app
