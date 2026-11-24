# ==========================================================
#  Juntar Vídeos — FamosoZora
#  Interface gráfica para juntar vídeos na ordem escolhida.
#  Os arquivos originais NUNCA são alterados: só são lidos.
#  Abra pelo FamosoZora Studio: "Juntar vídeos (partes)".
# ==========================================================

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

$Inv        = [Globalization.CultureInfo]::InvariantCulture
$Extensoes  = @('.mp4', '.mov', '.mkv', '.m4v', '.avi', '.ts', '.flv')
# a pasta de videos vem do Studio (FAMOSOZORA_VIDEOS); senao, a pasta deste script
$PastaBase  = if ($env:FAMOSOZORA_VIDEOS -and (Test-Path $env:FAMOSOZORA_VIDEOS)) { $env:FAMOSOZORA_VIDEOS } elseif ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
$Titulo     = 'Juntar Vídeos — FamosoZora'

$TmpProg  = Join-Path $env:TEMP 'juntar_famosozora_progresso.txt'
$TmpLog   = Join-Path $env:TEMP 'juntar_famosozora_erros.txt'
$TmpLista = Join-Path $env:TEMP 'juntar_famosozora_lista.txt'

$script:proc          = $null
$script:saida         = $null
$script:totalSeg      = 0.0
$script:cancelado     = $false
$script:nomeAutomatico = $true
$script:mudandoNome   = $false
$script:statusBase    = ''

# ---------------------------------------------------------- utilidades

function Msg([string]$texto, [string]$botoes = 'OK', [string]$icone = 'Information') {
    return [System.Windows.Forms.MessageBox]::Show($texto, $Titulo, $botoes, $icone)
}

function Formatar-Tempo([double]$seg) {
    if ($seg -lt 0) { $seg = 0 }
    $t = [TimeSpan]::FromSeconds([math]::Round($seg))
    return ('{0:00}:{1:00}:{2:00}' -f [math]::Floor($t.TotalHours), $t.Minutes, $t.Seconds)
}

function Formatar-Tamanho([long]$bytes) {
    if ($bytes -ge 1GB) { return ('{0:N2} GB' -f ($bytes / 1GB)) }
    return ('{0:N0} MB' -f ($bytes / 1MB))
}

function Fps-Numero([string]$r) {
    $p = $r -split '/'
    if ($p.Count -eq 2) {
        $a = 0.0; $b = 0.0
        if ([double]::TryParse($p[0], [Globalization.NumberStyles]::Float, $Inv, [ref]$a) -and
            [double]::TryParse($p[1], [Globalization.NumberStyles]::Float, $Inv, [ref]$b) -and $b -ne 0) {
            return [math]::Round($a / $b, 3)
        }
    }
    return 0
}

function Atualizar-Path {
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
                [Environment]::GetEnvironmentVariable('Path', 'User')
}

function Caminho-FFmpeg  { $c = Get-Command ffmpeg  -ErrorAction SilentlyContinue; if ($c) { $c.Source } }
function Caminho-FFprobe { $c = Get-Command ffprobe -ErrorAction SilentlyContinue; if ($c) { $c.Source } }

function Garantir-FFmpeg {
    if ((Caminho-FFmpeg) -and (Caminho-FFprobe)) { return $true }
    $r = Msg ("O ffmpeg (programa que junta os vídeos) não está instalado.`n`n" +
              "Quer instalar agora? Leva 1 a 2 minutos e precisa de internet.") 'YesNo' 'Question'
    if ($r -ne 'Yes') { return $false }
    try {
        Start-Process -FilePath 'winget' -ArgumentList 'install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements' -Wait
    } catch {
        Msg "Não consegui rodar o instalador (winget).`n`n$($_.Exception.Message)" 'OK' 'Error' | Out-Null
        return $false
    }
    Atualizar-Path
    if ((Caminho-FFmpeg) -and (Caminho-FFprobe)) {
        Msg 'ffmpeg instalado com sucesso!' | Out-Null
        return $true
    }
    Msg "A instalação terminou, mas o ffmpeg ainda não foi encontrado.`nFeche o programa e abra de novo." 'OK' 'Warning' | Out-Null
    return $false
}

