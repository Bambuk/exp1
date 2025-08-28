# PowerShell script to generate status change report
# Generates CSV report and chart image for task status changes by authors over last 2 weeks

Write-Host "Generating Status Change Report..." -ForegroundColor Green

# Activate virtual environment if it exists
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & "venv\Scripts\Activate.ps1"
}

# Set environment variables for test database if not already set
if (-not $env:DATABASE_URL_SYNC) {
    Write-Host "Setting test database environment..." -ForegroundColor Yellow
    $env:DATABASE_URL_SYNC = "postgresql://test:test@localhost:5432/radiator_test"
}

# Run the command
Write-Host "Running status change report generation..." -ForegroundColor Cyan
python -m radiator.commands.generate_status_change_report --table status_change_table.png

if ($LASTEXITCODE -eq 0) {
    Write-Host "Report generated successfully!" -ForegroundColor Green
    Write-Host "Check current directory for CSV and PNG files." -ForegroundColor Green
} else {
    Write-Host "Failed to generate report. Check logs for details." -ForegroundColor Red
    exit 1
}
