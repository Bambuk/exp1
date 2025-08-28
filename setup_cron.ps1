# PowerShell скрипт для настройки планировщика задач Windows

# Получаем путь к директории проекта
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SyncScript = Join-Path $ProjectDir "scripts\sync\sync_tracker.py"
$LogFile = Join-Path $ProjectDir "logs\tracker_sync.log"

# Создаем директорию для логов
$LogsDir = Split-Path $LogFile -Parent
if (!(Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir -Force
}

# Проверяем существование скрипта
if (!(Test-Path $SyncScript)) {
    Write-Error "Ошибка: Скрипт синхронизации не найден: $SyncScript"
    exit 1
}

# Имя задачи в планировщике
$TaskName = "TrackerSyncTask"

Write-Host "Настройка планировщика задач Windows для синхронизации трекера..."
Write-Host "Задача будет выполняться каждый час"
Write-Host "Режим синхронизации: recent (задачи за последние 7 дней)"
Write-Host ""

# Удаляем существующую задачу, если она есть
try {
    $ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($ExistingTask) {
        Write-Host "Удаляю существующую задачу..."
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }
} catch {
    # Задача не существует, это нормально
}

# Создаем действие (запуск Python скрипта)
$Action = New-ScheduledTaskAction -Execute "python.exe" -Argument "$SyncScript --sync-mode recent --days 7" -WorkingDirectory $ProjectDir

# Создаем триггер (каждый час)
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 365)

# Создаем настройки
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Создаем задачу
try {
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "Синхронизация данных из Yandex Tracker"
    Write-Host "Задача планировщика успешно создана!"
    Write-Host "Задача будет выполняться каждый час"
    Write-Host "Логи будут сохраняться в: $LogFile"
    Write-Host ""
    Write-Host "Для просмотра задачи выполните: Get-ScheduledTask -TaskName '$TaskName'"
    Write-Host "Для удаления задачи выполните: Unregister-ScheduledTask -TaskName '$TaskName'"
    Write-Host ""
    Write-Host "Для тестирования синхронизации выполните:"
    Write-Host "  python $SyncScript --sync-mode recent --days 1 --debug"
    Write-Host "  python $SyncScript --sync-mode active --limit 10"
    Write-Host "  python $SyncScript --sync-mode filter --status 'In Progress'"
} catch {
    Write-Error "Ошибка при создании задачи: $_"
    exit 1
}
