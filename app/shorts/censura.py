# Censura das legendas: troca palavras por "p***" e, se ligado no config, cala ou poe um bip no audio.
# A censura e uma escolha por Short (as diretrizes do canal permitem palavrao): nada e censurado sozinho.
#   - lista: censura.txt (uma palavra ou expressao por linha), usada so nos Shorts em que voce ligar;
#   - palavra avulsa: marcada no editor de legendas, vale so para aquele Short.
import re
import unicodedata

from nucleo.comum import PASTA_CONFIG, PASTA_PADRAO, _linhas_uteis, _sem_repetir

ARQUIVO = "censura.txt"


def _norm(p: str) -> str:
    """Minusculas, sem acento e sem pontuacao (para comparar palavras)."""
    p = unicodedata.normalize("NFD", p.lower())
    p = "".join(c for c in p if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", p)


def ler_censura() -> list:
    """Lista de censura: cada item e uma lista de palavras normalizadas (expressoes tem mais de uma)."""
    itens = []
    for arq in _sem_repetir(PASTA_PADRAO / ARQUIVO, PASTA_CONFIG / ARQUIVO):
        for linha in _linhas_uteis(arq):
            partes = [_norm(t) for t in linha.split()]
            partes = [t for t in partes if t]
            if partes and partes not in itens:
                itens.append(partes)
    return itens


def adicionar_a_lista(palavra: str) -> bool:
    """Grava a palavra (ou expressao) no censura.txt deste PC. Devolve False se ja estava na lista."""
    partes = [t for t in (_norm(t) for t in palavra.split()) if t]
    if not partes or partes in ler_censura():
        return False
    PASTA_CONFIG.mkdir(parents=True, exist_ok=True)
    arq = PASTA_CONFIG / ARQUIVO
    antes = arq.read_text(encoding="utf-8") if arq.exists() else ""
    limpa = " ".join(re.sub(r"^\W+|\W+$", "", t) for t in palavra.split()).lower()
    arq.write_text(antes + ("" if antes.endswith("\n") or not antes else "\n") + limpa + "\n", encoding="utf-8")
    return True


def mascarar(palavra: str) -> str:
    """'porra!' -> 'p***!' (mantem a pontuacao em volta)."""
    m = re.match(r"^(\W*)(.*?)(\W*)$", palavra, re.S)
    miolo = m.group(2)
    if not miolo:
        return palavra
    return f"{m.group(1)}{miolo[0]}***{m.group(3)}"


def indices_da_lista(palavras: list, lista: list) -> set:
    """Posicoes das palavras que batem com a lista de censura (expressoes contam todas as palavras delas)."""
    normal = [_norm(w["p"]) for w in palavras]
    achados = set()
    for item in lista:
        n = len(item)
        for k in range(len(normal) - n + 1):
            if normal[k : k + n] == item:
                achados.update(range(k, k + n))
    return achados


def aplicar(palavras: list, usar_lista: bool) -> list:
    """Devolve uma copia das palavras com as censuradas mascaradas e marcadas com "c": True.
    Censura: as marcadas a mao no editor ("cx") e, se usar_lista, as que estao no censura.txt."""
    da_lista = indices_da_lista(palavras, ler_censura()) if usar_lista else set()
    out = []
    for k, w in enumerate(palavras):
        w = dict(w)
        if w.get("cx") or k in da_lista:
            w["p"] = mascarar(w["p"])
            w["c"] = True
        out.append(w)
    return out


def trechos_para_calar(blocos) -> list:
    """Intervalos (no tempo do Short) das palavras censuradas, com uma pequena folga, ja juntando os vizinhos."""
    trechos = []
    for offset, palavras, _ in blocos:
        for w in palavras:
            if w.get("c"):
                a, b = max(0.0, offset + w["i"] - 0.04), offset + w["f"] + 0.04
                if trechos and a <= trechos[-1][1]:
                    trechos[-1] = (trechos[-1][0], max(trechos[-1][1], b))
                else:
                    trechos.append((a, b))
    return trechos
