# Edicao de cada Short (musica, efeitos sonoros e nome de quem fala), separada da sugestao do Claude.
# Arquivos (na pasta do projeto):
#   edicao_shorts\NN_sugestao.json  -> o que saiu da geracao (sugestao do Claude, ja com os arquivos escolhidos)
#   edicao_shorts\NN_edicao.json    -> o que voce mudou no editor (so existe se voce mexeu)
# "Restaurar sugestao do Claude" = apagar o NN_edicao.json.
# (O nome "edicao.json" solto na pasta do projeto ja e do video longo; por isso esta pasta separada.)
import copy
from pathlib import Path

from nucleo.comum import gravar_json, ler_json

PASTA = "edicao_shorts"
VERSAO = 1


def vazia(ini: float | None = None, fim: float | None = None) -> dict:
    return {
        "versao": VERSAO,
        "corte": {"inicio": ini, "fim": fim} if ini is not None else None,
        "musica": {"ligada": True, "arquivo": "", "volume": None},  # volume None = o do config.json
        "trocas_musica": [],  # [{"tempo": 30.1, "arquivo": "epico/virada.mp3"}] (tempo do Short)
        "efeitos_ligados": True,
        "efeitos": [],  # [{"tempo", "categoria", "arquivo", "volume", "motivo"}] (tempo do Short)
        "mostrar_nome_falante": False,
    }


def normalizar(dados) -> dict:
    """Completa o que faltar com os valores padrao (arquivo antigo ou escrito a mao)."""
    base = vazia()
    if not isinstance(dados, dict):
        return base
    out = copy.deepcopy(base)
    for k in base:
        if k in dados:
            out[k] = copy.deepcopy(dados[k])
    if not isinstance(out["musica"], dict):
        out["musica"] = base["musica"]
    out["musica"] = {**base["musica"], **out["musica"]}
    for k in ("efeitos", "trocas_musica"):
        out[k] = sorted(
            (
                [x for x in out[k] if isinstance(x, dict) and _numero(x.get("tempo")) is not None]
                if isinstance(out[k], list)
                else []
            ),
            key=lambda x: float(x["tempo"]),
        )
    out["efeitos_ligados"] = bool(out["efeitos_ligados"])
    out["mostrar_nome_falante"] = bool(out["mostrar_nome_falante"])
    return out


def _numero(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def arq_sugestao(pasta: Path, n: int) -> Path:
    return pasta / PASTA / f"{n:02d}_sugestao.json"


def arq_edicao(pasta: Path, n: int) -> Path:
    return pasta / PASTA / f"{n:02d}_edicao.json"


def _gravar(arq: Path, dados: dict):
    arq.parent.mkdir(exist_ok=True)
    gravar_json(arq, normalizar(dados))


def salvar_sugestao(pasta: Path, n: int, dados: dict):
    _gravar(arq_sugestao(pasta, n), dados)


def salvar_edicao(pasta: Path, n: int, dados: dict):
    _gravar(arq_edicao(pasta, n), dados)


def ler_sugestao(pasta: Path, n: int):
    d = ler_json(arq_sugestao(pasta, n), None)
    return normalizar(d) if isinstance(d, dict) else None


def ler_edicao(pasta: Path, n: int):
    d = ler_json(arq_edicao(pasta, n), None)
    return normalizar(d) if isinstance(d, dict) else None


def restaurar_sugestao(pasta: Path, n: int):
    arq_edicao(pasta, n).unlink(missing_ok=True)


def mesmo_corte(dados: dict | None, ini: float, fim: float) -> bool:
    """A edicao e deste trecho? (se voce pediu cortes novos, o Short NN pode ter virado outro trecho)"""
    c = (dados or {}).get("corte") or {}
    if c.get("inicio") is None:
        return True  # arquivo sem o trecho anotado: vale
    return abs(float(c["inicio"]) - ini) < 0.05 and abs(float(c["fim"]) - fim) < 0.05


def valendo(pasta: Path, n: int, ini: float, fim: float):
    """A edicao que vale no render: a sua (se for deste trecho), senao a sugestao, senao None."""
    for d in (ler_edicao(pasta, n), ler_sugestao(pasta, n)):
        if d is not None and mesmo_corte(d, ini, fim):
            return d
    return None
