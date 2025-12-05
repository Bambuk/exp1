"""Service for managing team-lead mapping from file."""

from pathlib import Path
from typing import Dict

from radiator.core.logging import logger


class TeamLeadMappingService:
    """Service for loading and managing team-lead mapping from file."""

    def __init__(self, mapping_file_path: str):
        """
        Initialize service with mapping file path.

        Args:
            mapping_file_path: Path to the team-lead mapping file
        """
        self.mapping_file_path = Path(mapping_file_path)

    def load_team_lead_mapping(self) -> Dict[str, str]:
        """
        Load team-lead mapping from file.

        Returns:
            Dictionary mapping team names to PM Lead names
        """
        mapping = {}

        if not self.mapping_file_path.exists():
            logger.warning(
                f"Team-lead mapping file not found: {self.mapping_file_path}"
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
                            f"expected 'Team;PM Lead' format: '{line}'"
                        )
                        continue

                    team = parts[0].strip()
                    lead = parts[1].strip()

                    # Skip if team is empty
                    if not team:
                        logger.warning(
                            f"Empty team in {self.mapping_file_path}:{line_num}: '{line}'"
                        )
                        continue

                    # Use "Без команды" for empty leads
                    if not lead:
                        lead = "Без команды"

                    mapping[team] = lead

            logger.info(
                f"Loaded {len(mapping)} team-lead mappings from {self.mapping_file_path}"
            )

        except Exception as e:
            logger.error(
                f"Error loading team-lead mapping from {self.mapping_file_path}: {e}"
            )
            return {}

        return mapping

    def get_lead_by_team(self, team_name: str) -> str:
        """
        Get PM Lead name for given team.

        Args:
            team_name: Name of the team

        Returns:
            PM Lead name or "Без команды" if team not found
        """
        mapping = self.load_team_lead_mapping()
        return mapping.get(team_name, "Без команды")
