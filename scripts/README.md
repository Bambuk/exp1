# Scripts

Эта папка содержит все скрипты для различных задач проекта.

## Структура

### `sync/` - Скрипты синхронизации
- Синхронизация с Yandex Tracker выполняется через модуль `radiator.commands.sync_tracker`

### `database/` - Скрипты для работы с базой данных
- `check_db.py` - Проверка содержимого базы данных
- `create_test_db.py` - Создание тестовой базы данных
- `create_test_db.ps1` - PowerShell версия создания тестовой БД
- `migrate.ps1` - Запуск миграций базы данных

### `reports/` - Скрипты для генерации отчетов
- `generate_demo_report.ps1` - Генерация демо отчета
- `generate_status_report.ps1` - Генерация отчета по статусам

### `analysis/` - Скрипты для анализа данных
- `real_cfd_parallel.py` - Анализ CFD с параллельной обработкой
- `export_cpo_tasks.py` - Экспорт задач CPO
- `check_cpo_tasks.py` - Проверка задач CPO

### `testing/` - Тестовые скрипты
- `test_single_task.py` - Тестирование одной задачи
- `test_tracker_api.py` - Тестирование Tracker API
- `test_tracker_with_env.py` - Тестирование с переменными окружения

## Использование

Все скрипты можно запускать из корня проекта. Они автоматически добавляют корень проекта в Python path.

Пример:
```bash
python -m radiator.commands.sync_tracker --filter "key:CPO-*" --limit 1000
```
