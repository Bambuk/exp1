# Миграции базы данных с Alembic

Этот проект использует Alembic для управления миграциями базы данных PostgreSQL.

## Структура

```
alembic/
├── env.py              # Конфигурация окружения Alembic
├── script.py.mako      # Шаблон для генерации файлов миграций
├── versions/           # Папка с файлами миграций
│   └── 99e284f2522b_initial_migration_based_on_existing_.py
└── alembic.ini        # Основной конфигурационный файл
```

## Команды Alembic

### Основные команды

```bash
# Проверить текущую версию
alembic current

# Показать историю миграций
alembic history

# Создать новую миграцию на основе изменений в моделях
alembic revision --autogenerate -m "Описание изменений"

# Применить все миграции до последней версии
alembic upgrade head

# Применить миграции до конкретной версии
alembic upgrade <revision_id>

# Откатить миграции на одну версию назад
alembic downgrade -1

# Откатить миграции до конкретной версии
alembic downgrade <revision_id>

# Показать SQL для миграции без выполнения
alembic upgrade <revision_id> --sql
```

### Работа с существующей схемой

Если у вас уже есть существующая схема базы данных:

1. **Сбросить состояние Alembic** (если нужно):
   ```bash
   # Подключиться к БД и очистить таблицу alembic_version
   DELETE FROM alembic_version;
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

### items
- `id` - первичный ключ
- `title` - название предмета
- `description` - описание
- `price` - цена в центах
- `image_url` - URL изображения
- `is_available` - доступен ли предмет
- `created_at` - дата создания
- `updated_at` - дата обновления
- `owner_id` - внешний ключ на users.id

## Индексы

- `ix_users_email` - уникальный индекс по email
- `ix_users_username` - уникальный индекс по username
- `ix_users_id` - индекс по id
- `ix_items_title` - индекс по title
- `ix_items_id` - индекс по id

## Связи

- `items.owner_id` -> `users.id` (ForeignKey)

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
