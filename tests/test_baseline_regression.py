"""Baseline regression tests for TTM Details Report.

This test ensures that refactoring doesn't break existing functionality.
It generates a report and compares it with a pre-generated baseline.
"""

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from radiator.commands.generate_ttm_details_report import TTMDetailsReportGenerator
from radiator.models.tracker import TrackerTask, TrackerTaskHistory


@pytest.fixture
def baseline_test_data(db_session):
    """Create baseline test data in database.

    Creates 3 tasks with complete history:
    1. CPO-100: Completed task with full workflow
    2. CPO-101: Completed task with pauses
    3. CPO-102: Unfinished task (no stable_done)
    """
    # Clear existing data
    db_session.query(TrackerTaskHistory).delete()
    db_session.query(TrackerTask).delete()
    db_session.commit()

    # Start date within Q1 2025 (2025-01-27 to 2025-04-20)
    base_date = datetime(2025, 2, 1, tzinfo=timezone.utc)

    # Task 1: CPO-100 - Completed task with full workflow
    task1 = TrackerTask(
        tracker_id="100",
        key="CPO-100",
        summary="Baseline Test Task 1",
        status="Done",
        author="Test Author",
        team="Test Team",
        created_at=base_date,
    )
    db_session.add(task1)
    db_session.flush()

    # History for CPO-100
    history1 = [
        # Creation
        TrackerTaskHistory(
            task_id=task1.id,
            tracker_id=task1.tracker_id,
            status="Открыт",
            status_display="Открыт",
            start_date=base_date,
            end_date=base_date + timedelta(days=1),
        ),
        # Discovery backlog
        TrackerTaskHistory(
            task_id=task1.id,
            tracker_id=task1.tracker_id,
            status="Discovery backlog",
            status_display="Discovery backlog",
            start_date=base_date + timedelta(days=1),
            end_date=base_date + timedelta(days=3),
        ),
        # Ready for development
        TrackerTaskHistory(
            task_id=task1.id,
            tracker_id=task1.tracker_id,
            status="Готова к разработке",
            status_display="Готова к разработке",
            start_date=base_date + timedelta(days=3),
            end_date=base_date + timedelta(days=5),
        ),
        # In work
        TrackerTaskHistory(
            task_id=task1.id,
            tracker_id=task1.tracker_id,
            status="МП / В работе",
            status_display="МП / В работе",
            start_date=base_date + timedelta(days=5),
            end_date=base_date + timedelta(days=15),
        ),
        # External test
        TrackerTaskHistory(
            task_id=task1.id,
            tracker_id=task1.tracker_id,
            status="МП / Внешний тест",
            status_display="МП / Внешний тест",
            start_date=base_date + timedelta(days=15),
            end_date=base_date + timedelta(days=18),
        ),
        # Done
        TrackerTaskHistory(
            task_id=task1.id,
            tracker_id=task1.tracker_id,
            status="Done",
            status_display="Done",
            start_date=base_date + timedelta(days=18),
            end_date=None,
        ),
    ]
    for h in history1:
        db_session.add(h)

    # Task 2: CPO-101 - Completed task with pauses
    task2 = TrackerTask(
        tracker_id="101",
        key="CPO-101",
        summary="Baseline Test Task 2 with Pauses",
        status="Done",
        author="Test Author 2",
        team="Test Team 2",
        created_at=base_date,
    )
    db_session.add(task2)
    db_session.flush()

    # History for CPO-101 with pauses
    history2 = [
        # Creation
        TrackerTaskHistory(
            task_id=task2.id,
            tracker_id=task2.tracker_id,
            status="Открыт",
            status_display="Открыт",
            start_date=base_date,
            end_date=base_date + timedelta(days=1),
        ),
        # Ready for development
        TrackerTaskHistory(
            task_id=task2.id,
            tracker_id=task2.tracker_id,
            status="Готова к разработке",
            status_display="Готова к разработке",
            start_date=base_date + timedelta(days=1),
            end_date=base_date + timedelta(days=3),
        ),
        # Pause 1
        TrackerTaskHistory(
            task_id=task2.id,
            tracker_id=task2.tracker_id,
            status="Пауза",
            status_display="Пауза",
            start_date=base_date + timedelta(days=3),
            end_date=base_date + timedelta(days=6),
        ),
        # In work
        TrackerTaskHistory(
            task_id=task2.id,
            tracker_id=task2.tracker_id,
            status="МП / В работе",
            status_display="МП / В работе",
            start_date=base_date + timedelta(days=6),
            end_date=base_date + timedelta(days=10),
        ),
        # External test
        TrackerTaskHistory(
            task_id=task2.id,
            tracker_id=task2.tracker_id,
            status="МП / Внешний тест",
            status_display="МП / Внешний тест",
            start_date=base_date + timedelta(days=10),
            end_date=base_date + timedelta(days=12),
        ),
        # Done
        TrackerTaskHistory(
            task_id=task2.id,
            tracker_id=task2.tracker_id,
            status="Done",
            status_display="Done",
            start_date=base_date + timedelta(days=12),
            end_date=None,
        ),
    ]
    for h in history2:
        db_session.add(h)

    # Task 3: CPO-102 - Unfinished task (no stable_done)
    task3 = TrackerTask(
        tracker_id="102",
        key="CPO-102",
        summary="Baseline Test Task 3 Unfinished",
        status="МП / В работе",
        author="Test Author 3",
        team="Test Team 3",
        created_at=base_date,
    )
    db_session.add(task3)
    db_session.flush()

    # History for CPO-102 - unfinished
    history3 = [
        # Creation
        TrackerTaskHistory(
            task_id=task3.id,
            tracker_id=task3.tracker_id,
            status="Открыт",
            status_display="Открыт",
            start_date=base_date,
            end_date=base_date + timedelta(days=1),
        ),
        # Ready for development
        TrackerTaskHistory(
            task_id=task3.id,
            tracker_id=task3.tracker_id,
            status="Готова к разработке",
            status_display="Готова к разработке",
            start_date=base_date + timedelta(days=1),
            end_date=base_date + timedelta(days=4),
        ),
        # In work (current status - no end_date)
        TrackerTaskHistory(
            task_id=task3.id,
            tracker_id=task3.tracker_id,
            status="МП / В работе",
            status_display="МП / В работе",
            start_date=base_date + timedelta(days=4),
            end_date=None,
        ),
    ]
    for h in history3:
        db_session.add(h)

    db_session.commit()

    return [task1, task2, task3]


