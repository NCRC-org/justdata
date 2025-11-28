#!/bin/bash
echo "Installing BranchMapper Dependencies..."
echo

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

# Install dependencies
echo "Installing Python packages..."
pip3 install --upgrade pip
pip3 install -r apps/branchmapper/requirements.txt

echo
echo "Installation complete!"
echo
echo "Next steps:"
echo "1. Copy .env.example to .env and fill in your API keys"
echo "2. Place bigquery_service_account.json in credentials/ directory"
echo "3. Set CENSUS_API_KEY in .env file"
echo "4. Run: python3 -m apps.branchmapper.app
echo
