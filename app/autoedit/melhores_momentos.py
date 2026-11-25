# MELHORES MOMENTOS (desde a 1.11.0): o Claude le a transcricao da live inteira e marca os momentos que valem um
# video de "melhores momentos" (risada, jogada boa, susto, briga, virada, final de partida...), cada um com o
# CONTEXTO (o comeco da situacao e o desfecho) e uma nota de 1 a 10. Guarda TODOS em analise\melhores.json; quantos
# entram no video e decidido depois, na hora de montar a versao (escolher()), pelo tempo que voce quer
# (instantaneo: da para trocar entre "~40 min" e "~15 min" sem perguntar de novo ao Claude).
# Sem o Claude Code no PC: escolhe pelos sinais (onde mais se fala e o som e mais alto), bem mais simples.
import threading
from pathlib import Path

from autoedit.base import cache_valido, gravar_cache, progresso
from nucleo.comum import ler_json, ler_tempo

VERSAO = 1
ARQUIVO = "melhores.json"
CONTEXTO_ANTES, CONTEXTO_DEPOIS = 2.0, 1.5  # folga (s) em volta de cada momento, para nao comecar/terminar seco
JUNTAR_SE_PERTO = 8.0  # dois momentos a menos disso viram um so (nao fica um pulo de 3 s no meio)

FORMATO = """{
  "momentos": [
    {"inicio": "01:12:05", "fim": "01:14:30", "nota": 9, "titulo": "a invasão que deu errado"}
  ]
}"""


def pedido(transcricao: str, parte: int = 1, total: int = 1) -> str:
    sobre = (f"ATENÇÃO: a live veio dividida; esta é a PARTE {parte} de {total}. Marque só o que está nesta parte "
             "(tempos do vídeo inteiro).\n\n") if total > 1 else ""  # fmt: skip
    return (
        "Você é editor do canal FamosoZora (gameplay, humor, conversa com o chat). Vai ler a transcrição de uma live "
        "(formato [início-fim] fala) e marcar os MELHORES MOMENTOS para um vídeo de melhores momentos no YouTube.\n"
        "Bons momentos: risada de verdade, piada boa, reação forte, susto, raiva, jogada boa ou muito ruim, virada, "
        "conquista, derrota, final de partida, história engraçada, interação boa com o chat.\n"
        "Regras:\n"
        "- Cada momento precisa se entender SOZINHO: comece um pouco antes (quando a situação começa) e termine "
        "depois do desfecho/da reação. Normalmente de 30 s a 5 min.\n"
        "- Dê uma nota de 1 a 10 (10 = imperdível). Seja exigente: momento morno é nota baixa.\n"
        "- Pode marcar bastante coisa: o Studio escolhe pelas notas quantos entram no vídeo.\n"
        "- Não marque: esperar carregar, menu, silêncio, problema técnico, papo sem graça.\n\n"
        + sobre + "Responda SÓ com um JSON válido neste formato (HH:MM:SS):\n" + FORMATO
        + "\n\n=== TRANSCRIÇÃO ===\n" + transcricao
    )  # fmt: skip


def validar(dados) -> list:
    if not isinstance(dados, dict) or not isinstance(dados.get("momentos"), list):
        return ['a resposta precisa ser {"momentos": [...]}']
    erros = []
    for k, m in enumerate(dados["momentos"], 1):
        try:
            if ler_tempo(m["fim"]) <= ler_tempo(m["inicio"]):
                erros.append(f"momento {k}: o fim vem antes do início")
            float(m.get("nota", 5))
        except (KeyError, TypeError, ValueError):
            erros.append(f"momento {k}: tempo ou nota inválidos")
    return erros


def juntar_respostas(respostas: list) -> list:
    out = []
    for r in respostas:
        for m in (r or {}).get("momentos") or []:
            a, b = ler_tempo(m["inicio"]), ler_tempo(m["fim"])
            if b - a >= 5:
                nota = max(1.0, min(10.0, float(m.get("nota", 5))))
                out.append({"inicio": a, "fim": b, "nota": nota, "titulo": str(m.get("titulo", "")).strip()})
    return sorted(out, key=lambda m: m["inicio"])


