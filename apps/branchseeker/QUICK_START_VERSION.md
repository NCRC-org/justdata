# Quick Start: Version Management

## Simple Workflow

1. **Make your code changes**

2. **Update CHANGELOG.json** - Add a new version entry at the top:
   ```json
   {
     "versions": [
       {
         "version": "1.0.1",
         "date": "2025-01-28",
         "changes": [
           "Fixed summary cards",
           "Added new feature"
         ]
       },
       ...existing versions...
     ]
   }
   ```

3. **Run the update script**:
   ```bash
   python apps/branchseeker/update_version.py
   ```

   Or on Windows:
   ```cmd
   apps\branchseeker\update_version.bat
   ```

4. **Done!** The version in `version.py` is now updated and will appear in the footer.

## Automatic Updates (Every 12 Hours)

The script checks if `CHANGELOG.json` was modified in the last 12 hours. If it was, it automatically updates `version.py`.

### Windows Task Scheduler

1. Open Task Scheduler
2. Create Task → General tab:
   - Name: "BranchSeeker Version Update"
   - Run whether user is logged on or not
3. Triggers tab → New:
   - Begin: At startup
   - Repeat task every: 12 hours
4. Actions tab → New:
   - Action: Start a program
   - Program: `python`
   - Arguments: `C:\DREAM\justdata\apps\branchseeker\update_version.py`
   - Start in: `C:\DREAM\justdata`

### Manual Check

To check if an update is needed:
```bash
python apps/branchseeker/update_version.py --check-only
```

To force update (ignore 12-hour check):
```bash
python apps/branchseeker/update_version.py --force
```

