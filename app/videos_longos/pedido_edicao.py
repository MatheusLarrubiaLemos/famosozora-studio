# Passo 5 (video longo): pedido de edicao para o Claude (copiar e colar, ou automatico com a transcricao junto),
# leitura/validacao do edicao.json, ajuste das bordas no silencio, plano do episodio (trechos que ficam) e capitulos.
# Formato do edicao.json (versao 3, desde a 1.9.0; sem gancho no video longo):
#   {"versao": 3, "remover": [{"inicio", "fim", "motivo"}], "manter": [...], "capitulos": [{"tempo", "titulo",
#    "titulo_en"}], "titulo", "descricao", "tags", ...                      <- o que o Claude escreve
#    "tipo": "longo", "video_original", "predefinicao": {"nome", "versao"}, "introducao": {"inicio", "fim"},
#    "serie": bool, "trechos": [...], "marcadores": [...], "historico_versao_app"}  <- Auto-Edit e editor
# Arquivos antigos sao convertidos sozinhos, com copia: versao 1 ("cortes", "abertura") e versao 2 (sem os campos
# do Auto-Edit) -> edicao.bak.json (ou edicao.v2.bak.json, se a de antes ja existir).
# Dentro do programa a lista do Claude que sai continua se chamando "cortes".
# Nao renderiza nada: quem renderiza e o editar_episodio.py.
import json
import re
from fractions import Fraction
from pathlib import Path

from nucleo.comum import CANAL_URL, carregar_config, ler_json, ler_tempo, tempo_txt
from nucleo.video import duracao_video, fps_video

CORTE_CURTO = 30.0  # cortes menores que isso ganham aviso na revisao
TRECHO_MINIMO = 1.0  # trecho mantido menor que isso entre dois cortes: os dois cortes viram um so
ABERTURA_MIN, ABERTURA_MAX = 15.0, 30.0
CAPITULO_MIN = 10.0  # regra do YouTube: cada capitulo com 10 s ou mais
CAPITULOS_MIN = 3  # regra do YouTube: no minimo 3 capitulos

VERSAO_EDICAO = 3
EXEMPLO = """{
  "versao": 3,
  "remover": [
    {"inicio": "00:00:00", "fim": "00:01:13", "motivo": "controle nao funcionava, jogo parado"}
  ],
  "manter": [
    {"inicio": "00:42:10", "fim": "00:43:05", "motivo": "cutscene do chefe, sem fala mas importante"}
  ],
  "capitulos": [
    {"tempo": "00:01:14", "titulo": "Aula de quimica", "titulo_en": "Chemistry class"}
  ],
  "titulo": "...", "descricao": "...",
  "titulo_en": "...", "descricao_en": "...",
  "opcoes_titulo": ["...", "...", "..."],
  "ideia_miniatura": "numero do episodio + 2 ou 3 palavras + personagem principal do dia",
  "tags": ["..."]
}"""


# ================================================================== pedido para o Claude
def texto_pedido(nome: str, pasta: Path, arq_diretrizes: Path, duracao: float) -> str:
    return (
        f'Claude, edita o vídeo longo do projeto "{nome}": transforma a live bruta num episódio '
        "editado, estilo programa de TV.\n"
        f"Pasta: {pasta}\n"
        f"Duração do vídeo original: {tempo_txt(duracao)}\n"
        "Leia a transcrição no arquivo transcricao_para_claude.txt dessa pasta (é grande: leia o arquivo, "
        "não peça pra eu colar). Ela tem o formato [início-fim] fala.\n"
        f"Siga as DIRETRIZES DO CANAL ({arq_diretrizes}). Resumo: o YouTube virou TV; o vídeo longo aprofunda; "
        "é bem editado mas não picotado; o foco é sempre a parte em que estou jogando.\n\n"
        + criterios()
        + "Salve como edicao.json nessa pasta, neste formato (tempos do vídeo original, HH:MM:SS):\n"
        f"{EXEMPLO}\n\n"
        "Se você não conseguir salvar no meu PC, me mande só o JSON completo num bloco de código "
        'que eu colo no Studio (botão "Colar edicao.json").'
    )


