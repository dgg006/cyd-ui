$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonLauncher = (Get-Command py).Source
$mosquitto = "C:\Program Files\Mosquitto\mosquitto.exe"

function Test-CommandLine([string]$pattern) {
    return [bool](Get-CimInstance Win32_Process | Where-Object {
        $_.CommandLine -and $_.CommandLine.Contains($pattern)
    })
}

if (-not (Test-CommandLine "mqtt\mosquitto.conf")) {
    Start-Process -FilePath $mosquitto `
        -ArgumentList "-c", "$projectRoot\mqtt\mosquitto.conf" `
        -WorkingDirectory $projectRoot `
        -WindowStyle Hidden
}

if (-not (Test-CommandLine "http.server 8124")) {
    Start-Process -FilePath $pythonLauncher `
        -ArgumentList "-3.13", "-m", "http.server", "8124", "--directory", $projectRoot `
        -WorkingDirectory $projectRoot `
        -WindowStyle Hidden
}

if (-not (Test-CommandLine "tools\ha_bridge.py")) {
    Start-Process -FilePath $pythonLauncher `
        -ArgumentList "-3.13", "tools\ha_bridge.py" `
        -WorkingDirectory $projectRoot `
        -WindowStyle Hidden
}

if (-not (Test-CommandLine "configurator\server.py")) {
    Start-Process -FilePath $pythonLauncher `
        -ArgumentList "-3.13", "configurator\server.py" `
        -WorkingDirectory $projectRoot `
        -WindowStyle Hidden
}

Start-Sleep -Seconds 2
Start-Process "http://127.0.0.1:8125/"
Write-Host "Entorno CYD iniciado."
