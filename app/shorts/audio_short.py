# Audio de cada Short: monta a sugestao (musica do clima e os efeitos e trocas de musica do Claude) e transforma
# a edicao que vale (a sua ou a sugestao) na lista de arquivos e tempos que a mixagem do ffmpeg usa.
from nucleo.comum import config_compartilhada
from nucleo.video import duracao_video
from shorts import biblioteca
from shorts.cortes import clima_do, sons_do
from shorts.edicao import vazia

CFG = config_compartilhada()
_DURACOES = {}


def duracao_arquivo(arquivo) -> float:
    chave = str(arquivo)
    if chave not in _DURACOES:
        _DURACOES[chave] = duracao_video(arquivo)
    return _DURACOES[chave]


def maximo_de_efeitos() -> int:
    try:
        return max(0, int(CFG.get("maximo_efeitos", 3)))
    except (TypeError, ValueError):
        return 3


def tempo_no_short(t: float, m: dict):
    """Tempo do video original -> tempo do Short (com a abertura na frente). None se cai fora do Short.
    Se o momento esta no corte, vale o corte (a abertura costuma repetir um momento do proprio corte)."""
    abertura, D = m.get("abertura"), m.get("D", 0.0)
    inicio_do_corte = (abertura[1] - D) if abertura else 0.0
    if m["ini"] <= t < m["fim"]:
        return round(inicio_do_corte + t - m["ini"], 3)
    if abertura and abertura[0] <= t < abertura[0] + abertura[1] - D:
        return round(t - abertura[0], 3)
    return None


def sugestao(corte: dict, m: dict, musica: str, semente: str = "") -> dict:
    """O que sai da geracao para o Short: a musica do clima do corte e os sons que o Claude sugeriu
    (efeitos e trocas de musica), ja com os arquivos escolhidos e no tempo do Short."""
    ed = vazia(m["ini"], m["fim"])
    ed["musica"]["arquivo"] = musica or ""
    efeitos_disponiveis = biblioteca.listar("efeito")
    usados, limite = set(), maximo_de_efeitos()
    for k, som in enumerate(sons_do(corte)):
        t = tempo_no_short(som["tempo"], m)
        if t is None:
            print(f"   [AVISO] som em {som['tempo']:.1f}s fica fora do Short; ignorado.")
            continue
        if som["tipo"] == "musica":
            opcoes = biblioteca.opcoes_de_musica(clima_do(som) or clima_do(corte))
            arq = biblioteca.sortear(opcoes, f"{semente}-{m['n']}-troca{k}", {musica})
            if arq and arq != musica and not ed["trocas_musica"]:  # uma troca de musica por Short
                ed["trocas_musica"].append({"tempo": t, "arquivo": arq, "motivo": som.get("motivo", "")})
            continue
        cat = str(som.get("categoria", "")).strip().lower()
        arquivos = list((efeitos_disponiveis.get(cat) or {}).keys())
        if not arquivos:
            print(f"   [AVISO] categoria de efeito '{cat}' sem arquivos na pasta efeitos; ignorado.")
            continue
        if len(ed["efeitos"]) >= limite:
            print(f"   [AVISO] mais de {limite} efeitos sugeridos; fiquei com os {limite} primeiros.")
            break
        arq = biblioteca.sortear(arquivos, f"{semente}-{m['n']}-{k}", usados)
        usados.add(arq)
        ed["efeitos"].append({"tempo": t, "categoria": cat, "arquivo": arq, "volume": None,
                              "motivo": som.get("motivo", "")})  # fmt: skip
    return ed


def para_mixagem(ed: dict, total: float) -> dict:
    """Edicao -> {"faixas", "volume", "efeitos", "avisos"} com os arquivos de verdade (os que sumiram viram aviso)."""
    avisos, faixas, efeitos = [], [], []
    mus = ed.get("musica") or {}
    if mus.get("ligada", True):
        if not mus.get("arquivo"):
            avisos.append("sem musica: nao achei nenhuma na pasta do clima nem em geral (o Short sai sem musica)")
        else:
            arq = biblioteca.caminho("musica", mus["arquivo"])
            if arq:
                faixas.append({"arquivo": arq, "inicio": 0.0, "dur": duracao_arquivo(arq)})
            else:
                avisos.append(f"a musica {mus['arquivo']} nao esta mais na pasta (o Short sai sem musica)")
        if faixas:
            for troca in ed.get("trocas_musica") or []:
                t = float(troca["tempo"])
                arq = biblioteca.caminho("musica", troca.get("arquivo", ""))
                if not arq:
                    avisos.append(f"troca de musica em {t:.1f}s: arquivo {troca.get('arquivo')} nao encontrado")
                elif 0.5 < t < total - 1.0:
                    faixas.append({"arquivo": arq, "inicio": t, "dur": duracao_arquivo(arq)})
    if ed.get("efeitos_ligados", True):
        for e in ed.get("efeitos") or []:
            arq = biblioteca.caminho("efeito", e.get("arquivo", ""))
            if not arq:
                avisos.append(
                    f"efeito em {float(e['tempo']):.1f}s: arquivo {e.get('arquivo') or '(nenhum)'} nao encontrado"
                )
                continue
            vol = e.get("volume")
            vol = float(CFG.get("volume_efeitos", 0.8)) if vol is None else float(vol)
            efeitos.append({"arquivo": arq, "tempo": float(e["tempo"]), "volume": vol})
    return {"faixas": faixas, "volume": mus.get("volume"), "efeitos": efeitos, "avisos": avisos}
