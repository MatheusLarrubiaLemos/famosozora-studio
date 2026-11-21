# Pecas comuns do Auto-Edit: pasta analise\ do projeto, "assinatura" do video (para saber se o cache ainda vale),
# area do jogo (o video menos a camera), leitura de dados crus do ffmpeg e o aviso de progresso que a tela le.
import subprocess
from pathlib import Path

from nucleo.comum import carregar_config, gravar_json, ler_json

PASSO = 0.1  # segundos por medida na linha do tempo de decisao
SEM_JANELA = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class Cancelado(Exception):
    """O usuario apertou Cancelar."""


def pasta_analise(pasta_projeto: Path) -> Path:
    p = Path(pasta_projeto) / "analise"
    p.mkdir(parents=True, exist_ok=True)
    return p


def assinatura(video: Path) -> dict:
    """Tamanho e data do video: se mudarem, a analise guardada nao vale mais."""
    try:
        st = Path(video).stat()
        return {"tamanho": st.st_size, "modificado": int(st.st_mtime)}
    except OSError:
        return {"tamanho": 0, "modificado": 0}


def cache_valido(arq: Path, video: Path, versao: int, extra: dict | None = None):
    """Le o JSON guardado se ele for deste video, desta versao do calculo e com os mesmos ajustes."""
    dados = ler_json(arq)
    if not isinstance(dados, dict):
        return None
    if dados.get("versao") != versao or dados.get("assinatura") != assinatura(video):
        return None
    if extra is not None and dados.get("ajustes") != extra:
        return None
    return dados


def gravar_cache(arq: Path, video: Path, versao: int, dados: dict, extra: dict | None = None):
    gravar_json(arq, {"versao": versao, "assinatura": assinatura(video), "ajustes": extra, **dados})


def areas_do_projeto(pasta_projeto: Path | None, cfg: dict | None = None) -> tuple:
    """(camera_area, gameplay_area) normalizadas [x, y, w, h]. O projeto.json pode ter as suas (desde a 1.9.0);
    sem elas vale a do canal (config.json)."""
    cfg = cfg or carregar_config()
    proj = ler_json(Path(pasta_projeto) / "projeto.json", {}) if pasta_projeto else {}
    proj = proj if isinstance(proj, dict) else {}
    cam = proj.get("camera_area") or cfg.get("camera_area")
    jogo = proj.get("gameplay_area") or cfg.get("gameplay_area")
    return cam, jogo


def mascara_jogo(largura: int, altura: int, camera, gameplay):
    """Mascara (numpy bool) dos pixels que sao do JOGO numa imagem largura x altura.
    Com gameplay_area: so ela. Sem: a imagem inteira menos a camera (a camera sempre mexe e enganaria)."""
    import numpy as np

    m = np.ones((altura, largura), dtype=bool)

    def caixa(area):
        x, y, w, h = (float(v) for v in area)
        x0, y0 = int(round(x * largura)), int(round(y * altura))
        x1, y1 = int(round((x + w) * largura)), int(round((y + h) * altura))
        return max(0, x0), max(0, y0), min(largura, x1), min(altura, y1)

    if gameplay:
        m[:] = False
        x0, y0, x1, y1 = caixa(gameplay)
        m[y0:y1, x0:x1] = True
    if camera:
        x0, y0, x1, y1 = caixa(camera)
        folga = 2  # pixels a mais em volta da camera (a borda borrada da compressao tambem mexe)
        m[max(0, y0 - folga) : y1 + folga, max(0, x0 - folga) : x1 + folga] = False
    if m.sum() < largura * altura * 0.05:  # area errada (quase nada sobrou): usa a imagem toda
        m[:] = True
    return m


_ultimo_aviso = {"t": 0.0}


def progresso(etapa: int, total: int, nome: str, fracao: float):
    """Linha que a tela de analise le: [etapa/total] nome  xx% (no maximo umas 3 por segundo)."""
    import time

    agora = time.monotonic()
    if 0 < fracao < 1 and agora - _ultimo_aviso["t"] < 0.3:
        return
    _ultimo_aviso["t"] = agora
    print(f"[{etapa}/{total}] {nome}  {max(0.0, min(1.0, fracao)) * 100:5.1f}%", flush=True)


def ler_cru(cmd: list, bytes_por_bloco: int, ao_ler, cancelar=None):
    """Roda o ffmpeg e entrega a saida crua em blocos de tamanho fixo (audio ou quadros). Erro = RuntimeError."""
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=SEM_JANELA)
    resto = b""
    try:
        while True:
            if cancelar is not None and cancelar():
                p.kill()
                raise Cancelado()
            pedaco = p.stdout.read(bytes_por_bloco * 16)
            if not pedaco:
                break
            resto += pedaco
            n = len(resto) // bytes_por_bloco
            if n:
                ao_ler(resto[: n * bytes_por_bloco])
                resto = resto[n * bytes_por_bloco :]
        erro = p.stderr.read().decode("utf-8", "ignore")
        p.wait()
    finally:
        if p.poll() is None:
            p.kill()
    if p.returncode != 0:
        raise RuntimeError("o ffmpeg falhou: " + erro[-400:])
