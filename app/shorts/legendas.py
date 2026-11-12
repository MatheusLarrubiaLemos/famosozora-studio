# Legendas dos Shorts: pega as palavras da transcricao, encaixa o texto corrigido pelo Claude
# no tempo de cada palavra e escreve o arquivo .ass (legenda, titulo, gancho e final).
import difflib
import re
import unicodedata
from pathlib import Path

from nucleo.comum import config_compartilhada, gravar_json, ler_json, ler_vocabulario
from nucleo.video import ALT, LARG, extrair_audio
from nucleo.whisper import carregar_whisper

CFG = config_compartilhada()


# cores da legenda por pessoa (tag \c do ASS: &HBBGGRR&). Sem amarelo.
# Quem fala mais no Short fica com a 1a cor (branco); as outras pessoas, com as seguintes.
CORES = {
    "branco": "&HFFFFFF&",
    "ciano": "&HFFE68C&",
    "rosa": "&HC896FF&",
    "verde": "&H9BFF96&",
    "laranja": "&H6EB4FF&",
    "lilas": "&HFFA0C8&",
    "azul": "&HFFB45A&",
    "vermelho": "&H6464FF&",
}


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
            if not norm(t) and toks:  # pontuacao solta: gruda na palavra anterior
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
            op = dict(
                language=CFG["idioma"],
                word_timestamps=True,
                beam_size=5,
                vad_filter=False,
                condition_on_previous_text=True,
            )
            if self.vocab:
                op["hotwords"] = self.vocab
            try:
                segs, _ = self.modelo.transcribe(audio, **op)
            except TypeError:
                op.pop("hotwords", None)
                segs, _ = self.modelo.transcribe(audio, **op)
            out = [
                {"i": round(ini + w.start, 3), "f": round(ini + w.end, 3), "p": w.word.strip()}
                for s in segs
                for w in (s.words or [])
                if w.word.strip()
            ]
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


def esc_ass(t: str) -> str:
    return t.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ")


def texto_multilinha(t: str) -> str:
    partes = re.split(r"\\n|\n|\|", t)
    return r"\N".join(esc_ass(p.strip()) for p in partes if p.strip())


def ass_tempo(seg: float) -> str:
    seg = max(0.0, seg)
    h = int(seg // 3600)
    m = int(seg % 3600 // 60)
    s = seg % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def agrupar(palavras, por_grupo):
    grupos, atual = [], []
    for w in palavras:
        if atual and (
            len(atual) >= por_grupo or w["i"] - atual[-1]["f"] > 0.6 or w.get("s") != atual[-1].get("s")
        ):  # trocou quem fala: legenda nova
            grupos.append(atual)
            atual = []
        atual.append(w)
        if w["p"][-1:] in ".!?":
            grupos.append(atual)
            atual = []
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
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {LARG}",
        f"PlayResY: {ALT}",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "",
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
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    fim_conteudo = t_final if t_final is not None else total
    dur_gancho = min(float(CFG["duracao_gancho"]), fim_conteudo)
    if gancho and CFG.get("mostrar_texto_gancho"):  # desligado por padrao (era a caixa amarela)
        g = texto_multilinha(gancho.upper())
        anim = r"{\an5\pos(540,%d)\fad(250,300)}" % y_gancho
        L.append(f"Dialogue: 3,{ass_tempo(0)},{ass_tempo(dur_gancho)},Gancho,,0,0,0,,{anim}{g}")

    if CFG["mostrar_titulo"] and titulo and layout != "camera":
        t0 = dur_gancho if gancho else 0
        if fim_conteudo > t0:
            t = titulo.upper() if maiusc else titulo
            t = "".join(ch for ch in t if ord(ch) < 0x2000)
            L.append(
                f"Dialogue: 0,{ass_tempo(t0)},{ass_tempo(fim_conteudo)},Titulo,,0,0,0,,{{\\fad(200,0)}}{esc_ass(t)}"
            )

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
                partes = [
                    (f"{{\\1a&H00&\\fscx112\\fscy112}}{tx}{{\\1a&H30&\\fscx100\\fscy100}}" if k == wi else tx)
                    for k, tx in enumerate(textos)
                ]
                L.append(
                    f"Dialogue: 1,{ass_tempo(offset + ini)},{ass_tempo(offset + fim)},Legenda,,0,0,0,,"
                    f"{{\\c{cor}\\1a&H30&}}{' '.join(partes)}"
                )

    if t_final is not None and total > t_final:
        l1, l2, l3 = (esc_ass(str(CFG.get(k, ""))) for k in ("final_linha_1", "final_linha_2", "final_linha_3"))
        if l1:
            L.append(
                f"Dialogue: 4,{ass_tempo(t_final + 0.05)},{ass_tempo(total)},FinalTopo,,0,0,0,,"
                r"{\an5\pos(540,760)\fad(300,0)}" + l1
            )
        if l2:
            L.append(
                f"Dialogue: 4,{ass_tempo(t_final + 0.25)},{ass_tempo(total)},FinalCTA,,0,0,0,,"
                r"{\an5\pos(540,905)\fad(150,0)\fscx40\fscy40\t(0,220,\fscx112\fscy112)\t(220,380,\fscx100\fscy100)}"
                + l2
            )
        if l3:
            L.append(
                f"Dialogue: 4,{ass_tempo(t_final + 0.55)},{ass_tempo(total)},FinalURL,,0,0,0,,"
                r"{\an5\pos(540,1050)\fad(300,0)}" + l3
            )
    return "\n".join(L) + "\n"
