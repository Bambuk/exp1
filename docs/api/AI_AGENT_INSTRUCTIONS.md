# 🤖 AI Agent Instructions: Yandex Tracker Sync System

## 📋 **ПРОЕКТ: Система синхронизации данных из Yandex Tracker**

### **Цель проекта:**
Автоматическая синхронизация задач и их истории из Yandex Tracker API в PostgreSQL базу данных через cron/планировщик задач.

---

## 🏗️ **АРХИТЕКТУРА СИСТЕМЫ**

### **Основные компоненты:**

#### 1. **Модели базы данных** (`radiator/models/tracker.py`)
- `TrackerTask` - основная информация о задачах
- `TrackerTaskHistory` - история изменений статусов
- `TrackerSyncLog` - логи синхронизации

#### 2. **API сервис** (`radiator/services/tracker_service.py`)
- `TrackerAPIService` - взаимодействие с Yandex Tracker API
- Методы поиска задач: `search_tasks()`, `get_recent_tasks()`, `get_active_tasks()`
- Параллельная обработка с rate limiting

#### 3. **CRUD операции** (`radiator/crud/tracker.py`)
- `CRUDTrackerTask` - операции с задачами
- `CRUDTrackerTaskHistory` - операции с историей
- `CRUDTrackerSyncLog` - операции с логами

#### 4. **Команда синхронизации** (`radiator/commands/sync_tracker.py`)
- `TrackerSyncCommand` - основная логика синхронизации
- Поддержка различных режимов: recent, active, filter, file
- Инкрементальная синхронизация

#### 5. **Конфигурация** (`radiator/core/config.py`)
- Настройки API трекера
- Параметры производительности
- Переменные окружения

---

## 🔧 **ТЕХНИЧЕСКИЕ ДЕТАЛИ**

### **База данных:**
- **Тип:** PostgreSQL
- **Схема:** Отдельные таблицы для трекера (не конфликтуют с существующими)
- **Миграции:** Alembic (`alembic/versions/add_tracker_tables.py`)

### **API интеграция:**
- **Endpoint:** `https://api.tracker.yandex.net/v2/issues`
- **Аутентификация:** OAuth токен + X-Org-ID
- **Rate limiting:** 0.1 сек между запросами
- **Параллелизм:** до 10 одновременных запросов

### **Режимы синхронизации:**
1. **`recent`** - задачи за указанный период (по умолчанию)
2. **`active`** - активные (не закрытые) задачи
3. **`filter`** - с пользовательскими фильтрами
4. **`file`** - legacy режим из файла

---

## 🚀 **ИСПОЛЬЗОВАНИЕ СИСТЕМЫ**

### **Базовые команды:**
```bash
# Синхронизация недавних задач (последние 30 дней)
python sync_tracker.py

# Синхронизация за последние 7 дней
python sync_tracker.py --days 7

# Синхронизация активных задач
python sync_tracker.py --sync-mode active

# Синхронизация с фильтрами
python sync_tracker.py --sync-mode filter --status "In Progress"

# Принудительная полная синхронизация
python sync_tracker.py --force-full-sync
```

### **Через Makefile:**
```bash
make sync-tracker          # недавние задачи
make sync-tracker-active   # активные задачи
make sync-tracker-recent   # за 7 дней
make sync-tracker-filter   # с фильтрами
make sync-tracker-debug    # с отладкой
```

---

## ⚙️ **НАСТРОЙКА И РАЗВЕРТЫВАНИЕ**

### **Переменные окружения** (`.env`):
```bash
# Yandex Tracker API
TRACKER_API_TOKEN=your_oauth_token_here
TRACKER_ORG_ID=your_organization_id_here
TRACKER_BASE_URL=https://api.tracker.yandex.net/v2/
TRACKER_MAX_WORKERS=10
TRACKER_REQUEST_DELAY=0.1

# База данных
DATABASE_URL_SYNC=postgresql://user:pass@localhost:5432/dbname
```

### **Автоматизация:**

#### **Linux/macOS (cron):**
```bash
chmod +x setup_cron.sh
./setup_cron.sh
# Создает cron-задачу: каждый час, задачи за последние 7 дней
```

