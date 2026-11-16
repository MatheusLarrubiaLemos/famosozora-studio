# Revisao das legendas de um Short: guarda a legenda original (como saiu da geracao) e a editada a mao,
# divide as palavras em linhas para o editor e encaixa o texto corrigido de volta no tempo das palavras.
# Arquivos (na pasta do projeto):  legendas\NN_original.json  e  legendas\NN_editada.json
import difflib
from pathlib import Path

from nucleo.comum import PASTA_CONFIG, gravar_json, ler_json
from shorts.censura import _norm
from shorts.pessoas import chave_voz

PALAVRAS_POR_LINHA = 10  # no maximo; a linha tambem quebra no fim da frase, na pausa e na troca de quem fala


def arq_original(pasta: Path, n: int) -> Path:
    return pasta / "legendas" / f"{n:02d}_original.json"


def arq_editada(pasta: Path, n: int) -> Path:
    return pasta / "legendas" / f"{n:02d}_editada.json"


def salvar_original(pasta: Path, n: int, arquivo: str, ini: float, fim: float, palavras: list):
    """Chamado na geracao: guarda as palavras exatamente como foram para o video."""
    (pasta / "legendas").mkdir(exist_ok=True)
    gravar_json(arq_original(pasta, n), {"n": n, "arquivo": arquivo, "inicio": ini, "fim": fim, "palavras": palavras})


def ler_original(pasta: Path, n: int):
    return ler_json(arq_original(pasta, n), None)


def ler_editada(pasta: Path, n: int):
    """{"palavras": [...], "censurar_lista": bool} ou None se esse Short nunca foi editado."""
    dados = ler_json(arq_editada(pasta, n), None)
    return dados if isinstance(dados, dict) and isinstance(dados.get("palavras"), list) else None


def salvar_editada(pasta: Path, n: int, palavras: list, censurar_lista: bool):
    (pasta / "legendas").mkdir(exist_ok=True)
    gravar_json(arq_editada(pasta, n), {"n": n, "palavras": palavras, "censurar_lista": bool(censurar_lista)})


def apagar_editada(pasta: Path, n: int):
    arq_editada(pasta, n).unlink(missing_ok=True)


# ------------------------------------------------------------------ linhas do editor
def dividir_em_linhas(palavras: list) -> list:
    """Agrupa as palavras em linhas para revisar: devolve listas de posicoes, ex.: [[0, 1, 2], [3, 4]]."""
    linhas, atual = [], []
    for k, w in enumerate(palavras):
        if atual:
            anterior = palavras[atual[-1]]
            if (
                len(atual) >= PALAVRAS_POR_LINHA
                or w["i"] - anterior["f"] > 0.6
                or chave_voz(w) != chave_voz(anterior)
                or anterior["p"][-1:] in ".!?"
            ):
                linhas.append(atual)
                atual = []
        atual.append(k)
    if atual:
        linhas.append(atual)
    return linhas


def texto_da_linha(palavras: list, posicoes: list) -> str:
    return " ".join(palavras[k]["p"] for k in posicoes)


def trocar_texto_da_linha(palavras: list, posicoes: list, texto: str) -> list:
    """Devolve a lista de palavras com o texto novo naquela linha.
    Mesma quantidade de palavras: so troca o texto e mantem o tempo de cada uma.
    Quantidade diferente: reparte o tempo da linha entre as palavras novas, pelo tamanho de cada uma."""
    novas = texto.split()
    antigas = [palavras[k] for k in posicoes]
    if len(novas) == len(antigas):
        trocadas = []
        for w, t in zip(antigas, novas):
            w2 = dict(w, p=t)
            if t != w["p"]:
                w2.pop("inc", None)  # voce conferiu essa palavra: deixa de ser "incerta"
            trocadas.append(w2)
    else:
        ini, fim = antigas[0]["i"], antigas[-1]["f"]
        pesos = [max(1, len(_norm(t))) for t in novas]
        trocadas, t0 = [], ini
        for t, peso in zip(novas, pesos):
            d = (fim - ini) * peso / sum(pesos)
            w2 = {"i": round(t0, 3), "f": round(t0 + d, 3), "p": t}
            for chave in ("s", "pessoa"):  # quem fala continua o mesmo
                if chave in antigas[0]:
                    w2[chave] = antigas[0][chave]
            trocadas.append(w2)
            t0 += d
    return palavras[: posicoes[0]] + trocadas + palavras[posicoes[-1] + 1 :]


# ------------------------------------------------------------------ sugestoes para o correcoes.txt
def sugestoes_de_correcao(originais: list, editadas: list) -> list:
    """Palavras trocadas a mao uma por uma: [(errada, certa)]. Servem de sugestao para o correcoes.txt."""
    a = [_norm(w["p"]) for w in originais]
    b = [_norm(w["p"]) for w in editadas]
    pares = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "replace" and (i2 - i1) == (j2 - j1):
            for k in range(i2 - i1):
                errada, certa = a[i1 + k], b[j1 + k]
                limpa = editadas[j1 + k]["p"].strip(".,!?;:\"'()…").lower()
                if errada and certa and errada != certa and len(errada) > 2 and (errada, limpa) not in pares:
                    pares.append((errada, limpa))
    return pares


def gravar_correcoes(pares: list) -> int:
    """Acrescenta 'errada = certa' no correcoes.txt (sem repetir). Devolve quantas entraram."""
    PASTA_CONFIG.mkdir(parents=True, exist_ok=True)
    arq = PASTA_CONFIG / "correcoes.txt"
    texto = arq.read_text(encoding="utf-8") if arq.exists() else ""
    ja_tem = {linha.split("=")[0].strip().lower() for linha in texto.splitlines() if "=" in linha}
    novas = [f"{e} = {c}" for e, c in pares if e not in ja_tem]
    if novas:
        arq.write_text(
            texto + ("" if texto.endswith("\n") or not texto else "\n") + "\n".join(novas) + "\n", encoding="utf-8"
        )
    return len(novas)
