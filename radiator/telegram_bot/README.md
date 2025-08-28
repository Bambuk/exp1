# Telegram Bot для отчетов

Telegram бот для автоматической отправки новых файлов из папки `reports`.

## Возможности

- 🔍 Автоматический мониторинг папки `reports`
- 📁 Отправка новых CSV, PNG, JPG и других файлов
- 📊 Уведомления о новых отчетах
- 💾 Сохранение состояния мониторинга
- 🧹 Автоматическая очистка старых записей

## Установка

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Создайте Telegram бота через [@BotFather](https://t.me/BotFather)

3. Получите ваш User ID (можно использовать [@userinfobot](https://t.me/userinfobot))

4. Настройте переменные окружения в `.env`:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_USER_ID=your_user_id_here
```

## Использование

### Запуск мониторинга
```bash
python -m radiator.telegram_bot.main
```

### Тестирование подключения
```bash
python -m radiator.telegram_bot.main --test
```

### Просмотр конфигурации
```bash
python -m radiator.telegram_bot.main --config
```

### Сброс состояния мониторинга
```bash
python -m radiator.telegram_bot.main --reset
```

### Очистка старых файлов
```bash
python -m radiator.telegram_bot.main --cleanup
```

## Конфигурация

Основные настройки в `radiator/telegram_bot/config.py`:

- `REPORTS_DIR` - папка для мониторинга (по умолчанию `reports`)
- `MONITORED_EXTENSIONS` - расширения файлов для мониторинга
- `POLLING_INTERVAL` - интервал проверки в секундах
- `MAX_FILE_SIZE` - максимальный размер файла для отправки

## Структура модуля

```
radiator/telegram_bot/
├── __init__.py          # Инициализация модуля
├── config.py            # Конфигурация бота
├── file_monitor.py      # Мониторинг файлов
├── bot.py              # Основной класс бота
├── main.py             # Точка входа
└── README.md           # Документация
```

## Логирование

Бот ведет логи в стандартном формате Python logging. Уровень логирования можно настроить в `bot.py`.

## Автозапуск

Для автоматического запуска бота можно использовать systemd или cron:

### Systemd сервис
Создайте файл `/etc/systemd/system/reports-telegram-bot.service`:
```ini
[Unit]
Description=Reports Telegram Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/radiator
ExecStart=/path/to/venv/bin/python -m radiator.telegram_bot.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Затем:
```bash
sudo systemctl enable reports-telegram-bot
sudo systemctl start reports-telegram-bot
```

### Cron
Добавьте в crontab:
```bash
# Проверка каждые 5 минут
*/5 * * * * cd /path/to/radiator && /path/to/venv/bin/python -m radiator.telegram_bot.main
```
