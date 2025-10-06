"""Main pytest configuration file that imports fixtures from other conftest files."""

import os
from pathlib import Path

import pytest

# Import fixtures from conftest_tracker.py
from .conftest_tracker import *  # noqa: F403, F401


@pytest.fixture(scope="session", autouse=True)
def setup_test_reports_dir():
    """Set up test reports directory environment variable."""
    # Force test environment
    os.environ["ENVIRONMENT"] = "test"

    # Import after setting environment
    from radiator.core.config import settings

    # Use TEST_REPORTS_DIR from settings
    test_reports_dir = Path(settings.TEST_REPORTS_DIR)
    test_reports_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (test_reports_dir / "csv").mkdir(exist_ok=True)
    (test_reports_dir / "png").mkdir(exist_ok=True)

    yield test_reports_dir

    # Cleanup: remove test files after tests complete
    import shutil

    if test_reports_dir.exists():
        shutil.rmtree(test_reports_dir, ignore_errors=True)


@pytest.fixture
def test_reports_dir():
    """Get test reports directory for individual tests."""
    from radiator.core.config import settings

    return settings.TEST_REPORTS_DIR
