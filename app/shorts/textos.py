# Textos para postar cada Short (YouTube, TikTok, Instagram): publicacao.json e textos_para_postar.txt.
from datetime import datetime
from pathlib import Path

from nucleo.comum import CANAL_URL, gravar_json, ler_json


def textos_do_corte(c: dict) -> dict:
    hashtags = c.get("hashtags", [])
    tags_txt = " ".join(hashtags) if isinstance(hashtags, list) else str(hashtags or "")
    desc = c.get("descricao", "")
    yt_desc = c.get("youtube_descricao") or "\n\n".join(
        x for x in [desc, "▶ Vídeo completo no canal: {link}", tags_txt] if x
    )
    tiktok = c.get("tiktok") or "\n\n".join(x for x in [desc, tags_txt] if x)
    return {
        "youtube": {
            "titulo": c.get("youtube_titulo") or c.get("titulo", ""),
            "descricao": yt_desc,
            "tags": c.get("tags", []),
            # ingles: no YouTube Studio, "Idiomas" -> adicionar titulo/descricao traduzidos
            "titulo_en": c.get("youtube_titulo_en", ""),
            "descricao_en": c.get("youtube_descricao_en", ""),
        },
        "tiktok": tiktok,
        "instagram": c.get("instagram") or tiktok,
    }


def preencher(t: str, link: str) -> str:
    return t.replace("{link}", link).replace("{canal}", CANAL_URL)


def salvar_publicacao(pasta: Path, saida: Path, itens, projeto: dict):
    arq = saida / "publicacao.json"
    antigo = ler_json(arq, {}) or {}
    postado_antes = {s.get("arquivo"): s.get("postado", {}) for s in antigo.get("shorts", [])}
    shorts = []
    for n, nome, c, dur in itens:
        shorts.append(
            {
                "n": n,
                "arquivo": nome,
                "duracao": round(dur, 1),
                "textos": textos_do_corte(c),
                "postado": postado_antes.get(nome, {"youtube": False, "tiktok": False, "instagram": False}),
            }
        )
    gravar_json(
        arq, {"projeto": pasta.name, "atualizado": datetime.now().isoformat(timespec="seconds"), "shorts": shorts}
    )

    link = projeto.get("link_video_completo") or CANAL_URL
    with open(saida / "textos_para_postar.txt", "w", encoding="utf-8") as f:
        f.write(f"TEXTOS PARA POSTAR - {pasta.name}\n(link do video completo: {link})\n\n")
        for s in shorts:
            t = s["textos"]
            f.write("=" * 70 + f"\n{s['arquivo']}  ({s['duracao']}s)\n" + "=" * 70 + "\n")
            f.write(f"[YOUTUBE] Titulo:\n{t['youtube']['titulo']}\n\n")
            f.write(f"[YOUTUBE] Descricao:\n{preencher(t['youtube']['descricao'], link)}\n\n")
            if t["youtube"]["tags"]:
                f.write(f"[YOUTUBE] Tags:\n{', '.join(t['youtube']['tags'])}\n\n")
            if t["youtube"].get("titulo_en"):
                f.write(f"[YOUTUBE - INGLES] Titulo:\n{t['youtube']['titulo_en']}\n\n")
            if t["youtube"].get("descricao_en"):
                f.write(f"[YOUTUBE - INGLES] Descricao:\n{preencher(t['youtube']['descricao_en'], link)}\n\n")
            f.write(f"[TIKTOK]:\n{preencher(t['tiktok'], link)}\n\n")
            f.write(f"[INSTAGRAM]:\n{preencher(t['instagram'], link)}\n\n")
