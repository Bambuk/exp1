# PowerShell скрипт для настройки планировщика задач Windows

# Получаем путь к директории проекта
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SyncScript = Join-Path $ProjectDir "sync_tracker.py"
$TaskFile = Join-Path $ProjectDir "tasks.txt"
$LogFile = Join-Path $ProjectDir "logs\tracker_sync.log"

# Создаем директорию для логов
$LogsDir = Split-Path $LogFile -Parent
if (!(Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir -Force
}

# Проверяем существование файлов
if (!(Test-Path $SyncScript)) {
    Write-Error "Ошибка: Скрипт синхронизации не найден: $SyncScript"
    exit 1
}

if (!(Test-Path $TaskFile)) {
    Write-Error "Ошибка: Файл со списком задач не найден: $TaskFile"
    Write-Host "Создайте файл tasks.txt со списком ID задач (по одному на строку)"
    exit 1
}

# Имя задачи в планировщике
$TaskName = "TrackerSyncTask"

Write-Host "Настройка планировщика задач Windows для синхронизации трекера..."
Write-Host "Задача будет выполняться каждый час"
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
$Action = New-ScheduledTaskAction -Execute "python.exe" -Argument "$SyncScript $TaskFile" -WorkingDirectory $ProjectDir

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
    Write-Host "  python $SyncScript $TaskFile --debug"
} catch {
    Write-Error "Ошибка при создании задачи: $_"
    exit 1
}