def criterios() -> str:
    """As regras da edicao do video longo (iguais no pedido de copiar e colar e no automatico)."""
    return (
        "ESTILO: programa de TV. Bem editado, mas SEM picotar: corte só onde realmente não acontece nada.\n"
        "- SEM GANCHO: o vídeo começa normal, do começo. A intro (a apresentação do começo) FICA.\n"
        "- Sai: espera parada antes de tudo começar, menus e carregamentos longos, tela parada, pausas e papo "
        "sem nada com o jogo parado.\n"
        "- Fica: tudo em que estou jogando, incluindo conversa e piada durante o jogo.\n"
        "- Tentativas repetidas da mesma missão: ficam a primeira, a que deu certo e as que tiveram reação boa.\n"
        "- Nenhum trecho removido menor que 30 s. Todo corte começa e termina em fim de frase. "
        "Corte pequeno deixa o vídeo picotado. O Studio põe uma transição suave (fade curto) em cada emenda.\n"
        "- PAUSAS: o Studio corta SOZINHO as pausas em que eu fico calado (deixa 3 s antes de eu voltar a falar, "
        "1 s depois de eu parar e os picos de som do jogo). Você NÃO precisa marcar essas pausas. Mas se um "
        "momento SEM FALA for importante (cutscene da história, chefe, perseguição, momento tenso, final de "
        'missão), coloque em "manter" para ele não ser cortado.\n'
        "- Você só vê a transcrição, não a tela: eu reviso cada trecho no Studio antes de gerar. "
        'Explique cada um no campo "motivo".\n\n'
        "TAMBÉM QUERO\n"
        "- capitulos: tempos do vídeo ORIGINAL (o Studio converte pro episódio editado), o primeiro no começo "
        "do jogo, no mínimo 3, títulos curtos em português (titulo) e inglês (titulo_en).\n"
        "- titulo: honesto e chamativo, com o objetivo do episódio. Palavrão pode. Se for série, cite o episódio.\n"
        "- descricao (sem os capítulos, o Studio coloca), titulo_en e descricao_en, 3 opcoes_titulo, "
        "ideia_miniatura (número do episódio + 2 ou 3 palavras + personagem principal do dia) e poucas tags.\n\n"
    )


def pedido_automatico(nome: str, duracao: float, diretrizes: str, transcricao: str, parte: int = 1, total: int = 1,
                      intervalo=("", "")) -> str:  # fmt: skip
    """Pedido completo para o 'claude -p': regras, diretrizes, formato e a transcricao (ou uma parte dela)."""
    sobre_parte = ""
    if total > 1:
        sobre_parte = (f"ATENÇÃO: a live é longa e veio dividida. Esta é a PARTE {parte} de {total} (de {intervalo[0]} "
                       f"a {intervalo[1]}). Marque o que sai e os capítulos SÓ desta parte (tempos do vídeo inteiro). "
                       "Título, descrição e tags podem ficar vazios: eles são pedidos no fim, com o resumo de "
                       "todas as partes.\n\n")  # fmt: skip
    return (
        f'Você vai editar o vídeo longo "{nome}" do canal FamosoZora: transformar a live bruta num episódio.\n'
        f"Duração do vídeo original: {tempo_txt(duracao)}\n\n"
        + criterios()
        + sobre_parte
        + "=== DIRETRIZES DO CANAL ===\n"
        + diretrizes.strip()
        + "\n\n=== FORMATO DA RESPOSTA ===\n"
        "Responda SÓ com um JSON válido neste formato (tempos do vídeo original, HH:MM:SS; sem texto antes ou "
        "depois):\n" + EXEMPLO + "\n\n=== TRANSCRIÇÃO ([início-fim] fala) ===\n" + transcricao
    )


def pedido_resumo(nome: str, capitulos: list, removidos: int) -> str:
    """Live dividida em partes: no fim, pede so o titulo, a descricao e as tags, com o resumo dos capitulos."""
    lista = "\n".join(f"- {c.get('tempo') or c.get('inicio')}: {c.get('titulo', '')}" for c in capitulos)
    return (
        f'Os capítulos do episódio "{nome}" (canal FamosoZora, gameplay) ficaram assim:\n{lista}\n'
        f"({removidos} trechos sem jogo foram removidos.)\n\n"
        "Escreva o título, a descrição e as tags do episódio. Título honesto e chamativo, com o objetivo do "
        "episódio; palavrão pode; se for série, cite o episódio. Descrição sem os capítulos (o Studio coloca).\n"
        'Responda SÓ com um JSON: {"titulo": "...", "descricao": "...", "titulo_en": "...", "descricao_en": "...", '
        '"opcoes_titulo": ["...", "...", "..."], "ideia_miniatura": "...", "tags": ["..."]}'
    )


# ================================================================== formato (versao 1/2 -> 3)
def para_interno(dados):
    """Qualquer versao do edicao.json -> formato de dentro do programa ("cortes", capitulos com "inicio").
    O gancho ("abertura") do video longo nao existe mais desde a 1.5.0: e descartado."""
    if not isinstance(dados, dict):
        return dados
    d = dict(dados)
    if "remover" in d:
        d["cortes"] = d.pop("remover")
    caps = []
    for c in d.get("capitulos") or []:
        if isinstance(c, dict) and "tempo" in c and "inicio" not in c:
            c = {**c, "inicio": c["tempo"]}
            c.pop("tempo")
        caps.append(c)
    if "capitulos" in d:
        d["capitulos"] = caps
    d.pop("abertura", None)
    return d


CAMPOS_AUTOEDIT = ("tipo", "video_original", "predefinicao", "introducao", "serie", "trechos", "marcadores",
                   "historico_versao_app")  # fmt: skip


