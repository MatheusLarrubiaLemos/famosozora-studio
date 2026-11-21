# Sinais de IMAGEM do Auto-Edit (Fase 1C), numa leitura so do video (2 quadros por segundo, 320x180, cinza):
#   - movimento: quanto a AREA DO JOGO mudou de um quadro para o outro (0 a 1). A camera fica de fora,
#     porque ela sempre mexe e enganaria a deteccao (base.mascara_jogo);
#   - tela congelada: quase nenhum movimento por um tempo (o mesmo calculo do "freezedetect" do ffmpeg);
#   - tela preta / loading: brilho medio muito baixo;
#   - trocas de cena: um salto grande de diferenca entre dois quadros (para encaixar cortes em trocas de tela).
# Saida: analise\imagem.json (ou imagem_<ini>-<fim>.json numa janela de Short).
from pathlib import Path

from autoedit.base import cache_valido, gravar_cache, ler_cru, mascara_jogo, progresso
from nucleo.video import achar_programa

VERSAO = 1
QPS = 2  # quadros por segundo analisados
LARG, ALT = 320, 180
CONGELADO_MOV = 0.004  # movimento abaixo disso = tela parada (um pouco acima de zero: ruido da compressao)
PRETO_BRILHO = 0.06  # brilho abaixo disso = tela preta
TROCA_MINIMA = 0.10  # diferenca minima para contar como troca de cena
TROCA_VEZES = 3.0  # ...e pelo menos 3x a diferenca normal dos quadros anteriores


def nome_arquivo(inicio: float, fim: float | None) -> str:
    return "imagem.json" if not inicio and fim is None else f"imagem_{inicio:.1f}-{fim:.1f}.json"


def medir(video: Path, pasta_analise: Path, duracao: float, camera=None, gameplay=None, inicio: float = 0.0,
          fim: float | None = None, cancelar=None, etapa=(1, 1)) -> dict:  # fmt: skip
    """Mede (ou le do cache) os sinais de imagem de [inicio, fim]."""
    import numpy as np

    arq = Path(pasta_analise) / nome_arquivo(inicio, fim)
    ajustes = {"inicio": round(inicio, 2), "fim": None if fim is None else round(fim, 2),
               "camera": camera, "jogo": gameplay}  # fmt: skip
    pronto = cache_valido(arq, video, VERSAO, ajustes)
    if pronto:
        return pronto
    dur = (fim if fim is not None else duracao) - inicio
    cmd = [achar_programa("ffmpeg"), "-hide_banner", "-nostdin", "-loglevel", "error", "-ss", f"{inicio:.3f}"]
    if fim is not None:
        cmd += ["-t", f"{dur:.3f}"]
    cmd += ["-i", str(video), "-map", "0:v:0", "-an", "-vf", f"fps={QPS},scale={LARG}:{ALT},format=gray",
            "-f", "rawvideo", "-"]  # fmt: skip
    mascara = mascara_jogo(LARG, ALT, camera, gameplay)
    tam = LARG * ALT
    mov, brilho, trocas = [], [], []
    estado = {"anterior": None, "n": 0}
    nome = "Imagem do jogo (movimento e telas paradas)"

    def ao_ler(cru: bytes):
        quadros = np.frombuffer(cru, dtype=np.uint8).reshape(-1, ALT, LARG)
        for q in quadros:
            area = q[mascara].astype(np.int16)
            brilho.append(round(float(area.mean()) / 255, 4))
            ant = estado["anterior"]
            d = 0.0 if ant is None else float(np.abs(area - ant).mean()) / 255
            mov.append(round(d, 4))
            if ant is not None and d >= TROCA_MINIMA:
                recentes = mov[-9:-1]
                normal = sorted(recentes)[len(recentes) // 2] if recentes else 0.0
                if d >= TROCA_VEZES * max(normal, 0.005):
                    trocas.append(round(inicio + (estado["n"] - 0.5) / QPS, 2))  # entre os dois quadros
            estado["anterior"] = area
            estado["n"] += 1
        progresso(*etapa, nome, estado["n"] / QPS / max(0.1, dur))

    ler_cru(cmd, tam, ao_ler, cancelar)
    dados = {"inicio": inicio, "passo": 1 / QPS, "movimento": mov, "brilho": brilho, "trocas": trocas}
    gravar_cache(arq, video, VERSAO, dados, ajustes)
    progresso(*etapa, nome, 1.0)
    return {"versao": VERSAO, "ajustes": ajustes, **dados}


def congelados(dados: dict, minimo: float = 2.0) -> list:
    """[(inicio, fim)] em que a tela do jogo ficou parada por 'minimo' segundos ou mais."""
    passo, base = dados["passo"], dados.get("inicio", 0.0)
    out, ini = [], None
    for k, m in enumerate(dados["movimento"] + [1.0]):
        if m < CONGELADO_MOV and k > 0:
            ini = k if ini is None else ini
        elif ini is not None:
            if (k - ini) * passo >= minimo:
                out.append((round(base + (ini - 1) * passo, 2), round(base + k * passo, 2)))
            ini = None
    return out


def pretos(dados: dict, minimo: float = 1.0) -> list:
    """[(inicio, fim)] de tela preta (ou quase) por 'minimo' segundos ou mais."""
    passo, base = dados["passo"], dados.get("inicio", 0.0)
    out, ini = [], None
    for k, b in enumerate(dados["brilho"] + [1.0]):
        if b < PRETO_BRILHO:
            ini = k if ini is None else ini
        elif ini is not None:
            if (k - ini) * passo >= minimo:
                out.append((round(base + ini * passo, 2), round(base + k * passo, 2)))
            ini = None
    return out
