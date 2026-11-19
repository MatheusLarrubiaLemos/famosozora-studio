# Tudo que conversa com o ffmpeg: achar o programa, medir o video (duracao, tamanho, fps),
# tirar o audio e montar o enquadramento 9:16 dos Shorts.
import os
import subprocess
from pathlib import Path

from nucleo.comum import PASTA_BIN, pausar_e_sair

LARG, ALT = 1080, 1920  # tamanho dos Shorts (9:16)
# sem janela preta piscando: quando quem chama e uma tela (pythonw), cada ffprobe/ffmpeg abria uma janelinha
SEM_JANELA = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def achar_programa(nome: str) -> str:
    from shutil import which

    for ext in (".exe", ""):
        if (PASTA_BIN / f"{nome}{ext}").exists():
            return str(PASTA_BIN / f"{nome}{ext}")
    caminho = which(nome)
    if caminho:
        return caminho
    links = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Links" / f"{nome}.exe"
    if links.exists():
        return str(links)
    print(f"\n[ERRO] Nao encontrei o {nome}. Instale o FamosoZora Studio de novo (o {nome} vem junto);")
    print('       no modo desenvolvedor, abra o "Studio (modo desenvolvedor).bat".')
    pausar_e_sair(1)


def duracao_video(video: Path) -> float:
    ffprobe = achar_programa("ffprobe")
    r = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(video)],
        capture_output=True,
        text=True,
        creationflags=SEM_JANELA,
    )
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def dimensoes_video(video: Path) -> tuple[int, int]:
    ffprobe = achar_programa("ffprobe")
    r = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=p=0:s=x",
            str(video),
        ],
        capture_output=True,
        text=True,
        creationflags=SEM_JANELA,
    )
    try:
        w, h = r.stdout.strip().split("x")[:2]
        return int(w), int(h)
    except Exception:
        return 1920, 1080


def extrair_audio(video: Path, inicio: float | None = None, duracao: float | None = None):
    """Audio 16 kHz mono como numpy float32 (sem depender do PyAV)."""
    import numpy as np

    ffmpeg = achar_programa("ffmpeg")
    cmd = [ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error"]
    if inicio is not None:
        cmd += ["-ss", f"{max(0.0, inicio):.3f}"]
    cmd += ["-i", str(video)]
    if duracao is not None:
        cmd += ["-t", f"{duracao:.3f}"]
    cmd += ["-map", "0:a:0", "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"]
    r = subprocess.run(cmd, capture_output=True, creationflags=SEM_JANELA)
    if r.returncode != 0 or not r.stdout:
        raise RuntimeError("ffmpeg nao conseguiu extrair o audio: " + r.stderr.decode("utf-8", "ignore")[-300:])
    return np.frombuffer(r.stdout, dtype=np.int16).astype(np.float32) / 32768.0


def _crop_area(area, src_w: int, src_h: int) -> str:
    """area = [x, y, w, h] normalizados (0 a 1). Retorna 'crop=w:h:x:y' em pixels pares."""
    x, y, w, h = area
    pw = max(2, int(w * src_w) // 2 * 2)
    ph = max(2, int(h * src_h) // 2 * 2)
    px = min(max(0, int(x * src_w)), src_w - pw)
    py = min(max(0, int(y * src_h)), src_h - ph)
    return f"crop={pw}:{ph}:{px}:{py}"


def filtro_layout(
    cfg: dict, src_w: int, src_h: int, larg: int = 1080, alt: int = 1920, entrada: str = "0:v", sufixo: str = ""
) -> str:
    """Monta o filtro de video 9:16 (sem o rotulo de saida)."""
    s = sufixo
    layout = cfg.get("layout", "desfocado")
    if layout == "camera" and cfg.get("camera_area"):
        hc = int(cfg.get("altura_camera", 600)) // 2 * 2
        hj = alt - hc
        cam = _crop_area(cfg["camera_area"], src_w, src_h)
        jogo = _crop_area(cfg["gameplay_area"], src_w, src_h) + "," if cfg.get("gameplay_area") else ""
        return (
            f"[{entrada}]split=2[c{s}][g{s}];"
            f"[c{s}]{cam},scale={larg}:{hc}:force_original_aspect_ratio=increase,crop={larg}:{hc},setsar=1[cam{s}];"
            f"[g{s}]{jogo}scale={larg}:{hj}:force_original_aspect_ratio=increase,crop={larg}:{hj},setsar=1[jogo{s}];"
            f"[cam{s}][jogo{s}]vstack=inputs=2"
        )
    if layout == "recorte":
        return f"[{entrada}]scale=-2:{alt},crop={larg}:{alt}"
    return (
        f"[{entrada}]split=2[a{s}][b{s}];"
        f"[a{s}]scale={larg}:{alt}:force_original_aspect_ratio=increase,crop={larg}:{alt},"
        f"boxblur=20:2,eq=brightness=-0.10[fundo{s}];"
        f"[b{s}]scale={larg}:-2[frente{s}];"
        f"[fundo{s}][frente{s}]overlay=(W-w)/2:(H-h)/2"
    )


def fps_video(video: Path) -> str:
    """Quadros por segundo do video (ex.: '60' ou '30000/1001'); a transicao suave precisa disso."""
    try:
        r = subprocess.run(
            [
                achar_programa("ffprobe"),
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=r_frame_rate",
                "-of",
                "default=nw=1:nk=1",
                str(video),
            ],
            capture_output=True,
            text=True,
            creationflags=SEM_JANELA,
        )
        fr = r.stdout.strip().splitlines()[0]
        n, d = (fr.split("/") + ["1"])[:2]
        if 10 <= float(n) / float(d) <= 120:
            return fr
    except Exception:
        pass
    return "30"


def tem_placa_nvidia() -> bool:
    """True se o PC tem placa NVIDIA (procura o programa nvidia-smi, que vem com o driver)."""
    from shutil import which

    sistema = Path(os.environ.get("SystemRoot", "")) / "System32" / "nvidia-smi.exe"
    return bool(which("nvidia-smi")) or sistema.exists()


def nvenc_funciona(ffmpeg, cfg: dict, args_nvenc: list, tamanho: str) -> bool:
    """Testa de verdade se a placa NVIDIA consegue montar video (NVENC). Avisa quando a placa existe e falha."""
    if str(cfg.get("codificar_na_gpu", "auto")).lower() in ("false", "nao", "não", "0", "off"):
        return False
    try:
        r = subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                f"color=c=black:s={tamanho}:d=0.3",
                *args_nvenc,
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            creationflags=SEM_JANELA,
        )
        if r.returncode == 0:
            return True
    except Exception:
        pass
    if tem_placa_nvidia():
        print("[AVISO] Achei uma placa NVIDIA, mas ela nao aceitou montar o video (driver antigo?).")
        print("        Vou usar o processador. Atualizar o driver da NVIDIA deixa isso mais rapido.\n")
    return False
