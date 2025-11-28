#!/usr/bin/env python3
"""
Move MergerMeter changes to JasonEdits branch using subprocess with shell=False
to bypass PowerShell wrapper issues with apostrophes in paths.
"""

import subprocess
import sys
from pathlib import Path

def run_git_command(cmd_list, description):
    """Run a git command using subprocess with shell=False to bypass PowerShell."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd_list)}")
    print('='*60)
    
    try:
        result = subprocess.run(
            cmd_list,
            shell=False,  # Critical: shell=False bypasses PowerShell wrapper
            check=False,
            capture_output=False,  # Show output in real-time
            text=True,
            cwd=str(Path(__file__).parent)  # Run from #JustData_Repo directory
        )
        
        if result.returncode != 0:
            print(f"\n⚠️  Command returned exit code: {result.returncode}")
            return False
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: Could not execute command: {e}")
        return False

def main():
    """Main workflow to move MergerMeter to JasonEdits branch."""
    print("\n" + "="*60)
    print("MergerMeter Migration to JasonEdits Branch")
    print("="*60)
    
    # Get the project root (#JustData_Repo)
    project_root = Path(__file__).parent
    
    # Step 1: Check current branch
    print("\n📋 Step 1: Checking current branch...")
    run_git_command(["git", "status"], "Check current branch and status")
    
    # Step 2: Fetch latest from remote
    print("\n📥 Step 2: Fetching latest from remote...")
    run_git_command(["git", "fetch"], "Fetch latest from GitHub")
    
    # Step 3: Switch to JasonEdits branch (or create it)
    print("\n🔄 Step 3: Switching to JasonEdits branch...")
    # First check if branch exists locally
    result = subprocess.run(
        ["git", "branch", "--list", "JasonEdits"],
        shell=False,
        capture_output=True,
        text=True,
        cwd=str(project_root)
    )
    
    if "JasonEdits" in result.stdout:
        print("JasonEdits branch exists locally, switching to it...")
        run_git_command(["git", "checkout", "JasonEdits"], "Switch to JasonEdits branch")
    else:
        # Check if it exists on remote
        result = subprocess.run(
            ["git", "branch", "-r", "--list", "origin/JasonEdits"],
            shell=False,
            capture_output=True,
            text=True,
            cwd=str(project_root)
        )
        
        if "origin/JasonEdits" in result.stdout:
            print("JasonEdits branch exists on remote, checking out...")
            run_git_command(["git", "checkout", "-b", "JasonEdits", "origin/JasonEdits"], 
                          "Create local JasonEdits from remote")
        else:
            print("JasonEdits branch doesn't exist, creating new branch...")
            run_git_command(["git", "checkout", "-b", "JasonEdits"], "Create new JasonEdits branch")
    
    # Step 4: Pull latest changes
    print("\n⬇️  Step 4: Pulling latest changes from JasonEdits...")
    run_git_command(["git", "pull", "origin", "JasonEdits"], "Pull latest from JasonEdits")
    
    # Step 5: Stage MergerMeter files
    print("\n📦 Step 5: Staging MergerMeter files...")
    files_to_add = [
        "apps/mergermeter/",
        "run_mergermeter.py"
    ]
    
    for file_path in files_to_add:
        full_path = project_root / file_path
        if full_path.exists():
            run_git_command(["git", "add", file_path], f"Stage {file_path}")
        else:
            print(f"⚠️  Warning: {file_path} not found, skipping...")
    
    # Also check for shared dependencies if they were modified
    shared_path = project_root / "shared"
    if shared_path.exists():
        print("\n📦 Staging shared dependencies...")
        run_git_command(["git", "add", "shared/"], "Stage shared dependencies")
    
    # Step 6: Show what will be committed
    print("\n📊 Step 6: Showing staged changes...")
    run_git_command(["git", "status"], "Show staged changes")
    
    # Step 7: Commit
    print("\n💾 Step 7: Committing changes...")
    commit_message = "Fix MergerMeter for GitHub merge - remove hard-coded paths, add graceful fallbacks, add README"
    run_git_command(["git", "commit", "-m", commit_message], "Commit MergerMeter changes")
    
    # Step 8: Show final status
    print("\n✅ Step 8: Final status...")
    run_git_command(["git", "status"], "Show final status")
    
    print("\n" + "="*60)
    print("Migration Complete!")
    print("="*60)
    print("\n📝 Next Steps:")
    print("1. Review the changes with: git log -1")
    print("2. Push to JasonEdits branch: git push origin JasonEdits")
    print("3. Verify on GitHub that changes are on JasonEdits branch")
    print("\n⚠️  Remember: Always push to origin JasonEdits, never to origin main!")
    print("="*60 + "\n")

if __name__ == '__main__':
    main()

