# Procura versao nova do Studio, sem travar a tela (roda em segundo plano).
#   - App instalado: consulta o "Release" mais novo no GitHub e compara com versao.py.
#     Se houver versao maior, baixa o instalador para a pasta temporaria do app (sem perguntar, desde a 1.9.0)
#     e instala sozinho, sem as telas do instalador: quando voce fecha o Studio, ou na hora ("Atualizar agora",
#     que fecha, instala e abre o Studio de novo). Quem espera o Studio fechar e um PowerShell escondido
#     (comando_de_instalacao): ele so instala quando nenhum programa do Studio (nem janela preta) esta rodando.
#   - Modo desenvolvedor (pasta do GitHub): faz "git fetch" e conta quantos commits novos a main
#     do GitHub tem que esta pasta ainda nao tem (e quantas mudancas locais ainda nao foram enviadas).
# Sem internet, repositorio privado ou qualquer erro: nao mostra nada, so registra no log.
import json
import os
import re
import subprocess
from pathlib import Path

from nucleo.comum import DADOS_APP, PASTA_APP, REPO_URL, abrir_url
from nucleo.registro import registrar

API_RELEASE = REPO_URL.replace("https://github.com/", "https://api.github.com/repos/") + "/releases/latest"
TEMPO_LIMITE = 15  # segundos para o GitHub responder


# ------------------------------------------------------------------ versoes
def numero_versao(texto: str) -> tuple:
    """'v1.10.2' -> (1, 10, 2). Compara certo: 1.10 e maior que 1.9 (o texto sozinho errava isso)."""
    partes = re.findall(r"\d+", str(texto))[:3]
    return tuple(int(p) for p in partes) + (0,) * (3 - len(partes))


def eh_mais_nova(remota: str, local: str) -> bool:
    return numero_versao(remota) > numero_versao(local)


# ------------------------------------------------------------------ app instalado: GitHub Releases
def buscar_release() -> dict | None:
    """Dados do Release mais novo: {"versao", "notas", "url_instalador", "nome_instalador", "pagina"} ou None."""
    try:
        with abrir_url(API_RELEASE, TEMPO_LIMITE, {"Accept": "application/vnd.github+json"}) as resposta:
            dados = json.loads(resposta.read().decode("utf-8"))
    except Exception as e:
        # 404 = repositorio privado (ou sem Release ainda); sem internet tambem cai aqui
        registrar(f"atualizacao: nao consegui consultar o GitHub ({e})")
        return None
    instalador = next((a for a in dados.get("assets", []) if a.get("name", "").lower().endswith(".exe")), None)
    return {
        "versao": str(dados.get("tag_name", "")).lstrip("vV"),
        "notas": dados.get("body") or "",
        "pagina": dados.get("html_url") or REPO_URL + "/releases/latest",
        "url_instalador": instalador.get("browser_download_url") if instalador else None,
        "nome_instalador": instalador.get("name") if instalador else None,
        "tamanho": int(instalador.get("size") or 0) if instalador else 0,
    }


def instalador_ja_baixado(release: dict) -> Path | None:
    """O instalador desta versao, se ja foi baixado inteiro antes (por exemplo, numa abertura anterior)."""
    if not release.get("nome_instalador"):
        return None
    arq = DADOS_APP / "temp" / release["nome_instalador"]
    if arq.exists() and (not release.get("tamanho") or arq.stat().st_size == release["tamanho"]):
        return arq
    return None


def limpar_instaladores_velhos(manter: str | None = None):
    """Apaga da pasta temporaria do app os instaladores que ja nao servem (de versoes ja instaladas)."""
    pasta = DADOS_APP / "temp"
    if not pasta.exists():
        return
    for arq in list(pasta.glob("FamosoZora-Studio-Setup-*.exe")) + list(pasta.glob("*.exe.baixando")):
        if arq.name != manter:
            try:
                arq.unlink()
            except OSError:
                pass  # o Windows ainda esta segurando: fica para a proxima


def baixar_instalador(release: dict, ao_progredir=None) -> Path:
    """Baixa o instalador para %LOCALAPPDATA%\\FamosoZora Studio\\temp. ao_progredir(feito, total) e opcional."""
    pronto = instalador_ja_baixado(release)
    if pronto:
        return pronto
    pasta = DADOS_APP / "temp"
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / release["nome_instalador"]
    parcial = destino.with_name(destino.name + ".baixando")
    with abrir_url(release["url_instalador"], 60) as resposta, open(parcial, "wb") as saida:
        total = int(resposta.headers.get("Content-Length") or 0)
        feito = 0
        while True:
            bloco = resposta.read(1024 * 256)
            if not bloco:
                break
            saida.write(bloco)
            feito += len(bloco)
            if ao_progredir:
                ao_progredir(feito, total)
    if total and parcial.stat().st_size != total:
        parcial.unlink(missing_ok=True)
        raise OSError("O download veio incompleto. Tente de novo.")
    os.replace(parcial, destino)
    limpar_instaladores_velhos(manter=destino.name)
    return destino


