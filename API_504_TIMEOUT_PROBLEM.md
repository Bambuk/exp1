# Проблема: 504 Gateway Timeout при синхронизации с Yandex Tracker API

## Описание проблемы

Команда `sync-tracker` падает с ошибкой **504 Gateway Timeout** даже при запросах с ограничением в 1 день.

### Пример ошибки:
```bash
make sync-tracker FILTER="Queue: FULLSTACK Updated: 2025-08-02 .. 2025-08-03"
```

**Лог ошибки:**
```
🚫 API Error 504: 504 Server Error: Gateway time out for url: https://api.tracker.yandex.net/v3/issues/_search?scrollType=unsorted&perScroll=1000&scrollTTLMillis=60000&expand=links
📍 Request details: method=POST, url=https://api.tracker.yandex.net/v3/issues/_search
📍 Request params: {'scrollType': 'unsorted', 'perScroll': 1000, 'scrollTTLMillis': 60000, 'expand': 'links'}
📍 Request json: {'query': 'Queue: FULLSTACK Updated: 2025-08-02 .. 2025-08-03'}
```

## Анализ проблемы

### 1. Текущая реализация
- Используется **scroll-пагинация** (`scrollType=unsorted`)
- Размер батча: **1000 задач** (`perScroll=1000`)
- TTL: **60 секунд** (`scrollTTLMillis=60000`)
- API не успевает обработать даже 1000 задач за раз

### 2. Местоположение проблемы
**Файл:** `radiator/services/tracker_service.py`
**Строка:** ~1342
```python
params = {
    "scrollType": "unsorted",
    "perScroll": 1000,  # ← ПРОБЛЕМА: слишком много
    "scrollTTLMillis": 60000,
    "expand": "links" if expand is None else ",".join(expand),
}
```

### 3. Логика выбора пагинации
**Файл:** `radiator/services/tracker_service.py`
**Строка:** ~822
```python
if limit > 10000:  # ← При >10000 задач используется scroll
    logger.info(f"Используем scroll-пагинацию (v3) для {limit} задач")
    return self._search_tasks_with_scroll(...)
```

## Предлагаемые решения

### Решение 1: Уменьшить размер батча (быстрое)
```python
# В _search_tasks_with_scroll
params = {
    "scrollType": "unsorted",
    "perScroll": 50,  # Уменьшить с 1000 до 50
    "scrollTTLMillis": 30000,  # Уменьшить с 60000 до 30000
    "expand": "links" if expand is None else ",".join(expand),
}
```

### Решение 2: Добавить retry для 504 ошибок
```python
max_retries = 3
retry_delay = 5  # секунд

for attempt in range(max_retries):
    try:
        response = self._make_request(...)
        break
    except HTTPError as e:
        if e.response.status_code == 504 and attempt < max_retries - 1:
            logger.warning(f"🔄 504 ошибка, повтор через {retry_delay}с")
            time.sleep(retry_delay)
            retry_delay *= 2
            continue
        raise
```

### Решение 3: Изменить порог для scroll-пагинации
```python
# В search_tasks
if limit > 1000:  # Уменьшить с 10000 до 1000
    logger.info(f"Используем scroll-пагинацию (v3) для {limit} задач")
    return self._search_tasks_with_scroll(...)
```

### Решение 4: Двухэтапная загрузка (радикальное)
1. **Этап 1:** Получить только ID задач через `search_tasks` (без данных)
2. **Этап 2:** Загружать задачи по батчам через `get_tasks_batch`

```python
def get_tasks_to_sync_in_batches(self, filters, limit=None, batch_size=20):
    # 1. Получаем только ID
    task_ids = tracker_service.search_tasks(filters["query"], limit)

    # 2. Загружаем по батчам
    all_tasks = []
    for i in range(0, len(task_ids), batch_size):
        batch_ids = task_ids[i:i + batch_size]
        batch_tasks = tracker_service.get_tasks_batch(batch_ids)
        all_tasks.extend(batch_tasks)

    return all_tasks
```

## Рекомендация

Начать с **Решения 1** (уменьшить `perScroll` до 50) как самого простого и быстрого. Если не поможет, добавить **Решение 2** (retry для 504).

## Файлы для изменения

1. `radiator/services/tracker_service.py` - основная логика
2. `radiator/commands/sync_tracker.py` - возможно, добавить fallback логику
3. Тесты для проверки нового поведения

## Тестирование

```bash
# Тест с маленьким лимитом
make sync-tracker FILTER="Queue: FULLSTACK Updated: 2025-08-02 .. 2025-08-03" LIMIT=10

# Тест с большим лимитом
make sync-tracker FILTER="Queue: FULLSTACK Updated: 2025-08-02 .. 2025-08-03" LIMIT=1000
```

## Дополнительные стратегии

### Временные интервалы
Если даже уменьшение батча не помогает, можно разбить запрос по дням/часам:

```python
def get_tasks_to_sync_by_date_ranges(
    self,
    filters: Dict[str, Any] = None,
    limit: int = None,
    date_range_days: int = 1,  # Разбивать по дням
    max_tasks_per_day: int = 50,  # Максимум задач в день
) -> List[Any]:
    # Разбиваем запрос на временные интервалы
    # "Updated: >=2025-01-01" -> "Updated: 2025-01-01", "Updated: 2025-01-02", etc.
```

### Разбивка по статусам
```python
# Вместо одного запроса
"Queue: FULLSTACK Updated: >=2025-01-01"

# Делаем несколько
"Queue: FULLSTACK Status: Open Updated: >=2025-01-01"
"Queue: FULLSTACK Status: In Progress Updated: >=2025-01-01"
"Queue: FULLSTACK Status: Done Updated: >=2025-01-01"
```

### Разбивка по исполнителям
```python
# Получаем список исполнителей
assignees = get_assignees_list()
for assignee in assignees:
    query = f"Queue: FULLSTACK Assignee: {assignee} Updated: >=2025-01-01"
```
