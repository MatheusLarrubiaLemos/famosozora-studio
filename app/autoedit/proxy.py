# Versao LEVE da live para o editor (Fase 1A): 540p, H.264, quadro-chave a cada 0,5 s (pular para qualquer ponto e
# instantaneo), audio AAC. Placa NVIDIA = NVENC; sem placa = x264 "veryfast". O original so e usado para exportar.
# Junto, as MINIATURAS da timeline: uma a cada 5 s, em folhas de 10x10 (analise\miniaturas\folha_001.jpg...).
# Tudo fica em <projeto>\analise\. Se o video original mudar, refaz.
import subprocess
from pathlib import Path

from autoedit.base import SEM_JANELA, Cancelado, assinatura, progresso
from nucleo.comum import carregar_config, gravar_json, ler_json
from nucleo.video import achar_programa, nvenc_funciona

VERSAO = 1
ALTURA = 540
QPS_PROXY = 30
MINI_A_CADA = 5.0  # segundos entre miniaturas
MINI_LARG, MINI_ALT = 160, 90
MINI_COLUNAS = MINI_LINHAS = 10


def arq_proxy(pasta_analise: Path) -> Path:
    return Path(pasta_analise) / "proxy.mp4"


def proxy_pronto(pasta_analise: Path, video: Path) -> bool:
    info = ler_json(Path(pasta_analise) / "proxy.json", {}) or {}
    return arq_proxy(pasta_analise).exists() and info.get("versao") == VERSAO and info.get("assinatura") == assinatura(
        video
    )


def _args_video(cod: str) -> list:
    gop = str(int(QPS_PROXY / 2))  # quadro-chave a cada 0,5 s
    if cod == "nvenc":
        return ["-c:v", "h264_nvenc", "-preset", "p3", "-cq", "28", "-b:v", "0", "-g", gop]
    return ["-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-g", gop, "-keyint_min", gop, "-sc_threshold", "0"]


