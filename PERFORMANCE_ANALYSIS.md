# 📊 Анализ производительности отчета TTM

## Дата: 10 октября 2025
## Метод: cProfile, 2 минуты работы

---

## 🔴 КРИТИЧЕСКАЯ ПРОБЛЕМА

### Проблема #1: N+1 Query в `get_task_hierarchy`

**Время выполнения**: 116 секунд из 117 (99% времени!)
**Количество запросов**: 62,111 запросов к БД
**Файл**: `radiator/commands/services/testing_returns_service.py:98`

#### Что происходит:

```python
def get_task_hierarchy(self, parent_key: str, visited: Optional[Set[str]] = None):
    # ❌ ПРОБЛЕМА: Загружает ВСЕ FULLSTACK задачи (10,003 шт!)
    subtasks = (
        self.db.query(TrackerTask.key)
        .filter(TrackerTask.key.like("FULLSTACK%"))
        .all()
    )

    # ❌ ПРОБЛЕМА: Для каждой задачи делает еще один запрос
    for (subtask_key,) in subtasks:  # 10,003 итераций!
        subtask = (
            self.db.query(TrackerTask)
            .filter(TrackerTask.key == subtask_key)
            .first()  # ❌ 10,003 дополнительных запросов!
        )
```

#### Статистика:
- **Вызвано**: 7 раз (для разных CPO задач)
- **Запросов за вызов**: ~8,873 запросов
- **Всего**: 7 × ~8,873 = **62,111 запросов к БД**
- **Время в БД**: 44 секунды (только execute)
- **Общее время**: 116 секунд

#### Почему это катастрофа:
1. Каждый раз загружаются **ВСЕ** 10,003 FULLSTACK задачи
2. Для каждой делается **дополнительный** запрос
3. Большинство задач **не являются** подзадачами
4. Это повторяется для **каждой CPO** задачи

---

## 📊 Детальная статистика

### Общая информация:
- **Всего вызовов функций**: 23,381,615
- **Время выполнения**: 115.156 секунд (2 минуты)
- **Количество функций**: 950
- **Запросов к PostgreSQL**: 62,253

### Топ-5 узких мест по времени:

| Функция | Вызовов | Время (сек) | % |
|---------|---------|-------------|---|
| `psycopg2.execute` | 62,253 | 42.9 | 37% |
| `get_task_hierarchy` | 7 | 116.3 | 101%* |
| `sqlalchemy._gen_cache_key` | 311,921 | 5.9 | 5% |
| `sqlalchemy.expect` | 311,673 | 3.5 | 3% |
| `json.raw_decode` | 62,064 | 3.5 | 3% |

*cumtime превышает tottime из-за рекурсивных вызовов

### Распределение времени:
- **БД запросы (execute)**: 44 сек (38%)
- **SQLAlchemy overhead**: 40 сек (35%)
- **get_task_hierarchy**: 30 сек (26%) - собственное время
- **Остальное**: 1 сек (1%)

---

## 💡 Решения

### ⚡ Решение #1: Исправить `get_task_hierarchy` (КРИТИЧНО!)

**Приоритет**: 🔴 НЕМЕДЛЕННО
**Ожидаемый эффект**: Уменьшение времени с **116 сек → 1-2 сек** (50x быстрее!)

#### Вариант A: Загрузить все связи одним запросом

```python
def get_task_hierarchy_optimized(self, parent_key: str) -> List[str]:
    """
    Get task hierarchy using a single recursive CTE query.
    """
    query = text("""
        WITH RECURSIVE task_tree AS (
            -- Base case: start with parent
            SELECT
                key,
                links,
                1 as level
            FROM tracker_tasks
            WHERE key = :parent_key

            UNION ALL

            -- Recursive case: find subtasks
            SELECT
                t.key,
                t.links,
                tt.level + 1
            FROM tracker_tasks t
            INNER JOIN task_tree tt ON (
                -- Check if t is a subtask of tt
                EXISTS (
                    SELECT 1
                    FROM jsonb_array_elements(t.links) AS link
                    WHERE link->>'type'->>'id' = 'subtask'
                    AND link->>'direction' = 'inward'
                    AND link->>'object'->>'key' = tt.key
                )
            )
            WHERE tt.level < 10  -- Prevent infinite recursion
        )
        SELECT key FROM task_tree;
    """)

    result = self.db.execute(query, {"parent_key": parent_key})
    return [row.key for row in result]
```

**Результат**: **1 SQL запрос** вместо 62,111!

#### Вариант B: Batch загрузка с фильтрацией в Python

