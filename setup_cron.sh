#!/bin/bash
# Скрипт для настройки cron-задачи синхронизации трекера

# Получаем абсолютный путь к директории проекта
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYNC_COMMAND="python -m radiator.commands.sync_tracker"
LOG_FILE="$PROJECT_DIR/logs/tracker_sync.log"

# Создаем директорию для логов
mkdir -p "$PROJECT_DIR/logs"

# Проверяем, что мы в правильной директории проекта
if [ ! -f "$PROJECT_DIR/radiator/commands/sync_tracker.py" ]; then
    echo "Ошибка: Модуль синхронизации не найден: $PROJECT_DIR/radiator/commands/sync_tracker.py"
    exit 1
fi

# Создаем cron-задачу (каждый час)
CRON_JOB="0 * * * * cd $PROJECT_DIR && $SYNC_COMMAND --filter 'updated: today()-7d .. today()' --limit 1000 >> $LOG_FILE 2>&1"

echo "Настройка cron-задачи для синхронизации трекера..."
echo "Задача будет выполняться каждый час"
echo "Режим синхронизации: recent (задачи за последние 7 дней)"
echo ""

# Проверяем, есть ли уже такая задача
if crontab -l 2>/dev/null | grep -q "radiator.commands.sync_tracker"; then
    echo "Cron-задача уже существует. Удаляю старую..."
    crontab -l 2>/dev/null | grep -v "radiator.commands.sync_tracker" | crontab -
fi

# Добавляем новую задачу
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "Cron-задача успешно добавлена!"
echo "Задача будет выполняться каждый час"
echo "Логи будут сохраняться в: $LOG_FILE"
echo ""
echo "Для просмотра текущих cron-задач выполните: crontab -l"
echo "Для редактирования cron-задач выполните: crontab -e"
echo ""
echo "Для тестирования синхронизации выполните:"
echo "  $SYNC_COMMAND --filter 'updated: today()-1d .. today()' --limit 10 --debug"
echo "  $SYNC_COMMAND --filter 'status: In Progress' --limit 10"
echo "  $SYNC_COMMAND --filter 'key:CPO-*' --limit 50"
