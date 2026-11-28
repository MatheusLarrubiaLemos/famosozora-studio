# Montagem do Short no ffmpeg: abertura + corte + final borrado, musica de fundo, efeitos sonoros e codificador.
# Audio: a musica abaixa sozinha quando alguem fala (ducking), entra e sai com fade, e se for menor que o Short
# repete com crossfade (sem "pulo" na emenda). Os efeitos entram no tempo certo, cada um com o seu volume.
# Tudo roda no processador (filtros de audio do ffmpeg): nao precisa de placa de video.
import math

from nucleo.comum import config_compartilhada
from nucleo.video import ALT, LARG, filtro_layout, nvenc_funciona

CFG = config_compartilhada()


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


FADE_EMENDA = 0.015  # fade de audio em cada emenda de um pedaco cortado dentro do Short (tira o estalo)


def pecas_mantidas(internos, total_bruto: float) -> list:
    """[(a, b)] relativos ao inicio do corte que FICAM (o contrario dos 'internos', ate o fim do final)."""
    out, pos = [], 0.0
    for a, b in sorted(internos):
        if a > pos + 0.01:
            out.append((pos, a))
        pos = max(pos, b)
    if total_bruto > pos + 0.01:
        out.append((pos, total_bruto))
    return out


def _filtros_internos(entrada_v: str, entrada_a: str, pecas: list, fps) -> list:
    """Tira os pedacos cortados dentro do Short: corta cada pedaco que fica (trim exato) e junta (concat)."""
    n = len(pecas)
    f = [f"{entrada_v}split={n}" + "".join(f"[iv{k}]" for k in range(n)),
         f"{entrada_a}asplit={n}" + "".join(f"[ia{k}]" for k in range(n))]  # fmt: skip
    for k, (a, b) in enumerate(pecas):
        d = b - a
        f.append(f"[iv{k}]trim=start={a:.3f}:end={b:.3f},setpts=PTS-STARTPTS[pv{k}]")
        f.append(f"[ia{k}]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS,"
                 f"afade=t=in:st=0:d={FADE_EMENDA},afade=t=out:st={max(0.0, d - FADE_EMENDA):.3f}:d={FADE_EMENDA}"
                 f"[pa{k}]")  # fmt: skip
    f.append("".join(f"[pv{k}][pa{k}]" for k in range(n)) + f"concat=n={n}:v=1:a=1[int_v][int_a]")
    return f


def _filtros_video_e_audio(src_w, src_h, ini_abertura, ini_corte, abertura, dur, final, fps, internos=None):
    """Enquadramento 9:16 e audio do corte e da abertura, e a transicao entre os dois.
    internos = [(a, b)] relativos ao inicio do corte que saem (editor do Short); dur ja vem sem eles.
    Devolve (filtros, T): T = instante em que o corte termina e comeca o final."""
    f = []
    dm = dur + final
    D = duracao_transicao() if abertura else 0.0
    tipo = str(CFG.get("transicao", "fade")).lower()
    tipo = "fade" if tipo in ("", "suave", "auto") else tipo
    if internos:
        bruto = dm + sum(b - a for a, b in internos)
        f.append(filtro_layout(CFG, src_w, src_h, LARG, ALT, f"{ini_corte}:v", "M")
                 + f",setsar=1,format=yuv420p,fps={fps},setpts=PTS-STARTPTS[brutoM_v]")  # fmt: skip
        f.append(f"[{ini_corte}:a:0]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,apad,"
                 f"atrim=0:{bruto:.3f},asetpts=PTS-STARTPTS[brutoM_a]")  # fmt: skip
        f += _filtros_internos("[brutoM_v]", "[brutoM_a]", pecas_mantidas(internos, bruto), fps)
        f.append(f"[int_v]trim=duration={dm:.3f},setpts=PTS-STARTPTS,settb=AVTB[segM_v]")
        f.append(f"[int_a]apad,atrim=0:{dm:.3f},asetpts=PTS-STARTPTS[segM_a]")
    else:
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


CROSSFADE = 1.5  # segundos de mistura na emenda da musica (e na troca de musica)
MUSICA_CURTA = 4.0  # musica menor que isso: so repete, sem crossfade


def volumes_musica(volume=None):
    """(volume durante o corte, volume no final). volume None = o do config.json; o final sobe na mesma proporcao."""
    base, final = float(CFG["volume_musica"]), float(CFG["volume_musica_final"])
    if volume is None:
        return base, final
    v = max(0.0, float(volume))
    return v, (final * v / base) if base > 0 else final


