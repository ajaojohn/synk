import synk.config as config
import os
import subprocess
import time

def print_error(message):
    print(f"\033[91m[X] {message}\033[0m")  # Red text
    time.sleep(1)  # Pause for a moment to let the user read the error
def print_success(message):
    print(f"\033[92m[✓] {message}\033[0m")  # Green text
    time.sleep(0.5)  # Pause for a moment to let the user read the success message:w
def print_warning(message):
    print(f"\033[93m[!] {message}\033[0m")  # Yellow text
    time.sleep(0.5)  # Pause for a moment to let the user read the warning message
def print_info(message):
    print(f"\033[94m[i] {message}\033[0m")  # Blue text
    time.sleep(0.5)  # Pause for a moment to let the user read the info message


def cfg_add_profile(cfg, profile_name):
    """
    Add a new profile to the configuration.
    """

    if not profile_name.isalnum():
    # Check profile name is a non-empty one word alphanumeric string
        print_error(f"Profile name must be a non-empty one word alphanumeric string")
        print("Try again.")
    elif profile_name in cfg["profiles"]:
    # Check if profile name is already taken
        print_error(f"Profile name already taken")
        print("Try again.")
    else:
        # Update config and save to file
        cfg["profiles"][profile_name] = {}
        if config.update_config(cfg):
            print_success(f"Profile '{profile_name}' created successfully.")
            # Sync config again to reflect any other changes
            cfg = config.load_config()
            return True
        else:
            print_error(f"Failed to create profile '{profile_name}'.")
    return False

def cfg_remove_sync(cfg, profile_name, sync_index):
    """
    Remove a sync from the specified profile.
    """
    try:
        sync = cfg["profiles"][profile_name].get("syncs", [])[sync_index]
    except IndexError:
        print_error(f"Failed to remove sync. Invalid sync number")
        return False

    # Remove the sync
    cfg["profiles"][profile_name]["syncs"].pop(sync_index)

    # Update config and save to file
    if config.update_config(cfg):
        print_success(f"Sync '{sync['source_file']} -> {sync['destination_repo_file']}' removed successfully.")
        # Sync config again to reflect any other changes
        cfg = config.load_config()
        return True
    else:
        print_error(f"Failed to remove sync '{sync['source_file']} -> {sync['destination_repo_file']}'.")
        return False

def cfg_add_sync(cfg, profile_name, source_file, destination_repo_file):
    """
    Add a new sync to the specified profile.
    """
    if not source_file or not destination_repo_file:
        print_error(f"Source file and destination repo file cannot be empty.")
        return False

    # Check if the profile exists
    if profile_name not in cfg["profiles"]:
        print_error(f"Profile '{profile_name}' does not exist.")
        return False

    # Create the sync entry
    sync = {
        "source_file": source_file,
        "destination_repo_file": destination_repo_file
    }
    # If the sync already exists, do not add it again
    if any(s["source_file"] == source_file and s["destination_repo_file"] == destination_repo_file for s in cfg["profiles"][profile_name].get("syncs", [])):
        print_warning(f"Sync '{source_file} -> {destination_repo_file}' already exists in profile '{profile_name}'.")
        return False
    # Add the sync to the profile
    cfg["profiles"][profile_name].setdefault("syncs", []).append(sync)

    # Update config and save to file
    if config.update_config(cfg):
        print_success(f"Sync '{source_file} -> {destination_repo_file}' added successfully.")
        # Sync config again to reflect any other changes
        cfg = config.load_config()
        return True
    else:
        print_error(f"Failed to add sync '{source_file} -> {destination_repo_file}'.")
        return False

def profile_index_is_valid(cfg, profile_index):
    """
    Check if the given profile index is valid.
    """
    return 0 <= profile_index < len(cfg["profiles"])


def sync_index_is_valid(cfg, profile_index, sync_index):
    """
    Check if the given sync index is valid for the specified profile.
    """
    profile_name = list(cfg["profiles"].keys())[profile_index]
    return 0 <= sync_index < len(cfg["profiles"][profile_name].get("syncs", []))


# File utils

def file_exists(file_path):
    """
    Check if a file exists at the given path.
    """
    return os.path.isfile(file_path)

def file_dir_exists(file_path):
    """
    Check if the directory of the given file path exists.
    """
    return os.path.isdir(os.path.dirname(file_path))

def locate_git_repo(file_path):
    current_dir = os.path.dirname(file_path)
    while current_dir and os.path.isdir(current_dir):
        try:
            repo_path = subprocess.check_output(
                ['git', 'rev-parse', '--git-dir'],
                cwd=current_dir,
                stderr=subprocess.DEVNULL
            ).decode().strip()
            if repo_path:
                return os.path.dirname(os.path.abspath(repo_path))
        except subprocess.CalledProcessError:
            pass
        current_dir = os.path.dirname(current_dir)
    return None

def is_valid_source_file(source_file):
    """
    Check if the source file is valid.
    """
    source_file = os.path.abspath(os.path.expanduser(source_file))
    if not file_exists(source_file):
        return (source_file, False)
    return (source_file, True)

def is_valid_destination_file(dst_file):
    """
    Check if the destination file is valid.
    1. Must be in a git repo

    If the path is in a git repo and the file exists, returns 2
    If the path is in a git repo but the file does not exist, returns 1
    If the path is not in a git repo, returns 0
    """
    dst_file = os.path.abspath(os.path.expanduser(dst_file))
    if file_dir_exists(dst_file):
        git_repo_path = locate_git_repo(dst_file)
        if git_repo_path:
            if file_exists(dst_file):
                return (dst_file, 2, git_repo_path)
            else:
                return (dst_file, 1, git_repo_path)
    # If the directory does not exist or is not in a git repo
    return (dst_file, 0, None)

def confirm(prompt):
    ans = input(f"{prompt} [y/N]: ").strip().lower()
    return ans == 'y'
