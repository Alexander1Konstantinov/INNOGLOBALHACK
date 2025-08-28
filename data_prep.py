import subprocess
import os
import json
from datetime import datetime, timedelta
class DataPrep:
    def __init__(self, data_path="C:\innoglobalhack\Hackaton"):
        self.data_path = data_path
    def get_commits_by_author(self, author_id, repo_path):
        os.chdir("C:\innoglobalhack\Hackaton")
        try:
            os.chdir(repo_path)
            print(f"Changed directory to {repo_path}\n")
        except FileNotFoundError:
            print(f"Error: The directory {repo_path} does not exist.")
            return []
        for id in author_id:
            if id:
                git_log_command = [
                    "git", "log", f'--author={id}', "--pretty=format:%H %cd %s", "--date=iso"
                ]
                result = subprocess.run(git_log_command, stdout=subprocess.PIPE, text=True)
                commits = result.stdout
                if commits:
                    return commits.splitlines()
        print("Неправильный author_id или у автора нет коммитов")
    def get_time_last_commit(self, author_id):
        for id in author_id:
            if id:
                git_log_command = [
                    "git", "log", "--author=" + id, "--pretty=format:%H %cd %s", "--date=iso", "-1"
                ]
                result = subprocess.run(git_log_command, stdout=subprocess.PIPE, text=True)
                commit = result.stdout
                if commit:
                    return datetime.strptime(commit.splitlines()[0].split()[1], "%Y-%m-%d")
        print("Неправильный author_id или у автора нет коммитов")
    def get_commit_code_by_hash(self, hash_code):
        git_show_command = [
            "git", "show", hash_code
        ]
        result = subprocess.run(git_show_command, stdout=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')
        commits = result.stdout.splitlines()
        return commits
    def get_added_str(self, show_commit):
        output = ''
        for row in show_commit:
            if row and row[0] == '+' and row[0:3] != '+++':
                output += row[1:]
                output += "\n"
        return output
    def get_removed_str(self, show_commit):
        output = ''
        for row in show_commit:
            if row and row[0] == '-' and row[0:3] != '---':
                output += row[1:]
                output += "\n"
        return output
    def get_last_n_largest_commits(self, commits, time, n, added=True):
        codes = {}
        time = time - timedelta(days=365)
        for commit in commits:
            if datetime.strptime(commit.split()[1], "%Y-%m-%d") < time:
                continue
            code = self.get_commit_code_by_hash(commit.split()[0])
            if added:
                code = self.get_added_str(code)
            else:
                code = self.get_removed_str(code)
            codes[commit] = (code)
        codes = sorted(codes.items(), key=lambda x: len(x[1]))[-n:]
        return dict(codes)
    def get_added_commits(self, author_id, repo_path, n):
        commits = self.get_commits_by_author(author_id, repo_path)
        t = self.get_time_last_commit(author_id)
        output = list(self.get_last_n_largest_commits(commits, t, n).values())
        return output
    def get_removed_commits(self, author_id, repo_path, n):
        commits = self.get_commits_by_author(author_id, repo_path)
        t = self.get_time_last_commit(author_id)
        largest_hashes = list(self.get_last_n_largest_commits(commits, t, n, True).keys())
        removed_codes = [self.get_removed_str(self.get_commit_code_by_hash(hash_code.split()[0])) for hash_code in
                         largest_hashes]
        return removed_codes
    def get_largest_messages(self, commits, t, n):
        commits = list(self.get_last_n_largest_commits(commits, t, n).keys())
        largest_commits_mess = [commit.split('+')[1][5:] for commit in commits]
        return largest_commits_mess
    def get_added_removed_descr(self, author_id, repo_path, n, llmh):
        added = self.get_added_commits(author_id, repo_path, n)
        removed = self.get_removed_commits(author_id, repo_path, n)
        t = self.get_time_last_commit(author_id)
        commits = self.get_commits_by_author(author_id, repo_path)
        message = self.get_largest_messages(commits, t, n)
        descr = []
        for i in range(len(added)):
            prompt = llmh.prepare_prompt_added_removed(added[i], removed[i], message[i])
            descr.append(llmh.evaluate_commits_with_llm(prompt))
        return descr
    def read_dataset(self, file_path="dataset.json"):
        with open(file_path, "r") as f:
            users = json.load(f)
            for user in users:
                yield user