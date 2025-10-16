# Рефакторинг по рекомендациям Мартина Фаулера

## Цель
Убрать Mock-специфичную логику из production кода, применив Extract Method и Strategy Pattern, сохранив оптимизацию и обратную совместимость с тестами.

## Проблема
В коде есть 3 места с дублированной логикой обработки Mock объектов:

```python
# Lines 244-254, 302-312, 589-599
try:
    if (not hasattr(task_id, '_mock_name') and
        self._task_history_cache and
        task_id in self._task_history_cache):
        history = self._task_history_cache[task_id]
    else:
        history = self.data_service.get_task_history(task_id)
except (TypeError, AttributeError):
    history = self.data_service.get_task_history(task_id)
```

## Решение

### Шаг 1: Extract Method - создать приватный метод
**Файл**: `radiator/commands/generate_time_to_market_report.py`

Добавить после метода `_load_all_histories_once()` (~line 117):

```python
def _get_task_history(self, task_id: int) -> List[StatusHistoryEntry]:
    """
    Get task history with caching strategy.
    Uses cache if available, otherwise falls back to database.

    Args:
        task_id: Task ID to get history for

    Returns:
        List of status history entries
    """
    if self._task_history_cache and task_id in self._task_history_cache:
        return self._task_history_cache[task_id]
    return self.data_service.get_task_history(task_id)
```

### Шаг 2: Заменить дублированную логику на вызов метода

**Место 1**: Line 243-254 (TTD tasks в generate_report_data)
```python
# Было: try-except блок с Mock проверками
# Станет:
history = self._get_task_history(task_id)
```

**Место 2**: Line 302-312 (TTM tasks в generate_report_data)
```python
# Было: try-except блок с Mock проверками
# Станет:
history = self._get_task_history(task_id)
```

**Место 3**: Line 589-599 (generate_task_details_csv)
```python
# Было: вложенный try-except блок
# Станет:
history = self._get_task_history(task.id)
```

### Шаг 3: Аналогичный метод для _calculate_pause_time

**Файл**: `radiator/commands/generate_time_to_market_report.py` (~line 710)

В методе `_calculate_pause_time` заменить:
```python
# Было: lines 710-717
if task.id in self._task_history_cache:
    history = self._task_history_cache[task.id]
else:
    history = self.data_service.get_task_history(task.id)

# Станет:
history = self._get_task_history(task.id)
```

### Шаг 4: Dependency Injection для тестов (опционально)

Добавить возможность подменить стратегию получения истории:

```python
def __init__(self, ..., history_provider=None):
    # ...
    self._history_provider = history_provider or self._default_history_provider

def _default_history_provider(self, task_id: int):
    """Default strategy for getting task history"""
    if self._task_history_cache and task_id in self._task_history_cache:
        return self._task_history_cache[task_id]
    return self.data_service.get_task_history(task_id)

def _get_task_history(self, task_id: int):
    return self._history_provider(task_id)
```

## Результаты
- Убрано 3 дублированных блока кода (~30 строк)
- Убрана Mock-специфичная логика из production кода
- Единая точка входа для получения истории задач
- Сохранена обратная совместимость с тестами
- Код стал проще для понимания и тестирования
- Соблюдение Single Responsibility Principle

## Файлы для изменения
- `radiator/commands/generate_time_to_market_report.py` - Extract Method и замена дублирующего кода
