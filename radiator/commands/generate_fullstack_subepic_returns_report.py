"""Отчёт по возвратам для подэпиков FULLSTACK."""

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

from radiator.commands.models.time_to_market_models import StatusHistoryEntry
from radiator.commands.services.data_service import DataService
from radiator.commands.services.testing_returns_service import TestingReturnsService
from radiator.models.tracker import TrackerTask

DEFAULT_START_DATE = datetime(2025, 1, 1)
PRODTEAM_FIELD_KEY = "63515d47fe387b7ce7b9fc55--prodteam"


@dataclass
class SubepicInfo:
    key: str
    summary: str
    author: Optional[str]
    prodteam: Optional[str]
    epic_key: str
    epic_summary: str


class FullstackSubepicReturnsReportGenerator:
    """Генератор CSV отчёта по возвратам подэпиков FULLSTACK."""

    COLUMN_NAMES: list[str] = [
        "Ключ задачи",
        "Название",
        "Автор",
        "Команда",
        "Ключ эпика",
        "Название эпика",
        "Возвраты InProgress",
        "Возвраты Ревью",
        "Возвраты Testing",
        "Возвраты Внешний тест",
        "Возвраты Апрув",
        "Возвраты Регресс-тест",
        "Возвраты Done",
    ]

    RETURN_STATUSES: List[str] = [
        "InProgress",
        "Ревью",
        "Testing",
        "Внешний тест",
        "Апрув",
        "Регресс-тест",
        "Done",
    ]

    def __init__(self, db=None, start_date: Optional[datetime] = None):
        self.db = db
        self.start_date = start_date or DEFAULT_START_DATE
        self.data_service = DataService(db) if db else None
        self.returns_service = TestingReturnsService(db)

    def _fetch_candidate_tasks(self):
        """Загрузить кандидатов из БД (FULLSTACK, с links, от стартовой даты)."""
        if not self.db:
            return []

        return (
            self.db.query(
                TrackerTask.key,
                TrackerTask.summary,
                TrackerTask.author,
                TrackerTask.prodteam,
                TrackerTask.full_data,
                TrackerTask.links,
            )
            .filter(
                TrackerTask.key.like("FULLSTACK-%"),
                TrackerTask.links.isnot(None),
                TrackerTask.created_at >= self.start_date,
            )
            .all()
        )

    @staticmethod
    def _extract_epic_from_link(link: dict) -> Optional[tuple[str, str]]:
        """Достать ключ и название эпика из ссылки."""
        if not isinstance(link, dict):
            return None

        link_type = link.get("type", {})
        direction = link.get("direction")
        if link_type.get("id") != "epic" or direction != "outward":
            return None

        obj = link.get("object") or {}
        epic_key = obj.get("key")
        epic_display = obj.get("display", "") or ""
        if not epic_key:
            return None
        return epic_key, epic_display

    def _parse_subepic_task(self, task) -> Optional[SubepicInfo]:
        """Преобразовать задачу в SubepicInfo, если она подэпик."""
        links = getattr(task, "links", None)
        if not links:
            return None

        epic_key = None
        epic_summary = ""

        for link in links:
            res = self._extract_epic_from_link(link)
            if res:
                epic_key, epic_summary = res
                break

        if not epic_key:
            return None

        prodteam = self._get_prodteam(task)

        return SubepicInfo(
            key=getattr(task, "key", ""),
            summary=getattr(task, "summary", "") or "",
            author=getattr(task, "author", None),
            prodteam=prodteam,
            epic_key=epic_key,
            epic_summary=epic_summary or "",
        )

    @staticmethod
    @staticmethod
    def _extract_prodteam(prodteam_value, full_data) -> Optional[str]:
        """Извлечь продуктовую команду из колонки или full_data."""
        if prodteam_value:
            return prodteam_value

        if isinstance(full_data, dict):
            return full_data.get(PRODTEAM_FIELD_KEY) or None

        return None

    def _get_prodteam(self, task) -> Optional[str]:
        """Получить продуктовую команду: колонка prodteam или full_data custom."""
        if getattr(task, "prodteam", None):
            return task.prodteam

        full_data = getattr(task, "full_data", None)
        return self._extract_prodteam(None, full_data)

    def _fetch_epic_prodteams(self, epic_keys: List[str]) -> dict[str, Optional[str]]:
        """Загрузить prodteam для эпиков батчем."""
        if not self.db or not epic_keys:
            return {}

        rows = (
            self.db.query(
                TrackerTask.key,
                TrackerTask.prodteam,
                TrackerTask.full_data,
            )
            .filter(TrackerTask.key.in_(epic_keys))
            .all()
        )

        result: dict[str, Optional[str]] = {}
        for key, prodteam, full_data in rows:
            result[key] = self._extract_prodteam(prodteam, full_data)

        return result

    def _load_subepics(self) -> List[SubepicInfo]:
        """Выбрать подэпики FULLSTACK с эпиком."""
        tasks = self._fetch_candidate_tasks()
        result: List[SubepicInfo] = []

        for task in tasks:
            parsed = self._parse_subepic_task(task)
            if parsed:
                result.append(parsed)

        return result

    def _load_histories(
        self, task_keys: List[str]
    ) -> dict[str, List[StatusHistoryEntry]]:
        """Батч-истории по ключам."""
        if not task_keys:
            return {}
        if not self.data_service:
            return {key: [] for key in task_keys}
        return self.data_service.get_task_histories_by_keys_batch(task_keys)

    def _count_returns_by_status(
        self, history: List[StatusHistoryEntry]
    ) -> dict[str, int]:
        """Посчитать возвраты по заданным статусам."""
        counts = {}
        for status in self.RETURN_STATUSES:
            counts[status] = self.returns_service.count_status_returns(history, status)
        return counts

    def _format_row(self, info: SubepicInfo, counts: dict[str, int]) -> dict:
        """Сформировать строку CSV."""
        return {
            "Ключ задачи": info.key,
            "Название": info.summary,
            "Автор": info.author or "",
            "Команда": info.prodteam or "",
            "Ключ эпика": info.epic_key,
            "Название эпика": info.epic_summary,
            "Возвраты InProgress": counts.get("InProgress", 0),
            "Возвраты Ревью": counts.get("Ревью", 0),
            "Возвраты Testing": counts.get("Testing", 0),
            "Возвраты Внешний тест": counts.get("Внешний тест", 0),
            "Возвраты Апрув": counts.get("Апрув", 0),
            "Возвраты Регресс-тест": counts.get("Регресс-тест", 0),
            "Возвраты Done": counts.get("Done", 0),
        }

    def _collect_rows(self) -> List[dict]:
        """Собрать строки отчёта."""
        subepics = self._load_subepics()
        epic_keys = list({s.epic_key for s in subepics})
        epic_prodteams = self._fetch_epic_prodteams(epic_keys)
        histories = self._load_histories([s.key for s in subepics])

        rows = []
        for info in subepics:
            prodteam = info.prodteam or epic_prodteams.get(info.epic_key)
            history = histories.get(info.key, [])
            counts = self._count_returns_by_status(history)
            # Подставляем продкоманду (сначала из задачи, потом из эпика)
            info_with_team = SubepicInfo(
                key=info.key,
                summary=info.summary,
                author=info.author,
                prodteam=prodteam,
                epic_key=info.epic_key,
                epic_summary=info.epic_summary,
            )
            rows.append(self._format_row(info_with_team, counts))

        return rows

    def generate_csv(self, output_path: str) -> str:
        """Сформировать CSV."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        rows = self._collect_rows()

        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.COLUMN_NAMES)
            writer.writeheader()
            if rows:
                writer.writerows(rows)

        return output_path


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate FULLSTACK sub-epic returns CSV report"
    )
    parser.add_argument(
        "--start-date",
        default="2025-01-01",
        help="Дата начала отбора подэпиков (YYYY-MM-DD), по умолчанию 2025-01-01",
    )
    parser.add_argument(
        "--output",
        default="data/reports/fullstack_subepic_returns.csv",
        help="Путь к выходному CSV (по умолчанию data/reports/fullstack_subepic_returns.csv)",
    )
    args = parser.parse_args()

    start_date = datetime.fromisoformat(args.start_date)

    from radiator.core.database import SessionLocal

    with SessionLocal() as db:
        generator = FullstackSubepicReturnsReportGenerator(db=db, start_date=start_date)
        csv_path = generator.generate_csv(args.output)
        print(f"Report generated: {csv_path}")


if __name__ == "__main__":
    main()
