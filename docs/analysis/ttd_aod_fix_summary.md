# Исправление TTD метрики для as-of-date отчетов

## Проблема

Метрика TTD (Time To Delivery - время от создания задачи до перехода в статус "Готова к разработке") не учитывала параметр `as_of_date` для задач, находящихся в статусе "Готова к разработке" с открытым интервалом.

### Пример проблемы

Для задачи, находящейся в статусе "Готова к разработке" с 2025-12-01 (без end_date):
- Отчет AOD 2026-01-18: TTD должен включать время до 2026-01-18
- Отчет текущий 2026-02-06: TTD должен включать время до 2026-02-06
- **До фикса**: TTD был одинаковым в обоих отчетах (рассчитывался только до момента входа в статус)

## Корневая причина

В методе `MetricsService.calculate_time_to_delivery()`:
1. TTD рассчитывался как время от start_date до момента входа в "Готова к разработке" (`target_entry.start_date`)
2. Для задач, которые **находятся** в статусе "Готова к разработке" с открытым интервалом, не учитывалось время пребывания в этом статусе
3. Не использовался параметр `as_of_date` для расчета TTD до исторической даты

## Примененные исправления

### 1. Обновление MetricsService

**Файл:** `radiator/commands/services/metrics_service.py`

**Изменения в методе `calculate_time_to_delivery`:**

1. Добавлен параметр `as_of_date: Optional[datetime] = None`

2. Добавлена логика для определения end_date:
```python
# Determine end date for TTD calculation
# If task still in "Готова к разработке" (open interval) and as_of_date provided
if target_entry.end_date is None and as_of_date is not None:
    from radiator.commands.services.datetime_utils import normalize_to_utc

    end_date = normalize_to_utc(as_of_date)
else:
    # Use start_date of "Готова к разработке" (when task entered this status)
    end_date = target_entry.start_date

# Calculate pause time only up to the end date
pause_time = self.calculate_pause_time_up_to_date(
    history_data, end_date
)

from radiator.commands.services.datetime_utils import normalize_to_utc
normalized_start = normalize_to_utc(start_date)
normalized_end = normalize_to_utc(end_date)

total_days = (normalized_end - normalized_start).days
effective_days = total_days - pause_time
return max(0, effective_days)
```

### 2. Обновление TTMDetailsReportGenerator

**Файл:** `radiator/commands/generate_ttm_details_report.py`

**Изменения в методе `_calculate_ttd`:**

1. Добавлен параметр `as_of_date: Optional[datetime] = None`
2. Проброс `as_of_date` в `metrics_service.calculate_time_to_delivery()`:
```python
return self.metrics_service.calculate_time_to_delivery(
    history, discovery_statuses, as_of_date=as_of_date
)
```

**Изменения в методе `_calculate_task_metrics`:**

Проброс `as_of_date` в вызов `_calculate_ttd`:
```python
"ttd": self._calculate_ttd(task.id, ["Готова к разработке"], history, as_of_date),
```

### 3. Тест

**Файл:** `tests/test_all_metrics_as_of_date.py`

Добавлен класс `TestTTDAsOfDate` с тестом:
- `test_ttd_with_as_of_date_for_open_ready_interval` - проверяет что TTD изменяется с разными as_of_date

## Результаты

### Тесты
- **Test TTD as-of-date** - ✅ **PASSED**
- **510 существующих тестов** - ✅ **PASSED**
- **0 регрессий**

### Логика работы

**Для задач, вышедших из "Готова к разработке":**
- TTD рассчитывается от start_date до момента входа в "Готова к разработке"
- `as_of_date` не влияет (TTD зафиксирован)

**Для задач в статусе "Готова к разработке" (open interval):**
- Без `as_of_date`: TTD = время до момента входа в статус (как раньше)
- С `as_of_date`: TTD = время от start_date до `as_of_date` (включая время в статусе "Готова к разработке")
- Учитывается pause time в этом периоде

## Важное замечание

Изменилась семантика TTD для незавершенных задач с открытым интервалом "Готова к разработке":

**Было:** TTD = время до **входа** в статус "Готова к разработке"
**Стало:** TTD = время до `as_of_date` (включая время **в** статусе "Готова к разработке")

Это более корректное поведение для исторических отчетов, так как показывает сколько времени прошло от создания задачи до указанной даты для задач, которые все еще находятся в фазе готовности к разработке.

## Обратная совместимость

Все изменения обратно совместимы:
- Параметр `as_of_date` имеет значение по умолчанию `None`
- Если `as_of_date` не передан, поведение для закрытых интервалов остается прежним
- Для открытых интервалов без `as_of_date` возвращается момент входа в статус
- Все существующие вызовы методов продолжают работать без изменений

## Покрытие as-of-date метрик

После этого исправления:

**✅ Поддерживают as-of-date (5/9):**
1. DevLT ✅
2. TTM (unfinished) ✅
3. Pause ✅
4. Tail ✅
5. **TTD** ✅ (исправлено)

**❌ Требуют исправления (4/9):**
6. Discovery backlog (дни)
7. Готова к разработке (дни)
8. TTD Pause
9. calculate_status_duration (базовый метод)

**Прогресс: 56% метрик поддерживают as-of-date** (было 44%)

## Дата исправления

2026-02-06
