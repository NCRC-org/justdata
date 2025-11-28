# Switch to JasonEdits Branch

Since Cursor's terminal tool has PowerShell issues with apostrophes in paths, use one of these methods:

## Method 1: Use the Batch File (Easiest)

1. **Open Command Prompt (cmd.exe) directly** - Don't use Cursor's terminal
2. Navigate to the #JustData_Repo directory:
   ```cmd
   cd "C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\DREAM Analysis\#JustData_Repo"
   ```
3. Run the batch file:
   ```cmd
   switch_to_jasonedits.bat
   ```

## Method 2: Manual Git Commands

Run these commands in **Command Prompt (cmd.exe)**:

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

REM Pull latest changes
git pull origin JasonEdits

REM Verify you're on the right branch
git status
```

## Method 3: Use Python Script (If you can run it directly)

If you can run Python scripts outside of Cursor's terminal:

```cmd
cd "C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\DREAM Analysis\#JustData_Repo"
python switch_to_jasonedits.py
```

## What This Does

1. ✅ Checks your current branch
2. ✅ Fetches latest from GitHub
3. ✅ Switches to JasonEdits branch (or creates it if it doesn't exist)
4. ✅ Pulls latest changes from JasonEdits
5. ✅ Shows final status

## Verification

After switching, verify you're on JasonEdits:

```cmd
git status
```

You should see:
```
On branch JasonEdits
```

## Important Notes

- **Always work on JasonEdits branch** - This is your personal work branch
- **Never push to main** - The main branch is protected
- **Always push to origin JasonEdits** when ready to save your work

## Troubleshooting

### "Branch JasonEdits does not exist"
- If it exists on remote: `git checkout -b JasonEdits origin/JasonEdits`
- If it doesn't exist: `git checkout -b JasonEdits`

### "Your branch is behind origin/JasonEdits"
- Run: `git pull origin JasonEdits` to update

### PowerShell Errors
- **Don't use Cursor's terminal** - Open Command Prompt (cmd.exe) directly
- Use the batch file method above

