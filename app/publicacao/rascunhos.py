# Rascunhos de publicacao: o que vai para a tela de revisao antes de voce clicar em Confirmar.
# Os textos vem do que o Claude ja escreveu (publicacao.json dos Shorts, edicao.json do video longo);
# o horario vem da fila (Shorts: 12:00 de Brasilia, um por dia, depois dos que ja estao agendados).
# Tambem marca no projeto o que ja foi agendado (para a lista mostrar "Publicados 2/5").
from pathlib import Path

from nucleo.comum import CANAL_URL, carregar_config, gravar_json, ler_ajustes, ler_json
from publicacao import fila
from publicacao.horario import HORA_SHORTS, proximos_dias_livres


def _pub(pasta: Path) -> dict:
    return ler_json(pasta / "prontos" / "publicacao.json", {}) or {}


def _tags(valor) -> list:
    if isinstance(valor, str):
        valor = valor.split(",")
    return [str(t).strip().lstrip("#") for t in (valor or []) if str(t).strip()]


def _preencher(texto, link: str) -> str:
    return str(texto or "").replace("{link}", link).replace("{canal}", CANAL_URL)


def shorts_prontos(info: dict) -> list:
    """Numeros dos Shorts que existem, ainda nao foram publicados e nao estao na fila."""
    pasta = info["pasta"]
    prontos = []
    for s in _pub(pasta).get("shorts", []):
        video = pasta / "prontos" / s.get("arquivo", "")
        if video.is_file() and not (s.get("postado") or {}).get("youtube") and not fila.na_fila(video):
            prontos.append(s["n"])
    return prontos


def rascunhos_de_shorts(info: dict, numeros: list, ocupados=None) -> list:
    """Um rascunho (item da fila ainda nao gravado) para cada Short, com o proximo dia livre de cada um."""
    pasta = info["pasta"]
    projeto = ler_json(pasta / "projeto.json", {}) or {}
    link = projeto.get("link_video_completo") or CANAL_URL
    cfg = carregar_config()
    hora = str(cfg.get("publicar_shorts_hora") or HORA_SHORTS)
    shorts = {s["n"]: s for s in _pub(pasta).get("shorts", [])}
    escolhidos = [shorts[n] for n in numeros if n in shorts]
    ocupados = fila.horarios_de_shorts() if ocupados is None else list(ocupados)
    horarios = proximos_dias_livres(ocupados, len(escolhidos), hora)
    playlist = ler_ajustes().get("ultima_playlist_short", "")
    saida = []
    for s, quando in zip(escolhidos, horarios):
        yt = (s.get("textos") or {}).get("youtube") or {}
        item = fila.novo_item("short", pasta.name, pasta / "prontos" / s["arquivo"],
                              (yt.get("titulo") or Path(s["arquivo"]).stem)[:100], quando)  # fmt: skip
        item.update(n=s["n"], descricao=_preencher(yt.get("descricao"), link), tags=_tags(yt.get("tags")),
                    titulo_en=yt.get("titulo_en", ""), descricao_en=_preencher(yt.get("descricao_en"), link),
                    playlist=playlist)  # fmt: skip
        saida.append(item)
    return saida


def episodio_do_projeto(pasta: Path):
    """O arquivo do episodio gerado (video longo), ou None."""
    ep = pasta / "episodio"
    nome = (ler_json(ep / "episodio.json", {}) or {}).get("arquivo")
    arq = ep / nome if nome else None
    return arq if arq and arq.is_file() else None


def rascunho_longo(info: dict) -> dict | None:
    """Rascunho do video longo: titulo, descricao com os capitulos (no tempo do episodio), tags e o horario
    sugerido. None se o episodio ainda nao foi gerado."""
    from publicacao.horario import sugestao_longo
    from videos_longos.pedido_edicao import para_interno, tempo_yt

    pasta = info["pasta"]
    arq = episodio_do_projeto(pasta)
    if not arq:
        return None
    ep = ler_json(pasta / "episodio" / "episodio.json", {}) or {}
    dados = para_interno(ler_json(pasta / "edicao.json", {}) or {})
    caps = ep.get("capitulos") or []

    def com_capitulos(texto, chave="titulo"):
        linhas = [f"{tempo_yt(float(c['inicio']))} {c.get(chave) or c.get('titulo', '')}" for c in caps]
        partes = [str(texto or "").strip()] + (["\n".join(linhas)] if len(linhas) >= 3 else [])
        return "\n\n".join(p for p in partes if p)

    item = fila.novo_item("longo", pasta.name, arq, str(dados.get("titulo") or pasta.name)[:100],
                          sugestao_longo(carregar_config()))  # fmt: skip
    item.update(descricao=com_capitulos(dados.get("descricao")), tags=_tags(dados.get("tags")),
                titulo_en=str(dados.get("titulo_en") or ""),
                descricao_en=com_capitulos(dados.get("descricao_en"), "titulo_en") if dados.get("descricao_en") else "",
                playlist=ler_ajustes().get("ultima_playlist_longo", ""))  # fmt: skip
    return item


def marcar_no_projeto(item: dict):
    """Item agendado/publicado: anota no publicacao.json do projeto (Short) ou no projeto.json (video longo)."""
    from nucleo.comum import PASTA_SHORTS

    pasta = PASTA_SHORTS / item["projeto"]
    if item["tipo"] == "short":
        arq = pasta / "prontos" / "publicacao.json"
        pub = ler_json(arq, None)
        if not isinstance(pub, dict):
            return
        for s in pub.get("shorts", []):
            if s.get("n") == item.get("n") or s.get("arquivo") == Path(item["video"]).name:
                s.setdefault("postado", {})["youtube"] = True
                s["agendado_para"] = item["horario"]
                s["link_youtube"] = item.get("link", "")
        gravar_json(arq, pub)
    else:
        arq = pasta / "projeto.json"
        projeto = ler_json(arq, {}) or {}
        projeto["episodio_publicado"] = {"horario": item["horario"], "link": item.get("link", "")}
        if item.get("link") and not projeto.get("link_video_completo"):
            projeto["link_video_completo"] = item["link"]  # os Shorts passam a apontar para o video longo
        gravar_json(arq, projeto)
