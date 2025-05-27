import os
import subprocess
from pathlib import Path
import openai
from openai import OpenAI
import argparse
import git
import re

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
        #calculate number of commits
        num_commits = len(result.stdout.splitlines())
        #return an object with the number of commits and the commit log
        return {"num_commits": num_commits, "commit_log": result.stdout}
    except subprocess.CalledProcessError:
        return "Failed to retrieve commit log"

def get_detailed_commit_log(repo_path, count=10):
    try:
        repo = git.Repo(repo_path)
        commits = list(repo.iter_commits('HEAD', max_count=count))
        detailed_commits = []

        for commit in commits:
            commit_info = (
                f"Commit: {commit.hexsha}\n"
                f"Author: {commit.author.name} <{commit.author.email}>\n"
                f"Date: {commit.committed_datetime}\n\n"
                f"Message: {commit.message.strip()}\n"
            )

            if commit.parents:
                diffs = commit.diff(commit.parents[0], create_patch=True)
            else:
                empty_tree = repo.tree('4b825dc642cb6eb9a060e54bf8d69288fbee4904')
                diffs = commit.diff(empty_tree, create_patch=True)

            file_changes = []
            for diff in diffs:
                change_type = (
                    "Added" if diff.new_file else
                    "Deleted" if diff.deleted_file else
                    "Modified"
                )
                filename = diff.b_path or diff.a_path or "Unknown file"
                patch = diff.diff.decode(errors='ignore')

                added_lines = []
                removed_lines = []

                for line in patch.splitlines():
                    if line.startswith('+++') or line.startswith('---') or line.startswith('@@'):
                        continue
                    clean_line = remove_emojis(line)
                    if clean_line.startswith('+'):
                        added_lines.append(clean_line)
                    elif clean_line.startswith('-'):
                        removed_lines.append(clean_line)

                file_block = f"- {filename} ({change_type})"
                if added_lines:
                    file_block += f"\n  ADDED lines:\n    " + "\n    ".join(added_lines)
                if removed_lines:
                    file_block += f"\n  REMOVED lines:\n    " + "\n    ".join(removed_lines)
                if not (added_lines or removed_lines):
                    file_block += "\n  (No content changes)"

                file_changes.append(file_block)

            commit_info += f"\nFiles changed:\n" + "\n".join(file_changes)
            commit_info += "\n" + "=" * 60 + "\n"
            detailed_commits.append(commit_info)

        return "\n".join(detailed_commits), commits
    except Exception as e:
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

def scan_directory(directory='.', days=1, commits=0, free=False, current=False, delve=False):
    """Scan a directory for git repositories and get their commit logs."""
    directory = os.path.abspath(directory)
    print(f"Scanning {directory} for Git repositories...\n")
    
    found_repos = 0
    all_commits = ""

    for root, dirs, _ in os.walk(directory):
        # Skip .git directories to avoid recursion issues
        if '.git' in dirs:
            dirs.remove('.git')
            
        if is_git_repo(root) and (delve or found_repos == 0):
            found_repos += 1
            repo_path = Path(root)
            if commits == 0:
                commit_log = get_commit_log(root, days)
                detailed_log, _ = get_detailed_commit_log(root, commit_log.get("num_commits", 5))
            else:
                detailed_log, commit_log = get_detailed_commit_log(root, commits)
            
            print(f"Repository found: {repo_path.name}")
            print(f"Location: {repo_path}")
            print("\nCommit Log:")
            print("-" * 50)
            print(commit_log.get("commit_log", "Failed to retrieve commit log"))    
            print("-" * 50)
            print("\n")

            if current:
                # Get the current changes
                repo = git.Repo(repo_path)
                changed_files = [item.a_path for item in repo.index.diff(None)] #Files not staged
                changed_files.extend([item.a_path for item in repo.index.diff('HEAD')]) #Files staged
                file_contents = {}
                for file_path in changed_files:
                    with open(os.path.join(repo_path, file_path), 'r') as file:
                        file_contents[file_path] = file.read()
                for file_path, content in file_contents.items():
                    # Process the content of each file
                    all_commits += (f"File: {file_path}\nContent:\n{content}\n{'='*20}")
            else:
                all_commits += f"Repository: {repo_path.name}\n{detailed_log}\n\n"
    
    if found_repos == 0:
        print("No Git repositories found in the specified directory.")
    else:
        print(f"Found {found_repos} Git repositories.")
        
        if all_commits:
            
            analysis = analyze_commits_with_ai(all_commits, free)
            if free:
                print(analysis)
            else:
                print("\nAI Analysis:")
                print("=" * 80)
                print(analysis)
                print("=" * 80)

def remove_emojis(text):
    emoji_pattern = re.compile(
        "[" 
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002700-\U000027BF"  # Dingbats
        "\U0001F900-\U0001F9FF"  # supplemental symbols
        "\U0001FA70-\U0001FAFF"  # Extended-A
        "\u200d"                 # zero-width joiner
        "\ufe0f"                 # variation selector-16
        "]+", flags=re.UNICODE
    )
    return emoji_pattern.sub('', text)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', nargs='?', default='.', help='directory to scan for Git repositories')
    parser.add_argument('days', nargs='?', default=1, type=int, help='number of days to scan for commits')
    parser.add_argument('commits', nargs='?', default=0, type=int, help='number of commits to scan')
    parser.add_argument('-f', '--free', action='store_true', help='output the prompt instead of sending it to OpenAI')
    parser.add_argument('-c', '--current', action='store_true', help='scan the current changes (use before you commit)')
    parser.add_argument('-d', '--delve', action='store_true', help='check for multiple repositiories')   
    args = parser.parse_args()

    scan_directory(args.directory, args.days, args.commits, free=args.free, current=args.current, delve=args.delve)

if __name__ == "__main__":
    main()   