# Changelog: Исправление логических изъянов TTM и TTD

**Дата:** 2025-10-06

## Исправленные проблемы

### 🔴 Проблема #1: Рассогласование в расчете Pause Time для статистики

**Что было:**
В основном цикле обработки задач (`generate_time_to_market_report.py`, строки 160 и 183) использовался метод `calculate_pause_time(history)`, который вычислял **полное** время паузы для всей истории задачи, включая паузы **после** достижения целевого статуса.

При этом в методах `calculate_time_to_delivery` и `calculate_time_to_market` правильно использовался `calculate_pause_time_up_to_date`, который вычитал паузы только до целевого статуса.

**Последствия:**
- TTD/TTM корректно вычитали только релевантные паузы
- Но в статистику `pause_times` попадало завышенное значение, включающее паузы после целевого статуса
- Метрики `pause_mean` и `pause_p85` в отчетах были некорректны

**Что исправлено:**
Изменена логика в `generate_time_to_market_report.py`:

**Для TTD задач (строки 159-178):**
```python
# Теперь вычисляем pause time только до "Готова к разработке"
ttd = self.metrics_service.calculate_time_to_delivery(
    history, status_mapping.discovery_statuses
)
if ttd is not None:
    # Находим дату перехода в "Готова к разработке"
    sorted_history = sorted(history, key=lambda x: x.start_date)
    ttd_target_date = None
    for entry in sorted_history:
        if entry.status == "Готова к разработке":
            ttd_target_date = entry.start_date
            break

    # Вычисляем pause time ТОЛЬКО до этой даты
    pause_time = self.metrics_service.calculate_pause_time_up_to_date(
        history, ttd_target_date
    ) if ttd_target_date else 0

    group_data[group_value]["ttd_times"].append(ttd)
    group_data[group_value]["ttd_pause_times"].append(pause_time)
```

**Для TTM задач (строки 192-211):**
```python
# Теперь вычисляем pause time только до первого done статуса
ttm = self.metrics_service.calculate_time_to_market(
    history, status_mapping.done_statuses
)
if ttm is not None:
    # Находим дату первого done статуса
    sorted_history = sorted(history, key=lambda x: x.start_date)
    ttm_target_date = None
    for entry in sorted_history:
        if entry.status in status_mapping.done_statuses:
            ttm_target_date = entry.start_date
            break

    # Вычисляем pause time ТОЛЬКО до этой даты
    pause_time = self.metrics_service.calculate_pause_time_up_to_date(
        history, ttm_target_date
    ) if ttm_target_date else 0

    group_data[group_value]["ttm_times"].append(ttm)
    group_data[group_value]["ttm_pause_times"].append(pause_time)
```

**Результат:**
- Статистика `pause_mean` и `pause_p85` теперь соответствует **реально вычтенному** pause time из TTD/TTM
- Данные в отчетах корректны и согласованы

---

### 🔴 Проблема #2: Некорректный консольный вывод total_tasks

**Что было:**
В консольном выводе (`console_renderer.py`, строка 143) показывалось:
```python
print(f"Total tasks analyzed: {self.report.total_tasks}")
```

Где `total_tasks = ttd_metrics.count + ttm_metrics.count`, что приводило к подсчету одной задачи дважды, если она:
- Перешла в "Готова к разработке" в Q1 (учтена в ttd_metrics)
- Перешла в "Done" в Q2 (учтена в ttm_metrics)

**Что исправлено:**
Удалена строка с выводом `total_tasks` из консоли (`console_renderer.py`, строка 143).

**Результат:**
- Консольный вывод больше не вводит в заблуждение
- В CSV/таблицах по-прежнему показываются **отдельные счетчики** для каждой метрики (ttd_tasks, ttm_tasks), которые корректны

---

## Добавленные тесты

Добавлены новые тесты в `tests/test_pause_time_metrics.py`:

### 1. `test_pause_time_up_to_date_excludes_later_pauses`
Проверяет, что `calculate_pause_time_up_to_date` корректно исключает паузы после указанной даты:
- Пауза ДО целевого статуса: учитывается ✅
- Пауза ПОСЛЕ целевого статуса: не учитывается ✅

### 2. `test_pause_time_statistics_match_calculation`
Проверяет полное соответствие:
- TTD вычитает правильное pause time
- Pause time для статистики совпадает с вычтенным значением
- TTM вычитает правильное pause time (включая обе паузы)
- Pause time для статистики совпадает с вычтенным значением

**Результат тестов:**
```
======================= 13 passed, 29 warnings in 0.47s ========================
```
Все тесты пройдены успешно ✅

---

## Что НЕ менялось (по согласованию)

### Множественные переходы в один статус
Текущее поведение (брать **первый** переход в целевой статус) признано корректным с бизнес-точки зрения и оставлено без изменений.

### Определение квартала для задачи
Для каждой метрики квартал определяется по **своему** событию:
- TTD: по дате перехода в "Готова к разработке"
- TTM: по дате перехода в done статус

Это означает, что одна задача может попасть в разные кварталы для разных метрик - это нормально и соответствует бизнес-логике.

### task_details_csv
Не менялось по согласованию.

---

## Затронутые файлы

1. ✅ `radiator/commands/generate_time_to_market_report.py` - исправлен расчет pause time
2. ✅ `radiator/commands/renderers/console_renderer.py` - удален некорректный вывод
3. ✅ `tests/test_pause_time_metrics.py` - добавлены новые тесты
4. 📄 `ANALYSIS_TTM_TTD_LOGIC_FLAWS.md` - документация по найденным проблемам
5. 📄 `CHANGELOG_TTM_TTD_FIX.md` - этот файл

---

## Рекомендации по использованию

После применения исправлений:

1. **Пересгенерировать отчеты** - старые отчеты содержат некорректную статистику по pause time
2. **Проверить данные** - значения `pause_mean` и `pause_p85` теперь должны быть меньше или равны предыдущим
3. **Интерпретация метрик** - pause time в отчетах теперь точно соответствует тому, что было вычтено из TTD/TTM

---

## Backward Compatibility

⚠️ **Изменения в данных отчетов:**
- Значения `pause_mean` и `pause_p85` изменятся (уменьшатся)
- TTD/TTM значения остаются **без изменений** (они всегда считались правильно)
- Консольный вывод изменился (удалена строка с total_tasks)

**Рекомендация:** Если есть автоматизация, которая парсит консольный вывод, необходимо обновить скрипты.
