# O Claude OLHA a tela (Fase 1D): a cada 10 s, uma miniatura da area do jogo; 16 miniaturas viram um MOSAICO
# (analise\mosaicos\mosaico_001.jpg...), com o numero de cada uma escrito (quando da). O Claude Code do PC le os
# mosaicos (ferramenta Read, so nessa pasta) e diz o que e cada miniatura:
#   gameplay | menu | loading | espera | area_de_trabalho | cutscene | outro   (+ confianca alta/media/baixa)
# "cutscene" conta como gameplay (a historia do jogo fica). Para gastar menos, so vao os mosaicos com trechos em
# que os sinais de som e imagem nao tem certeza (sem fala e com pouca acao). Sem Claude: pula e avisa.
# Saida: analise\cenas.json  {"cenas": [{"tempo": s, "tipo", "confianca"}]}
import math
import subprocess
from pathlib import Path

from autoedit.base import SEM_JANELA, cache_valido, gravar_cache, progresso
from nucleo.comum import tempo_txt
from nucleo.video import achar_programa

VERSAO = 1
A_CADA = 10.0
POR_MOSAICO = 16  # 4 x 4
TIPOS = ("gameplay", "menu", "loading", "espera", "area_de_trabalho", "cutscene", "outro")
SEM_JOGO = ("menu", "loading", "espera", "area_de_trabalho")
SEGUNDOS_POR_MOSAICO = 25  # estimativa de quanto o Claude demora para olhar um mosaico
FONTES = ("C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")


def _fonte():
    for f in FONTES:
        if Path(f).exists():
            return f
    return None


def _filtro_area(camera, gameplay) -> str:
    """Filtro que deixa so a area do jogo (gameplay_area recortada, ou a camera pintada de preto)."""
    partes = []
    if gameplay:
        x, y, w, h = gameplay
        partes.append(f"crop=iw*{w:.4f}:ih*{h:.4f}:iw*{x:.4f}:ih*{y:.4f}")
    elif camera:
        x, y, w, h = camera
        partes.append(f"drawbox=x=iw*{x:.4f}:y=ih*{y:.4f}:w=iw*{w:.4f}:h=ih*{h:.4f}:color=black:t=fill")
    return ",".join(partes + [""])


def gerar_mosaicos(fonte: Path, pasta_analise: Path, duracao: float, camera=None, gameplay=None, cancelar=None,
                   etapa=(1, 1)) -> list:  # fmt: skip
    """Cria os mosaicos (lidos do proxy, rapido). Devolve [(arquivo, [tempos das 16 miniaturas])]."""
    pasta = Path(pasta_analise) / "mosaicos"
    pasta.mkdir(parents=True, exist_ok=True)
    for velho in pasta.glob("mosaico_*.jpg"):
        velho.unlink(missing_ok=True)
    fonte_txt = _fonte()
    texto = ""
    if fonte_txt:
        fonte_esc = fonte_txt.replace(":", "\\:")
        texto = (f",drawtext=fontfile='{fonte_esc}':text='%{{eif\\:mod(n\\,16)+1\\:d}}':x=6:y=6:fontsize=28:"
                 "fontcolor=yellow:box=1:boxcolor=black@0.7")  # fmt: skip
    vf = f"fps=1/{A_CADA},{_filtro_area(camera, gameplay)}scale=320:180{texto},tile=4x4"
    cmd = [achar_programa("ffmpeg"), "-hide_banner", "-nostdin", "-loglevel", "error", "-y", "-i", str(fonte),
           "-an", "-vf", vf, "-q:v", "4", str(pasta / "mosaico_%03d.jpg")]  # fmt: skip
    r = subprocess.run(cmd, capture_output=True, creationflags=SEM_JANELA)
    if r.returncode != 0 and texto:  # sem o texto (fonte com problema): tenta de novo
        vf = f"fps=1/{A_CADA},{_filtro_area(camera, gameplay)}scale=320:180,tile=4x4"
        cmd[cmd.index("-vf") + 1] = vf
        r = subprocess.run(cmd, capture_output=True, creationflags=SEM_JANELA)
    if r.returncode != 0:
        raise RuntimeError("não consegui montar os mosaicos: " + r.stderr.decode("utf-8", "ignore")[-300:])
    arquivos = sorted(pasta.glob("mosaico_*.jpg"))
    n_mini = max(1, math.ceil(duracao / A_CADA - 0.01))
    out = []
    for k, arq in enumerate(arquivos):
        tempos = [(k * POR_MOSAICO + j) * A_CADA for j in range(POR_MOSAICO) if k * POR_MOSAICO + j < n_mini]
        out.append((arq, tempos))
    progresso(*etapa, "Mosaicos para o Claude", 1.0)
    return out


