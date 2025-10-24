"""Main application entry point for CLI commands."""

from radiator.core.config import settings
from radiator.core.logging import setup_logging


def main():
    """Main function - CLI application entry point."""
    setup_logging()
    print(f"Radiator CLI v{settings.APP_VERSION}")
    print("Use specific commands like:")
    print("  python -m radiator.commands.generate_status_change_report")
    print("  python -m radiator.commands.generate_ttm_details_report")
    print("  python -m radiator.commands.sync_tracker")


if __name__ == "__main__":
    main()
