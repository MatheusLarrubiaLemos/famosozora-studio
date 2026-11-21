# O que o editor de video LE e GRAVA (sem tela):
#   Longo: <projeto>\edicao.json (versao 3: trechos, marcadores, introducao, serie, predefinicao). Na 1a gravacao de
#          cada vez que o editor abre, o arquivo de antes vira edicao.anterior.json (copia de seguranca).
#          Marcador de capitulo vira capitulo do edicao.json; "Criar Short daqui" poe um corte no cortes.json.
#   Short: <projeto>\edicao_shorts\NN_autoedit.json (os cortes de dentro do Short, mesma ideia do edicao.json,
#          com "tipo": "short" e os limites) e, se voce mexeu no comeco/fim, o inicio/fim do corte no cortes.json.
import shutil
from pathlib import Path

from autoedit import trechos as tr
from nucleo.comum import gravar_json, ler_json, ler_tempo
from versao import VERSAO

FOLGA_SHORT = 10.0  # segundos antes e depois do Short que aparecem no editor (para poder aumentar)
SHORT_ANTES, SHORT_DEPOIS = 15.0, 30.0  # "Criar Short daqui": comeco e fim sugeridos em volta do marcador


# ================================================================== longo
def ler_edicao_longo(pasta: Path) -> dict:
    """O edicao.json (ja na versao 3, convertido se for antigo), ou um vazio se ainda nao existe."""
    from videos_longos.pedido_edicao import VERSAO_EDICAO, campos_novos, migrar_arquivo

    arq = Path(pasta) / "edicao.json"
    if arq.exists():
        migrar_arquivo(pasta)
        dados = ler_json(arq, {}) or {}
    else:
        dados = {"versao": VERSAO_EDICAO, "remover": [], "capitulos": []}
    for k, v in campos_novos(dados).items():
        dados.setdefault(k, v)
    return dados


def protegidos_do_claude(dados: dict) -> list:
    """[(a, b)] que o Claude mandou manter (sem fala, mas importante)."""
    out = []
    for m in dados.get("manter") or []:
        try:
            a, b = ler_tempo(m["inicio"]), ler_tempo(m["fim"])
        except (KeyError, TypeError, ValueError):
            continue
        if b > a:
            out.append((a, b))
    return out


def cortes_do_claude(dados: dict) -> list:
    """[(a, b, ativo, motivo)] do "remover" do Claude (aparecem no editor como faixa propria)."""
    out = []
    for c in dados.get("remover") or dados.get("cortes") or []:
        try:
            a, b = ler_tempo(c["inicio"]), ler_tempo(c["fim"])
        except (KeyError, TypeError, ValueError):
            continue
        out.append((a, b, c.get("ativo", True) is not False, str(c.get("motivo", ""))))
    return out


class GravadorLongo:
    def __init__(self, pasta: Path):
        self.pasta = Path(pasta)
        self._copia_feita = False

    def gravar(self, estado, serie: bool, regras: dict | None, video: Path | None = None):
        from videos_longos.pedido_edicao import gravar_edicao, para_interno

        arq = self.pasta / "edicao.json"
        if arq.exists() and not self._copia_feita:
            shutil.copy2(arq, self.pasta / "edicao.anterior.json")
        self._copia_feita = True
        dados = para_interno(ler_edicao_longo(self.pasta))
        dados.update(estado.para_dict())
        dados.pop("limites", None)
        dados["serie"] = bool(serie)
        dados["tipo"] = "longo"
        if video:
            dados["video_original"] = str(video)
        if regras and not dados.get("predefinicao"):
            dados["predefinicao"] = {"nome": regras["nome"], "versao": regras["versao"], "tipo": regras["tipo"]}
        dados["capitulos"] = capitulos_com_marcadores(dados.get("capitulos") or [], estado.marcadores)
        dados["historico_versao_app"] = VERSAO
        gravar_edicao(arq, dados)
        estado.mudou_desde_salvar = False


def capitulos_com_marcadores(capitulos: list, marcadores: list) -> list:
    """Cada marcador de capitulo vira um capitulo (se ainda nao tiver um a menos de 10 s dele)."""
    caps = [dict(c) for c in capitulos]

    def tempo_de(c):
        try:
            return ler_tempo(c.get("inicio", c.get("tempo")))
        except (TypeError, ValueError):
            return -1e9

    from videos_longos.pedido_edicao import fmt_tempo

    for m in marcadores:
        if m.get("tipo") != "capitulo":
            continue
        if any(abs(tempo_de(c) - m["tempo"]) < 10 for c in caps):
            continue
        caps.append({"inicio": fmt_tempo(m["tempo"]), "titulo": m.get("texto") or "Capítulo"})
    return sorted(caps, key=tempo_de)


