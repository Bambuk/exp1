# Telegram Bot для отчетов

Telegram бот для автоматической отправки новых файлов из папки `reports`.

## Возможности

- 🔍 Автоматический мониторинг папки `reports`
- 📁 Отправка новых CSV, PNG, JPG и других файлов
- 📊 Уведомления о новых отчетах
- 💾 Сохранение состояния мониторинга
- 🧹 Автоматическая очистка старых записей
- 🤖 **НОВОЕ**: Выполнение команд make прямо из Telegram

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

## Доступные команды

Бот теперь поддерживает следующие команды (отправляйте их как сообщения, начинающиеся с `/`):

### `/help`
Показать доступные команды и примеры использования.

### `/generate_time_to_market_teams`
Сгенерировать отчет Time to Market по командам.

### `/sync_and_report`
Запустить полный процесс CPO: синхронизация трекера + генерация отчета.

### `/sync_tracker [ФИЛЬТР]`
Синхронизировать трекер с пользовательским фильтром. Если фильтр не указан, используется по умолчанию: `Queue: CPO Updated: >=01.01.2025`

**Примеры:**
- `/sync_tracker Queue: CPO Status: In Progress`
- `/sync_tracker key:CPO-*`
- `/sync_tracker` (использует фильтр по умолчанию)

### `/restart_service`
Перезапустить сервис телеграм бота. Команда отправляет уведомление о перезапуске и завершает процесс, что позволяет systemd или supervisor автоматически перезапустить сервис.

**⚠️ Внимание:** Эта команда завершает работу бота. Убедитесь, что у вас настроен автозапуск через systemd или supervisor.

## Выполнение команд

Команды выполняются асинхронно, и бот отправляет:
- Подтверждение при запуске команды
- Статус успеха/ошибки при завершении
- Вывод команды (первые 1000 символов) для успешных команд
- Сообщения об ошибках для неудачных команд

Все команды выполняются в директории проекта с активированным виртуальным окружением.

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
├── command_executor.py  # Выполнение команд make
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
