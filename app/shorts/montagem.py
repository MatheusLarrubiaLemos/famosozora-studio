# Montagem do Short no ffmpeg: abertura + corte + final borrado, musica de fundo e codificador.
import random

from nucleo.comum import PASTA_MUSICAS, config_compartilhada, listar_musicas
from nucleo.video import ALT, LARG, filtro_layout, nvenc_funciona

CFG = config_compartilhada()


def escolher_musica(corte: dict, n: int, semente: str):
    escolha = str(corte.get("musica") or CFG.get("musica") or "").strip()
    if not escolha or escolha.lower() in ("nenhuma", "sem", "false", "off", "nao", "não"):
        return None
    arquivos = listar_musicas()
    if not arquivos:
        return None
    if escolha.lower() == "aleatoria":
        ordem = arquivos[:]
        random.Random(semente).shuffle(ordem)
        return ordem[(n - 1) % len(ordem)]
    for p in arquivos:
        if p.name.lower() == escolha.lower() or p.stem.lower() == escolha.lower():
            return p
    print(f"   [AVISO] musica '{escolha}' nao encontrada em {PASTA_MUSICAS}; seguindo sem musica.")
    return None


def args_video(cod: str) -> list:
    """'nvenc' = placa de video NVIDIA (rapido); 'x264' = processador."""
    if cod == "nvenc":
        return [
            "-c:v",
            "h264_nvenc",
            "-preset",
            "p5",
            "-tune",
            "hq",
            "-rc",
            "vbr",
            "-cq",
            str(int(CFG["qualidade_crf"]) + 1),
            "-b:v",
            "0",
            "-profile:v",
            "high",
        ]
    return ["-c:v", "libx264", "-preset", "medium", "-crf", str(CFG["qualidade_crf"])]


def testar_nvenc(ffmpeg) -> bool:
    return nvenc_funciona(ffmpeg, CFG, args_video("nvenc"), "1080x1920")


def duracao_transicao() -> float:
    if str(CFG.get("transicao", "fade")).lower() in ("nenhuma", "corte", "off", "false"):
        return 0.0
    return max(0.0, min(1.0, float(CFG.get("duracao_transicao", 0.45))))


def montar_comando(
    ffmpeg, video, src_w, src_h, ini, dur, abertura, final, musica, total, saida_tmp, cod="x264", fps="30"
):
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-stats", "-y"]
    f = []
    idx = 0
    if abertura:
        a_ini, a_dur = abertura
        cmd += ["-ss", f"{a_ini:.3f}", "-t", f"{a_dur + 0.5:.3f}", "-i", str(video)]
        ia = idx
        idx += 1
    cmd += ["-ss", f"{ini:.3f}", "-t", f"{dur + final + 0.5:.3f}", "-i", str(video)]
    im = idx
    idx += 1
    if musica:
        cmd += ["-stream_loop", "-1", "-i", str(musica)]
        imu = idx
        idx += 1

    dm = dur + final
    D = duracao_transicao() if abertura else 0.0
    tipo = str(CFG.get("transicao", "fade")).lower()
    tipo = "fade" if tipo in ("", "suave", "auto") else tipo
    f.append(
        filtro_layout(CFG, src_w, src_h, LARG, ALT, f"{im}:v", "M")
        + f",setsar=1,format=yuv420p,fps={fps},trim=duration={dm:.3f},setpts=PTS-STARTPTS,settb=AVTB[segM_v]"
    )
    f.append(
        f"[{im}:a:0]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,apad,"
        f"atrim=0:{dm:.3f},asetpts=PTS-STARTPTS[segM_a]"
    )
    if abertura:
        a_ini, a_dur = abertura
        f.append(
            filtro_layout(CFG, src_w, src_h, LARG, ALT, f"{ia}:v", "A")
            + f",setsar=1,format=yuv420p,fps={fps},trim=duration={a_dur:.3f},setpts=PTS-STARTPTS,"
            f"settb=AVTB[segA_v]"
        )
        f.append(
            f"[{ia}:a:0]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,apad,"
            f"atrim=0:{a_dur:.3f},asetpts=PTS-STARTPTS[segA_a]"
        )
        if D > 0:  # transicao suave: uma cena se mistura na outra (antes era um flash branco)
            f.append(f"[segA_v][segM_v]xfade=transition={tipo}:duration={D:.3f}:offset={a_dur - D:.3f}[vc]")
            f.append(f"[segA_a][segM_a]acrossfade=d={D:.3f}:c1=qsin:c2=qsin[ac]")
        else:
            f.append("[segA_v][segA_a][segM_v][segM_a]concat=n=2:v=1:a=1[vc][ac]")
        T = a_dur + dur - D
    else:
        f.append("[segM_v]null[vc]")
        f.append("[segM_a]anull[ac]")
        T = dur

    if final > 0:
        f.append(
            f"[vc]split=2[vn][vb];"
            f"[vb]boxblur=24:3:enable='gte(t,{T - 0.2:.3f})',eq=brightness=-0.12,"
            f"format=yuva420p,fade=t=in:st={T:.3f}:d=0.6:alpha=1[vbf];"
            f"[vn][vbf]overlay=format=auto[vo]"
        )
        voz = f"[ac]afade=t=out:st={T:.3f}:d=0.9"
    else:
        f.append("[vc]null[vo]")
        voz = "[ac]anull"
    f.append("[vo]subtitles=temp_legenda.ass,format=yuv420p[v]")

    if musica:
        vb, vf = float(CFG["volume_musica"]), float(CFG["volume_musica_final"])
        f.append(voz + ",asplit=2[voz][sc]")
        f.append(
            f"[{imu}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
            f"atrim=0:{total:.3f},asetpts=PTS-STARTPTS,"
            f"volume='{vb}+({vf}-{vb})*clip((t-{T:.3f})/0.8,0,1)':eval=frame,"
            f"afade=t=in:st=0:d=1.0,afade=t=out:st={max(0.0, total - 1.2):.3f}:d=1.2[mus]"
        )
        f.append("[mus][sc]sidechaincompress=threshold=0.05:ratio=5:attack=20:release=500[musd]")
        f.append("[voz][musd]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.97[a]")
    else:
        f.append(voz + "[a]")

    cmd += [
        "-filter_complex",
        ";".join(f),
        "-map",
        "[v]",
        "-map",
        "[a]",
        *args_video(cod),
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        "-t",
        f"{total:.3f}",
        str(saida_tmp),
    ]
    return cmd
