"""Tests for quarter field support in fullstack subepic returns report."""

import pytest

from radiator.commands.generate_fullstack_subepic_returns_report import (
    FullstackSubepicReturnsReportGenerator,
)
from radiator.models.tracker import TrackerTask


class TestExtractQuarterFromFullData:
    """Test cases for extracting quarter from full_data."""

    def test_extract_quarter_from_full_data_success(self):
        """Test extracting quarter from full_data JSONB."""
        generator = FullstackSubepicReturnsReportGenerator()

        # Mock full_data with quarter field
        full_data = {
            "id": "12345",
            "key": "TEST-123",
            "6361307d94f52e42ae308615--quarter": "2025.Q4",
        }

        result = generator._extract_quarter_from_full_data(full_data)
        assert result == "2025.Q4"

    def test_extract_quarter_from_full_data_missing_field(self):
        """Test extracting quarter when field is missing."""
        generator = FullstackSubepicReturnsReportGenerator()

        # Mock full_data without quarter field
        full_data = {"id": "12345", "key": "TEST-123"}

        result = generator._extract_quarter_from_full_data(full_data)
        assert result is None

    def test_extract_quarter_from_full_data_empty(self):
        """Test extracting quarter from empty full_data."""
        generator = FullstackSubepicReturnsReportGenerator()

        # Test with None
        assert generator._extract_quarter_from_full_data(None) is None

        # Test with empty dict
        assert generator._extract_quarter_from_full_data({}) is None

    def test_extract_quarter_from_full_data_empty_string(self):
        """Test extracting quarter when value is empty string."""
        generator = FullstackSubepicReturnsReportGenerator()

        # Mock full_data with empty quarter
        full_data = {"id": "12345", "6361307d94f52e42ae308615--quarter": ""}

        result = generator._extract_quarter_from_full_data(full_data)
        assert result is None

    def test_extract_quarter_from_full_data_whitespace(self):
        """Test extracting quarter when value is whitespace."""
        generator = FullstackSubepicReturnsReportGenerator()

        # Mock full_data with whitespace quarter
        full_data = {"id": "12345", "6361307d94f52e42ae308615--quarter": "   "}

        result = generator._extract_quarter_from_full_data(full_data)
        assert result is None

    def test_extract_quarter_from_full_data_with_whitespace(self):
        """Test extracting quarter with surrounding whitespace."""
        generator = FullstackSubepicReturnsReportGenerator()

        # Mock full_data with quarter that has whitespace
        full_data = {"id": "12345", "6361307d94f52e42ae308615--quarter": "  2025.Q4  "}

        result = generator._extract_quarter_from_full_data(full_data)
        assert result == "2025.Q4"


class TestFetchEpicQuarters:
    """Test cases for fetching epic quarters in batch."""

    def test_fetch_epic_quarters_batch(self, db_session):
        """Test fetching quarters for multiple epics."""
        # Create test epics with quarters
        epic1 = TrackerTask(
            tracker_id="epic1-id",
            key="EPIC-1",
            summary="Epic 1",
            full_data={"6361307d94f52e42ae308615--quarter": "2025.Q4"},
        )
        epic2 = TrackerTask(
            tracker_id="epic2-id",
            key="EPIC-2",
            summary="Epic 2",
            full_data={"6361307d94f52e42ae308615--quarter": "2025.Q3"},
        )
        epic3 = TrackerTask(
            tracker_id="epic3-id",
            key="EPIC-3",
            summary="Epic 3",
            full_data={},  # No quarter
        )

        db_session.add_all([epic1, epic2, epic3])
        db_session.commit()

        generator = FullstackSubepicReturnsReportGenerator(db=db_session)
        result = generator._fetch_epic_quarters(["EPIC-1", "EPIC-2", "EPIC-3"])

        assert result["EPIC-1"] == "2025.Q4"
        assert result["EPIC-2"] == "2025.Q3"
        assert result["EPIC-3"] is None

    def test_fetch_epic_quarters_empty_list(self, db_session):
        """Test fetching quarters with empty epic list."""
        generator = FullstackSubepicReturnsReportGenerator(db=db_session)
        result = generator._fetch_epic_quarters([])

        assert result == {}

    def test_fetch_epic_quarters_no_db(self):
        """Test fetching quarters without database connection."""
        generator = FullstackSubepicReturnsReportGenerator(db=None)
        result = generator._fetch_epic_quarters(["EPIC-1"])

        assert result == {}


class TestGetQuarterForTaskWithoutEpic:
    """Test cases for getting quarter for tasks without epic."""

    def test_get_quarter_for_task_without_epic(self, db_session):
        """Test extracting quarter from task without epic."""
        # Create test task with quarter
        task = TrackerTask(
            tracker_id="task1-id",
            key="FULLSTACK-123",
            summary="Task 1",
            full_data={"6361307d94f52e42ae308615--quarter": "2025.Q4"},
        )

        db_session.add(task)
        db_session.commit()

        generator = FullstackSubepicReturnsReportGenerator(db=db_session)
        result = generator._get_quarter_for_task_without_epic("FULLSTACK-123")

        assert result == "2025.Q4"

    def test_get_quarter_for_task_without_epic_missing_quarter(self, db_session):
        """Test extracting quarter when task has no quarter."""
        # Create test task without quarter
        task = TrackerTask(
            tracker_id="task2-id", key="FULLSTACK-124", summary="Task 2", full_data={}
        )

        db_session.add(task)
        db_session.commit()

        generator = FullstackSubepicReturnsReportGenerator(db=db_session)
        result = generator._get_quarter_for_task_without_epic("FULLSTACK-124")

        assert result is None

    def test_get_quarter_for_task_without_epic_no_task(self, db_session):
        """Test extracting quarter when task doesn't exist."""
        generator = FullstackSubepicReturnsReportGenerator(db=db_session)
        result = generator._get_quarter_for_task_without_epic("NONEXISTENT-123")

        assert result is None

    def test_get_quarter_for_task_without_epic_no_db(self):
        """Test extracting quarter without database connection."""
        generator = FullstackSubepicReturnsReportGenerator(db=None)
        result = generator._get_quarter_for_task_without_epic("FULLSTACK-123")

        assert result is None


