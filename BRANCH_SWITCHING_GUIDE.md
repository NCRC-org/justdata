# Branch Switching Guide for Map Experiment

## Current Setup

✅ You're now on the `map-experiment` branch  
✅ Your main app is safe on the `JasonEdits` branch  
✅ You can experiment freely here without affecting the working app

## How to Switch Between Branches

### To work on the map experiment (current branch):
```bash
git checkout map-experiment
```
You're already here! Start experimenting with the map.

### To go back to your main working app:
```bash
git checkout JasonEdits
```

### To see which branch you're on:
```bash
git branch
```
The current branch will have an asterisk (*) next to it.

## Running the App Locally

### On the map-experiment branch:
1. Make sure you're on the branch:
   ```bash
   git checkout map-experiment
   ```

2. Run the app as usual:
   ```bash
   python run_branchseeker.py
   ```
   or however you normally start it.

3. Access at: `http://localhost:5000` (or your usual port)

### On the JasonEdits branch (main app):
1. Switch to the branch:
   ```bash
   git checkout JasonEdits
   ```

2. Run the app:
   ```bash
   python run_branchseeker.py
   ```

## Important Notes

- **Uncommitted changes**: If you have uncommitted changes when switching branches, Git will either:
  - Carry them over (if no conflicts)
  - Warn you and prevent switching (if there are conflicts)
  
- **To save your work before switching**:
  ```bash
  git add .
  git commit -m "WIP: experimenting with map feature"
  ```

- **To discard changes** (if you want to start fresh):
  ```bash
  git checkout -- .
  ```
  ⚠️ This will delete all uncommitted changes!

## Experimenting with the Map

You can now:
- Add map libraries (Leaflet, Mapbox, Google Maps, etc.)
- Modify `report_template.html` to include a map
- Add map-related JavaScript in `app.js`
- Add map styling in `style.css`
- Test different map configurations

All changes will only affect the `map-experiment` branch!

## When You're Done Experimenting

### If you like the map and want to merge it:
```bash
# Switch back to main branch
git checkout JasonEdits

# Merge the map experiment
git merge map-experiment
```

### If you don't like it and want to delete the branch:
```bash
# Switch back to main branch first
git checkout JasonEdits

# Delete the experiment branch
git branch -D map-experiment
```

## Quick Reference

| Action | Command |
|--------|---------|
| See all branches | `git branch` |
| Switch to map experiment | `git checkout map-experiment` |
| Switch to main app | `git checkout JasonEdits` |
| Save current work | `git add . && git commit -m "message"` |
| Discard changes | `git checkout -- .` |
| See what changed | `git status` |