function Ler-Info([string]$arq) {
    $probe = Caminho-FFprobe
    $v = @{}; $a = @{}
    foreach ($l in (& $probe -v error -select_streams v:0 -show_entries 'stream=codec_name,width,height,r_frame_rate,avg_frame_rate,pix_fmt' -of 'default=nw=1' "$arq")) {
        $k, $val = "$l" -split '=', 2; $v[$k] = $val
    }
    foreach ($l in (& $probe -v error -select_streams a:0 -show_entries 'stream=codec_name,sample_rate,channels' -of 'default=nw=1' "$arq")) {
        $k, $val = "$l" -split '=', 2; $a[$k] = $val
    }
    $dTxt = (& $probe -v error -show_entries 'format=duration' -of 'default=nw=1:nk=1' "$arq") -join ''
    $dur = 0.0
    [void][double]::TryParse($dTxt.Trim(), [Globalization.NumberStyles]::Float, $Inv, [ref]$dur)

    $fps = Fps-Numero $v['avg_frame_rate']
    if ($fps -le 0 -or $fps -gt 240) { $fps = Fps-Numero $v['r_frame_rate'] }

    return [pscustomobject]@{
        Codec      = $v['codec_name']
        W          = $v['width']
        H          = $v['height']
        FpsTexto   = $v['r_frame_rate']
        Fps        = $fps
        Pix        = $v['pix_fmt']
        TemAudio   = [bool]$a['codec_name']
        ACodec     = $a['codec_name']
        ARate      = $a['sample_rate']
        ACh        = $a['channels']
        Duracao    = $dur
        Assinatura = "$($v['codec_name'])|$($v['width'])x$($v['height'])|$($v['r_frame_rate'])|$($v['pix_fmt'])||$($a['codec_name'])|$($a['sample_rate'])|$($a['channels'])"
    }
}

function Descrever([object]$info) {
    $aud = if ($info.TemAudio) { "$($info.ACodec) $($info.ARate)Hz $($info.ACh)ch" } else { 'sem áudio' }
    return "$($info.W)x$($info.H), $($info.Fps) fps, $($info.Codec) / $aud"
}

# ---------------------------------------------------------- janela

$form = New-Object System.Windows.Forms.Form
$form.Text          = $Titulo
$form.ClientSize    = New-Object System.Drawing.Size(860, 560)
$form.MinimumSize   = New-Object System.Drawing.Size(720, 480)
$form.StartPosition = 'CenterScreen'
$form.Font          = New-Object System.Drawing.Font('Segoe UI', 10)
$form.AllowDrop     = $true

$lblDica = New-Object System.Windows.Forms.Label
$lblDica.Text     = 'Arraste os vídeos para a lista (ou clique em Adicionar). Depois arraste os itens, ou use Subir/Descer, para acertar a ordem.'
$lblDica.Location = New-Object System.Drawing.Point(12, 10)
$lblDica.Size     = New-Object System.Drawing.Size(700, 40)
$lblDica.Anchor   = 'Top, Left, Right'
$form.Controls.Add($lblDica)

$lista = New-Object System.Windows.Forms.ListView
$lista.View          = 'Details'
$lista.FullRowSelect = $true
$lista.GridLines     = $true
$lista.MultiSelect   = $false
$lista.HideSelection = $false
$lista.AllowDrop     = $true
$lista.Location      = New-Object System.Drawing.Point(12, 52)
$lista.Size          = New-Object System.Drawing.Size(700, 330)
$lista.Anchor        = 'Top, Bottom, Left, Right'
[void]$lista.Columns.Add('Ordem', 60)
$colArq = $lista.Columns.Add('Arquivo', 420)
[void]$lista.Columns.Add('Duração', 100)
[void]$lista.Columns.Add('Tamanho', 100)
$form.Controls.Add($lista)

