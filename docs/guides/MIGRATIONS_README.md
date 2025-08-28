# Миграции базы данных

Этот документ описывает процесс управления миграциями базы данных в проекте Radiator.

## Обзор

Проект использует Alembic для управления миграциями базы данных PostgreSQL. Миграции позволяют:
- Отслеживать изменения схемы базы данных
- Применять изменения к базе данных
- Откатывать изменения при необходимости

## Структура

```
alembic/
├── versions/          # Файлы миграций
├── env.py            # Конфигурация окружения
├── script.py.mako    # Шаблон для новых миграций
└── alembic.ini       # Основной конфиг файл
```

## Команды

### Основные команды

1. **Инициализация** (выполнено):
   ```bash
   alembic init alembic
   ```

2. **Создать начальную миграцию**:
   ```bash
   alembic revision --autogenerate -m "Initial migration based on existing schema"
   ```

3. **Применить миграцию**:
   ```bash
   alembic upgrade head
   ```

## Текущая схема

Проект содержит следующие таблицы:

### users
- `id` - первичный ключ
- `email` - уникальный email пользователя
- `username` - уникальное имя пользователя
- `full_name` - полное имя
- `hashed_password` - хешированный пароль
- `is_active` - активен ли пользователь
- `is_superuser` - является ли суперпользователем
- `bio` - биография
- `avatar_url` - URL аватара
- `created_at` - дата создания
- `updated_at` - дата обновления

### tracker_tasks
- `id` - первичный ключ
- `tracker_id` - уникальный ID задачи в Yandex Tracker
- `key` - код задачи (например, TEST-123)
- `summary` - краткое описание
- `description` - полное описание
- `status` - текущий статус
- `assignee` - исполнитель
- `created_at` - дата создания
- `updated_at` - дата обновления
- `last_sync_at` - дата последней синхронизации

### tracker_task_history
- `id` - первичный ключ
- `task_id` - внешний ключ на tracker_tasks.id
- `status` - статус
- `status_display` - отображаемое название статуса
- `start_date` - дата начала статуса
- `end_date` - дата окончания статуса
- `created_at` - дата создания записи

### tracker_sync_log
- `id` - первичный ключ
- `sync_started_at` - время начала синхронизации
- `sync_completed_at` - время завершения синхронизации
- `status` - статус синхронизации
- `tasks_processed` - количество обработанных задач
- `tasks_created` - количество созданных задач
- `tasks_updated` - количество обновленных задач
- `history_entries_processed` - количество обработанных записей истории
- `error_message` - сообщение об ошибке (если есть)

## Индексы

- `ix_users_email` - уникальный индекс по email
- `ix_users_username` - уникальный индекс по username
- `ix_users_id` - индекс по id
- `ix_tracker_tasks_tracker_id` - уникальный индекс по tracker_id
- `ix_tracker_tasks_key` - индекс по коду задачи
- `ix_tracker_tasks_last_sync` - индекс по дате последней синхронизации
- `ix_tracker_history_task_status` - составной индекс по task_id и status
- `ix_tracker_history_dates` - составной индекс по start_date и end_date

## Добавление новых миграций

1. **Внесите изменения в модели** в папке `radiator/models/`

2. **Создайте миграцию**:
   ```bash
   alembic revision --autogenerate -m "Описание изменений"
   ```

3. **Проверьте сгенерированный код** в файле миграции

4. **Примените миграцию**:
   ```bash
   alembic upgrade head
   ```

## Откат миграций

```bash
# Откатить на одну версию назад
alembic downgrade -1

# Откатить до конкретной версии
alembic downgrade <revision_id>

# Откатить все миграции
alembic downgrade base
```

## Конфигурация

Основные настройки в `alembic.ini`:
- `sqlalchemy.url` - URL подключения к базе данных
- `script_location` - папка с миграциями
- `version_num_format` - формат номера версии

## Troubleshooting

### Ошибка "Can't locate revision"
Если Alembic не может найти ревизию:
1. Проверьте, что файл миграции существует в `alembic/versions/`
2. Убедитесь, что таблица `alembic_version` содержит правильный ID ревизии

### Проблемы с подключением
1. Проверьте переменные окружения `DATABASE_URL_SYNC`
2. Убедитесь, что PostgreSQL запущен и доступен
3. Проверьте права доступа к базе данных

### Конфликты схемы
Если схема в базе данных не соответствует моделям:
1. Создайте новую миграцию с `--autogenerate`
2. Проверьте сгенерированный код
3. При необходимости отредактируйте миграцию вручную
