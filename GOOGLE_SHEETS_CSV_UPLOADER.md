# Google Sheets CSV Uploader

Автоматический загрузчик CSV файлов в Google Sheets. Мониторит папку `reports` и автоматически загружает новые CSV файлы как новые листы в указанный Google Sheets документ.

## 🚀 Быстрый старт

1. **Установите зависимости:**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

2. **Проверьте подключение:**
```bash
python3 scripts/test_google_sheets_connection.py
```

3. **Загрузите тестовый файл:**
```bash
python3 scripts/google_sheets_csv_uploader.py --process-file reports/test_report.csv
```

4. **Запустите мониторинг:**
```bash
python3 scripts/google_sheets_csv_uploader.py --monitor
```

## 📋 Основные команды

```bash
# Показать конфигурацию
python3 scripts/google_sheets_csv_uploader.py --config

# Тестировать подключение
python3 scripts/google_sheets_csv_uploader.py --test

# Обработать все необработанные файлы
python3 scripts/google_sheets_csv_uploader.py --process-all

# Обработать конкретный файл
python3 scripts/google_sheets_csv_uploader.py --process-file reports/example.csv

# Показать статистику
python3 scripts/google_sheets_csv_uploader.py --stats

# Запустить непрерывный мониторинг
python3 scripts/google_sheets_csv_uploader.py --monitor
```

## ⚙️ Конфигурация

Все настройки находятся в `radiator/services/google_sheets_config.py`:

- **Google Sheets Document ID:** `1lmN2L9UORwOPycpRZNX_TKl93S8WSh71YmKuyYDrL7g`
- **Service Account Email:** `cpo-radiator@testrestservice01.iam.gserviceaccount.com`
- **Credentials File:** `sheet-api-key.json`
- **Reports Directory:** `reports/`
- **Polling Interval:** 30 секунд

## 🔧 Возможности

- ✅ Автоматический мониторинг папки `reports`
- ✅ Загрузка CSV файлов как новых листов в Google Sheets
- ✅ Обработка различных кодировок (UTF-8, Windows-1251, CP1251)
- ✅ Автоматическое именование листов на основе имени файла
- ✅ Валидация файлов перед загрузкой
- ✅ Автоматическое изменение размера колонок
- ✅ Обработка NaN значений
- ✅ Сохранение состояния обработанных файлов
- ✅ Подробное логирование

## 📊 Статистика

```bash
python3 scripts/google_sheets_csv_uploader.py --stats
```

Показывает:
- Общее количество файлов
- Количество известных файлов
- Количество обработанных файлов
- Количество необработанных файлов

## 🗂️ Структура файлов

```
radiator/
├── services/
│   ├── google_sheets_service.py      # Основной сервис Google Sheets
│   ├── csv_processor.py              # Обработка CSV файлов
│   ├── csv_file_monitor.py           # Мониторинг файлов
│   └── google_sheets_config.py       # Конфигурация
├── scripts/
│   ├── google_sheets_csv_uploader.py # Основной скрипт
│   └── test_google_sheets_connection.py # Тест подключения
└── reports/                          # Папка с CSV файлами
```

## 📝 Логирование

Логи сохраняются в `logs/google_sheets_bot.log` и выводятся в консоль.

Уровни логирования:
- `DEBUG` - подробная информация
- `INFO` - общая информация (по умолчанию)
- `WARNING` - предупреждения
- `ERROR` - ошибки

## 🔄 Состояние

Скрипт сохраняет состояние в `.google_sheets_state.json`:
- Список известных файлов
- Временные метки файлов
- Список обработанных файлов

## 🚨 Ограничения Google Sheets

- Максимум 1,000,000 строк на лист
- Максимум 1,000 колонок на лист
- Максимум 100 символов в имени листа
- Имена листов не могут содержать: `[ ] * ? / \ :`

## 🛠️ Устранение неполадок

### Ошибка аутентификации
```
ERROR: Failed to authenticate with Google Sheets API
```
**Решение:** Проверьте файл `sheet-api-key.json` и права доступа Service Account'а.

### Ошибка доступа к документу
```
ERROR: Failed to connect to Google Sheets
```
**Решение:** Поделитесь Google Sheets документом с email Service Account'а.

### Файл не обрабатывается
**Возможные причины:**
- Файл уже обработан
- Файл слишком большой
- Файл поврежден
- Ошибка в Google Sheets API

**Решение:** Проверьте логи и попробуйте обработать файл вручную.

## 📈 Примеры использования

### Обработка всех файлов
```bash
python3 scripts/google_sheets_csv_uploader.py --process-all
```

### Обработка конкретного файла
```bash
python3 scripts/google_sheets_csv_uploader.py --process-file reports/my_report.csv
```

### Запуск в фоновом режиме
```bash
nohup python3 scripts/google_sheets_csv_uploader.py --monitor > google_sheets.log 2>&1 &
```

## 🔗 Интеграция

Этот загрузчик работает независимо от телеграм бота и может использоваться параллельно с ним. Оба сервиса могут мониторить одну и ту же папку `reports` без конфликтов.

## 📚 Дополнительная документация

- [Подробное руководство](docs/guides/GOOGLE_SHEETS_CSV_UPLOADER_README.md)
- [API документация](docs/api/)
- [Тестирование](docs/guides/TEST_ENVIRONMENT_README.md)
