#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Update status history for tasks with recent status changes.

.DESCRIPTION
    This script runs the UpdateStatusHistoryCommand to update status history
    for tasks that changed status in recent days from a specific queue.

.PARAMETER Queue
    Queue name to filter tasks (default: CPO)

.PARAMETER Days
    Number of days to look back for status changes (default: 14)

.PARAMETER Limit
    Maximum number of tasks to process (default: 1000)

.PARAMETER Verbose
    Enable verbose logging

.EXAMPLE
    .\update_status_history.ps1
    # Update status history for CPO queue, last 14 days

.EXAMPLE
    .\update_status_history.ps1 -Queue "DEV" -Days 7 -Limit 100
    # Update status history for DEV queue, last 7 days, max 100 tasks

.EXAMPLE
    .\update_status_history.ps1 -Queue "QA" -Days 30 -Verbose
    # Update status history for QA queue, last 30 days, with verbose logging
#>

param(
    [string]$Queue = "CPO",
    [int]$Days = 14,
    [int]$Limit = 1000,
    [switch]$Verbose
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Function to check if Python is available
function Test-Python {
    try {
        $pythonVersion = python --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
            return $true
        }
    }
    catch {
        Write-Host "❌ Python not found in PATH" -ForegroundColor Red
        return $false
    }
    return $false
}

# Function to check if virtual environment exists
function Test-VirtualEnv {
    if (Test-Path "venv") {
        Write-Host "✅ Virtual environment found" -ForegroundColor Green
        return $true
    }
    else {
        Write-Host "⚠️  Virtual environment not found, using system Python" -ForegroundColor Yellow
        return $false
    }
}

# Function to activate virtual environment
function Activate-VirtualEnv {
    if (Test-Path "venv\Scripts\Activate.ps1") {
        Write-Host "🔧 Activating virtual environment..." -ForegroundColor Blue
        & "venv\Scripts\Activate.ps1"
        return $true
    }
    return $false
}

# Function to check test environment
function Check-TestEnvironment {
    Write-Host "🔍 Checking test environment..." -ForegroundColor Blue
    
    # Check if .env.test exists
    if (Test-Path ".env.test") {
        Write-Host "✅ .env.test file found" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Virtual environment not found, using system Python" -ForegroundColor Yellow
    }
    
    # Check if test database exists
    try {
        $testDbExists = python -c "
import os
os.environ['ENVIRONMENT'] = 'test'
from radiator.core.config import settings
print('Test Database URL:', settings.DATABASE_URL)
"
        Write-Host "✅ Test environment configuration loaded" -ForegroundColor Green
        Write-Host "   $testDbExists" -ForegroundColor Gray
    }
    catch {
        Write-Host "❌ Failed to load test environment configuration" -ForegroundColor Red
        Write-Host "   Error: $_" -ForegroundColor Red
    }
}

# Main execution
Write-Host "🚀 Starting Status History Update Command" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Queue: $Queue" -ForegroundColor White
Write-Host "Days: $Days" -ForegroundColor White
Write-Host "Limit: $Limit" -ForegroundColor White
Write-Host "Verbose: $Verbose" -ForegroundColor White
Write-Host ""

# Check prerequisites
if (-not (Test-Python)) {
    Write-Host "❌ Python is required to run this command" -ForegroundColor Red
    exit 1
}

# Check if command file exists
if (-not (Test-Path "radiator\commands\update_status_history.py")) {
    Write-Host "❌ Command file not found: radiator\commands\update_status_history.py" -ForegroundColor Red
    exit 1
}

# Check virtual environment
$hasVenv = Test-VirtualEnv
if ($hasVenv) {
    Activate-VirtualEnv
}

# Check test environment
Check-TestEnvironment

Write-Host ""
Write-Host "🔧 Running UpdateStatusHistoryCommand..." -ForegroundColor Blue

# Build command arguments
$pythonArgs = @(
    "radiator\commands\update_status_history.py"
    "--queue", $Queue
    "--days", $Days
    "--limit", $Limit
)

if ($Verbose) {
    $pythonArgs += "--verbose"
}

# Run the command
try {
    Write-Host "📋 Command: python $($pythonArgs -join ' ')" -ForegroundColor Gray
    
    $result = & python @pythonArgs
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ Status history update completed successfully!" -ForegroundColor Green
        Write-Host "   Queue: $Queue" -ForegroundColor Gray
        Write-Host "   Period: Last $Days days" -ForegroundColor Gray
        Write-Host "   Limit: $Limit tasks" -ForegroundColor Gray
    } else {
        Write-Host ""
        Write-Host "❌ Status history update failed with exit code: $LASTEXITCODE" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}
catch {
    Write-Host ""
    Write-Host "❌ Failed to run UpdateStatusHistoryCommand" -ForegroundColor Red
    Write-Host "   Error: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "🏁 Command execution completed" -ForegroundColor Cyan