function Novo-Botao([string]$texto, [int]$y, [int]$alt = 34) {
    $b = New-Object System.Windows.Forms.Button
    $b.Text     = $texto
    $b.Location = New-Object System.Drawing.Point(724, $y)
    $b.Size     = New-Object System.Drawing.Size(124, $alt)
    $b.Anchor   = 'Top, Right'
    $form.Controls.Add($b)
    return $b
}
$btnAdd    = Novo-Botao 'Adicionar…'        52
$btnSubir  = Novo-Botao '▲  Subir'          100
$btnDescer = Novo-Botao '▼  Descer'         140
$btnRem    = Novo-Botao 'Remover'           188
$btnAZ     = Novo-Botao 'Ordenar A→Z'       228
$btnLimpar = Novo-Botao 'Limpar lista'      276

$lblNome = New-Object System.Windows.Forms.Label
$lblNome.Text     = 'Nome do vídeo final:'
$lblNome.Location = New-Object System.Drawing.Point(12, 398)
$lblNome.AutoSize = $true
$lblNome.Anchor   = 'Bottom, Left'
$form.Controls.Add($lblNome)

$txtNome = New-Object System.Windows.Forms.TextBox
$txtNome.Location = New-Object System.Drawing.Point(160, 395)
$txtNome.Size     = New-Object System.Drawing.Size(440, 26)
$txtNome.Anchor   = 'Bottom, Left, Right'
$txtNome.Text     = 'video_juntado'
$form.Controls.Add($txtNome)

$lblExt = New-Object System.Windows.Forms.Label
$lblExt.Text     = '.mp4'
$lblExt.Location = New-Object System.Drawing.Point(604, 398)
$lblExt.AutoSize = $true
$lblExt.Anchor   = 'Bottom, Right'
$form.Controls.Add($lblExt)

$lblInfo = New-Object System.Windows.Forms.Label
$lblInfo.Location  = New-Object System.Drawing.Point(12, 430)
$lblInfo.Size      = New-Object System.Drawing.Size(700, 44)
$lblInfo.Anchor    = 'Bottom, Left, Right'
$lblInfo.ForeColor = [System.Drawing.Color]::DimGray
$form.Controls.Add($lblInfo)

$barra = New-Object System.Windows.Forms.ProgressBar
$barra.Location = New-Object System.Drawing.Point(12, 482)
$barra.Size     = New-Object System.Drawing.Size(700, 24)
$barra.Anchor   = 'Bottom, Left, Right'
$barra.Minimum  = 0
$barra.Maximum  = 1000
$form.Controls.Add($barra)

$lblStatus = New-Object System.Windows.Forms.Label
$lblStatus.Text     = 'Pronto para começar.'
$lblStatus.Location = New-Object System.Drawing.Point(12, 514)
$lblStatus.Size     = New-Object System.Drawing.Size(700, 36)
$lblStatus.Anchor   = 'Bottom, Left, Right'
$form.Controls.Add($lblStatus)

$btnJuntar = New-Object System.Windows.Forms.Button
$btnJuntar.Text      = 'JUNTAR'
$btnJuntar.Font      = New-Object System.Drawing.Font('Segoe UI', 12, [System.Drawing.FontStyle]::Bold)
$btnJuntar.Location  = New-Object System.Drawing.Point(724, 430)
$btnJuntar.Size      = New-Object System.Drawing.Size(124, 60)
$btnJuntar.Anchor    = 'Bottom, Right'
$btnJuntar.BackColor = [System.Drawing.Color]::FromArgb(46, 160, 67)
$btnJuntar.ForeColor = [System.Drawing.Color]::White
$btnJuntar.FlatStyle = 'Flat'
$form.Controls.Add($btnJuntar)

$btnCancelar = New-Object System.Windows.Forms.Button
$btnCancelar.Text     = 'Cancelar'
$btnCancelar.Location = New-Object System.Drawing.Point(724, 500)
$btnCancelar.Size     = New-Object System.Drawing.Size(124, 34)
$btnCancelar.Anchor   = 'Bottom, Right'
$btnCancelar.Enabled  = $false
$form.Controls.Add($btnCancelar)

