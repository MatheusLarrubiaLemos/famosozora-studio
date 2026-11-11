@echo off
title Transcrever video - FamosoZora
set "PY=%~dp0ferramentas\.venv\Scripts\python.exe"
set PYTHONIOENCODING=utf-8
set HF_HUB_DISABLE_SYMLINKS_WARNING=1
if not exist "%PY%" goto sem_instalar
"%PY%" "%~dp0ferramentas\transcrever.py" %*
echo.
pause
exit /b 0
:sem_instalar
echo Rode primeiro o arquivo "0 - Instalar - so na primeira vez".
pause
exit /b 1
