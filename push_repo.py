#!/usr/bin/env python3
"""
Push the AdaptivHealth repository to GitHub using GitPython.
This bypasses the terminal issues with gh auth login.
"""

import os
import subprocess
from pathlib import Path

def get_gh_token():
    """Extract the GitHub token from gh CLI."""
    try:
        token = subprocess.check_output(['gh', 'auth', 'token'], text=True).strip()
        if token:
            return token
    except Exception as e:
        print(f"Error getting gh token: {e}")
    return None

def push_with_git_python():
    """Use GitPython to push the repository."""
    try:
        from git import Repo
        
        repo_path = Path("c:\\Users\\hp\\Desktop\\AdpativHealth")
        repo = Repo(repo_path)
        
        # Get the token
        token = get_gh_token()
        if not token:
            print("ERROR: Could not obtain GitHub token from gh CLI")
            print("Please ensure you are authenticated with: gh auth login")
            return False
        
        # Create the remote URL with token
        origin_url = f"https://rbithin10:{token}@github.com/rbithin10/AdaptivHealth.git"
        
        # Get origin remote
        origin = repo.remote('origin')
        
        # Push
        print(f"Pushing to {repo.remotes.origin.url}...")
        repo.remotes.origin.push()
        print("✓ Push successful!")
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def push_with_subprocess():
    """Use subprocess to run git push with proper environment."""
    try:
        # Change to repo directory
        os.chdir(r"c:\Users\hp\Desktop\AdpativHealth")
        
        # Try to get token
        result = subprocess.run(['gh', 'auth', 'token'], 
                               capture_output=True, text=True, timeout=5)
        token = result.stdout.strip()
        
        if not token:
            print("ERROR: Could not obtain GitHub token")
            return False
        
        # Set up git config to use token -based auth
        subprocess.run(['git', 'config', 'credential.helper', 'store'], check=False)
        
        # Push with token in URL
        remote_url = f"https://rbithin10:{token}@github.com/rbithin10/AdaptivHealth.git"
        
        print("Executing: git push...")
        result = subprocess.run(['git', 'push', 'origin', 'main'], 
                               timeout=60,
                               capture_output=True, 
                               text=True)
        
        if result.returncode == 0:
            print("✓ Push successful!")
            print(result.stdout)
            return True
        else:
            print(f"ERROR: Push failed with code {result.returncode}")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("ERROR: Command timed out")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Attempting to push AdaptivHealth repository...")
    print()
    
    # Try subprocess first (simpler)
    success = push_with_subprocess()
    
    if not success:
        print()
        print("Trying GitPython approach...")
        success = push_with_git_python()
    
    if success:
        print()
        print("Repository pushed successfully!")
        exit(0)
    else:
        print()
        print("Failed to push repository")
        exit(1)