$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 500

# ---------------------------------------------------------- lista

function Itens { return @($lista.Items | ForEach-Object { $_ }) }

function Renumerar {
    $i = 1; $total = 0.0
    foreach ($it in (Itens)) {
        $it.Text = "$i"
        $total += $it.Tag.Info.Duracao
        $i++
    }
    $n = $lista.Items.Count
    if ($n -eq 0) {
        $lblInfo.Text = 'Nenhum vídeo na lista ainda.'
    } else {
        $pasta = Split-Path -Parent $lista.Items[0].Tag.Caminho
        $lblInfo.Text = "$n vídeo(s)  •  duração total: $(Formatar-Tempo $total)`nSerá salvo em: $pasta"
    }
    if ($script:nomeAutomatico -and $n -gt 0) {
        $base = [IO.Path]::GetFileNameWithoutExtension($lista.Items[0].Tag.Caminho)
        $script:mudandoNome = $true
        $txtNome.Text = "$base - completo"
        $script:mudandoNome = $false
    }
}

function Adicionar-Arquivos([string[]]$caminhos) {
    if (-not (Garantir-FFmpeg)) { return }
    $arquivos = New-Object System.Collections.Generic.List[string]
    foreach ($c in $caminhos) {
        if (Test-Path -LiteralPath $c -PathType Container) {
            Get-ChildItem -LiteralPath $c -File | Where-Object { $Extensoes -contains $_.Extension.ToLower() } |
                Sort-Object Name | ForEach-Object { $arquivos.Add($_.FullName) }
        } elseif ($Extensoes -contains ([IO.Path]::GetExtension($c).ToLower())) {
            $arquivos.Add($c)
        }
    }
    if ($arquivos.Count -eq 0) {
        Msg 'Nenhum vídeo reconhecido (mp4, mov, mkv, m4v, avi, ts, flv).' 'OK' 'Warning' | Out-Null
        return
    }
    $form.Cursor = 'WaitCursor'
    $lblStatus.Text = 'Lendo informações dos vídeos…'
    $form.Refresh()
    foreach ($arq in $arquivos) {
        $fi = Get-Item -LiteralPath $arq
        if (@(Itens | Where-Object { $_.Tag.Caminho -eq $fi.FullName }).Count -gt 0) { continue }
        $info = Ler-Info $fi.FullName
        $it = New-Object System.Windows.Forms.ListViewItem('')
        [void]$it.SubItems.Add($fi.Name)
        [void]$it.SubItems.Add((Formatar-Tempo $info.Duracao))
        [void]$it.SubItems.Add((Formatar-Tamanho $fi.Length))
        $it.ToolTipText = $fi.FullName + "`n" + (Descrever $info)
        $it.Tag = [pscustomobject]@{ Caminho = $fi.FullName; Info = $info }
        [void]$lista.Items.Add($it)
    }
    $form.Cursor = 'Default'
    $lblStatus.Text = 'Pronto para começar.'
    Renumerar
}

function Mover([int]$delta) {
    if ($lista.SelectedIndices.Count -ne 1) { return }
    $i = $lista.SelectedIndices[0]; $j = $i + $delta
    if ($j -lt 0 -or $j -ge $lista.Items.Count) { return }
    $it = $lista.Items[$i]
    $lista.Items.RemoveAt($i)
    [void]$lista.Items.Insert($j, $it)
    $it.Selected = $true; $it.Focused = $true; $it.EnsureVisible()
    [void]$lista.Focus()
    Renumerar
}

$lista.ShowItemToolTips = $true
$lista.Add_Resize({ $colArq.Width = [math]::Max(150, $lista.ClientSize.Width - 60 - 100 - 100 - 4) })

