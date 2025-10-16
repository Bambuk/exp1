"""Service for managing author-team mapping from file."""

from pathlib import Path
from typing import Dict, List

from radiator.core.logging import logger


class AuthorTeamMappingService:
    """Service for loading and managing author-team mapping from file."""

    def __init__(self, mapping_file_path: str):
        """
        Initialize service with mapping file path.

        Args:
            mapping_file_path: Path to the author-team mapping file
        """
        self.mapping_file_path = Path(mapping_file_path)

    def load_author_team_mapping(self) -> Dict[str, str]:
        """
        Load author-team mapping from file.

        Returns:
            Dictionary mapping author names to team names
        """
        mapping = {}

        if not self.mapping_file_path.exists():
            logger.warning(
                f"Author-team mapping file not found: {self.mapping_file_path}"
            )
            return mapping

        try:
            with open(self.mapping_file_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()

                    # Skip empty lines
                    if not line:
                        continue

                    # Validate line format (must contain semicolon)
                    if ";" not in line:
                        logger.warning(
                            f"Invalid line format in {self.mapping_file_path}:{line_num} - "
                            f"missing semicolon: '{line}'"
                        )
                        continue

                    # Split by semicolon
                    parts = line.split(";", 1)  # Split only on first semicolon
                    if len(parts) != 2:
                        logger.warning(
                            f"Invalid line format in {self.mapping_file_path}:{line_num} - "
                            f"expected 'Author;Team' format: '{line}'"
                        )
                        continue

                    author = parts[0].strip()
                    team = parts[1].strip()

                    # Skip if author is empty
                    if not author:
                        logger.warning(
                            f"Empty author in {self.mapping_file_path}:{line_num}: '{line}'"
                        )
                        continue

                    # Use "Без команды" for empty teams
                    if not team:
                        team = "Без команды"

                    mapping[author] = team

            logger.info(
                f"Loaded {len(mapping)} author-team mappings from {self.mapping_file_path}"
            )

        except Exception as e:
            logger.error(
                f"Error loading author-team mapping from {self.mapping_file_path}: {e}"
            )
            return {}

        return mapping

    def get_team_by_author(self, author_name: str) -> str:
        """
        Get team name for given author.

        Args:
            author_name: Name of the author

        Returns:
            Team name or "Без команды" if author not found
        """
        mapping = self.load_author_team_mapping()
        return mapping.get(author_name, "Без команды")

    def get_all_teams(self) -> List[str]:
        """
        Get all unique team names from the mapping.

        Returns:
            List of unique team names
        """
        mapping = self.load_author_team_mapping()
        teams = list(set(mapping.values()))
        teams.sort()  # Sort alphabetically
        return teams
