"""Ad-hoc выборка CPO-задач без Арх. ревью с суммой времени в статусе
"МП / В работе" за последние N месяцев > порога, выводит ключи в файл.

Запуск:
  python -m radiator.commands.adhoc_cpo_mpinprogress_no_archreview \
    --months 3 --min-minutes 10

Результат: файл data/reports/no_arch_%Y%m%d_%H%M%S.txt с ключами через запятую.
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from sqlalchemy import text
from sqlalchemy.orm import Session

# Ensure project root on sys.path (align with other commands)
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from radiator.core.config import settings
from radiator.core.database import SessionLocal
from radiator.core.logging import logger

DEFAULT_MONTHS = 3
DEFAULT_MIN_MINUTES = 10


SQL_QUERY = text(
    """
    WITH cpo_tasks AS (
      SELECT id, key
      FROM tracker_tasks
      WHERE key ILIKE 'CPO-%'
        AND task_updated_at >= (NOW() - make_interval(months => :months))
    ),
    hist AS (
      SELECT h.task_id,
             h.start_date,
             CASE
               WHEN h.end_date IS NULL OR h.end_date < h.start_date THEN NOW()
               ELSE h.end_date
             END AS end_norm,
             h.status,
             h.status_display
      FROM tracker_task_history h
      JOIN cpo_tasks t ON t.id = h.task_id
    ),
    mp_intervals AS (
      SELECT task_id,
             EXTRACT(EPOCH FROM (
               LEAST(end_norm, NOW())
               - GREATEST(start_date, NOW() - make_interval(months => :months))
             )) AS seconds_overlap
      FROM hist
      WHERE (
        status_display IN ('МП / В работе','МП/В работе')
        OR status IN ('МП / В работе','МП/В работе')
      )
        AND end_norm > (NOW() - make_interval(months => :months))
        AND start_date < NOW()
    ),
    mp_agg AS (
      SELECT task_id, SUM(GREATEST(seconds_overlap, 0)) AS seconds_total
      FROM mp_intervals
      GROUP BY task_id
    ),
    arch_review_tasks AS (
      SELECT DISTINCT h.task_id
      FROM tracker_task_history h
      WHERE h.status_display = 'Арх. ревью'
    )
    SELECT t.key
    FROM mp_agg ma
    JOIN tracker_tasks t ON t.id = ma.task_id
    LEFT JOIN arch_review_tasks ar ON ar.task_id = t.id
    WHERE ma.seconds_total >= :min_seconds
      AND ar.task_id IS NULL
    ORDER BY t.key
    """
)


def run_query(db: Session, months: int, min_minutes: int) -> List[str]:
    """Выполнить SQL и вернуть список ключей задач."""
    params = {
        "months": int(months),
        "min_seconds": int(min_minutes) * 60,
    }
    result = db.execute(SQL_QUERY, params)
    keys = [row[0] for row in result.fetchall()]
    return keys


def write_keys_to_file(keys: List[str], outfile: Path | None = None) -> Path:
    """Записать ключи через запятую в файл и вернуть путь к файлу."""
    reports_dir = Path(settings.REPORTS_DIR)
    reports_dir.mkdir(parents=True, exist_ok=True)

    if outfile is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"no_arch_{timestamp}.txt"
        outfile = reports_dir / filename
    else:
        # Если передан относительный путь, сохраняем его в reports_dir
        outfile = Path(outfile)
        if not outfile.is_absolute():
            outfile = reports_dir / outfile

    content = ",".join(keys)
    with open(outfile, "w", encoding="utf-8") as f:
        f.write(content)

    return outfile


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Ad-hoc выборка: CPO-задачи без 'Арх. ревью' и с суммой времени в 'МП / В работе'"
            " за последние N месяцев > порога. Результат — файл с ключами через запятую."
        )
    )
    parser.add_argument(
        "--months",
        type=int,
        default=DEFAULT_MONTHS,
        help=f"Количество месяцев для окна (default: {DEFAULT_MONTHS})",
    )
    parser.add_argument(
        "--min-minutes",
        type=int,
        default=DEFAULT_MIN_MINUTES,
        help=f"Минимальная сумма минут в статусе 'МП / В работе' (default: {DEFAULT_MIN_MINUTES})",
    )
    parser.add_argument(
        "--outfile",
        default="auto",
        help=(
            "Имя файла результата (по умолчанию auto -> data/reports/no_arch_%timestamp%.txt)."
        ),
    )

    args = parser.parse_args()

    try:
        with SessionLocal() as db:
            keys = run_query(db, months=args.months, min_minutes=args.min_minutes)

        # Определяем путь файла
        out_path = None if args.outfile == "auto" else Path(args.outfile)
        file_path = write_keys_to_file(keys, out_path)

        print(str(file_path))
        return 0
    except Exception as e:
        logger.error(f"Failed to generate ad-hoc report: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