$btnAdd.Add_Click({
    $dlg = New-Object System.Windows.Forms.OpenFileDialog
    $dlg.Title       = 'Escolha os vídeos'
    $dlg.Multiselect = $true
    $dlg.Filter      = 'Vídeos|*.mp4;*.mov;*.mkv;*.m4v;*.avi;*.ts;*.flv|Todos os arquivos|*.*'
    $dlg.InitialDirectory = $PastaBase
    if ($dlg.ShowDialog($form) -eq 'OK') {
        Adicionar-Arquivos ($dlg.FileNames | Sort-Object)
    }
})
$btnSubir.Add_Click({ Mover -1 })
$btnDescer.Add_Click({ Mover 1 })
$btnRem.Add_Click({
    if ($lista.SelectedIndices.Count -eq 1) {
        $i = $lista.SelectedIndices[0]
        $lista.Items.RemoveAt($i)
        if ($lista.Items.Count -gt 0) { $lista.Items[[math]::Min($i, $lista.Items.Count - 1)].Selected = $true }
        Renumerar
    }
})
$btnAZ.Add_Click({
    $ord = Itens | Sort-Object { $_.SubItems[1].Text }
    $lista.Items.Clear()
    foreach ($it in $ord) { [void]$lista.Items.Add($it) }
    Renumerar
})
$btnLimpar.Add_Click({ $lista.Items.Clear(); Renumerar })

$lista.Add_KeyDown({
    param($s, $e)
    if ($e.Control -and $e.KeyCode -eq 'Up')   { Mover -1; $e.Handled = $true }
    if ($e.Control -and $e.KeyCode -eq 'Down') { Mover 1;  $e.Handled = $true }
    if ($e.KeyCode -eq 'Delete') { $btnRem.PerformClick() }
})

$txtNome.Add_TextChanged({ if (-not $script:mudandoNome) { $script:nomeAutomatico = $false } })

# --- arrastar e soltar (arquivos de fora + reordenar dentro da lista)
$lista.Add_ItemDrag({
    param($s, $e)
    [void]$lista.DoDragDrop($e.Item, [System.Windows.Forms.DragDropEffects]::Move)
})
$aoArrastar = {
    param($s, $e)
    if ($e.Data.GetDataPresent([System.Windows.Forms.DataFormats]::FileDrop)) {
        $e.Effect = [System.Windows.Forms.DragDropEffects]::Copy
    } elseif ($e.Data.GetDataPresent([System.Windows.Forms.ListViewItem])) {
        $e.Effect = [System.Windows.Forms.DragDropEffects]::Move
        $pt = $lista.PointToClient((New-Object System.Drawing.Point($e.X, $e.Y)))
        $alvo = $lista.GetItemAt($pt.X, $pt.Y)
        if ($alvo) { $alvo.EnsureVisible() }
    } else {
        $e.Effect = [System.Windows.Forms.DragDropEffects]::None
    }
}
$lista.Add_DragEnter($aoArrastar)
$lista.Add_DragOver($aoArrastar)
$form.Add_DragEnter($aoArrastar)
$form.Add_DragOver($aoArrastar)
$lista.Add_DragDrop({
    param($s, $e)
    if ($e.Data.GetDataPresent([System.Windows.Forms.DataFormats]::FileDrop)) {
        $arqs = [string[]]$e.Data.GetData([System.Windows.Forms.DataFormats]::FileDrop)
        Adicionar-Arquivos ($arqs | Sort-Object)
        return
    }
    $it = $e.Data.GetData([System.Windows.Forms.ListViewItem])
    if (-not $it) { return }
    $pt = $lista.PointToClient((New-Object System.Drawing.Point($e.X, $e.Y)))
    $alvo = $lista.GetItemAt($pt.X, $pt.Y)
    $destino = if ($alvo) { $alvo.Index } else { $lista.Items.Count - 1 }
    if ($destino -eq $it.Index) { return }
    $lista.Items.Remove($it)
    [void]$lista.Items.Insert($destino, $it)
    $it.Selected = $true; $it.Focused = $true
    Renumerar
})
$form.Add_DragDrop({
    param($s, $e)
    if ($e.Data.GetDataPresent([System.Windows.Forms.DataFormats]::FileDrop)) {
        Adicionar-Arquivos (([string[]]$e.Data.GetData([System.Windows.Forms.DataFormats]::FileDrop)) | Sort-Object)
    }
})

