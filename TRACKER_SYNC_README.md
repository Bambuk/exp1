# Синхронизация данных из Yandex Tracker

Этот модуль позволяет автоматически синхронизировать данные о задачах и их истории из Yandex Tracker API в базу данных.

## Возможности

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

### 3. Создание файла со списком задач

Создайте файл `tasks.txt` со списком ID задач для синхронизации:

```txt
12345
67890
11111
22222
33333
```

Каждая строка должна содержать один ID задачи. Пустые строки и комментарии (начинающиеся с #) игнорируются.

### 4. Настройка базы данных

Убедитесь, что база данных настроена и доступна. Модели будут созданы автоматически при первом запуске.

## Использование

### Ручной запуск

```bash
# Обычная синхронизация
python sync_tracker.py tasks.txt

# Синхронизация с отладочной информацией
python sync_tracker.py tasks.txt --debug

# Принудительная полная синхронизация
python sync_tracker.py tasks.txt --force-full-sync
```

### Через Makefile

```bash
# Обычная синхронизация
make sync-tracker

# Синхронизация с отладкой
make sync-tracker-debug

# Принудительная полная синхронизация
make sync-tracker-force
```

### Автоматическая синхронизация

#### Linux/macOS (cron)

```bash
# Настройка cron-задачи (каждый час)
chmod +x setup_cron.sh
./setup_cron.sh
```

#### Windows (Планировщик задач)

```powershell
# Запуск PowerShell от имени администратора
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\setup_cron.ps1
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
python sync_tracker.py tasks.txt >> logs/sync.log 2>&1
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

## Производительность

- **Параллельная обработка**: до 10 задач одновременно
- **Rate limiting**: 0.1 секунды между запросами
- **Батчевая обработка**: до 100 задач за раз
- **Инкрементальная синхронизация**: только новые/измененные данные

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
