# Status History Update Command

Команда для обновления истории статусов задач из Yandex Tracker по указанному запросу.

## 🎯 **Назначение**

Команда `UpdateStatusHistoryCommand` предназначена для:
- Поиска задач, которые изменили статус за указанный период
- Обновления истории статусов для найденных задач
- Работы с конкретными очередями (CPO, DEV, QA и др.)
- Логирования всех операций синхронизации

## 📋 **Использование**

### **Командная строка:**

```bash
# Базовое использование (CPO очередь, последние 14 дней)
python radiator/commands/update_status_history.py

# С указанием очереди и периода
python radiator/commands/update_status_history.py --queue DEV --days 7

# С ограничением количества задач
python radiator/commands/update_status_history.py --queue QA --days 30 --limit 500

# Включение подробного логирования
python radiator/commands/update_status_history.py --queue CPO --days 14 --verbose
```

### **PowerShell скрипт:**

```powershell
# Базовое использование
.\update_status_history.ps1

# С параметрами
.\update_status_history.ps1 -Queue "DEV" -Days 7 -Limit 100

# С подробным логированием
.\update_status_history.ps1 -Queue "QA" -Days 30 -Verbose
```

### **Makefile команды (Linux/macOS):**

```bash
# Обновление истории для CPO очереди (последние 14 дней)
make update-status-history-cpo

# Обновление истории для DEV очереди (последние 7 дней)
make update-status-history-dev

# Обновление истории для QA очереди (последние 30 дней)
make update-status-history-qa

# Пользовательские параметры
make update-status-history-custom QUEUE=SUPPORT DAYS=7 LIMIT=500
```

## 🔧 **Параметры**

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `--queue` | Название очереди для фильтрации задач | `CPO` |
| `--days` | Количество дней для поиска изменений статуса | `14` |
| `--limit` | Максимальное количество задач для обработки | `1000` |
| `--verbose` | Включить подробное логирование | `False` |

## 📊 **Логика работы**

### **1. Поиск задач:**
```
Query: Queue: {QUEUE} "Last status change": today()-{DAYS}d..today() "Sort by": Updated DESC
```

**Пример запроса для CPO очереди за 14 дней:**
```
Queue: CPO "Last status change": today()-14d..today() "Sort by": Updated DESC
```

### **2. Обработка каждой задачи:**
- Получение задачи из базы данных
- Загрузка changelog из Yandex Tracker API
- Извлечение истории изменений статуса
- Удаление старой истории
- Создание новой истории
- Обновление timestamp'а последней синхронизации

### **3. Логирование операций:**
- Создание записи в `tracker_sync_logs`
- Обновление статуса и статистики
- Запись ошибок при неудачных операциях

## 🗄️ **Структура данных**

### **Модель TrackerTaskHistory:**
```python
class TrackerTaskHistory(Base):
    __tablename__ = "tracker_task_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(Integer, nullable=False, index=True)
    tracker_id = Column(String(255), nullable=False, index=True)
    status = Column(String(255), nullable=False)
    status_display = Column(String(255), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### **Пример данных:**
```sql
INSERT INTO tracker_task_history VALUES (
    'uuid-123', 1, 'TEST-456', 'open', 'Открыт', 
    '2024-01-15 09:00:00', '2024-01-15 11:30:00', 
    '2024-01-15 10:00:00'
);
```

## 🚀 **Примеры использования**

### **Обновление истории для CPO очереди:**
```bash
# Последние 14 дней
python radiator/commands/update_status_history.py --queue CPO --days 14

# Последние 7 дней с ограничением
python radiator/commands/update_status_history.py --queue CPO --days 7 --limit 200
```

### **Обновление истории для DEV очереди:**
```bash
# Последние 7 дней
python radiator/commands/update_status_history.py --queue DEV --days 7

