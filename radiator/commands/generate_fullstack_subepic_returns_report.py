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
FULLSTACK_TEAM_FIELD_KEY = "6361307d94f52e42ae308615--team"
FULLSTACK_PRODTEAM_FIELD_KEY = "6361307d94f52e42ae308615--prodteam"
FULLSTACK_QUARTER_FIELD_KEY = "6361307d94f52e42ae308615--quarter"


@dataclass
class SubepicInfo:
    key: str
    summary: str
    author: Optional[str]
    prodteam: Optional[str]
    epic_key: str
    epic_summary: str
    created_at: Optional[datetime] = None


class FullstackSubepicReturnsReportGenerator:
    """Генератор CSV отчёта по возвратам подэпиков FULLSTACK."""

    COLUMN_NAMES: list[str] = [
        "Ключ задачи",
        "Название",
        "Автор",
        "Команда",
        "Ключ эпика",
        "Название эпика",
        "Месяц эпика",
        "Квартал эпика",
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
        """Загрузить кандидатов из БД (FULLSTACK, от стартовой даты)."""
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
                TrackerTask.created_at,
            )
            .filter(
                TrackerTask.key.like("FULLSTACK-%"),
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

    def _parse_task(self, task) -> Optional[SubepicInfo]:
        """Преобразовать задачу в SubepicInfo."""
        links = getattr(task, "links", None)

        epic_key = ""
        epic_summary = ""

        if links:
            for link in links:
                res = self._extract_epic_from_link(link)
                if res:
                    epic_key, epic_summary = res
                    break

        prodteam = self._get_prodteam(task)
        created_at = getattr(task, "created_at", None)

        return SubepicInfo(
            key=getattr(task, "key", ""),
            summary=getattr(task, "summary", "") or "",
            author=getattr(task, "author", None),
            prodteam=prodteam,
            epic_key=epic_key,
            epic_summary=epic_summary or "",
            created_at=created_at,
        )

    @staticmethod
    def _extract_prodteam(prodteam_value, full_data) -> Optional[str]:
        """Извлечь продуктовую команду из колонки или full_data."""
        if prodteam_value:
            return prodteam_value

        if isinstance(full_data, dict):
            return full_data.get(PRODTEAM_FIELD_KEY) or None

        return None

    @staticmethod
    def _extract_team_from_full_data(full_data) -> Optional[str]:
        """Извлечь команду из full_data по ключу FULLSTACK team."""
        if not isinstance(full_data, dict):
            return None
        value = full_data.get(FULLSTACK_TEAM_FIELD_KEY)
        if value:
            return str(value).strip() if str(value).strip() else None
        return None

    @staticmethod
    def _extract_prodteam_from_full_data(full_data) -> Optional[str]:
        """Извлечь prodteam из full_data по ключу FULLSTACK prodteam."""
        if not isinstance(full_data, dict):
            return None
        value = full_data.get(FULLSTACK_PRODTEAM_FIELD_KEY)
        if value:
            return str(value).strip() if str(value).strip() else None
        return None

    @staticmethod
    def _extract_quarter_from_full_data(full_data) -> Optional[str]:
        """Извлечь квартал из full_data."""
        if not isinstance(full_data, dict):
            return None
        value = full_data.get(FULLSTACK_QUARTER_FIELD_KEY)
        if value:
            return str(value).strip() if str(value).strip() else None
        return None

    def _get_team_for_task_without_epic(self, task_key: str) -> Optional[str]:
        """Получить команду для задачи без эпика из её full_data (сначала team, затем prodteam)."""
        if not self.db:
            return None

        task = (
            self.db.query(TrackerTask.full_data)
            .filter(TrackerTask.key == task_key)
            .first()
        )

        if not task or not task.full_data:
            return None

        # Сначала пробуем team
        team = self._extract_team_from_full_data(task.full_data)
        if team:
            return team

        # Затем prodteam
        prodteam = self._extract_prodteam_from_full_data(task.full_data)
        return prodteam

    def _get_quarter_for_task_without_epic(self, task_key: str) -> Optional[str]:
        """Получить квартал для задачи без эпика из её full_data."""
        if not self.db:
            return None

        task = (
            self.db.query(TrackerTask.full_data)
            .filter(TrackerTask.key == task_key)
            .first()
        )

        if not task or not task.full_data:
            return None

        return self._extract_quarter_from_full_data(task.full_data)

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

    def _fetch_epic_teams(self, epic_keys: List[str]) -> dict[str, Optional[str]]:
        """Загрузить team для эпиков батчем из full_data."""
        if not self.db or not epic_keys:
            return {}

        rows = (
            self.db.query(
                TrackerTask.key,
                TrackerTask.full_data,
            )
            .filter(TrackerTask.key.in_(epic_keys))
            .all()
        )

        result: dict[str, Optional[str]] = {}
        for key, full_data in rows:
            result[key] = self._extract_team_from_full_data(full_data)

        return result

    def _find_team_from_subepics(
        self, subepics: List[SubepicInfo], epic_teams: dict[str, Optional[str]]
    ) -> dict[str, Optional[str]]:
        """Найти team у подэпиков для эпиков, у которых нет team."""
        result: dict[str, Optional[str]] = {}

        # Группируем подэпики по epic_key
        epic_to_subepics: dict[str, List[SubepicInfo]] = {}
        for info in subepics:
            if info.epic_key not in epic_to_subepics:
                epic_to_subepics[info.epic_key] = []
            epic_to_subepics[info.epic_key].append(info)

        # Для каждого эпика без team ищем team у подэпиков
        for epic_key, subepic_list in epic_to_subepics.items():
            if epic_teams.get(epic_key):
                # У эпика уже есть team, пропускаем
                result[epic_key] = epic_teams[epic_key]
                continue

            # Ищем team у подэпиков
            if not self.db:
                result[epic_key] = None
                continue

            subepic_keys = [s.key for s in subepic_list]
            rows = (
                self.db.query(
                    TrackerTask.key,
                    TrackerTask.full_data,
                )
                .filter(TrackerTask.key.in_(subepic_keys))
                .all()
            )

            # Берём первый найденный team
            team_found = None
            for key, full_data in rows:
                team = self._extract_team_from_full_data(full_data)
                if team:
                    team_found = team
                    break

            result[epic_key] = team_found

        return result

    def _fetch_epic_prodteams_fullstack(
        self, epic_keys: List[str]
    ) -> dict[str, Optional[str]]:
        """Загрузить prodteam для эпиков батчем из full_data (FULLSTACK поле)."""
        if not self.db or not epic_keys:
            return {}

        rows = (
            self.db.query(
                TrackerTask.key,
                TrackerTask.full_data,
            )
            .filter(TrackerTask.key.in_(epic_keys))
            .all()
        )

        result: dict[str, Optional[str]] = {}
        for key, full_data in rows:
            result[key] = self._extract_prodteam_from_full_data(full_data)

        return result

    def _fetch_epic_quarters(self, epic_keys: List[str]) -> dict[str, Optional[str]]:
        """Загрузить кварталы для эпиков батчем из full_data."""
        if not self.db or not epic_keys:
            return {}

        rows = (
            self.db.query(
                TrackerTask.key,
                TrackerTask.full_data,
            )
            .filter(TrackerTask.key.in_(epic_keys))
            .all()
        )

        result: dict[str, Optional[str]] = {}
        for key, full_data in rows:
            result[key] = self._extract_quarter_from_full_data(full_data)

        return result

    def _find_prodteam_from_subepics(
        self, subepics: List[SubepicInfo], epic_prodteams: dict[str, Optional[str]]
    ) -> dict[str, Optional[str]]:
        """Найти prodteam у подэпиков для эпиков, у которых нет prodteam."""
        result: dict[str, Optional[str]] = {}

        # Группируем подэпики по epic_key
        epic_to_subepics: dict[str, List[SubepicInfo]] = {}
        for info in subepics:
            if info.epic_key not in epic_to_subepics:
                epic_to_subepics[info.epic_key] = []
            epic_to_subepics[info.epic_key].append(info)

        # Для каждого эпика без prodteam ищем prodteam у подэпиков
        for epic_key, subepic_list in epic_to_subepics.items():
            if epic_prodteams.get(epic_key):
                # У эпика уже есть prodteam, пропускаем
                result[epic_key] = epic_prodteams[epic_key]
                continue

            # Ищем prodteam у подэпиков
            if not self.db:
                result[epic_key] = None
                continue

            subepic_keys = [s.key for s in subepic_list]
            rows = (
                self.db.query(
                    TrackerTask.key,
                    TrackerTask.full_data,
                )
                .filter(TrackerTask.key.in_(subepic_keys))
                .all()
            )

            # Берём первый найденный prodteam
            prodteam_found = None
            for key, full_data in rows:
                prodteam = self._extract_prodteam_from_full_data(full_data)
                if prodteam:
                    prodteam_found = prodteam
                    break

            result[epic_key] = prodteam_found

        return result

    def _load_tasks(self) -> List[SubepicInfo]:
        """Выбрать задачи FULLSTACK (подэпики и обычные задачи)."""
        tasks = self._fetch_candidate_tasks()
        result: List[SubepicInfo] = []

        for task in tasks:
            parsed = self._parse_task(task)
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

    @staticmethod
    def _compute_epic_months(subepics: List[SubepicInfo]) -> dict[str, str]:
        """Вычислить базовый месяц для каждого эпика (min created_at подэпиков)."""
        epic_to_dates: dict[str, List[datetime]] = {}
        for info in subepics:
            if info.created_at:
                if info.epic_key not in epic_to_dates:
                    epic_to_dates[info.epic_key] = []
                epic_to_dates[info.epic_key].append(info.created_at)

        result: dict[str, str] = {}
        for epic_key, dates in epic_to_dates.items():
            if dates:
                min_date = min(dates)
                result[epic_key] = min_date.strftime("%Y-%m")
        return result

    def _format_row(
        self,
        info: SubepicInfo,
        counts: dict[str, int],
        epic_month: Optional[str] = None,
        epic_quarter: Optional[str] = None,
    ) -> dict:
        """Сформировать строку CSV."""
        return {
            "Ключ задачи": info.key,
            "Название": info.summary,
            "Автор": info.author or "",
            "Команда": info.prodteam or "",
            "Ключ эпика": info.epic_key,
            "Название эпика": info.epic_summary,
            "Месяц эпика": epic_month or "",
            "Квартал эпика": epic_quarter or "",
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
        subepics = self._load_tasks()
        # Исключаем пустую строку из epic_keys (задачи без эпика обрабатываются отдельно)
        epic_keys = [s.epic_key for s in subepics if s.epic_key]
        epic_keys = list(set(epic_keys))  # Убираем дубликаты
        epic_months = self._compute_epic_months(subepics)
        histories = self._load_histories([s.key for s in subepics])

        # Поиск команды: сначала team (эпик → подэпики), затем prodteam (эпик → подэпики)
        # Только для эпиков (не для задач без эпика)
        epic_teams = self._fetch_epic_teams(epic_keys) if epic_keys else {}
        subepic_teams = self._find_team_from_subepics(subepics, epic_teams)

        # Загружаем кварталы эпиков
        epic_quarters = self._fetch_epic_quarters(epic_keys) if epic_keys else {}

        # Если team не найден, используем prodteam
        epic_prodteams_fullstack = (
            self._fetch_epic_prodteams_fullstack(epic_keys) if epic_keys else {}
        )
        subepic_prodteams_fullstack = self._find_prodteam_from_subepics(
            subepics, epic_prodteams_fullstack
        )

        # Формируем финальный словарь команд для каждого эпика
        epic_teams_final: dict[str, Optional[str]] = {}
        for epic_key in epic_keys:
            # Сначала team
            team_value = epic_teams.get(epic_key) or subepic_teams.get(epic_key)
            if team_value:
                epic_teams_final[epic_key] = team_value
            else:
                # Fallback на prodteam
                prodteam_value = epic_prodteams_fullstack.get(
                    epic_key
                ) or subepic_prodteams_fullstack.get(epic_key)
                epic_teams_final[epic_key] = prodteam_value

        rows = []
        for info in subepics:
            # Для задач без эпика команда определяется из самой задачи
            if info.epic_key == "":
                team = self._get_team_for_task_without_epic(info.key)
                # Для задач без эпика месяц вычисляется из created_at самой задачи
                if info.created_at:
                    epic_month = info.created_at.strftime("%Y-%m")
                else:
                    epic_month = None
                # Для задач без эпика квартал определяется из самой задачи
                quarter = self._get_quarter_for_task_without_epic(info.key)
            else:
                # Для подэпиков используем найденную команду для эпика
                team = epic_teams_final.get(info.epic_key)
                epic_month = epic_months.get(info.epic_key)
                # Для подэпиков используем квартал эпика
                quarter = epic_quarters.get(info.epic_key)

            history = histories.get(info.key, [])
            counts = self._count_returns_by_status(history)
            # Подставляем команду
            info_with_team = SubepicInfo(
                key=info.key,
                summary=info.summary,
                author=info.author,
                prodteam=team,  # Используем найденную команду
                epic_key=info.epic_key,
                epic_summary=info.epic_summary,
                created_at=info.created_at,
            )
            rows.append(self._format_row(info_with_team, counts, epic_month, quarter))

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
