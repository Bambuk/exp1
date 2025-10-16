# Google Sheets Commands в Makefile

Команды для управления Google Sheets CSV загрузчиком через Makefile.

## 🚀 Основные команды

### Запуск мониторинга
```bash
make google-sheets-monitor
```
Запускает непрерывный мониторинг файлов с маркерами загрузки.

### Тестирование
```bash
make google-sheets-test
```
Проверяет подключение к Google Sheets.

### Статистика
```bash
make google-sheets-stats
```
Показывает статистику загрузчика:
- Общее количество файлов
- Количество обработанных файлов
- Количество файлов с маркерами загрузки

## 🔧 Управление файлами

### Обработка файлов с маркерами
```bash
make google-sheets-process-markers
```
Обрабатывает только файлы, отмеченные для загрузки через Telegram.

### Обработка всех файлов
```bash
make google-sheets-process-all
```
Обрабатывает все необработанные CSV файлы (без маркеров).

### Очистка
```bash
make google-sheets-cleanup
```
Очищает старые записи из состояния загрузчика.

## ⚙️ Конфигурация

### Просмотр настроек
```bash
make google-sheets-config
```
Показывает текущую конфигурацию загрузчика.

### Тест интеграции
```bash
make google-sheets-test-integration
```
Запускает полный тест интеграции с Google Sheets.

## 📋 Примеры использования

### Полный workflow
```bash
# 1. Запустить Telegram бот
make telegram-bot

# 2. В отдельном терминале - запустить Google Sheets загрузчик
make google-sheets-monitor

# 3. В Telegram нажать кнопки "📊 Загрузить в Google Sheets" для нужных файлов
# 4. Файлы автоматически загрузятся в Google Sheets
```

### Ручная обработка
```bash
# Проверить статистику
make google-sheets-stats

# Обработать файлы с маркерами
make google-sheets-process-markers

# Проверить результат
make google-sheets-stats
```

### Отладка
```bash
# Тест подключения
make google-sheets-test

# Тест интеграции
make google-sheets-test-integration

# Просмотр конфигурации
make google-sheets-config
```

## 🔍 Мониторинг

### Проверка состояния
```bash
make google-sheets-stats
```

Вывод показывает:
- **Total files** - общее количество CSV файлов
- **Known files** - количество известных файлов
- **Processed files** - количество обработанных файлов
- **Unprocessed files** - количество необработанных файлов
- **Files with upload markers** - количество файлов с маркерами загрузки

### Логи
Логи сохраняются в `logs/google_sheets_bot.log` и выводятся в консоль.

## 🛠️ Устранение неполадок

### Проблемы с подключением
```bash
make google-sheets-test
```

### Проблемы с обработкой
```bash
make google-sheets-stats
make google-sheets-process-markers
```

### Очистка состояния
```bash
make google-sheets-cleanup
```

## 📚 Связанные команды

- `make telegram-bot` - запуск Telegram бота
- `make telegram-test` - тест Telegram бота
- `make help` - полный список команд
