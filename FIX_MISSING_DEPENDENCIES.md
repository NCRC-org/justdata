# Fix Missing Dependencies

## Issue

The applications are failing to start because required Python packages are not installed:
- `flask` - Web framework
- `dotenv` (python-dotenv) - Environment variable loading

## Solution

### Option 1: Install and Start Everything (Recommended)

Run this batch file to install all dependencies and start all servers:
```cmd
INSTALL_AND_START_ALL.bat
```

### Option 2: Install Dependencies First, Then Start

**Step 1:** Install all dependencies
```cmd
INSTALL_DEPENDENCIES.bat
```

**Step 2:** Start all servers
```cmd
START_ALL_SERVERS.bat
```

### Option 3: Manual Installation

Install dependencies manually:
```cmd
pip install flask python-dotenv pandas google-cloud-bigquery openpyxl anthropic openai numpy
```

Or install from requirements.txt:
```cmd
pip install -r requirements.txt
```

## Required Packages

The applications need these packages (from requirements.txt):

**Core:**
- flask>=2.3.0
- python-dotenv
- pandas>=1.5.0
- numpy>=1.21.0

**Cloud Services:**
- google-cloud-bigquery>=3.0.0
- anthropic>=0.7.0 (Claude API)
- openai>=1.0.0

**Reporting:**
- openpyxl>=3.0.0 (Excel files)
- playwright>=1.40.0 (PDF generation)

**Other:**
- requests
- user-agents>=2.2.0

## After Installation

Once dependencies are installed, you can start the servers:
```cmd
START_ALL_SERVERS.bat
```

Or start individually:
```cmd
python run_branchseeker.py
python run_lendsight.py
python run_mergermeter.py
python run_branchmapper.py
```

