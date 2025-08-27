# 🚀 Quick Reference: Yandex Tracker Sync

## ⚡ **БЫСТРЫЙ СТАРТ**

```bash
# 1. Проверить настройки
python test_tracker_sync.py

# 2. Запустить синхронизацию
python sync_tracker.py

# 3. Настроить автоматизацию
./setup_cron.sh          # Linux/macOS
.\setup_cron.ps1         # Windows
```

## 🔑 **ОСНОВНЫЕ КОМАНДЫ**

```bash
# Синхронизация
python sync_tracker.py                           # последние 30 дней
python sync_tracker.py --days 7                  # последние 7 дней
python sync_tracker.py --sync-mode active        # активные задачи
python sync_tracker.py --sync-mode filter --status "In Progress"  # с фильтром

# Отладка
python sync_tracker.py --debug                   # с подробными логами
python sync_tracker.py --force-full-sync         # принудительная полная синхронизация
```

## ⚙️ **НАСТРОЙКИ (.env)**

```bash
TRACKER_API_TOKEN=your_token_here
TRACKER_ORG_ID=your_org_id_here
DATABASE_URL_SYNC=postgresql://user:pass@localhost:5432/dbname
```

## 📊 **МОНИТОРИНГ**

```sql
-- Статус синхронизации
SELECT * FROM tracker_sync_logs ORDER BY sync_started_at DESC LIMIT 5;

-- Количество задач по статусам
SELECT status, COUNT(*) FROM tracker_tasks GROUP BY status;

-- История изменений
SELECT * FROM tracker_task_history WHERE tracker_id = 'task_id' ORDER BY start_date;
```

## 🚨 **РЕШЕНИЕ ПРОБЛЕМ**

| Проблема | Решение |
|----------|---------|
| API ошибка 422 | Упростить запрос, убрать сложные OR |
| Медленная синхронизация | Увеличить `TRACKER_MAX_WORKERS` |
| Блокировка API | Увеличить `TRACKER_REQUEST_DELAY` |
| Нет задач | Проверить фильтры, увеличить период |

## 📁 **КЛЮЧЕВЫЕ ФАЙЛЫ**

- `radiator/models/tracker.py` - модели БД
- `radiator/services/tracker_service.py` - API логика
- `radiator/commands/sync_tracker.py` - команда синхронизации
- `test_tracker_sync.py` - тестирование
- `AI_AGENT_INSTRUCTIONS.md` - подробные инструкции

## 🎯 **РЕЖИМЫ СИНХРОНИЗАЦИИ**

- **`recent`** - задачи за период (по умолчанию)
- **`active`** - активные задачи
- **`filter`** - с пользовательскими фильтрами
- **`file`** - из файла (legacy)

## 🔧 **MAKEFILE КОМАНДЫ**

```bash
make sync-tracker          # недавние задачи
make sync-tracker-active   # активные задачи
make sync-tracker-recent   # за 7 дней
make sync-tracker-debug    # с отладкой
make test-tracker-sync     # запустить тесты
```

---
**📖 Полная документация:** `AI_AGENT_INSTRUCTIONS.md`  
**🧪 Тестирование:** `python test_tracker_sync.py`  
**✅ Статус:** Готово к продакшену
