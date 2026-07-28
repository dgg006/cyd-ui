$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$secrets = Get-Content -Raw -LiteralPath (Join-Path $projectRoot "secrets.yaml")
$mqttUsername = [regex]::Match($secrets, '(?m)^mqtt_username:\s*["'']?([^"''\r\n]+)').Groups[1].Value.Trim()
$mqttPassword = [regex]::Match($secrets, '(?m)^mqtt_password:\s*["'']?([^"''\r\n]+)').Groups[1].Value.Trim()
$mqttBroker = "192.168.31.240"
$mosquitto = "C:\Program Files\mosquitto"

$accessFile = "C:\Users\ServiCell Taller\Desktop\Nabu Casa.txt"
$accessLines = Get-Content -LiteralPath $accessFile
$haBaseUrl = ($accessLines | Where-Object { $_ -match '^https://' } | Select-Object -First 1).TrimEnd('/')
$tokenLine = $accessLines | Where-Object { $_ -match '(?i)token' } | Select-Object -First 1
$haToken = ($tokenLine -replace '^[^:]*:\s*', '').Trim()
$haHeaders = @{ Authorization = "Bearer $haToken" }

$controlMap = @{
  living = "switch.sonoff_1001327309_2"
}

function Publish-ControlState([string] $controlId, [string] $entityId) {
  try {
    $state = Invoke-RestMethod -Uri "$haBaseUrl/api/states/$entityId" -Headers $haHeaders -Method Get -TimeoutSec 20
    $event = @{
      type = "control_changed"
      id = $controlId
      active = ($state.state -eq "on")
      reliability = if ($state.state -in @("unavailable", "unknown")) { "unavailable" } else { "valid" }
    } | ConvertTo-Json -Compress
  } catch {
    $event = @{
      type = "control_changed"
      id = $controlId
      active = $false
      reliability = "unavailable"
    } | ConvertTo-Json -Compress
  }

  $event | & "$mosquitto\mosquitto_pub.exe" `
    -h $mqttBroker -p 1883 -u $mqttUsername -P $mqttPassword `
    -t "esphome_ui/cyd-ui/event" -q 1 -l
}

Write-Host "Puente Home Assistant activo para Llave Cuarto Chico Canal2"

& "$mosquitto\mosquitto_sub.exe" `
  -h $mqttBroker -p 1883 -u $mqttUsername -P $mqttPassword `
  -t "esphome_ui/cyd-ui/cmd" -q 1 -F "%p" |
ForEach-Object {
  try {
    $command = $_ | ConvertFrom-Json

    if ($command.type -eq "sync_request") {
      foreach ($controlId in $controlMap.Keys) {
        Publish-ControlState $controlId $controlMap[$controlId]
      }
      Write-Host "Estado inicial sincronizado"
      return
    }

    if ($command.type -ne "action" -or $command.action -ne "toggle") {
      return
    }

    $controlId = [string] $command.id
    if (!$controlMap.ContainsKey($controlId)) {
      Write-Host "Control sin asignar ignorado: $controlId"
      return
    }

    $entityId = $controlMap[$controlId]
    $body = @{ entity_id = $entityId } | ConvertTo-Json -Compress
    Invoke-RestMethod -Uri "$haBaseUrl/api/services/switch/toggle" -Headers $haHeaders `
      -Method Post -ContentType "application/json" -Body $body -TimeoutSec 20 | Out-Null
    Start-Sleep -Milliseconds 400
    Publish-ControlState $controlId $entityId
    Write-Host "$controlId -> $entityId alternado y confirmado"
  } catch {
    Write-Warning $_
  }
}
