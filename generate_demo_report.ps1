# PowerShell script to generate demo status change report
# Generates CSV report and chart image with demo data

Write-Host "Generating Demo Status Change Report..." -ForegroundColor Green

# Run the demo command
Write-Host "Running demo status change report generation..." -ForegroundColor Cyan
python -m radiator.commands.generate_status_change_report_demo --table demo_status_change_table.png

if ($LASTEXITCODE -eq 0) {
    Write-Host "Demo report generated successfully!" -ForegroundColor Green
    Write-Host "Check current directory for demo CSV and PNG files." -ForegroundColor Green
    
    # Show created files
    Write-Host "`nCreated files:" -ForegroundColor Yellow
    Get-ChildItem demo_* | ForEach-Object {
        Write-Host "  - $($_.Name)" -ForegroundColor White
    }
} else {
    Write-Host "Failed to generate demo report. Check logs for details." -ForegroundColor Red
    exit 1
}
