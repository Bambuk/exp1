"""
Tests for database isolation - ensuring tests don't connect to production database.

These tests verify that:
1. Test fixtures use test database
2. TrackerSyncCommand warns when created without db parameter in test environment
3. assert_test_database function works correctly
"""

import warnings

import pytest

from radiator.commands.sync_tracker import TrackerSyncCommand
from radiator.core.config import settings
from radiator.core.database import assert_test_database, get_test_database_url_sync


class TestDatabaseIsolation:
    """Test database isolation mechanisms."""

    def test_db_session_uses_test_database(self, db_session):
        """Test that db_session fixture uses test database."""
        # Get database URL from session
        db_url = str(db_session.bind.url)

        # Should contain test database name
        assert (
            "radiator_test" in db_url or "test" in db_url.lower()
        ), f"db_session fixture should use test database, but got: {db_url}"

    def test_sync_command_fixture_uses_test_database(self, sync_command):
        """Test that sync_command fixture uses test database."""
        # Get database URL from sync_command's db session
        db_url = str(sync_command.db.bind.url)

        # Should contain test database name
        assert (
            "radiator_test" in db_url or "test" in db_url.lower()
        ), f"sync_command fixture should use test database, but got: {db_url}"

    def test_tracker_sync_command_warns_without_db_in_test_env(self):
        """Test that TrackerSyncCommand warns when created without db in test environment."""
        # Only test if we're in test environment
        if settings.ENVIRONMENT != "test":
            pytest.skip("Not in test environment")

        # Should raise warning when creating TrackerSyncCommand without db parameter
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            cmd = TrackerSyncCommand()

            # Should have at least one warning
            assert (
                len(w) > 0
            ), "Expected warning when creating TrackerSyncCommand without db"

            # Check that warning message contains expected text
            warning_messages = [str(warning.message) for warning in w]
            assert any(
                "db parameter" in msg.lower() for msg in warning_messages
            ), f"Expected warning about db parameter, got: {warning_messages}"

            # Cleanup
            cmd.db.close()

    def test_tracker_sync_command_no_warning_with_db(self, db_session):
        """Test that TrackerSyncCommand doesn't warn when db is provided."""
        # Should not raise warning when db is provided
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            cmd = TrackerSyncCommand(db=db_session)

            # Should not have warnings about db parameter
            warning_messages = [str(warning.message) for warning in w]
            db_warnings = [
                msg for msg in warning_messages if "db parameter" in msg.lower()
            ]
            assert (
                len(db_warnings) == 0
            ), f"Should not warn when db is provided, but got: {db_warnings}"

    def test_assert_test_database_raises_on_production_url(self):
        """Test that assert_test_database raises error on production URL in test environment."""
        # Only test if we're in test environment
        if settings.ENVIRONMENT != "test":
            pytest.skip("Not in test environment")

        # Should raise RuntimeError for production database URL
        prod_url = "postgresql://postgres:12345@192.168.1.108:5432/radiator"

        with pytest.raises(RuntimeError, match="non-test database"):
            assert_test_database(prod_url)

    def test_assert_test_database_passes_on_test_url(self):
        """Test that assert_test_database passes on test database URL."""
        # Only test if we're in test environment
        if settings.ENVIRONMENT != "test":
            pytest.skip("Not in test environment")

        # Should not raise for test database URL
        test_url = get_test_database_url_sync()
        assert_test_database(test_url)  # Should not raise

    def test_sync_command_with_fixture_creates_sync_log_in_test_db(
        self, sync_command, db_session
    ):
        """Test that sync_command creates sync_log in test database, not production."""
        from radiator.models.tracker import TrackerSyncLog

        # Count sync logs before
        initial_count = db_session.query(TrackerSyncLog).count()

        # Create sync log
        sync_log = sync_command.create_sync_log()

        # Verify sync log was created
        assert sync_log is not None
        assert sync_log.id is not None

        # Count sync logs after
        final_count = db_session.query(TrackerSyncLog).count()
        assert (
            final_count == initial_count + 1
        ), "Sync log should be created in test database"

        # Verify sync log is in test database
        found_log = db_session.query(TrackerSyncLog).filter_by(id=sync_log.id).first()
        assert found_log is not None, "Sync log should be found in test database"

        # Cleanup
        db_session.delete(sync_log)
        db_session.commit()
