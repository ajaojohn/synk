import synk.utils as utils
import os
import shutil
import filecmp
import subprocess
from datetime import datetime
from synk.utils import confirm, print_error, print_success, print_warning
import tempfile

def sync_all(cfg, profile_name):
    plan = plan_syncs(cfg, profile_name)
    show_plan(plan)

    if not confirm("Proceed with these changes?"):
        print_error("Sync plan aborted.")
        return

    apply_plan(plan)

    if confirm("Commit these changes?"):
        commit_changes(plan)
    else:
        print_warning("Skipped commit.")
        return

    if confirm("Push to remote?"):
        push_changes(plan)
    else:
        print_warning("Skipped push.")


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
            print_success(f"  [NEW]      {item['source']} -> {item['destination']}")
        elif item["type"] == "modified":
            print_success(f"  [MODIFIED] {item['source']} -> {item['destination']}")
        elif item["type"] == "skipped":
            print_warning(f"  [SKIPPED]  {item['source']} -> {item['destination']}")
        elif item["type"] == "error":
            print_error(f"  [ERROR]    {item['source']} -> {item['destination']} ({item['reason']})")

    total = sum(1 for item in plan if item["type"] in ["new", "modified"])
    print(f"\nTotal changes to apply: {total}")

def apply_plan(plan):
    """
    Apply the planned syncs, with rollback on failure.
    """
    backups = []      # list of (original_path, backup_path)
    staged_files = [] # list of paths added to git

    try:
        for item in plan:
            if item["type"] not in ["new", "modified"]:
                continue

            src = item["source"]
            dst = item["destination"]
            repo = item["git_repo"]

            # Backup existing file if it exists
            backup_path = None
            if os.path.exists(dst):
                fd, backup_path = tempfile.mkstemp()
                os.close(fd)  # close the open file descriptor
                shutil.copy2(dst, backup_path)
                backups.append( (dst, backup_path) )

            # Copy new contents
            shutil.copy2(src, dst)

            # Stage in git
            subprocess.run(
                ["git", "add", dst],
                cwd=repo, check=True,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            staged_files.append( (repo, dst) )

            print_success(f"Synced: {src} -> {dst}")

    except Exception as e:
        print_error(f"Error during sync: {e}")
        print_warning("Rolling back changes...")

        # Restore backups
        for orig, backup in backups:
            shutil.copy2(backup, orig)
            print_warning(f"Restored original: {orig}")

        # Unstage any files that were staged
        for repo, staged in staged_files:
            try:
                subprocess.run(
                    ["git", "restore", "--staged", staged],
                    cwd=repo, check=True,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                print_warning(f"Unstaged from git: {staged}")
            except Exception as unstaging_error:
                print_error(f"Failed to unstage {staged}: {unstaging_error}")

        print_error("Sync aborted with rollback.")
        raise

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
            print_success(f"Committed in {repo}")
        except subprocess.CalledProcessError:
            print_warning(f"No changes to commit in {repo}")

def push_changes(plan):
    repos = set(item["git_repo"] for item in plan if item["type"] in ["new", "modified"])
    for repo in repos:
        try:
            subprocess.run(["git", "push"],
                           cwd=repo, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print_success(f"Pushed from {repo}")
        except subprocess.CalledProcessError:
            print_error(f"Push failed in {repo}")



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
