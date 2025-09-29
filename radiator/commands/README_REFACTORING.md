# Рефакторинг Time To Market Report

## Обзор

Этот документ описывает рефакторинг команды генерации отчетов Time To Market, направленный на улучшение архитектуры, читаемости и поддерживаемости кода.

## Проблемы исходного кода

1. **Монолитный класс** - один класс выполнял слишком много функций
2. **Дублирование кода** - повторяющаяся логика для TTD/TTM
3. **Смешение ответственности** - данные, бизнес-логика и рендеринг в одном месте
4. **Слабая типизация** - отсутствие четких типов данных
5. **Сложная конфигурация** - загрузка конфигов разбросана по методам
6. **Отсутствие тестов** - нет тестов для критической логики

## Архитектура после рефакторинга

### 1. Модели данных (`models/`)

- **`time_to_market_models.py`** - типизированные модели данных
- Четкое разделение между конфигурацией, данными и результатами
- Использование dataclasses для упрощения работы с данными
- Enum'ы для типов отчетов и группировки

### 2. Сервисы (`services/`)

- **`config_service.py`** - загрузка и управление конфигурацией
- **`data_service.py`** - операции с базой данных
- **`metrics_service.py`** - расчет метрик времени

### 3. Рендереры (`renderers/`)

- **`base_renderer.py`** - базовый класс для рендереров
- **`csv_renderer.py`** - генерация CSV отчетов
- **`table_renderer.py`** - генерация табличных изображений
- **`console_renderer.py`** - вывод в консоль

### 4. Основной класс

- **`generate_time_to_market_report_refactored.py`** - упрощенный основной класс
- Использует композицию сервисов
- Четкое разделение ответственности

## Преимущества рефакторинга

### 1. Разделение ответственности (Single Responsibility Principle)
- Каждый класс имеет одну четкую ответственность
- Легче понимать и изменять код

### 2. Открытость/закрытость (Open/Closed Principle)
- Легко добавлять новые форматы вывода (новые рендереры)
- Легко добавлять новые типы метрик

### 3. Принцип подстановки Лисков (Liskov Substitution Principle)
- Все рендереры взаимозаменяемы через базовый класс

### 4. Инверсия зависимостей (Dependency Inversion Principle)
- Высокоуровневые модули не зависят от низкоуровневых
- Зависимости инжектируются через конструктор

### 5. Улучшенная тестируемость
- Каждый сервис можно тестировать независимо
- Легко создавать моки для тестирования

### 6. Типизация
- Четкие типы данных с помощью dataclasses
- Лучшая поддержка IDE и статического анализа

## Использование

### Базовое использование

```python
from radiator.commands.generate_time_to_market_report_refactored import GenerateTimeToMarketReportCommand
from radiator.commands.models.time_to_market_models import GroupBy, ReportType

# Создание команды
with GenerateTimeToMarketReportCommand(group_by=GroupBy.AUTHOR) as cmd:
    # Генерация данных отчета
    report = cmd.generate_report_data()

    # Генерация CSV
    csv_file = cmd.generate_csv(report_type=ReportType.BOTH)

    # Генерация таблицы
    table_file = cmd.generate_table(report_type=ReportType.TTD)

    # Вывод в консоль
    cmd.print_summary(report_type=ReportType.TTM)
```

### Командная строка

```bash
# Группировка по авторам, оба типа отчетов
python -m radiator.commands.generate_time_to_market_report_refactored --group-by author --report-type both

# Группировка по командам, только TTD
python -m radiator.commands.generate_time_to_market_report_refactored --group-by team --report-type ttd

# Указание кастомной директории конфигурации
python -m radiator.commands.generate_time_to_market_report_refactored --config-dir /path/to/config
```

## Тестирование

```bash
# Запуск тестов
pytest tests/test_time_to_market_refactored.py -v

# Запуск с покрытием
pytest tests/test_time_to_market_refactored.py --cov=radiator.commands --cov-report=html
```

## Расширение функциональности

### Добавление нового формата вывода

1. Создать новый рендерер, наследующий от `BaseRenderer`
2. Реализовать метод `render()`
3. Добавить поддержку в основной класс

```python
class JSONRenderer(BaseRenderer):
    def render(self, filepath: Optional[str] = None, report_type: ReportType = ReportType.BOTH) -> str:
        # Реализация генерации JSON
        pass
```

### Добавление новых метрик

1. Добавить методы в `MetricsService`
2. Обновить модели данных при необходимости
3. Добавить поддержку в рендереры

## Миграция

Для миграции с старого кода:

1. Заменить импорты
2. Обновить вызовы методов (использовать enum'ы вместо строк)
3. Обновить обработку результатов

## Заключение

Рефакторинг значительно улучшил:
- **Читаемость** кода
- **Тестируемость** компонентов
- **Расширяемость** функциональности
- **Поддерживаемость** в долгосрочной перспективе

Код стал более модульным, типобезопасным и готовым к дальнейшему развитию.
