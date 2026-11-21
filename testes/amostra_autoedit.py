# Video de AMOSTRA para testar o Auto-Edit (gerado com o ffmpeg, sem live de verdade). Tem, em ordem:
#   gameplay com fala -> silencio com tela congelada -> tela preta -> "menu" (imagem fixa com texto)
#   -> gameplay sem fala mas com som do jogo -> gameplay com fala.
# Em cima de tudo, uma "camera" no canto de cima a esquerda que SEMPRE mexe (para conferir que ela fica de fora).
# Tambem devolve uma transcricao falsa (palavras com tempo) das partes com fala.
import subprocess
from pathlib import Path

# (nome, duracao em s) de cada parte, na escala 1 (~3 min)
PARTES = [("fala", 30), ("silencio", 30), ("preto", 20), ("menu", 30), ("jogo_sem_fala", 40), ("fala2", 30)]
CAMERA_AREA = [0.0, 0.0, 0.25, 0.25]


def partes(escala: float = 1.0) -> list:
    """[(nome, inicio, fim)]"""
    out, t = [], 0.0
    for nome, d in PARTES:
        out.append((nome, t, t + d * escala))
        t += d * escala
    return out


def gerar(destino: Path, escala: float = 1.0, largura: int = 640, altura: int = 360) -> dict:
    """Cria o video e devolve {"video", "duracao", "partes", "palavras", "camera_area"}."""
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    tam = f"{largura}x{altura}"
    fontes_v, fontes_a = [], []
    for nome, d in PARTES:
        d = d * escala
        if nome in ("fala", "fala2", "jogo_sem_fala"):
            v = f"testsrc2=size={tam}:rate=30:duration={d}"  # padrao que se mexe = gameplay
        elif nome == "silencio":
            v = f"color=c=0x336699:size={tam}:rate=30:duration={d},drawgrid=w=40:h=40:c=white"
        elif nome == "preto":
            v = f"color=c=black:size={tam}:rate=30:duration={d}"
        else:  # menu: imagem fixa clara com faixas
            v = f"color=c=0xcccccc:size={tam}:rate=30:duration={d},drawbox=x=100:y=80:w=300:h=40:c=0x222222:t=fill"
        if nome in ("fala", "fala2"):
            # "voz": tom com volume ligando e desligando 2x por segundo
            a = f"sine=frequency=220:sample_rate=48000:duration={d},volume='0.6*gt(sin(2*PI*2*t),0)':eval=frame"
        elif nome == "jogo_sem_fala":
            a = f"anoisesrc=color=pink:amplitude=0.25:sample_rate=48000:duration={d}"
        else:
            a = f"anullsrc=r=48000:cl=mono,atrim=duration={d}"
        fontes_v.append(v)
        fontes_a.append(a)
    total = sum(d for _, d in PARTES) * escala
    entradas, filtros = [], []
    for k, (v, a) in enumerate(zip(fontes_v, fontes_a)):
        entradas += ["-f", "lavfi", "-i", v, "-f", "lavfi", "-i", a]
        filtros.append(f"[{2 * k}:v]setsar=1,format=yuv420p[v{k}];[{2 * k + 1}:a]aformat=channel_layouts=stereo[a{k}]")
    n = len(PARTES)
    cw, ch = int(largura * CAMERA_AREA[2]), int(altura * CAMERA_AREA[3])
    entradas += ["-f", "lavfi", "-i", f"testsrc=size={cw}x{ch}:rate=30:duration={total}"]
    juntar = "".join(f"[v{k}][a{k}]" for k in range(n)) + f"concat=n={n}:v=1:a=1[vj][aj]"
    filtros.append(juntar)
    filtros.append(f"[{2 * n}:v]format=yuv420p[cam];[vj][cam]overlay=0:0[v]")
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *entradas, "-filter_complex", ";".join(filtros),
           "-map", "[v]", "-map", "[aj]", "-c:v", "libx264", "-preset", "ultrafast", "-g", "30", "-c:a", "aac",
           "-shortest", str(destino)]  # fmt: skip
    subprocess.run(cmd, check=True)
    palavras = []
    for nome, a, b in partes(escala):
        if nome in ("fala", "fala2"):
            t = a
            while t + 0.25 < b:
                palavras.append({"i": round(t, 2), "f": round(t + 0.25, 2), "p": "palavra"})
                t += 0.5
    return {"video": destino, "duracao": total, "partes": partes(escala), "palavras": palavras,
            "camera_area": CAMERA_AREA}  # fmt: skip
