# Passo 3: gera os Shorts no estilo "trailer" a partir do cortes.json (escrito pelo Claude):
#   gancho no inicio  ->  trecho com legenda precisa  ->  final borrado com INSCREVA-SE
#   + musica de fundo que abaixa sozinha quando alguem fala.
# O video original so e LIDO.
import difflib
import random
import re
import subprocess
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

from comum import (CANAL_URL, EXTENSOES_AUDIO, PASTA_MUSICAS, PASTA_SHORTS, achar_programa,
                   carregar_config, carregar_whisper, dimensoes_video, duracao_video, escolher_pasta,
                   extrair_audio, filtro_layout, gravar_json, ler_correcoes, ler_json, ler_tempo,
                   ler_vocabulario, nome_seguro, pausar_e_sair, rodar, tempo_txt)
from falantes import Falantes, marcar_palavras

CFG = carregar_config()
LARG, ALT = 1080, 1920

# cores da legenda por pessoa (tag \c do ASS: &HBBGGRR&). Sem amarelo.
# Quem fala mais no Short fica com a 1a cor (branco); as outras pessoas, com as seguintes.
CORES = {
    "branco": "&HFFFFFF&", "ciano": "&HFFE68C&", "rosa": "&HC896FF&", "verde": "&H9BFF96&",
    "laranja": "&H6EB4FF&", "lilas": "&HFFA0C8&", "azul": "&HFFB45A&", "vermelho": "&H6464FF&",
}


