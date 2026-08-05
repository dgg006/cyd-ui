@echo off
title Puente CYD - Laboratorio
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "tools\start_lab_gateway.ps1"
if errorlevel 1 (
  echo.
  echo El puente termino con un error. Revisa el mensaje anterior.
  pause
)
