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
    info = generator._parse_task(task)

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
    info = generator._parse_task(task)

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
    info = generator._parse_task(task)
    # Задача с не-эпик ссылкой теперь возвращается с пустыми epic_key и epic_summary
    assert info is not None
    assert info.epic_key == ""
    assert info.epic_summary == ""


def test_parse_task_without_epic():
    """Тест: задача FULLSTACK без связи с эпиком должна возвращать SubepicInfo с пустыми epic_key и epic_summary."""
    created_at = datetime(2025, 5, 10, tzinfo=timezone.utc)
    task = SimpleNamespace(
        key="FULLSTACK-999",
        summary="Task without epic",
        author="charlie",
        prodteam="team-c",
        created_at=created_at,
        links=None,  # Нет links вообще
        full_data={},
    )

    generator = FullstackSubepicReturnsReportGenerator(db=None)
    info = generator._parse_task(task)

    assert info == SubepicInfo(
        key="FULLSTACK-999",
        summary="Task without epic",
        author="charlie",
        prodteam="team-c",
        epic_key="",
        epic_summary="",
        created_at=created_at,
    )


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
    generator._load_tasks = lambda: [
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
    generator._fetch_epic_quarters = lambda keys: {}
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
            "Квартал эпика": "",
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

    generator._load_tasks = lambda: [
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
    generator = FullstackSubepicReturnsReportGenerator(
        db=db_session, start_date=datetime(2025, 10, 1, tzinfo=timezone.utc)
    )

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

    # Находим нужную строку
    subepic_row = next((r for r in rows if r["Ключ задачи"] == "FULLSTACK-12"), None)
    assert subepic_row is not None
    assert subepic_row["Команда"] == "epic-team-value"
    assert subepic_row["Ключ задачи"] == "FULLSTACK-12"


def test_fetch_candidate_tasks_includes_tasks_without_links(db_session):
    """Тест: _fetch_candidate_tasks должна возвращать задачи даже без links."""
    generator = FullstackSubepicReturnsReportGenerator(
        db=db_session, start_date=datetime(2025, 1, 1, tzinfo=timezone.utc)
    )

    from radiator.models.tracker import TrackerTask

    # Создаём задачу с links
    task_with_links = TrackerTask(
        tracker_id="task-1",
        key="FULLSTACK-1",
        summary="Task with links",
        author="alice",
        links=[{"type": {"id": "epic"}, "direction": "outward"}],
        created_at=datetime(2025, 2, 1, tzinfo=timezone.utc),
    )
    db_session.add(task_with_links)

    # Создаём задачу без links
    task_without_links = TrackerTask(
        tracker_id="task-2",
        key="FULLSTACK-2",
        summary="Task without links",
        author="bob",
        links=None,
        created_at=datetime(2025, 2, 2, tzinfo=timezone.utc),
    )
    db_session.add(task_without_links)

    # Создаём задачу с пустым списком links
    task_with_empty_links = TrackerTask(
        tracker_id="task-3",
        key="FULLSTACK-3",
        summary="Task with empty links",
        author="charlie",
        links=[],
        created_at=datetime(2025, 2, 3, tzinfo=timezone.utc),
    )
    db_session.add(task_with_empty_links)

    db_session.commit()

    tasks = generator._fetch_candidate_tasks()

    # Должны быть все три задачи
    task_keys = [task.key for task in tasks]
    assert "FULLSTACK-1" in task_keys
    assert "FULLSTACK-2" in task_keys
    assert "FULLSTACK-3" in task_keys


def test_load_tasks_includes_all_tasks(db_session):
    """Тест: метод должен возвращать список, включающий и подэпики, и задачи без эпика."""
    generator = FullstackSubepicReturnsReportGenerator(
        db=db_session, start_date=datetime(2025, 1, 1, tzinfo=timezone.utc)
    )

    from radiator.models.tracker import TrackerTask

    # Создаём подэпик с эпиком
    subepic = TrackerTask(
        tracker_id="subepic-load-tasks-2",
        key="FULLSTACK-101",
        summary="Subepic with epic",
        author="alice",
        links=[
            {
                "type": {"id": "epic"},
                "direction": "outward",
                "object": {"key": "FULLSTACK-1001", "display": "Epic 1001"},
            }
        ],
        created_at=datetime(2025, 3, 15, tzinfo=timezone.utc),
    )
    db_session.add(subepic)

    # Создаём обычную задачу без эпика
    regular_task = TrackerTask(
        tracker_id="task-load-tasks-2",
        key="FULLSTACK-201",
        summary="Regular task without epic",
        author="bob",
        links=None,
        created_at=datetime(2025, 4, 20, tzinfo=timezone.utc),
    )
    db_session.add(regular_task)

    db_session.commit()

    tasks = generator._load_tasks()

    # Должны быть обе задачи
    task_keys = [task.key for task in tasks]
    assert "FULLSTACK-101" in task_keys
    assert "FULLSTACK-201" in task_keys

    # Проверяем, что подэпик имеет epic_key, а обычная задача - пустой
    subepic_info = next(t for t in tasks if t.key == "FULLSTACK-101")
    regular_info = next(t for t in tasks if t.key == "FULLSTACK-201")

    assert subepic_info.epic_key == "FULLSTACK-1001"
    assert regular_info.epic_key == ""


def test_compute_epic_month_for_task_without_epic():
    """Тест: для задачи с epic_key='' месяц должен вычисляться из created_at самой задачи."""
    generator = FullstackSubepicReturnsReportGenerator(db=None)

    subepics = [
        SubepicInfo(
            key="FULLSTACK-100",
            summary="Subepic with epic",
            author="alice",
            prodteam="team-a",
            epic_key="FULLSTACK-1000",
            epic_summary="Epic 1000",
            created_at=datetime(2025, 3, 15, tzinfo=timezone.utc),
        ),
        SubepicInfo(
            key="FULLSTACK-200",
            summary="Task without epic",
            author="bob",
            prodteam="team-b",
            epic_key="",
            epic_summary="",
            created_at=datetime(2025, 4, 20, tzinfo=timezone.utc),
        ),
    ]

    months = generator._compute_epic_months(subepics)

    # Для подэпика с эпиком месяц вычисляется из created_at подэпиков того же эпика
    assert months["FULLSTACK-1000"] == "2025-03"
    # Для задачи без эпика месяц вычисляется из created_at самой задачи
    assert months[""] == "2025-04"


def test_get_team_for_task_without_epic(db_session):
    """Тест: метод должен извлекать команду из задачи (сначала team, затем prodteam)."""
    generator = FullstackSubepicReturnsReportGenerator(db=db_session)

    from radiator.models.tracker import TrackerTask

    # Создаём задачу с team в full_data
    task_with_team = TrackerTask(
        tracker_id="task-team-get-team-1",
        key="FULLSTACK-301",
        summary="Task with team",
        full_data={"6361307d94f52e42ae308615--team": "task-team-value"},
    )
    db_session.add(task_with_team)

    # Создаём задачу с prodteam в full_data
    task_with_prodteam = TrackerTask(
        tracker_id="task-prodteam-get-team-1",
        key="FULLSTACK-401",
        summary="Task with prodteam",
        full_data={"6361307d94f52e42ae308615--prodteam": "task-prodteam-value"},
    )
    db_session.add(task_with_prodteam)

    db_session.commit()

    # Проверяем извлечение team
    team = generator._get_team_for_task_without_epic("FULLSTACK-301")
    assert team == "task-team-value"

    # Проверяем извлечение prodteam (если team нет)
    prodteam = generator._get_team_for_task_without_epic("FULLSTACK-401")
    assert prodteam == "task-prodteam-value"


def test_collect_rows_mixed_subepics_and_regular_tasks(db_session):
    """Интеграционный тест: подэпик с эпиком и обычная задача без эпика попадают в отчёт с правильными данными."""
    generator = FullstackSubepicReturnsReportGenerator(
        db=db_session, start_date=datetime(2025, 1, 1, tzinfo=timezone.utc)
    )

    from radiator.models.tracker import TrackerTask

    # Создаём эпик с team в full_data
    epic = TrackerTask(
        tracker_id="epic-integration-mixed-1",
        key="FULLSTACK-5001",
        summary="Epic for integration test",
        full_data={"6361307d94f52e42ae308615--team": "epic-team-integration"},
    )
    db_session.add(epic)

    # Создаём подэпик с эпиком
    subepic = TrackerTask(
        tracker_id="subepic-integration-mixed-1",
        key="FULLSTACK-6001",
        summary="Subepic with epic",
        author="alice",
        prodteam=None,
        links=[
            {
                "type": {"id": "epic"},
                "direction": "outward",
                "object": {
                    "key": "FULLSTACK-5001",
                    "display": "Epic for integration test",
                },
            }
        ],
        created_at=datetime(2025, 3, 15, tzinfo=timezone.utc),
        full_data={},
    )
    db_session.add(subepic)

    # Создаём обычную задачу без эпика с team в full_data
    regular_task = TrackerTask(
        tracker_id="task-integration-mixed-1",
        key="FULLSTACK-7001",
        summary="Regular task without epic",
        author="bob",
        links=None,
        created_at=datetime(2025, 4, 20, tzinfo=timezone.utc),
        full_data={"6361307d94f52e42ae308615--team": "regular-task-team"},
    )
    db_session.add(regular_task)

    db_session.commit()

    rows = generator._collect_rows()

    # Должны быть обе задачи
    task_keys = [r["Ключ задачи"] for r in rows]
    assert "FULLSTACK-6001" in task_keys
    assert "FULLSTACK-7001" in task_keys

    # Проверяем подэпик
    subepic_row = next(r for r in rows if r["Ключ задачи"] == "FULLSTACK-6001")
    assert subepic_row["Ключ эпика"] == "FULLSTACK-5001"
    assert subepic_row["Название эпика"] == "Epic for integration test"
    assert subepic_row["Команда"] == "epic-team-integration"
    assert subepic_row["Месяц эпика"] == "2025-03"

    # Проверяем обычную задачу без эпика
    regular_row = next(r for r in rows if r["Ключ задачи"] == "FULLSTACK-7001")
    assert regular_row["Ключ эпика"] == ""
    assert regular_row["Название эпика"] == ""
    assert regular_row["Команда"] == "regular-task-team"
    assert regular_row["Месяц эпика"] == "2025-04"  # месяц создания задачи


def test_collect_rows_includes_tasks_without_epic():
    """Tracer Bullet: проверяет, что в отчёт попадают подэпик с эпиком и обычная FULLSTACK задача без эпика."""
    generator = FullstackSubepicReturnsReportGenerator(db=None)

    created_at_subepic = datetime(2025, 3, 15, tzinfo=timezone.utc)
    created_at_regular = datetime(2025, 4, 20, tzinfo=timezone.utc)

    # Мокаем _load_subepics, чтобы вернуть и подэпик, и обычную задачу
    generator._load_tasks = lambda: [
        SubepicInfo(
            key="FULLSTACK-100",
            summary="Subepic with epic",
            author="alice",
            prodteam="team-a",
            epic_key="FULLSTACK-1000",
            epic_summary="Epic 1000",
            created_at=created_at_subepic,
        ),
        SubepicInfo(
            key="FULLSTACK-200",
            summary="Regular task without epic",
            author="bob",
            prodteam="team-b",
            epic_key="",
            epic_summary="",
            created_at=created_at_regular,
        ),
    ]
    generator._load_histories = lambda keys: {
        "FULLSTACK-100": [],
        "FULLSTACK-200": [],
    }
    # Мокаем функции поиска команды
    generator._fetch_epic_teams = lambda keys: {"FULLSTACK-1000": "epic-team"}
    generator._find_team_from_subepics = lambda subepics, epic_teams: {}
    generator._fetch_epic_prodteams_fullstack = lambda keys: {}
    generator._find_prodteam_from_subepics = lambda subepics, epic_prodteams: {}

    rows = generator._collect_rows()

    # Должно быть 2 строки
    assert len(rows) == 2

    # Подэпик с эпиком
    subepic_row = next(r for r in rows if r["Ключ задачи"] == "FULLSTACK-100")
    assert subepic_row["Ключ эпика"] == "FULLSTACK-1000"
    assert subepic_row["Название эпика"] == "Epic 1000"
    assert subepic_row["Месяц эпика"] == "2025-03"

    # Обычная задача без эпика
    regular_row = next(r for r in rows if r["Ключ задачи"] == "FULLSTACK-200")
    assert regular_row["Ключ эпика"] == ""
    assert regular_row["Название эпика"] == ""
    assert regular_row["Месяц эпика"] == "2025-04"  # месяц создания задачи
