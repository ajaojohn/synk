import time
import synk.config as config
import synk.utils as utils
import synk.sync as sync
from synk.utils import print_error, print_success, print_warning
import sys
import os
from prompt_toolkit import prompt
from prompt_toolkit.completion import PathCompleter

completer = PathCompleter(expanduser=True)


def main():
    print("Starting Synk.......")

    # Ensure a config file exists
    config.check_config_file_exists()

    # Load config
    cfg = config.load_config()

    # Run main menu
    run_main_menu(cfg)

def print_main_menu_options(cfg):
    """
    Display main menu options
    """
    # Ask user to choose a profile or create a new one
    print("\nWelcome to Synk CLI")
    print("- 'create' -> To create a new profile type.")
    print("- 'select \{prof_number\}' -> To select an existing profile type e.g 'select 1'.")
    print("- 'exit' -> to exit Synk.")
    print("{:-<40}".format(" "))  # Separator line
    print("Profiles:")
    for i, profile in enumerate(cfg["profiles"]):
        print(f"\t{str(i+1).rjust(2)}. {profile}")


def run_main_menu(cfg):
    """
    Run Synk main menu
    """
    # Handle user choice
    print_options = True
    while (True):
        if print_options:
            print_main_menu_options(cfg)

        choice = input("\nEnter your choice: ").strip().lower()

        if choice == "create":
        # Create a new profile
            run_create_profile_menu(cfg)
            print_options = False

        elif choice.startswith("select"):
        # Select an existing profile
            # Ensure correct format
            parts = choice.split()
            if len(parts) != 2 or not parts[1].isdigit():
                print_error("Invalid format for 'select'. Use 'select {profile_number}'")
                print_options = False
                continue
            profile_index = int(parts[1]) - 1
            if not utils.profile_index_is_valid(cfg, profile_index):
                print_error("Invalid profile number")
                print_options = False
                continue

            run_profile_menu(cfg, profile_index)
            print_options = True

        elif choice == "exit":
            print("Exiting Synk CLI.")
            sys.exit(0)
        else:
            print_error("Invalid choice")
            print_options = False






def run_create_profile_menu(cfg):
    """
    Create and store a new profile
    """
    print("Create a new profile")
    profile_name = ""
    profile_name = input("\nEnter new profile name: ").strip()
    utils.cfg_add_profile(cfg, profile_name)




def print_main_profile_menu_options(cfg, profile_index):
    """
    Display profile menu options
    """
    profile_name = list(cfg["profiles"].keys())[profile_index]
    print(f"\nProfile: {profile_name}")

    print("Syncs:")
    print("{:-<40}".format(" "))  # Separator line
    syncs = cfg["profiles"][profile_name].get("syncs", [])
    if not syncs:
        print("\tNo syncs found.")
    else:
        for i, sync in enumerate(cfg["profiles"][profile_name].get("syncs", [])):
            print(f"\t{str(i+1).rjust(2)}. {sync['source_file']} -> {sync['destination_repo_file']}")

    print("\n- 'add' -> To add a new sync.")
    print("- 'remove {sync_number}' -> To remove an existing sync e.g 'remove 1'.")
    print("- 'sync all' -> To sync all files in this profile.")
    print("- 'back' -> To go back to main menu.")
    print("- 'exit' -> To exit Synk.")


def run_profile_menu(cfg, profile_index):
    """
    Must have already validated profile_index
    Display and handle profile menu
    """
    ## Display profile menu
    print_options = True

    while True:
        if print_options:
            print_main_profile_menu_options(cfg, profile_index)
        choice = input("\nEnter your choice: ").strip().lower()

        if choice == "add":
        # Add a new sync
            profile_name = list(cfg["profiles"].keys())[profile_index]
            run_add_sync_menu(cfg, profile_name)
            print_options = True

        elif choice.startswith("remove"):
        # Remove an existing sync
            parts = choice.split()
            if len(parts) != 2 or not parts[1].isdigit():
                print_error("Invalid format for 'remove'. Use 'remove {sync_number}'")
                continue
            sync_index = int(parts[1]) - 1

            utils.cfg_remove_sync(cfg, profile_name, sync_index)
            print_options = True

        elif choice == "sync all":
            # Sync all files in this profile
            profile_name = list(cfg["profiles"].keys())[profile_index]
            sync.sync_all(cfg, profile_name)
            print_options = True

        elif choice == "back":
            print("Returning to main menu.")
            return
        elif choice == "exit":
            print("Exiting Synk CLI.")
            sys.exit(0)
        else:
            print_error("Invalid choice")
            print_options = False

def run_add_sync_menu(cfg, profile_name):
    """
    Add a new sync to the specified profile
    """
    print("Add a new sync")

    # Get source file and ensure it exists
    source_file = prompt("\nEnter source file path (file to by synced): ", completer = completer).strip()
    source_file, source_is_valid = utils.is_valid_source_file(source_file)
    while source_is_valid is False:
        print_error(f"Invalid source file '{source_file}'. Please ensure the file exists and is accessible.")
        source_file = prompt("\nEnter source file path (file to by synced): ", completer = completer).strip()
        source_file, source_is_valid = utils.is_valid_source_file(source_file)
    print_success(f"Source file '{source_file}' is valid.")

    # Get destination file and ensure it is valid
    dst_file = prompt("Enter destination repository file path (repo file containing file to be updated): ", completer = completer).strip()
    dst_file, dst_is_valid, git_repo_path = utils.is_valid_destination_file(dst_file)
    while dst_is_valid == 0:
        print_error(f"Invalid destination repository file '{dst_file}'. Please ensure the destination directory exists and is accessible.")
        dst_file = prompt("Enter destination repository file path (repo file containing file to be updated): ", completer = completer).strip()
        dst_file, dst_is_valid, git_repo_path = utils.is_valid_destination_file(dst_file)
    # if dst_is_valid == 0# :
    #     print_error(f" Invalid destination repository file '{dst_file}'. Please ensure the destination directory exists and is accessible.")
    #     return
    if dst_is_valid == 1:
        print_warning(f"This will create a new file at '{dst_file}' in git repo '{git_repo_path}'.")
    elif dst_is_valid == 2:
        print_success(f"Destination file '{dst_file}' located in git repo '{git_repo_path}'.")

    # Confirm adding the sync
    confirmed = input("Confirm adding this sync? (y/n): ").strip().lower()
    while confirmed not in ['y', 'n']:
        print_error("Invalid input. Please enter 'y' or 'n'.")
        confirmed = input("Confirm adding this sync? (y/n): ").strip().lower()

    if confirmed == 'n':
        print_error("Sync addition cancelled.")
        return
    else:
        # Add the sync if confirmed
        utils.cfg_add_sync(cfg, profile_name, source_file, dst_file)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')
