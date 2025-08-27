#!/bin/bash
# Скрипт для настройки cron-задачи синхронизации трекера

# Получаем абсолютный путь к директории проекта
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYNC_SCRIPT="$PROJECT_DIR/sync_tracker.py"
TASK_FILE="$PROJECT_DIR/tasks.txt"
LOG_FILE="$PROJECT_DIR/logs/tracker_sync.log"

# Создаем директорию для логов
mkdir -p "$PROJECT_DIR/logs"

# Проверяем существование файлов
if [ ! -f "$SYNC_SCRIPT" ]; then
    echo "Ошибка: Скрипт синхронизации не найден: $SYNC_SCRIPT"
    exit 1
fi

if [ ! -f "$TASK_FILE" ]; then
    echo "Ошибка: Файл со списком задач не найден: $TASK_FILE"
    echo "Создайте файл tasks.txt со списком ID задач (по одному на строку)"
    exit 1
fi

# Делаем скрипт исполняемым
chmod +x "$SYNC_SCRIPT"

# Создаем cron-задачу (каждый час)
CRON_JOB="0 * * * * cd $PROJECT_DIR && python $SYNC_SCRIPT $TASK_FILE >> $LOG_FILE 2>&1"

echo "Настройка cron-задачи для синхронизации трекера..."
echo "Задача будет выполняться каждый час"
echo ""

# Проверяем, есть ли уже такая задача
if crontab -l 2>/dev/null | grep -q "$SYNC_SCRIPT"; then
    echo "Cron-задача уже существует. Удаляю старую..."
    crontab -l 2>/dev/null | grep -v "$SYNC_SCRIPT" | crontab -
fi

# Добавляем новую задачу
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "Cron-задача успешно добавлена!"
echo "Скрипт будет выполняться каждый час"
echo "Логи будут сохраняться в: $LOG_FILE"
echo ""
echo "Для просмотра текущих cron-задач выполните: crontab -l"
echo "Для редактирования cron-задач выполните: crontab -e"
echo ""
echo "Для тестирования синхронизации выполните:"
echo "  python $SYNC_SCRIPT $TASK_FILE --debug"
