# Синхронизация данных из Yandex Tracker

Этот модуль позволяет автоматически синхронизировать данные о задачах и их истории из Yandex Tracker API в базу данных.

## Возможности

- ✅ **Динамический поиск задач** - автоматический поиск через API вместо статичного списка
- ✅ Синхронизация данных о задачах (название, описание, статус, исполнитель и т.д.)
- ✅ Синхронизация истории изменений статусов задач
- ✅ Инкрементальная синхронизация (только новые/измененные данные)
- ✅ Параллельная обработка для ускорения синхронизации
- ✅ Логирование всех операций
- ✅ Автоматическое создание cron-задач
- ✅ Поддержка Windows и Linux

## Установка и настройка

### 1. Установка зависимостей

Убедитесь, что у вас установлены все необходимые зависимости:

```bash
pip install -r requirements.txt
```

### 2. Настройка переменных окружения

Создайте файл `.env` на основе `env.example` и заполните настройки:

```bash
# Yandex Tracker API Configuration
TRACKER_API_TOKEN=your_tracker_api_token_here
TRACKER_ORG_ID=your_organization_id_here
TRACKER_BASE_URL=https://api.tracker.yandex.net/v2/
TRACKER_MAX_WORKERS=10
TRACKER_REQUEST_DELAY=0.1
TRACKER_SYNC_BATCH_SIZE=100
```

**Где взять эти данные:**
- `TRACKER_API_TOKEN` - OAuth токен из Yandex Tracker
- `TRACKER_ORG_ID` - ID организации в Yandex Tracker

### 3. Настройка базы данных

Убедитесь, что база данных настроена и доступна. Модели будут созданы автоматически при первом запуске.

## Использование

### Новый API-режим (рекомендуется)

#### Синхронизация недавних задач (по умолчанию)
```bash
# Синхронизация задач, обновленных за последние 30 дней
python sync_tracker.py

# Синхронизация задач за последние 7 дней
python sync_tracker.py --days 7

# Синхронизация задач за последние 3 дня, максимум 50 задач
python sync_tracker.py --days 3 --limit 50
```

#### Синхронизация активных задач
```bash
# Синхронизация всех активных задач (не закрытых)
python sync_tracker.py --sync-mode active

# Синхронизация активных задач с лимитом
python sync_tracker.py --sync-mode active --limit 100
```

#### Синхронизация с фильтрами
```bash
# Синхронизация задач в определенном статусе
python sync_tracker.py --sync-mode filter --status "In Progress"

# Синхронизация задач для конкретного исполнителя
python sync_tracker.py --sync-mode filter --assignee "john.doe"

# Синхронизация задач для конкретной команды
python sync_tracker.py --sync-mode filter --team "Development"

# Комбинированные фильтры
python sync_tracker.py --sync-mode filter --status "Open" --assignee "john.doe" --limit 25
```


### Legacy режим (из файла)

```bash
# Синхронизация из файла (для обратной совместимости)
python sync_tracker.py --sync-mode file --file-path tasks.txt
```

### Через Makefile

```bash
# Синхронизация недавних задач
make sync-tracker

# Синхронизация активных задач
make sync-tracker-active

# Синхронизация за последние 7 дней
make sync-tracker-recent

# Синхронизация с фильтрами
make sync-tracker-filter

# Legacy режим из файла
make sync-tracker-file

# Синхронизация с отладкой
make sync-tracker-debug

```

### Автоматическая синхронизация

#### Linux/macOS (cron)

```bash
# Настройка cron-задачи (каждый час, задачи за последние 7 дней)
chmod +x setup_cron.sh
./setup_cron.sh
```

#### Windows (Планировщик задач)

```powershell
# Запуск PowerShell от имени администратора
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
bash setup_cron.sh
```

## Режимы синхронизации

### 1. **recent** (по умолчанию)
- Получает задачи, обновленные за указанный период
- Параметры: `--days N` (по умолчанию 30)
- Идеально для регулярной синхронизации

### 2. **active**
- Получает все активные (не закрытые) задачи
- Параметры: `--limit N` (по умолчанию 100)
- Подходит для полного обновления активных задач

### 3. **filter**
- Получает задачи по пользовательским фильтрам
- Параметры: `--status`, `--assignee`, `--team`, `--author`
- Гибкая настройка для специфических потребностей

### 4. **file** (legacy)
- Загружает список задач из файла
- Параметры: `--file-path PATH`
- Для обратной совместимости

## Примеры использования

### Регулярная синхронизация (cron)
```bash
# Каждый час синхронизируем задачи за последние 7 дней
0 * * * * cd /path/to/project && python sync_tracker.py --days 7 >> logs/sync.log 2>&1
```

