# Ajudantes das telas: cores, abrir arquivos e pastas, e rodar as outras partes do programa.
import os
import shutil
import subprocess
import sys
from pathlib import Path

from interface import tema
from nucleo.comum import (
    DADOS_APP,
    FERRAMENTAS,
    PASTA_APP,
)
from nucleo.video import tem_placa_nvidia


def primeiro_existente(*caminhos):
    for c in caminhos:
        if Path(c).exists():
            return Path(c)
    return Path(caminhos[0])


# app instalado: tudo na raiz do programa; pasta do GitHub: guias em docs\
ARQ_GUIA = primeiro_existente(PASTA_APP / "COMO USAR.md", PASTA_APP / "docs" / "COMO USAR.md")


ARQ_NOVIDADES = PASTA_APP / "CHANGELOG.md"


ARQ_PUBLICAR = primeiro_existente(PASTA_APP / "PUBLICAR.md", PASTA_APP / "docs" / "PUBLICAR.md")


ARQ_DIRETRIZES = primeiro_existente(PASTA_APP / "DIRETRIZES DO CANAL.md", PASTA_APP / "docs" / "DIRETRIZES DO CANAL.md")


BAT_DEV = PASTA_APP / "Studio (modo desenvolvedor).bat"


def tem_nvidia() -> bool:
    return tem_placa_nvidia()


def gpu_baixada() -> bool:
    return any((DADOS_APP / "gpu" / "nvidia").glob("*/bin/*.dll"))


PY = Path(sys.executable)


PY_CONSOLE = PY.with_name("python.exe") if PY.name.lower() == "pythonw.exe" else PY


PY_JANELA = PY.with_name("pythonw.exe") if PY.with_name("pythonw.exe").exists() else PY


COR_FUNDO = tema.FUNDO  # as cores ficam todas em interface/tema.py


COR_TEXTO = tema.TEXTO


COR_DESTAQUE = tema.LARANJA


def achar_git():
    """git do PATH ou o que vem junto com o GitHub Desktop."""
    g = shutil.which("git")
    if g:
        return g
    base = Path(os.environ.get("LOCALAPPDATA", "")) / "GitHubDesktop"
    achados = sorted(base.glob("app-*/resources/app/git/cmd/git.exe"))
    return str(achados[-1]) if achados else None


def abrir(caminho):
    caminho = str(caminho)
    if not hasattr(os, "startfile"):
        print("ABRIR:", caminho)
        return
    try:
        os.startfile(caminho)
    except OSError:
        # sem programa associado (ex.: .md ou .json): abre no Bloco de Notas
        subprocess.Popen(["notepad.exe", caminho])


def abrir_texto(caminho):
    if os.name == "nt":
        subprocess.Popen(["notepad.exe", str(caminho)])
    else:
        print("ABRIR TEXTO:", caminho)


def mostrar_na_pasta(arquivo: Path):
    if os.name == "nt":
        subprocess.Popen(f'explorer /select,"{arquivo}"')
    else:
        print("MOSTRAR:", arquivo)


def rodar_script(modulo: str, *args, console=True):
    """Abre outra parte do programa (ex.: "shorts.gerar_shorts") num processo separado."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8", HF_HUB_DISABLE_SYMLINKS_WARNING="1")
    if console:
        flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        cmd = [str(PY_CONSOLE), "-m", modulo, *map(str, args), "--pausar"]
        return subprocess.Popen(cmd, creationflags=flags, env=env, cwd=str(FERRAMENTAS))
    cmd = [str(PY_JANELA), "-m", modulo, *map(str, args)]
    return subprocess.Popen(cmd, env=env, cwd=str(FERRAMENTAS))


def em_segundo_plano(raiz, trabalho, ao_terminar, intervalo_ms: int = 150):
    """Roda trabalho() numa linha separada (a tela nao trava) e chama ao_terminar(resultado) na tela.
    O Tkinter so aceita mexer na tela pela linha principal: por isso a tela confere de tempos em tempos
    se o trabalho acabou, em vez de o trabalho mexer na tela direto."""
    import threading

    caixa = {}

    def rodar():
        try:
            caixa["resultado"] = trabalho()
        except Exception as e:  # o erro vira o resultado; quem chamou decide o que fazer
            caixa["resultado"] = e
        caixa["pronto"] = True

    def conferir():
        if caixa.get("pronto"):
            ao_terminar(caixa["resultado"])
        else:
            raiz.after(intervalo_ms, conferir)

    threading.Thread(target=rodar, daemon=True).start()
    raiz.after(intervalo_ms, conferir)
