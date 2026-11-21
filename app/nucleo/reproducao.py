# Contas do player embutido (interface/player.py), separadas da tela para dar para testar sem abrir janela:
#   - quais pedacos do video original ficam no episodio (para o player "pular o que sai" e mostrar como fica);
#   - para onde pular quando o tempo cai num pedaco que sai;
#   - em qual linha da legenda o video esta agora (para a lista acompanhar o video).
from bisect import bisect_right


def mantidos_do_plano(plano: dict | None) -> list:
    """[(inicio, fim)] em segundos do video original: o que fica no episodio (cortes do Claude e pausas ja tirados).
    Sem plano: lista vazia (o player toca tudo)."""
    if not plano or not plano.get("trechos"):
        return []
    fps = float(plano["fps"])
    return [(a / fps, (a + n) / fps) for a, n in plano["trechos"] if n > 0]


def pulo(t: float, mantidos: list, folga: float = 0.04):
    """Se o tempo t cai num pedaco que SAI, devolve o tempo para onde pular (o comeco do proximo pedaco que fica).
    Se t esta num pedaco que fica, devolve None. Depois do ultimo pedaco: devolve o fim dele (o player para la).
    folga: o finzinho de cada pedaco conta como "fica" (o player confere o tempo algumas vezes por segundo)."""
    if not mantidos:
        return None
    inicios = [a for a, _ in mantidos]
    k = bisect_right(inicios, t + folga) - 1
    if k >= 0 and t < mantidos[k][1] - folga:
        return None
    if k + 1 < len(mantidos):
        return mantidos[k + 1][0]
    return mantidos[-1][1] if t < mantidos[-1][1] + 1 else None


def situacao(t: float, cortes: list, mantidos: list) -> tuple:
    """O que acontece com o tempo t no episodio: ("fica", None), ("sai", n do trecho do Claude) ou ("pausa", None).
    cortes = plano["cortes"] (so os ativos contam)."""
    for c in cortes or []:
        if c.get("ativo", True) and c["ini_aj"] <= t < c["fim_aj"]:
            return "sai", c["n"]
    if mantidos and pulo(t, mantidos, folga=0) is not None:
        return "pausa", None
    return "fica", None


def linha_no_tempo(inicios: list, fins: list, t: float):
    """Indice da linha da legenda que esta passando no tempo t (ou a ultima que ja comecou). None antes da 1a."""
    k = bisect_right(inicios, t) - 1
    if k < 0:
        return None
    return k


def dentro_da_linha(inicios: list, fins: list, t: float):
    """Como linha_no_tempo, mas so devolve a linha se o tempo t estiver DENTRO dela (para mostrar a legenda)."""
    k = linha_no_tempo(inicios, fins, t)
    if k is None or t > fins[k]:
        return None
    return k


def limitar(t: float, ini: float | None, fim: float | None) -> float:
    """Prende o tempo t entre ini e fim (qualquer um dos dois pode ser None = sem limite)."""
    if ini is not None:
        t = max(ini, t)
    if fim is not None:
        t = min(fim, t)
    return max(0.0, t)


def texto_do_tempo(t: float, com_decimo: bool = True) -> str:
    """1:02:03.4 / 2:03.4 (sem horas quando nao precisa): o relogio do player."""
    t = max(0.0, float(t or 0))
    h, resto = divmod(t, 3600)
    m, s = divmod(resto, 60)
    seg = f"{s:04.1f}" if com_decimo else f"{int(s):02d}"
    return f"{int(h)}:{int(m):02d}:{seg}" if h >= 1 else f"{int(m)}:{seg}"
