"""Configuration service for Time To Market report."""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from radiator.commands.models.time_to_market_models import Quarter, StatusMapping
from radiator.core.logging import logger


class ConfigService:
    """Service for loading and managing configuration."""

    def __init__(self, config_dir: str = "data/config"):
        """
        Initialize configuration service.

        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)

    def load_quarters(self) -> List[Quarter]:
        """
        Load quarters/periods from file.

        Returns:
            List of Quarter objects
        """
        try:
            quarters_file = self.config_dir / "quarters.txt"
            if not quarters_file.exists():
                logger.warning(f"Quarters file not found: {quarters_file}")
                return []

            quarters = []
            with open(quarters_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and ";" in line:
                        try:
                            name, start_str, end_str = line.split(";", 2)
                            start_date = datetime.strptime(
                                start_str.strip(), "%Y-%m-%d"
                            )
                            end_date = datetime.strptime(end_str.strip(), "%Y-%m-%d")

                            quarters.append(
                                Quarter(
                                    name=name.strip(),
                                    start_date=start_date,
                                    end_date=end_date,
                                )
                            )
                        except ValueError as e:
                            logger.warning(
                                f"Failed to parse quarter line '{line}': {e}"
                            )
                            continue

            logger.info(f"Loaded {len(quarters)} quarters")
            return quarters

        except Exception as e:
            logger.error(f"Failed to load quarters: {e}")
            return []

    def load_status_mapping(self) -> StatusMapping:
        """
        Load status to block mapping from file.

        Returns:
            StatusMapping object
        """
        try:
            mapping_file = self.config_dir / "status_order.txt"
            if not mapping_file.exists():
                logger.warning(f"Status mapping file not found: {mapping_file}")
                return StatusMapping(discovery_statuses=[], done_statuses=[])

            discovery_statuses = []
            done_statuses = []

            with open(mapping_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and ";" in line:
                        status, block = line.split(";", 1)
                        status = status.strip()
                        block = block.strip()

                        if block == "discovery":
                            discovery_statuses.append(status)
                        elif block == "done":
                            done_statuses.append(status)

            logger.info(
                f"Loaded {len(discovery_statuses)} discovery and {len(done_statuses)} done statuses"
            )
            return StatusMapping(
                discovery_statuses=discovery_statuses, done_statuses=done_statuses
            )

        except Exception as e:
            logger.error(f"Failed to load status mapping: {e}")
            return StatusMapping(discovery_statuses=[], done_statuses=[])
