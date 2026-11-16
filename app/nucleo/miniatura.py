# Miniaturas: uma imagem pequena de cada video (para os cartoes de projeto) e a thumb do pacote de postagem.
# Tudo feito com o ffmpeg que ja vem com o programa. Se der erro, o programa segue sem a imagem.
import subprocess
from pathlib import Path

from nucleo.comum import ler_json

NOME = "miniatura.png"
LARGURA, ALTURA = 112, 63  # 16:9, cabe numa linha da lista


def ffmpeg_ou_nada():
    """Caminho do ffmpeg, ou None se nao achar (sem fechar o programa)."""
    from nucleo.video import achar_programa

    try:
        return achar_programa("ffmpeg")
    except SystemExit:
        return None


def tirar_quadro(video: Path, destino: Path, segundo: float, largura: int = 0, altura: int = 0) -> bool:
    """Salva um quadro do video como imagem. largura/altura = 0 mantem o tamanho original."""
    ffmpeg = ffmpeg_ou_nada()
    if not ffmpeg or not Path(video).exists():
        return False
    filtro = []
    if largura and altura:
        filtro = ["-vf", f"scale={largura}:{altura}:force_original_aspect_ratio=decrease,"
                         f"pad={largura}:{altura}:(ow-iw)/2:(oh-ih)/2:color=0x2B2A28"]  # fmt: skip
    destino.parent.mkdir(parents=True, exist_ok=True)
    comando = [ffmpeg, "-y", "-loglevel", "error", "-ss", f"{max(0.0, segundo):.2f}", "-i", str(video),
               "-frames:v", "1", *filtro, str(destino)]  # fmt: skip
    try:
        r = subprocess.run(comando, capture_output=True, timeout=60,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))  # fmt: skip
    except (OSError, subprocess.TimeoutExpired):
        return False
    return r.returncode == 0 and destino.exists() and destino.stat().st_size > 0


def miniatura(pasta: Path):
    """A miniatura do projeto, se ja existe."""
    arq = Path(pasta) / NOME
    return arq if arq.exists() and arq.stat().st_size > 0 else None


def video_do_projeto(pasta: Path):
    projeto = ler_json(Path(pasta) / "projeto.json", {}) or {}
    video = Path(projeto.get("video") or "")
    return video if projeto.get("video") and video.exists() else None


def gerar_miniatura(pasta: Path):
    """Cria a miniatura do projeto (um quadro a 10% do video, no maximo no minuto 1). Devolve o arquivo ou None."""
    video = video_do_projeto(pasta)
    if not video:
        return None
    duracao = float((ler_json(Path(pasta) / "projeto.json", {}) or {}).get("duracao") or 0)
    segundo = min(60.0, duracao * 0.1) if duracao else 5.0
    arq = Path(pasta) / NOME
    return arq if tirar_quadro(video, arq, segundo, LARGURA, ALTURA) else None
