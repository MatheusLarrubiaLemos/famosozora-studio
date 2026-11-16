# Outro padrao no final de todo video longo. Voce coloca o seu outro (ex.: outro.mp4) na pasta outro\ da pasta
# de trabalho; no render, o Studio junta ele no fim do episodio com uma transicao curta (xfade no video e
# acrossfade no audio). Se a resolucao, o FPS ou o audio do outro forem diferentes, ele e convertido na hora para
# combinar com o episodio. Outro sem audio ganha silencio. Pasta vazia = episodio sem outro (com aviso).
import subprocess
from fractions import Fraction
from pathlib import Path

from nucleo import comum
from nucleo.comum import EXTENSOES_VIDEO

DURACAO_MIN, DURACAO_MAX = 5.0, 20.0  # a tela final do YouTube precisa de 5 a 20 s
TRANSICAO = 0.6  # segundos de transicao entre o fim do episodio e o outro
SEM_JANELA = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def achar_outro():
    """O video de outro (o primeiro em ordem alfabetica da pasta outro\\), ou None se a pasta estiver vazia."""
    pasta = comum.PASTA_OUTRO
    if not pasta.exists():
        return None
    videos = sorted(f for f in pasta.iterdir() if f.is_file() and f.suffix.lower() in EXTENSOES_VIDEO
                    and not f.name.startswith(("_", ".")))  # fmt: skip
    return videos[0] if videos else None


def _ffprobe(video: Path, *args) -> str:
    from nucleo.video import achar_programa

    try:
        ffprobe = achar_programa("ffprobe")
        r = subprocess.run([ffprobe, "-v", "error", *args, str(video)], capture_output=True, text=True, timeout=60,
                           creationflags=SEM_JANELA)  # fmt: skip
    except (OSError, SystemExit, subprocess.TimeoutExpired):
        return ""
    return (r.stdout or "").strip()


def info_outro(video: Path) -> dict | None:
    """{duracao, largura, altura, fps, tem_audio} do outro, ou None se o arquivo nao abrir."""
    dur = _ffprobe(video, "-show_entries", "format=duration", "-of", "default=nw=1:nk=1")
    dims = _ffprobe(video, "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate",
                    "-of", "csv=p=0")  # fmt: skip
    audio = _ffprobe(video, "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0")
    try:
        largura, altura, taxa = dims.splitlines()[0].split(",")[:3]
        return {"duracao": float(dur), "largura": int(largura), "altura": int(altura),
                "fps": Fraction(taxa) if taxa and taxa != "0/0" else Fraction(30), "tem_audio": bool(audio)}  # fmt: skip
    except (ValueError, IndexError, ZeroDivisionError):
        return None


def avisos_do_outro(info: dict | None) -> list:
    if info is None:
        return ["Não consegui abrir o vídeo do outro: o episódio vai sem outro."]
    d = info["duracao"]
    if d < DURACAO_MIN or d > DURACAO_MAX:
        return [f"O outro tem {d:.0f} s: para pôr a tela final do YouTube ele precisa ter de 5 a 20 s."]
    return []


def situacao(incluir: bool = True) -> tuple:
    """(arquivo ou None, info ou None, texto para mostrar na tela, tudo_certo?)."""
    if not incluir:
        return None, None, "Sem outro neste vídeo (desligado).", True
    arq = achar_outro()
    if not arq:
        return None, None, "⚠ A pasta outro está vazia: o episódio vai sem outro. Coloque o seu outro.mp4 lá.", False
    info = info_outro(arq)
    avisos = avisos_do_outro(info)
    if info is None:
        return arq, None, "⚠ " + avisos[0], False
    texto = f"Outro: {arq.name} ({info['duracao']:.0f} s)"
    if avisos:
        return arq, info, texto + "   ⚠ " + avisos[0], False
    return arq, info, texto + "  ✓", True


def comando_com_outro(ffmpeg: str, video: Path, ini: float, n_quadros: int, fps: Fraction, outro: Path, info: dict,
                      largura: int, altura: int, args_video: list, base: Path, taxa_audio: int = 48000,
                      fade_in: float = 0.0, transicao: float = TRANSICAO) -> tuple:  # fmt: skip
    """O ultimo trecho do episodio + o outro, com xfade (video) e acrossfade (audio), num arquivo de video e num
    .wav do mesmo tamanho (para juntar com os outros trechos sem recodificar). Devolve (comando, quadros, segundos)."""
    dur0 = n_quadros / fps
    d_outro = info["duracao"]
    d = min(transicao, float(dur0) / 2, d_outro / 2)
    n1 = int(round(d_outro * fps))
    n_trans = int(round(d * fps))
    total_q = n_quadros + n1 - n_trans
    total = total_q / fps
    amostras = int(round(total * taxa_audio))
    fps_txt = f"{fps.numerator}/{fps.denominator}"
    entrada = "" if fade_in <= 0 else f",fade=t=in:st=0:d={fade_in:.3f}"
    aformat = f"aresample={taxa_audio},aformat=sample_fmts=s16:channel_layouts=stereo"
    fi = max(0.015, fade_in)
    filtro = (
        f"[0:v]trim=end_frame={n_quadros},setpts=PTS-STARTPTS,fps={fps_txt}{entrada},format=yuv420p,setsar=1[v0];"
        f"[1:v]scale={largura}:{altura}:force_original_aspect_ratio=decrease,"
        f"pad={largura}:{altura}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps={fps_txt},format=yuv420p,"
        f"setpts=PTS-STARTPTS[v1];"
        f"[v0][v1]xfade=transition=fade:duration={d:.3f}:offset={float(dur0) - d:.4f}[v];"
        f"[0:a]{aformat},apad,atrim=end_sample={int(round(float(dur0) * taxa_audio))},"
        f"afade=t=in:st=0:d={fi:.3f}[a0];"
    )
    if info.get("tem_audio"):
        filtro += f"[1:a]{aformat},apad,atrim=end_sample={int(round(d_outro * taxa_audio))}[a1];"
    else:
        filtro += f"anullsrc=r={taxa_audio}:cl=stereo,atrim=end_sample={int(round(d_outro * taxa_audio))}[a1];"
    filtro += f"[a0][a1]acrossfade=d={d:.3f}:c1=tri:c2=tri,apad,atrim=end_sample={amostras}[a]"
    escala = fps.numerator * (1000 if fps.denominator == 1 else 1)
    cmd = [ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{ini:.6f}",
           "-t", f"{float(dur0) + 1:.3f}", "-i", str(video), "-i", str(outro), "-filter_complex", filtro,
           "-map", "[v]", "-frames:v", str(total_q), *args_video, "-pix_fmt", "yuv420p", "-fps_mode", "cfr",
           "-r", fps_txt, "-video_track_timescale", str(escala), "-an", str(base.with_suffix(".mp4")),
           "-map", "[a]", "-vn", "-c:a", "pcm_s16le", str(base.with_suffix(".wav"))]  # fmt: skip
    return cmd, total_q, float(total)
