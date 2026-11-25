# Testes do "como ficou" e do "Cortar mais" do editor de video (vem depois da 1.10.0): a linha do tempo mostra o video
# ja cortado (conta de ida e volta entre o tempo do original e o do video final) e cada rodada do "Cortar mais" usa
# regras mais rigidas e so poe sugestoes no que ainda fica no video.


def test_mapa_de_tempo_vai_e_volta():
    """Original -> final -> original da o mesmo ponto (fora dos cortes); dentro de um corte cai na emenda."""
    from autoedit.trechos import MapaTempo

    m = MapaTempo([(10, 20, "cortar", 1.0), (30, 40, "acelerar", 2.0), (50, 55, "cortar", 1.0)], 0, 100)
    for t in (0, 5, 9.9, 25, 30, 35, 40, 45, 70, 100):  # (bem na borda de um corte o ponto e ambiguo)
        assert abs(m.original(m.final(t)) - t) < 1e-3, t
    assert m.final(15) == 10  # dentro do corte: o ponto da emenda
    assert m.original(10) in (10.0, 20.0)  # a emenda (fim do que fica antes ou comeco do depois)
    assert m.final(100) == 100 - 10 - 5 - 5  # 10 s cortados, 10 s a 2x (=5 s a menos), mais 5 s cortados
    assert m.original(999) == 100  # nao passa do fim


def test_regras_mais_rigidas_a_cada_rodada():
    from autoedit import predefinicoes

    base = predefinicoes.da("longo")
    r2, r3 = predefinicoes.mais_rigida(base, 2), predefinicoes.mais_rigida(base, 3)
    assert r2["silencio_min"] < base["silencio_min"] and r3["silencio_min"] <= r2["silencio_min"]
    assert r2["sem_acao_min"] < base["sem_acao_min"] and r3["sem_jogo_min"] >= 1.5  # nunca abaixo do minimo
    assert r2["silencio_so_sem_acao"] is False  # da 2a rodada em diante, corta silencio mesmo durante o jogo
    assert "rodada 2" in r2["nome"] and base["nome"] in r2["nome"]
    assert predefinicoes.mais_rigida(base, 1)["silencio_min"] == base["silencio_min"]


def test_cortar_mais_so_no_que_ficou():
    """A rodada nova so entra onde o video ainda esta: nada em cima do que ja sai nem do que voce ja decidiu."""
    from autoedit import predefinicoes
    from editor.estado import EstadoEditor

    trechos = [{"inicio": 10, "fim": 20, "acao": "cortar", "motivo": "silencio", "origem": "auto", "revisado": True},
               {"inicio": 60, "fim": 70, "acao": "manter", "motivo": "silencio", "origem": "auto", "revisado": True}]  # fmt: skip
    e = EstadoEditor("longo", 100.0, predefinicoes.da("longo"), trechos)
    antes = e.duracao_final()
    novas = e.cortar_mais([
        {"inicio": 12, "fim": 18, "acao": "cortar", "motivo": "silencio"},  # ja sai: ignora
        {"inicio": 62, "fim": 66, "acao": "cortar", "motivo": "silencio"},  # voce recusou ali: ignora
        {"inicio": 30, "fim": 34, "acao": "cortar", "motivo": "sem_acao"},  # novo, no que ficou: entra
    ], rodada=2)  # fmt: skip
    assert [(n["inicio"], n["fim"], n["rodada"]) for n in novas] == [(30, 34, 2)]
    # sugestao ainda nao revisada ja conta como corte (ate voce recusar), como as da 1a rodada
    assert not novas[0]["revisado"] and e.duracao_final() == antes - 4
    e.recusar(next(k for k, t in enumerate(e.trechos) if t["inicio"] == 30))
    assert e.duracao_final() == antes
    assert e.desfazer() and e.desfazer() and len(e.trechos) == 2  # da para desfazer a rodada
