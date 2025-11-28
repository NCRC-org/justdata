#!/bin/bash
# Linux/Mac shell script to update version from changelog
# Usage: ./update_version.sh [--check-only] [--force]

cd "$(dirname "$0")"
python3 update_version.py "$@"

