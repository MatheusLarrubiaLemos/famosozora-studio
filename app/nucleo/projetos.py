# Lista os projetos (um por video) da pasta de trabalho e diz em que passo cada um esta.
from pathlib import Path

from nucleo.comum import PASTA_SHORTS, ler_json

REDES = [("youtube", "YouTube"), ("tiktok", "TikTok"), ("instagram", "Instagram")]


IGNORAR = {"ferramentas", "musicas", "__pycache__"}


def info_projeto(p: Path) -> dict:
    cortes = ler_json(p / "cortes.json", None)
    lista = (cortes.get("cortes", []) if isinstance(cortes, dict) else cortes) if cortes else []
    prontos = p / "prontos"
    mp4 = [f for f in prontos.glob("*.mp4") if not f.name.startswith("_")] if prontos.exists() else []
    pub = ler_json(prontos / "publicacao.json", {}) or {}
    shorts_pub = pub.get("shorts", [])
    postados = sum(1 for s in shorts_pub if all(s.get("postado", {}).get(r) for r, _ in REDES))
    info = {
        "pasta": p,
        "nome": p.name,
        "transcrito": (p / "transcricao.json").exists(),
        "n_cortes": len(lista),
        "tem_cortes": cortes is not None,
        "n_shorts": len(mp4),
        "postados": postados,
        "n_pub": len(shorts_pub),
        "projeto": ler_json(p / "projeto.json", {}) or {},
        "episodio": estado_episodio(p),
    }
    if not info["transcrito"]:
        passo = "Transcrever o vídeo (passo 1)."
    elif not info["tem_cortes"]:
        passo = "Pedir os cortes ao Claude (passo 2)."
    elif info["n_shorts"] < info["n_cortes"]:
        passo = "Gerar os Shorts (passo 3)."
    elif info["postados"] < info["n_shorts"]:
        passo = "Publicar no YouTube, TikTok e Instagram pelo Buffer (passo 4)."
    else:
        passo = "Tudo postado! Bora pro próximo vídeo."
    info["passo"] = passo
    return info


def estado_episodio(p: Path) -> str:
    """'-' sem edicao.json, 'revisar' com edicao.json e sem episodio, 'ok' com o episodio gerado."""
    ep = p / "episodio"
    if ep.exists() and any(not f.name.startswith("_") for f in ep.glob("*.mp4")):
        return "ok"
    return "revisar" if (p / "edicao.json").exists() else "-"


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
