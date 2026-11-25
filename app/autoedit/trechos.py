# Os TRECHOS do arquivo de edicao (desde a 1.9.0) e as contas em cima deles:
#   - resolver(): o que vale no fim, quando trechos se sobrepoem (o que voce fez a mao ganha das sugestoes);
#   - MapaTempo: "tempo no video original -> tempo no video final" (para capitulos, legendas do Short...);
#   - mesclar_reanalise(): analisar de novo SEM perder os seus cortes manuais nem as sugestoes ja revisadas;
#   - Historico: desfazer/refazer sem limite durante a sessao do editor.
# Um trecho: {"inicio", "fim", "acao": manter|cortar|acelerar, "motivo", "origem": auto|manual,
#             "confianca": alta|media|baixa, "revisado": bool, "velocidade" (so no acelerar)}
import copy

ACOES = ("manter", "cortar", "acelerar")
MOTIVOS = ("silencio", "sem_jogo", "sem_acao", "papo_fora", "duvida", "fora_melhores", "manual")
NOMES_MOTIVO = {"silencio": "silêncio", "sem_jogo": "sem jogo", "sem_acao": "sem ação", "papo_fora": "papo fora",
                "duvida": "dúvida", "fora_melhores": "fora dos melhores", "manual": "manual"}  # fmt: skip


def prioridade(t: dict) -> int:
    """O que voce decidiu (manual ou sugestao revisada) vale mais que a sugestao automatica."""
    return 2 if t.get("origem") == "manual" or t.get("revisado") else 1


def normalizar(trechos, duracao: float | None = None) -> list:
    """Confere a lista vinda do arquivo (tempos, acoes); item ruim e descartado."""
    out = []
    for t in trechos or []:
        if not isinstance(t, dict):
            continue
        try:
            a, b = float(t["inicio"]), float(t["fim"])
        except (KeyError, TypeError, ValueError):
            continue
        if duracao:
            a, b = max(0.0, a), min(float(duracao), b)
        if b - a < 0.05:
            continue
        item = {"inicio": round(a, 3), "fim": round(b, 3),
                "acao": t.get("acao") if t.get("acao") in ACOES else "cortar",
                "motivo": t.get("motivo") if t.get("motivo") in MOTIVOS else "manual",
                "origem": "manual" if t.get("origem") == "manual" else "auto",
                "confianca": t.get("confianca") if t.get("confianca") in ("alta", "media", "baixa") else "media",
                "revisado": bool(t.get("revisado"))}  # fmt: skip
        if item["acao"] == "acelerar":
            try:
                item["velocidade"] = min(4.0, max(1.1, float(t.get("velocidade", 2.0))))
            except (TypeError, ValueError):
                item["velocidade"] = 2.0
        for extra in ("nota", "forcar", "rodada"):
            if t.get(extra):
                item[extra] = t[extra]
        out.append(item)
    return sorted(out, key=lambda t: (t["inicio"], t["fim"]))


def resolver(trechos, duracao: float, protegidos=()) -> list:
    """[(inicio, fim, acao, velocidade)] do que SAI ou ACELERA (sem os 'manter'), sem sobreposicao, em ordem.
    protegidos = [(a, b)] (introducao, momentos que o Claude mandou manter): sugestao automatica nao corta ali;
    so um corte manual com "forcar" (voce confirmou)."""
    lista = [t for t in trechos or [] if t["fim"] > t["inicio"]]
    if not lista:
        return []
    bordas = {0.0, float(duracao)}
    for t in lista:
        bordas.update((max(0.0, t["inicio"]), min(float(duracao), t["fim"])))
    for a, b in protegidos:
        bordas.update((max(0.0, a), min(float(duracao), b)))
    bordas = sorted(b for b in bordas if 0 <= b <= duracao)
    # varredura em ordem de tempo (desde a 1.11.1): cada pedaco so compara com os trechos que estao "abertos" ali.
    # Antes comparava com TODOS: com milhares de sugestoes (live de 9 h) levava segundos e travava o editor.
    ordem = sorted(range(len(lista)), key=lambda k: lista[k]["inicio"])
    proximo, abertos = 0, []
    pedacos = []
    for a, b in zip(bordas, bordas[1:]):
        if b - a < 1e-6:
            continue
        meio = (a + b) / 2
        while proximo < len(ordem) and lista[ordem[proximo]]["inicio"] <= meio:
            abertos.append(ordem[proximo])
            proximo += 1
        abertos = [k for k in abertos if lista[k]["fim"] > meio]
        vencedor = None
        for k in abertos:
            chave = (prioridade(lista[k]), k)
            if vencedor is None or chave > vencedor[0]:
                vencedor = (chave, lista[k])
        if vencedor is None:
            continue
        t = vencedor[1]
        if t["acao"] == "manter":
            continue
        protegido = any(pa <= meio < pb for pa, pb in protegidos)
        if protegido and not (t.get("origem") == "manual" and t.get("forcar")):
            continue
        vel = float(t.get("velocidade", 2.0)) if t["acao"] == "acelerar" else 1.0
        if pedacos and abs(pedacos[-1][1] - a) < 1e-6 and pedacos[-1][2] == t["acao"] and pedacos[-1][3] == vel:
            pedacos[-1] = (pedacos[-1][0], b, t["acao"], vel)
        else:
            pedacos.append((a, b, t["acao"], vel))
    return [(round(a, 3), round(b, 3), acao, vel) for a, b, acao, vel in pedacos]


