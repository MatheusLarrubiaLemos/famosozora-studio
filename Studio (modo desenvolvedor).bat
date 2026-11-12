@echo off
setlocal
rem Roda o FamosoZora Studio direto desta pasta do GitHub (para testar mudancas antes do instalador).
rem Para usar no dia a dia, instale o app pelo .exe da pagina Releases do GitHub.
title FamosoZora Studio - modo desenvolvedor
cd /d "%~dp0"
set "PYW=%~dp0.venv\Scripts\pythonw.exe"
if /i "%~1"=="instalar" goto instalar
if exist "%PYW%" goto abrir

:instalar
echo Preparando o modo desenvolvedor (precisa de internet, so na primeira vez)...
where ffmpeg >nul 2>&1
if errorlevel 1 winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements
py -3.12 --version >nul 2>&1
if errorlevel 1 (
  winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements
  echo Python instalado. Feche esta janela e abra este arquivo de novo.
  pause
  exit /b 0
)
if not exist ".venv\Scripts\python.exe" py -3.12 -m venv .venv
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install --upgrade -r app\requirements.txt
if errorlevel 1 (
  echo [ERRO] A instalacao falhou. Tire um print e mande pro Claude.
  pause
  exit /b 1
)
where nvidia-smi >nul 2>&1
if not errorlevel 1 ".venv\Scripts\python.exe" -m pip install nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"

:abrir
cd /d "%~dp0app"
start "" "%PYW%" "%~dp0app\main.py"
exit /b 0
