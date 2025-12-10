import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from radiator.commands.generate_fullstack_subepic_returns_report import (
    FullstackSubepicReturnsReportGenerator,
    SubepicInfo,
)
from radiator.commands.models.time_to_market_models import StatusHistoryEntry


def test_tracer_creates_csv_header(tmp_path: Path):
    output = tmp_path / "fullstack_subepic_returns.csv"

    generator = FullstackSubepicReturnsReportGenerator(db=None)
    generator.generate_csv(str(output))

    assert output.exists()

    with output.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)

    expected_columns = generator.COLUMN_NAMES

    assert header == expected_columns


def test_parse_subepic_by_epic_link():
    created_at = datetime(2025, 2, 10, tzinfo=timezone.utc)
    task = SimpleNamespace(
        key="FULLSTACK-1",
        summary="Subepic",
        author="alice",
        prodteam="team-a",
        created_at=created_at,
        links=[
            {
                "id": "202872",
                "type": {"id": "epic"},
                "direction": "outward",
                "object": {"key": "FULLSTACK-10", "display": "Epic name"},
            }
        ],
    )

    generator = FullstackSubepicReturnsReportGenerator(db=None)
    info = generator._parse_subepic_task(task)

    assert info == SubepicInfo(
        key="FULLSTACK-1",
        summary="Subepic",
        author="alice",
        prodteam="team-a",
        epic_key="FULLSTACK-10",
        epic_summary="Epic name",
        created_at=created_at,
    )


def test_parse_subepic_prodteam_from_full_data():
    created_at = datetime(2025, 7, 5, tzinfo=timezone.utc)
    task = SimpleNamespace(
        key="FULLSTACK-11",
        summary="Subepic FD",
        author="dave",
        prodteam=None,
        created_at=created_at,
        full_data={"63515d47fe387b7ce7b9fc55--prodteam": "team-fd"},
        links=[
            {
                "type": {"id": "epic"},
                "direction": "outward",
                "object": {"key": "FULLSTACK-99", "display": "Epic 99"},
            }
        ],
    )

    generator = FullstackSubepicReturnsReportGenerator(db=None)
    info = generator._parse_subepic_task(task)

    assert info and info.prodteam == "team-fd"
    assert info.created_at == created_at


def test_parse_subepic_ignores_non_epic_link():
    task = SimpleNamespace(
        key="FULLSTACK-2",
        summary="No epic",
        author="bob",
        prodteam="team-b",
        links=[
            {"type": {"id": "depends"}, "direction": "outward", "object": {"key": "X"}}
        ],
    )

    generator = FullstackSubepicReturnsReportGenerator(db=None)
    assert generator._parse_subepic_task(task) is None


def test_count_returns_by_status():
    now = datetime.now(timezone.utc)
    history = [
        StatusHistoryEntry("InProgress", "InProgress", now, now + timedelta(hours=1)),
        StatusHistoryEntry("Ревью", "Ревью", now, now + timedelta(hours=2)),
        StatusHistoryEntry("InProgress", "InProgress", now, now + timedelta(hours=3)),
        StatusHistoryEntry("InProgress", "InProgress", now, now + timedelta(hours=4)),
    ]

    generator = FullstackSubepicReturnsReportGenerator(db=None)
    counts = generator._count_returns_by_status(history)

    assert counts["InProgress"] == 1  # два входа => 1 возврат
    assert counts["Ревью"] == 0


def test_collect_rows_with_stubbed_data(tmp_path: Path):
    now = datetime.now(timezone.utc)
    history = [
        StatusHistoryEntry("Testing", "Testing", now, now + timedelta(hours=1)),
        StatusHistoryEntry("Testing", "Testing", now, now + timedelta(hours=2)),
        StatusHistoryEntry("Done", "Done", now, now + timedelta(hours=3)),
    ]

    generator = FullstackSubepicReturnsReportGenerator(db=None)

    created_at = datetime(2025, 3, 15, tzinfo=timezone.utc)
    generator._load_subepics = lambda: [
        SubepicInfo(
            key="FULLSTACK-3",
            summary="Subepic 3",
            author="carol",
            prodteam="team-c",
            epic_key="FULLSTACK-30",
            epic_summary="Epic 30",
            created_at=created_at,
        )
    ]
    generator._load_histories = lambda keys: {"FULLSTACK-3": history}

    rows = generator._collect_rows()

    assert rows == [
        {
            "Ключ задачи": "FULLSTACK-3",
            "Название": "Subepic 3",
            "Автор": "carol",
            "Команда": "team-c",
            "Ключ эпика": "FULLSTACK-30",
            "Название эпика": "Epic 30",
            "Месяц эпика": "2025-03",
            "Возвраты InProgress": 0,
            "Возвраты Ревью": 0,
            "Возвраты Testing": 0,  # одно вхождение -> 0 возвратов (второе подряд не считается)
            "Возвраты Внешний тест": 0,
            "Возвраты Апрув": 0,
            "Возвраты Регресс-тест": 0,
            "Возвраты Done": 0,
        }
    ]


def test_collect_rows_fills_prodteam_from_epic():
    history = []
    generator = FullstackSubepicReturnsReportGenerator(db=None)
    created_at = datetime(2025, 4, 10, tzinfo=timezone.utc)

    generator._load_subepics = lambda: [
        SubepicInfo(
            key="FULLSTACK-4",
            summary="Subepic 4",
            author="erin",
            prodteam=None,
            epic_key="FULLSTACK-40",
            epic_summary="Epic 40",
            created_at=created_at,
        )
    ]
    generator._load_histories = lambda keys: {"FULLSTACK-4": history}
    generator._fetch_epic_prodteams = lambda keys: {"FULLSTACK-40": "team-from-epic"}

    rows = generator._collect_rows()

    assert rows[0]["Команда"] == "team-from-epic"
    assert rows[0]["Месяц эпика"] == "2025-04"


def test_compute_epic_month_from_first_subepic():
    """Тест: месяц эпика = min(created_at) среди подэпиков."""
    generator = FullstackSubepicReturnsReportGenerator(db=None)

    subepics = [
        SubepicInfo(
            key="FULLSTACK-5",
            summary="Subepic 5 (later)",
            author="frank",
            prodteam="team-f",
            epic_key="FULLSTACK-50",
            epic_summary="Epic 50",
            created_at=datetime(2025, 6, 20, tzinfo=timezone.utc),
        ),
        SubepicInfo(
            key="FULLSTACK-6",
            summary="Subepic 6 (earlier)",
            author="grace",
            prodteam="team-g",
            epic_key="FULLSTACK-50",
            epic_summary="Epic 50",
            created_at=datetime(2025, 5, 15, tzinfo=timezone.utc),
        ),
    ]

    months = generator._compute_epic_months(subepics)

    assert months["FULLSTACK-50"] == "2025-05"  # min дата среди подэпиков
