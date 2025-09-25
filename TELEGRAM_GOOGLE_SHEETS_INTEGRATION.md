# Интеграция Telegram бота с Google Sheets

Система для выборочной загрузки CSV файлов в Google Sheets через Telegram бота с кнопками.

## 🎯 Как это работает

1. **Telegram бот** мониторит папку `reports` и отправляет новые CSV файлы в чат
2. **К каждому CSV файлу** добавляется кнопка "📊 Загрузить в Google Sheets"
3. **Пользователь** нажимает кнопку для файлов, которые нужно загрузить в Google Sheets
4. **Google Sheets загрузчик** обрабатывает только файлы с маркерами загрузки
5. **После загрузки** маркер удаляется, файл остается в папке

## 🚀 Быстрый старт

### 1. Запуск Telegram бота с кнопками

```bash
# Активируйте виртуальное окружение
source venv/bin/activate

# Запустите телеграм бот с поддержкой кнопок
python3 -m radiator.telegram_bot.main
```

### 2. Запуск Google Sheets загрузчика

```bash
# В отдельном терминале
source venv/bin/activate

# Запустите мониторинг файлов с маркерами
python3 scripts/google_sheets_csv_uploader.py --monitor
```

## 📋 Команды

### Telegram бот
```bash
# Тест подключения
python3 -m radiator.telegram_bot.main --test

# Запуск с кнопками
python3 -m radiator.telegram_bot.main

# Показать конфигурацию
python3 -m radiator.telegram_bot.main --config
```

### Google Sheets загрузчик
```bash
# Тест подключения
python3 scripts/google_sheets_csv_uploader.py --test

# Обработать файлы с маркерами
python3 scripts/google_sheets_csv_uploader.py --process-markers

# Показать статистику
python3 scripts/google_sheets_csv_uploader.py --stats

# Запустить мониторинг
python3 scripts/google_sheets_csv_uploader.py --monitor
```

## 🔧 Как использовать

### 1. Получение файлов в Telegram
- Бот автоматически отправляет новые CSV файлы в чат
- К каждому CSV файлу прикреплена кнопка "📊 Загрузить в Google Sheets"

### 2. Выбор файлов для загрузки
- Нажмите кнопку "📊 Загрузить в Google Sheets" для нужных файлов
- Бот создаст маркерный файл (`.upload_me_<filename>`)
- Вы получите подтверждение: "✅ Файл добавлен в очередь загрузки"

### 3. Автоматическая загрузка
- Google Sheets загрузчик мониторит маркерные файлы
- Автоматически загружает файлы в Google Sheets
- Удаляет маркеры после успешной загрузки

## 📁 Структура файлов

```
reports/
├── status_change_report_20250925.csv
├── .upload_me_status_change_report_20250925.csv  # маркер загрузки
├── time_to_market_report.csv
└── .upload_me_time_to_market_report.csv  # маркер загрузки
```

## 🔍 Мониторинг

### Статистика
```bash
python3 scripts/google_sheets_csv_uploader.py --stats
```

Показывает:
- Общее количество файлов
- Количество обработанных файлов
- Количество файлов с маркерами загрузки
- Список файлов, готовых к загрузке

### Логи
- Telegram бот: консоль + `logs/`
- Google Sheets загрузчик: `logs/google_sheets_bot.log`

## ⚙️ Конфигурация

### Telegram бот
- `TELEGRAM_BOT_TOKEN` - токен бота
- `TELEGRAM_USER_ID` - ваш User ID
- `REPORTS_DIR` - папка для мониторинга

### Google Sheets
- `GOOGLE_SHEETS_DOCUMENT_ID` - ID документа
- `GOOGLE_SHEETS_CREDENTIALS_PATH` - путь к JSON ключам
- `GOOGLE_SHEETS_POLLING_INTERVAL` - интервал проверки

## 🛠️ Устранение неполадок

### Кнопки не появляются
- Проверьте, что запущен бот с поддержкой callback queries
- Убедитесь, что файл имеет расширение `.csv`

### Файлы не загружаются
- Проверьте наличие маркерных файлов: `ls reports/.upload_me_*`
- Проверьте логи Google Sheets загрузчика
- Убедитесь, что Google Sheets API работает

### Маркеры не удаляются
- Проверьте права доступа к папке `reports`
- Проверьте логи на ошибки

## 🧪 Тестирование

```bash
# Тест интеграции
python3 scripts/test_telegram_sheets_integration.py

# Тест Google Sheets подключения
python3 scripts/test_google_sheets_connection.py
```

## 📊 Примеры использования

### Создание маркера вручную
```bash
echo "Upload request for my_file.csv" > reports/.upload_me_my_file.csv
```

### Обработка конкретного файла
```bash
python3 scripts/google_sheets_csv_uploader.py --process-file reports/my_file.csv
```

### Обработка всех файлов с маркерами
```bash
python3 scripts/google_sheets_csv_uploader.py --process-markers
```

## 🔄 Workflow

1. **Новый CSV файл** появляется в папке `reports`
2. **Telegram бот** отправляет файл с кнопкой в чат
3. **Пользователь** нажимает кнопку для нужных файлов
4. **Создается маркерный файл** `.upload_me_<filename>`
5. **Google Sheets загрузчик** находит файлы с маркерами
6. **Загружает файлы** в Google Sheets как новые листы
7. **Удаляет маркеры** после успешной загрузки
8. **Файлы остаются** в папке `reports`

## 🎉 Преимущества

- ✅ **Выборочная загрузка** - только нужные файлы попадают в Google Sheets
- ✅ **Простое управление** - одна кнопка в Telegram
- ✅ **Надежность** - файловые маркеры не теряются при перезапуске
- ✅ **Прозрачность** - видно, какие файлы готовы к загрузке
- ✅ **Безопасность** - файлы не удаляются автоматически
