@echo off
setlocal
set "PYW=%~dp0shorts\ferramentas\.venv\Scripts\pythonw.exe"
if not exist "%PYW%" goto instalar
start "" "%PYW%" "%~dp0shorts\ferramentas\painel.py"
exit /b 0

:instalar
echo As ferramentas ainda nao foram instaladas. Vou abrir o instalador...
call "%~dp0shorts\0 - Instalar (so na primeira vez).bat"
