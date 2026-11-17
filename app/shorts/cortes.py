# Le o cortes.json (escrito pelo Claude) e cuida do formato: versao, migracao automatica dos formatos antigos
# (com copia de seguranca cortes.bak.json), valores padrao dos campos novos (clima, motivo, nota, sons)
# e o teto opcional de Shorts por video ("maximo_shorts" no config.json; vazio = sem limite).
import shutil
from pathlib import Path

from nucleo.comum import gravar_json, ler_json, ler_tempo

VERSAO = 3  # 1 = lista solta; 2 = {"cortes": [...], "correcoes": {...}}; 3 = + clima, motivo, nota e sons
CLIMAS = ("engracado", "epico", "tenso", "emocionante", "calmo", "caotico")
NOTA_PADRAO = 5


def _sem_acento(t: str) -> str:
    import unicodedata

    t = unicodedata.normalize("NFD", str(t or "").strip().lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def clima_do(corte: dict) -> str:
    """'Engraçado' -> 'engracado'. Clima desconhecido ou vazio -> '' (usa a pasta geral)."""
    c = _sem_acento(corte.get("clima", "")).replace("ç", "c")
    return c if c in CLIMAS else ""


def nota_do(corte: dict) -> float:
    try:
        return max(1.0, min(10.0, float(corte.get("nota", NOTA_PADRAO))))
    except (TypeError, ValueError):
        return float(NOTA_PADRAO)


def sons_do(corte: dict) -> list:
    """Sugestoes de som do Claude que tem tempo valido (o resto e ignorado sem dar erro)."""
    out = []
    for s in corte.get("sons") or []:
        if not isinstance(s, dict):
            continue
        try:
            tempo = ler_tempo(s.get("tempo"))
        except (TypeError, ValueError):
            continue
        tipo = "musica" if str(s.get("tipo", "")).lower() == "musica" else "efeito"
        out.append({**s, "tempo": tempo, "tipo": tipo})
    return sorted(out, key=lambda s: s["tempo"])


def migrar(dados):
    """Leva qualquer formato antigo para a versao 3. Devolve (dados novos, mudou?).
    Os campos que ja existiam nao mudam; os novos sao opcionais (quem le usa os valores padrao)."""
    if isinstance(dados, list):
        return {"versao": VERSAO, "cortes": dados, "correcoes": {}}, True
    if not isinstance(dados, dict):
        return {"versao": VERSAO, "cortes": [], "correcoes": {}}, True
    novo = dict(dados)
    novo.setdefault("cortes", [])
    novo.setdefault("correcoes", {})
    mudou = novo.get("versao") != VERSAO or "cortes" not in dados
    novo["versao"] = VERSAO
    return novo, mudou


def ler_cortes(pasta: Path, gravar_migracao: bool = True):
    """O cortes.json ja na versao 3, ou None se o arquivo tem erro de formatacao (ou nao existe).
    Formato antigo: guarda cortes.bak.json (sem apagar uma copia que ja exista) e grava a versao 3."""
    arq = pasta / "cortes.json"
    dados = ler_json(arq, None)
    if dados is None:
        return None
    novo, mudou = migrar(dados)
    if mudou and gravar_migracao:
        bak = pasta / "cortes.bak.json"
        if not bak.exists():
            shutil.copy2(arq, bak)
        gravar_json(arq, novo)
    return novo


def maximo_de_shorts(cfg: dict):
    """O teto do config.json (numero > 0) ou None = sem limite. E so um teto, nunca uma meta."""
    try:
        m = int(cfg.get("maximo_shorts") or 0)
    except (TypeError, ValueError):
        return None
    return m if m > 0 else None


CAMPOS_DE_TITULO = ("titulo", "youtube_titulo", "youtube_titulo_en")


def sem_nome_do_video(titulo: str, nome_video: str) -> str:
    """Tira o nome do video quando ele vem colado no FIM do titulo: "Explodi a bike - Bully ep 4",
    "... | Bully ep 4", "... (Bully ep 4)", "... #Bully ep 4". Titulo que e so o nome do video fica como esta."""
    import re

    titulo = str(titulo or "").strip()
    nome = _sem_acento(nome_video)
    if not nome or len(nome) < 3:
        return titulo
    separador = r"\s*[\-–—|:•·#(\[]+\s*"  # precisa de um separador de verdade (so espaco nao vale)
    padrao = separador + r"\s*".join(re.escape(c) for c in nome.replace(" ", "")) + r"[\s)\]!.]*$"
    m = re.search(padrao, _sem_acento(titulo))
    if not m or not titulo[: m.start()].strip():
        return titulo
    return titulo[: m.start()].rstrip()


def limpar_titulos(cortes: list, nome_video: str) -> int:
    """Tira o nome do video do fim dos titulos de cada corte. Devolve quantos titulos mudaram."""
    mudou = 0
    for c in cortes:
        if not isinstance(c, dict):
            continue
        for campo in CAMPOS_DE_TITULO:
            if isinstance(c.get(campo), str):
                novo = sem_nome_do_video(c[campo], nome_video)
                if novo != c[campo]:
                    c[campo] = novo
                    mudou += 1
    return mudou


def descartado(corte) -> bool:
    """Corte que voce excluiu no editor ("descartado": true): nao vira Short de novo."""
    return isinstance(corte, dict) and bool(corte.get("descartado"))


def descartar_corte(pasta: Path, n: int, descartar: bool = True) -> bool:
    """Marca (ou desmarca) o corte n como descartado no cortes.json. Devolve True se achou o corte."""
    dados = ler_cortes(pasta)
    if not dados or not isinstance(dados["cortes"], list) or not 0 < n <= len(dados["cortes"]):
        return False
    corte = dados["cortes"][n - 1]
    if not isinstance(corte, dict):
        return False
    if descartar:
        corte["descartado"] = True
    else:
        corte.pop("descartado", None)
    gravar_json(pasta / "cortes.json", dados)
    return True


def escolhidos(cortes: list, maximo) -> set:
    """Numeros (1, 2, 3...) dos cortes que viram Short: todos, ou os de nota mais alta ate o teto.
    O numero do arquivo continua sendo a posicao no cortes.json (para nao baguncar o que ja foi revisado)."""
    numeros = [n for n in range(1, len(cortes) + 1) if not descartado(cortes[n - 1])]
    if maximo is None or len(numeros) <= maximo:
        return set(numeros)
    ordem = sorted(numeros, key=lambda n: (-nota_do(cortes[n - 1]), n))
    return set(ordem[:maximo])


MENSAGEM_ZERO = "Nenhum trecho forte o bastante nesse vídeo."
