#!/bin/bash
# Скрипт для настройки cron-задачи синхронизации трекера

# Получаем абсолютный путь к директории проекта
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYNC_SCRIPT="$PROJECT_DIR/sync_tracker.py"
LOG_FILE="$PROJECT_DIR/logs/tracker_sync.log"

# Создаем директорию для логов
mkdir -p "$PROJECT_DIR/logs"

# Проверяем существование скрипта
if [ ! -f "$SYNC_SCRIPT" ]; then
    echo "Ошибка: Скрипт синхронизации не найден: $SYNC_SCRIPT"
    exit 1
fi

# Делаем скрипт исполняемым
chmod +x "$SYNC_SCRIPT"

# Создаем cron-задачу (каждый час)
CRON_JOB="0 * * * * cd $PROJECT_DIR && python $SYNC_SCRIPT --sync-mode recent --days 7 >> $LOG_FILE 2>&1"

echo "Настройка cron-задачи для синхронизации трекера..."
echo "Задача будет выполняться каждый час"
echo "Режим синхронизации: recent (задачи за последние 7 дней)"
echo ""

# Проверяем, есть ли уже такая задача
if crontab -l 2>/dev/null | grep -q "$SYNC_SCRIPT"; then
    echo "Cron-задача уже существует. Удаляю старую..."
    crontab -l 2>/dev/null | grep -v "$SYNC_SCRIPT" | crontab -
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
echo "  python $SYNC_SCRIPT --sync-mode recent --days 1 --debug"
echo "  python $SYNC_SCRIPT --sync-mode active --limit 10"
echo "  python $SYNC_SCRIPT --sync-mode filter --status 'In Progress'"
