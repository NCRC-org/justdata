# Version Management System

This directory includes an automated version management system for BranchSeeker.

## Files

- **`version.py`**: Current version number (auto-updated)
- **`CHANGELOG.json`**: Log of all changes with version numbers
- **`update_version.py`**: Script to automatically update version from changelog

## How It Works

1. **When you make changes**: Update `CHANGELOG.json` with a new version entry
2. **Automatic update**: Run `update_version.py` to sync `version.py` with the changelog
3. **Version display**: The version appears in the footer of all pages

## Usage

### Manual Update

After updating `CHANGELOG.json`, run:

```bash
python justdata/apps/branchseeker/update_version.py
```

### Check Only (No Update)

To check if an update is needed without updating:

```bash
python justdata/apps/branchseeker/update_version.py --check-only
```

### Force Update

To update even if changelog hasn't changed recently:

```bash
python justdata/apps/branchseeker/update_version.py --force
```

### Scheduled Updates (Every 12 Hours)

#### Windows (Task Scheduler)

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger: "Daily" → "Repeat task every: 12 hours"
4. Action: "Start a program"
5. Program: `python`
6. Arguments: `C:\DREAM\justdata\justdata\apps\branchseeker\update_version.py`
7. Start in: `C:\DREAM\justdata`

#### Linux/Mac (Cron)

Add to crontab (`crontab -e`):

```
0 */12 * * * cd /path/to/justdata && python justdata/apps/branchseeker/update_version.py
```

## Updating the Changelog

When you make changes, add a new entry to `CHANGELOG.json`:

```json
{
  "versions": [
    {
      "version": "1.0.1",
      "date": "2025-01-28",
      "changes": [
        "Fixed summary cards deduplication",
        "Added version number to footer",
        "Improved Excel export formatting"
      ]
    },
    {
      "version": "1.0.0",
      ...
    }
  ]
}
```

**Important**: Always add new versions at the **top** of the versions array (latest first).

## Version Numbering

Follow semantic versioning:
- **MAJOR.MINOR.PATCH** (e.g., 1.0.0)
- **MAJOR**: Breaking changes
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, backward compatible

## Automatic Detection

The script checks if `CHANGELOG.json` was modified in the last 12 hours (configurable). If it was, it updates `version.py` automatically. This prevents unnecessary updates when the changelog hasn't changed.

