# MergerMeter Migration to JasonEdits Branch - Manual Steps

Since the terminal tool has PowerShell issues with apostrophes in paths, use one of these methods:

## Method 1: Use the Batch File (Recommended)

1. Open **Command Prompt** (cmd.exe) directly (not through Cursor)
2. Navigate to the #JustData_Repo directory:
   ```cmd
   cd "C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\DREAM Analysis\#JustData_Repo"
   ```
3. Run the batch file:
   ```cmd
   move_mergermeter_to_jasonedits.bat
   ```

## Method 2: Use Python Script Directly

1. Open **Command Prompt** (cmd.exe) directly
2. Navigate to the #JustData_Repo directory
3. Run:
   ```cmd
   python move_mergermeter_to_jasonedits.py
   ```

## Method 3: Manual Git Commands

Run these commands one by one in Command Prompt (cmd.exe):

```cmd
cd "C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\DREAM Analysis\#JustData_Repo"

REM Check current branch
git status

REM Fetch latest
git fetch

REM Switch to JasonEdits (or create it)
git checkout JasonEdits
REM If that fails, try:
REM git checkout -b JasonEdits origin/JasonEdits
REM Or if branch doesn't exist:
REM git checkout -b JasonEdits

REM Pull latest changes
git pull origin JasonEdits

REM Stage MergerMeter files
git add apps/mergermeter/
git add run_mergermeter.py
git add shared/

REM Show what will be committed
git status

REM Commit
git commit -m "Fix MergerMeter for GitHub merge - remove hard-coded paths, add graceful fallbacks, add README"

REM Push to JasonEdits branch
git push origin JasonEdits
```

## Method 4: Use C:\DREAM Symbolic Link (If Available)

If you have a C:\DREAM symbolic link set up:

```cmd
cd C:\DREAM\#JustData_Repo
python move_mergermeter_to_jasonedits.py
```

## What Gets Committed

The following files will be committed to JasonEdits:

- ✅ `apps/mergermeter/` - All MergerMeter application files
  - Fixed `config.py` (no hard-coded paths)
  - Fixed `excel_generator.py` (graceful fallbacks)
  - New `README.md` (setup guide)
  - All other mergermeter files
- ✅ `run_mergermeter.py` - Entry point script
- ✅ `shared/` - Shared dependencies (if modified)

## Verification

After pushing, verify on GitHub:

1. Go to your repository on GitHub
2. Switch to the `JasonEdits` branch
3. Verify that `apps/mergermeter/` exists with all files
4. Check that `run_mergermeter.py` exists in the root
5. Verify `apps/mergermeter/README.md` exists

## Important Notes

⚠️ **Always push to `origin JasonEdits`, never to `origin main`!**

The JasonEdits branch is your personal work branch. The main branch is protected.

## Troubleshooting

### "Branch JasonEdits does not exist"
- If it exists on remote: `git checkout -b JasonEdits origin/JasonEdits`
- If it doesn't exist: `git checkout -b JasonEdits`

### "Your branch is behind origin/JasonEdits"
- Run: `git pull origin JasonEdits` to update

### "Nothing to commit"
- Check that files are staged: `git status`
- If files show as modified but not staged, run: `git add .`

### PowerShell Errors
- **Don't use Cursor's terminal** - open Command Prompt (cmd.exe) directly
- Or use the batch file method above