# ---------------------------------------------------------- juntar

function Travar-Tela([bool]$rodando) {
    foreach ($c in @($lista, $btnAdd, $btnSubir, $btnDescer, $btnRem, $btnAZ, $btnLimpar, $txtNome, $btnJuntar)) {
        $c.Enabled = -not $rodando
    }
    $btnCancelar.Enabled = $rodando
    $form.AllowDrop = -not $rodando
}

function Limpar-Temporarios {
    foreach ($f in @($TmpProg, $TmpLista)) {
        if (Test-Path -LiteralPath $f) { Remove-Item -LiteralPath $f -Force -ErrorAction SilentlyContinue }
    }
}

$btnJuntar.Add_Click({
    $itens = @(Itens | ForEach-Object { $_.Tag })
    if ($itens.Count -lt 2) { Msg 'Coloque pelo menos 2 vídeos na lista.' 'OK' 'Warning' | Out-Null; return }
    if (-not (Garantir-FFmpeg)) { return }

    # nome do arquivo final (nunca sobrescreve nada)
    $nome = $txtNome.Text.Trim()
    if ($nome.ToLower().EndsWith('.mp4')) { $nome = $nome.Substring(0, $nome.Length - 4) }
    $nome = $nome -replace '[\\/:*?"<>|]', '_'
    if (-not $nome) { $nome = 'video_juntado' }
    $pasta = Split-Path -Parent $itens[0].Caminho
    $saida = Join-Path $pasta "$nome.mp4"
    $n = 2
    while (Test-Path -LiteralPath $saida) { $saida = Join-Path $pasta "${nome}_$n.mp4"; $n++ }

    $total = 0.0; foreach ($x in $itens) { $total += $x.Info.Duracao }
    $iguais = @($itens | Where-Object { $_.Info.Assinatura -ne $itens[0].Info.Assinatura }).Count -eq 0

    # espaço em disco
    try {
        $soma = 0L; foreach ($x in $itens) { $soma += (Get-Item -LiteralPath $x.Caminho).Length }
        $drive = New-Object System.IO.DriveInfo([IO.Path]::GetPathRoot($saida))
        if ($drive.AvailableFreeSpace -lt ($soma * 1.05)) {
            $r = Msg ("Pode faltar espaço no disco $($drive.Name).`n`nLivre: $(Formatar-Tamanho $drive.AvailableFreeSpace)`n" +
                      "Necessário (aprox.): $(Formatar-Tamanho $soma)`n`nTentar mesmo assim?") 'YesNo' 'Warning'
            if ($r -ne 'Yes') { return }
        }
    } catch { }

    $resumo = ($itens | ForEach-Object -Begin { $i = 1 } -Process { "  $i. $([IO.Path]::GetFileName($_.Caminho))"; $i++ }) -join "`n"

    if ($iguais) {
        $r = Msg ("Juntar nesta ordem?`n`n$resumo`n`nResultado: $([IO.Path]::GetFileName($saida))`n" +
                  "Duração total: $(Formatar-Tempo $total)`n`nModo rápido: sem perder qualidade.") 'YesNo' 'Question'
        if ($r -ne 'Yes') { return }
    } else {
        $det = ($itens | ForEach-Object -Begin { $i = 1 } -Process { "  $i. $([IO.Path]::GetFileName($_.Caminho))`n      $(Descrever $_.Info)"; $i++ }) -join "`n"
        $r = Msg ("Os vídeos foram gravados com configurações diferentes:`n`n$det`n`n" +
                  "Para juntar, vai ser preciso RECODIFICAR (usando o formato do vídeo 1).`n" +
                  "Em vídeos longos isso pode levar de 30 minutos a algumas horas.`n`nContinuar?") 'YesNo' 'Warning'
        if ($r -ne 'Yes') { return }
    }

    Limpar-Temporarios
    if (Test-Path -LiteralPath $TmpLog) { Remove-Item -LiteralPath $TmpLog -Force -ErrorAction SilentlyContinue }

    $comum = "-hide_banner -nostdin -n -loglevel error -nostats -progress `"$TmpProg`""
    if ($iguais) {
        $linhas = $itens | ForEach-Object { "file '" + ($_.Caminho -replace "'", "'\''") + "'" }
        [IO.File]::WriteAllLines($TmpLista, [string[]]$linhas, (New-Object System.Text.UTF8Encoding($false)))
        $argsFF = "$comum -f concat -safe 0 -i `"$TmpLista`" -map 0:v:0 -map 0:a? -c copy `"$saida`""
    } else {
        $ref = $itens[0].Info
        $W = $ref.W; $H = $ref.H
        $fps = if ($ref.Fps -gt 0) { $ref.Fps.ToString($Inv) } else { '30' }
        $entradas = ($itens | ForEach-Object { "-i `"$($_.Caminho)`"" }) -join ' '
        $fc = ''; $cc = ''
        for ($i = 0; $i -lt $itens.Count; $i++) {
            $fc += "[${i}:v]scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=$fps,format=yuv420p[v$i];"
            if ($itens[$i].Info.TemAudio) {
                $fc += "[${i}:a]aresample=48000,aformat=channel_layouts=stereo[a$i];"
            } else {
                $d = $itens[$i].Info.Duracao.ToString($Inv)
                $fc += "anullsrc=r=48000:cl=stereo,atrim=duration=$d[a$i];"
            }
            $cc += "[v$i][a$i]"
        }
        $fc += "${cc}concat=n=$($itens.Count):v=1:a=1[v][a]"
        $argsFF = "$comum $entradas -filter_complex `"$fc`" -map `"[v]`" -map `"[a]`" -c:v libx264 -preset veryfast -crf 18 -c:a aac -b:a 192k -movflags +faststart `"$saida`""
    }

    # roda o ffmpeg escondido; erros vão para um arquivo de log
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName        = $env:ComSpec
    $psi.Arguments       = '/d /s /c ""' + (Caminho-FFmpeg) + '" ' + $argsFF + ' 2>"' + $TmpLog + '""'
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow  = $true
    try {
        $script:proc = [System.Diagnostics.Process]::Start($psi)
    } catch {
        Msg "Não consegui iniciar o ffmpeg.`n`n$($_.Exception.Message)" 'OK' 'Error' | Out-Null
        return
    }
    $script:saida     = $saida
    $script:totalSeg  = $total
    $script:cancelado = $false
    $barra.Value = 0
    $script:statusBase = if ($iguais) { 'Juntando (modo rápido)…' } else { 'Recodificando e juntando… (isso demora)' }
    $lblStatus.Text = $script:statusBase
    Travar-Tela $true
    $timer.Start()
})

function Ler-Progresso {
    if (-not (Test-Path -LiteralPath $TmpProg)) { return $null }
    try {
        $fs = [IO.File]::Open($TmpProg, 'Open', 'Read', 'ReadWrite')
        try {
            $pos = [math]::Max(0, $fs.Length - 4000)
            [void]$fs.Seek($pos, 'Begin')
            $txt = (New-Object IO.StreamReader($fs)).ReadToEnd()
        } finally { $fs.Close() }
        $m = [regex]::Matches($txt, 'out_time_(?:us|ms)=(\d+)')
        if ($m.Count -gt 0) { return [double]$m[$m.Count - 1].Groups[1].Value / 1e6 }
    } catch { }
    return $null
}

$timer.Add_Tick({
    $seg = Ler-Progresso
    if ($seg -ne $null -and $script:totalSeg -gt 0) {
        $pct = [math]::Min(1.0, $seg / $script:totalSeg)
        $barra.Value = [int]($pct * 1000)
        $lblStatus.Text = ('{0}  {1:0}%   ({2} de {3})' -f $script:statusBase, ($pct * 100), (Formatar-Tempo $seg), (Formatar-Tempo $script:totalSeg))
    }
    if ($script:proc -and $script:proc.HasExited) {
        $timer.Stop()
        $codigo = $script:proc.ExitCode
        $script:proc = $null
        Limpar-Temporarios
        Travar-Tela $false
        if ($codigo -eq 0 -and -not $script:cancelado) {
            $barra.Value = 1000
            $lblStatus.Text = "Pronto! Criado: $([IO.Path]::GetFileName($script:saida))"
            # anota o video novo para o "Transcrever" do Studio ja abrir na pasta dele
            if ($env:FAMOSOZORA_ULTIMO_JUNTADO) {
                try {
                    $dirAnot = Split-Path -Parent $env:FAMOSOZORA_ULTIMO_JUNTADO
                    if (-not (Test-Path -LiteralPath $dirAnot)) { [void](New-Item -ItemType Directory -Path $dirAnot) }
                    [IO.File]::WriteAllText($env:FAMOSOZORA_ULTIMO_JUNTADO, $script:saida, (New-Object System.Text.UTF8Encoding($false)))
                } catch { }
            }
            $r = Msg ("Pronto! Vídeo criado:`n$($script:saida)`n`nOs originais não foram tocados.`n`nPróximo passo no Studio: "Transcrever a live" (já abre nesta pasta).`n`nAbrir a pasta?") 'YesNo' 'Information'
            if ($r -eq 'Yes') { Start-Process explorer.exe -ArgumentList "/select,`"$($script:saida)`"" }
        } else {
            # apaga só o arquivo NOVO incompleto (os originais nunca são tocados)
            if ($script:saida -and (Test-Path -LiteralPath $script:saida)) {
                Remove-Item -LiteralPath $script:saida -Force -ErrorAction SilentlyContinue
            }
            $barra.Value = 0
            if ($script:cancelado) {
                $lblStatus.Text = 'Cancelado. Nenhum arquivo foi alterado.'
            } else {
                $erro = ''
                if (Test-Path -LiteralPath $TmpLog) { $erro = (Get-Content -LiteralPath $TmpLog -Tail 12 -ErrorAction SilentlyContinue) -join "`n" }
                $lblStatus.Text = "Deu erro (código $codigo). Os originais não foram alterados."
                Msg ("Algo deu errado (código $codigo). Os originais não foram alterados.`n`n$erro`n`n" +
                     "Tire um print desta mensagem e mande pro Claude.") 'OK' 'Error' | Out-Null
            }
        }
    }
})

function Parar-FFmpeg {
    if ($script:proc -and -not $script:proc.HasExited) {
        $script:cancelado = $true
        Start-Process -FilePath 'taskkill.exe' -ArgumentList "/T /F /PID $($script:proc.Id)" -WindowStyle Hidden -Wait
    }
}

$btnCancelar.Add_Click({
    $r = Msg 'Cancelar a junção? O arquivo incompleto será apagado (os originais ficam intactos).' 'YesNo' 'Question'
    if ($r -eq 'Yes') { $lblStatus.Text = 'Cancelando…'; Parar-FFmpeg }
})

$form.Add_FormClosing({
    param($s, $e)
    if ($script:proc -and -not $script:proc.HasExited) {
        $r = Msg 'Ainda está juntando. Cancelar e fechar?' 'YesNo' 'Warning'
        if ($r -ne 'Yes') { $e.Cancel = $true; return }
        Parar-FFmpeg
        Start-Sleep -Milliseconds 500
        if ($script:saida -and (Test-Path -LiteralPath $script:saida)) {
            Remove-Item -LiteralPath $script:saida -Force -ErrorAction SilentlyContinue
        }
        Limpar-Temporarios
    }
})

$form.Add_Shown({
    Renumerar
    [void](Garantir-FFmpeg)
})

[void]$form.ShowDialog()