```python
def get_task_hierarchy_batch(self, parent_key: str) -> List[str]:
    """
    Get task hierarchy using batch loading.
    """
    result = [parent_key]
    visited = {parent_key}
    to_process = [parent_key]

    while to_process:
        # Загружаем все задачи, которые могут быть подзадачами
        # текущего уровня одним запросом
        current_level = to_process
        to_process = []

        # ✅ ОДИН запрос для всего уровня
        subtasks = (
            self.db.query(TrackerTask.key, TrackerTask.links)
            .filter(TrackerTask.key.like("FULLSTACK%"))
            .all()
        )

        # Фильтрация в Python
        for subtask_key, links in subtasks:
            if subtask_key in visited:
                continue

            # Проверка, является ли подзадачей
            for link in (links or []):
                if (link.get("type", {}).get("id") == "subtask" and
                    link.get("direction") == "inward" and
                    link.get("object", {}).get("key") in current_level):
                    result.append(subtask_key)
                    visited.add(subtask_key)
                    to_process.append(subtask_key)
                    break

        if len(result) > 1000:  # Safety limit
            break

    return result
```

**Результат**: Количество запросов = **глубина иерархии** (обычно 2-3)

### ⚡ Решение #2: Batch загрузка истории задач

**Приоритет**: 🟡 ВЫСОКИЙ
**Ожидаемый эффект**: Дополнительное ускорение на 20-30%

```python
# data_service.py
def get_tasks_history_batch(self, task_ids: List[int]) -> Dict[int, List[StatusHistoryEntry]]:
    """
    Load history for multiple tasks in one query.
    """
    from collections import defaultdict

    history_query = (
        self.db.query(
            TrackerTaskHistory.task_id,
            TrackerTaskHistory.status,
            TrackerTaskHistory.status_display,
            TrackerTaskHistory.start_date,
            TrackerTaskHistory.end_date,
        )
        .filter(TrackerTaskHistory.task_id.in_(task_ids))
        .order_by(TrackerTaskHistory.task_id, TrackerTaskHistory.start_date)
    )

    result = defaultdict(list)
    for task_id, status, status_display, start_date, end_date in history_query.all():
        result[task_id].append(
            StatusHistoryEntry(status, status_display, start_date, end_date)
        )

    return result
```

**Применение в отчете**:
```python
# generate_time_to_market_report.py
# БЫЛО:
for task in ttd_tasks:
    history = self.data_service.get_task_history(task.id)  # 200 запросов

# СТАЛО:
all_task_ids = [task.id for task in ttd_tasks]
all_history = self.data_service.get_tasks_history_batch(all_task_ids)  # 1 запрос!

for task in ttd_tasks:
    history = all_history.get(task.id, [])
```

---

## 🎯 Ожидаемый результат

### До оптимизации:
- **Время**: 120+ секунд (прерывается по таймауту)
- **Запросов к БД**: ~62,000+
- **Узкое место**: get_task_hierarchy (99% времени)

### После Решения #1 (исправить get_task_hierarchy):
- **Время**: ~10-15 секунд (**8-12x быстрее**)
- **Запросов к БД**: ~500-1,000
- **Узкое место**: загрузка истории задач

### После Решения #1 + #2 (+ batch loading):
- **Время**: ~5-8 секунд (**15-24x быстрее**)
- **Запросов к БД**: ~50-100
- **Узкое место**: расчет метрик в Python

---

## 🔧 План внедрения

### Этап 1: Критические исправления (1-2 часа)
1. ✅ Создать профилирующий скрипт
2. ✅ Выявить узкие места
3. ⏳ Исправить `get_task_hierarchy` (Вариант A или B)
4. ⏳ Протестировать

### Этап 2: Дополнительные оптимизации (2-3 часа)
5. ⏳ Реализовать `get_tasks_history_batch`
6. ⏳ Обновить `generate_time_to_market_report`
7. ⏳ Протестировать производительность

### Этап 3: SQL-оптимизации (опционально, 3-4 часа)
8. ⏳ Добавить composite индексы
9. ⏳ Рассмотреть SQL-расчет метрик
10. ⏳ Финальное тестирование

---

## 📝 Заключение

**Основная проблема**: `get_task_hierarchy` делает 62,111 запросов к БД вместо 1-10.

**Решение**: Переписать на recursive CTE или batch loading.

**Эффект**: Ускорение в **50-100 раз** (с 120+ сек до 1-2 сек для этой функции).

**Приоритет**: 🔴 КРИТИЧЕСКИЙ - исправить немедленно.

---

*Дата анализа: 10 октября 2025*
*Инструмент: Python cProfile*
*Файл профиля: ttm_profile_stats.prof*