def _formato(entrada: str) -> str:
    return f"[{entrada}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo"


def tamanho_da_faixa(faixas: list, i: int, total: float) -> float:
    """Quanto a faixa i toca: ate a proxima troca (mais o crossfade) ou ate o fim do Short."""
    ini = faixas[i]["inicio"]
    prox = faixas[i + 1]["inicio"] if i + 1 < len(faixas) else None
    L = (prox - ini + CROSSFADE) if prox is not None else (total - ini)
    return max(0.1, min(L, total - ini))


def copias_da_faixa(fx: dict, L: float) -> int:
    """Quantas vezes a musica entra emendada (com crossfade) para cobrir L segundos."""
    dur = fx.get("dur") or 0
    if dur < MUSICA_CURTA or dur >= L:
        return 1
    return min(40, math.ceil((L - CROSSFADE) / (dur - CROSSFADE)))


def _filtros_faixas(faixas: list, total: float) -> list:
    """Cada faixa de musica (a principal e as trocas) cobre o seu pedaco do Short; viram [musbruta].
    faixa = {"entradas": [n, ...] (o mesmo arquivo aberto uma vez por repeticao), "inicio": s, "dur": duracao}
    (o ffmpeg nao consegue emendar com crossfade copias de uma entrada so: por isso o arquivo entra varias vezes)"""
    f, saidas = [], []
    for i, fx in enumerate(faixas):
        ini = fx["inicio"]
        prox = faixas[i + 1]["inicio"] if i + 1 < len(faixas) else None
        L = tamanho_da_faixa(faixas, i, total)
        if len(fx["entradas"]) > 1:
            nomes = [f"m{i}_{k}" for k in range(len(fx["entradas"]))]
            for e, n in zip(fx["entradas"], nomes):
                f.append(_formato(e) + f"[{n}]")
            atual = nomes[0]
            for k, n in enumerate(nomes[1:], 1):
                f.append(f"[{atual}][{n}]acrossfade=d={CROSSFADE}:c1=qsin:c2=qsin[m{i}_x{k}]")
                atual = f"m{i}_x{k}"
            f.append(f"[{atual}]anull[m{i}_cheia]")
        else:
            f.append(_formato(fx["entradas"][0]) + f"[m{i}_cheia]")
        entra = 1.0 if i == 0 else CROSSFADE
        sai = f",afade=t=out:st={max(0.0, L - CROSSFADE):.3f}:d={CROSSFADE}" if prox is not None else ""
        atraso = int(round(ini * 1000))
        f.append(
            f"[m{i}_cheia]atrim=0:{L:.3f},asetpts=PTS-STARTPTS,afade=t=in:st=0:d={entra}{sai}"
            + (f",adelay={atraso}|{atraso}" if atraso > 0 else "")
            + f"[m{i}]"
        )
        saidas.append(f"[m{i}]")
    if len(saidas) == 1:
        f.append(f"{saidas[0]}apad,atrim=0:{total:.3f}[musbruta]")
    else:
        f.append(
            f"{''.join(saidas)}amix=inputs={len(saidas)}:duration=longest:normalize=0,apad,atrim=0:{total:.3f}[musbruta]"
        )
    return f


def _filtros_efeitos(efeitos: list) -> tuple:
    """Cada efeito no seu tempo, com o seu volume. efeito = {"entrada": n, "tempo": s, "volume": v}."""
    f, nomes = [], []
    for j, e in enumerate(efeitos):
        atraso = int(round(max(0.0, e["tempo"]) * 1000))
        f.append(
            _formato(e["entrada"]) + f",volume={max(0.0, float(e['volume'])):.3f}"
            + (f",adelay={atraso}|{atraso}" if atraso > 0 else "") + f"[e{j}]"
        )  # fmt: skip
        nomes.append(f"[e{j}]")
    return f, nomes


