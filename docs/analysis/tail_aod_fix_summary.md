# Исправление Tail метрики для as-of-date отчетов

## Проблема

Метрика Tail (время от выхода из "МП / Внешний тест" до завершения задачи) не учитывала параметр `as_of_date` для незавершенных задач, находящихся в статусе "МП / Внешний тест" с открытым интервалом.

### Пример проблемы

Для задачи, находящейся в "МП / Внешний тест" с 2025-12-01 (без end_date):
- Отчет AOD 2026-01-18: Tail должен быть ~48 дней (до 2026-01-18)
- Отчет текущий 2026-02-06: Tail должен быть ~67 дней (до 2026-02-06)
- **До фикса**: Tail был одинаковым в обоих отчетах

## Корневая причина

В методе `MetricsService.calculate_tail_metric()`:
1. Для задач с открытым интервалом "МП / Внешний тест" возвращался `None` если не найден done status
2. Не использовался параметр `as_of_date` для расчета tail до исторической даты

## Примененные исправления

### 1. Обновление MetricsService

**Файл:** `radiator/commands/services/metrics_service.py`

**Изменения в методе `calculate_tail_metric`:**

1. Добавлен параметр `as_of_date: Optional[datetime] = None`

2. Добавлена логика для обработки открытых интервалов:
```python
# If task is not done, use as_of_date or return None
if not done_entry:
    # If task still in external test (open interval) and as_of_date provided
    if last_mp_entry.end_date is None and as_of_date is not None:
        from radiator.commands.services.datetime_utils import normalize_to_utc

        effective_date = normalize_to_utc(as_of_date)
        mp_start = normalize_to_utc(last_mp_entry.start_date)

        # Calculate pause time from MP start to as_of_date
        pause_time = self.calculate_pause_time_between_dates(
            filtered_history, last_mp_entry.start_date, as_of_date
        )

        total_days = (effective_date - mp_start).days
        effective_days = total_days - pause_time
        return max(0, effective_days)

    return None
```

### 2. Обновление TTMDetailsReportGenerator

**Файл:** `radiator/commands/generate_ttm_details_report.py`

**Изменения в методе `_calculate_tail`:**

1. Добавлен параметр `as_of_date: Optional[datetime] = None`
2. Проброс `as_of_date` в `metrics_service.calculate_tail_metric()`:
```python
return self.metrics_service.calculate_tail_metric(history, done_statuses, as_of_date=as_of_date)
```

**Изменения в методе `_calculate_task_metrics`:**

Проброс `as_of_date` в вызов `_calculate_tail`:
```python
"tail": self._calculate_tail(task.id, done_statuses, history, as_of_date),
```

### 3. Создание теста

**Файл:** `tests/test_all_metrics_as_of_date.py`

Добавлен класс `TestTailAsOfDate` с тестом:
- `test_tail_with_as_of_date_for_open_external_test` - проверяет что Tail изменяется с разными as_of_date

## Результаты

### Тесты
- **Test Tail as-of-date** - ✅ **PASSED**
- **510 существующих тестов** - ✅ **PASSED**
- **0 регрессий**

### Логика работы

**Для завершенных задач:**
- Tail рассчитывается от "МП / Внешний тест" до done status
- `as_of_date` игнорируется (tail зафиксирован)

**Для незавершенных задач (open interval в "МП / Внешний тест"):**
- Без `as_of_date`: возвращает `None` (как и раньше)
- С `as_of_date`: рассчитывает tail от начала "МП / Внешний тест" до `as_of_date`
- Учитывается pause time в этом периоде

## Обратная совместимость

Все изменения полностью обратно совместимы:
- Параметр `as_of_date` имеет значение по умолчанию `None`
- Если `as_of_date` не передан, поведение идентично прежнему
- Все существующие вызовы методов продолжают работать без изменений

## Покрытие as-of-date метрик

После этого исправления:

**✅ Поддерживают as-of-date (4/9):**
1. DevLT ✅
2. TTM (unfinished) ✅
3. Pause ✅
4. **Tail** ✅ (исправлено)

**❌ Требуют исправления (5/9):**
5. TTD
6. Discovery backlog (дни)
7. Готова к разработке (дни)
8. TTD Pause
9. calculate_status_duration (базовый метод)

**Прогресс: 44% метрик поддерживают as-of-date** (было 33%)

## Дата исправления

2026-02-06