def campos_novos(dados: dict) -> dict:
    """Campos da versao 3 que faltarem (Auto-Edit e editor), com o valor padrao."""
    from versao import VERSAO

    return {"tipo": dados.get("tipo") or "longo", "video_original": dados.get("video_original") or "",
            "predefinicao": dados.get("predefinicao"), "introducao": dados.get("introducao"),
            "serie": bool(dados.get("serie")), "trechos": list(dados.get("trechos") or []),
            "marcadores": list(dados.get("marcadores") or []), "historico_versao_app": VERSAO}  # fmt: skip


def para_disco(dados: dict) -> dict:
    """Formato de dentro do programa -> edicao.json versao 3 (o que vai para o arquivo)."""
    d = {k: v for k, v in dados.items() if k not in ("cortes", "abertura", "versao")}
    d.update(campos_novos(dados))
    saida = {"versao": VERSAO_EDICAO, "remover": list(dados.get("cortes") or [])}
    caps = []
    for c in dados.get("capitulos") or []:
        c = dict(c)
        if "inicio" in c:
            c = {"tempo": c.pop("inicio"), **c}
        caps.append(c)
    d["capitulos"] = caps
    saida.update(d)
    return saida


def gravar_edicao(arq: Path, dados: dict):
    """Grava o edicao.json no formato novo (versao 3)."""
    from nucleo.comum import gravar_json

    gravar_json(arq, para_disco(dados))


def migrar_arquivo(pasta: Path) -> bool:
    """edicao.json antigo (versao 1 ou 2): guarda uma copia (.bak.json) e grava na versao 3. True se migrou."""
    import shutil

    arq = Path(pasta) / "edicao.json"
    try:
        bruto = json.loads(arq.read_text(encoding="utf-8"))
    except Exception:
        return False
    if not isinstance(bruto, dict) or bruto.get("versao") == VERSAO_EDICAO:
        return False
    bak = Path(pasta) / "edicao.bak.json"
    if bak.exists():
        bak = Path(pasta) / f"edicao.v{bruto.get('versao', 1)}.bak.json"
    if not bak.exists():
        shutil.copy2(arq, bak)
    gravar_edicao(arq, para_interno(bruto))
    return True


# ================================================================== leitura e validacao
def fmt_tempo(seg: float) -> str:
    """HH:MM:SS, com decimal so se precisar (aceito pelo ler_tempo)."""
    seg = max(0.0, float(seg))
    base = tempo_txt(seg)
    resto = round(seg - int(seg), 2)
    if resto >= 0.01 and resto < 1:
        base += f"{resto:.2f}"[1:]
    return base


def extrair_json(texto: str):
    """Le o JSON vindo da area de transferencia (aceita bloco ```json ... ``` e texto em volta)."""
    t = (texto or "").strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", t, re.S)
    if m:
        t = m.group(1).strip()
    if "{" in t and "}" in t:
        t = t[t.index("{") : t.rindex("}") + 1]
    return json.loads(t)


def erro_json_amigavel(e: Exception) -> str:
    if isinstance(e, json.JSONDecodeError):
        return (
            f"O edicao.json tem um erro de formatação na linha {e.lineno}, coluna {e.colno} "
            f"({e.msg}).\nPeça pro Claude conferir e mandar de novo."
        )
    return f"Não consegui ler o edicao.json ({e}).\nPeça pro Claude conferir e mandar de novo."


def _tempo(valor, nome: str, erros: list):
    try:
        return ler_tempo(valor)
    except Exception:
        erros.append(f"{nome}: tempo inválido ({valor!r}). Use o formato 00:01:13.")
        return None


