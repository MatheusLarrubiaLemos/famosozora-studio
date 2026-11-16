# Tocador de audio simples, dentro do proprio Studio (sem abrir outro programa): usado pelo editor de
# Shorts para ouvir o trecho de uma linha e parar com a tecla Espaco.
# No Windows usa o "winsound", que ja vem com o Python. Em outro sistema, quem chama abre o trecho no player.
import subprocess
import time
from pathlib import Path

_estado = {"ate": 0.0}


def disponivel() -> bool:
    try:
        import winsound  # noqa: F401
    except ImportError:
        return False
    return True


def cortar_audio(ffmpeg: str, video: Path, ini: float, fim: float, saida: Path) -> bool:
    """Tira o audio do trecho (ini a fim, em segundos) num .wav que o winsound toca."""
    saida.parent.mkdir(parents=True, exist_ok=True)
    comando = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{max(0.0, ini):.3f}",
               "-t", f"{max(0.1, fim - ini):.3f}", "-i", str(video), "-vn", "-ac", "2", "-ar", "44100",
               "-c:a", "pcm_s16le", str(saida)]  # fmt: skip
    r = subprocess.run(comando, capture_output=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return r.returncode == 0 and saida.exists()


def tocar(arquivo: Path, duracao: float) -> bool:
    """Toca o .wav sem travar a tela. Devolve False se nao der para tocar aqui."""
    try:
        import winsound
    except ImportError:
        return False
    winsound.PlaySound(str(arquivo), winsound.SND_FILENAME | winsound.SND_ASYNC)
    _estado["ate"] = time.monotonic() + duracao
    return True


def parar():
    try:
        import winsound

        winsound.PlaySound(None, 0)
    except ImportError:
        pass
    _estado["ate"] = 0.0


def tocando() -> bool:
    return time.monotonic() < _estado["ate"]
