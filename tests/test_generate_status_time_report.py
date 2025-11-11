import csv
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def tmp_csv_path(tmp_path: Path) -> Path:
    return tmp_path / "status_time_report.csv"


def test_generate_csv_report_basic(tmp_csv_path):
    from radiator.commands.generate_status_time_report import StatusTimeReportGenerator

    generator = StatusTimeReportGenerator(data_service=MagicMock())

    tasks = [SimpleNamespace(id=1, key="CPO-1")]
    statuses = ["Discovery", "Delivery"]
    status_times = {"Discovery": 2, "Delivery": 3}

    histories = {"CPO-1": [MagicMock()]}

    generator._ensure_output_dir = MagicMock()
    generator._get_tasks = MagicMock(return_value=tasks)
    generator.data_service.get_task_histories_by_keys_batch.return_value = histories
    generator._collect_unique_statuses = MagicMock(return_value=statuses)
    generator._calculate_status_times = MagicMock(return_value=status_times)

    csv_path = generator.generate_csv(queue="CPO", output_path=tmp_csv_path)

    assert csv_path.exists()

    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        row = next(reader)

    assert header == ["Ключ задачи", "Discovery", "Delivery"]
    assert row == ["CPO-1", "2", "3"]

    generator._get_tasks.assert_called_once()
    generator.data_service.get_task_histories_by_keys_batch.assert_called_once_with(
        ["CPO-1"]
    )
    generator._collect_unique_statuses.assert_called_once_with(tasks, histories)
    generator._calculate_status_times.assert_called_once_with(histories["CPO-1"])


def test_generate_csv_with_multiple_tasks(tmp_csv_path):
    from radiator.commands.generate_status_time_report import StatusTimeReportGenerator

    generator = StatusTimeReportGenerator(data_service=MagicMock())

    tasks = [SimpleNamespace(id=1, key="CPO-1"), SimpleNamespace(id=2, key="CPO-2")]
    statuses = ["Discovery", "Done"]
    histories = {
        "CPO-1": [MagicMock()],
        "CPO-2": [MagicMock()],
    }

    generator._ensure_output_dir = MagicMock()
    generator._get_tasks = MagicMock(return_value=tasks)
    generator.data_service.get_task_histories_by_keys_batch.return_value = histories
    generator._collect_unique_statuses = MagicMock(return_value=statuses)
    generator._calculate_status_times = MagicMock(
        side_effect=[
            {"Discovery": 1, "Done": 0},
            {"Done": 5},
        ]
    )

    csv_path = generator.generate_csv(queue="CPO", output_path=tmp_csv_path)

    with open(csv_path, newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))

    assert rows[0] == ["Ключ задачи", "Discovery", "Done"]
    assert rows[1] == ["CPO-1", "1", "0"]
    assert rows[2] == ["CPO-2", "", "5"]

    generator.data_service.get_task_histories_by_keys_batch.assert_called_once_with(
        ["CPO-1", "CPO-2"]
    )
    generator._collect_unique_statuses.assert_called_once_with(tasks, histories)


def test_get_tasks_by_queue():
    from radiator.commands.generate_status_time_report import StatusTimeReportGenerator

    fake_tasks = [
        SimpleNamespace(id=1, key="CPO-1"),
        SimpleNamespace(id=2, key="CPO-2"),
    ]

    data_service = MagicMock()
    data_service.get_tasks_by_queue.return_value = fake_tasks

    generator = StatusTimeReportGenerator(data_service=data_service)

    tasks = generator._get_tasks(queue="CPO", created_since=None)

    data_service.get_tasks_by_queue.assert_called_once_with("CPO", None)
    assert tasks == fake_tasks


def test_get_tasks_by_queue_with_date():
    from radiator.commands.generate_status_time_report import StatusTimeReportGenerator

    cutoff = datetime(2025, 1, 15, tzinfo=timezone.utc)
    fake_tasks = [SimpleNamespace(id=3, key="CPO-3")]

    data_service = MagicMock()
    data_service.get_tasks_by_queue.return_value = fake_tasks

    generator = StatusTimeReportGenerator(data_service=data_service)

    tasks = generator._get_tasks(queue="CPO", created_since=cutoff)

    data_service.get_tasks_by_queue.assert_called_once_with("CPO", cutoff)
    assert tasks == fake_tasks