# ================================================================== palavras e legendas
def norm(p: str) -> str:
    p = unicodedata.normalize("NFD", p.lower())
    p = "".join(c for c in p if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", p)


def palavras_brutas(segmentos, ini, fim):
    out = []
    for s in segmentos:
        if s["fim"] < ini or s["inicio"] > fim:
            continue
        for w in s.get("palavras", []):
            if w["f"] > ini and w["i"] < fim:
                out.append(dict(w))
    return out


def aplicar_correcoes(palavras, correcoes: dict):
    if not correcoes:
        return palavras
    mapa = {norm(k): v for k, v in correcoes.items()}
    for w in palavras:
        m = re.match(r"^(\W*)(.*?)(\W*)$", w["p"])
        chave = norm(m.group(2)) if m else norm(w["p"])
        if chave in mapa:
            w["p"] = f"{m.group(1)}{mapa[chave]}{m.group(3)}" if m else mapa[chave]
    return palavras


def _distribuir(tokens, ini, fim):
    pesos = [max(1, len(norm(t))) for t in tokens]
    total = sum(pesos)
    out, t = [], ini
    for tok, p in zip(tokens, pesos):
        d = (fim - ini) * p / total
        out.append({"i": t, "f": t + d, "p": tok})
        t += d
    return out


def _tokens_legenda(texto: str):
    """Separa as palavras da legenda. Trechos entre [[ ]] sao "nao tenho certeza":
    nesses, vale o que o audio (Whisper) entendeu."""
    toks, incerto = [], []
    for m in re.finditer(r"\[\[(.+?)\]\]|(\S+)", texto):
        palavras = m.group(1).split() if m.group(1) is not None else [m.group(2)]
        for t in palavras:
            if not norm(t) and toks:          # pontuacao solta: gruda na palavra anterior
                toks[-1] += t
                continue
            if norm(t):
                toks.append(t)
                incerto.append(m.group(1) is not None)
    return toks, incerto


def alinhar(brutas, texto: str):
    """Usa o texto corrigido (escrito pelo Claude) com o tempo das palavras do Whisper."""
    alvo, incerto = _tokens_legenda(texto)
    if not brutas or not alvo:
        return brutas
    a = [norm(w["p"]) for w in brutas]
    b = [norm(t) for t in alvo]
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    if sm.ratio() < 0.3:
        print("   [AVISO] a legenda corrigida ficou muito diferente do audio; usando a transcricao.")
        return brutas
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                w = brutas[i1 + k]
                out.append({"i": w["i"], "f": w["f"], "p": alvo[j1 + k]})
        elif tag == "replace":
            if any(incerto[j1:j2]):
                out += [dict(w) for w in brutas[i1:i2]]
            else:
                out += _distribuir(alvo[j1:j2], brutas[i1]["i"], brutas[i2 - 1]["f"])
        elif tag == "insert":
            toks = [t for t, inc in zip(alvo[j1:j2], incerto[j1:j2]) if not inc]
            if not toks:
                continue
            n = len(toks)
            ini = out[-1]["f"] if out else (brutas[0]["i"] - 0.25 * n)
            fim = brutas[i1]["i"] if i1 < len(brutas) else ini + 0.3 * n
            if fim - ini < 0.12 * n:
                fim = ini + 0.12 * n
            out += _distribuir(toks, ini, fim)
        # "delete": palavra que nao esta na legenda corrigida -> some
    ultimo = -1e9
    for w in out:
        w["i"] = max(w["i"], ultimo)
        w["f"] = max(w["f"], w["i"] + 0.06)
        ultimo = w["i"]
    return out


class Retranscritor:
    """Transcreve de novo so o trecho do corte, com o modelo mais preciso (se tiver placa de video)."""

    def __init__(self, pasta: Path):
        self.modo = str(CFG.get("retranscrever_cortes", "auto")).lower()
        self.arq = pasta / "retranscricao_cache.json"
        self.cache = ler_json(self.arq, {}) or {}
        self.modelo = None
        self.tentou = False
        self.vocab = ", ".join(ler_vocabulario())

    def palavras(self, video: Path, ini: float, fim: float):
        chave = f"{ini:.2f}-{fim:.2f}"
        if chave in self.cache:
            return [dict(w) for w in self.cache[chave]]
        if self.modo in ("false", "nao", "não", "0", "off"):
            return None
        if not self.tentou:
            self.tentou = True
            try:
                print("Legenda de alta precisao: vou transcrever cada corte de novo.")
                permitir_cpu = self.modo in ("true", "sim", "1", "on", "cpu")
                self.modelo, _ = carregar_whisper(CFG, [CFG["modelo_precisao"], CFG["modelo_gpu"]], permitir_cpu)
                if self.modelo is None:
                    print("(sem placa de video: usando a transcricao original)\n")
            except Exception as e:
                print(f"[AVISO] Nao consegui carregar o Whisper ({e}). Usando a transcricao original.\n")
                self.modelo = None
        if self.modelo is None:
            return None
        try:
            audio = extrair_audio(video, ini, fim - ini)
            op = dict(language=CFG["idioma"], word_timestamps=True, beam_size=5, vad_filter=False,
                      condition_on_previous_text=True)
            if self.vocab:
                op["hotwords"] = self.vocab
            try:
                segs, _ = self.modelo.transcribe(audio, **op)
            except TypeError:
                op.pop("hotwords", None)
                segs, _ = self.modelo.transcribe(audio, **op)
            out = [{"i": round(ini + w.start, 3), "f": round(ini + w.end, 3), "p": w.word.strip()}
                   for s in segs for w in (s.words or []) if w.word.strip()]
        except Exception as e:
            print(f"   [AVISO] retranscricao falhou ({e}); usando a original.")
            return None
        self.cache[chave] = out
        gravar_json(self.arq, self.cache)
        return [dict(w) for w in out]


def palavras_do_trecho(segmentos, retrans, video, ini, fim, legenda, correcoes):
    palavras = retrans.palavras(video, ini, fim)
    if not palavras:
        palavras = palavras_brutas(segmentos, ini, fim)
    palavras = aplicar_correcoes(palavras, correcoes)
    if legenda:
        palavras = alinhar(palavras, legenda)
    return [w for w in palavras if w["f"] > ini and w["i"] < fim]


def relativas(palavras, base, dur):
    out = []
    for w in palavras:
        i, f = max(0.0, w["i"] - base), min(dur, w["f"] - base)
        if f > i:
            out.append({**w, "i": i, "f": f})
    return out


# ================================================================== ASS (legenda, gancho, final)
def esc_ass(t: str) -> str:
    return t.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ")


def texto_multilinha(t: str) -> str:
    partes = re.split(r"\\n|\n|\|", t)
    return r"\N".join(esc_ass(p.strip()) for p in partes if p.strip())


def ass_tempo(seg: float) -> str:
    seg = max(0.0, seg)
    h = int(seg // 3600); m = int(seg % 3600 // 60); s = seg % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def agrupar(palavras, por_grupo):
    grupos, atual = [], []
    for w in palavras:
        if atual and (len(atual) >= por_grupo or w["i"] - atual[-1]["f"] > 0.6
                      or w.get("s") != atual[-1].get("s")):      # trocou quem fala: legenda nova
            grupos.append(atual); atual = []
        atual.append(w)
        if w["p"][-1:] in ".!?":
            grupos.append(atual); atual = []
    if atual:
        grupos.append(atual)
    return grupos


def cores_por_falante(blocos) -> dict:
    """id do falante -> cor. Quem fala mais fica com a 1a cor da lista (branco)."""
    lista = [CORES.get(str(c).lower(), "&HFFFFFF&") for c in CFG.get("cores_falantes") or ["branco"]]
    conta = {}
    for _, palavras, _ in blocos:
        for w in palavras:
            if "s" in w:
                conta[w["s"]] = conta.get(w["s"], 0) + 1
    ordem = sorted(conta, key=lambda k: -conta[k])
    return {spk: (lista[n] if n < len(lista) else lista[0]) for n, spk in enumerate(ordem)}


def montar_ass(blocos, gancho: str, titulo: str, total: float, t_final):
    maiusc = bool(CFG["legenda_maiuscula"])
    cor_de = cores_por_falante(blocos)
    fonte = CFG["fonte"]
    borda = float(CFG.get("borda_legenda", 4))
    layout = CFG["layout"] if (CFG["layout"] != "camera" or CFG.get("camera_area")) else "desfocado"
    y_gancho = int(CFG.get("altura_camera", 600)) if layout == "camera" else (400 if layout == "desfocado" else 360)

    L = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {LARG}", f"PlayResY: {ALT}",
        "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Legenda,{fonte},{CFG['tamanho_legenda']},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,"
        f"-1,0,0,0,100,100,0,0,1,{borda},2,2,60,60,{CFG['posicao_legenda']},1",
        f"Style: Titulo,{fonte},{CFG['tamanho_titulo']},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,"
        f"-1,0,0,0,100,100,0,0,1,6,2,8,70,70,300,1",
        f"Style: Gancho,{fonte},{CFG['tamanho_gancho']},&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,"
        f"-1,0,0,0,100,100,1,0,1,4,3,5,70,70,0,1",
        f"Style: FinalTopo,{fonte},56,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,"
        f"-1,0,0,0,100,100,1,0,1,5,2,5,60,60,0,1",
        f"Style: FinalCTA,{fonte},104,&H00FFFFFF,&H00FFFFFF,&H002020E0,&H002020E0,"
        f"-1,0,0,0,100,100,2,0,3,20,0,5,60,60,0,1",
        f"Style: FinalURL,{fonte},60,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,"
        f"-1,0,0,0,100,100,0,0,1,5,2,5,60,60,0,1",
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    fim_conteudo = t_final if t_final is not None else total
    dur_gancho = min(float(CFG["duracao_gancho"]), fim_conteudo)
    if gancho and CFG.get("mostrar_texto_gancho"):          # desligado por padrao (era a caixa amarela)
        g = texto_multilinha(gancho.upper())
        anim = r"{\an5\pos(540,%d)\fad(250,300)}" % y_gancho
        L.append(f"Dialogue: 3,{ass_tempo(0)},{ass_tempo(dur_gancho)},Gancho,,0,0,0,,{anim}{g}")

    if CFG["mostrar_titulo"] and titulo and layout != "camera":
        t0 = dur_gancho if gancho else 0
        if fim_conteudo > t0:
            t = titulo.upper() if maiusc else titulo
            t = "".join(ch for ch in t if ord(ch) < 0x2000)
            L.append(f"Dialogue: 0,{ass_tempo(t0)},{ass_tempo(fim_conteudo)},Titulo,,0,0,0,,{{\\fad(200,0)}}{esc_ass(t)}")

    por = max(1, int(CFG["palavras_por_legenda"]))
    for offset, palavras, dur_bloco in blocos:
        grupos = agrupar(palavras, por)
        for gi, g in enumerate(grupos):
            fim_g = g[-1]["f"]
            prox = grupos[gi + 1][0]["i"] if gi + 1 < len(grupos) else dur_bloco
            if prox - fim_g < 0.35:
                fim_g = prox
            fim_g = min(fim_g, dur_bloco)
            textos = [esc_ass(w["p"].upper() if maiusc else w["p"]) for w in g]
            cor = cor_de.get(g[0].get("s"), "&HFFFFFF&")
            for wi, w in enumerate(g):
                ini = w["i"]
                fim = g[wi + 1]["i"] if wi + 1 < len(g) else fim_g
                fim = min(fim, dur_bloco)
                if fim <= ini:
                    continue
                # palavra falada agora: cheia e um pouco maior; as outras: levemente apagadas
                partes = [(f"{{\\1a&H00&\\fscx112\\fscy112}}{tx}{{\\1a&H30&\\fscx100\\fscy100}}"
                           if k == wi else tx) for k, tx in enumerate(textos)]
                L.append(f"Dialogue: 1,{ass_tempo(offset + ini)},{ass_tempo(offset + fim)},Legenda,,0,0,0,,"
                         f"{{\\c{cor}\\1a&H30&}}{' '.join(partes)}")

    if t_final is not None and total > t_final:
        l1, l2, l3 = (esc_ass(str(CFG.get(k, ""))) for k in ("final_linha_1", "final_linha_2", "final_linha_3"))
        if l1:
            L.append(f"Dialogue: 4,{ass_tempo(t_final + 0.05)},{ass_tempo(total)},FinalTopo,,0,0,0,,"
                     r"{\an5\pos(540,760)\fad(300,0)}" + l1)
        if l2:
            L.append(f"Dialogue: 4,{ass_tempo(t_final + 0.25)},{ass_tempo(total)},FinalCTA,,0,0,0,,"
                     r"{\an5\pos(540,905)\fad(150,0)\fscx40\fscy40\t(0,220,\fscx112\fscy112)\t(220,380,\fscx100\fscy100)}" + l2)
        if l3:
            L.append(f"Dialogue: 4,{ass_tempo(t_final + 0.55)},{ass_tempo(total)},FinalURL,,0,0,0,,"
                     r"{\an5\pos(540,1050)\fad(300,0)}" + l3)
    return "\n".join(L) + "\n"


# ================================================================== musica
def escolher_musica(corte: dict, n: int, semente: str):
    escolha = str(corte.get("musica") or CFG.get("musica") or "").strip()
    if not escolha or escolha.lower() in ("nenhuma", "sem", "false", "off", "nao", "não"):
        return None
    if not PASTA_MUSICAS.exists():
        return None
    arquivos = sorted(p for p in PASTA_MUSICAS.iterdir() if p.suffix.lower() in EXTENSOES_AUDIO)
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


# ================================================================== ffmpeg
def args_video(cod: str) -> list:
    """'nvenc' = placa de video NVIDIA (rapido); 'x264' = processador."""
    if cod == "nvenc":
        return ["-c:v", "h264_nvenc", "-preset", "p5", "-tune", "hq", "-rc", "vbr",
                "-cq", str(int(CFG["qualidade_crf"]) + 1), "-b:v", "0", "-profile:v", "high"]
    return ["-c:v", "libx264", "-preset", "medium", "-crf", str(CFG["qualidade_crf"])]


def testar_nvenc(ffmpeg) -> bool:
    if str(CFG.get("codificar_na_gpu", "auto")).lower() in ("false", "nao", "não", "0", "off"):
        return False
    try:
        r = subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                            "color=c=black:s=1080x1920:d=0.3", *args_video("nvenc"), "-f", "null", "-"],
                           capture_output=True, text=True, timeout=60)
        return r.returncode == 0
    except Exception:
        return False