def _normalizar_cortes(dados: dict, duracao: float, dur_txt: str, erros: list, avisos: list) -> list:
    """Confere cada corte, junta os sobrepostos e devolve a lista pronta para gravar."""
    cortes = []
    brutos = dados.get("cortes", [])
    if not isinstance(brutos, list):
        erros.append('"remover" precisa ser uma lista.')
        brutos = []
    for n, c in enumerate(brutos, 1):
        if not isinstance(c, dict):
            erros.append(f"Corte {n}: formato inválido.")
            continue
        ini = _tempo(c.get("inicio"), f"Corte {n} (início)", erros)
        fim = _tempo(c.get("fim"), f"Corte {n} (fim)", erros)
        if ini is None or fim is None:
            continue
        if fim <= ini:
            erros.append(f"Corte {n}: o fim ({c.get('fim')}) vem antes do início ({c.get('inicio')}).")
            continue
        if ini < 0 or (duracao and ini >= duracao):
            erros.append(f"Corte {n}: começa em {c.get('inicio')}, fora do vídeo (o vídeo tem {dur_txt}).")
            continue
        if duracao and fim > duracao:
            if fim > duracao + 2:
                erros.append(f"Corte {n}: termina em {c.get('fim')}, depois do fim do vídeo ({dur_txt}).")
                continue
            fim = duracao
        cortes.append(
            {
                "inicio": ini,
                "fim": fim,
                "motivo": str(c.get("motivo", "")).strip(),
                "ativo": c.get("ativo", True) is not False,
            }
        )
    cortes.sort(key=lambda c: c["inicio"])
    juntos = []
    for c in cortes:
        if juntos and c["inicio"] <= juntos[-1]["fim"]:
            u = juntos[-1]
            avisos.append(
                f"Cortes sobrepostos juntados: {fmt_tempo(u['inicio'])} → {fmt_tempo(max(u['fim'], c['fim']))}."
            )
            u["fim"] = max(u["fim"], c["fim"])
            if c["motivo"] and c["motivo"] not in u["motivo"]:
                u["motivo"] = (u["motivo"] + " + " + c["motivo"]).strip(" +")
            u["ativo"] = u["ativo"] or c["ativo"]
        else:
            juntos.append(dict(c))
    prontos = []
    for c in juntos:
        item = {"inicio": fmt_tempo(c["inicio"]), "fim": fmt_tempo(c["fim"]), "motivo": c["motivo"]}
        if not c["ativo"]:
            item["ativo"] = False
        prontos.append(item)
    return prontos


def _normalizar_manter(dados: dict, duracao: float, avisos: list) -> list:
    """Momentos sem fala que o Claude quer manter (nao saem nos cortes de pausa). Item ruim so vira aviso."""
    out = []
    for n, m in enumerate(dados.get("manter") or [], 1):
        try:
            a, b = ler_tempo(m["inicio"]), ler_tempo(m["fim"])
        except (KeyError, TypeError, ValueError):
            avisos.append(f"Momento para manter {n}: tempo inválido (ignorado).")
            continue
        if b <= a or (duracao and a >= duracao):
            avisos.append(f"Momento para manter {n}: tempos errados (ignorado).")
            continue
        out.append({"inicio": fmt_tempo(a), "fim": fmt_tempo(min(b, duracao) if duracao else b),
                    "motivo": str(m.get("motivo", "")).strip()})  # fmt: skip
    return sorted(out, key=lambda m: ler_tempo(m["inicio"]))


def _normalizar_autoedit(dados: dict, duracao: float) -> dict:
    """Campos do Auto-Edit e do editor (versao 3): trechos, introducao, marcadores. Item ruim e descartado."""
    from autoedit import trechos as tr

    intro = dados.get("introducao")
    try:
        intro = {"inicio": float(intro["inicio"]), "fim": float(intro["fim"])} if intro else None
        if intro and intro["fim"] <= intro["inicio"]:
            intro = None
    except (KeyError, TypeError, ValueError):
        intro = None
    marcadores = []
    for m in dados.get("marcadores") or []:
        try:
            t = float(m["tempo"])
        except (KeyError, TypeError, ValueError):
            continue
        tipo = m.get("tipo") if m.get("tipo") in ("short", "capitulo", "nota") else "nota"
        marcadores.append({"tempo": round(t, 3), "tipo": tipo, "texto": str(m.get("texto", ""))})
    return {"trechos": tr.normalizar(dados.get("trechos"), duracao), "introducao": intro,
            "marcadores": sorted(marcadores, key=lambda m: m["tempo"])}  # fmt: skip


def _normalizar_capitulos(dados: dict, duracao: float, dur_txt: str, erros: list) -> list:
    """Confere os capitulos e devolve em ordem de tempo."""
    caps = []
    for n, c in enumerate(dados.get("capitulos", []) or [], 1):
        if not isinstance(c, dict):
            erros.append(f"Capítulo {n}: formato inválido.")
            continue
        t = _tempo(c.get("inicio"), f"Capítulo {n}", erros)
        if t is None:
            continue
        if not str(c.get("titulo", "")).strip():
            erros.append(f"Capítulo {n}: falta o título.")
            continue
        if duracao and t >= duracao:
            erros.append(f"Capítulo {n} ({c.get('inicio')}) começa depois do fim do vídeo ({dur_txt}).")
            continue
        caps.append({**c, "inicio": fmt_tempo(t)})
    caps.sort(key=lambda c: ler_tempo(c["inicio"]))
    return caps


def normalizar(dados, duracao: float):
    """Confere o edicao.json e devolve (dados_normalizados, erros, avisos).
    Cortes sobrepostos sao juntados; tempos fora do video dao erro."""
    erros, avisos = [], []
    if not isinstance(dados, dict):
        return None, ['O edicao.json precisa ser um objeto { ... } com a lista "remover".'], []
    dados = para_interno(dados)
    out = dict(dados)
    out["versao"] = VERSAO_EDICAO
    dur_txt = tempo_txt(duracao) if duracao else "?"

    out["cortes"] = _normalizar_cortes(dados, duracao, dur_txt, erros, avisos)
    out["manter"] = _normalizar_manter(dados, duracao, avisos)
    out.update(_normalizar_autoedit(dados, duracao))
    caps = out["capitulos"] = _normalizar_capitulos(dados, duracao, dur_txt, erros)

    if not str(dados.get("titulo", "")).strip():
        avisos.append("O edicao.json não tem título.")
    if not caps:
        avisos.append("O edicao.json não tem capítulos.")
    return out, erros, avisos


