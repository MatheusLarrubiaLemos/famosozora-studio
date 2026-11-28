# Quanto tempo um Short pode ter (desde a 1.11.5): o Short PRONTO (gancho + corte + final com INSCREVA-SE) tem no
# maximo "shorts_duracao_maxima" segundos (60 por padrao). Se passar, o Short e acelerado ate
# "shorts_velocidade_maxima" (1.25x por padrao) para caber. As contas daqui valem no pedido ao Claude, na conferencia
# da resposta dele e na montagem do Short (gerar_shorts / montagem).
import math

LIMITE_YOUTUBE = 180.0  # o YouTube aceita Shorts de ate 3 minutos
GANCHO_MAXIMO = 5.0  # o gancho (abertura) tem de 2 a 5 s


def duracao_maxima(cfg: dict) -> float:
    """Tamanho maximo do Short pronto, em segundos. 0 ou vazio = o limite do YouTube (3 minutos)."""
    try:
        v = float(cfg.get("shorts_duracao_maxima", 60) or 0)
    except (TypeError, ValueError):
        v = 60.0
    return LIMITE_YOUTUBE if v <= 0 else min(v, LIMITE_YOUTUBE)


def velocidade_maxima(cfg: dict) -> float:
    """Quanto o Short pode ser acelerado para caber (1 = nunca acelera). Fica entre 1x e 2x."""
    try:
        v = float(cfg.get("shorts_velocidade_maxima", 1.25) or 1)
    except (TypeError, ValueError):
        v = 1.25
    return max(1.0, min(2.0, v))


def _transicao(cfg: dict) -> float:
    if str(cfg.get("transicao", "fade")).lower() in ("nenhuma", "corte", "off", "false"):
        return 0.0
    try:
        return max(0.0, min(1.0, float(cfg.get("duracao_transicao", 0.45))))
    except (TypeError, ValueError):
        return 0.45


def duracao_do_final(cfg: dict) -> float:
    """Segundos do final com INSCREVA-SE."""
    try:
        return max(0.0, float(cfg.get("duracao_final", 3.5) or 0))
    except (TypeError, ValueError):
        return 3.5


def total_do_short(cfg: dict, dur_corte: float, dur_gancho: float = 0.0) -> float:
    """Tamanho do Short pronto, sem acelerar: gancho + corte + final (o gancho entra com transicao por cima)."""
    if dur_gancho > 0 and cfg.get("usar_abertura", True):
        return dur_gancho + dur_corte + duracao_do_final(cfg) - _transicao(cfg)
    return dur_corte + duracao_do_final(cfg)


def limites_do_corte(cfg: dict) -> tuple:
    """(ideal, com_aceleracao): ate quantos segundos o CORTE pode ter, contando um gancho de 5 s e o final.
    ideal = cabe sem acelerar; com_aceleracao = cabe acelerando ate a velocidade maxima."""
    sobra = total_do_short(cfg, 0.0, GANCHO_MAXIMO if cfg.get("usar_abertura", True) else 0.0)
    maxima = duracao_maxima(cfg)
    ideal = max(5.0, maxima - sobra)
    acelerado = max(ideal, maxima * velocidade_maxima(cfg) - sobra)
    return ideal, acelerado


def velocidade_para_caber(total: float, cfg: dict) -> float:
    """Velocidade do Short pronto: 1 se ja cabe; senao o necessario para caber, no maximo a velocidade maxima."""
    maxima = duracao_maxima(cfg)
    if total <= maxima + 0.05:
        return 1.0
    precisa = math.ceil(total / maxima * 10000) / 10000  # arredonda para cima: assim cabe de verdade
    return min(velocidade_maxima(cfg), precisa)
