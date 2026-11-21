# Prepara o modo desenvolvedor (rodado pelo "Studio (modo desenvolvedor).bat", em qualquer PC):
#   1. confere se o Python 3.12 existe (se nao, explica e abre a pagina de download);
#   2. cria a pasta .venv e instala as bibliotecas, so quando o requirements muda;
#   3. baixa o ffmpeg para a pasta bin\ se faltar (a mesma versao do instalador), e a libmpv-2.dll (o player
#      embutido nas telas; sem ela o Studio funciona, so abre os trechos no player do Windows);
#   4. com placa NVIDIA, baixa as bibliotecas da placa; sem placa (notebook), tudo roda no processador.
# Uso: preparar_dev.ps1            -> so faz o que falta (rapido quando ja esta tudo pronto)
#      preparar_dev.ps1 instalar   -> reinstala as bibliotecas mesmo sem mudanca
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$raiz = Split-Path -Parent $PSScriptRoot
$venv = Join-Path $raiz ".venv"
$pyVenv = Join-Path $venv "Scripts\python.exe"
$forcar = $args -contains "instalar"

# Mesmo ffmpeg do instalador (build\montar_app.ps1). Mudou la, mude aqui.
$ffmpegZip = "ffmpeg-n8.1-latest-win64-gpl-8.1.zip"

function Passo([string]$texto) { Write-Host "`n== $texto" -ForegroundColor Yellow }

# ------------------------------------------------------------------ 1. Python 3.12
function Achar-Python312 {
    foreach ($tentativa in @(@("py", "-3.12"), @("python"), @("python3"))) {
        $cmd = Get-Command $tentativa[0] -ErrorAction SilentlyContinue
        if (-not $cmd) { continue }
        $extra = @($tentativa | Select-Object -Skip 1)
        try {
            $saida = & $cmd.Source @extra -c "import sys;print('%d.%d|%s' % (sys.version_info[0], sys.version_info[1], sys.executable))" 2>$null
        } catch { continue }
        if ($LASTEXITCODE -eq 0 -and $saida -like "3.12|*") { return ($saida -split "\|", 2)[1].Trim() }
    }
    return $null
}

if (-not (Test-Path $pyVenv) -or $forcar) {
    Passo "Procurando o Python 3.12"
    $py = Achar-Python312
    if (-not $py) {
        Add-Type -AssemblyName System.Windows.Forms
        $r = [System.Windows.Forms.MessageBox]::Show(
            "O modo desenvolvedor precisa do Python 3.12, e ele nao esta instalado neste PC.`n`n" +
            "1. Clique em OK para abrir a pagina de download.`n" +
            "2. Baixe o 'Windows installer (64-bit)' do Python 3.12.`n" +
            "3. Na primeira tela do instalador, MARQUE 'Add python.exe to PATH' e clique em 'Install Now'.`n" +
            "4. Depois abra o 'Studio (modo desenvolvedor).bat' de novo.",
            "FamosoZora Studio - falta o Python", "OKCancel", "Information")
        if ($r -eq "OK") { Start-Process "https://www.python.org/downloads/release/python-31210/" }
        exit 2
    }
    Write-Host "Python 3.12: $py"
    if (-not (Test-Path $pyVenv)) {
        Passo "Criando a pasta .venv (so na primeira vez)"
        & $py -m venv $venv
        if ($LASTEXITCODE -ne 0) { throw "Nao consegui criar a pasta .venv" }
    }
}

# ------------------------------------------------------------------ 2. bibliotecas (so quando o requirements muda)
$requisitos = @((Join-Path $raiz "app\requirements.txt"), (Join-Path $raiz "requirements-dev.txt"))
$assinatura = ($requisitos | ForEach-Object { (Get-FileHash $_ -Algorithm SHA256).Hash }) -join "-"
$arqAssinatura = Join-Path $venv "requisitos_instalados.txt"
$instalado = if (Test-Path $arqAssinatura) { (Get-Content $arqAssinatura -Raw).Trim() } else { "" }
if ($forcar -or $instalado -ne $assinatura) {
    Passo "Instalando as bibliotecas (o requirements mudou ou e a primeira vez)"
    & $pyVenv -m pip install --upgrade --quiet pip
    & $pyVenv -m pip install --no-warn-script-location -r (Join-Path $raiz "requirements-dev.txt")
    if ($LASTEXITCODE -ne 0) { throw "A instalacao das bibliotecas falhou (sem internet?)" }
    Set-Content -Path $arqAssinatura -Value $assinatura -Encoding ascii
} else {
    Write-Host "Bibliotecas: ja estao em dia."
}

# ------------------------------------------------------------------ 3. ffmpeg
$bin = Join-Path $raiz "bin"
if (-not (Test-Path (Join-Path $bin "ffmpeg.exe")) -or -not (Test-Path (Join-Path $bin "ffprobe.exe"))) {
    Passo "Baixando o ffmpeg (cerca de 190 MB, so na primeira vez)"
    New-Item -ItemType Directory -Force -Path $bin | Out-Null
    $zip = Join-Path $env:TEMP "famosozora_ffmpeg.zip"
    $tmp = Join-Path $env:TEMP "famosozora_ffmpeg"
    Invoke-WebRequest "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/$ffmpegZip" -OutFile $zip
    if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
    Expand-Archive $zip $tmp
    Get-ChildItem $tmp -Recurse -Include "ffmpeg.exe", "ffprobe.exe" | Copy-Item -Destination $bin
    Remove-Item $zip, $tmp -Recurse -Force
}
Write-Host ("ffmpeg: " + ((& (Join-Path $bin "ffmpeg.exe") -hide_banner -version | Select-Object -First 1) -replace " Copyright.*", ""))
if (-not (Test-Path (Join-Path $bin "libmpv-2.dll"))) {
    Passo "Baixando o player de video embutido (libmpv, cerca de 35 MB, so na primeira vez)"
    try { & (Join-Path $PSScriptRoot "baixar_mpv.ps1") -Destino $bin }
    catch { Write-Host "[AVISO] Nao consegui baixar o player ($_). O Studio abre os trechos no player do Windows." }
} else {
    Write-Host "Player de video: pronto."
}

# ------------------------------------------------------------------ 4. placa NVIDIA (opcional)
$temNvidia = (Get-Command nvidia-smi -ErrorAction SilentlyContinue) -or (Test-Path "$env:SystemRoot\System32\nvidia-smi.exe")
$marcaGpu = Join-Path $venv "gpu_instalada.txt"
if ($env:FAMOSOZORA_SEM_GPU -eq "1") { $temNvidia = $false }  # para testar como se fosse o notebook
if ($temNvidia) {
    if ($forcar -or -not (Test-Path $marcaGpu)) {
        Passo "Placa NVIDIA encontrada: baixando as bibliotecas dela (cerca de 1 GB, so na primeira vez)"
        & $pyVenv -m pip install --no-warn-script-location nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"
        if ($LASTEXITCODE -eq 0) { Set-Content -Path $marcaGpu -Value "ok" -Encoding ascii }
        else { Write-Host "[AVISO] Nao consegui baixar as bibliotecas da NVIDIA. O Studio usa o processador." }
    } else {
        Write-Host "Placa NVIDIA: pronta."
    }
} else {
    Write-Host "Sem placa NVIDIA neste PC: a transcricao e os videos usam o processador (funciona, so e mais lento)."
}

Write-Host "`nTudo pronto." -ForegroundColor Green
exit 0
