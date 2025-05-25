import os
import subprocess
from pathlib import Path
import openai
from openai import OpenAI
import argparse

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

def get_detailed_commit_log(repo_path, count=10):
    """Get detailed commit information for the specified number of commits."""
    try:
        # Get commit hashes first
        hash_result = subprocess.run(
            ['git', '-C', repo_path, 'log', f'-{count}', '--pretty=format:%H'],
            capture_output=True, text=True, check=True
        )
        commit_hashes = hash_result.stdout.strip().split('\n')
        
        detailed_commits = []
        for commit_hash in commit_hashes:
            if not commit_hash:  # Skip empty lines
                continue
                
            # Get full commit details
            detail_result = subprocess.run(
                ['git', '-C', repo_path, 'show', commit_hash, '--name-status'],
                capture_output=True, text=True, check=True
            )
            detailed_commits.append(detail_result.stdout)
            
        return '\n'.join(detailed_commits)
    except subprocess.CalledProcessError as e:
        return f"Failed to retrieve detailed commit log: {str(e)}"

def analyze_commits_with_ai(all_commits, free=False):
    """Analyze commits using OpenAI to identify new technologies."""
    client = OpenAI()  # Uses OPENAI_API_KEY from environment variables
    
    prompt = f"Find any new or unique technologies used in the following commits and summarize them in a blog post:\n\n{all_commits}"
    
    if free:
        return prompt
    
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a technology analyst who specializes in identifying new technologies from commit logs."},
                {"role": "user", "content": prompt}
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
            detailed_log = get_detailed_commit_log(root, 5)  # Get details for 5 most recent commits
            
            print(f"Repository found: {repo_path.name}")
            print(f"Location: {repo_path}")
            print("\nCommit Log:")
            print("-" * 50)
            print(commit_log)
            print("-" * 50)
            print("\n")
            
            all_commits += f"\nRepository: {repo_path.name}\n{detailed_log}\n\n"
    
    if found_repos == 0:
        print("No Git repositories found in the specified directory.")
    else:
        print(f"Found {found_repos} Git repositories.")
        
        if all_commits:
            parser = argparse.ArgumentParser()
            parser.add_argument('--free', action='store_true')
            args = parser.parse_args()
            
            analysis = analyze_commits_with_ai(all_commits, free=args.free)
            if args.free:
                print(analysis)
            else:
                print("\nAI Analysis:")
                print("=" * 80)
                print(analysis)
                print("=" * 80)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', nargs='?', default='.', help='directory to scan for Git repositories')
    parser.add_argument('--free', action='store_true', help='output the prompt instead of sending it to OpenAI')
    args = parser.parse_args()

    scan_directory(args.directory)

if __name__ == "__main__":
    main()   