def fps_video(video: Path) -> str:
    """Quadros por segundo do video (ex.: '60' ou '30000/1001'); a transicao suave precisa disso."""
    try:
        r = subprocess.run([achar_programa("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=r_frame_rate", "-of", "default=nw=1:nk=1", str(video)],
                           capture_output=True, text=True)
        fr = r.stdout.strip().splitlines()[0]
        n, d = (fr.split("/") + ["1"])[:2]
        if 10 <= float(n) / float(d) <= 120:
            return fr
    except Exception:
        pass
    return "30"


def duracao_transicao() -> float:
    if str(CFG.get("transicao", "fade")).lower() in ("nenhuma", "corte", "off", "false"):
        return 0.0
    return max(0.0, min(1.0, float(CFG.get("duracao_transicao", 0.45))))


def montar_comando(ffmpeg, video, src_w, src_h, ini, dur, abertura, final, musica, total, saida_tmp, cod="x264",
                   fps="30"):
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-stats", "-y"]
    f = []
    idx = 0
    if abertura:
        a_ini, a_dur = abertura
        cmd += ["-ss", f"{a_ini:.3f}", "-t", f"{a_dur + 0.5:.3f}", "-i", str(video)]
        ia = idx; idx += 1
    cmd += ["-ss", f"{ini:.3f}", "-t", f"{dur + final + 0.5:.3f}", "-i", str(video)]
    im = idx; idx += 1
    if musica:
        cmd += ["-stream_loop", "-1", "-i", str(musica)]
        imu = idx; idx += 1

    dm = dur + final
    D = duracao_transicao() if abertura else 0.0
    tipo = str(CFG.get("transicao", "fade")).lower()
    tipo = "fade" if tipo in ("", "suave", "auto") else tipo
    f.append(filtro_layout(CFG, src_w, src_h, LARG, ALT, f"{im}:v", "M")
             + f",setsar=1,format=yuv420p,fps={fps},trim=duration={dm:.3f},setpts=PTS-STARTPTS,settb=AVTB[segM_v]")
    f.append(f"[{im}:a:0]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,apad,"
             f"atrim=0:{dm:.3f},asetpts=PTS-STARTPTS[segM_a]")
    if abertura:
        a_ini, a_dur = abertura
        f.append(filtro_layout(CFG, src_w, src_h, LARG, ALT, f"{ia}:v", "A")
                 + f",setsar=1,format=yuv420p,fps={fps},trim=duration={a_dur:.3f},setpts=PTS-STARTPTS,"
                   f"settb=AVTB[segA_v]")
        f.append(f"[{ia}:a:0]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,apad,"
                 f"atrim=0:{a_dur:.3f},asetpts=PTS-STARTPTS[segA_a]")
        if D > 0:   # transicao suave: uma cena se mistura na outra (antes era um flash branco)
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
        f.append(f"[vc]split=2[vn][vb];"
                 f"[vb]boxblur=24:3:enable='gte(t,{T - 0.2:.3f})',eq=brightness=-0.12,"
                 f"format=yuva420p,fade=t=in:st={T:.3f}:d=0.6:alpha=1[vbf];"
                 f"[vn][vbf]overlay=format=auto[vo]")
        voz = f"[ac]afade=t=out:st={T:.3f}:d=0.9"
    else:
        f.append("[vc]null[vo]")
        voz = "[ac]anull"
    f.append("[vo]subtitles=temp_legenda.ass,format=yuv420p[v]")

    if musica:
        vb, vf = float(CFG["volume_musica"]), float(CFG["volume_musica_final"])
        f.append(voz + ",asplit=2[voz][sc]")
        f.append(f"[{imu}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                 f"atrim=0:{total:.3f},asetpts=PTS-STARTPTS,"
                 f"volume='{vb}+({vf}-{vb})*clip((t-{T:.3f})/0.8,0,1)':eval=frame,"
                 f"afade=t=in:st=0:d=1.0,afade=t=out:st={max(0.0, total - 1.2):.3f}:d=1.2[mus]")
        f.append("[mus][sc]sidechaincompress=threshold=0.05:ratio=5:attack=20:release=500[musd]")
        f.append("[voz][musd]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.97[a]")
    else:
        f.append(voz + "[a]")

    cmd += ["-filter_complex", ";".join(f), "-map", "[v]", "-map", "[a]",
            *args_video(cod),
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", f"{total:.3f}", str(saida_tmp)]
    return cmd


# ================================================================== textos para postar
def textos_do_corte(c: dict) -> dict:
    hashtags = c.get("hashtags", [])
    tags_txt = " ".join(hashtags) if isinstance(hashtags, list) else str(hashtags or "")
    desc = c.get("descricao", "")
    yt_desc = c.get("youtube_descricao") or "\n\n".join(
        x for x in [desc, "▶ Vídeo completo no canal: {link}", tags_txt] if x)
    tiktok = c.get("tiktok") or "\n\n".join(x for x in [desc, tags_txt] if x)
    return {
        "youtube": {"titulo": c.get("youtube_titulo") or c.get("titulo", ""), "descricao": yt_desc,
                    "tags": c.get("tags", []),
                    # ingles: no YouTube Studio, "Idiomas" -> adicionar titulo/descricao traduzidos
                    "titulo_en": c.get("youtube_titulo_en", ""), "descricao_en": c.get("youtube_descricao_en", "")},
        "tiktok": tiktok,
        "instagram": c.get("instagram") or tiktok,
    }


def preencher(t: str, link: str) -> str:
    return t.replace("{link}", link).replace("{canal}", CANAL_URL)


def salvar_publicacao(pasta: Path, saida: Path, itens, projeto: dict):
    arq = saida / "publicacao.json"
    antigo = ler_json(arq, {}) or {}
    postado_antes = {s.get("arquivo"): s.get("postado", {}) for s in antigo.get("shorts", [])}
    shorts = []
    for n, nome, c, dur in itens:
        shorts.append({
            "n": n, "arquivo": nome, "duracao": round(dur, 1),
            "textos": textos_do_corte(c),
            "postado": postado_antes.get(nome, {"youtube": False, "tiktok": False, "instagram": False}),
        })
    gravar_json(arq, {"projeto": pasta.name, "atualizado": datetime.now().isoformat(timespec="seconds"),
                      "shorts": shorts})

    link = projeto.get("link_video_completo") or CANAL_URL
    with open(saida / "textos_para_postar.txt", "w", encoding="utf-8") as f:
        f.write(f"TEXTOS PARA POSTAR - {pasta.name}\n(link do video completo: {link})\n\n")
        for s in shorts:
            t = s["textos"]
            f.write("=" * 70 + f"\n{s['arquivo']}  ({s['duracao']}s)\n" + "=" * 70 + "\n")
            f.write(f"[YOUTUBE] Titulo:\n{t['youtube']['titulo']}\n\n")
            f.write(f"[YOUTUBE] Descricao:\n{preencher(t['youtube']['descricao'], link)}\n\n")
            if t["youtube"]["tags"]:
                f.write(f"[YOUTUBE] Tags:\n{', '.join(t['youtube']['tags'])}\n\n")
            if t["youtube"].get("titulo_en"):
                f.write(f"[YOUTUBE - INGLES] Titulo:\n{t['youtube']['titulo_en']}\n\n")
            if t["youtube"].get("descricao_en"):
                f.write(f"[YOUTUBE - INGLES] Descricao:\n{preencher(t['youtube']['descricao_en'], link)}\n\n")
            f.write(f"[TIKTOK]:\n{preencher(t['tiktok'], link)}\n\n")
            f.write(f"[INSTAGRAM]:\n{preencher(t['instagram'], link)}\n\n")


# ================================================================== principal
def escolher_projeto():
    if len(sys.argv) > 1:
        return Path(sys.argv[1])
    candidatas = sorted([p for p in PASTA_SHORTS.iterdir() if (p / "cortes.json").exists()],
                        key=lambda p: (p / "cortes.json").stat().st_mtime, reverse=True)
    if len(candidatas) == 1:
        return candidatas[0]
    if candidatas:
        print("Videos com cortes prontos:\n")
        for i, p in enumerate(candidatas, 1):
            print(f"  [{i}] {p.name}")
        r = input("\nNumero (ENTER = o mais recente): ").strip()
        return candidatas[int(r) - 1] if r.isdigit() and 1 <= int(r) <= len(candidatas) else candidatas[0]
    print("Nenhuma pasta com cortes.json encontrada. Escolha a pasta do video...")
    return escolher_pasta("Escolha a pasta do video (dentro de shorts)", PASTA_SHORTS)


def main():
    pasta = escolher_projeto()
    if not pasta or not (pasta / "cortes.json").exists():
        print("\n[ERRO] Essa pasta nao tem cortes.json. Peca pro Claude escolher os cortes primeiro.")
        pausar_e_sair(1)

    projeto = ler_json(pasta / "projeto.json", {}) or {}
    video = Path(projeto.get("video", ""))
    if not video.exists():
        print(f"\n[ERRO] Nao achei o video original: {video}\nEle foi movido ou renomeado?")
        pausar_e_sair(1)
    segmentos = (ler_json(pasta / "transcricao.json", {}) or {}).get("segmentos", [])
    dados = ler_json(pasta / "cortes.json", {})
    if dados is None:
        print("\n[ERRO] O cortes.json esta com erro de formatacao. Peca pro Claude conferir.")
        pausar_e_sair(1)
    cortes = dados.get("cortes", []) if isinstance(dados, dict) else dados
    correcoes = {**ler_correcoes(), **(dados.get("correcoes", {}) if isinstance(dados, dict) else {})}

    saida = pasta / "prontos"
    saida.mkdir(exist_ok=True)
    ffmpeg = achar_programa("ffmpeg")
    src_w, src_h = dimensoes_video(video)
    dur_video = duracao_video(video)
    if CFG["layout"] == "camera" and not CFG.get("camera_area"):
        print("[AVISO] layout 'camera' escolhido, mas a camera ainda nao foi marcada.")
        print("        Use 'Marcar camera' no Studio. Usando o fundo desfocado por enquanto.\n")
        CFG["layout"] = "desfocado"
    retrans = Retranscritor(pasta)
    falantes = Falantes(pasta, CFG)
    fps = fps_video(video)
    cod = "nvenc" if testar_nvenc(ffmpeg) else "x264"

    print("=" * 60)
    print(f" Video:  {video.name}")
    print(f" Cortes: {len(cortes)}   Layout: {CFG['layout']}")
    print(" Codificando na: " + ("PLACA DE VIDEO (NVENC)" if cod == "nvenc" else "PROCESSADOR (x264)"))
    print(f" Saida:  {saida}")
    print("=" * 60 + "\n")

    feitos, pulados, erros = 0, 0, 0
    itens = []
    for n, c in enumerate(cortes, 1):
        try:
            ini, fim = ler_tempo(c["inicio"]), ler_tempo(c["fim"])
        except Exception:
            print(f"[{n}/{len(cortes)}] [ERRO] tempos invalidos: {c.get('inicio')} -> {c.get('fim')}")
            erros += 1
            continue
        titulo = c.get("titulo") or f"Corte {n}"
        nome = f"{n:02d} - {nome_seguro(titulo, 60)}.mp4"
        destino = saida / nome
        dur = fim - ini

        abertura = None
        ab = c.get("abertura")
        if ab and CFG.get("usar_abertura", True):
            try:
                a_ini, a_fim = ler_tempo(ab["inicio"]), ler_tempo(ab["fim"])
                if a_fim > a_ini:
                    abertura = (a_ini, a_fim - a_ini)
            except Exception:
                print("   [AVISO] abertura com tempo invalido; ignorando.")
        final = float(CFG.get("duracao_final", 0) or 0)
        if dur_video > 0:
            final = max(0.0, min(final, dur_video - fim))
        D = duracao_transicao() if abertura else 0.0
        total = (abertura[1] if abertura else 0) + dur + final - D
        itens.append((n, nome, c, total))

        if destino.exists():
            print(f"[{n}/{len(cortes)}] ja existe, pulando: {nome}")
            pulados += 1
            continue
        if dur <= 0:
            print(f"[{n}/{len(cortes)}] [ERRO] tempos invalidos ({c['inicio']} -> {c['fim']})")
            erros += 1
            continue
        print(f"[{n}/{len(cortes)}] {tempo_txt(ini)} -> {tempo_txt(fim)} ({dur:.0f}s + final)  {titulo}")

        palavras = palavras_do_trecho(segmentos, retrans, video, ini, fim, c.get("legenda", ""), correcoes)
        marcar_palavras(palavras, falantes.trechos(video, ini, fim))
        blocos, off = [], 0.0
        if abertura:
            a_ini, a_dur = abertura
            if a_ini >= ini - 0.05 and a_ini + a_dur <= fim + 0.05:
                pa = [w for w in palavras if w["f"] > a_ini and w["i"] < a_ini + a_dur]
            else:
                pa = palavras_do_trecho(segmentos, retrans, video, a_ini, a_ini + a_dur,
                                        c.get("legenda_abertura", ""), correcoes)
                marcar_palavras(pa, falantes.trechos(video, a_ini, a_ini + a_dur))
            # na transicao (D segundos) as duas cenas se misturam: cada legenda fica com metade
            blocos.append((0.0, relativas(pa, a_ini, a_dur - D / 2), a_dur - D / 2))
            off = a_dur - D / 2
            blocos.append((off, relativas(palavras, ini + D / 2, dur - D / 2), dur - D / 2))
        else:
            blocos.append((off, relativas(palavras, ini, dur), dur))
        t_final = off + (dur - D / 2 if abertura else dur) if final > 0 else None

        (pasta / "temp_legenda.ass").write_text(
            montar_ass(blocos, c.get("texto_gancho", ""), titulo, total, t_final), encoding="utf-8")
        musica = escolher_musica(c, n, pasta.name)
        if musica:
            print(f"   musica: {musica.name}")
        temp_saida = saida / f"_gerando_{n:02d}.mp4"
        cmd = montar_comando(ffmpeg, video, src_w, src_h, ini, dur, abertura, final, musica, total, temp_saida, cod, fps)
        r = subprocess.run(cmd, cwd=str(pasta))
        if r.returncode != 0 and cod == "nvenc":
            print("   [AVISO] a placa de video falhou nesse corte; tentando no processador...")
            cmd = montar_comando(ffmpeg, video, src_w, src_h, ini, dur, abertura, final, musica, total,
                                 temp_saida, "x264", fps)
            r = subprocess.run(cmd, cwd=str(pasta))
        if r.returncode == 0 and temp_saida.exists():
            temp_saida.replace(destino)
            feitos += 1
        else:
            erros += 1
            if temp_saida.exists():
                temp_saida.unlink()
            print("   [ERRO] esse corte falhou.")
    (pasta / "temp_legenda.ass").unlink(missing_ok=True)

    salvar_publicacao(pasta, saida, itens, projeto)

    print("\n" + "=" * 60)
    print(f" PRONTO! {feitos} criado(s), {pulados} ja existia(m), {erros} com erro.")
    print(f" Pasta: {saida}")
    print(" Textos pra postar: textos_para_postar.txt (ou botao 'Publicar' no Studio)")
    print("=" * 60)


if __name__ == "__main__":
    rodar(main)
