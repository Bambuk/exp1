"""Utility for loading fields configuration from file."""

from pathlib import Path
from typing import List


def load_fields_list(fields_file: Path = None) -> List[str]:
    """
    Load fields list from config file.

    Args:
        fields_file: Path to fields file. If None, uses default path.

    Returns:
        List of field names, with empty lines filtered out and whitespace stripped.

    Raises:
        FileNotFoundError: If the fields file doesn't exist.
    """
    if fields_file is None:
        # Default path: project_root/data/config/fields.txt
        fields_file = (
            Path(__file__).parent.parent.parent / "data" / "config" / "fields.txt"
        )

    with open(fields_file, "r") as f:
        fields = [line.strip() for line in f if line.strip()]

    return fields
