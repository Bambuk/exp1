#!/usr/bin/env python3
"""
Скрипт для анализа состояния базы данных и выявления проблем производительности.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from radiator.core.config import settings
from radiator.core.database import SessionLocal
from radiator.models.tracker import TrackerSyncLog, TrackerTask, TrackerTaskHistory


class DatabaseAnalyzer:
    """Анализатор состояния базы данных."""

    def __init__(self):
        """Инициализация анализатора."""
        self.db = SessionLocal()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()

    def analyze_table_sizes(self):
        """Анализ размеров таблиц."""
        print("📊 АНАЛИЗ РАЗМЕРОВ ТАБЛИЦ")
        print("=" * 50)

        query = text(
            """
            SELECT
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
        """
        )

        result = self.db.execute(query)
        for row in result:
            print(f"{row.tablename:<25} {row.size:>10} ({row.size_bytes:,} bytes)")

    def analyze_table_stats(self):
        """Анализ статистики таблиц."""
        print("\n📈 СТАТИСТИКА ТАБЛИЦ")
        print("=" * 50)

        tables = ["tracker_tasks", "tracker_task_history", "tracker_sync_logs"]

        for table in tables:
            try:
                # Количество записей
                count_query = text(f"SELECT COUNT(*) as count FROM {table}")
                count_result = self.db.execute(count_query).fetchone()

                # Размер таблицы
                size_query = text(
                    f"""
                    SELECT pg_size_pretty(pg_total_relation_size('{table}')) as size
                """
                )
                size_result = self.db.execute(size_query).fetchone()

                print(f"\n{table}:")
                print(f"  Записей: {count_result.count:,}")
                print(f"  Размер: {size_result.size}")

            except Exception as e:
                print(f"Ошибка при анализе таблицы {table}: {e}")

    def analyze_indexes(self):
        """Анализ индексов."""
        print("\n🔍 АНАЛИЗ ИНДЕКСОВ")
        print("=" * 50)

        query = text(
            """
            SELECT
                t.tablename,
                i.indexname,
                i.indexdef,
                pg_size_pretty(pg_relation_size(i.indexname::regclass)) as size
            FROM pg_indexes i
            JOIN pg_tables t ON i.tablename = t.tablename
            WHERE t.schemaname = 'public'
            ORDER BY t.tablename, pg_relation_size(i.indexname::regclass) DESC;
        """
        )

        result = self.db.execute(query)
        for row in result:
            print(f"\n{row.tablename}.{row.indexname}")
            print(f"  Размер: {row.size}")
            print(f"  Определение: {row.indexdef}")

    def analyze_slow_queries(self):
        """Анализ медленных запросов (если включен pg_stat_statements)."""
        print("\n🐌 АНАЛИЗ МЕДЛЕННЫХ ЗАПРОСОВ")
        print("=" * 50)

        try:
            query = text(
                """
                SELECT
                    query,
                    calls,
                    total_time,
                    mean_time,
                    rows
                FROM pg_stat_statements
                WHERE query LIKE '%tracker%'
                ORDER BY mean_time DESC
                LIMIT 10;
            """
            )

            result = self.db.execute(query)
            rows = result.fetchall()

            if rows:
                for row in rows:
                    print(f"\nЗапрос: {row.query[:100]}...")
                    print(f"  Вызовов: {row.calls}")
                    print(f"  Общее время: {row.total_time:.2f}ms")
                    print(f"  Среднее время: {row.mean_time:.2f}ms")
                    print(f"  Строк: {row.rows}")
            else:
                print("pg_stat_statements не настроен или нет данных")

        except Exception as e:
            print(f"Ошибка при анализе медленных запросов: {e}")

    def analyze_duplicate_history(self):
        """Анализ дубликатов в истории задач."""
        print("\n🔄 АНАЛИЗ ДУБЛИКАТОВ В ИСТОРИИ")
        print("=" * 50)

        try:
            # Найти дубликаты
            query = text(
                """
                SELECT
                    task_id,
                    status,
                    start_date,
                    COUNT(*) as duplicate_count
                FROM tracker_task_history
                GROUP BY task_id, status, start_date
                HAVING COUNT(*) > 1
                ORDER BY duplicate_count DESC
                LIMIT 10;
            """
            )

            result = self.db.execute(query)
            rows = result.fetchall()

            if rows:
                print("Найдены дубликаты:")
                total_duplicates = 0
                for row in rows:
                    print(
                        f"  Task {row.task_id}, статус '{row.status}', дата {row.start_date}: {row.duplicate_count} записей"
                    )
                    total_duplicates += row.duplicate_count - 1

                print(f"\nОбщее количество лишних записей: {total_duplicates}")
            else:
                print("Дубликаты не найдены")

        except Exception as e:
            print(f"Ошибка при анализе дубликатов: {e}")

    def analyze_missing_indexes(self):
        """Анализ отсутствующих индексов."""
        print("\n❌ АНАЛИЗ ОТСУТСТВУЮЩИХ ИНДЕКСОВ")
        print("=" * 50)

        # Проверяем основные поля для поиска
        critical_fields = [
            ("tracker_tasks", "status"),
            ("tracker_tasks", "assignee"),
            ("tracker_tasks", "author"),
            ("tracker_tasks", "team"),
            ("tracker_tasks", "created_at"),
            ("tracker_tasks", "updated_at"),
            ("tracker_task_history", "task_id"),
            ("tracker_task_history", "status"),
            ("tracker_task_history", "start_date"),
            ("tracker_task_history", "end_date"),
        ]

        for table, column in critical_fields:
            try:
                query = text(
                    """
                    SELECT COUNT(*) as count
                    FROM pg_indexes
                    WHERE tablename = :table
                    AND indexdef LIKE :pattern
                """
                )

                result = self.db.execute(
                    query, {"table": table, "pattern": f"%{column}%"}
                ).fetchone()

                if result.count == 0:
                    print(f"⚠️  Отсутствует индекс для {table}.{column}")
                else:
                    print(f"✅ Индекс для {table}.{column} существует")

            except Exception as e:
                print(f"Ошибка при проверке индекса {table}.{column}: {e}")

    def analyze_connection_pool(self):
        """Анализ пула соединений."""
        print("\n🔗 АНАЛИЗ ПУЛА СОЕДИНЕНИЙ")
        print("=" * 50)

        try:
            query = text(
                """
                SELECT
                    state,
                    COUNT(*) as count
                FROM pg_stat_activity
                WHERE datname = current_database()
                GROUP BY state
                ORDER BY count DESC;
            """
            )

            result = self.db.execute(query)
            for row in result:
                print(f"{row.state}: {row.count} соединений")

        except Exception as e:
            print(f"Ошибка при анализе пула соединений: {e}")

    def analyze_data_growth(self):
        """Анализ роста данных."""
        print("\n📈 АНАЛИЗ РОСТА ДАННЫХ")
        print("=" * 50)

        try:
            # Анализ по месяцам
            query = text(
                """
                SELECT
                    DATE_TRUNC('month', created_at) as month,
                    COUNT(*) as tasks_count
                FROM tracker_tasks
                WHERE created_at >= NOW() - INTERVAL '12 months'
                GROUP BY DATE_TRUNC('month', created_at)
                ORDER BY month;
            """
            )

            result = self.db.execute(query)
            print("Рост задач по месяцам:")
            for row in result:
                print(f"  {row.month.strftime('%Y-%m')}: {row.tasks_count:,} задач")

        except Exception as e:
            print(f"Ошибка при анализе роста данных: {e}")

    def get_recommendations(self):
        """Получить рекомендации по оптимизации."""
        print("\n💡 РЕКОМЕНДАЦИИ ПО ОПТИМИЗАЦИИ")
        print("=" * 50)

        recommendations = [
            "1. КРИТИЧНО: Оптимизировать метод _cleanup_duplicate_history() - загружает все записи в память",
            "2. ВЫСОКИЙ ПРИОРИТЕТ: Использовать bulk операции вместо поштучной вставки",
            "3. СРЕДНИЙ ПРИОРИТЕТ: Добавить кэширование полных данных задач в JSONB колонке",
            "4. Проверить настройки пула соединений (текущие: pool_size=20, max_overflow=30)",
            "5. Рассмотреть партиционирование таблицы tracker_task_history по датам",
            "6. Добавить составной индекс для поиска дубликатов: (task_id, status, start_date)",
            "7. Настроить мониторинг медленных запросов через pg_stat_statements",
            "8. Рассмотреть архивирование старых записей истории",
        ]

        for rec in recommendations:
            print(f"  {rec}")

    def run_full_analysis(self):
        """Запустить полный анализ."""
        print("🔍 АНАЛИЗ СОСТОЯНИЯ БАЗЫ ДАННЫХ")
        print("=" * 60)
        print(f"Время анализа: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"База данных: {settings.DATABASE_URL_SYNC}")
        print("=" * 60)

        self.analyze_table_sizes()
        self.analyze_table_stats()
        self.analyze_indexes()
        self.analyze_duplicate_history()
        self.analyze_missing_indexes()
        self.analyze_connection_pool()
        self.analyze_data_growth()
        self.analyze_slow_queries()
        self.get_recommendations()

        print("\n✅ Анализ завершен")


def main():
    """Главная функция."""
    try:
        with DatabaseAnalyzer() as analyzer:
            analyzer.run_full_analysis()
    except Exception as e:
        print(f"❌ Ошибка при анализе базы данных: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
