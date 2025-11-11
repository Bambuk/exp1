import argparse
import csv
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from radiator.commands.services.data_service import DataService
from radiator.core.database import SessionLocal
from radiator.core.logging import logger


class StatusTimeReportGenerator:
    def __init__(
        self,
        db: Optional[Session] = None,
        data_service: Optional[DataService] = None,
        output_dir: Optional[Path] = None,
    ):
        if data_service is None and db is None:
            raise ValueError("Either data_service or db must be provided")
        self.output_dir = Path(output_dir) if output_dir else None
        self.db = db
        self.data_service = data_service or DataService(db)

    def _ensure_output_dir(self, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        return output_path

    def _default_output_path(self) -> Path:
        base_dir = self.output_dir or Path("data/reports")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return base_dir / f"status_time_report_{timestamp}.csv"

    def generate_csv(
        self,
        queue: str,
        created_since: Optional[datetime] = None,
        output_path: Optional[Path] = None,
    ) -> Path:
        if output_path is None:
            output_path = self._default_output_path()

        output_path = Path(output_path)
        self._ensure_output_dir(output_path)

        tasks = list(self._get_tasks(queue, created_since))
        if not tasks:
            logger.warning(
                "No tasks found for queue '%s' with created_since=%s",
                queue,
                created_since,
            )
            with output_path.open("w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Ключ задачи"])
            return output_path

        histories_by_key = self.data_service.get_task_histories_by_keys_batch(
            [task.key for task in tasks]
        )
        statuses = self._collect_unique_statuses(tasks, histories_by_key)

        with output_path.open("w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            header = ["Ключ задачи"] + statuses
            writer.writerow(header)

            for task in tasks:
                history = histories_by_key.get(task.key, [])
                if not history:
                    logger.warning("No history entries for task %s", task.key)
                status_times = self._calculate_status_times(history)

                row = [task.key]
                for status in statuses:
                    value = status_times.get(status)
                    if value is None:
                        row.append("")
                    else:
                        row.append(str(value))

                writer.writerow(row)

        return output_path

    def _get_tasks(self, queue: str, created_since: Optional[datetime] = None):
        return self.data_service.get_tasks_by_queue(queue, created_since)

    def _collect_unique_statuses(
        self,
        tasks: Iterable,
        histories_by_key: Optional[dict[str, Iterable]] = None,
    ) -> list[str]:
        unique_statuses = set()

        for task in tasks:
            if histories_by_key is not None:
                history = histories_by_key.get(task.key, [])
            else:
                history = self.data_service.get_task_history(task.id)
            if not history:
                continue
            for entry in history:
                if entry.status:
                    unique_statuses.add(entry.status)

        return sorted(unique_statuses)

    def _calculate_status_times(self, history: Iterable) -> dict[str, int]:
        if not history:
            return {}

        sorted_history = sorted(history, key=lambda entry: entry.start_date)
        status_durations: dict[str, int] = {}

        for index, entry in enumerate(sorted_history):
            if entry.end_date is None:
                continue

            next_index = index + 1
            next_start = entry.end_date
            if next_index < len(sorted_history):
                next_start = sorted_history[next_index].start_date or entry.end_date

            duration = (next_start - entry.start_date).days
            if duration < 0:
                continue

            status_durations[entry.status] = (
                status_durations.get(entry.status, 0) + duration
            )

        return status_durations


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate status time report by queue")
    parser.add_argument("--queue", required=True, help="Tracker queue name, e.g. CPO")
    parser.add_argument(
        "--created-since",
        help="Filter tasks created on or after this date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--output",
        help="Optional path to output CSV file (defaults to data/reports with timestamp)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    created_since: Optional[datetime] = None
    if args.created_since:
        try:
            created_since = datetime.strptime(args.created_since, "%Y-%m-%d")
        except ValueError as exc:
            raise SystemExit("Invalid --created-since format. Use YYYY-MM-DD.") from exc

    output_path: Optional[Path] = Path(args.output) if args.output else None

    with SessionLocal() as db:
        generator = StatusTimeReportGenerator(db=db)
        csv_path = generator.generate_csv(
            queue=args.queue, created_since=created_since, output_path=output_path
        )

    print(f"Status time report generated: {csv_path}")


if __name__ == "__main__":
    main()
