@echo off
title Marcar camera e gameplay - FamosoZora
set "PY=%~dp0ferramentas\.venv\Scripts\python.exe"
set PYTHONIOENCODING=utf-8
if not exist "%PY%" goto sem_instalar
"%PY%" "%~dp0ferramentas\marcar_camera.py" %*
exit /b 0
:sem_instalar
echo Rode primeiro o arquivo "0 - Instalar - so na primeira vez".
pause
exit /b 1
