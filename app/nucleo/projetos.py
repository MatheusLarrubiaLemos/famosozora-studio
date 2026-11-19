# Lista os projetos (um por video) da pasta de trabalho e diz em que passo cada um esta,
# tanto nos Shorts quanto no video longo.
from pathlib import Path

from nucleo.comum import PASTA_SHORTS, carregar_config, ler_json

REDES = [("youtube", "YouTube"), ("tiktok", "TikTok"), ("instagram", "Instagram")]


def redes_ativas(cfg: dict | None = None) -> list:
    """Onde voce publica hoje ("redes" no config.json; padrao: so o YouTube). Um Short conta como publicado
    quando foi publicado em todas as redes ativas."""
    cfg = cfg if cfg is not None else carregar_config()
    nomes = [r for r, _ in REDES]
    ativas = [r for r in (cfg.get("redes") or ["youtube"]) if r in nomes]
    return ativas or ["youtube"]


IGNORAR = {"ferramentas", "musicas", "__pycache__"}  # pastas antigas que nao sao projetos


def estado_episodio(p: Path) -> str:
    """'-' sem edicao.json, 'revisar' com edicao.json e sem episodio, 'ok' com o episodio gerado."""
    ep = p / "episodio"
    if ep.exists() and any(not f.name.startswith("_") for f in ep.glob("*.mp4")):
        return "ok"
    return "revisar" if (p / "edicao.json").exists() else "-"


def _passo_shorts(info: dict, cortes_com_erro: bool) -> str:
    if not info["transcrito"]:
        return "Transcrever o vídeo (passo 1)."
    if cortes_com_erro:
        return "O cortes.json está com erro de formatação: peça pro Claude conferir."
    if not info["tem_cortes"]:
        return "Pedir os cortes ao Claude (passo 2)."
    if info["n_cortes"] == 0:
        return "Nenhum trecho forte o bastante nesse vídeo (o Claude não achou corte bom). Pode pedir de novo."
    if info["limpo"] and info["n_shorts"] == 0:
        return "Projeto limpo: a mídia foi para a Lixeira e o resumo ficou guardado."
    if info["n_shorts"] < info["n_cortes"]:
        return "Gerar os Shorts (passo 3)."
    if info["postados"] < info["n_shorts"]:
        return "Revisar os Shorts (passo 4) e publicar (passo 5)."
    return "Tudo publicado! Se quiser liberar espaço: botão direito > Excluir > Só os Shorts gerados."


def _passo_longo(info: dict) -> str:
    if not info["transcrito"]:
        return "Transcrever a live (passo 2)."
    if info["episodio"] == "-":
        return "Pedir a edição ao Claude (passo 3: Editar vídeo longo)."
    if info["episodio"] == "revisar":
        if info["limpo"]:
            return "Projeto limpo: o episódio foi para a Lixeira e o resumo ficou guardado."
        return "Revisar os cortes e gerar o episódio (passo 3: Editar vídeo longo)."
    if info["projeto"].get("episodio_publicado"):
        return "Episódio publicado! Se quiser liberar espaço: botão direito > Excluir > Só o episódio gerado."
    return "Episódio gerado! Publique (botão laranja) e confira o outro no final."


def proximo_shorts(info: dict, cortes_com_erro: bool) -> str:
    """Codigo do proximo passo dos Shorts (a tela usa para escolher o botao laranja)."""
    if not info["transcrito"]:
        return "transcrever"
    if cortes_com_erro or not info["tem_cortes"] or info["n_cortes"] == 0:
        return "cortes"
    if info["n_shorts"] < info["n_cortes"] and not (info["limpo"] and info["n_shorts"] == 0):
        return "gerar"
    if info["postados"] < info["n_shorts"]:
        return "revisar"
    return "pronto"


def proximo_longo(info: dict) -> str:
    """Codigo do proximo passo do video longo."""
    if not info["transcrito"]:
        return "transcrever"
    if info["episodio"] == "-":
        return "editar"
    if info["episodio"] == "revisar":
        return "revisar"
    return "pronto" if info["projeto"].get("episodio_publicado") else "publicar"


ESTADOS = {"nao_transcrito": "não transcrito", "transcrito": "transcrito", "com_cortes": "com cortes",
           "com_shorts": "com Shorts"}  # fmt: skip


def estado_video(info: dict) -> str:
    """Codigo do estado do video (coluna "Etapa" da lista): nao_transcrito, transcrito, com_cortes ou com_shorts."""
    if info.get("n_shorts"):
        return "com_shorts"
    if not info.get("transcrito"):
        return "nao_transcrito"
    return "com_cortes" if info.get("tem_cortes") else "transcrito"


def info_projeto(p: Path, maximo=None, ativas: list | None = None) -> dict:
    """Tudo o que a lista mostra de um projeto. ativas = redes_ativas() (quem lista varios passa uma vez so)."""
    from shorts.cortes import escolhidos, ler_cortes

    cortes = ler_cortes(p, gravar_migracao=False)
    lista = cortes["cortes"] if cortes and isinstance(cortes["cortes"], list) else []
    prontos = p / "prontos"
    mp4 = [f for f in prontos.glob("*.mp4") if not f.name.startswith("_")] if prontos.exists() else []
    pub = ler_json(prontos / "publicacao.json", {}) or {}
    shorts_pub = pub.get("shorts", [])
    ativas = ativas if ativas is not None else redes_ativas()
    postados = sum(1 for s in shorts_pub if all((s.get("postado") or {}).get(r) for r in ativas))
    projeto = ler_json(p / "projeto.json", {}) or {}
    info = {
        "pasta": p,
        "nome": p.name,
        "transcrito": (p / "transcricao.json").exists(),
        "n_cortes": len(escolhidos(lista, maximo)),  # com o teto de Shorts, so os que viram Short
        "tem_cortes": cortes is not None,
        "n_shorts": len(mp4),
        "postados": postados,
        "n_pub": len(shorts_pub),
        "projeto": projeto,
        "episodio": estado_episodio(p),
        "limpo": bool(projeto.get("limpo_em")),
    }
    cortes_com_erro = (p / "cortes.json").exists() and cortes is None
    info["passo"] = _passo_shorts(info, cortes_com_erro)
    info["passo_longo"] = _passo_longo(info)
    info["proximo"] = proximo_shorts(info, cortes_com_erro)
    info["proximo_longo"] = proximo_longo(info)
    info["estado"] = estado_video(info)
    return info


def listar_projetos():
    if not PASTA_SHORTS.exists():
        return []
    pastas = [
        p
        for p in PASTA_SHORTS.iterdir()
        if p.is_dir() and p.name not in IGNORAR and ((p / "projeto.json").exists() or (p / "transcricao.json").exists())
    ]
    pastas.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    from shorts.cortes import maximo_de_shorts

    cfg = carregar_config()  # uma vez so (antes lia o config.json de novo para cada projeto, a cada 4 s)
    maximo, ativas = maximo_de_shorts(cfg), redes_ativas(cfg)
    return [info_projeto(p, maximo, ativas) for p in pastas]
