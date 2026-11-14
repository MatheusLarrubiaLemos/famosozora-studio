@echo off
setlocal
rem Roda o FamosoZora Studio direto desta pasta do GitHub, em qualquer PC (de mesa ou notebook).
rem Na primeira vez ele prepara tudo sozinho: Python (.venv), bibliotecas, ffmpeg e placa NVIDIA (se tiver).
rem Nas proximas, so confere o que mudou e abre. Para o dia a dia, instale o app pelo .exe da pagina Releases.
rem   "Studio (modo desenvolvedor).bat" instalar   -> reinstala as bibliotecas
rem   "Studio (modo desenvolvedor).bat" preparar   -> so prepara, sem abrir o Studio
title FamosoZora Studio - modo desenvolvedor
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build\preparar_dev.ps1" %*
if errorlevel 2 exit /b 2
if errorlevel 1 (
  echo.
  echo [ERRO] A preparacao falhou. Tire um print desta janela e mande pro Claude.
  pause
  exit /b 1
)
if /i "%~1"=="preparar" exit /b 0
cd /d "%~dp0app"
start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0app\main.py"
exit /b 0
