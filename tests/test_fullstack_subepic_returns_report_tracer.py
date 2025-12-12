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
    # Мокаем новые функции поиска команды
    generator._fetch_epic_teams = lambda keys: {}
    generator._find_team_from_subepics = lambda subepics, epic_teams: {}
    generator._fetch_epic_prodteams_fullstack = lambda keys: {"FULLSTACK-30": "team-c"}
    generator._find_prodteam_from_subepics = lambda subepics, epic_prodteams: {}

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
    # Мокаем новые функции поиска команды
    generator._fetch_epic_teams = lambda keys: {}
    generator._find_team_from_subepics = lambda subepics, epic_teams: {}
    generator._fetch_epic_prodteams_fullstack = lambda keys: {
        "FULLSTACK-40": "team-from-epic"
    }
    generator._find_prodteam_from_subepics = lambda subepics, epic_prodteams: {}

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


def test_extract_team_from_full_data():
    """Тест: helper извлекает team из full_data."""
    generator = FullstackSubepicReturnsReportGenerator(db=None)

    # С новым ключом FULLSTACK
    full_data_with_team = {"6361307d94f52e42ae308615--team": "team-fullstack"}
    assert (
        generator._extract_team_from_full_data(full_data_with_team) == "team-fullstack"
    )

    # Без ключа
    full_data_empty = {}
    assert generator._extract_team_from_full_data(full_data_empty) is None

    # С None
    assert generator._extract_team_from_full_data(None) is None


def test_fetch_epic_teams(db_session):
    """Тест: поиск team у эпика через full_data."""
    generator = FullstackSubepicReturnsReportGenerator(db=db_session)

    from radiator.models.tracker import TrackerTask

    # Создаём эпик с team в full_data
    epic = TrackerTask(
        tracker_id="epic-1",
        key="FULLSTACK-100",
        summary="Epic with team",
        full_data={"6361307d94f52e42ae308615--team": "epic-team"},
    )
    db_session.add(epic)

    # Эпик без team
    epic_no_team = TrackerTask(
        tracker_id="epic-2",
        key="FULLSTACK-200",
        summary="Epic without team",
        full_data={},
    )
    db_session.add(epic_no_team)
    db_session.commit()

    teams = generator._fetch_epic_teams(["FULLSTACK-100", "FULLSTACK-200"])

    assert teams["FULLSTACK-100"] == "epic-team"
    assert teams["FULLSTACK-200"] is None


def test_find_team_from_subepics(db_session):
    """Тест: поиск team у подэпиков, если нет у эпика."""
    generator = FullstackSubepicReturnsReportGenerator(db=db_session)

    from radiator.models.tracker import TrackerTask

    # Создаём подэпики с team в full_data
    subepic1 = TrackerTask(
        tracker_id="subepic-1",
        key="FULLSTACK-7",
        summary="Subepic 7",
        full_data={"6361307d94f52e42ae308615--team": "subepic-team"},
    )
    db_session.add(subepic1)

    subepic2 = TrackerTask(
        tracker_id="subepic-2",
        key="FULLSTACK-8",
        summary="Subepic 8",
        full_data={},
    )
    db_session.add(subepic2)
    db_session.commit()

    # Эпик без team, подэпик с team
    subepics = [
        SubepicInfo(
            key="FULLSTACK-7",
            summary="Subepic 7",
            author="alice",
            prodteam=None,
            epic_key="FULLSTACK-70",
            epic_summary="Epic 70",
            created_at=datetime(2025, 8, 1, tzinfo=timezone.utc),
        ),
        SubepicInfo(
            key="FULLSTACK-8",
            summary="Subepic 8",
            author="bob",
            prodteam=None,
            epic_key="FULLSTACK-70",
            epic_summary="Epic 70",
            created_at=datetime(2025, 8, 2, tzinfo=timezone.utc),
        ),
    ]

    epic_teams = {"FULLSTACK-70": None}  # Эпик без team
    subepic_teams = generator._find_team_from_subepics(subepics, epic_teams)

    assert subepic_teams["FULLSTACK-70"] == "subepic-team"  # Берём из первого подэпика

    # Все без team
    epic_teams_empty = {"FULLSTACK-70": None}
    subepics_no_team = [
        SubepicInfo(
            key="FULLSTACK-9",
            summary="Subepic 9",
            author="charlie",
            prodteam=None,
            epic_key="FULLSTACK-70",
            epic_summary="Epic 70",
            created_at=datetime(2025, 8, 3, tzinfo=timezone.utc),
        )
    ]

    subepic_teams_empty = generator._find_team_from_subepics(
        subepics_no_team, epic_teams_empty
    )

    assert subepic_teams_empty["FULLSTACK-70"] is None


