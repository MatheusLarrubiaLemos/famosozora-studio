# O Claude no seu computador: acha o Claude Code (o programa "claude" do terminal) e o app do Claude
# (Cowork), e manda o pedido de publicacao. Dois jeitos (escolha em Configuracoes > Claude):
#   - "claude_code": abre uma janela com o Claude Code + Claude in Chrome (claude --chrome) ja com o pedido.
#     Ele agenda sozinho; voce so acompanha e aprova o que ele pedir.
#   - "cowork": copia o pedido e abre o app do Claude. Voce cola (Ctrl+V) no Cowork e envia.
#   - "auto" (padrao): usa o Claude Code se ele estiver instalado; senao, o Cowork.
# Todos os "publicadores" tem a mesma cara: preparar (monta os pacotes), enviar e consultar_status.
import os
import shutil
import subprocess
import webbrowser
from pathlib import Path

from nucleo.comum import PASTA_PUBLICAR, ler_ajustes
from publicacao import fila
from publicacao.pacote import gravar_pedido, juntar_para_enviar, montar_pacote, pasta_enviar, texto_pedido

MODOS = {"auto": "Automático (Claude Code se tiver; senão Cowork)",
         "claude_code": "Claude Code + Claude in Chrome (sozinho)",
         "cowork": "Cowork / app do Claude (copiar e colar)"}  # fmt: skip
SEM_JANELA = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def achar_claude_code():
    """Caminho do Claude Code (programa 'claude' do terminal), ou None.
    Cuidado: o app do Claude (Cowork) tambem se chama claude.exe, mas fica em AnthropicClaude e nao serve aqui."""
    candidatos = [shutil.which("claude")]
    casa = Path.home()
    appdata = Path(os.environ.get("APPDATA", casa / "AppData" / "Roaming"))
    candidatos += [casa / ".local" / "bin" / "claude.exe", casa / ".local" / "bin" / "claude",
                   appdata / "npm" / "claude.cmd", casa / ".claude" / "local" / "claude.exe"]  # fmt: skip
    for c in candidatos:
        if c and Path(c).is_file() and "anthropicclaude" not in str(c).lower():
            return str(c)
    return None


def versao_claude_code(caminho: str | None = None) -> str | None:
    """'2.1.0 (Claude Code)' ou None se nao respondeu."""
    caminho = caminho or achar_claude_code()
    if not caminho:
        return None
    try:
        r = subprocess.run([caminho, "--version"], capture_output=True, text=True, timeout=30,
                           encoding="utf-8", errors="replace", creationflags=SEM_JANELA)  # fmt: skip
    except (OSError, subprocess.TimeoutExpired):
        return None
    saida = (r.stdout or "").strip().splitlines()
    return saida[0] if r.returncode == 0 and saida else None


def achar_app_claude():
    """O app do Claude para computador (onde fica o Cowork), ou None."""
    local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    for c in (local / "AnthropicClaude" / "claude.exe", local / "Programs" / "Claude" / "Claude.exe",
              local / "Programs" / "claude-desktop" / "Claude.exe"):  # fmt: skip
        if c.is_file():
            return str(c)
    return None


def modo_escolhido() -> str:
    m = ler_ajustes().get("publicar_modo", "auto")
    return m if m in MODOS else "auto"


def modo_efetivo() -> str:
    """O jeito que vai ser usado de verdade agora ('claude_code' ou 'cowork')."""
    m = modo_escolhido()
    if m == "auto":
        return "claude_code" if achar_claude_code() else "cowork"
    return m


# ------------------------------------------------------------------ os 3 passos de todo publicador
def preparar(itens: list, progresso=None) -> list:
    """Monta o pacote de cada item (video, thumb, dados) e grava na fila. progresso(k, total, fracao)."""
    for k, item in enumerate(itens):
        montar_pacote(item, (lambda f, k=k: progresso(k, len(itens), f)) if progresso else None)
        fila.atualizar(item["id"], pacote=item["pacote"], video_pacote=item.get("video_pacote", ""))
    return itens


