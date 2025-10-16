# Оптимизация медленных тестов

## Топ-10 самых медленных тестов (по времени выполнения)

| № | Время | Тест | Статус | Примечания |
|---|-------|------|--------|------------|
| 1 | 9.45s | `tests/test_time_to_market_integration.py::TestTimeToMarketReportIntegration::test_generate_table_integration` | ⚪ Откачен | Интеграционный тест генерации таблиц - откачен к исходному состоянию |
| 2 | 6.66s | `tests/test_full_integration.py::TestFullIntegration::test_complete_search_tasks_workflow` | 🔴 Не оптимизирован | Полный workflow поиска задач |
| 3 | 4.03s | `tests/test_error_handling.py::TestErrorHandling::test_search_tasks_invalid_query` | 🔴 Не оптимизирован | Тест обработки ошибок поиска |
| 4 | 3.54s | `tests/test_error_handling.py::TestErrorHandling::test_search_tasks_empty_result` | 🔴 Не оптимизирован | Тест пустых результатов поиска |
| 5 | 2.32s | `tests/test_error_handling.py::TestErrorHandling::test_memory_usage_edge_cases` | 🔴 Не оптимизирован | Тест граничных случаев памяти |
| 6 | 1.15s | `tests/test_time_to_market_integration.py::TestTimeToMarketReportIntegration::test_full_workflow_author_grouping` | 🔴 Не оптимизирован | Workflow группировки по авторам |
| 7 | 1.14s | `tests/test_time_to_market_integration.py::TestTimeToMarketReportIntegration::test_error_handling_integration` | 🔴 Не оптимизирован | Интеграционный тест обработки ошибок |
| 8 | 1.14s | `tests/test_time_to_market_integration.py::TestTimeToMarketReportIntegration::test_generate_csv_integration` | 🔴 Не оптимизирован | Интеграционный тест генерации CSV |
| 9 | 1.13s | `tests/test_time_to_market_integration.py::TestTimeToMarketReportIntegration::test_context_manager_cleanup` | 🔴 Не оптимизирован | Тест очистки контекста |
| 10 | 1.12s | `tests/test_time_to_market_integration.py::TestTimeToMarketReportIntegration::test_different_report_types` | 🔴 Не оптимизирован | Тест разных типов отчетов |

## Статусы оптимизации

- 🔴 **Не оптимизирован** - тест еще не был оптимизирован
- 🟡 **В работе** - тест находится в процессе оптимизации
- 🟢 **Оптимизирован** - тест был оптимизирован
- ⚪ **Пропущен** - тест пропущен по каким-то причинам

## План оптимизации

### Приоритет 1 (критически медленные > 5s)
1. `test_generate_table_integration` (9.45s)
2. `test_complete_search_tasks_workflow` (6.66s)

### Приоритет 2 (медленные 2-5s)
3. `test_search_tasks_invalid_query` (4.03s)
4. `test_search_tasks_empty_result` (3.54s)
5. `test_memory_usage_edge_cases` (2.32s)

### Приоритет 3 (умеренно медленные 1-2s)
6-10. Остальные тесты time-to-market интеграции

## Возможные стратегии оптимизации

1. **Мокирование внешних зависимостей** - замена реальных API вызовов на моки
2. **Параллельное выполнение** - использование pytest-xdist для параллельного запуска
3. **Кэширование данных** - кэширование тестовых данных между тестами
4. **Уменьшение объема данных** - использование меньших наборов тестовых данных
5. **Оптимизация фикстур** - улучшение setup/teardown процессов
6. **Разделение интеграционных тестов** - выделение быстрых unit-тестов

## История изменений

- **2024-01-XX** - Создан файл отслеживания медленных тестов
- **2024-01-XX** - Попытка оптимизации test_generate_table_integration с моками
- **2024-01-XX** - Откат изменений - решено оставить интеграционные тесты как есть

## Команды для тестирования

```bash
# Запуск конкретного медленного теста
pytest tests/test_time_to_market_integration.py::TestTimeToMarketReportIntegration::test_generate_table_integration -v

# Запуск с профилированием времени
pytest --durations=10 -v

# Запуск только медленных тестов (>1s)
pytest --durations=1 -v
```
