# Fila de publicacao: tudo o que foi mandado (ou vai ser mandado) para o YouTube, com horario e situacao.
# Fica em <pasta de trabalho>\configuracoes\fila_publicacao.json e sobrevive a fechar o app: ao abrir de novo,
# o Studio confere os pacotes e continua de onde parou.
# Situacoes (status) de cada item:
#   na fila   -> confirmado por voce, ainda nao foi para o Claude
#   enviando  -> o pedido foi para o Claude; esperando ele avisar (resultado.json no pacote)
#   agendado  -> o Claude agendou no YouTube Studio (tem o link)
#   publicado -> o horario passou: o video ja esta no ar
#   erro      -> deu errado (o motivo fica em "erro"); da para mandar de novo
import json
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from nucleo.comum import PASTA_FILA, gravar_json, ler_json
from publicacao.horario import agora, em_brasilia, iso

VERSAO = 1
STATUS = ("na fila", "enviando", "agendado", "publicado", "erro")
ATIVOS = ("na fila", "enviando", "agendado")  # ainda nao estao no ar
SEM_RESPOSTA_HORAS = 12  # "enviando" ha mais tempo que isso, sem resposta do Claude, vira erro


def arquivo() -> Path:
    return PASTA_FILA / "fila_publicacao.json"


def migrar(dados) -> tuple:
    """Leva o arquivo para a versao atual. Devolve (dados, mudou?)."""
    if isinstance(dados, list):  # nunca existiu, mas se alguem gravar so a lista, aproveita
        return {"versao": VERSAO, "itens": dados}, True
    if not isinstance(dados, dict):
        return {"versao": VERSAO, "itens": []}, True
    novo = dict(dados)
    novo.setdefault("itens", [])
    mudou = novo.get("versao") != VERSAO
    novo["versao"] = VERSAO
    return novo, mudou


def ler() -> dict:
    arq = arquivo()
    dados = ler_json(arq, None)
    if dados is None:
        if arq.exists():  # arquivo estragado: guarda uma copia e comeca uma fila nova
            arq.replace(arq.with_suffix(".estragado.json"))
        return {"versao": VERSAO, "itens": []}
    novo, mudou = migrar(dados)
    if mudou:
        bak = arq.with_suffix(".bak.json")
        if not bak.exists():
            bak.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
        gravar(novo)
    return novo


def gravar(dados: dict):
    """Grava num arquivo temporario e troca de uma vez (se o PC desligar no meio, a fila antiga fica)."""
    arq = arquivo()
    arq.parent.mkdir(parents=True, exist_ok=True)
    temp = arq.with_suffix(".gravando")
    gravar_json(temp, dados)
    os.replace(temp, arq)


def itens() -> list:
    return ler()["itens"]


def novo_item(tipo: str, projeto: str, video: Path, titulo: str, horario, **extra) -> dict:
    """Item novo (ainda nao gravado). tipo: 'short' ou 'longo'."""
    agora_txt = datetime.now().isoformat(timespec="seconds")
    item = {"id": uuid.uuid4().hex[:10], "tipo": tipo, "projeto": projeto, "video": str(video), "titulo": titulo,
            "descricao": "", "tags": [], "playlist": "", "horario": iso(horario), "caminho": "claude",
            "status": "na fila", "link": "", "erro": "", "pacote": "", "criado_em": agora_txt,
            "atualizado_em": agora_txt}  # fmt: skip
    item.update(extra)
    return item


def adicionar(novos: list) -> list:
    dados = ler()
    dados["itens"].extend(novos)
    gravar(dados)
    return novos


def atualizar(id_: str, **campos) -> dict | None:
    dados = ler()
    for item in dados["itens"]:
        if item["id"] == id_:
            item.update(campos)
            item["atualizado_em"] = datetime.now().isoformat(timespec="seconds")
            gravar(dados)
            return item
    return None


def remover(id_: str) -> bool:
    dados = ler()
    antes = len(dados["itens"])
    dados["itens"] = [i for i in dados["itens"] if i["id"] != id_]
    gravar(dados)
    return len(dados["itens"]) < antes


def pegar(id_: str) -> dict | None:
    return next((i for i in itens() if i["id"] == id_), None)


def ordenados() -> list:
    return sorted(itens(), key=lambda i: i.get("horario") or "")


def proximos() -> list:
    """O que ainda vai sair (na fila, enviando ou agendado), do mais cedo para o mais tarde."""
    return [i for i in ordenados() if i["status"] in ATIVOS]


def horarios_de_shorts() -> list:
    """Horarios ja ocupados por Shorts (menos os que deram erro): para o calculo do proximo dia livre."""
    return [em_brasilia(i["horario"]) for i in itens() if i["tipo"] == "short" and i["status"] != "erro"]


def na_fila(video: Path) -> dict | None:
    """O item ativo (ainda nao publicado) deste video, se tiver."""
    alvo = str(video)
    return next((i for i in itens() if i["video"] == alvo and i["status"] in ATIVOS), None)


def pendentes_em(caminhos) -> list:
    """Itens ainda nao publicados cujo video e um destes caminhos ou esta dentro de uma destas pastas."""
    caminhos = [Path(c) for c in caminhos]
    achados = []
    for item in itens():
        if item["status"] not in ATIVOS:
            continue
        video = Path(item["video"])
        if any(video == c or c in video.parents for c in caminhos):
            achados.append(item)
    return achados


def ler_resultado(pacote: str):
    """O resultado.json que o Claude grava no pacote quando termina: {"status": "agendado", "link": ...}."""
    if not pacote:
        return None
    dados = ler_json(Path(pacote) / "resultado.json", None)
    return dados if isinstance(dados, dict) and dados.get("status") else None


def conferir(referencia: datetime | None = None) -> list:
    """Atualiza a situacao de cada item: le o resultado.json dos pacotes, marca como publicado o que ja passou
    do horario e como erro o que ficou sem resposta. Devolve [(item, situacao anterior)] do que mudou."""
    dados = ler()
    ref = em_brasilia(referencia) if referencia else agora()
    mudados = []
    for item in dados["itens"]:
        antes = item["status"]
        if item["status"] in ("na fila", "enviando", "erro"):
            r = ler_resultado(item.get("pacote", ""))
            if r and str(r["status"]).lower() in ("agendado", "publicado"):
                item["status"] = "agendado"
                item["link"] = str(r.get("link") or item.get("link") or "")
                item["erro"] = ""
            elif r and str(r["status"]).lower() == "erro" and item["status"] == "enviando":
                item["status"] = "erro"
                item["erro"] = str(r.get("motivo") or r.get("erro") or "o Claude avisou que deu erro")
            elif item["status"] == "enviando" and item.get("enviado_em"):
                enviado = datetime.fromisoformat(item["enviado_em"])
                if datetime.now() - enviado > timedelta(hours=SEM_RESPOSTA_HORAS):
                    item["status"] = "erro"
                    item["erro"] = "o Claude não respondeu (o resultado.json não apareceu). Confira no YouTube Studio."
        if item["status"] == "agendado" and em_brasilia(item["horario"]) <= ref:
            item["status"] = "publicado"
        if item["status"] != antes:
            item["atualizado_em"] = datetime.now().isoformat(timespec="seconds")
            mudados.append((dict(item), antes))
    if mudados:
        gravar(dados)
    return mudados
