# Setting Up Windows Task Scheduler for Automatic Version Updates

This guide walks you through setting up Windows Task Scheduler to automatically run the version update script every 12 hours.

## Prerequisites

1. Make sure Python is installed and accessible from the command line
2. Know the full path to your project (e.g., `C:\DREAM\justdata`)
3. Have administrator privileges (may be needed for some settings)

## Step-by-Step Instructions

### Step 1: Open Task Scheduler

1. Press `Windows Key + R` to open the Run dialog
2. Type `taskschd.msc` and press Enter
   - OR search for "Task Scheduler" in the Start menu
   - OR go to Control Panel → Administrative Tools → Task Scheduler

### Step 2: Create a New Task

1. In the right panel, click **"Create Task"** (not "Create Basic Task")
   - "Create Basic Task" is simpler but has fewer options
   - "Create Task" gives you more control

### Step 3: General Tab Settings

1. **Name**: Enter `BranchSeeker Version Update`
2. **Description**: Enter `Automatically updates version.py from CHANGELOG.json every 12 hours`
3. **Security options**:
   - ✅ Check **"Run whether user is logged on or not"**
   - Select **"Run with highest privileges"** (if you have admin rights)
   - **Configure for**: Select your Windows version (usually "Windows 10" or "Windows 11")

### Step 4: Triggers Tab

1. Click the **"Triggers"** tab
2. Click **"New..."** button
3. Configure the trigger:
   - **Begin the task**: Select **"At startup"** (this starts the 12-hour cycle)
   - ✅ Check **"Repeat task every"**
   - Set to **12 hours**
   - **For a duration of**: Select **"Indefinitely"**
   - ✅ Check **"Enabled"**
4. Click **"OK"**

### Step 5: Actions Tab

1. Click the **"Actions"** tab
2. Click **"New..."** button
3. Configure the action:
   - **Action**: Select **"Start a program"**
   - **Program/script**: Enter the full path to Python
     - Common locations:
       - `C:\Users\YourUsername\AppData\Local\Programs\Python\Python39\python.exe`
       - `C:\Python39\python.exe`
       - `C:\Program Files\Python39\python.exe`
     - **To find your Python path**: Open Command Prompt and type `where python`
   - **Add arguments (optional)**: Enter the full path to the script:
     ```
     C:\DREAM\justdata\apps\branchseeker\update_version.py
     ```
   - **Start in (optional)**: Enter the project root:
     ```
     C:\DREAM\justdata
     ```
4. Click **"OK"**

### Step 6: Conditions Tab (Optional)

1. Click the **"Conditions"** tab
2. Uncheck **"Start the task only if the computer is on AC power"** (if you want it to run on battery)
3. Uncheck **"Start the task only if the following network connection is available"** (unless you need network)
4. Leave other settings as default

### Step 7: Settings Tab

1. Click the **"Settings"** tab
2. Recommended settings:
   - ✅ Check **"Allow task to be run on demand"**
   - ✅ Check **"Run task as soon as possible after a scheduled start is missed"**
   - ✅ Check **"If the task fails, restart every"** - Set to `1 hour` (optional, for retry)
   - **Stop the task if it runs longer than**: Leave unchecked or set to `1 hour`
   - **If the running task does not end when requested, force it to stop**: ✅ Check this

### Step 8: Save and Test

1. Click **"OK"** to save the task
2. You may be prompted for your Windows password (if "Run whether user is logged on or not" is selected)
3. **Test the task**:
   - Right-click on your task in the Task Scheduler Library
   - Select **"Run"**
   - Check the "Last Run Result" column - it should show `(0x0)` if successful

### Step 9: Verify It's Working

1. In Task Scheduler, find your task in the list
2. Check the **"Last Run Time"** and **"Next Run Time"** columns
3. To see detailed logs:
   - Right-click the task → **"History"** tab
   - Or go to **"View"** menu → **"Show All Tasks History"**

## Alternative: Using Command Line (PowerShell as Administrator)

If you prefer command line, you can create the task using PowerShell:

```powershell
# Run PowerShell as Administrator
$action = New-ScheduledTaskAction -Execute "python" -Argument "C:\DREAM\justdata\apps\branchseeker\update_version.py" -WorkingDirectory "C:\DREAM\justdata"
$trigger = New-ScheduledTaskTrigger -AtStartup -RepetitionInterval (New-TimeSpan -Hours 12) -RepetitionDuration (New-TimeSpan -Days 365)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType S4U -RunLevel Highest

Register-ScheduledTask -TaskName "BranchSeeker Version Update" -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Automatically updates version.py from CHANGELOG.json every 12 hours"
```

## Troubleshooting

### Task doesn't run
1. Check Task Scheduler → Task Scheduler Library → Your task → History tab
2. Look for error messages
3. Common issues:
   - Python path is incorrect → Use `where python` to find correct path
   - Script path is incorrect → Use full absolute path
   - Permissions issue → Try running Task Scheduler as Administrator

### Task runs but doesn't update version
1. Check if `CHANGELOG.json` was actually modified in the last 12 hours
2. Run the script manually to see error messages:
   ```cmd
   cd C:\DREAM\justdata
   python apps\branchseeker\update_version.py
   ```
3. Check file permissions - the script needs write access to `version.py`

### Task runs too frequently or not frequently enough
1. Right-click task → Properties → Triggers tab
2. Edit the trigger and adjust the "Repeat task every" setting

## Manual Testing

To test the script manually before scheduling:

```cmd
cd C:\DREAM\justdata
python apps\branchseeker\update_version.py --check-only
```

This will show you if an update is needed without making changes.

## Disabling/Removing the Task

- **Disable**: Right-click task → Disable
- **Delete**: Right-click task → Delete
- **Edit**: Right-click task → Properties



