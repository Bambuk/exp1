#!/usr/bin/env python3
"""
Script for syncing data from Yandex Tracker.
This script can be run manually or via cron.

Usage:
    python sync_tracker.py [--sync-mode MODE] [--days DAYS] [--limit LIMIT] [--status STATUS] [--assignee ASSIGNEE] [--team TEAM] [--force-full-sync] [--debug]

Examples:
    # Sync recent tasks (default)
    python sync_tracker.py
    
    # Sync active tasks
    python sync_tracker.py --sync-mode active
    
    # Sync tasks updated in last 7 days
    python sync_tracker.py --days 7
    
    # Sync tasks with specific status
    python sync_tracker.py --status "In Progress" --limit 50
    
    # Sync tasks for specific assignee
    python sync_tracker.py --assignee "john.doe" --sync-mode filter
    
    # Legacy mode - sync from file
    python sync_tracker.py --sync-mode file --file-path tasks.txt
    
    # Force full sync
    python sync_tracker.py --force-full-sync
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from radiator.commands.sync_tracker import main

if __name__ == "__main__":
    main()