def test_collect_unique_statuses():
    from radiator.commands.generate_status_time_report import StatusTimeReportGenerator
    from radiator.commands.models.time_to_market_models import StatusHistoryEntry

    tasks = [SimpleNamespace(id=1), SimpleNamespace(id=2)]

    data_service = MagicMock()
    data_service.get_task_history.side_effect = [
        [
            StatusHistoryEntry(
                status="Discovery",
                status_display="Discovery",
                start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
                end_date=None,
            ),
            StatusHistoryEntry(
                status="Delivery",
                status_display="Delivery",
                start_date=datetime(2025, 1, 5, tzinfo=timezone.utc),
                end_date=None,
            ),
        ],
        [
            StatusHistoryEntry(
                status="Discovery",
                status_display="Discovery",
                start_date=datetime(2025, 1, 2, tzinfo=timezone.utc),
                end_date=None,
            ),
            StatusHistoryEntry(
                status="Done",
                status_display="Done",
                start_date=datetime(2025, 1, 10, tzinfo=timezone.utc),
                end_date=None,
            ),
        ],
    ]

    generator = StatusTimeReportGenerator(data_service=data_service)

    statuses = generator._collect_unique_statuses(tasks)

    assert statuses == ["Delivery", "Discovery", "Done"]


def test_collect_unique_statuses_empty_history():
    from radiator.commands.generate_status_time_report import StatusTimeReportGenerator

    tasks = [SimpleNamespace(id=1)]

    data_service = MagicMock()
    data_service.get_task_history.return_value = []

    generator = StatusTimeReportGenerator(data_service=data_service)

    statuses = generator._collect_unique_statuses(tasks)

    assert statuses == []


def test_generate_csv_no_tasks(tmp_csv_path):
    from radiator.commands.generate_status_time_report import StatusTimeReportGenerator

    data_service = MagicMock()

    generator = StatusTimeReportGenerator(data_service=data_service)
    generator._ensure_output_dir = MagicMock()
    generator._get_tasks = MagicMock(return_value=[])
    generator.data_service.get_task_histories_by_keys_batch = MagicMock()
    generator._collect_unique_statuses = MagicMock()
    generator._calculate_status_times = MagicMock()

    csv_path = generator.generate_csv(queue="CPO", output_path=tmp_csv_path)

    with open(csv_path, newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))

    assert rows == [["Ключ задачи"]]
    generator.data_service.get_task_histories_by_keys_batch.assert_not_called()
    generator._collect_unique_statuses.assert_not_called()
    generator._calculate_status_times.assert_not_called()


def test_main_invalid_created_since(monkeypatch):
    from radiator.commands.generate_status_time_report import main

    monkeypatch.setenv("PYTHONWARNINGS", "ignore")
    monkeypatch.setattr(
        "radiator.commands.generate_status_time_report.SessionLocal", MagicMock()
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "generate_status_time_report",
            "--queue",
            "CPO",
            "--created-since",
            "invalid-date",
        ],
    )

    with pytest.raises(SystemExit) as exc:
        main()

    assert "Invalid --created-since format" in str(exc.value)


def test_calculate_status_times_single_task():
    from radiator.commands.generate_status_time_report import StatusTimeReportGenerator
    from radiator.commands.models.time_to_market_models import StatusHistoryEntry

    history = [
        StatusHistoryEntry(
            status="Discovery",
            status_display="Discovery",
            start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2025, 1, 3, tzinfo=timezone.utc),
        ),
        StatusHistoryEntry(
            status="Delivery",
            status_display="Delivery",
            start_date=datetime(2025, 1, 3, tzinfo=timezone.utc),
            end_date=datetime(2025, 1, 6, tzinfo=timezone.utc),
        ),
        StatusHistoryEntry(
            status="Done",
            status_display="Done",
            start_date=datetime(2025, 1, 6, tzinfo=timezone.utc),
            end_date=None,
        ),
    ]

    data_service = MagicMock()
    generator = StatusTimeReportGenerator(data_service=data_service)

    times = generator._calculate_status_times(history)

    assert times == {"Discovery": 2, "Delivery": 3}


def test_calculate_status_times_multiple_visits():
    from radiator.commands.generate_status_time_report import StatusTimeReportGenerator
    from radiator.commands.models.time_to_market_models import StatusHistoryEntry

    history = [
        StatusHistoryEntry(
            status="Discovery",
            status_display="Discovery",
            start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2025, 1, 2, tzinfo=timezone.utc),
        ),
        StatusHistoryEntry(
            status="Delivery",
            status_display="Delivery",
            start_date=datetime(2025, 1, 2, tzinfo=timezone.utc),
            end_date=datetime(2025, 1, 4, tzinfo=timezone.utc),
        ),
        StatusHistoryEntry(
            status="Discovery",
            status_display="Discovery",
            start_date=datetime(2025, 1, 4, tzinfo=timezone.utc),
            end_date=datetime(2025, 1, 6, tzinfo=timezone.utc),
        ),
    ]

    data_service = MagicMock()
    generator = StatusTimeReportGenerator(data_service=data_service)

    times = generator._calculate_status_times(history)

    assert times == {"Discovery": 3, "Delivery": 2}