class MapaTempo:
    """Tempo no video original -> tempo no video final (depois dos cortes e das aceleracoes).
    inicio = de onde o video final comeca (Short: o inicio do corte; longo: 0)."""

    def __init__(self, resolvidos: list, inicio: float = 0.0, fim: float | None = None):
        self.inicio = float(inicio)
        self.fim = fim
        self.pedacos = [(a, b, acao, vel) for a, b, acao, vel in resolvidos if b > self.inicio
                        and (fim is None or a < fim)]  # fmt: skip
        # tabelas para achar a resposta por bissecao (desde a 1.11.1; antes percorria todos os cortes a cada
        # chamada, e a linha do tempo "como ficou" chama isto milhares de vezes por desenho)
        self._p = sorted((max(a, self.inicio), b if fim is None else min(b, fim), acao, vel)
                         for a, b, acao, vel in self.pedacos)  # fmt: skip
        self._inicios = [a for a, _, _, _ in self._p]
        self._perda_antes = [0.0]  # perda_antes[i] = quanto os pedacos 0..i-1 tiram do video
        for a, b, acao, vel in self._p:
            self._perda_antes.append(self._perda_antes[-1] + self._perda(a, b, b, acao, vel))
        self._final_ini = [a - self.inicio - self._perda_antes[i] for i, (a, _, _, _) in enumerate(self._p)]
        self._inteiros = sorted(self.pedacos)  # sem aparar no inicio/fim (para o cortado(), como antes)
        self._inicios_inteiros = [a for a, _, _, _ in self._inteiros]

    @staticmethod
    def _perda(a, b, t, acao, vel) -> float:
        """Quanto o pedaco [a, b) tira do video ate o instante t."""
        dentro = min(t, b) - a
        return dentro if acao == "cortar" else dentro * (1 - 1 / vel)

    def final(self, t: float) -> float:
        """Onde o instante t (do original) cai no video final. Dentro de um corte = o ponto da emenda."""
        from bisect import bisect_left

        t = float(t)
        x = max(0.0, t - self.inicio)
        i = bisect_left(self._inicios, t)  # pedacos 0..i-1 comecam antes de t
        if i:
            a, b, acao, vel = self._p[i - 1]
            x -= self._perda_antes[i - 1] + self._perda(a, b, t, acao, vel)
        return round(x, 4)

    def original(self, u: float) -> float:
        """O contrario de final(): o instante u do video final -> onde ele esta no original (pula os cortes).
        Usado pela linha do tempo "como ficou" do editor (as partes que saem somem dela)."""
        from bisect import bisect_left

        u = max(0.0, float(u))
        j = bisect_left(self._final_ini, u) - 1  # o ultimo pedaco que comeca antes de u (no video final)
        if j < 0:
            t = self.inicio + u
        else:
            a, b, acao, vel = self._p[j]
            if acao != "cortar" and u <= self._final_ini[j] + (b - a) / vel:  # dentro de um trecho acelerado
                return round(a + (u - self._final_ini[j]) * vel, 4)
            fim_final = self._final_ini[j] + (0.0 if acao == "cortar" else (b - a) / vel)
            t = b + (u - fim_final)  # no pedaco que fica inteiro, depois deste
        return round(t if self.fim is None else min(self.fim, t), 4)

    def cortado(self, t: float) -> bool:
        from bisect import bisect_right

        i = bisect_right(self._inicios_inteiros, t) - 1  # o pedaco que comeca em t ou antes (nao se sobrepoem)
        if i < 0:
            return False
        a, b, acao, _ = self._inteiros[i]
        return a <= t < b and acao == "cortar"

    def duracao_final(self, fim: float) -> float:
        return self.final(fim)

    def palavras(self, palavras: list) -> list:
        """Palavras {i, f, ...} no tempo final; as que estao dentro de um trecho cortado somem da legenda."""
        out = []
        for w in palavras:
            meio = (float(w["i"]) + float(w["f"])) / 2
            if self.cortado(meio):
                continue
            i, f = self.final(w["i"]), self.final(w["f"])
            out.append({**w, "i": i, "f": max(i + 0.01, f)})
        return out


