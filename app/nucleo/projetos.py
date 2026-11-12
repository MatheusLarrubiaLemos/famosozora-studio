# Lista os projetos (um por video) da pasta de trabalho e diz em que passo cada um esta,
# tanto nos Shorts quanto no video longo.
from pathlib import Path

from nucleo.comum import PASTA_SHORTS, ler_json

REDES = [("youtube", "YouTube"), ("tiktok", "TikTok"), ("instagram", "Instagram")]
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
    if info["limpo"] and info["n_shorts"] == 0:
        return "Projeto limpo: a mídia foi para a Lixeira e o resumo ficou guardado."
    if info["n_shorts"] < info["n_cortes"]:
        return "Gerar os Shorts (passo 3)."
    if info["postados"] < info["n_shorts"]:
        return "Publicar no YouTube, TikTok e Instagram pelo Buffer (passo 4)."
    return "Tudo postado! Pode limpar o projeto."


def _passo_longo(info: dict) -> str:
    if not info["transcrito"]:
        return "Transcrever a live (passo 2)."
    if info["episodio"] == "-":
        return "Pedir a edição ao Claude (passo 3: Editar vídeo longo)."
    if info["episodio"] == "revisar":
        if info["limpo"]:
            return "Projeto limpo: o episódio foi para a Lixeira e o resumo ficou guardado."
        return "Revisar os cortes e gerar o episódio (passo 3: Editar vídeo longo)."
    return "Episódio gerado! Poste e depois limpe o projeto."


def info_projeto(p: Path) -> dict:
    cortes = ler_json(p / "cortes.json", None)
    lista = (cortes.get("cortes", []) if isinstance(cortes, dict) else cortes) if cortes else []
    prontos = p / "prontos"
    mp4 = [f for f in prontos.glob("*.mp4") if not f.name.startswith("_")] if prontos.exists() else []
    pub = ler_json(prontos / "publicacao.json", {}) or {}
    shorts_pub = pub.get("shorts", [])
    postados = sum(1 for s in shorts_pub if all(s.get("postado", {}).get(r) for r, _ in REDES))
    projeto = ler_json(p / "projeto.json", {}) or {}
    info = {
        "pasta": p,
        "nome": p.name,
        "transcrito": (p / "transcricao.json").exists(),
        "n_cortes": len(lista),
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
    return [info_projeto(p) for p in pastas]
