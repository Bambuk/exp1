# Архитектура системы одновременных загрузок в Google Sheets

## Обзор системы

Система использует **асинхронную архитектуру с маркерами файлов** для безопасной обработки одновременных запросов загрузки в Google Sheets.

## Компоненты системы

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Telegram Bot  │    │  File Monitor    │    │ Google Sheets   │
│                 │    │                  │    │   Service       │
│ • Обработка     │───▶│ • Создание       │───▶│ • Загрузка      │
│   callback      │    │   маркеров       │    │   данных        │
│   запросов      │    │ • Отслеживание   │    │ • Создание      │
│ • Создание      │    │   состояния      │    │   листов        │
│   кнопок        │    │ • Очистка        │    │ • Форматирование│
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Поток обработки одновременных запросов

### 1. Пользователь нажимает кнопки (одновременно)

```
Пользователь нажимает:
├── Кнопка "📊 Загрузить в Google Sheets" для file1.csv
├── Кнопка "📊 Загрузить в Google Sheets" для file2.csv
└── Кнопка "📊 Загрузить в Google Sheets" для file3.csv
```

### 2. Telegram Bot обрабатывает callback запросы

```python
async def handle_callback_query(self, callback_query):
    # Каждый запрос обрабатывается независимо
    if query_data.startswith("upload_csv:"):
        filename = query_data.split(":", 1)[1]
        await self._handle_upload_csv_request(query_id, filename)
```

### 3. Создание маркеров файлов (атомарно)

```python
async def _handle_upload_csv_request(self, query_id: str, filename: str):
    # Создание маркера файла
    marker_filename = f".upload_me_{filename}"
    marker_path = self.reports_dir / marker_filename

    with open(marker_path, "w", encoding="utf-8") as f:
        f.write(f"Upload request for {filename}\n")
        f.write(f"Created at: {datetime.now().isoformat()}\n")
```

**Результат:**
```
reports/
├── file1.csv
├── file2.csv
├── file3.csv
├── .upload_me_file1.csv  ← Маркер для file1.csv
├── .upload_me_file2.csv  ← Маркер для file2.csv
└── .upload_me_file3.csv  ← Маркер для file3.csv
```

### 4. Фоновый процесс обработки

```python
def start_monitoring(self):
    while True:
        # Поиск файлов с маркерами
        files_with_markers = self.file_monitor.get_files_with_upload_markers()

        for filename in files_with_markers:
            # Обработка файла
            success = self.process_single_file(file_path)
            if success:
                # Удаление маркера после успешной обработки
                self.file_monitor.remove_upload_marker(filename)
```

## Безопасность при одновременных запросах

### ✅ Что работает безопасно:

1. **Атомарное создание маркеров**
   - Каждый маркер создается в отдельном файле
   - Нет race conditions при создании маркеров
   - Файловые операции атомарны на уровне ОС

2. **Независимая обработка запросов**
   - Каждый callback запрос обрабатывается асинхронно
   - Нет блокировок между разными файлами
   - Все запросы получают ответ от бота

3. **Защита от дубликатов**
   - Множественные запросы для одного файла не создают дубликатов
   - Последний запрос перезаписывает маркер
   - Система обрабатывает каждый файл только один раз

### ⚠️ Потенциальные проблемы:

1. **Ограничения Google Sheets API**
   - Rate limiting (100 запросов в 100 секунд на пользователя)
   - Одновременные запросы могут превысить лимиты
   - Рекомендуется добавить очередь с задержками

2. **Конфликты имен листов**
   - Если несколько файлов имеют одинаковые имена
   - Google Sheets может переименовать листы автоматически
   - Рекомендуется добавить уникальные суффиксы

## Рекомендации по улучшению

### 1. Добавить очередь обработки

```python
class UploadQueue:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.processing = set()

    async def add_upload_request(self, filename: str):
        await self.queue.put(filename)

    async def process_queue(self):
        while True:
            filename = await self.queue.get()
            if filename not in self.processing:
                self.processing.add(filename)
                await self.process_file(filename)
                self.processing.remove(filename)
```

### 2. Добавить rate limiting

```python
import time

class RateLimiter:
    def __init__(self, max_requests=90, time_window=100):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []

    async def wait_if_needed(self):
        now = time.time()
        # Удаляем старые запросы
        self.requests = [req_time for req_time in self.requests
                        if now - req_time < self.time_window]

        if len(self.requests) >= self.max_requests:
            sleep_time = self.time_window - (now - self.requests[0])
            await asyncio.sleep(sleep_time)

        self.requests.append(now)
```

### 3. Добавить уникальные имена листов

```python
def _generate_unique_sheet_name(self, filename: str) -> str:
    base_name = self._sanitize_sheet_name(filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base_name}_{timestamp}"
```

## Заключение

Текущая система **безопасно обрабатывает одновременные запросы** благодаря:

- Асинхронной архитектуре
- Атомарным операциям с файлами
- Независимой обработке запросов
- Системе маркеров для отслеживания состояния

Система готова к использованию в продакшене, но рекомендуется добавить дополнительные меры для работы с Google Sheets API.
