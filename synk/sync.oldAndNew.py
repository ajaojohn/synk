#!/usr/bin/env python3

import synk.utils as utils
import os
import shutil
import filecmp
import subprocess
from datetime import datetime
from synk.utils import confirm, print_error, print_success, print_warning

def sync_all(cfg, profile_name):
    """
    Sync all files in the specified profile.
    """

    profile_syncs = cfg["profiles"][profile_name].get("syncs", [])
    for i, sync_entry in enumerate(profile_syncs):
        source_file = sync_entry["source_file"]
        destination_repo_file = sync_entry["destination_repo_file"]

        # Perform the sync operation
        success, message = sync(source_file, destination_repo_file)

        if success == 0:
            print_successful_sync(source_file, destination_repo_file, i + 1)
        elif success == 1:
            print_failed_sync(source_file, destination_repo_file, i + 1, message)
        elif success == 2:
            print_skipped_sync(source_file, destination_repo_file, i + 1)

def sync_all(cfg, profile_name):
    plan = plan_syncs(cfg, profile_name)
    show_plan(plan)

    if not confirm("Proceed with these changes?"):
        print("Aborted.")
        return

    apply_plan(plan)

    if confirm("Commit these changes?"):
        commit_changes(plan)
    else:
        print("Skipped commit.")

    if confirm("Push to remote?"):
        push_changes(plan)
    else:
        print("Skipped push.")


def sync(src_file, dst_file):
    """
    Perform the sync operation between source and destination files.
    """
    # Ensure source file exists
    src_file, src_is_valid = utils.is_valid_source_file(src_file)
    if not src_is_valid:
        return (1, f"Source file '{src_file}' does not exist or is not accessible.")

    # Ensure destination file is valid
    dst_file, dst_is_valid, git_repo_path = utils.is_valid_destination_file(dst_file)
    if dst_is_valid == 0:
        return (1, f"Destination repository file '{dst_file}' is invalid (not in a git repo).")

    return git_sync(src_file, dst_file, git_repo_path)

def git_sync(src_file, dst_file, git_repo_path=None):
    """
    Sync the source file to the destination file in a git repository.
    If the destination file does not exist, it will be created.
    If the destination file exists and is identical to the source file, it will be skipped.
    """
    # Check if files are identical
    if os.path.exists(dst_file) and filecmp.cmp(src_file, dst_file, shallow=False):
        return (2, "Skipped: no changes detected")

    try:
        shutil.copy2(src_file, dst_file)

        # Add the file to git
        subprocess.run(["git", "add", dst_file], cwd=git_repo_path, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Commit the changes
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_message = f"Synk[@{timestamp}]: Synced '{os.path.basename(src_file)}' to '{os.path.basename(dst_file)}'"

        # Push the changes to the remote repository
        subprocess.run(["git", "commit", "-m", commit_message], cwd=git_repo_path, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "push"], cwd=git_repo_path, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


        return (0, "Sync successful")

    except subprocess.CalledProcessError as e:
        return (1, f"Git command failed: \n{e}")
    except Exception as e:
        return (1, f"Sync failed: \n{str(e)}")

def plan_syncs(cfg, profile_name):
    """
    Returns a list of planned sync actions with type:
    - new
    - modified
    - skipped
    """

    plan = []
    profile_syncs = cfg["profiles"][profile_name].get("syncs", [])

    for sync_entry in profile_syncs:
        src = sync_entry["source_file"]
        dst = sync_entry["destination_repo_file"]

        # Validate source
        src, src_ok = utils.is_valid_source_file(src)
        if not src_ok:
            plan.append({"source": src, "destination": dst, "type": "error", "reason": "Source does not exist"})
            continue

        # Validate destination
        dst, dst_status, git_repo = utils.is_valid_destination_file(dst)
        if dst_status == 0 or not git_repo:
            plan.append({"source": src, "destination": dst, "type": "error", "reason": "Destination not in git repo"})
            continue

        if not os.path.exists(dst):
            plan.append({"source": src, "destination": dst, "type": "new", "git_repo": git_repo})
        elif filecmp.cmp(src, dst, shallow=False):
            plan.append({"source": src, "destination": dst, "type": "skipped", "git_repo": git_repo})
        else:
            plan.append({"source": src, "destination": dst, "type": "modified", "git_repo": git_repo})

    return plan

def show_plan(plan):
    print("\nPlanned changes:\n")
    for item in plan:
        if item["type"] == "new":
            print(f"  [NEW]      {item['source']} -> {item['destination']}")
        elif item["type"] == "modified":
            print(f"  [MODIFIED] {item['source']} -> {item['destination']}")
        elif item["type"] == "skipped":
            print(f"  [SKIPPED]  {item['source']} -> {item['destination']}")
        elif item["type"] == "error":
            print(f"  [ERROR]    {item['source']} -> {item['destination']} ({item['reason']})")

    total = sum(1 for item in plan if item["type"] in ["new", "modified"])
    print(f"\nTotal changes to apply: {total}")

def apply_plan(plan):
    for item in plan:
        if item["type"] not in ["new", "modified"]:
            continue

        try:
            shutil.copy2(item["source"], item["destination"])
            subprocess.run(["git", "add", item["destination"]],
                            cwd=item["git_repo"], check=True,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"  ✅ Synced: {item['source']} -> {item['destination']}")
        except Exception as e:
            print(f"  ❌ Failed to sync {item['source']} -> {item['destination']}:\n{e}")

def commit_changes(plan, commit_message=None):
    # get unique repos in the plan
    repos = set(item["git_repo"] for item in plan if item["type"] in ["new", "modified"])

    if not commit_message:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_message = f"Synk[@{timestamp}]: Synced files"

    for repo in repos:
        try:
            subprocess.run(["git", "commit", "-m", commit_message],
                           cwd=repo, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"  ✅ Committed in {repo}")
        except subprocess.CalledProcessError:
            print(f"  ⚠️  No changes to commit in {repo}")

def push_changes(plan):
    repos = set(item["git_repo"] for item in plan if item["type"] in ["new", "modified"])
    for repo in repos:
        try:
            subprocess.run(["git", "push"],
                           cwd=repo, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"  ✅ Pushed from {repo}")
        except subprocess.CalledProcessError:
            print(f"  ❌ Push failed in {repo}")



def print_failed_sync(source_file, destination_repo_file, sync_index, error_message):
    """
    Print an error message if the sync operation fails.
    """
    print(f"\033[91m{sync_index}. Failed to sync '{source_file}' to '{destination_repo_file}'. {error_message}.\033[0m")

def print_successful_sync(source_file, destination_repo_file, sync_index):
    """
    Print a success message if the sync operation is successful.
    """
    print(f"\033[92m{sync_index}. Successfully synced '{source_file}' to '{destination_repo_file}'.\033[0m")
    return True

def print_skipped_sync(source_file, destination_repo_file, sync_index):
    """
    Print a message if the sync operation is skipped due to no changes detected.
    """
    print(f"\033[93m{sync_index}. Skipped syncing '{source_file}' to '{destination_repo_file}' (no changes detected).\033[0m")
    return True
