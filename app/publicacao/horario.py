# Horarios de publicacao, sempre no horario de Brasilia (o Brasil nao tem horario de verao desde 2019).
# Shorts: as 12:00, no dia seguinte ao ultimo Short ja agendado (um por dia). Video longo: voce escolhe;
# a sugestao padrao vem do config.json ("publicar_longo_hora" e "publicar_longo_daqui_a_dias").
from datetime import datetime, timedelta, timezone

BRASILIA = timezone(timedelta(hours=-3), "Brasília")
HORA_SHORTS = "12:00"
FOLGA_MINUTOS = 60  # nao agenda para daqui a menos de 1 hora (da tempo do Claude subir o video)
DIAS_DA_SEMANA = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")


def agora() -> datetime:
    return datetime.now(BRASILIA)


def _hora(texto: str) -> tuple:
    h, m = str(texto or HORA_SHORTS).strip().split(":")[:2]
    h, m = int(h), int(m)
    if not (0 <= h < 24 and 0 <= m < 60):
        raise ValueError(texto)
    return h, m


def em_brasilia(valor) -> datetime:
    """Aceita datetime ou texto ISO ('2026-11-18T12:00:00-03:00') e devolve no horario de Brasilia."""
    dt = valor if isinstance(valor, datetime) else datetime.fromisoformat(str(valor))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BRASILIA)
    return dt.astimezone(BRASILIA)


def proximo_dia_livre(ocupados, hora: str = HORA_SHORTS, referencia: datetime | None = None) -> datetime:
    """O proximo horario de Short: 'hora' do dia seguinte ao ultimo dia ocupado (ou hoje/amanha, se nada
    estiver agendado). Nunca menos de 1 hora a partir de agora. ocupados = datetimes (ou textos ISO)."""
    h, m = _hora(hora)
    ref = em_brasilia(referencia) if referencia else agora()
    candidato = ref.replace(hour=h, minute=m, second=0, microsecond=0)
    if candidato < ref + timedelta(minutes=FOLGA_MINUTOS):
        candidato += timedelta(days=1)
    dias = {em_brasilia(o).date() for o in ocupados}
    futuros = [d for d in dias if d >= candidato.date()]
    if futuros:
        ultimo = max(futuros)
        candidato = candidato.replace(year=ultimo.year, month=ultimo.month, day=ultimo.day) + timedelta(days=1)
    return candidato


def proximos_dias_livres(ocupados, quantos: int, hora: str = HORA_SHORTS, referencia=None) -> list:
    """'quantos' horarios seguidos, um por dia (para "Publicar todos os Shorts prontos")."""
    ocupados = list(ocupados)
    saida = []
    for _ in range(quantos):
        h = proximo_dia_livre(ocupados + saida, hora, referencia)
        saida.append(h)
    return saida


def sugestao_longo(cfg: dict, referencia: datetime | None = None) -> datetime:
    """Sugestao para o video longo: daqui a N dias (padrao 1) no horario do config (padrao 18:00)."""
    h, m = _hora(cfg.get("publicar_longo_hora") or "18:00")
    try:
        dias = max(0, int(cfg.get("publicar_longo_daqui_a_dias", 1)))
    except (TypeError, ValueError):
        dias = 1
    ref = em_brasilia(referencia) if referencia else agora()
    sug = (ref + timedelta(days=dias)).replace(hour=h, minute=m, second=0, microsecond=0)
    if sug < ref + timedelta(minutes=FOLGA_MINUTOS):
        sug += timedelta(days=1)
    return sug


def texto_horario(valor, com_ano: bool = False) -> str:
    """'qua 18/11 às 12:00' (horario de Brasilia)."""
    dt = em_brasilia(valor)
    data = dt.strftime("%d/%m/%Y" if com_ano else "%d/%m")
    return f"{DIAS_DA_SEMANA[dt.weekday()]} {data} às {dt.strftime('%H:%M')}"


def para_caixa(valor) -> str:
    """Como o horario aparece na caixa de edicao: '18/11/2026 12:00'."""
    return em_brasilia(valor).strftime("%d/%m/%Y %H:%M")


def ler_caixa(texto: str) -> datetime:
    """Le '18/11/2026 12:00' (ou '18/11 12:00', ano atual) no horario de Brasilia. Da ValueError se nao der."""
    texto = " ".join(str(texto).replace("às", " ").replace("as ", " ").split())
    try:
        data, hora = texto.split(" ")
        partes = data.split("/")
        dia, mes = int(partes[0]), int(partes[1])
        ano = int(partes[2]) if len(partes) > 2 and partes[2] else agora().year
        if ano < 100:
            ano += 2000
        h, m = _hora(hora)
        return datetime(ano, mes, dia, h, m, tzinfo=BRASILIA)
    except (ValueError, IndexError):
        raise ValueError(f'"{texto}" não é uma data. Use dia/mês/ano hora:minuto, ex.: 18/11/2026 12:00') from None


def iso(valor) -> str:
    return em_brasilia(valor).isoformat(timespec="minutes")
