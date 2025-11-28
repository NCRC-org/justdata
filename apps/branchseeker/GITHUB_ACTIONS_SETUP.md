# Setting Up GitHub Actions for Automatic Version Updates

This guide shows you how to set up GitHub Actions to automatically update your version number in the cloud, without needing your machine to be on.

## Benefits

✅ Runs automatically every 12 hours  
✅ Runs when you update CHANGELOG.json  
✅ Works even when your computer is off  
✅ Commits the updated version.py back to GitHub  
✅ Free for public repositories  
✅ Free for private repositories (with limits)

## Prerequisites

1. Your code must be in a GitHub repository
2. You need push access to the repository
3. GitHub Actions must be enabled (enabled by default)

## Step-by-Step Setup

### Step 1: Create the Workflow File

I've already created the workflow file for you at:
`.github/workflows/update-version.yml`

This file tells GitHub Actions:
- When to run (every 12 hours OR when CHANGELOG.json changes)
- What to do (check changelog, update version.py)
- How to commit changes back

### Step 2: Push to GitHub

1. **Commit the workflow file**:
   ```bash
   git add .github/workflows/update-version.yml
   git commit -m "Add GitHub Actions workflow for version updates"
   git push
   ```

2. **Verify it's there**:
   - Go to your GitHub repository
   - Click the "Actions" tab
   - You should see "Update Version from Changelog" in the list

### Step 3: Test It Manually

1. Go to your GitHub repository
2. Click the **"Actions"** tab
3. Find **"Update Version from Changelog"** in the left sidebar
4. Click **"Run workflow"** button (top right)
5. Select your branch (usually `main` or `master`)
6. Click **"Run workflow"**

This will trigger the workflow immediately so you can see if it works.

### Step 4: Verify It Works

1. After running, click on the workflow run
2. You should see it complete successfully
3. If version.py was updated, check the commit - it should show a new commit with the updated version

## How It Works

### Automatic Triggers

The workflow runs in three scenarios:

1. **Every 12 hours** (scheduled):
   - Checks if CHANGELOG.json was modified
   - Updates version.py if needed

2. **When you push CHANGELOG.json**:
   - Immediately checks and updates version.py
   - Commits the change back

3. **Manual trigger**:
   - You can click "Run workflow" anytime
   - Useful for testing

### What Happens

1. GitHub Actions checks out your code
2. Runs the `update_version.py` script
3. If version needs updating:
   - Updates version.py
   - Commits the change
   - Pushes it back to GitHub
4. You get a new commit: `chore: auto-update version from CHANGELOG.json`

## Your Workflow Now

### When You Make Changes:

1. **Make your code changes**
2. **Update CHANGELOG.json** with new version
3. **Commit and push**:
   ```bash
   git add CHANGELOG.json
   git add [your other changed files]
   git commit -m "feat: added new feature"
   git push
   ```
4. **GitHub Actions automatically**:
   - Detects CHANGELOG.json changed
   - Runs the workflow
   - Updates version.py
   - Commits and pushes the update

### Result:

- Your code changes are committed
- Version is automatically updated
- Everything is in sync

## Customization

### Change the Schedule

Edit `.github/workflows/update-version.yml`:

```yaml
schedule:
  - cron: '0 */12 * * *'  # Every 12 hours
```

Cron format examples:
- `'0 */6 * * *'` - Every 6 hours
- `'0 0 * * *'` - Once daily at midnight
- `'0 0 * * 1'` - Once weekly (Mondays)

### Disable Scheduled Runs

If you only want it to run when CHANGELOG.json changes, remove the `schedule` section:

```yaml
on:
  push:
    paths:
      - 'justdata/apps/branchseeker/CHANGELOG.json'
  workflow_dispatch:
```

## Troubleshooting

### Workflow doesn't run

1. Check GitHub Actions is enabled:
   - Repository → Settings → Actions → General
   - Make sure "Allow all actions and reusable workflows" is selected

2. Check the workflow file is in the right place:
   - Should be at: `.github/workflows/update-version.yml`
   - Must be committed and pushed

### Workflow runs but doesn't update

1. Check the workflow logs:
   - Actions tab → Click on the run → Check the logs
   - Look for error messages

2. Verify CHANGELOG.json format:
   - Must be valid JSON
   - Latest version must be at the top

3. Check file permissions:
   - The workflow needs write access
   - Should work automatically with GITHUB_TOKEN

### Commits aren't being pushed

1. Check the "Commit and push changes" step in logs
2. Verify GITHUB_TOKEN has write permissions (should be automatic)
3. Make sure you're not in a protected branch that requires reviews

## Disabling GitHub Actions

If you want to go back to local-only updates:

1. Go to repository → Settings → Actions
2. Under "Actions permissions", select "Disable Actions"
3. Or just delete the workflow file

## Comparison: Local vs GitHub Actions

| Feature | Local (Task Scheduler) | GitHub Actions |
|---------|------------------------|----------------|
| Requires computer on | ✅ Yes | ❌ No |
| Runs automatically | ✅ Yes (every 12h) | ✅ Yes (every 12h) |
| Runs on file change | ❌ No | ✅ Yes |
| Commits automatically | ❌ No | ✅ Yes |
| Free | ✅ Yes | ✅ Yes (public repos) |
| Setup complexity | Medium | Easy |

## Best Practice: Use Both!

You can use both:
- **GitHub Actions**: For automatic commits when you push
- **Local Task Scheduler**: For local testing before pushing

Or just use GitHub Actions - it's simpler and works everywhere!