# С подробным логированием
python radiator/commands/update_status_history.py --queue DEV --days 7 --verbose
```

### **Обновление истории для QA очереди:**
```bash
# Последние 30 дней
python radiator/commands/update_status_history.py --queue QA --days 30

# С ограничением количества задач
python radiator/commands/update_status_history.py --queue QA --days 30 --limit 500
```

## 📝 **Логи и мониторинг**

### **Уровни логирования:**
- **INFO**: Основные операции (поиск задач, создание истории)
- **DEBUG**: Детальная информация (количество записей, время выполнения)
- **WARNING**: Пропущенные задачи (не найдены в БД, нет changelog)
- **ERROR**: Критические ошибки (API недоступен, ошибки БД)

### **Метрики в базе данных:**
```sql
-- Последние операции синхронизации
SELECT * FROM tracker_sync_logs 
WHERE status = 'completed' 
ORDER BY sync_completed_at DESC 
LIMIT 10;

-- Статистика по очередям
SELECT 
    COUNT(*) as total_tasks,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed
FROM tracker_sync_logs;
```

## ⚠️ **Ограничения и особенности**

### **1. Полная перезапись истории:**
- При каждой синхронизации **вся история удаляется** и создается заново
- Это обеспечивает актуальность данных, но может быть ресурсоемко

### **2. Зависимость от существующих задач:**
- Команда работает только с задачами, которые уже есть в базе данных
- Если задача не найдена, она пропускается с предупреждением

### **3. Rate limiting:**
- Учитывается `TRACKER_REQUEST_DELAY` из настроек
- Параллельная обработка ограничена `TRACKER_MAX_WORKERS`

### **4. Размер данных:**
- По умолчанию обрабатывается до 1000 задач
- Можно увеличить лимит, но это может занять много времени

## 🔍 **Отладка и диагностика**

### **Проверка конфигурации:**
```bash
# Проверка переменных окружения
python -c "from radiator.core.config import settings; print('API Token:', bool(settings.TRACKER_API_TOKEN))"

# Проверка подключения к БД
python -c "from radiator.core.database import SessionLocal; db = SessionLocal(); print('DB OK')"
```

### **Тестирование API:**
```bash
# Проверка доступности Yandex Tracker API
python -c "from radiator.services.tracker_service import tracker_service; print('API OK')"
```

### **Проверка логов:**
```bash
# Запуск с подробным логированием
python radiator/commands/update_status_history.py --queue CPO --days 1 --verbose
```

## 📚 **Связанные компоненты**

- **`TrackerAPIService`** - взаимодействие с Yandex Tracker API
- **`CRUDTrackerTaskHistory`** - операции с историей статусов
- **`TrackerSyncLog`** - логирование операций синхронизации
- **`sync_tracker.py`** - основная команда синхронизации задач

## 🎯 **Лучшие практики**

1. **Регулярность выполнения:** Запускайте команду регулярно (например, через cron)
2. **Мониторинг логов:** Следите за ошибками и предупреждениями
3. **Оптимизация периодов:** Используйте разумные периоды (7-30 дней)
4. **Ограничение задач:** Не обрабатывайте слишком много задач за раз
5. **Резервное копирование:** Делайте бэкапы перед массовыми обновлениями

## 🚨 **Устранение неполадок**

### **Ошибка "Task not found in database":**
- Задача не была синхронизирована ранее
- Запустите основную синхронизацию: `python sync_tracker.py`

### **Ошибка "API request failed":**
- Проверьте `TRACKER_API_TOKEN` и `TRACKER_ORG_ID`
- Убедитесь в доступности Yandex Tracker API

### **Ошибка "Database connection failed":**
- Проверьте настройки подключения к БД
- Убедитесь, что PostgreSQL запущен

### **Медленная работа:**
- Уменьшите количество параллельных запросов (`TRACKER_MAX_WORKERS`)
- Увеличьте задержку между запросами (`TRACKER_REQUEST_DELAY`)
- Ограничьте количество задач (`--limit`)