def enviar(itens: list, copiar=None) -> dict:
    """Manda o pedido para o Claude. copiar(texto) poe o texto na area de transferencia (a tela passa essa funcao).
    Devolve {"modo": ..., "pedido": arquivo, "aviso": texto para mostrar}. Da RuntimeError se nao der."""
    from datetime import datetime

    juntar_para_enviar(itens)  # todos os videos numa pasta so: voce arrasta de uma vez para o YouTube Studio
    pedido = gravar_pedido(itens)
    modo = modo_efetivo()
    if modo == "claude_code":
        claude = achar_claude_code()
        if not claude:
            raise RuntimeError("Não achei o Claude Code neste computador. Instale o Claude Code, ou escolha "
                               "'Cowork' em Configurações > Claude.")  # fmt: skip
        abrir_claude_code(claude, pedido)  # o proprio Claude abre a pasta dos videos na hora de pedir (pedido, passo A)
        aviso = ("Abri o Claude Code. Quando ele abrir a pasta \"ENVIAR ESTES VIDEOS\": selecione todos (Ctrl+A), "
                 "arraste para o YouTube Studio (Criar > Enviar vídeos) e responda 'pronto' na janela do Claude. "
                 "Depois ele confere e agenda um por um sozinho.")  # fmt: skip
    else:
        if copiar:
            copiar(texto_pedido(itens))
        abrir_app_claude()
        abrir_pasta_dos_videos(itens)  # o Cowork nao abre pastas no Windows: o Studio ja deixa aberta
        aviso = ("Copiei o pedido e abri a pasta \"ENVIAR ESTES VIDEOS\". No app do Claude, abra o Cowork, cole "
                 "(Ctrl+V) e envie. "
                 f"O pedido também está em:\n{pedido}")  # fmt: skip
    enviado = datetime.now().isoformat(timespec="seconds")
    for item in itens:
        fila.atualizar(item["id"], status="enviando", enviado_em=enviado, erro="", modo=modo)
    return {"modo": modo, "pedido": pedido, "aviso": aviso}


def consultar_status(item: dict) -> str:
    """A situacao atual do item (depois de conferir o resultado.json do pacote)."""
    fila.conferir()
    atual = fila.pegar(item["id"])
    return atual["status"] if atual else "erro"


# ------------------------------------------------------------------ abrir o Claude
def comando_claude_code(claude: str, pedido: Path) -> list:
    """O comando que abre o Claude Code com o pedido (a janela fica aberta para voce acompanhar)."""
    instrucao = (f'Leia o arquivo "{pedido.name}" nesta pasta e faça exatamente o que ele pede. '
                 "Use o Chrome (Claude in Chrome) para mexer no YouTube Studio.")  # fmt: skip
    # o pedido vem LOGO DEPOIS do claude: as versoes novas do Claude Code leem TUDO o que vem depois de
    # "--add-dir" como mais pastas, e o pedido virava um "nome de pasta" (a janela abria sem fazer nada).
    # O --add-dir fica no FIM, so com a pasta publicar\: ela ja vem liberada (o Claude precisa ler o video para
    # enviar ao YouTube e gravar o resultado.json), sem parar para pedir permissao.
    # "Bash(explorer.exe:*)" liberado: o Claude abre a pasta dos videos NA HORA de pedir para arrastar (antes o
    # Studio abria no comeco e ela ficava escondida atras das outras janelas). Fica ANTES do --add-dir (veja acima).
    base = [claude, instrucao, "--chrome", "--allowedTools", "Bash(explorer.exe:*)", "--add-dir", str(PASTA_PUBLICAR)]
    if os.name == "nt":
        return ["cmd", "/c", "start", "Claude - publicando no YouTube", "/D", str(pedido.parent), "cmd", "/k", *base]
    return base


def abrir_claude_code(claude: str, pedido: Path):
    comando = comando_claude_code(claude, pedido)
    subprocess.Popen(comando, cwd=str(pedido.parent))


def abrir_pasta_dos_videos(itens: list):
    """Abre no Explorer a pasta com todos os videos do envio (voce seleciona todos e arrasta para o YouTube)."""
    if hasattr(os, "startfile"):
        try:
            os.startfile(str(pasta_enviar()))
        except OSError:
            pass


def abrir_app_claude():
    """Abre o app do Claude (Cowork). Sem o app, abre o Claude no navegador."""
    app = achar_app_claude()
    if app and hasattr(os, "startfile"):
        try:
            os.startfile(app)
            return
        except OSError:
            pass
    webbrowser.open("https://claude.ai/new")
