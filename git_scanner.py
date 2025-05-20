#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path
import openai
from openai import OpenAI

openai.api_key = os.environ.get('OPENAI_API_KEY')  # Set your OpenAI API key

def is_git_repo(path):
    """Check if the given path is a git repository."""
    git_dir = os.path.join(path, '.git')
    return os.path.isdir(git_dir)

def get_commit_log(repo_path, days=1):
    """Get the commit log for a git repository from the last N days."""
    try:
        result = subprocess.run(
            ['git', '-C', repo_path, 'log', f'--since="{days} days ago"', '--pretty=format:%h - %an, %ar : %s'],
            capture_output=True, text=True, check=True
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return "Failed to retrieve commit log"

def analyze_commits_with_ai(all_commits):
    """Analyze commits using OpenAI to identify new technologies."""
    client = OpenAI()  # Uses OPENAI_API_KEY from environment variables
    
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a technology analyst who specializes in identifying new technologies from commit logs."},
                {"role": "user", "content": f"Find any new or unique technologies used in the following commits and summarize them in a blog post:\n\n{all_commits}"}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error analyzing commits: {str(e)}"

def scan_directory(directory='.'):
    """Scan a directory for git repositories and get their commit logs."""
    directory = os.path.abspath(directory)
    print(f"Scanning {directory} for Git repositories...\n")
    
    found_repos = 0
    all_commits = ""
    
    for root, dirs, _ in os.walk(directory):
        # Skip .git directories to avoid recursion issues
        if '.git' in dirs:
            dirs.remove('.git')
            
        if is_git_repo(root):
            found_repos += 1
            repo_path = Path(root)
            commit_log = get_commit_log(root)
            
            print(f"Repository found: {repo_path.name}")
            print(f"Location: {repo_path}")
            print("\nCommit Log:")
            print("-" * 50)
            print(commit_log)
            print("-" * 50)
            print("\n")
            
            all_commits += f"\nRepository: {repo_path.name}\n{commit_log}\n\n"
    
    if found_repos == 0:
        print("No Git repositories found in the specified directory.")
    else:
        print(f"Found {found_repos} Git repositories.")
        
        if all_commits:
            print("\nAnalyzing commits with AI...\n")
            analysis = analyze_commits_with_ai(all_commits)
            print("\nAI Analysis:")
            print("=" * 80)
            print(analysis)
            print("=" * 80)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        scan_directory(sys.argv[1])
    else:
        scan_directory()

