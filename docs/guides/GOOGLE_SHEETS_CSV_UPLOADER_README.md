# Google Sheets CSV Uploader

Автоматический загрузчик CSV файлов в Google Sheets. Мониторит папку `reports` и автоматически загружает новые CSV файлы как новые листы в указанный Google Sheets документ.

## Возможности

- 🔍 Автоматический мониторинг папки `reports` на новые CSV файлы
- 📊 Загрузка CSV файлов как новых листов в Google Sheets
- 🔄 Обработка различных кодировок (UTF-8, Windows-1251, CP1251)
- 📝 Автоматическое именование листов на основе имени файла
- 🔍 **Автоматические фильтры** на всех данных (заголовки + строки) для удобной фильтрации данных
- 🛡️ Валидация файлов перед загрузкой
- 📈 Автоматическое изменение размера колонок
- 💾 Сохранение состояния обработанных файлов
- 🧹 Очистка старых записей

## Установка

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Убедитесь, что файл `sheet-api-key.json` находится в корне проекта

3. Настройте переменные окружения в `.env` (опционально):
```bash
# Google Sheets настройки
GOOGLE_SHEETS_CREDENTIALS_PATH=sheet-api-key.json
GOOGLE_SHEETS_DOCUMENT_ID=1lmN2L9UORwOPycpRZNX_TKl93S8WSh71YmKuyYDrL7g
GOOGLE_SHEETS_SHEET_PREFIX=Report_

# Мониторинг
REPORTS_DIR=reports
GOOGLE_SHEETS_POLLING_INTERVAL=30

# Логирование
GOOGLE_SHEETS_LOG_LEVEL=INFO
GOOGLE_SHEETS_LOG_FILE=logs/google_sheets_bot.log
```

## Использование

### Основные команды

```bash
# Показать конфигурацию
python scripts/google_sheets_csv_uploader.py --config

# Тестировать подключение к Google Sheets
python scripts/google_sheets_csv_uploader.py --test

# Обработать все необработанные файлы
python scripts/google_sheets_csv_uploader.py --process-all

# Обработать конкретный файл
python scripts/google_sheets_csv_uploader.py --process-file data/reports/example.csv

# Показать статистику
python scripts/google_sheets_csv_uploader.py --stats

# Очистить старые записи
python scripts/google_sheets_csv_uploader.py --cleanup

# Запустить непрерывный мониторинг
python scripts/google_sheets_csv_uploader.py --monitor
```

### Непрерывный мониторинг

Для автоматической загрузки новых CSV файлов запустите мониторинг:

```bash
python scripts/google_sheets_csv_uploader.py --monitor
```

Скрипт будет:
- Проверять папку `reports` каждые 30 секунд (настраивается)
- Автоматически загружать новые CSV файлы в Google Sheets
- Создавать фильтры на всех данных для удобной работы с данными
- Создавать новые листы с именами на основе файлов
- Логировать все операции

## Конфигурация

### Google Sheets настройки

- `GOOGLE_SHEETS_CREDENTIALS_PATH` - путь к JSON файлу с ключами Service Account
- `GOOGLE_SHEETS_DOCUMENT_ID` - ID Google Sheets документа
- `GOOGLE_SHEETS_SHEET_PREFIX` - префикс для новых листов

### Мониторинг

- `REPORTS_DIR` - папка для мониторинга (по умолчанию `reports`)
- `GOOGLE_SHEETS_POLLING_INTERVAL` - интервал проверки в секундах (по умолчанию 30)

### Обработка файлов

- `GOOGLE_SHEETS_MAX_FILE_SIZE` - максимальный размер файла в байтах (по умолчанию 50MB)
- Поддерживаемые кодировки: UTF-8, Windows-1251, CP1251, ISO-8859-1

## Ограничения Google Sheets

- Максимум 1,000,000 строк на лист
- Максимум 1,000 колонок на лист
- Максимум 100 символов в имени листа
- Имена листов не могут содержать: `[ ] * ? / \ :`

## Логирование

Логи сохраняются в файл `logs/google_sheets_bot.log` и выводятся в консоль.

Уровни логирования:
- `DEBUG` - подробная информация
- `INFO` - общая информация (по умолчанию)
- `WARNING` - предупреждения
- `ERROR` - ошибки

## Состояние

Скрипт сохраняет состояние обработанных файлов в файл `.google_sheets_state.json`. Это позволяет:
- Не обрабатывать файлы повторно
- Отслеживать изменения в существующих файлах
- Восстанавливать состояние после перезапуска

## Обработка ошибок

- Файлы с ошибками не помечаются как обработанные
- Ошибки логируются с подробным описанием
- При ошибке подключения к Google Sheets скрипт завершается
- Файлы, которые не удалось прочитать, пропускаются

## Примеры использования

### Обработка всех файлов в папке

```bash
# Сначала проверим, что есть файлы для обработки
python scripts/google_sheets_csv_uploader.py --stats

# Обработаем все необработанные файлы
python scripts/google_sheets_csv_uploader.py --process-all
```

### Обработка конкретного файла

```bash
python scripts/google_sheets_csv_uploader.py --process-file data/reports/my_report.csv
```

### Запуск в фоновом режиме

```bash
# Запуск в фоне с перенаправлением логов
nohup python scripts/google_sheets_csv_uploader.py --monitor > google_sheets.log 2>&1 &

# Остановка
pkill -f google_sheets_csv_uploader.py
```

## Устранение неполадок

### Ошибка аутентификации

```
ERROR: Failed to authenticate with Google Sheets API
```

**Решение:**
1. Проверьте, что файл `sheet-api-key.json` существует и доступен
2. Убедитесь, что Service Account имеет доступ к Google Sheets документу
3. Проверьте, что Google Sheets API включен в Google Cloud Console

### Ошибка доступа к документу

```
ERROR: Failed to connect to Google Sheets
```

**Решение:**
1. Поделитесь Google Sheets документом с email Service Account'а
2. Убедитесь, что Service Account имеет права "Editor"
3. Проверьте правильность Document ID

### Файл не обрабатывается

**Возможные причины:**
1. Файл уже обработан (проверьте статистику)
2. Файл слишком большой (проверьте размер)
3. Файл поврежден или имеет неподдерживаемую кодировку
4. Ошибка в Google Sheets API

**Решение:**
1. Проверьте логи для подробной информации
2. Попробуйте обработать файл вручную: `--process-file path/to/file.csv`
3. Проверьте статистику: `--stats`

## Интеграция с существующим проектом

Этот загрузчик работает независимо от телеграм бота и может использоваться параллельно с ним. Оба сервиса могут мониторить одну и ту же папку `reports` без конфликтов.