@pytest.fixture
def baseline_csv_path():
    """Path to baseline CSV file."""
    return Path(__file__).parent / "fixtures" / "baseline_ttm_details.csv"


@pytest.fixture
def generate_baseline_if_missing(
    baseline_test_data, baseline_csv_path, db_session, test_reports_dir
):
    """Generate baseline CSV if it doesn't exist."""
    if not baseline_csv_path.exists():
        print(f"\n📝 Generating baseline CSV at {baseline_csv_path}")

        # Ensure fixtures directory exists
        baseline_csv_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate report with current implementation
        generator = TTMDetailsReportGenerator(db=db_session, config_dir="data/config")
        generator.generate_csv(str(baseline_csv_path))

        print(f"✅ Baseline CSV generated: {baseline_csv_path}")
    else:
        print(f"\n✅ Using existing baseline: {baseline_csv_path}")

    return baseline_csv_path


def test_baseline_consistency(
    baseline_test_data,
    baseline_csv_path,
    generate_baseline_if_missing,
    db_session,
    test_reports_dir,
):
    """Test that current implementation produces the same results as baseline.

    This test:
    1. Uses the same test data as baseline
    2. Generates a new report
    3. Compares it with baseline CSV line by line
    4. Fails if there are any differences

    If this test fails after refactoring, it means the behavior has changed.
    Review the changes carefully to ensure they are intentional.
    """
    # Generate current report
    current_csv_path = Path(test_reports_dir) / "current_ttm_details.csv"
    generator = TTMDetailsReportGenerator(db=db_session, config_dir="data/config")
    generator.generate_csv(str(current_csv_path))

    # Read both CSVs
    with open(baseline_csv_path, "r", encoding="utf-8") as f:
        baseline_rows = list(csv.DictReader(f))

    with open(current_csv_path, "r", encoding="utf-8") as f:
        current_rows = list(csv.DictReader(f))

    # Compare number of rows
    assert len(current_rows) == len(baseline_rows), (
        f"Number of rows mismatch: baseline={len(baseline_rows)}, "
        f"current={len(current_rows)}"
    )

    # Compare each row
    for i, (baseline_row, current_row) in enumerate(zip(baseline_rows, current_rows)):
        # Compare all columns
        for col in baseline_row.keys():
            baseline_val = baseline_row[col]
            current_val = current_row.get(col, "")

            assert current_val == baseline_val, (
                f"Row {i+1}, Column '{col}' mismatch:\n"
                f"  Baseline: {baseline_val}\n"
                f"  Current:  {current_val}\n"
                f"  Task: {baseline_row.get('Ключ задачи', 'unknown')}"
            )

    print(f"✅ Baseline consistency check passed: {len(baseline_rows)} rows match")


def test_baseline_file_exists(baseline_csv_path, generate_baseline_if_missing):
    """Test that baseline file exists and is readable."""
    assert baseline_csv_path.exists(), f"Baseline file not found: {baseline_csv_path}"

    # Check that it's a valid CSV
    with open(baseline_csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        rows = list(reader)

    # Verify expected columns exist
    expected_columns = [
        "Ключ задачи",
        "Название",
        "Автор",
        "Команда",
        "PM Lead",
        "Квартал",
        "TTM",
        "Пауза",
        "Tail",
        "DevLT",
        "TTD",
    ]

    for col in expected_columns:
        assert col in headers, f"Expected column '{col}' not found in baseline"

    print(f"✅ Baseline file is valid: {len(rows)} rows, {len(headers)} columns")