### Синхронизация по расписанию
```bash
# Утром - все активные задачи
0 9 * * * cd /path/to/project && python sync_tracker.py --sync-mode active --limit 200

# Вечером - задачи за последние 24 часа
0 18 * * * cd /path/to/project && python sync_tracker.py --days 1 --limit 100
```

### Синхронизация по командам
```bash
# Задачи команды разработки
python sync_tracker.py --sync-mode filter --team "Development" --status "In Progress"

# Задачи конкретного исполнителя
python sync_tracker.py --sync-mode filter --assignee "alice.smith" --limit 50
```

## Структура базы данных

### Таблица `tracker_tasks`

Основная информация о задачах:
- `id` - внутренний ID записи
- `tracker_id` - ID задачи в Yandex Tracker
- `summary` - название задачи
- `description` - описание задачи
- `status` - текущий статус
- `author` - автор задачи
- `assignee` - исполнитель
- `team` - команда
- `prodteam` - продуктовая команда
- `profit_forecast` - прогноз прибыли
- `created_at`, `updated_at`, `last_sync_at` - временные метки

### Таблица `tracker_task_history`

История изменений статусов:
- `id` - уникальный ID записи
- `task_id` - ссылка на задачу
- `tracker_id` - ID задачи в трекере
- `status` - статус
- `status_display` - отображаемое название статуса
- `start_date` - дата начала статуса
- `end_date` - дата окончания статуса

### Таблица `tracker_sync_logs`

Логи синхронизации:
- `id` - уникальный ID записи
- `sync_started_at` - время начала синхронизации
- `sync_completed_at` - время завершения
- `tasks_processed` - количество обработанных задач
- `tasks_created` - количество созданных задач
- `tasks_updated` - количество обновленных задач
- `errors_count` - количество ошибок
- `status` - статус синхронизации (running/completed/failed)

## Логирование

Все операции логируются в стандартный вывод и могут быть перенаправлены в файл:

```bash
python sync_tracker.py --sync-mode recent --days 7 >> logs/sync.log 2>&1
```

## Мониторинг

### Проверка статуса синхронизации

```sql
-- Последняя успешная синхронизация
SELECT * FROM tracker_sync_logs
WHERE status = 'completed'
ORDER BY sync_completed_at DESC
LIMIT 1;

-- Статистика по дням
SELECT
    DATE(sync_started_at) as sync_date,
    COUNT(*) as sync_count,
    SUM(tasks_processed) as total_tasks,
    SUM(tasks_created) as total_created,
    SUM(tasks_updated) as total_updated
FROM tracker_sync_logs
WHERE status = 'completed'
GROUP BY DATE(sync_started_at)
ORDER BY sync_date DESC;
```

### Проверка данных

```sql
-- Количество задач по статусам
SELECT status, COUNT(*) as count
FROM tracker_tasks
GROUP BY status;

-- История изменений для конкретной задачи
SELECT * FROM tracker_task_history
WHERE tracker_id = '12345'
ORDER BY start_date;
```

## Устранение неполадок

### Ошибки API

- Проверьте правильность `TRACKER_API_TOKEN` и `TRACKER_ORG_ID`
- Убедитесь, что токен не истек
- Проверьте права доступа к API

### Ошибки базы данных

- Убедитесь, что база данных доступна
- Проверьте права доступа пользователя БД
- Проверьте логи подключения

### Медленная синхронизация

- Уменьшите `TRACKER_REQUEST_DELAY` (но не ниже 0.1)
- Увеличьте `TRACKER_MAX_WORKERS` (но не выше 20)
- Проверьте скорость интернет-соединения

### Нет задач для синхронизации

- Проверьте фильтры поиска
- Увеличьте период поиска (`--days`)
- Проверьте, есть ли задачи в трекере с указанными критериями

## Производительность

- **Параллельная обработка**: до 10 задач одновременно
- **Rate limiting**: 0.1 секунды между запросами
- **Батчевая обработка**: до 100 задач за раз
- **Инкрементальная синхронизация**: только новые/измененные данные
- **API поиск**: автоматическое получение актуальных задач

## Безопасность

- Токены API хранятся в переменных окружения
- Все запросы к API логируются
- Ошибки не содержат чувствительной информации
- Поддержка HTTPS для всех API-запросов

## Поддержка

При возникновении проблем:

1. Проверьте логи синхронизации
2. Убедитесь в корректности настроек
3. Проверьте доступность API и базы данных
4. Запустите с флагом `--debug` для детальной информации
5. Проверьте фильтры поиска и период синхронизации