def test_fetch_epic_prodteams_fullstack(db_session):
    """Тест: поиск prodteam у эпика через full_data (FULLSTACK поле)."""
    generator = FullstackSubepicReturnsReportGenerator(db=db_session)

    from radiator.models.tracker import TrackerTask

    # Создаём эпик с prodteam в full_data
    epic = TrackerTask(
        tracker_id="epic-3",
        key="FULLSTACK-300",
        summary="Epic with prodteam",
        full_data={"6361307d94f52e42ae308615--prodteam": "epic-prodteam"},
    )
    db_session.add(epic)

    # Эпик без prodteam
    epic_no_prodteam = TrackerTask(
        tracker_id="epic-4",
        key="FULLSTACK-400",
        summary="Epic without prodteam",
        full_data={},
    )
    db_session.add(epic_no_prodteam)
    db_session.commit()

    prodteams = generator._fetch_epic_prodteams_fullstack(
        ["FULLSTACK-300", "FULLSTACK-400"]
    )

    assert prodteams["FULLSTACK-300"] == "epic-prodteam"
    assert prodteams["FULLSTACK-400"] is None


def test_find_prodteam_from_subepics(db_session):
    """Тест: поиск prodteam у подэпиков, если нет у эпика."""
    generator = FullstackSubepicReturnsReportGenerator(db=db_session)

    from radiator.models.tracker import TrackerTask

    # Создаём подэпики с prodteam в full_data
    subepic1 = TrackerTask(
        tracker_id="subepic-3",
        key="FULLSTACK-10",
        summary="Subepic 10",
        full_data={"6361307d94f52e42ae308615--prodteam": "subepic-prodteam"},
    )
    db_session.add(subepic1)

    subepic2 = TrackerTask(
        tracker_id="subepic-4",
        key="FULLSTACK-11",
        summary="Subepic 11",
        full_data={},
    )
    db_session.add(subepic2)
    db_session.commit()

    subepics = [
        SubepicInfo(
            key="FULLSTACK-10",
            summary="Subepic 10",
            author="dave",
            prodteam=None,
            epic_key="FULLSTACK-80",
            epic_summary="Epic 80",
            created_at=datetime(2025, 9, 1, tzinfo=timezone.utc),
        ),
        SubepicInfo(
            key="FULLSTACK-11",
            summary="Subepic 11",
            author="eve",
            prodteam=None,
            epic_key="FULLSTACK-80",
            epic_summary="Epic 80",
            created_at=datetime(2025, 9, 2, tzinfo=timezone.utc),
        ),
    ]

    epic_prodteams = {"FULLSTACK-80": None}  # Эпик без prodteam
    subepic_prodteams = generator._find_prodteam_from_subepics(subepics, epic_prodteams)

    assert (
        subepic_prodteams["FULLSTACK-80"] == "subepic-prodteam"
    )  # Берём из первого подэпика


def test_collect_rows_with_team_from_epic(db_session):
    """Тест: команда заполняется из team эпика."""
    generator = FullstackSubepicReturnsReportGenerator(db=db_session)

    from radiator.models.tracker import TrackerTask

    # Создаём эпик с team в full_data
    epic = TrackerTask(
        tracker_id="epic-5",
        key="FULLSTACK-500",
        summary="Epic 500",
        full_data={"6361307d94f52e42ae308615--team": "epic-team-value"},
    )
    db_session.add(epic)

    # Создаём подэпик без prodteam
    subepic = TrackerTask(
        tracker_id="subepic-5",
        key="FULLSTACK-12",
        summary="Subepic 12",
        author="frank",
        prodteam=None,
        links=[
            {
                "type": {"id": "epic"},
                "direction": "outward",
                "object": {"key": "FULLSTACK-500", "display": "Epic 500"},
            }
        ],
        created_at=datetime(2025, 10, 1, tzinfo=timezone.utc),
        full_data={},
    )
    db_session.add(subepic)
    db_session.commit()

    rows = generator._collect_rows()

    # Должна быть одна строка с командой из эпика
    assert len(rows) == 1
    assert rows[0]["Команда"] == "epic-team-value"
    assert rows[0]["Ключ задачи"] == "FULLSTACK-12"
