# Audio de cada Short: monta a sugestao (musica do clima e, na Fase 4, os efeitos do Claude) e transforma
# a edicao que vale (a sua ou a sugestao) na lista de arquivos e tempos que a mixagem do ffmpeg usa.
from nucleo.comum import config_compartilhada
from nucleo.video import duracao_video
from shorts import biblioteca
from shorts.edicao import vazia

CFG = config_compartilhada()
_DURACOES = {}


def duracao_arquivo(arquivo) -> float:
    chave = str(arquivo)
    if chave not in _DURACOES:
        _DURACOES[chave] = duracao_video(arquivo)
    return _DURACOES[chave]


def sugestao(corte: dict, m: dict, musica: str) -> dict:
    """O que sai da geracao para o Short: a musica escolhida para o clima do corte."""
    ed = vazia(m["ini"], m["fim"])
    ed["musica"]["arquivo"] = musica or ""
    return ed


def para_mixagem(ed: dict, total: float) -> dict:
    """Edicao -> {"faixas", "volume", "efeitos", "avisos"} com os arquivos de verdade (os que sumiram viram aviso)."""
    avisos, faixas, efeitos = [], [], []
    mus = ed.get("musica") or {}
    if mus.get("ligada", True):
        if not mus.get("arquivo"):
            avisos.append("sem musica: nao achei nenhuma na pasta do clima nem em geral (o Short sai sem musica)")
        else:
            arq = biblioteca.caminho("musica", mus["arquivo"])
            if arq:
                faixas.append({"arquivo": arq, "inicio": 0.0, "dur": duracao_arquivo(arq)})
            else:
                avisos.append(f"a musica {mus['arquivo']} nao esta mais na pasta (o Short sai sem musica)")
        if faixas:
            for troca in ed.get("trocas_musica") or []:
                t = float(troca["tempo"])
                arq = biblioteca.caminho("musica", troca.get("arquivo", ""))
                if not arq:
                    avisos.append(f"troca de musica em {t:.1f}s: arquivo {troca.get('arquivo')} nao encontrado")
                elif 0.5 < t < total - 1.0:
                    faixas.append({"arquivo": arq, "inicio": t, "dur": duracao_arquivo(arq)})
    if ed.get("efeitos_ligados", True):
        for e in ed.get("efeitos") or []:
            arq = biblioteca.caminho("efeito", e.get("arquivo", ""))
            if not arq:
                avisos.append(
                    f"efeito em {float(e['tempo']):.1f}s: arquivo {e.get('arquivo') or '(nenhum)'} nao encontrado"
                )
                continue
            vol = e.get("volume")
            vol = float(CFG.get("volume_efeitos", 0.8)) if vol is None else float(vol)
            efeitos.append({"arquivo": arq, "tempo": float(e["tempo"]), "volume": vol})
    return {"faixas": faixas, "volume": mus.get("volume"), "efeitos": efeitos, "avisos": avisos}
