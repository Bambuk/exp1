#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Скрипт для управления миграциями базы данных с Alembic

.DESCRIPTION
    Предоставляет удобные команды для работы с миграциями Alembic

.PARAMETER Command
    Команда для выполнения (status, history, create, upgrade, downgrade, reset)

.PARAMETER Message
    Сообщение для новой миграции (используется с командой create)

.EXAMPLE
    .\migrate.ps1 status
    .\migrate.ps1 create "Add new field"
    .\migrate.ps1 upgrade
#>

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("status", "history", "create", "upgrade", "downgrade", "reset")]
    [string]$Command,
    
    [Parameter(Mandatory=$false)]
    [string]$Message
)

function Show-Status {
    Write-Host "📊 Текущий статус миграций:" -ForegroundColor Green
    alembic current
}

function Show-History {
    Write-Host "📚 История миграций:" -ForegroundColor Green
    alembic history
}

function Create-Migration {
    param([string]$MigrationMessage)
    
    if ([string]::IsNullOrEmpty($MigrationMessage)) {
        $MigrationMessage = Read-Host "Введите описание миграции"
    }
    
    Write-Host "🔄 Создание новой миграции: $MigrationMessage" -ForegroundColor Yellow
    alembic revision --autogenerate -m $MigrationMessage
}

function Upgrade-Migrations {
    Write-Host "⬆️ Применение миграций..." -ForegroundColor Yellow
    alembic upgrade head
}

function Downgrade-Migration {
    Write-Host "⬇️ Откат на одну миграцию назад..." -ForegroundColor Yellow
    alembic downgrade -1
}

function Reset-Migrations {
    Write-Host "🔄 Сброс всех миграций..." -ForegroundColor Red
    $confirmation = Read-Host "Вы уверены, что хотите сбросить все миграции? (y/N)"
    if ($confirmation -eq 'y' -or $confirmation -eq 'Y') {
        alembic downgrade base
    } else {
        Write-Host "Операция отменена" -ForegroundColor Yellow
    }
}

function Show-Help {
    Write-Host @"
🔧 Команды для работы с миграциями:

  status     - Показать текущий статус миграций
  history    - Показать историю миграций
  create     - Создать новую миграцию
  upgrade    - Применить все миграции
  downgrade  - Откатить на одну миграцию назад
  reset      - Сбросить все миграции

Примеры использования:
  .\migrate.ps1 status
  .\migrate.ps1 create "Добавить новое поле"
  .\migrate.ps1 upgrade
  .\migrate.ps1 downgrade
"@ -ForegroundColor Cyan
}

# Основная логика
switch ($Command) {
    "status" { Show-Status }
    "history" { Show-History }
    "create" { Create-Migration -MigrationMessage $Message }
    "upgrade" { Upgrade-Migrations }
    "downgrade" { Downgrade-Migration }
    "reset" { Reset-Migrations }
    default { Show-Help }
}
