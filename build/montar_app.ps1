# Monta a pasta do app (Python portatil + bibliotecas + ffmpeg + scripts) em dist\app.
# Roda no GitHub Actions (Windows). Tambem funciona num PC com Python 3.12 instalado.
param([string]$Saida = "dist")
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$raiz = Split-Path -Parent $PSScriptRoot
$dist = Join-Path $raiz $Saida
$app = Join-Path $dist "app"
$ferr = Join-Path $raiz "shorts\ferramentas"

$versao = (Select-String -Path (Join-Path $ferr "versao.py") -Pattern 'VERSAO = "(.+)"').Matches[0].Groups[1].Value
Write-Host "== Montando FamosoZora Studio $versao =="

if (Test-Path $app) { Remove-Item $app -Recurse -Force }
New-Item -ItemType Directory -Force -Path $app, "$app\ferramentas", "$app\bin", "$app\musicas" | Out-Null

# 1) Python portatil: copia do Python 3.12 instalado (tem tkinter/tcl junto)
$pyExe = (Get-Command python).Source
$pyDir = Split-Path $pyExe
$pyVer = & $pyExe -c "import sys;print('%d.%d' % sys.version_info[:2])"
if ($pyVer -ne "3.12") { throw "Precisa do Python 3.12 (achei $pyVer)" }
Write-Host "Copiando Python de $pyDir"
Copy-Item $pyDir "$app\python" -Recurse
# garante o pip funcionando na copia (sem apagar nada de dentro dele)
& "$app\python\python.exe" -m ensurepip --upgrade
& "$app\python\python.exe" -m pip install --upgrade --no-warn-script-location pip
if ($LASTEXITCODE -ne 0) { throw "pip nao funcionou na copia do Python" }
& "$app\python\python.exe" -m pip install --no-warn-script-location -r (Join-Path $ferr "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "pip falhou" }
& "$app\python\python.exe" -c "import tkinter, faster_whisper, sherpa_onnx, numpy; print('bibliotecas OK')"
if ($LASTEXITCODE -ne 0) { throw "teste de import falhou" }
Get-ChildItem "$app\python" -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force

# 2) ffmpeg + ffprobe (build GPL do BtbN: tem libass para legenda e NVENC para placa NVIDIA)
$zip = Join-Path $env:TEMP "ffmpeg.zip"
Invoke-WebRequest "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip" -OutFile $zip
$tmp = Join-Path $env:TEMP "ffmpeg_x"
if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
Expand-Archive $zip $tmp
Get-ChildItem $tmp -Recurse -Include "ffmpeg.exe", "ffprobe.exe" | Copy-Item -Destination "$app\bin"
& "$app\bin\ffmpeg.exe" -hide_banner -version | Select-Object -First 1

# 3) Scripts, configuracoes padrao, musicas e documentos
Copy-Item (Join-Path $ferr "*.py") "$app\ferramentas"
foreach ($f in "config.json", "vocabulario.txt", "correcoes.txt", "requirements.txt") { Copy-Item (Join-Path $ferr $f) "$app\ferramentas" }
Copy-Item (Join-Path $raiz "videos\juntar_videos_gui.ps1") "$app\ferramentas"
Copy-Item (Join-Path $raiz "shorts\musicas\*") "$app\musicas"
Copy-Item (Join-Path $raiz "shorts\COMO USAR.md") $app
Copy-Item (Join-Path $raiz "CHANGELOG.md") $app
Copy-Item (Join-Path $raiz "DIRETRIZES DO CANAL.md") $app
Copy-Item (Join-Path $PSScriptRoot "icone.ico") $app
Set-Content -Path "$app\ferramentas\APP_INSTALADO" -Value "Instalado pelo instalador do FamosoZora Studio $versao"

# teste: o app abre os modulos sem erro
Push-Location "$app\ferramentas"
& "$app\python\python.exe" -c "import comum, gerar_shorts, transcrever, falantes, marcar_camera; print('modulos OK', comum.VERSAO, comum.APP_INSTALADO)"
$ok = $LASTEXITCODE
Pop-Location
if ($ok -ne 0) { throw "teste dos modulos falhou" }

"versao=$versao" | Out-File -FilePath (Join-Path $dist "versao.txt") -Encoding ascii
Write-Host "== App montado em $app =="