def pelos_sinais(palavras: list, duracao: float, janela: float = 60.0) -> list:
    """Sem o Claude: cada minuto vira um "momento" com nota pela quantidade de fala (onde mais se conversa e reage).
    Bem mais simples que o Claude, mas melhor que nada."""
    if duracao <= 0:
        return []
    n = max(1, int(duracao // janela) + 1)
    falas = [0.0] * n
    for i, f in palavras:
        falas[min(n - 1, int(i // janela))] += max(0.0, f - i)
    maior = max(falas) or 1.0
    return [{"inicio": k * janela, "fim": min(duracao, (k + 1) * janela), "nota": round(1 + 9 * v / maior, 1),
             "titulo": ""} for k, v in enumerate(falas) if v > 0]  # fmt: skip


def classificar(video: Path, pasta_projeto: Path, pasta_analise: Path, cancelar_evento=None, avisar=print,
                etapa=(1, 1), pedir=None) -> dict:  # fmt: skip
    """Pede ao Claude (ou le do cache). pedir = funcao de teste no lugar do Claude. Devolve {"momentos", "aviso",
    "fonte": "claude" | "sinais"}."""
    from nucleo import claude_local

    arq = Path(pasta_analise) / ARQUIVO
    arq_txt = Path(pasta_projeto) / "transcricao_para_claude.txt"
    ajustes = {"transcricao": int(arq_txt.stat().st_mtime) if arq_txt.exists() else 0}
    pronto = cache_valido(arq, video, VERSAO, ajustes)
    if pronto:
        return pronto
    if not arq_txt.exists():
        return {"momentos": [], "fonte": "", "aviso": "Sem transcrição: os melhores momentos não foram escolhidos."}
    if pedir is None and not claude_local.disponivel():
        from autoedit.analisar import info_projeto, palavras_do_projeto

        _, dur = info_projeto(pasta_projeto)
        dados = {"momentos": pelos_sinais(palavras_do_projeto(pasta_projeto), dur), "fonte": "sinais",
                 "aviso": "Sem o Claude Code: os melhores momentos foram escolhidos só por onde mais se fala."}  # fmt: skip
        gravar_cache(arq, video, VERSAO, dados, ajustes)
        return dados
    partes = claude_local.dividir_transcricao(arq_txt.read_text(encoding="utf-8"))
    pedidos = [pedido(p, k, len(partes)) for k, p in enumerate(partes, 1)]
    progresso(*etapa, "O Claude escolhendo os melhores momentos", 0.0)
    try:
        if pedir:
            respostas = [pedir(p, validar) for p in pedidos]
        else:
            respostas = claude_local.pedir_partes(pedidos, validar, cancelar_evento or threading.Event(), avisar)
    except claude_local.Cancelado:
        raise
    except Exception as e:
        return {"momentos": [], "fonte": "", "aviso": f"O Claude não conseguiu escolher os melhores momentos ({e})."}
    dados = {"momentos": juntar_respostas(respostas), "fonte": "claude", "aviso": ""}
    gravar_cache(arq, video, VERSAO, dados, ajustes)
    progresso(*etapa, "O Claude escolhendo os melhores momentos", 1.0)
    return {"versao": VERSAO, **dados}


def guardados(pasta_projeto: Path) -> list | None:
    """Os momentos ja escolhidos para esta live (None = ainda nao escolheu: precisa do Claude)."""
    dados = ler_json(Path(pasta_projeto) / "analise" / ARQUIVO, None)
    return dados.get("momentos") if isinstance(dados, dict) and dados.get("momentos") is not None else None


def alvo_automatico(duracao: float) -> float:
    """Quanto tempo de melhores momentos, em segundos: ~8% da live, entre 10 e 45 min (9 h -> ~43 min)."""
    return min(45 * 60.0, max(10 * 60.0, duracao * 0.08))


def escolher(momentos: list, alvo: float, duracao: float, protegidos=()) -> list:
    """Os momentos que entram (das notas mais altas para baixo, ate dar o tempo 'alvo'), na ordem do video, com a
    folga de contexto e juntando os que ficaram perto. Os 'protegidos' (introducao...) entram sempre.
    Devolve [(inicio, fim)]."""
    escolhidos, total = [], 0.0
    for a, b in protegidos:
        escolhidos.append((max(0.0, a), min(duracao, b)))
        total += b - a
    for m in sorted(momentos, key=lambda m: (-m["nota"], m["inicio"])):
        if total >= alvo:
            break
        a, b = max(0.0, m["inicio"] - CONTEXTO_ANTES), min(duracao, m["fim"] + CONTEXTO_DEPOIS)
        if b - a > alvo * 0.6 and escolhidos:  # um momento enorme nao come o video inteiro
            continue
        if escolhidos and total + (b - a) > alvo * 1.15:  # passaria muito do tempo: tenta os menores
            continue
        escolhidos.append((a, b))
        total += b - a
    juntos = []
    for a, b in sorted(escolhidos):
        if juntos and a - juntos[-1][1] <= JUNTAR_SE_PERTO:
            juntos[-1] = (juntos[-1][0], max(juntos[-1][1], b))
        else:
            juntos.append((a, b))
    return juntos


def cortes_fora(ficam: list, duracao: float) -> list:
    """Tudo o que NAO esta nos momentos escolhidos vira sugestao de corte ("fora dos melhores momentos")."""
    out, pos = [], 0.0
    for a, b in ficam:
        if a - pos > 0.5:
            out.append({"inicio": round(pos, 3), "fim": round(a, 3), "acao": "cortar", "motivo": "fora_melhores",
                        "origem": "auto", "confianca": "alta"})  # fmt: skip
        pos = max(pos, b)
    if duracao - pos > 0.5:
        out.append({"inicio": round(pos, 3), "fim": round(duracao, 3), "acao": "cortar", "motivo": "fora_melhores",
                    "origem": "auto", "confianca": "alta"})  # fmt: skip
    return out
