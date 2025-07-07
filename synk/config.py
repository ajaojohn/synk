import json
from pathlib import Path
import sys

CONFIG_FILE = Path("config.json")

DEFAULT_CONFIG = {
    "settings": {},
    "profiles": {}
}

"""
Profiles structure:
{
    "settings": { },
    "profiles": {
        "profile1": {
            syncs: [
                {
                    "source_file": "/path/to/file",
                    "destination_repo_file": "/path/to/destination",
                },
                ...
            ]
        }, ...
    }
}
"""


def check_config_file_exists():
    """
    Check if the config file already exists in script's root dir, if not create a

    - If CONFIG_FILE exists, the function does nothing
    - Else, attempts to create a default config file
    """
    if (CONFIG_FILE.exists()):
        return

    try:
        with CONFIG_FILE.open("w") as f:
            json.dump(DEFAULT_CONFIG, f, indent = 2)
            print(f"[✓] Created default config file.")
    except Exception as e:
        print(f"[X] Error creating a default {CONFIG_FILE}: {e}")
        sys.exit(1)


def load_config():
    """
    Loads and returns config dict from config
    (Call only after check_config_file_exists)
    """

    try:
        with CONFIG_FILE.open() as f:
            return json.load(f)
    except Exception as e:
            print(f"[X] Error loading {CONFIG_FILE}: {e}")
            sys.exit(1)


def update_config(cfg):
    """
    Updates the config file with the given config dict
    """

    try:
        with CONFIG_FILE.open("w") as f:
            json.dump(cfg, f, indent = 2)
            return True
    except Exception as e:
            print(f"[X] Error updating {CONFIG_FILE}: {e}")
            return False
