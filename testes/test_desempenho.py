# Testes de DESEMPENHO do editor (vem depois da 1.11.0): numa live de 9 h com milhares de sugestoes, as contas de
# "o que sai" (resolver), "quanto dura" (duracao_final) e "onde cai no video final" (MapaTempo) travavam o app:
# comparavam cada pedaco com TODAS as sugestoes. Agora sao varreduras em ordem e bissecao. Aqui: o resultado tem
# que ser IGUAL ao do jeito antigo (que fica copiado aqui so para comparar) e tem que ser rapido.
import random
import time


def _resolver_antigo(trechos, duracao, protegidos=()):
    from autoedit.trechos import prioridade

    lista = [t for t in trechos or [] if t["fim"] > t["inicio"]]
    if not lista:
        return []
    bordas = {0.0, float(duracao)}
    for t in lista:
        bordas.update((max(0.0, t["inicio"]), min(float(duracao), t["fim"])))
    for a, b in protegidos:
        bordas.update((max(0.0, a), min(float(duracao), b)))
    bordas = sorted(b for b in bordas if 0 <= b <= duracao)
    pedacos = []
    for a, b in zip(bordas, bordas[1:]):
        if b - a < 1e-6:
            continue
        meio = (a + b) / 2
        vencedor = None
        for k, t in enumerate(lista):
            if t["inicio"] <= meio < t["fim"]:
                chave = (prioridade(t), k)
                if vencedor is None or chave > vencedor[0]:
                    vencedor = (chave, t)
        if vencedor is None:
            continue
        t = vencedor[1]
        if t["acao"] == "manter":
            continue
        if any(pa <= meio < pb for pa, pb in protegidos) and not (t.get("origem") == "manual" and t.get("forcar")):
            continue
        vel = float(t.get("velocidade", 2.0)) if t["acao"] == "acelerar" else 1.0
        if pedacos and abs(pedacos[-1][1] - a) < 1e-6 and pedacos[-1][2] == t["acao"] and pedacos[-1][3] == vel:
            pedacos[-1] = (pedacos[-1][0], b, t["acao"], vel)
        else:
            pedacos.append((a, b, t["acao"], vel))
    return [(round(a, 3), round(b, 3), acao, vel) for a, b, acao, vel in pedacos]


def _final_antigo(pedacos, inicio, fim, t):
    x = max(0.0, float(t) - inicio)
    for a, b, acao, vel in pedacos:
        a, b = max(a, inicio), b if fim is None else min(b, fim)
        if t <= a:
            break
        dentro = min(t, b) - a
        x -= dentro if acao == "cortar" else dentro * (1 - 1 / vel)
    return round(x, 4)


def _trechos_aleatorios(n, duracao, semente):
    from autoedit import trechos as tr

    r = random.Random(semente)
    lista = []
    for _ in range(n):
        a = r.uniform(0, duracao)
        acao = r.choice(["cortar", "cortar", "cortar", "manter", "acelerar"])
        lista.append({"inicio": a, "fim": a + r.uniform(0.5, 60), "acao": acao, "motivo": "silencio",
                      "origem": r.choice(["auto", "auto", "manual"]), "revisado": r.random() < 0.3,
                      "forcar": r.random() < 0.2, "velocidade": r.choice([1.5, 2.0, 3.0])})  # fmt: skip
    return tr.normalizar(lista, duracao)


def test_resultado_igual_ao_jeito_antigo():
    from autoedit import trechos as tr

    for semente in range(30):
        lista = _trechos_aleatorios(120, 3600.0, semente)
        protegidos = [(100.0, 200.0), (1500.0, 1520.0)]
        novo = tr.resolver(lista, 3600.0, protegidos)
        assert novo == _resolver_antigo(lista, 3600.0, protegidos), semente
        for inicio, fim in ((0.0, None), (300.0, 2000.0)):
            m = tr.MapaTempo(novo, inicio, fim)
            pedacos = m.pedacos
            r = random.Random(semente)
            aleatorios = [r.uniform(0, 3600) for _ in range(200)]
            bordas = [a for a, _, _, _ in novo] + [b for _, b, _, _ in novo]
            for t in aleatorios + bordas:
                assert m.final(t) == _final_antigo(pedacos, inicio, fim, t), (semente, t)
                # ida e volta (longe das emendas: ali o video final "pula" e os dois lados caem no mesmo ponto)
                perto_de_emenda = any(abs(t - x) < 0.01 for x in bordas)
                if t in aleatorios and not perto_de_emenda and not m.cortado(t) and (fim is None or t < fim) and t >= inicio:
                    assert abs(m.original(m.final(t)) - t) < 2e-3, (semente, t)  # ida e volta
                assert m.cortado(t) == any(a <= t < b and acao == "cortar" for a, b, acao, _ in pedacos)


def test_live_de_9_horas_com_milhares_de_sugestoes_e_rapida():
    from autoedit import trechos as tr

    duracao = 9 * 3600.0
    lista = _trechos_aleatorios(6000, duracao, 7)
    inicio = time.perf_counter()
    res = tr.resolver(lista, duracao)
    tr.duracao_final(lista, duracao)
    m = tr.MapaTempo(res)
    for t in lista:  # a linha do tempo "como ficou" chama isto para cada sugestao desenhada
        m.final(t["inicio"])
        m.original(m.final(t["fim"]))
        m.cortado(t["inicio"])
    assert time.perf_counter() - inicio < 2.0  # o jeito antigo levava dezenas de segundos aqui


def test_bordas_fora_das_palavras_igual_ao_antigo_e_rapido():
    """_sem_cortar_palavra / _tem_palavra (cada corte olhava as ~80 mil palavras da live): agora so as de perto."""
    from autoedit import decidir_cortes as dc

    def antigo(palavras, a, b):
        for i, f in palavras:
            if i < a < f:
                a = f
            if i < b < f:
                b = i
        return a, b

    r = random.Random(5)
    for _ in range(100):
        palavras, t = [], 0.0
        for _ in range(200):
            t += r.uniform(0, 2)
            palavras.append((t, t + r.uniform(0.05, 3)))
        linha = dc.Linha(0, t + 5, palavras)
        for _ in range(30):
            a = r.uniform(0, t)
            b = a + r.uniform(-1, 20)
            assert dc._sem_cortar_palavra(linha, a, b) == antigo(linha.palavras, a, b)
            assert dc._tem_palavra(linha, a, b) == any(i < b and f > a for i, f in linha.palavras)
    # live de 9 h (~70 mil palavras), 2 mil cortes: rapido
    palavras = [(x * 0.4, x * 0.4 + 0.3) for x in range(int(9 * 3600 / 0.4))]
    linha = dc.Linha(0, 9 * 3600, palavras)
    inicio = time.perf_counter()
    for k in range(2000):
        dc._sem_cortar_palavra(linha, k * 15.05, k * 15.05 + 4.1)
    assert time.perf_counter() - inicio < 1.0
