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


def _filtros_video_e_audio(src_w, src_h, ini_abertura, ini_corte, abertura, dur, final, fps):
    """Enquadramento 9:16 e audio do corte e da abertura, e a transicao entre os dois.
    Devolve (filtros, T): T = instante em que o corte termina e comeca o final."""
    f = []
    dm = dur + final
    D = duracao_transicao() if abertura else 0.0
    tipo = str(CFG.get("transicao", "fade")).lower()
    tipo = "fade" if tipo in ("", "suave", "auto") else tipo
    f.append(
        filtro_layout(CFG, src_w, src_h, LARG, ALT, f"{ini_corte}:v", "M")
        + f",setsar=1,format=yuv420p,fps={fps},trim=duration={dm:.3f},setpts=PTS-STARTPTS,settb=AVTB[segM_v]"
    )
    f.append(
        f"[{ini_corte}:a:0]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,apad,"
        f"atrim=0:{dm:.3f},asetpts=PTS-STARTPTS[segM_a]"
    )
    if not abertura:
        f.append("[segM_v]null[vc]")
        f.append("[segM_a]anull[ac]")
        return f, dur
    a_ini, a_dur = abertura
    f.append(
        filtro_layout(CFG, src_w, src_h, LARG, ALT, f"{ini_abertura}:v", "A")
        + f",setsar=1,format=yuv420p,fps={fps},trim=duration={a_dur:.3f},setpts=PTS-STARTPTS,"
        f"settb=AVTB[segA_v]"
    )
    f.append(
        f"[{ini_abertura}:a:0]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,apad,"
        f"atrim=0:{a_dur:.3f},asetpts=PTS-STARTPTS[segA_a]"
    )
    if D > 0:  # transicao suave: uma cena se mistura na outra (antes era um flash branco)
        f.append(f"[segA_v][segM_v]xfade=transition={tipo}:duration={D:.3f}:offset={a_dur - D:.3f}[vc]")
        f.append(f"[segA_a][segM_a]acrossfade=d={D:.3f}:c1=qsin:c2=qsin[ac]")
    else:
        f.append("[segA_v][segA_a][segM_v][segM_a]concat=n=2:v=1:a=1[vc][ac]")
    return f, a_dur + dur - D


def _filtros_censura(calar, bip: bool):
    """Censura no audio: cala (ou troca por um bip) os trechos das palavras censuradas.
    Devolve (filtros, nome do audio que segue adiante)."""
    if not calar:
        return [], "[ac]"
    quando = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in calar)
    f = [f"[ac]volume=0:enable='{quando}'[ac_calado]"]
    if not bip:
        return f, "[ac_calado]"
    f.append(
        "sine=frequency=1000:sample_rate=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"  # o tom sai baixo (1/8): por isso o volume 1.5
        f"volume=1.5,volume=0:enable='not({quando})'[bip]"
    )
    f.append("[ac_calado][bip]amix=inputs=2:duration=first:normalize=0[ac_bip]")
    return f, "[ac_bip]"


def _filtros_final_e_legenda(final: float, T: float, voz_base: str, legenda: str):
    """Final borrado (a partir de T) e a legenda por cima. Devolve (filtros, audio da voz)."""
    if final > 0:
        f = [
            f"[vc]split=2[vn][vb];"
            f"[vb]boxblur=24:3:enable='gte(t,{T - 0.2:.3f})',eq=brightness=-0.12,"
            f"format=yuva420p,fade=t=in:st={T:.3f}:d=0.6:alpha=1[vbf];"
            f"[vn][vbf]overlay=format=auto[vo]"
        ]
        voz = f"{voz_base}afade=t=out:st={T:.3f}:d=0.9"
    else:
        f = ["[vc]null[vo]"]
        voz = f"{voz_base}anull"
    f.append(f"[vo]subtitles={legenda},format=yuv420p[v]")
    return f, voz


def _filtros_musica(voz: str, musica, ini_musica, total: float, T: float) -> list:
    """Musica de fundo que abaixa sozinha quando alguem fala e sobe no final."""
    if not musica:
        return [voz + "[a]"]
    vb, vf = float(CFG["volume_musica"]), float(CFG["volume_musica_final"])
    return [
        voz + ",asplit=2[voz][sc]",
        f"[{ini_musica}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
        f"atrim=0:{total:.3f},asetpts=PTS-STARTPTS,"
        f"volume='{vb}+({vf}-{vb})*clip((t-{T:.3f})/0.8,0,1)':eval=frame,"
        f"afade=t=in:st=0:d=1.0,afade=t=out:st={max(0.0, total - 1.2):.3f}:d=1.2[mus]",
        "[mus][sc]sidechaincompress=threshold=0.05:ratio=5:attack=20:release=500[musd]",
        "[voz][musd]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.97[a]",
    ]


def montar_comando(
    ffmpeg,
    video,
    src_w,
    src_h,
    ini,
    dur,
    abertura,
    final,
    musica,
    total,
    saida_tmp,
    cod="x264",
    fps="30",
    legenda="temp_legenda.ass",
    calar=None,
    bip=False,
):
    """Comando completo do ffmpeg para um Short: entradas, filtros (imagem, audio, censura, final,
    legenda e musica) e a saida."""
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-stats", "-y"]
    entradas = 0
    ini_abertura = ini_musica = None
    if abertura:
        a_ini, a_dur = abertura
        cmd += ["-ss", f"{a_ini:.3f}", "-t", f"{a_dur + 0.5:.3f}", "-i", str(video)]
        ini_abertura, entradas = entradas, entradas + 1
    cmd += ["-ss", f"{ini:.3f}", "-t", f"{dur + final + 0.5:.3f}", "-i", str(video)]
    ini_corte, entradas = entradas, entradas + 1
    if musica:
        cmd += ["-stream_loop", "-1", "-i", str(musica)]
        ini_musica = entradas

    f, T = _filtros_video_e_audio(src_w, src_h, ini_abertura, ini_corte, abertura, dur, final, fps)
    censura, voz_base = _filtros_censura(calar, bip)
    final_legenda, voz = _filtros_final_e_legenda(final, T, voz_base, legenda)
    f += censura + final_legenda + _filtros_musica(voz, musica, ini_musica, total, T)

    cmd += ["-filter_complex", ";".join(f), "-map", "[v]", "-map", "[a]", *args_video(cod),
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", f"{total:.3f}", str(saida_tmp)]  # fmt: skip
    return cmd
