$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$secrets = Get-Content -Raw -LiteralPath (Join-Path $projectRoot "secrets.yaml")
$username = [regex]::Match($secrets, '(?m)^mqtt_username:\s*["'']?([^"''\r\n]+)').Groups[1].Value.Trim()
$password = [regex]::Match($secrets, '(?m)^mqtt_password:\s*["'']?([^"''\r\n]+)').Groups[1].Value.Trim()
$broker = "192.168.31.240"
$mosquitto = "C:\Program Files\mosquitto"
$states = @{}
$controlIds = @("living", "kitchen", "garage", "night", "heater", "garden")

function Publish-ControlState([string] $controlId, [bool] $active) {
  $event = @{
    type = "control_changed"
    id = $controlId
    active = $active
    reliability = "valid"
  } | ConvertTo-Json -Compress

  $event | & "$mosquitto\mosquitto_pub.exe" `
    -h $broker -p 1883 -u $username -P $password `
    -t "esphome_ui/cyd-ui/event" -q 1 -l
}

Write-Host "Simulador HA escuchando acciones del panel..."

& "$mosquitto\mosquitto_sub.exe" `
  -h $broker -p 1883 -u $username -P $password `
  -t "esphome_ui/cyd-ui/cmd" -q 1 -F "%p" |
ForEach-Object {
  try {
    $command = $_ | ConvertFrom-Json
    if ($command.type -eq "sync_request") {
      foreach ($controlId in $controlIds) {
        Publish-ControlState $controlId ([bool] $states[$controlId])
      }
      Write-Host "Sincronizacion inicial enviada"
      return
    }
    if ($command.type -ne "action" -or $command.action -ne "toggle") {
      return
    }

    $controlId = [string] $command.id
    $nextState = -not [bool] $states[$controlId]
    $states[$controlId] = $nextState

    Publish-ControlState $controlId $nextState

    Write-Host "$controlId -> active=$nextState"
  } catch {
    Write-Warning $_
  }
}
