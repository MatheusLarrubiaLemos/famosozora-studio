# Cortes automaticos das PAUSAS do video longo (os "jump cuts" dos videos de gameplay cortadinhos).
# Alem dos trechos grandes que o Claude marca para sair, o Studio corta sozinho as pausas em que ninguem fala
# e nada acontece no jogo. Regras (todas no config.json):
#   - pausa sem fala maior que "episodio_pausa_minima" (4 s) vira candidata a corte;
#   - ficam "episodio_contexto_antes" (3 s) antes de voltar a falar (o contexto do que vai ser dito) e
#     "episodio_contexto_depois" (1 s) depois de parar de falar (a reacao respira);
#   - momentos de ACAO no meio da pausa ficam: picos de som do jogo (explosao, briga, morte...) e os momentos
#     que o Claude marcou em "manter" (cutscene importante, boss, momento tenso sem fala);
#   - corte menor que 1 s nao vale a pena (nao corta).
# A emenda dessas pausas e um corte seco (sem escurecer), so com um fade bem curto no audio.
# O som do jogo e medido uma vez e guardado em atividade.json na pasta do projeto.
import subprocess
from pathlib import Path

from nucleo.comum import gravar_json, ler_json

PASSO = 0.5  # segundos por medida do som do jogo
VERSAO_ATIVIDADE = 1
PADRAO = {
    "episodio_cortar_pausas": True,
    "episodio_pausa_minima": 4.0,
    "episodio_contexto_antes": 3.0,
    "episodio_contexto_depois": 1.0,
    "episodio_acao_sensibilidade": 8.0,  # dB acima do som normal do jogo que contam como acao (menor = mais acao)
}
JUNTAR_FALA = 1.0  # palavras com menos que isso entre elas sao a mesma fala
MARGEM_ACAO = 1.5  # segundos mantidos em volta de cada pico de acao
CORTE_MINIMO = 1.0


def ajuste(cfg: dict, chave: str) -> float:
    try:
        return max(0.0, float(cfg.get(chave, PADRAO[chave])))
    except (TypeError, ValueError):
        return float(PADRAO[chave])


def ligado(cfg: dict, dados: dict | None = None) -> bool:
    """Cortar as pausas? O edicao.json do projeto ("cortar_pausas") vale por cima do config.json."""
    if dados is not None and "cortar_pausas" in dados:
        return dados["cortar_pausas"] is not False
    return str(cfg.get("episodio_cortar_pausas", True)).lower() not in ("false", "0", "nao", "não", "off")


# ------------------------------------------------------------------ falas
def falas(palavras, juntar: float = JUNTAR_FALA) -> list:
    """[(inicio, fim)] de cada fala (palavras quase emendadas viram uma fala so). palavras = [(i, f)]."""
    out = []
    for i, f in sorted(palavras):
        if out and i - out[-1][1] <= juntar:
            out[-1] = (out[-1][0], max(out[-1][1], f))
        else:
            out.append((i, f))
    return out


# ------------------------------------------------------------------ som do jogo (acao)
def medir_atividade(ffmpeg: str, video: Path, pasta: Path, avisar=print) -> dict:
    """Volume do video a cada PASSO segundos (em dB), guardado em atividade.json. Le o audio uma vez so."""
    import numpy as np

    arq = Path(pasta) / "atividade.json"
    guardado = ler_json(arq, None)
    if (
        isinstance(guardado, dict)
        and guardado.get("versao") == VERSAO_ATIVIDADE
        and guardado.get("video") == str(video)
    ):
        return guardado
    avisar("Medindo o som do jogo para achar os momentos de acao (so na primeira vez)...")
    taxa = 4000
    amostras = int(taxa * PASSO)
    cmd = [ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-i", str(video), "-map", "0:a:0", "-vn",
           "-ac", "1", "-ar", str(taxa), "-f", "s16le", "-"]  # fmt: skip
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))  # fmt: skip
    db, sobra = [], b""
    while True:
        bloco = proc.stdout.read(amostras * 2 * 600)
        if not bloco:
            break
        bloco = sobra + bloco
        inteiro = len(bloco) // (amostras * 2) * (amostras * 2)
        sobra = bloco[inteiro:]
        if inteiro:
            x = np.frombuffer(bloco[:inteiro], dtype=np.int16).astype(np.float32).reshape(-1, amostras) / 32768.0
            rms = np.sqrt(np.mean(x * x, axis=1)) + 1e-6
            db += [round(float(v), 1) for v in 20 * np.log10(rms)]
    proc.wait()
    dados = {"versao": VERSAO_ATIVIDADE, "video": str(video), "passo": PASSO, "db": db}
    if db:
        gravar_json(arq, dados)
    return dados


def momentos_de_acao(atividade: dict | None, sensibilidade: float, margem: float = MARGEM_ACAO) -> list:
    """[(inicio, fim)] em que o som do jogo fica bem acima do normal (o normal = a mediana do video)."""
    if not atividade or not atividade.get("db"):
        return []
    db = sorted(atividade["db"])
    normal = db[len(db) // 2]
    passo = float(atividade.get("passo") or PASSO)
    out = []
    for k, v in enumerate(atividade["db"]):
        if v >= normal + sensibilidade:
            a, b = max(0.0, k * passo - margem), (k + 1) * passo + margem
            if out and a <= out[-1][1]:
                out[-1] = (out[-1][0], b)
            else:
                out.append((a, b))
    return out


# ------------------------------------------------------------------ o que sai
def _tirar(intervalo: tuple, guardar: list) -> list:
    """Partes de 'intervalo' que nao encostam em nenhum dos intervalos de 'guardar'."""
    partes = [intervalo]
    for ga, gb in guardar:
        novas = []
        for a, b in partes:
            if gb <= a or ga >= b:
                novas.append((a, b))
                continue
            if ga > a:
                novas.append((a, ga))
            if gb < b:
                novas.append((gb, b))
        partes = novas
    return partes


def pausas_para_cortar(palavras, inicio: float, fim: float, cfg: dict, acao=(), manter=()) -> list:
    """[(a, b)] das pausas a cortar dentro de [inicio, fim] (um trecho que fica no episodio).
    acao/manter = [(a, b)] que nunca saem."""
    minima = ajuste(cfg, "episodio_pausa_minima")
    antes, depois = ajuste(cfg, "episodio_contexto_antes"), ajuste(cfg, "episodio_contexto_depois")
    if minima <= 0:
        return []
    dentro = [(max(a, inicio), min(b, fim)) for a, b in falas(palavras) if b > inicio and a < fim]
    # buracos sem fala: do comeco do trecho ate a 1a fala, entre as falas, e da ultima ate o fim do trecho
    buracos, pos = [], inicio
    for a, b in dentro:
        if a > pos:
            buracos.append((pos, a, pos > inicio, True))  # (a, b, tem fala antes?, tem fala depois?)
        pos = max(pos, b)
    if fim > pos:
        buracos.append((pos, fim, pos > inicio, False))
    guardar = sorted(list(acao) + list(manter))
    cortes = []
    for a, b, fala_antes, fala_depois in buracos:
        if b - a < minima:
            continue
        ca = a + (depois if fala_antes else 0.0)
        cb = b - (antes if fala_depois else 0.0)
        for x, y in _tirar((ca, cb), guardar):
            if y - x >= CORTE_MINIMO:
                cortes.append((round(x, 3), round(y, 3)))
    return cortes