def mesclar_reanalise(antigos: list, novos: list) -> list:
    """Analisar de novo: ficam os seus (manuais e revisados); as sugestoes novas entram onde nao batem com eles."""
    meus = [t for t in antigos or [] if t.get("origem") == "manual" or t.get("revisado")]
    out = list(meus)
    for n in novos:
        if not any(n["inicio"] < m["fim"] and n["fim"] > m["inicio"] for m in meus):
            out.append(n)
    return sorted(out, key=lambda t: (t["inicio"], t["fim"]))


def duracao_final(trechos, duracao: float, protegidos=(), extras_cortados=()) -> float:
    """Quanto o video vai ter depois dos cortes (extras_cortados = cortes do Claude ja resolvidos [(a, b)])."""
    res = resolver(trechos, duracao, protegidos)
    res = res + [(a, b, "cortar", 1.0) for a, b in extras_cortados]
    res = _sem_sobrepor(res)
    return MapaTempo(res).final(duracao)


def _sem_sobrepor(pedacos: list) -> list:
    """Junta pedacos (cortar vence acelerar) para a conta da duracao nao contar duas vezes."""
    bordas = sorted({x for a, b, _, _ in pedacos for x in (a, b)})
    # varredura em ordem (como no resolver): rapido com milhares. (k, pedaco): k guarda a ordem original
    ordem = sorted(enumerate(pedacos), key=lambda kp: kp[1][0])
    proximo, abertos = 0, []
    out = []
    for a, b in zip(bordas, bordas[1:]):
        meio = (a + b) / 2
        while proximo < len(ordem) and ordem[proximo][1][0] <= meio:
            abertos.append(ordem[proximo])
            proximo += 1
        abertos = [kp for kp in abertos if kp[1][1] > meio]
        cobre = [p for _, p in sorted(abertos)]
        if not cobre:
            continue
        p = next((c for c in cobre if c[2] == "cortar"), cobre[0])
        if out and abs(out[-1][1] - a) < 1e-6 and out[-1][2:] == p[2:]:
            out[-1] = (out[-1][0], b, p[2], p[3])
        else:
            out.append((a, b, p[2], p[3]))
    return out


class Historico:
    """Desfazer/refazer sem limite: guarda uma copia do estado antes de cada mudanca."""

    def __init__(self, estado):
        self.atual = copy.deepcopy(estado)
        self._antes, self._depois = [], []

    def mudar(self, novo):
        self._antes.append(self.atual)
        self.atual = copy.deepcopy(novo)
        self._depois.clear()

    def desfazer(self):
        if not self._antes:
            return None
        self._depois.append(self.atual)
        self.atual = self._antes.pop()
        return copy.deepcopy(self.atual)

    def refazer(self):
        if not self._depois:
            return None
        self._antes.append(self.atual)
        self.atual = self._depois.pop()
        return copy.deepcopy(self.atual)

    def pode_desfazer(self) -> bool:
        return bool(self._antes)

    def pode_refazer(self) -> bool:
        return bool(self._depois)
