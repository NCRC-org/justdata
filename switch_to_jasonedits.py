#!/usr/bin/env python3
"""
Switch to JasonEdits branch using subprocess with shell=False
to bypass PowerShell wrapper issues with apostrophes in paths.
"""

import subprocess
import sys
from pathlib import Path

def run_git_command(cmd_list, description=""):
    """Run a git command using subprocess with shell=False to bypass PowerShell."""
    if description:
        print(f"\n{description}")
        print(f"Running: {' '.join(cmd_list)}")
        print("-" * 60)
    
    try:
        result = subprocess.run(
            cmd_list,
            shell=False,  # Critical: shell=False bypasses PowerShell wrapper
            check=False,
            capture_output=False,  # Show output in real-time
            text=True,
            cwd=str(Path(__file__).parent)  # Run from #JustData_Repo directory
        )
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"ERROR: Could not execute command: {e}")
        return False

def main():
    """Switch to JasonEdits branch."""
    project_root = Path(__file__).parent
    
    print("=" * 60)
    print("Switching to JasonEdits Branch")
    print("=" * 60)
    
    # Step 1: Check current branch
    print("\n📋 Checking current branch...")
    run_git_command(["git", "status"], "Current status")
    
    # Step 2: Fetch latest
    print("\n📥 Fetching latest from remote...")
    run_git_command(["git", "fetch"], "Fetching")
    
    # Step 3: Check if JasonEdits exists on remote
    print("\n🔍 Checking for JasonEdits branch...")
    result = subprocess.run(
        ["git", "branch", "-r", "--list", "origin/JasonEdits"],
        shell=False,
        capture_output=True,
        text=True,
        cwd=str(project_root)
    )
    
    remote_exists = "origin/JasonEdits" in result.stdout
    
    # Step 4: Check if JasonEdits exists locally
    result = subprocess.run(
        ["git", "branch", "--list", "JasonEdits"],
        shell=False,
        capture_output=True,
        text=True,
        cwd=str(project_root)
    )
    
    local_exists = "JasonEdits" in result.stdout
    
    # Step 5: Switch to or create JasonEdits
    print("\n🔄 Switching to JasonEdits branch...")
    if local_exists:
        print("JasonEdits branch exists locally, switching...")
        success = run_git_command(["git", "checkout", "JasonEdits"], "Switching to JasonEdits")
    elif remote_exists:
        print("JasonEdits exists on remote, checking out...")
        success = run_git_command(["git", "checkout", "-b", "JasonEdits", "origin/JasonEdits"], 
                                 "Creating local JasonEdits from remote")
    else:
        print("JasonEdits doesn't exist, creating new branch...")
        success = run_git_command(["git", "checkout", "-b", "JasonEdits"], "Creating new JasonEdits branch")
    
    if success:
        # Step 6: Pull latest if branch exists on remote
        if remote_exists:
            print("\n⬇️  Pulling latest changes...")
            run_git_command(["git", "pull", "origin", "JasonEdits"], "Pulling from JasonEdits")
        
        # Step 7: Show final status
        print("\n✅ Final status:")
        run_git_command(["git", "status"], "Current branch status")
        
        print("\n" + "=" * 60)
        print("✓ Successfully switched to JasonEdits branch!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("✗ Failed to switch to JasonEdits branch")
        print("=" * 60)
        sys.exit(1)

if __name__ == '__main__':
    main()

