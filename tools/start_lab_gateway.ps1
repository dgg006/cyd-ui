$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$esphome = (Get-Command esphome -ErrorAction Stop).Source
$pythonRoot = Split-Path -Parent (Split-Path -Parent $esphome)
$python = Join-Path $pythonRoot "python.exe"

Set-Location $projectRoot
Write-Host "Iniciando puente CYD del laboratorio..." -ForegroundColor Cyan
Write-Host "El encendido/apagado remoto de climatizacion queda bloqueado." -ForegroundColor Yellow
& $python (Join-Path $PSScriptRoot "cyd_lab_gateway.py")