#### **Windows (Планировщик задач):**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\setup_cron.ps1
# Создает задачу: каждый час, задачи за последние 7 дней
```

---

## 🧪 **ТЕСТИРОВАНИЕ**

### **Тестовый скрипт:**
```bash
python test_tracker_sync.py
# Проверяет: окружение, БД, API, запускает тестовую синхронизацию
```

### **Что тестируется:**
1. ✅ Настройки окружения
2. ✅ Подключение к базе данных
3. ✅ Доступность API трекера
4. ✅ Поиск задач через API
5. ✅ Тестовая синхронизация (5 задач за 3 дня)

---

## 🔍 **ОТЛАДКА И МОНИТОРИНГ**

### **Логирование:**
- Все операции логируются в стандартный вывод
- Можно перенаправить в файл: `>> logs/sync.log 2>&1`
- Уровень отладки: `--debug` флаг

### **Мониторинг синхронизации:**
```sql
-- Последняя успешная синхронизация
SELECT * FROM tracker_sync_logs 
WHERE status = 'completed' 
ORDER BY sync_completed_at DESC LIMIT 1;

-- Статистика по дням
SELECT DATE(sync_started_at) as sync_date,
       COUNT(*) as sync_count,
       SUM(tasks_processed) as total_tasks
FROM tracker_sync_logs 
WHERE status = 'completed'
GROUP BY DATE(sync_started_at);
```

### **Проверка данных:**
```sql
-- Количество задач по статусам
SELECT status, COUNT(*) as count 
FROM tracker_tasks GROUP BY status;

-- История изменений для задачи
SELECT * FROM tracker_task_history 
WHERE tracker_id = 'task_id_here' 
ORDER BY start_date;
```

---

## 🚨 **ИЗВЕСТНЫЕ ПРОБЛЕМЫ И РЕШЕНИЯ**

### **1. Ошибка 422 при сложных запросах по статусам:**
- **Проблема:** Сложные OR-запросы не поддерживаются API
- **Решение:** Используйте простые запросы или fallback на получение всех задач

### **2. Rate limiting:**
- **Проблема:** API может блокировать при частых запросах
- **Решение:** Увеличьте `TRACKER_REQUEST_DELAY` до 0.2-0.5 сек

### **3. Потеря контекста при длинных чатах:**
- **Проблема:** AI может "забыть" детали проекта
- **Решение:** Используйте этот файл как справочник

---

## 📚 **КЛЮЧЕВЫЕ ФАЙЛЫ ДЛЯ ПОНИМАНИЯ:**

### **Обязательно изучить:**
1. `radiator/models/tracker.py` - структура данных
2. `radiator/services/tracker_service.py` - логика API
3. `radiator/commands/sync_tracker.py` - основная команда
4. `radiator/crud/tracker.py` - операции с БД

### **Дополнительно:**
1. `TRACKER_SYNC_README.md` - подробная документация
2. `test_tracker_sync.py` - примеры использования
3. `setup_cron.sh` / `setup_cron.ps1` - автоматизация

---

## 🎯 **ТИПИЧНЫЕ ЗАДАЧИ И РЕШЕНИЯ**

### **Добавить новый фильтр поиска:**
1. Обновить `get_tasks_by_filter()` в `tracker_service.py`
2. Добавить параметр в `sync_tracker.py`
3. Обновить документацию

### **Изменить структуру данных:**
1. Обновить модель в `tracker.py`
2. Создать миграцию Alembic
3. Обновить CRUD операции
4. Обновить команду синхронизации

### **Оптимизировать производительность:**
1. Увеличить `TRACKER_MAX_WORKERS`
2. Уменьшить `TRACKER_REQUEST_DELAY`
3. Добавить кэширование результатов

---

## 🔗 **ПОЛЕЗНЫЕ ССЫЛКИ:**

- **Yandex Tracker API:** https://cloud.yandex.ru/docs/tracker/api
- **SQLAlchemy:** https://docs.sqlalchemy.org/
- **Alembic:** https://alembic.sqlalchemy.org/
- **Проект на GitHub:** [ссылка на репозиторий]

---

## 💡 **СОВЕТЫ ДЛЯ AI-АССИСТЕНТА:**

1. **Всегда проверяйте** переменные окружения перед запуском
2. **Используйте тестовый скрипт** для диагностики проблем
3. **Логируйте все операции** для отладки
4. **Помните о rate limiting** API трекера
5. **Проверяйте структуру БД** перед изменениями
6. **Тестируйте изменения** на небольшом объеме данных
7. **Документируйте все изменения** в коде

---

**📝 Последнее обновление:** 27 августа 2025  
**🔧 Версия системы:** 1.0  
**👨‍💻 Разработчик:** AI Assistant + User  
**✅ Статус:** Полностью функциональна и готова к продакшену
