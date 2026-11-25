# Junta todos os sinais e DECIDE as sugestoes de corte (Fase 1F). E uma conta fixa: o mesmo video com a mesma
# predefinicao da sempre o mesmo resultado (nada de sorteio, nada de Claude aqui dentro).
# Para cada 0,1 s, um rotulo:
#   manter    -> tem fala, ou o jogo tem som e movimento
#   silencio  -> sem fala E volume do jogo baixo (no "Longo (TV)": e tambem sem acao)
#   sem_jogo  -> tela preta/loading, ou o Claude viu menu, loading, espera ou area de trabalho
#   sem_acao  -> sem fala E quase sem movimento na area do jogo
# Depois aplica as regras da predefinicao: tamanho minimo de cada tipo, margens antes/depois do que fica, nunca
# cortar palavra, ima nas trocas de cena, juntar cortes proximos e nao deixar sobrinha sem fala entre dois cortes.
# Papo fora do jogo (lido pelo Claude) e confianca baixa viram so SUGESTAO (amarelo): nao saem sozinhos.
import math

from autoedit.base import PASSO

ORDEM_MOTIVOS = ("sem_jogo", "silencio", "sem_acao")  # desempate: o primeiro vence
CORTE_INUTIL = 0.3  # corte menor que isso (depois das margens) nao vale a pena
CONGELADO = 0.004


class Linha:
    """A linha do tempo de [inicio, fim) em passos de 0,1 s, com fala, volume, movimento e brilho."""

    def __init__(self, inicio: float, fim: float, palavras=(), som=None, imagem=None, cenas_sem_jogo=()):
        import numpy as np

        self.inicio, self.fim = float(inicio), float(fim)
        self.n = max(1, int(math.ceil((self.fim - self.inicio) / PASSO - 1e-9)))
        self.palavras = sorted((float(i), float(f)) for i, f in palavras if f > self.inicio and i < self.fim)
        self.fala = np.zeros(self.n, dtype=bool)
        for i, f in self.palavras:
            self.fala[self._k(i) : self._k(f, cima=True)] = True
        if som and som.get("fala_vad"):
            for i, f in som["fala_vad"]:
                if f > self.inicio and i < self.fim:
                    self.fala[self._k(i) : self._k(f, cima=True)] = True
        self.volume = self._reamostrar(som, "volume", 1.0)
        self.movimento = self._reamostrar(imagem, "movimento", 1.0)
        self.brilho = self._reamostrar(imagem, "brilho", 0.5)
        self.trocas = sorted(t for t in (imagem or {}).get("trocas", []) if self.inicio < t < self.fim)
        self.sem_jogo = np.zeros(self.n, dtype=np.int8)  # 0 = jogo; 1 = baixa; 2 = media; 3 = alta (Claude)
        for a, b, conf in cenas_sem_jogo:
            v = {"baixa": 1, "media": 2, "alta": 3}.get(conf, 2)
            fatia = slice(self._k(a), self._k(b, cima=True))
            self.sem_jogo[fatia] = np.maximum(self.sem_jogo[fatia], v)

    def _k(self, t: float, cima: bool = False) -> int:
        x = (t - self.inicio) / PASSO
        k = math.ceil(x - 1e-9) if cima else math.floor(x + 1e-9)
        return min(self.n, max(0, k))

    def tempo(self, k: int) -> float:
        return round(self.inicio + k * PASSO, 3)

    def _reamostrar(self, dados, chave: str, padrao: float):
        """Leva uma medida (com outro passo) para os passos de 0,1 s da linha."""
        import numpy as np

        if not dados or not dados.get(chave):
            return np.full(self.n, padrao, dtype=np.float32)
        valores = np.asarray(dados[chave], dtype=np.float32)
        passo, base = float(dados.get("passo", PASSO)), float(dados.get("inicio", 0.0))
        t = self.inicio + (np.arange(self.n) + 0.5) * PASSO
        idx = np.clip(((t - base) / passo).astype(int), 0, len(valores) - 1)
        return valores[idx]

    def sem_certeza(self, a: float, b: float) -> bool:
        """O trecho [a, b) precisa do Claude olhar a tela? (quase sem fala e nem tudo preto)"""
        ka, kb = self._k(a), self._k(b, cima=True)
        if kb <= ka:
            return False
        fala = float(self.fala[ka:kb].mean())
        preto = float((self.brilho[ka:kb] < 0.06).mean())
        return fala < 0.3 and preto < 0.9


def rotulos(linha: Linha, regras: dict):
    """Rotulo de cada passo: 0 manter, 1 sem_jogo, 2 silencio, 3 sem_acao (numpy int8)."""
    import numpy as np

    sem_fala = ~linha.fala
    mov_baixo = linha.movimento < float(regras["movimento_baixo"])
    vol_baixo = linha.volume < float(regras["volume_baixo"])
    preto = linha.brilho < 0.06
    r = np.zeros(linha.n, dtype=np.int8)
    sem_acao = sem_fala & mov_baixo
    silencio = sem_fala & vol_baixo
    if regras.get("silencio_so_sem_acao"):
        silencio = silencio & mov_baixo
    r[sem_acao] = 3
    r[silencio] = 2
    r[sem_fala & (preto | (linha.sem_jogo >= 2))] = 1
    return r


