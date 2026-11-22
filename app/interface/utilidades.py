# Ajudantes das telas: cores, abrir arquivos e pastas, rodar as outras partes do programa e lembrar das
# janelas que so podem abrir uma vez (clicar de novo so traz a que ja esta aberta para a frente).
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
    """Abre outra parte do programa (ex.: "shorts.gerar_shorts") num processo separado.
    Com o Studio aberto, roda ESCONDIDO e o andamento aparece na tela "Tarefa" dentro do Studio
    (interface/tela_tarefa.py, desde a 1.9.2); sem ele, abre a janela preta como antes."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8", HF_HUB_DISABLE_SYMLINKS_WARNING="1")
    if console:
        from interface.telas import studio_aberto

        st = studio_aberto()
        if st is not None and hasattr(st, "navegacao"):
            from interface.tela_tarefa import TelaTarefa, nome_da_tarefa

            cmd = [str(PY_CONSOLE), "-m", modulo, *map(str, args)]
            return TelaTarefa(st, cmd, nome_da_tarefa(modulo, args), env, str(FERRAMENTAS)).proc
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


# ---------------------------------------------------------------- janelas que so podem abrir uma vez
_janelas_abertas = {}


def janela_ja_aberta(chave):
    """Se a janela com essa chave ja esta aberta, traz ela para a frente (e volta se estava minimizada) e devolve
    o objeto dela; senao devolve None. Ex.: clicar duas vezes em Publicar nao abre duas revisoes."""
    obj = _janelas_abertas.get(chave)
    if obj is None:
        return None
    try:
        if obj.jan.winfo_exists():
            obj.jan.deiconify()
            obj.jan.lift()
            obj.jan.focus_force()
            return obj
    except Exception:
        pass
    _janelas_abertas.pop(chave, None)
    return None


def lembrar_janela(chave, obj):
    """Anota que a janela obj.jan esta aberta com essa chave. Quando ela fecha, a chave fica livre de novo.
    (A janela pode ja ter fechado sozinha, ex.: o Claude respondeu um erro na hora: ai nao anota nada.)"""

    def fechou(evento):
        if evento.widget is obj.jan and _janelas_abertas.get(chave) is obj:
            _janelas_abertas.pop(chave, None)

    try:
        if not obj.jan.winfo_exists():
            return obj
        obj.jan.bind("<Destroy>", fechou, add="+")
    except Exception:  # a janela fechou no meio do caminho
        return obj
    _janelas_abertas[chave] = obj
    return obj