def ler_edicao(pasta: Path, duracao: float):
    """(dados, erros, avisos) do edicao.json da pasta."""
    arq = Path(pasta) / "edicao.json"
    if not arq.exists():
        return None, ["Esse projeto ainda não tem edicao.json."], []
    migrar_arquivo(pasta)
    try:
        bruto = json.loads(arq.read_text(encoding="utf-8"))
    except Exception as e:
        return None, [erro_json_amigavel(e)], []
    return normalizar(bruto, duracao)


# ================================================================== video
def info_video(pasta: Path):
    """(caminho do video, duracao em s). O video original so e LIDO."""
    projeto = ler_json(Path(pasta) / "projeto.json", {}) or {}
    video = Path(projeto.get("video", ""))
    dur = float(projeto.get("duracao") or 0)
    if video.exists():
        dur = duracao_video(video) or dur
    return video, dur


def fps_fracao(video: Path) -> Fraction:
    """Quadros por segundo exatos (ex.: 60 ou 30000/1001)."""
    return Fraction(fps_video(video))


# ================================================================== bordas no silencio
def carregar_palavras(pasta: Path):
    segs = (ler_json(Path(pasta) / "transcricao.json", {}) or {}).get("segmentos", [])
    pal = [(float(w["i"]), float(w["f"])) for s in segs for w in s.get("palavras", []) if "i" in w and "f" in w]
    pal.sort()
    return pal


def pausas(palavras):
    """Lista de pausas (inicio, fim) entre palavras, incluindo antes da 1a e depois da ultima."""
    out = []
    fim_ant = 0.0
    for i, f in palavras:
        if i > fim_ant:
            out.append((fim_ant, i))
        fim_ant = max(fim_ant, f)
    out.append((fim_ant, 1e9))
    return out


def ponto_silencio(t: float, lista_pausas, janela: float) -> float:
    """Leva t para o meio da pausa entre palavras mais proxima (no maximo 'janela' segundos)."""
    if janela <= 0 or not lista_pausas:
        return t
    melhor, melhor_dist = None, None
    for a, b in lista_pausas:
        if b < t - janela:
            continue
        if a > t + janela:
            break
        dist = 0.0 if a <= t <= b else min(abs(t - a), abs(t - b))
        curta = (b - a) < 0.15  # micro-pausa entre palavras emendadas: so se nao tiver outra
        chave = (curta, dist)
        if melhor is None or chave < melhor_dist:
            melhor, melhor_dist = (a, b), chave
    if melhor is None:
        return t
    a, b = melhor
    if a <= t <= b and (b - a) > 2 * janela:
        # ja esta numa pausa longa: so afasta um pouco das palavras
        return min(max(t, a + 0.25), b - 0.25)
    alvo = (a + b) / 2
    lo, hi = max(a, t - janela), min(b, t + janela)
    return min(max(alvo, lo), hi)


# ================================================================== plano do episodio
def _q(t: float, fps: Fraction) -> int:
    return int(round(Fraction(t).limit_denominator(100000) * fps))


