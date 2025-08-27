#!/usr/bin/env python3
"""
Script for syncing data from Yandex Tracker.
This script can be run manually or via cron.

Usage:
    python sync_tracker.py <task_list_file> [--force-full-sync] [--debug]

Example:
    python sync_tracker.py tasks.txt --debug
    python sync_tracker.py tasks.txt --force-full-sync
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from radiator.commands.sync_tracker import main

if __name__ == "__main__":
    main()
