#!/usr/bin/env pwsh
# Youth Permission Tracker - API Startup Script (PowerShell)

Write-Host "Starting Youth Permission Tracker API..." -ForegroundColor Cyan
Write-Host ""

$workspaceRoot = "c:\sandbox\youth-permission-tracker"
Set-Location $workspaceRoot

# Check if Python environment exists
$venvPath = Join-Path $workspaceRoot "sandbox\Scripts\Activate.ps1"
if (Test-Path $venvPath) {
    Write-Host "Activating Python environment..." -ForegroundColor Yellow
    & $venvPath
    Write-Host "Python environment activated." -ForegroundColor Green
    Write-Host ""
}

Write-Host "Starting API server on http://localhost:5000" -ForegroundColor Green
Write-Host ""
Write-Host "Once the server starts, open your browser to:" -ForegroundColor Cyan
Write-Host "  http://localhost:5000/website/youth_editor.html" -ForegroundColor White
Write-Host "or" -ForegroundColor Cyan
Write-Host "  file:///c:/sandbox/youth-permission-tracker/website/youth_editor.html" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop the server." -ForegroundColor Yellow
Write-Host ""

python run_local.py