def montar_plano(dados: dict, duracao: float, fps: Fraction, palavras=None, cfg=None, so_ativos=True, acao=None):
    """Calcula o que fica e o que sai, ja com as bordas no silencio e alinhadas aos quadros.
    Alem dos cortes do Claude, corta sozinho as pausas sem fala (videos_longos/pausas.py). acao = [(a, b)] dos
    momentos de acao do jogo (que nunca saem); None = sem medir o som do jogo.
    Retorna dict com:
      cortes  : [{n, inicio, fim, ini_aj, fim_aj, dur, motivo, ativo}]  (n = posicao no edicao.json)
      trechos : [(quadro_inicial, n_quadros)]  -> o que fica, em ordem
      secas   : posicoes em "trechos" que comecam depois de uma pausa cortada (corte seco, sem fade)
      pausas  : {"n": quantas pausas sairam, "segundos": quanto tempo elas somam}
      abertura: (quadro_inicial, n_quadros) ou None
      dur_final, dur_original, fps
    """
    cfg = cfg or carregar_config()
    janela = float(cfg.get("episodio_ajuste_silencio", 2.0) or 0)
    lp = pausas(palavras) if palavras else []
    total_q = max(1, _q(duracao, fps) - 1)  # o ultimo quadro do arquivo nem sempre sai depois da busca

    cortes = []
    for n, c in enumerate(dados.get("cortes", []), 1):
        ini, fim = ler_tempo(c["inicio"]), ler_tempo(c["fim"])
        ia = 0.0 if ini <= 0.05 else ponto_silencio(ini, lp, janela)
        fa = duracao if fim >= duracao - 0.05 else ponto_silencio(fim, lp, janela)
        if fa <= ia:
            ia, fa = ini, fim
        cortes.append(
            {
                "n": n,
                "inicio": ini,
                "fim": fim,
                "ini_aj": ia,
                "fim_aj": fa,
                "dur": fa - ia,
                "motivo": c.get("motivo", ""),
                "ativo": c.get("ativo", True) is not False,
            }
        )

    # intervalos que saem (em quadros): os do Claude (marcados) e os do Auto-Edit / editor (trechos "cortar")
    sai = []
    for c in cortes:
        if so_ativos and not c["ativo"]:
            continue
        a, b = max(0, _q(c["ini_aj"], fps)), min(total_q, _q(c["fim_aj"], fps))
        if b > a:
            sai.append((a, b, "claude"))
    resolvidos = trechos_resolvidos(dados, duracao)
    for a, b, acao_t, _ in resolvidos:
        if acao_t == "cortar":
            qa, qb = max(0, _q(a, fps)), min(total_q, _q(b, fps))
            if qb > qa:
                sai.append((qa, qb, "auto"))
    sai.sort()
    juntos = []
    for a, b, quem in sai:
        if juntos:
            ua, ub, uq = juntos[-1]
            claude = "claude" in (quem, uq)
            # sobra minuscula entre dois cortes do Claude: junta (os do Auto-Edit ja vem com as regras deles)
            if a <= ub or (claude and a - ub < TRECHO_MINIMO * fps):
                juntos[-1] = (ua, max(ub, b), "claude" if claude else "auto")
                continue
        juntos.append((a, b, quem))
    trechos, emendas, pos = [], [], 0
    for a, b, quem in juntos:
        if a > pos:
            trechos.append((pos, a - pos))
            emendas.append((quem, (b - a) / fps))  # o que saiu DEPOIS deste trecho
        pos = max(pos, b)
    if total_q - pos > 0:
        trechos.append((pos, total_q - pos))
        emendas.append(None)
    # sobra minuscula no comeco/fim do video: descarta
    if len(trechos) > 1:
        guardar = [k for k, t in enumerate(trechos) if t[1] >= TRECHO_MINIMO * fps]
        if guardar:
            trechos, emendas = [trechos[k] for k in guardar], [emendas[k] for k in guardar]
    if autoedit_ativo(dados):
        regras = regras_da_edicao(dados)
        trechos, secas, velocidades = _aplicar_autoedit(trechos, emendas, resolvidos, fps, regras)
        info_pausas = {"n": 0, "segundos": 0.0}
    else:
        regras, velocidades = None, {}
        trechos, secas, info_pausas = _cortar_pausas(trechos, dados, fps, palavras, cfg, acao)

    abertura = None
    ab = dados.get("abertura")
    if ab and cfg.get("episodio_usar_abertura", True):
        a, b = ler_tempo(ab["inicio"]), ler_tempo(ab["fim"])
        a = ponto_silencio(a, lp, min(janela, 1.0))
        b = ponto_silencio(b, lp, min(janela, 1.0))
        qa, qb = max(0, _q(a, fps)), min(total_q, _q(b, fps))
        if qb > qa:
            abertura = (qa, qb - qa)

    quadros = sum(Fraction(n) / Fraction(velocidades.get(k, 1)).limit_denominator(100) for k, (_, n) in
                  enumerate(trechos)) + (abertura[1] if abertura else 0)  # fmt: skip
    auto = [r for r in resolvidos if r[2] == "cortar"]
    return {
        "cortes": cortes,
        "trechos": trechos,
        "secas": secas,
        "velocidades": velocidades,
        "fade_audio": (float(regras["crossfade_ms"]) / 2000) if regras else None,
        "autoedit": {"n": len(auto), "segundos": round(sum(b - a for a, b, _, _ in auto), 1)},
        "pausas": info_pausas,
        "abertura": abertura,
        "fps": fps,
        "dur_original": duracao,
        "dur_final": float(quadros / fps),
    }


# ================================================================== Auto-Edit (desde a 1.9.0)
def autoedit_ativo(dados: dict) -> bool:
    """A live foi analisada (ou editada no editor novo)? Entao valem os trechos, e o corte de pausas da 1.8.0
    fica desligado (o Auto-Edit faz esse trabalho com as regras da predefinicao)."""
    return bool(dados.get("predefinicao") or dados.get("trechos"))


def regras_da_edicao(dados: dict) -> dict:
    from autoedit import predefinicoes

    return predefinicoes.da((dados.get("predefinicao") or {}).get("tipo") or dados.get("tipo") or "longo")


