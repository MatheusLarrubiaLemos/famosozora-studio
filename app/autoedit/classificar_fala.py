# O Claude LE A CONVERSA (Fase 1E): pela transcricao, marca os trechos de PAPO FORA DO JOGO (assunto que nao tem
# nada a ver com o jogo, esperar alguem, resolver problema de som/camera...) e acha a INTRODUCAO do episodio
# (o trecho em que voce apresenta o episodio). Papo pode ser conteudo bom: vira so SUGESTAO em amarelo, nunca
# corte automatico. Sem Claude: pula e avisa. Saida: analise\fala.json
import threading
from pathlib import Path

from autoedit.base import cache_valido, gravar_cache, progresso
from nucleo.comum import ler_tempo

VERSAO = 1

FORMATO = """{
  "papo_fora": [
    {"inicio": "00:12:05", "fim": "00:14:30", "motivo": "resolvendo o som do microfone"}
  ],
  "introducao": {"inicio": "00:00:40", "fim": "00:01:30"}
}"""


def pedido(transcricao: str, parte: int = 1, total: int = 1) -> str:
    sobre = (f"ATENÇÃO: a live veio dividida; esta é a PARTE {parte} de {total}. Marque só o que está nesta parte "
             "(tempos do vídeo inteiro).\n\n") if total > 1 else ""  # fmt: skip
    return (
        "Você vai ler a transcrição de uma live de gameplay do canal FamosoZora (formato [início-fim] fala) e "
        "marcar duas coisas:\n"
        "1) papo_fora: trechos de 20 s ou mais em que a conversa NÃO tem nada a ver com o jogo que está na tela "
        "(esperar alguém, resolver problema de som, câmera ou internet, assunto pessoal longo, ler doação parado). "
        "Conversa e piada DURANTE o jogo NÃO é papo fora: fica. Na dúvida, não marque.\n"
        "2) introducao: o trecho em que o streamer apresenta o episódio (\"fala galera, hoje a gente vai...\"). "
        "Se não tiver, use null.\n\n" + sobre + "Responda SÓ com um JSON válido neste formato (HH:MM:SS):\n" + FORMATO
        + "\n\n=== TRANSCRIÇÃO ===\n" + transcricao
    )


def validar(dados) -> list:
    if not isinstance(dados, dict):
        return ["a resposta precisa ser um objeto { ... }"]
    erros = []
    for k, p in enumerate(dados.get("papo_fora") or [], 1):
        try:
            if ler_tempo(p["fim"]) <= ler_tempo(p["inicio"]):
                erros.append(f"papo_fora {k}: o fim vem antes do início")
        except (KeyError, TypeError, ValueError):
            erros.append(f"papo_fora {k}: tempo inválido")
    intro = dados.get("introducao")
    if intro:
        try:
            ler_tempo(intro["inicio"]), ler_tempo(intro["fim"])
        except (KeyError, TypeError, ValueError):
            erros.append("introducao: tempo inválido")
    return erros


def juntar_respostas(respostas: list) -> dict:
    papo, intro = [], None
    for r in respostas:
        for p in (r or {}).get("papo_fora") or []:
            a, b = ler_tempo(p["inicio"]), ler_tempo(p["fim"])
            if b - a >= 5:
                papo.append({"inicio": a, "fim": b, "motivo": str(p.get("motivo", "")).strip()})
        i = (r or {}).get("introducao")
        if i and intro is None:
            a, b = ler_tempo(i["inicio"]), ler_tempo(i["fim"])
            if b > a:
                intro = {"inicio": a, "fim": b}
    return {"papo_fora": sorted(papo, key=lambda p: p["inicio"]), "introducao": intro}


def classificar(video: Path, pasta_projeto: Path, pasta_analise: Path, cancelar_evento=None, avisar=print,
                etapa=(1, 1), pedir=None) -> dict:  # fmt: skip
    """Pede ao Claude (ou le do cache). pedir = funcao de teste no lugar do Claude."""
    from nucleo import claude_local

    arq = Path(pasta_analise) / "fala.json"
    arq_txt = Path(pasta_projeto) / "transcricao_para_claude.txt"
    ajustes = {"transcricao": int(arq_txt.stat().st_mtime) if arq_txt.exists() else 0}
    pronto = cache_valido(arq, video, VERSAO, ajustes)
    if pronto:
        return pronto
    if not arq_txt.exists():
        return {"papo_fora": [], "introducao": None, "aviso": "Sem transcrição: a leitura da conversa foi pulada."}
    if pedir is None and not claude_local.disponivel():
        return {"papo_fora": [], "introducao": None,
                "aviso": "Claude Code não encontrado: a leitura da conversa (papo fora do jogo) foi pulada."}  # fmt: skip
    texto = arq_txt.read_text(encoding="utf-8")
    partes = claude_local.dividir_transcricao(texto)
    pedidos = [pedido(p, k, len(partes)) for k, p in enumerate(partes, 1)]
    progresso(*etapa, "O Claude lendo a conversa", 0.0)
    try:
        if pedir:
            respostas = [pedir(p, validar) for p in pedidos]
        else:
            respostas = claude_local.pedir_partes(pedidos, validar, cancelar_evento or threading.Event(), avisar)
    except claude_local.Cancelado:
        raise
    except Exception as e:
        return {"papo_fora": [], "introducao": None, "aviso": f"O Claude não conseguiu ler a conversa ({e})."}
    dados = {**juntar_respostas(respostas), "aviso": ""}
    gravar_cache(arq, video, VERSAO, dados, ajustes)
    progresso(*etapa, "O Claude lendo a conversa", 1.0)
    return {"versao": VERSAO, **dados}
