$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
Write-Host "Starting Ninety Level 10 Test Suite..." -ForegroundColor Cyan

$env:APP_NOW = "2026-11-11T15:00:00Z"

if (Test-Path ".\.venv\Scripts\python.exe") {
  & .\.venv\Scripts\python.exe scripts/test_all.py
} else {
  & python scripts/test_all.py
}
