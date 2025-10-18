# Scripts

Эта папка содержит все скрипты для различных задач проекта.

## Структура

### `sync/` - Скрипты синхронизации
- Синхронизация с Yandex Tracker выполняется через модуль `radiator.commands.sync_tracker`
- `sync_by_keys.py` - Батчевая синхронизация задач по ключам из файла

### `database/` - Скрипты для работы с базой данных
- `check_db.py` - Проверка содержимого базы данных
- `create_test_db.py` - Создание тестовой базы данных

### `reports/` - Скрипты для генерации отчетов
- Отчеты генерируются через команды `make generate-*`

### `analysis/` - Скрипты для анализа данных
- `real_cfd_parallel.py` - Анализ CFD с параллельной обработкой

### `testing/` - Тестовые скрипты
- Тестирование выполняется через `pytest tests/`

## Использование

Все скрипты можно запускать из корня проекта. Они автоматически добавляют корень проекта в Python path.

### sync_by_keys.py

Скрипт для батчевой синхронизации задач по ключам из файла. Решает проблему 504 Gateway Timeout при синхронизации большого количества задач.

**Аргументы:**
- `--file` / `-f`: путь к файлу с ключами задач (обязательный)
- `--batch-size` / `-b`: размер батча (по умолчанию 200)
- `--skip-history`: флаг для sync-tracker
- `--limit`: лимит для sync-tracker

**Примеры:**
```bash
# Базовое использование
python scripts/sync_by_keys.py --file data/input/my_keys.txt

# С кастомным размером батча
python scripts/sync_by_keys.py --file data/input/my_keys.txt --batch-size 100

# Через Makefile
make sync-tracker-by-keys FILE=data/input/my_keys.txt
make sync-tracker-by-keys FILE=data/input/my_keys.txt EXTRA_ARGS="--batch-size 100 --skip-history"
```

**Формат файла с ключами:**
```
FULLSTACK-1234
FULLSTACK-1235
CPO-789
```

**Особенности:**
- Игнорирует пустые строки
- Валидирует формат ключей (QUEUE-NUMBER)
- При ошибке батча прерывает работу с exit code 1
- Показывает прогресс с помощью tqdm

### Другие скрипты

Пример:
```bash
python -m radiator.commands.sync_tracker --filter "key:CPO-*" --limit 1000
```