def _corridas(r) -> list:
    """[(k_ini, k_fim)] de passos seguidos com rotulo de corte (qualquer um)."""
    out, ini = [], None
    for k, v in enumerate(list(r) + [0]):
        if v and ini is None:
            ini = k
        elif not v and ini is not None:
            out.append((ini, k))
            ini = None
    return out


def _motivo_e_confianca(linha: Linha, r, ka: int, kb: int, regras: dict) -> tuple:
    import numpy as np

    contagem = {m: int((r[ka:kb] == k).sum()) for k, m in enumerate(("", *ORDEM_MOTIVOS)) if m}
    motivo = max(ORDEM_MOTIVOS, key=lambda m: (contagem[m], -ORDEM_MOTIVOS.index(m)))
    if motivo == "sem_jogo":
        preto = float((linha.brilho[ka:kb] < 0.06).mean())
        claude = int(np.max(linha.sem_jogo[ka:kb])) if kb > ka else 0
        conf = "alta" if preto > 0.8 or claude >= 3 else ("media" if claude >= 2 or preto > 0.4 else "baixa")
    elif motivo == "silencio":
        conf = "alta" if float(np.mean(linha.volume[ka:kb])) < float(regras["volume_baixo"]) * 0.5 else "media"
    else:
        mov = float(np.mean(linha.movimento[ka:kb]))
        conf = "alta" if mov < CONGELADO else ("media" if mov < float(regras["movimento_baixo"]) * 0.5 else "baixa")
    return motivo, conf


def _minimo(motivo: str, regras: dict) -> float:
    return float(regras[{"sem_jogo": "sem_jogo_min", "silencio": "silencio_min", "sem_acao": "sem_acao_min"}[motivo]])


def _indice_palavras(linha: Linha) -> tuple:
    """(inicios das palavras, a palavra mais longa): para achar so as palavras perto de um ponto por bissecao.
    Desde a 1.11.1: antes cada corte olhava as ~80 mil palavras de uma live de 9 h (segundos por versao)."""
    if getattr(linha, "_inicios_palavras", None) is None:
        linha._inicios_palavras = [i for i, _ in linha.palavras]
        linha._maior_palavra = max((f - i for i, f in linha.palavras), default=0.0)
    return linha._inicios_palavras, linha._maior_palavra


def _tem_palavra(linha: Linha, a: float, b: float) -> bool:
    from bisect import bisect_left

    inicios, maior = _indice_palavras(linha)
    k = bisect_left(inicios, a - maior - 1e-9)  # antes disso, nenhuma palavra chega ate 'a'
    while k < len(inicios) and inicios[k] < b:
        if linha.palavras[k][1] > a:
            return True
        k += 1
    return False


def _sem_cortar_palavra(linha: Linha, a: float, b: float) -> tuple:
    """Puxa as bordas do corte para fora das palavras (o mesmo de antes, olhando so as palavras perto)."""
    from bisect import bisect_left

    inicios, maior = _indice_palavras(linha)
    k = bisect_left(inicios, min(a, b) - maior - 1e-9)  # palavras que comecam antes disso nao chegam em a nem b
    while k < len(inicios) and inicios[k] < max(a, b):
        i, f = linha.palavras[k]
        if i < a < f:
            a = f
        if i < b < f:
            b = i
        k += 1
    return a, b


def _ima(linha: Linha, a: float, b: float, alcance: float) -> tuple:
    """Leva cada borda para a troca de cena mais perto (ate 'alcance' s), sem engolir fala."""
    if alcance <= 0 or not linha.trocas:
        return a, b
    perto_a = min(linha.trocas, key=lambda t: abs(t - a))
    if abs(perto_a - a) <= alcance and perto_a < b and not _tem_palavra(linha, min(a, perto_a), max(a, perto_a)):
        a = perto_a
    perto_b = min(linha.trocas, key=lambda t: abs(t - b))
    if abs(perto_b - b) <= alcance and perto_b > a and not _tem_palavra(linha, min(b, perto_b), max(b, perto_b)):
        b = perto_b
    return a, b


NIVEL = {"baixa": 0, "media": 1, "alta": 2}