def _filtros_audio_final(voz: str, faixas: list, volume, efeitos: list, total: float, T: float) -> list:
    """Voz + musica (que abaixa quando alguem fala e sobe no final) + efeitos -> [a]."""
    if not faixas and not efeitos:
        return [voz + "[a]"]
    f = [voz + (",asplit=2[voz][sc]" if faixas else "[voz]")]
    mix = ["[voz]"]
    if faixas:
        vb, vf = volumes_musica(volume)
        f += _filtros_faixas(faixas, total)
        f.append(
            f"[musbruta]volume='{vb:.3f}+({vf:.3f}-{vb:.3f})*clip((t-{T:.3f})/0.8,0,1)':eval=frame,"
            f"afade=t=out:st={max(0.0, total - 1.2):.3f}:d=1.2[mus]"
        )
        # ducking: a musica abaixa quando tem fala (mais forte que na 1.3.0, que quase nao abaixava com voz baixa)
        limiar, forca = float(CFG.get("ducking_limiar", 0.015)), float(CFG.get("ducking_forca", 10))
        f.append(f"[mus][sc]sidechaincompress=threshold={limiar}:ratio={forca}:attack=15:release=400[musd]")
        mix.append("[musd]")
    ef, nomes = _filtros_efeitos(efeitos)
    f += ef
    mix += nomes
    f.append(f"{''.join(mix)}amix=inputs={len(mix)}:duration=first:normalize=0,alimiter=limit=0.97[a]")
    return f


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
    audio=None,
    internos=None,
    velocidade=1.0,
):
    """Comando completo do ffmpeg para um Short: entradas, filtros (imagem, audio, censura, final,
    legenda, musica e efeitos) e a saida.
    audio = {"faixas": [{"arquivo", "inicio", "dur"}], "volume": v ou None, "efeitos": [{"arquivo", "tempo", "volume"}]}
    (musica = um arquivo so, do jeito antigo: vira uma faixa desde o inicio).
    velocidade > 1 = o Short pronto (ja com legenda, musica e efeitos) e acelerado para caber no tamanho maximo
    (shorts/duracao.py): tudo anda junto, entao legenda e som continuam no lugar."""
    if audio is None:
        audio = {"faixas": [{"arquivo": musica, "inicio": 0.0, "dur": None}] if musica else [], "volume": None}
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-stats", "-y"]
    entradas = 0
    ini_abertura = None
    if abertura:
        a_ini, a_dur = abertura
        cmd += ["-ss", f"{a_ini:.3f}", "-t", f"{a_dur + 0.5:.3f}", "-i", str(video)]
        ini_abertura, entradas = entradas, entradas + 1
    sai = sum(b - a for a, b in internos or [])
    cmd += ["-ss", f"{ini:.3f}", "-t", f"{dur + sai + final + 0.5:.3f}", "-i", str(video)]
    ini_corte, entradas = entradas, entradas + 1
    faixas, efeitos = [], []
    lista = audio.get("faixas") or []
    for i, fx in enumerate(lista):
        copias = copias_da_faixa(fx, tamanho_da_faixa(lista, i, total))
        repetir = (fx.get("dur") or 0) < MUSICA_CURTA  # curta ou sem duracao: o ffmpeg repete sozinho, sem crossfade
        cmd += (["-stream_loop", "-1"] if repetir else []) + ["-i", str(fx["arquivo"])]
        for _ in range(copias - 1):
            cmd += ["-i", str(fx["arquivo"])]
        faixas.append({**fx, "entradas": list(range(entradas, entradas + copias))})
        entradas += copias
    for e in audio.get("efeitos") or []:
        if 0 <= e["tempo"] < total:
            cmd += ["-i", str(e["arquivo"])]
            efeitos.append({**e, "entrada": entradas})
            entradas += 1

    f, T = _filtros_video_e_audio(src_w, src_h, ini_abertura, ini_corte, abertura, dur, final, fps, internos)
    censura, voz_base = _filtros_censura(calar, bip)
    final_legenda, voz = _filtros_final_e_legenda(final, T, voz_base, legenda)
    f += censura + final_legenda + _filtros_audio_final(voz, faixas, audio.get("volume"), efeitos, total, T)

    saida_v, saida_a, dura = "[v]", "[a]", total
    if velocidade and velocidade > 1.0001:
        f.append(f"[v]setpts=PTS/{velocidade:.4f}[vrapido]")
        f.append(f"[a]atempo={velocidade:.4f}[arapido]")  # atempo: acelera sem a voz ficar fina
        saida_v, saida_a, dura = "[vrapido]", "[arapido]", total / velocidade
    cmd += ["-filter_complex", ";".join(f), "-map", saida_v, "-map", saida_a, *args_video(cod),
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", f"{dura:.3f}", str(saida_tmp)]  # fmt: skip
    return cmd
