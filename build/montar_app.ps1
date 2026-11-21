# Monta a pasta do app (Python portatil + bibliotecas + ffmpeg + scripts) em dist\app.
# Roda no GitHub Actions (Windows). Tambem funciona num PC com Python 3.12 instalado.
param([string]$Saida = "dist")
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$raiz = Split-Path -Parent $PSScriptRoot
$dist = Join-Path $raiz $Saida
$app = Join-Path $dist "app"
$ferr = Join-Path $raiz "app"

$versao = (& python (Join-Path $PSScriptRoot "ler_versao.py")).Trim()
Write-Host "== Montando FamosoZora Studio $versao =="

if (Test-Path $app) { Remove-Item $app -Recurse -Force }
New-Item -ItemType Directory -Force -Path $app, "$app\ferramentas", "$app\bin", "$app\musicas", "$app\efeitos" | Out-Null

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
#    Versao TRAVADA na linha 8.1 (so recebe correcoes). A "master" mudava todo dia e passou a exigir
#    driver NVIDIA novo demais. Para trocar de versao, mude a linha abaixo e teste os Shorts antes.
$ffmpegZip = "ffmpeg-n8.1-latest-win64-gpl-8.1.zip"
$zip = Join-Path $env:TEMP "ffmpeg.zip"
Invoke-WebRequest "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/$ffmpegZip" -OutFile $zip
$tmp = Join-Path $env:TEMP "ffmpeg_x"
if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
Expand-Archive $zip $tmp
Get-ChildItem $tmp -Recurse -Include "ffmpeg.exe", "ffprobe.exe" | Copy-Item -Destination "$app\bin"
& "$app\bin\ffmpeg.exe" -hide_banner -version | Select-Object -First 1

# 2b) libmpv-2.dll: o motor do player de video embutido nas telas (desde a 1.9.0)
& (Join-Path $PSScriptRoot "baixar_mpv.ps1") -Destino "$app\bin"

# 3) Scripts, configuracoes padrao, musicas e documentos
Copy-Item (Join-Path $ferr "*.py"), (Join-Path $ferr "requirements.txt") "$app\ferramentas"
foreach ($pasta in "interface", "shorts", "videos_longos", "nucleo", "publicacao", "padrao") {
    Copy-Item (Join-Path $ferr $pasta) "$app\ferramentas\$pasta" -Recurse
}
Get-ChildItem "$app\ferramentas" -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
# musicas por clima e efeitos sonoros por categoria, COM as subpastas (o Git nao guarda pasta vazia: cria todas)
Copy-Item (Join-Path $raiz "musicas\*") "$app\musicas" -Recurse
Copy-Item (Join-Path $raiz "efeitos\*") "$app\efeitos" -Recurse
foreach ($clima in "engracado", "epico", "tenso", "emocionante", "calmo", "caotico", "geral") {
    New-Item -ItemType Directory -Force -Path "$app\musicas\$clima" | Out-Null
}
foreach ($categoria in "risada", "impacto", "falha", "suspense", "vitoria", "transicao") {
    New-Item -ItemType Directory -Force -Path "$app\efeitos\$categoria" | Out-Null
}
if (-not (Test-Path "$app\musicas\geral\idle_zora_01.m4a")) { throw "as musicas nao foram copiadas com as subpastas" }
# so os guias vao no app (os relatorios de docs\relatorios ficam so no GitHub)
Copy-Item (Join-Path $raiz "docs\COMO USAR.md"), (Join-Path $raiz "docs\DIRETRIZES DO CANAL.md"), (Join-Path $raiz "docs\PUBLICAR.md") $app
Copy-Item (Join-Path $raiz "CHANGELOG.md") $app
Copy-Item (Join-Path $PSScriptRoot "icone.ico") $app
Set-Content -Path "$app\ferramentas\APP_INSTALADO" -Value "Instalado pelo instalador do FamosoZora Studio $versao"

# teste: o app abre os modulos sem erro
Push-Location "$app\ferramentas"
& "$app\python\python.exe" -c "import main, versao; from nucleo import comum, transcrever, ativar_gpu; from shorts import gerar_shorts, falantes, biblioteca, audio_short, lote; from videos_longos import pedido_edicao, editar_episodio, outro, edicao_com_claude; from interface import marcar_camera, editor_legendas, player, janela_principal, janela_publicar, janela_excluir, janela_claude, janela_lote, janela_preparar_lote, reportar_bug; from publicacao import fila, horario, pacote, claude_pc, rascunhos; from nucleo import claude_local, tocador, selecao, relato_bug; import tkinterdnd2, send2trash; assert player.disponivel(), 'player: ' + player.motivo_indisponivel(); print('modulos OK', versao.VERSAO, comum.APP_INSTALADO, 'player OK')"
$ok = $LASTEXITCODE
Pop-Location
if ($ok -ne 0) { throw "teste dos modulos falhou" }

"versao=$versao" | Out-File -FilePath (Join-Path $dist "versao.txt") -Encoding ascii
Write-Host "== App montado em $app =="
