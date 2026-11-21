# Baixa a libmpv-2.dll (o motor do player de video embutido nas telas do Studio) para a pasta indicada.
# Usado pelo build\montar_app.ps1 (instalador) e pelo build\preparar_dev.ps1 (modo desenvolvedor).
# Vem do build do mpv para Windows do "shinchiro" no GitHub (o mesmo que varios players usam). Ele so guarda os
# ultimos ~30 dias de versoes, entao pega sempre a mais nova ("latest"): a parte da DLL que o Studio usa nao muda.
# Uso: baixar_mpv.ps1 -Destino <pasta>
param([Parameter(Mandatory = $true)][string]$Destino)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$cab = @{ "User-Agent" = "famosozora-studio-build"; "Accept" = "application/vnd.github+json" }
if ($env:GH_TOKEN) { $cab["Authorization"] = "Bearer $env:GH_TOKEN" }  # na maquina do GitHub: sem limite de consultas
$rel = Invoke-RestMethod "https://api.github.com/repos/shinchiro/mpv-winbuild-cmake/releases/latest" -Headers $cab
$asset = $rel.assets | Where-Object { $_.name -match '^mpv-dev-x86_64-\d{8}-git-[0-9a-f]+\.7z$' } | Select-Object -First 1
if (-not $asset) { throw "Nao achei o arquivo mpv-dev-x86_64 na versao $($rel.tag_name) do mpv" }

$tmp = Join-Path $env:TEMP "famosozora_mpv"
if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
$arq = Join-Path $tmp $asset.name
Write-Host ("Baixando {0} ({1:N0} MB)" -f $asset.name, ($asset.size / 1MB))
Invoke-WebRequest $asset.browser_download_url -OutFile $arq -Headers @{ "User-Agent" = "famosozora-studio-build" }

# o arquivo e .7z: usa o 7-Zip do PC (a maquina do GitHub ja tem) ou baixa o 7zr.exe oficial (pequeno, so extrai)
$seteZip = (Get-Command 7z -ErrorAction SilentlyContinue).Source
if (-not $seteZip -and (Test-Path "$env:ProgramFiles\7-Zip\7z.exe")) { $seteZip = "$env:ProgramFiles\7-Zip\7z.exe" }
if (-not $seteZip) {
    $seteZip = Join-Path $tmp "7zr.exe"
    Invoke-WebRequest "https://www.7-zip.org/a/7zr.exe" -OutFile $seteZip
}
& $seteZip e $arq "-o$tmp\x" "libmpv-2.dll" -r -y | Out-Null
if ($LASTEXITCODE -ne 0 -or -not (Test-Path "$tmp\x\libmpv-2.dll")) { throw "Nao consegui tirar a libmpv-2.dll de $($asset.name)" }

New-Item -ItemType Directory -Force -Path $Destino | Out-Null
Copy-Item "$tmp\x\libmpv-2.dll" $Destino -Force
Remove-Item $tmp -Recurse -Force
Write-Host "libmpv-2.dll: mpv $($rel.tag_name)"
