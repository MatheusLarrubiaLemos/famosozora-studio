@echo off
rem Abre a interface grafica do Juntar Videos (FamosoZora)
start "" powershell.exe -NoProfile -ExecutionPolicy Bypass -STA -WindowStyle Hidden -File "%~dp0juntar_videos_gui.ps1"
