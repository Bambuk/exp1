# Скрипт для синхронизации задач CPO за последние полгода
# Убедитесь, что у вас настроены переменные окружения для Tracker API

Write-Host "🔄 Начинаем синхронизацию задач CPO за последние полгода..." -ForegroundColor Yellow

# Проверяем наличие переменных окружения
if (-not $env:TRACKER_API_TOKEN -or $env:TRACKER_API_TOKEN -eq "your_tracker_api_token_here") {
    Write-Host "❌ Ошибка: Не настроен TRACKER_API_TOKEN" -ForegroundColor Red
    Write-Host "Создайте файл .env и заполните TRACKER_API_TOKEN и TRACKER_ORG_ID" -ForegroundColor Red
    exit 1
}

if (-not $env:TRACKER_ORG_ID -or $env:TRACKER_ORG_ID -eq "your_organization_id_here") {
    Write-Host "❌ Ошибка: Не настроен TRACKER_ORG_ID" -ForegroundColor Red
    Write-Host "Создайте файл .env и заполните TRACKER_API_TOKEN и TRACKER_ORG_ID" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Переменные окружения настроены" -ForegroundColor Green

# Рассчитываем дату 6 месяцев назад
$sixMonthsAgo = (Get-Date).AddMonths(-6).ToString("yyyy-MM-dd")
Write-Host "📅 Ищем задачи, обновленные с: $sixMonthsAgo" -ForegroundColor Cyan

# Запускаем синхронизацию с фильтрами
Write-Host "🚀 Запускаем синхронизацию..." -ForegroundColor Green

try {
    # Используем режим filter с фильтрами по ключу CPO и дате обновления
    python -m radiator.commands.sync_tracker `
        --sync-mode filter `
        --key "CPO-*" `
        --updated-since $sixMonthsAgo `
        --limit 1000 `

    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Синхронизация завершена успешно!" -ForegroundColor Green
    } else {
        Write-Host "❌ Синхронизация завершилась с ошибкой" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Ошибка при выполнении синхронизации: $_" -ForegroundColor Red
    exit 1
}

Write-Host "🎉 Все задачи CPO за последние полгода загружены в базу данных!" -ForegroundColor Green
