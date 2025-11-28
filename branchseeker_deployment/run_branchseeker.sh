#!/bin/bash
cd "$(dirname "$0")"
echo "Starting BranchSeeker..."
echo "Access at: http://localhost:8083"
python3 -m apps.branchseeker.app
