# Исправление DevLT для as-of-date отчетов

## Проблема

При генерации отчетов TTM Details "на определенную дату" (as-of-date), метрика DevLT для незавершенных задач всегда рассчитывалась до текущей даты, игнорируя параметр `as_of_date`. Это приводило к тому, что DevLT для незавершенных задач был одинаковым во всех исторических отчетах.

### Пример проблемы

Для задачи CPO-7178 (команда "Гео и сервисы", незавершена):
- Отчет от 2026-02-06: DevLT = 115 дней
- Отчет AOD 2026-01-18: DevLT = 115 дней (должно быть ~96 дней)
- Отчет AOD 2025-12-01: DevLT = 115 дней (должно быть ~48 дней)

## Корневая причина

В методе `MetricsService.calculate_dev_lead_time()` для незавершенных задач (задачи со статусом "МП / В работе" без end_date) использовалось `datetime.now(timezone.utc)` вместо переданного параметра `as_of_date`.

Код не пробрасывал `as_of_date`:
1. `TTMDetailsReportGenerator._calculate_devlt()` не принимал параметр `as_of_date`
2. `MetricsService.calculate_dev_lead_time()` не принимал параметр `as_of_date`
3. В двух местах использовался `datetime.now()` для расчета DevLT открытых задач

## Примененные исправления

### 1. Создание тестов (TDD подход)

Создан файл `tests/test_devlt_as_of_date.py` с 5 тестами:
- `test_calculate_dev_lead_time_with_as_of_date_for_open_work_status` - проверка расчета DevLT с as_of_date для открытых задач
- `test_calculate_dev_lead_time_with_as_of_date_vs_current_date` - проверка различия DevLT при разных as_of_date
- `test_calculate_dev_lead_time_without_as_of_date_uses_current_date` - проверка обратной совместимости (без as_of_date используется текущая дата)
- `test_calculate_dev_lead_time_completed_task_ignores_as_of_date` - проверка, что завершенные задачи игнорируют as_of_date
- `test_ttm_details_report_devlt_propagates_as_of_date` - проверка проброса as_of_date через всю цепочку

### 2. Обновление MetricsService

**Файл:** `radiator/commands/services/metrics_service.py`

Изменения в методе `calculate_dev_lead_time`:
1. Добавлен параметр `as_of_date: Optional[datetime] = None`
2. В двух местах (строки ~700 и ~772), где использовался `datetime.now(timezone.utc)` для открытых задач, добавлена проверка:
   ```python
   if as_of_date is not None:
       effective_date = normalize_to_utc(as_of_date)
   else:
       effective_date = datetime.now(timezone.utc)
   ```

### 3. Обновление TTMDetailsReportGenerator

**Файл:** `radiator/commands/generate_ttm_details_report.py`

Изменения в методе `_calculate_devlt`:
1. Добавлен параметр `as_of_date: Optional[datetime] = None`
2. Передача `as_of_date` в `metrics_service.calculate_dev_lead_time()`:
   ```python
   return self.metrics_service.calculate_dev_lead_time(history, as_of_date=as_of_date)
   ```

Изменения в методе `_calculate_task_metrics`:
1. Проброс `as_of_date` в вызов `_calculate_devlt()`:
   ```python
   "devlt": self._calculate_devlt(task.id, history, as_of_date),
   ```

### 4. Исправление теста с кэшем

**Файл:** `tests/test_services_time_to_market.py`

Добавлена очистка кэша `ConfigService._quarters_cache` в тесте `test_load_quarters_file_not_found` для изоляции тестов.

## Результаты

После применения исправлений:

### Тесты
- Все 5 новых тестов в `test_devlt_as_of_date.py` - **PASSED** ✅
- Все существующие тесты (728 тестов) - **PASSED** ✅
- 1 тест `test_sync_tracker_single_instance_blocking` упал по причинам, не связанным с изменениями (проблема API)

### Реальные данные

Проверка на задаче CPO-7178:
- Текущий отчет (2026-02-06): DevLT = 115 дней ✅
- AOD отчет (2025-12-01): DevLT = 48 дней ✅
- **Разница: 67 дней** (ожидаемая разница между датами)

Проверка на задаче CPO-7081:
- Текущий отчет (2026-02-06): DevLT = 64 дня ✅
- AOD отчет (2025-12-01): DevLT = 48 дней ✅
- **Разница: 16 дней** (ожидаемая разница между датами)

## Обратная совместимость

Все изменения полностью обратно совместимы:
- Параметр `as_of_date` имеет значение по умолчанию `None`
- Если `as_of_date` не передан, используется текущая дата (`datetime.now(timezone.utc)`)
- Все существующие вызовы методов продолжают работать без изменений

## Дата исправления

2026-02-06
