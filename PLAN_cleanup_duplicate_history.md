# План оптимизации _cleanup_duplicate_history()

## Проблема

Метод загружает все 88,462 записи в память Python (строка 362 в `radiator/commands/sync_tracker.py`), что при росте данных приведет к критическим проблемам производительности.

## Решение

### 1. Написать тесты (TDD)

Обновить `tests/test_sync_tracker_integration.py`:

- Добавить тест с большим объемом данных (100+ дубликатов)
- Добавить тест с батчевым удалением
- Сохранить существующий `test_cleanup_duplicate_history`

### 2. Создать миграцию для составного индекса

Файл: `alembic/versions/XXXXX_add_history_dedup_index.py`

Добавить составной индекс для ускорения поиска дубликатов:

```sql
CREATE INDEX idx_tracker_history_dedup
ON tracker_task_history (task_id, status, start_date);
```

Этот индекс оптимизирует GROUP BY запрос по полям (task_id, status, start_date).

### 3. Переписать метод _cleanup_duplicate_history()

Файл: `radiator/commands/sync_tracker.py:358-381`

Заменить текущую реализацию на SQL-запрос с использованием CTE и window functions:

```python
def _cleanup_duplicate_history(self) -> int:
    """Clean up duplicate history entries using efficient SQL."""
    from sqlalchemy import text

    # Use CTE with ROW_NUMBER to find duplicates, keeping oldest record
    query = text("""
        WITH duplicates AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY task_id, status, start_date
                       ORDER BY created_at ASC
                   ) as row_num
            FROM tracker_task_history
        )
        DELETE FROM tracker_task_history
        WHERE id IN (
            SELECT id FROM duplicates WHERE row_num > 1
        )
        RETURNING id
    """)

    result = self.db.execute(query)
    deleted_count = result.rowcount
    self.db.commit()

    return deleted_count
```

**Преимущества:**

- Вся работа выполняется на стороне БД
- Используются индексы для быстрого GROUP BY
- Память Python не используется
- PostgreSQL window functions эффективнее Python циклов

### 4. Обновить логирование

Файл: `radiator/commands/sync_tracker.py:460`

Добавить метрики производительности в лог-сообщение.

## Ожидаемый результат

- Уменьшение потребления памяти: с O(N) до O(1)
- Ускорение работы: с O(N²) до O(N log N) за счет индексов
- Для 88K записей: с ~30 секунд до <1 секунды

## Шаги выполнения

1. [ ] Написать тесты для оптимизированного метода cleanup с большим объемом данных
2. [ ] Создать миграцию для добавления составного индекса (task_id, status, start_date)
3. [ ] Переписать _cleanup_duplicate_history() используя SQL CTE и window functions
4. [ ] Запустить тесты и убедиться, что все проходят
5. [ ] Применить миграцию на тестовой БД