class TestFormatRowWithQuarter:
    """Test cases for format_row with quarter field."""

    def test_format_row_includes_quarter(self, db_session):
        """Test that format_row includes quarter in output."""
        from radiator.commands.generate_fullstack_subepic_returns_report import (
            SubepicInfo,
        )

        generator = FullstackSubepicReturnsReportGenerator(db=db_session)

        info = SubepicInfo(
            key="FULLSTACK-123",
            summary="Test task",
            author="test_author",
            prodteam="Test Team",
            epic_key="EPIC-1",
            epic_summary="Test Epic",
        )

        counts = {
            "InProgress": 1,
            "Ревью": 2,
            "Testing": 3,
            "Внешний тест": 0,
            "Апрув": 1,
            "Регресс-тест": 0,
            "Done": 1,
        }

        row = generator._format_row(
            info, counts, epic_month="2025-12", epic_quarter="2025.Q4"
        )

        assert "Квартал эпика" in row
        assert row["Квартал эпика"] == "2025.Q4"

    def test_format_row_quarter_empty_string(self, db_session):
        """Test that format_row handles missing quarter."""
        from radiator.commands.generate_fullstack_subepic_returns_report import (
            SubepicInfo,
        )

        generator = FullstackSubepicReturnsReportGenerator(db=db_session)

        info = SubepicInfo(
            key="FULLSTACK-123",
            summary="Test task",
            author="test_author",
            prodteam="Test Team",
            epic_key="EPIC-1",
            epic_summary="Test Epic",
        )

        counts = {
            "InProgress": 0,
            "Ревью": 0,
            "Testing": 0,
            "Внешний тест": 0,
            "Апрув": 0,
            "Регресс-тест": 0,
            "Done": 0,
        }

        row = generator._format_row(
            info, counts, epic_month="2025-12", epic_quarter=None
        )

        assert "Квартал эпика" in row
        assert row["Квартал эпика"] == ""


class TestCollectRowsWithQuarters:
    """Integration test for _collect_rows with quarters."""

    def test_collect_rows_with_quarters(self, db_session):
        """Test that _collect_rows includes quarters for epics and tasks."""
        from datetime import datetime

        from radiator.models.tracker import TrackerTaskHistory

        # Create epic with quarter
        epic = TrackerTask(
            tracker_id="epic-id",
            key="EPIC-1",
            summary="Test Epic",
            created_at=datetime(2025, 10, 1),
            full_data={"6361307d94f52e42ae308615--quarter": "2025.Q4"},
        )

        # Create subepic linked to epic
        subepic = TrackerTask(
            tracker_id="subepic-id",
            key="FULLSTACK-100",
            summary="Test Subepic",
            created_at=datetime(2025, 10, 15),
            links=[
                {
                    "type": {"id": "epic"},
                    "direction": "outward",
                    "object": {"key": "EPIC-1", "display": "Test Epic"},
                }
            ],
            full_data={},
        )

        # Create task without epic but with quarter
        standalone_task = TrackerTask(
            tracker_id="standalone-id",
            key="FULLSTACK-200",
            summary="Standalone Task",
            created_at=datetime(2025, 11, 1),
            links=[],
            full_data={"6361307d94f52e42ae308615--quarter": "2025.Q3"},
        )

        db_session.add_all([epic, subepic, standalone_task])
        db_session.commit()

        # Add minimal history
        history1 = TrackerTaskHistory(
            task_id=subepic.id,
            tracker_id=subepic.tracker_id,
            status="InProgress",
            status_display="InProgress",
            start_date=datetime(2025, 10, 15),
        )
        history2 = TrackerTaskHistory(
            task_id=standalone_task.id,
            tracker_id=standalone_task.tracker_id,
            status="InProgress",
            status_display="InProgress",
            start_date=datetime(2025, 11, 1),
        )

        db_session.add_all([history1, history2])
        db_session.commit()

        generator = FullstackSubepicReturnsReportGenerator(
            db=db_session, start_date=datetime(2025, 1, 1)
        )

        rows = generator._collect_rows()

        # Find rows by key
        subepic_row = next(
            (r for r in rows if r["Ключ задачи"] == "FULLSTACK-100"), None
        )
        standalone_row = next(
            (r for r in rows if r["Ключ задачи"] == "FULLSTACK-200"), None
        )

        assert subepic_row is not None
        assert subepic_row["Квартал эпика"] == "2025.Q4"  # From epic

        assert standalone_row is not None
        assert standalone_row["Квартал эпика"] == "2025.Q3"  # From task itself