def _rodar(cmd: list, dur: float, etapa, nome: str, cancelar) -> int:
    p = subprocess.Popen(cmd + ["-progress", "pipe:1", "-nostats"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, encoding="utf-8", errors="replace", creationflags=SEM_JANELA)  # fmt: skip
    try:
        for linha in p.stdout:
            if cancelar is not None and cancelar():
                p.kill()
                raise Cancelado()
            if linha.startswith("out_time_us="):
                try:
                    progresso(*etapa, nome, int(linha.split("=")[1]) / 1e6 / max(0.1, dur))
                except ValueError:
                    pass
        p.wait()
    finally:
        if p.poll() is None:
            p.kill()
    if p.returncode != 0:
        print(p.stderr.read()[-800:])
    return p.returncode


def gerar_proxy(video: Path, pasta_analise: Path, duracao: float, cancelar=None, etapa=(1, 1)) -> Path:
    """Cria (ou reaproveita) o proxy.mp4. Devolve o caminho. Erro = RuntimeError."""
    destino = arq_proxy(pasta_analise)
    if proxy_pronto(pasta_analise, video):
        progresso(*etapa, "Versão leve para o editor", 1.0)
        return destino
    ffmpeg = achar_programa("ffmpeg")
    cfg = carregar_config()
    cod = "nvenc" if nvenc_funciona(ffmpeg, cfg, _args_video("nvenc"), "960x540") else "x264"
    if cod == "x264":
        print("Sem placa NVIDIA: a versão leve é feita no processador (mais devagar).", flush=True)
    temp = destino.with_name("proxy.gerando.mp4")
    nome = "Versão leve para o editor"

    def comando(c):
        return [ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error", "-y", "-i", str(video),
                "-map", "0:v:0", "-map", "0:a:0?", "-vf", f"scale=-2:min({ALTURA}\\,ih),fps={QPS_PROXY},format=yuv420p",
                *_args_video(c), "-c:a", "aac", "-b:a", "96k", "-ac", "2", "-movflags", "+faststart", str(temp)]  # fmt: skip

    try:
        r = _rodar(comando(cod), duracao, etapa, nome, cancelar)
        if r != 0 and cod == "nvenc":
            print("A placa de vídeo falhou na versão leve; tentando no processador...", flush=True)
            r = _rodar(comando("x264"), duracao, etapa, nome, cancelar)
    except Cancelado:
        temp.unlink(missing_ok=True)
        raise
    if r != 0 or not temp.exists():
        temp.unlink(missing_ok=True)
        raise RuntimeError("não consegui criar a versão leve do vídeo (veja o studio.log).")
    temp.replace(destino)
    gravar_json(Path(pasta_analise) / "proxy.json", {"versao": VERSAO, "assinatura": assinatura(video),
                                                     "codificador": cod, "altura": ALTURA})  # fmt: skip
    progresso(*etapa, nome, 1.0)
    return destino


def pasta_miniaturas(pasta_analise: Path) -> Path:
    return Path(pasta_analise) / "miniaturas"


def gerar_miniaturas(fonte: Path, video: Path, pasta_analise: Path, duracao: float, cancelar=None,
                     etapa=(1, 1)) -> dict:  # fmt: skip
    """Folhas de miniaturas da timeline (lidas do proxy, que e rapido). Devolve o miniaturas.json."""
    pasta = pasta_miniaturas(pasta_analise)
    info_arq = pasta / "miniaturas.json"
    info = ler_json(info_arq, {}) or {}
    if info.get("versao") == VERSAO and info.get("assinatura") == assinatura(video):
        progresso(*etapa, "Miniaturas da timeline", 1.0)
        return info
    pasta.mkdir(parents=True, exist_ok=True)
    for velho in pasta.glob("folha_*.jpg"):
        velho.unlink(missing_ok=True)
    ffmpeg = achar_programa("ffmpeg")
    vf = (f"fps=1/{MINI_A_CADA},scale={MINI_LARG}:{MINI_ALT}:force_original_aspect_ratio=decrease,"
          f"pad={MINI_LARG}:{MINI_ALT}:(ow-iw)/2:(oh-ih)/2,tile={MINI_COLUNAS}x{MINI_LINHAS}")  # fmt: skip
    cmd = [ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error", "-y", "-skip_frame", "nokey", "-i", str(fonte),
           "-an", "-vf", vf, "-q:v", "5", str(pasta / "folha_%03d.jpg")]  # fmt: skip
    if _rodar(cmd, duracao, etapa, "Miniaturas da timeline", cancelar) != 0:
        # sem quadros-chave suficientes (video original com poucos): le todos os quadros
        cmd.remove("-skip_frame")
        cmd.remove("nokey")
        if _rodar(cmd, duracao, etapa, "Miniaturas da timeline", cancelar) != 0:
            raise RuntimeError("não consegui criar as miniaturas da timeline.")
    info = {"versao": VERSAO, "assinatura": assinatura(video), "a_cada": MINI_A_CADA, "largura": MINI_LARG,
            "altura": MINI_ALT, "colunas": MINI_COLUNAS, "linhas": MINI_LINHAS,
            "folhas": sorted(p.name for p in pasta.glob("folha_*.jpg"))}  # fmt: skip
    gravar_json(info_arq, info)
    progresso(*etapa, "Miniaturas da timeline", 1.0)
    return info


def onde_esta_miniatura(info: dict, t: float):
    """(folha, x, y) da miniatura do instante t, ou None."""
    if not info or not info.get("folhas"):
        return None
    k = max(0, int(t // info["a_cada"]))
    por_folha = info["colunas"] * info["linhas"]
    f = k // por_folha
    if f >= len(info["folhas"]):
        f, k = len(info["folhas"]) - 1, por_folha * len(info["folhas"]) - 1
    resto = k % por_folha
    return info["folhas"][f], (resto % info["colunas"]) * info["largura"], (resto // info["colunas"]) * info["altura"]
