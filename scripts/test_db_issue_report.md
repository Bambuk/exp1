# Отчет: Тесты пишут в живую БД

## Проблема

Тесты могут писать в живую БД `radiator` вместо тестовой БД `radiator_test`.

## Причина

1. **TrackerSyncCommand создает SessionLocal() в __init__()**
   - При создании `TrackerSyncCommand()` в конструкторе создается `SessionLocal()`
   - `SessionLocal()` использует `settings.DATABASE_URL_SYNC` из конфигурации
   - Если переменная окружения `ENVIRONMENT=test` не установлена, используется живая БД

2. **Прямое использование SessionLocal() в тестах**
   - В `tests/test_ttm_details_report.py` (строки 572, 1369) используется `SessionLocal()` напрямую
   - Это обходит фикстуру `db_session` и может подключиться к живой БД

3. **Метод run() создает sync_log**
   - Метод `run()` вызывает `create_sync_log()`, который создает запись в `tracker_sync_logs`
   - Если подключение к живой БД, записи попадают туда

## Найденные проблемные места

### Критические (HIGH SEVERITY):

1. **tests/test_ttm_details_report.py**
   - Строка 569: `from radiator.core.database import SessionLocal`
   - Строка 572: `with SessionLocal() as db:` - **НАПРЯМУЮ ПОДКЛЮЧАЕТСЯ К БД**
   - Строка 1366: `from radiator.core.database import SessionLocal`
   - Строка 1369: `with SessionLocal() as db:` - **НАПРЯМУЮ ПОДКЛЮЧАЕТСЯ К БД**

2. **tests/test_incremental_sync.py**
   - Строка 17: `from radiator.core.database import SessionLocal` (импорт, но не используется напрямую)
   - Строки 115, 140, 228: `with TrackerSyncCommand() as sync_cmd:` - создает SessionLocal() в __init__

3. **tests/test_pagination_duplicate.py**
   - Строка 14: `from radiator.core.database import SessionLocal` (импорт, но не используется напрямую)
   - Множественные создания `TrackerSyncCommand()` - создает SessionLocal() в __init__

4. **Множественные тесты вызывают sync_cmd.run()**
   - `test_optimized_sync.py` - 3 вызова
   - `test_sync_error_handling.py` - 2 вызова
   - `test_sync_output_format.py` - 3 вызова
   - `test_sync_tracker_integration.py` - 2 вызова
   - И другие...

### Средние (MEDIUM SEVERITY):

- Все тесты, которые создают `TrackerSyncCommand()` без замены `db` на тестовую сессию
- Все тесты, которые проверяют `sync_log` из БД

## Проверка конфигурации

При проверке текущих настроек:
```python
ENVIRONMENT: NOT SET
DATABASE_URL_SYNC: postgresql://postgres:12345@192.168.1.108:5432/radiator
ENVIRONMENT setting: development
```

Это означает, что **БЕЗ pytest** (или если pytest-env не работает) используется живая БД.

## Решение

### Немедленные действия:

1. **Исправить test_ttm_details_report.py**
   - Заменить `SessionLocal()` на использование фикстуры `db_session`
   - Убрать прямые импорты `SessionLocal`

2. **Проверить все тесты с TrackerSyncCommand**
   - Убедиться, что все тесты заменяют `sync_cmd.db` на `db_session` из фикстуры
   - Или создать фикстуру, которая создает TrackerSyncCommand с тестовой сессией

3. **Проверить переменные окружения**
   - Убедиться, что `pytest-env` установлен и работает
   - Проверить, что `ENVIRONMENT=test` устанавливается при запуске тестов

### Долгосрочные улучшения:

1. **Изменить TrackerSyncCommand**
   - Принимать `db` как параметр в конструкторе
   - Не создавать SessionLocal() по умолчанию

2. **Создать фикстуру для TrackerSyncCommand**
   - Фикстура должна создавать TrackerSyncCommand с тестовой сессией

3. **Добавить проверку в CI/CD**
   - Проверять, что тесты не могут подключиться к живой БД

## Статистика

- Файлов с проблемами: 12
- Всего проблемных мест: 64
- Критических проблем: ~30
- Средних проблем: ~34
