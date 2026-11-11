@echo off
setlocal
title Instalar / atualizar - FamosoZora Studio
cd /d "%~dp0ferramentas"
echo.
echo ===============================================
echo   Instalando / atualizando o FamosoZora Studio
echo   Pode levar alguns minutos. Precisa de internet.
echo ===============================================
echo.

echo [1/5] Verificando o ffmpeg...
where ffmpeg >nul 2>&1
if errorlevel 1 winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements

echo [2/5] Verificando o Python 3.12...
py -3.12 --version >nul 2>&1
if errorlevel 1 goto instalar_python
goto python_ok

:instalar_python
echo Instalando o Python 3.12...
winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements
echo.
echo Python instalado. FECHE esta janela e rode este arquivo DE NOVO.
pause
exit /b 0

:python_ok
echo [3/5] Criando o ambiente e instalando o Whisper...
if not exist ".venv\Scripts\python.exe" py -3.12 -m venv .venv
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install --upgrade -r requirements.txt
if errorlevel 1 goto erro

echo [4/5] Verificando placa de video NVIDIA...
where nvidia-smi >nul 2>&1
if errorlevel 1 goto sem_nvidia
echo Placa NVIDIA encontrada. Instalando aceleracao por GPU...
".venv\Scripts\python.exe" -m pip install nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"
goto atalho

:sem_nvidia
echo Sem placa NVIDIA: a transcricao vai usar o processador - funciona, so e mais lento.

:atalho
echo [5/5] Criando o atalho "FamosoZora Studio" na Area de Trabalho...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$d=[Environment]::GetFolderPath('Desktop'); $s=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $d 'FamosoZora Studio.lnk')); $s.TargetPath=(Resolve-Path '%~dp0ferramentas\.venv\Scripts\pythonw.exe').Path; $s.Arguments=[char]34+(Resolve-Path '%~dp0ferramentas\painel.py').Path+[char]34; $s.WorkingDirectory=(Resolve-Path '%~dp0ferramentas').Path; $s.Description='FamosoZora Studio'; $s.Save()"

echo.
echo ===============================================
echo   PRONTO! Abra o "FamosoZora Studio" pelo atalho
echo   na Area de Trabalho (ou pelo arquivo na pasta
echo   "canal famosozora").
echo ===============================================
pause
exit /b 0

:erro
echo.
echo [ERRO] A instalacao falhou. Tire um print desta janela e mande pro Claude.
pause
exit /b 1