def _juntar(cortes: list, linha: Linha, regras: dict) -> list:
    """Junta cortes com pouca coisa entre eles (e sem fala nesse pedacinho)."""
    juntar = float(regras["juntar_menor_que"])
    minimo = float(regras["trecho_minimo"])
    out = []
    for c in sorted(cortes, key=lambda c: c["inicio"]):
        if out:
            u = out[-1]
            entre = c["inicio"] - u["fim"]
            if entre < juntar or (entre < minimo and not _tem_palavra(linha, u["fim"], c["inicio"])):
                if c["fim"] - c["inicio"] > u["fim"] - u["inicio"]:
                    u["motivo"] = c["motivo"]
                u["confianca"] = min(u["confianca"], c["confianca"], key=NIVEL.get)
                u["fim"] = max(u["fim"], c["fim"])
                continue
        out.append(dict(c))
    # sobrinha sem fala no comeco ou no fim da janela: vai junto
    if out and out[0]["inicio"] - linha.inicio < minimo and not _tem_palavra(linha, linha.inicio, out[0]["inicio"]):
        out[0]["inicio"] = linha.inicio
    if out and linha.fim - out[-1]["fim"] < minimo and not _tem_palavra(linha, out[-1]["fim"], linha.fim):
        out[-1]["fim"] = linha.fim
    return out


def decidir(linha: Linha, regras: dict, papo_fora=()) -> list:
    """Sugestoes de corte: [{inicio, fim, acao, motivo, origem, confianca, revisado}] em ordem de tempo."""
    r = rotulos(linha, regras)
    candidatos = []
    for ka, kb in _corridas(r):
        motivo, conf = _motivo_e_confianca(linha, r, ka, kb, regras)
        a, b = linha.tempo(ka), linha.tempo(kb) if kb < linha.n else linha.fim
        if b - a + 1e-6 < _minimo(motivo, regras):
            continue
        if a > linha.inicio + 1e-6:
            a += float(regras["margem_depois"])
        if b < linha.fim - 1e-6:
            b -= float(regras["margem_antes"])
        if regras.get("nao_cortar_palavra", True):
            a, b = _sem_cortar_palavra(linha, a, b)
        a, b = _ima(linha, a, b, float(regras.get("ima_troca_cena", 0)))
        if b - a < CORTE_INUTIL:
            continue
        candidatos.append({"inicio": a, "fim": b, "motivo": motivo, "confianca": conf})
    cortes = _juntar(candidatos, linha, regras)
    acelerar = bool(regras.get("acelerar_em_vez_de_cortar"))
    motivos_acel = set(regras.get("acelerar_motivos") or [])
    out = []
    for c in cortes:
        acao = "manter" if c["confianca"] == "baixa" else "cortar"
        item = {"inicio": round(c["inicio"], 3), "fim": round(c["fim"], 3), "acao": acao, "motivo": c["motivo"],
                "origem": "auto", "confianca": c["confianca"], "revisado": False}  # fmt: skip
        if acelerar and acao == "cortar" and c["motivo"] in motivos_acel:
            item["acao"] = "acelerar"
            item["velocidade"] = float(regras.get("acelerar_velocidade", 2.0))
        out.append(item)
    for p in papo_fora:  # so sugestao (amarelo): papo pode ser conteudo bom
        a, b = max(linha.inicio, float(p["inicio"])), min(linha.fim, float(p["fim"]))
        if b - a >= 1:
            out.append({"inicio": round(a, 3), "fim": round(b, 3), "acao": "manter", "motivo": "papo_fora",
                        "origem": "auto", "confianca": "baixa", "revisado": False,
                        "nota": str(p.get("motivo", ""))})  # fmt: skip
    return sorted(out, key=lambda t: (t["inicio"], t["fim"]))


def relatorio(trechos: list) -> dict:
    """Quanto sai por motivo (so o que esta valendo como corte) e quantas sugestoes foram recusadas."""
    saiu, recusadas = {}, {}
    for t in trechos:
        if t.get("acao") == "cortar":
            saiu[t["motivo"]] = saiu.get(t["motivo"], 0.0) + (t["fim"] - t["inicio"])
        elif t.get("origem") == "auto" and t.get("revisado") and t.get("acao") == "manter":
            recusadas[t["motivo"]] = recusadas.get(t["motivo"], 0) + 1
    return {"saiu": {k: round(v, 1) for k, v in saiu.items()}, "recusadas": recusadas}


def sugestao_de_regra(trechos: list, regras: dict, limite: int = 8) -> str:
    """Se voce recusou muitas sugestoes de um tipo, sugere afrouxar a regra (so sugere; voce decide)."""
    rec = relatorio(trechos)["recusadas"]
    for motivo in ("sem_acao", "silencio", "sem_jogo"):
        if rec.get(motivo, 0) >= limite:
            chave = {"sem_acao": "sem_acao_min", "silencio": "silencio_min", "sem_jogo": "sem_jogo_min"}[motivo]
            atual = float(regras[chave])
            novo = round(atual * 1.35 + 0.5, 1)
            nome = {"sem_acao": "sem ação", "silencio": "silêncio", "sem_jogo": "sem jogo"}[motivo]
            return (f"Você recusou {rec[motivo]} sugestões de \"{nome}\". Quer afrouxar a regra de {atual:g} s para "
                    f"{novo:g} s? (Configurações → Cortes automáticos)")  # fmt: skip
    return ""