def criar_short_daqui(pasta: Path, t: float, duracao: float, texto: str = "", palavras=()) -> int:
    """'Criar Short daqui' (marcador ⭐): poe um corte novo no cortes.json, com comeco e fim sugeridos em volta do
    marcador (encaixados em pausas da fala). Devolve o numero do Short novo."""
    from shorts.cortes import VERSAO as VERSAO_CORTES
    from shorts.cortes import ler_cortes
    from videos_longos.pedido_edicao import fmt_tempo, pausas, ponto_silencio

    lp = pausas(sorted(palavras)) if palavras else []
    a = ponto_silencio(max(0.0, t - SHORT_ANTES), lp, 2.0)
    b = ponto_silencio(min(duracao or t + SHORT_DEPOIS, t + SHORT_DEPOIS), lp, 2.0)
    dados = ler_cortes(Path(pasta)) or {"versao": VERSAO_CORTES, "cortes": [], "correcoes": {}}
    titulo = texto.strip() or f"Short do minuto {int(t // 60)}"
    dados["cortes"].append({"inicio": fmt_tempo(a), "fim": fmt_tempo(max(b, a + 5)), "titulo": titulo,
                            "motivo": "marcado no editor do vídeo longo", "origem": "editor"})  # fmt: skip
    gravar_json(Path(pasta) / "cortes.json", dados)
    return len(dados["cortes"])


# ================================================================== short
def arq_short(pasta: Path, n: int) -> Path:
    return Path(pasta) / "edicao_shorts" / f"{n:02d}_autoedit.json"


def corte_do_short(pasta: Path, n: int):
    from shorts.cortes import ler_cortes

    dados = ler_cortes(Path(pasta), gravar_migracao=False) or {"cortes": []}
    cortes = dados.get("cortes") or []
    if not 0 < n <= len(cortes) or not isinstance(cortes[n - 1], dict):
        return None
    return cortes[n - 1]


def ler_short(pasta: Path, n: int) -> dict | None:
    """O que foi feito no editor para o Short n: {"trechos", "marcadores", "limites", ...} ou None."""
    dados = ler_json(arq_short(pasta, n))
    return dados if isinstance(dados, dict) and dados.get("tipo") == "short" else None


def cortes_internos(pasta: Path, n: int, ini: float, fim: float) -> list:
    """[(a, b)] (tempos do original) que saem de DENTRO do Short n, se a edicao for deste trecho.
    O render (shorts/gerar_shorts.py) tira esses pedacos e a legenda acompanha (MapaTempo)."""
    dados = ler_short(pasta, n)
    if not dados:
        return []
    lim = dados.get("limites") or [None, None]
    if lim[0] is None or abs(float(lim[0]) - ini) > 0.06 or abs(float(lim[1]) - fim) > 0.06:
        return []  # o corte mudou depois (Claude de novo, outro trecho): a edicao antiga nao vale
    res = tr.resolver(tr.normalizar(dados.get("trechos")), fim + 60)
    out = []
    for a, b, acao, _ in res:
        if acao != "cortar":
            continue
        a, b = max(a, ini), min(b, fim)
        if b - a >= 0.05:
            out.append((round(a, 3), round(b, 3)))
    return out


def gravar_short(pasta: Path, n: int, estado, regras: dict | None):
    """Grava o NN_autoedit.json e, se o comeco/fim mudou, o corte no cortes.json."""
    from shorts.cortes import ler_cortes
    from videos_longos.pedido_edicao import fmt_tempo

    arq = arq_short(pasta, n)
    arq.parent.mkdir(parents=True, exist_ok=True)
    corpo = estado.para_dict()
    corpo.pop("introducao", None)
    gravar_json(arq, {"versao": 3, "tipo": "short", "n": n, **corpo,
                      "janela": [estado.inicio, estado.fim],
                      "predefinicao": {"nome": regras["nome"], "versao": regras["versao"], "tipo": "short"}
                      if regras else None, "historico_versao_app": VERSAO})  # fmt: skip
    if estado.limites:
        dados = ler_cortes(Path(pasta))
        if dados and 0 < n <= len(dados["cortes"]):
            c = dados["cortes"][n - 1]
            a, b = estado.limites
            try:
                igual = abs(ler_tempo(c["inicio"]) - a) < 0.01 and abs(ler_tempo(c["fim"]) - b) < 0.01
            except (KeyError, TypeError, ValueError):
                igual = False
            if not igual:
                c["inicio"], c["fim"] = fmt_tempo(a), fmt_tempo(b)
                gravar_json(Path(pasta) / "cortes.json", dados)
    estado.mudou_desde_salvar = False
