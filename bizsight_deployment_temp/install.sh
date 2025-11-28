#!/bin/bash
echo "========================================"
echo "BizSight Installation Script"
echo "========================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 not found!"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

echo "[1/3] Checking Python version..."
python3 --version

echo ""
echo "[2/3] Installing Python packages..."
pip3 install --upgrade pip
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to upgrade pip"
    exit 1
fi

pip3 install -r apps/bizsight/requirements.txt
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install dependencies"
    exit 1
fi

echo ""
echo "[3/3] Installing Playwright browser..."
playwright install chromium
if [ $? -ne 0 ]; then
    echo "[WARNING] Playwright installation failed. PDF export may not work."
fi

echo ""
echo "========================================"
echo "Installation Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Copy .env.example to .env"
echo "2. Edit .env and add your API keys"
echo "3. Place bigquery_service_account.json in credentials/ directory"
echo "4. Run: ./run_bizsight.sh"
echo ""