def pedido(mosaicos: list, quero: dict) -> str:
    """Texto do pedido. quero = {arquivo: [numeros das miniaturas (1 a 16) que importam]}."""
    linhas = []
    for arq, tempos in mosaicos:
        nums = quero.get(arq)
        if not nums:
            continue
        lista = ", ".join(f"{n} = {tempo_txt(tempos[n - 1])}" for n in nums if n - 1 < len(tempos))
        linhas.append(f"- {arq} → miniaturas {lista}")
    return (
        "Você vai olhar mosaicos de uma live de gameplay do canal FamosoZora. Cada mosaico tem 16 miniaturas da "
        "TELA DO JOGO (a câmera foi tirada), em 4 linhas de 4, da esquerda para a direita e de cima para baixo "
        "(a 1ª é a do canto de cima à esquerda; quando dá, o número está escrito em amarelo). Uma miniatura a "
        "cada 10 segundos.\n\nUse a ferramenta Read para abrir cada arquivo e diga o que é CADA miniatura pedida:\n"
        "gameplay (jogando, andando, lutando), menu (menu do jogo, inventário, configurações), loading (tela de "
        "carregamento ou preta), espera (tela de 'já volto', lobby parado, fila), area_de_trabalho (Windows, "
        "navegador, outro programa), cutscene (cena da história do jogo) ou outro.\n\n"
        "Arquivos e miniaturas:\n" + "\n".join(linhas) + "\n\n"
        'Responda SÓ com um JSON: {"cenas": [{"tempo": "HH:MM:SS", "tipo": "gameplay", "confianca": "alta"}]} '
        "com uma entrada para cada miniatura pedida (confianca: alta, media ou baixa)."
    )


def validar(dados) -> list:
    if not isinstance(dados, dict) or not isinstance(dados.get("cenas"), list):
        return ['falta a lista "cenas"']
    erros = []
    for k, c in enumerate(dados["cenas"], 1):
        if not isinstance(c, dict) or str(c.get("tipo", "")).lower() not in TIPOS:
            erros.append(f"cena {k}: tipo inválido ({c.get('tipo') if isinstance(c, dict) else c})")
    return erros


def incertos(tempos: list, sem_certeza) -> list:
    """Numeros (1 a 16) das miniaturas de um mosaico em que os sinais nao tem certeza."""
    return [j + 1 for j, t in enumerate(tempos) if sem_certeza(t, t + A_CADA)]


def estimativa(mosaicos: list, sem_certeza) -> tuple[int, float]:
    """(quantos mosaicos vao ao Claude, segundos estimados)."""
    n = sum(1 for _, tempos in mosaicos if incertos(tempos, sem_certeza))
    return n, n * SEGUNDOS_POR_MOSAICO


def classificar(video: Path, fonte: Path, pasta_analise: Path, duracao: float, sem_certeza, camera=None,
                gameplay=None, cancelar_evento=None, avisar=print, etapa=(1, 1), pedir=None) -> dict:  # fmt: skip
    """Classifica as cenas incertas com o Claude (ou le do cache). pedir = funcao de teste no lugar do Claude.
    Devolve {"cenas": [...], "aviso": texto ou ""}."""
    import threading

    from nucleo import claude_local
    from nucleo.comum import ler_tempo

    arq = Path(pasta_analise) / "cenas.json"
    ajustes = {"camera": camera, "jogo": gameplay}
    pronto = cache_valido(arq, video, VERSAO, ajustes)
    if pronto:
        return pronto
    if pedir is None and not claude_local.disponivel():
        return {"cenas": [], "aviso": "Claude Code não encontrado: a análise das cenas (menu, loading...) foi pulada."}
    mosaicos = gerar_mosaicos(fonte, pasta_analise, duracao, camera, gameplay, etapa=etapa)
    quero = {arq_m: incertos(tempos, sem_certeza) for arq_m, tempos in mosaicos}
    quero = {k: v for k, v in quero.items() if v}
    n, segundos = len(quero), len(quero) * SEGUNDOS_POR_MOSAICO
    if not quero:
        dados = {"cenas": [], "aviso": ""}
        gravar_cache(arq, video, VERSAO, dados, ajustes)
        return {"versao": VERSAO, **dados}
    avisar(f"O Claude vai olhar {n} mosaico(s) (~{max(1, round(segundos / 60))} min).")
    cancelar = cancelar_evento or threading.Event()
    cenas = []
    lotes = list(quero.items())
    for k in range(0, len(lotes), 6):  # 6 mosaicos por pedido (a resposta nao fica grande demais)
        parte = dict(lotes[k : k + 6])
        texto_pedido = pedido([m for m in mosaicos if m[0] in parte], parte)
        try:
            if pedir:
                resposta = pedir(texto_pedido, validar)
            else:
                resposta = claude_local.pedir_json(texto_pedido, validar, cancelar, avisar,
                                                   ler_pasta=Path(pasta_analise) / "mosaicos")  # fmt: skip
        except claude_local.Cancelado:
            raise
        except Exception as e:
            return {"cenas": cenas, "aviso": f"O Claude não conseguiu olhar as cenas ({e}). Segui sem essa parte."}
        for c in resposta.get("cenas") or []:
            try:
                t = ler_tempo(c["tempo"])
            except (KeyError, TypeError, ValueError):
                continue
            tipo = str(c.get("tipo", "outro")).lower()
            conf = str(c.get("confianca", "media")).lower()
            cenas.append({"tempo": t, "tipo": tipo, "confianca": conf if conf in ("alta", "media", "baixa") else "media"})
        progresso(*etapa, "O Claude olhando as cenas", min(1.0, (k + 6) / len(lotes)))
    cenas.sort(key=lambda c: c["tempo"])
    dados = {"cenas": cenas, "aviso": ""}
    gravar_cache(arq, video, VERSAO, dados, ajustes)
    return {"versao": VERSAO, **dados}


def sem_jogo(cenas: list) -> list:
    """[(inicio, fim, confianca)] das cenas que NAO sao jogo (cada miniatura vale 10 s)."""
    return [(c["tempo"], c["tempo"] + A_CADA, c["confianca"]) for c in cenas if c["tipo"] in SEM_JOGO]