def abrir_instalador(arquivo: Path):
    """Abre o instalador baixado com as telas normais (ele mesmo fecha o Studio antes de atualizar)."""
    subprocess.Popen([str(arquivo)], cwd=str(arquivo.parent))


# ------------------------------------------------------------------ instalar sozinho (sem clicar em nada)
ESPERA_MAXIMA_MIN = (
    60  # minutos esperando as janelas pretas do Studio terminarem antes de desistir (tenta de novo depois)
)


def _aspas(texto: str) -> str:
    """Texto entre aspas simples para o PowerShell (aspas simples dentro viram duas)."""
    return "'" + str(texto).replace("'", "''") + "'"


def comando_de_instalacao(instalador: Path, pid: int, reabrir: bool, mostrar_progresso: bool,
                          pasta_app: Path = PASTA_APP) -> list:  # fmt: skip
    """Comando (PowerShell escondido) que espera o Studio fechar e instala a versao nova sem perguntar nada.
    - espera o processo do Studio (pid) acabar e qualquer outro programa do Studio (as janelas pretas usam o
      Python da pasta do app) terminar; se continuar ocupado por ESPERA_MAXIMA_MIN minutos, desiste (o
      instalador fica guardado e e usado na proxima vez que o Studio fechar);
    - mostrar_progresso=True: aparece so a barrinha de progresso do instalador (/SILENT); False: nada aparece;
    - reabrir=True: o instalador abre o Studio de novo no fim (/REABRIR=1, lido pelo build/instalador.iss)."""
    argumentos = ["/SP-", "/SUPPRESSMSGBOXES", "/NORESTART", "/SILENT" if mostrar_progresso else "/VERYSILENT"]
    if reabrir:
        argumentos.append("/REABRIR=1")
    do_studio = _aspas(str(Path(pasta_app) / "python") + "\\*")
    script = (
        "$ErrorActionPreference = 'SilentlyContinue'; "
        f"Wait-Process -Id {int(pid)} -Timeout 120; "
        f"$ate = (Get-Date).AddMinutes({ESPERA_MAXIMA_MIN}); "
        f"function Ocupado {{ [bool](Get-Process | Where-Object {{ $_.Path -like {do_studio} }}) }}; "
        "while ((Ocupado) -and ((Get-Date) -lt $ate)) { Start-Sleep -Seconds 3 }; "
        f"if (-not (Ocupado)) {{ Start-Process -FilePath {_aspas(instalador)} -ArgumentList {_aspas(' '.join(argumentos))} }}"
    )
    return ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden",
            "-Command", script]  # fmt: skip


def instalar_ao_fechar(instalador: Path, reabrir: bool = False, mostrar_progresso: bool = False) -> bool:
    """Deixa engatilhada a instalacao: assim que o Studio fechar, a versao nova e instalada sozinha.
    Devolve False se nao deu para engatilhar (fora do Windows, por exemplo)."""
    if os.name != "nt" or not Path(instalador).exists():
        return False
    try:
        subprocess.Popen(
            comando_de_instalacao(Path(instalador), os.getpid(), reabrir, mostrar_progresso),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0),
            close_fds=True,
        )
    except OSError as e:
        registrar("atualizacao: nao consegui engatilhar a instalacao", e)
        return False
    registrar(f"atualizacao: {Path(instalador).name} vai ser instalado quando o Studio fechar (reabrir={reabrir})")
    return True


# ------------------------------------------------------------------ modo desenvolvedor: git
def _git(git: str, pasta: Path, *args, tempo=60) -> subprocess.CompletedProcess:
    ambiente = dict(os.environ, GIT_TERMINAL_PROMPT="0")  # nunca pede senha numa janela escondida
    return subprocess.run(
        [git, "-C", str(pasta), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=tempo, env=ambiente,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )  # fmt: skip


def situacao_git(git: str, pasta: Path = PASTA_APP, buscar: bool = True) -> dict | None:
    """{"atras": commits novos no GitHub, "a_frente": commits daqui ainda nao enviados,
    "mudancas": arquivos mudados sem commit, "ramo": nome do ramo}. None se nao der para saber."""
    if not git or not (pasta / ".git").exists():
        return None
    try:
        if buscar:
            r = _git(git, pasta, "fetch", "--quiet", "origin", tempo=20)
            if r.returncode != 0:
                registrar(f"atualizacao: git fetch falhou ({r.stderr.strip()[:200]})")
                return None
        ramo = _git(git, pasta, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        contagem = _git(git, pasta, "rev-list", "--left-right", "--count", "HEAD...origin/main")
        a_frente, atras = (int(x) for x in contagem.stdout.split()) if contagem.returncode == 0 else (0, 0)
        mudancas = [linha for linha in _git(git, pasta, "status", "--porcelain").stdout.splitlines() if linha.strip()]
        return {"atras": atras, "a_frente": a_frente, "mudancas": len(mudancas), "ramo": ramo}
    except Exception as e:
        registrar("atualizacao: erro ao conferir o git", e)
        return None