def protegidos_da_edicao(dados: dict) -> list:
    """[(a, b)] que sugestao automatica nao corta: a introducao do episodio e o que o Claude mandou manter."""
    out = list(momentos_para_manter(dados))
    intro = dados.get("introducao")
    if isinstance(intro, dict):
        try:
            a, b = float(intro["inicio"]), float(intro["fim"])
            if b > a:
                out.append((a, b))
        except (KeyError, TypeError, ValueError):
            pass
    return out


def trechos_resolvidos(dados: dict, duracao: float) -> list:
    """[(a, b, acao, velocidade)] do que sai ou acelera pelos trechos do Auto-Edit / editor."""
    from autoedit import trechos as tr

    lista = tr.normalizar(dados.get("trechos"), duracao)
    return tr.resolver(lista, duracao, protegidos_da_edicao(dados)) if lista else []


def _aplicar_autoedit(trechos: list, emendas: list, resolvidos: list, fps: Fraction, regras: dict) -> tuple:
    """Divide os trechos que ficam onde tem aceleracao e marca as emendas sem fade na imagem (corte seco).
    Devolve (trechos, secas, velocidades {posicao: x})."""
    grande = float(regras.get("corte_grande", 30.0))
    fade_grande = float(regras.get("fade_corte_grande", 0.2))
    acel = [(_q(a, fps), _q(b, fps), vel) for a, b, acao, vel in resolvidos if acao == "acelerar"]
    novos, secas, velocidades = [], set(), {}
    seca_proximo = False
    for (q, n), emenda in zip(trechos, emendas):
        fim_q, pos = q + n, q
        pedacos = []
        for a, b, vel in acel:
            a, b = max(a, pos), min(b, fim_q)
            if b - a < 2:
                continue
            if a > pos:
                pedacos.append((pos, a - pos, 1.0))
            pedacos.append((a, b - a, vel))
            pos = b
        if fim_q > pos:
            pedacos.append((pos, fim_q - pos, 1.0))
        for k, (pq, pn, vel) in enumerate(pedacos):
            if seca_proximo or k > 0:  # emenda de corte pequeno do Auto-Edit, ou troca de velocidade
                secas.add(len(novos))
            if vel != 1.0:
                velocidades[len(novos)] = vel
            novos.append((pq, pn))
            seca_proximo = False
        if emenda:
            quem, segundos = emenda
            seca_proximo = quem == "auto" and (segundos < grande or fade_grande <= 0)
    return novos, secas, velocidades


def momentos_para_manter(dados: dict) -> list:
    """[(a, b)] dos momentos que o Claude mandou manter (sem fala, mas importantes): nunca saem nas pausas."""
    out = []
    for m in dados.get("manter") or []:
        try:
            a, b = ler_tempo(m["inicio"]), ler_tempo(m["fim"])
        except (KeyError, TypeError, ValueError):
            continue
        if b > a:
            out.append((a, b))
    return out


def _cortar_pausas(trechos: list, dados: dict, fps: Fraction, palavras, cfg: dict, acao) -> tuple:
    """Tira as pausas sem fala de dentro de cada trecho que fica. Devolve (trechos, secas, info)."""
    from videos_longos import pausas

    info = {"n": 0, "segundos": 0.0}
    if not palavras or not trechos or not pausas.ligado(cfg, dados):
        return trechos, set(), info
    manter = momentos_para_manter(dados)
    novos, secas = [], set()
    for q, n in trechos:
        fim_q = q + n
        cortes = pausas.pausas_para_cortar(palavras, float(q / fps), float(fim_q / fps), cfg, acao or [], manter)
        pos, depois_de_pausa = q, False
        for a, b in cortes:
            qa, qb = max(pos, _q(a, fps)), min(fim_q, _q(b, fps))
            if qb - qa < 1:
                continue
            if qa > pos:
                if depois_de_pausa:
                    secas.add(len(novos))
                novos.append((pos, qa - pos))
                depois_de_pausa = True  # o proximo pedaco deste trecho comeca num corte seco
            info["n"] += 1
            info["segundos"] += float((qb - qa) / fps)
            pos = qb
        if fim_q > pos:
            if depois_de_pausa:
                secas.add(len(novos))
            novos.append((pos, fim_q - pos))
    info["segundos"] = round(info["segundos"], 1)
    return novos, secas, info


def original_para_editado(t: float, plano: dict) -> float:
    """Tempo do video original -> tempo no episodio editado (soma os trechos mantidos antes + a abertura)."""
    fps = plano["fps"]
    q = _q(t, fps)
    soma = Fraction(plano["abertura"][1] if plano["abertura"] else 0)
    velocidades = plano.get("velocidades") or {}
    for k, (a, n) in enumerate(plano["trechos"]):
        if q <= a:
            break
        soma += Fraction(min(n, q - a)) / Fraction(velocidades.get(k, 1)).limit_denominator(100)
    return float(soma / fps)


