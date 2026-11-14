# Procura versao nova do Studio, sem travar a tela (roda em segundo plano).
#   - App instalado: consulta o "Release" mais novo no GitHub e compara com versao.py.
#     Se houver versao maior, baixa o instalador para a pasta temporaria do app e abre.
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
    }


def baixar_instalador(release: dict, ao_progredir=None) -> Path:
    """Baixa o instalador para %LOCALAPPDATA%\\FamosoZora Studio\\temp. ao_progredir(feito, total) e opcional."""
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
    return destino


def abrir_instalador(arquivo: Path):
    """Abre o instalador baixado (ele mesmo fecha o Studio antes de atualizar)."""
    subprocess.Popen([str(arquivo)], cwd=str(arquivo.parent))


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
