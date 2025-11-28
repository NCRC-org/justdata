# How to Start Applications in Cursor

## Quick Start

Just ask me (Auto) to start an application! For example:
- "Start LendSight"
- "Start BranchSeeker"
- "Start BranchMapper"
- "Start MergerMeter"
- "Start both applications"

I'll run the commands for you.

## Manual Start (if needed)

### Start BranchSeeker
```bash
python run_branchseeker.py
```
Then open: **http://127.0.0.1:8080**

### Start BranchMapper
```bash
python run_branchmapper.py
```
Then open: **http://127.0.0.1:8084**

### Start LendSight
```bash
python run_lendsight.py
```
Then open: **http://127.0.0.1:8082**

### Start MergerMeter
```bash
python run_mergermeter.py
```
Then open: **http://127.0.0.1:8083**

### Start Multiple Apps (in separate terminals)
1. Terminal 1: `python run_lendsight.py` (Port 8082)
2. Terminal 2: `python run_branchseeker.py` (Port 8080)
3. Terminal 3: `python run_branchmapper.py` (Port 8084)
4. Terminal 4: `python run_mergermeter.py` (Port 8083)

## What You'll See

### BranchSeeker (Port 8080)
- **Main Page**: http://127.0.0.1:8080/
  - Analysis form for bank branch data
  - Select counties, years, generate reports
  - Excel export of analysis tables

### BranchMapper (Port 8084)
- **Main Page**: http://127.0.0.1:8084/
  - Interactive map of bank branches
  - Select state/county, view branches on map
  - Export map and data

### LendSight (Port 8082)
- **Main Page**: http://127.0.0.1:8082/
  - Mortgage lending analysis
  - HMDA data analysis
  - Generate member reports

### MergerMeter (Port 8083)
- **Main Page**: http://127.0.0.1:8083/
  - Two-bank merger impact analysis
  - Community benefits analysis
  - Assessment area mapping

## Tips

- The server will keep running until you press `Ctrl+C`
- You can run both apps simultaneously on different ports
- Changes to code require restarting the server
- Check terminal output for any errors

## Troubleshooting

**Port already in use?**
- Another instance might be running
- Check Task Manager for Python processes
- Or use different ports by setting `PORT` environment variable

**Module not found?**
- Make sure you're in the project root directory
- Install dependencies: `pip install -r requirements.txt`

**Can't connect?**
- Make sure the server started successfully
- Check the terminal for error messages
- Verify the port number matches the URL