def capitulos_editados(dados: dict, plano: dict, total: float | None = None):
    """Converte os capitulos para o tempo do episodio e aplica as regras do YouTube.
    total = duracao do video final (com o outro, se tiver). Retorna (lista [(seg, titulo, titulo_en)], avisos)."""
    avisos = []
    total = plano["dur_final"] if total is None else total
    caps = []
    for c in dados.get("capitulos", []):
        t = original_para_editado(ler_tempo(c["inicio"]), plano)
        caps.append([t, str(c.get("titulo", "")).strip(), str(c.get("titulo_en", "") or "").strip()])
    caps.sort(key=lambda c: c[0])
    if not caps:
        return [], ["Sem capítulos."]
    if caps[0][0] > 0:
        caps[0][0] = 0.0  # regra do YouTube: o primeiro capitulo e sempre 0:00
    final = []
    for c in caps:
        if final and c[0] - final[-1][0] < CAPITULO_MIN:
            avisos.append(f'Capítulo "{c[1]}" ficou a menos de 10 s do anterior no episódio e foi tirado.')
            continue
        final.append(c)
    while len(final) > 1 and total - final[-1][0] < CAPITULO_MIN:
        avisos.append(f'Capítulo "{final[-1][1]}" ficou a menos de 10 s do fim e foi tirado.')
        final.pop()
    if len(final) < CAPITULOS_MIN:
        avisos.append(f"Só {len(final)} capítulo(s): o YouTube só mostra capítulos com 3 ou mais.")
    return [tuple(c) for c in final], avisos


def tempo_yt(seg: float) -> str:
    """Formato dos capitulos do YouTube: 0:00, 12:34, 1:02:03."""
    s = int(seg)
    h, m, s = s // 3600, s % 3600 // 60, s % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def metadados_capitulos(caps, total: float, titulo: str = "") -> str:
    """Arquivo FFMETADATA com os capitulos (vao dentro do .mp4)."""

    def esc(t):
        return re.sub(r"([=;#\\\n])", r"\\\1", t)

    L = [";FFMETADATA1"]
    if titulo:
        L.append(f"title={esc(titulo)}")
    for k, (t, tit, _) in enumerate(caps):
        fim = caps[k + 1][0] if k + 1 < len(caps) else total
        L += [
            "",
            "[CHAPTER]",
            "TIMEBASE=1/1000",
            f"START={int(t * 1000)}",
            f"END={int(fim * 1000)}",
            f"title={esc(tit)}",
        ]
    return "\n".join(L) + "\n"


# ================================================================== textos do episodio
def textos_episodio(dados: dict, caps, avisos_caps, arquivo: str, dur_final: float, projeto: str) -> str:
    def p(t):
        return str(t or "").replace("{canal}", CANAL_URL).replace("{link}", CANAL_URL).strip()

    def bloco_caps(en=False):
        return "\n".join(f"{tempo_yt(t)} {(ten or tit) if en else tit}" for t, tit, ten in caps)

    L = [f"TEXTOS DO EPISÓDIO - {projeto}", f"Arquivo: {arquivo}  ({tempo_txt(dur_final)})", ""]
    L += [
        "=" * 70,
        "YOUTUBE - PORTUGUÊS",
        "=" * 70,
        "[Título]",
        p(dados.get("titulo")),
        "",
        "[Descrição] (já com os capítulos)",
        p(dados.get("descricao")),
    ]
    if caps:
        L += ["", "Capítulos:", bloco_caps()]
    L.append("")
    if dados.get("titulo_en") or dados.get("descricao_en"):
        L += [
            "=" * 70,
            "YOUTUBE - INGLÊS (YouTube Studio → Idiomas → adicionar tradução)",
            "=" * 70,
            "[Title]",
            p(dados.get("titulo_en")),
            "",
            "[Description] (with chapters)",
            p(dados.get("descricao_en")),
        ]
        if caps:
            L += ["", "Chapters:", bloco_caps(en=True)]
        L.append("")
    opcoes = [o for o in dados.get("opcoes_titulo", []) or [] if str(o).strip()]
    if opcoes:
        L += ["=" * 70, "OPÇÕES DE TÍTULO", "=" * 70] + [f"{k}. {o}" for k, o in enumerate(opcoes, 1)] + [""]
    if dados.get("ideia_miniatura"):
        L += ["=" * 70, "IDEIA DA MINIATURA", "=" * 70, p(dados.get("ideia_miniatura")), ""]
    tags = dados.get("tags") or []
    if tags:
        L += ["=" * 70, "TAGS", "=" * 70, ", ".join(tags) if isinstance(tags, list) else str(tags), ""]
    if avisos_caps:
        L += ["=" * 70, "AVISOS DOS CAPÍTULOS", "=" * 70] + [f"- {a}" for a in avisos_caps] + [""]
    return "\n".join(L)
