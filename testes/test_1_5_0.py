# Testes da versao 1.5.0 (rapidos, sem abrir janelas): editor de legendas (inserir, excluir e mudar o tempo
# de uma linha), Short descartado, Lixeira.
import pytest

from shorts import revisao
from shorts.cortes import descartar_corte, escolhidos, ler_cortes


def _palavras():
    # duas linhas: "Oi tudo bem." (10 a 11.5) e "Vamos jogar" (13 a 14)
    return [{"i": 10.0, "f": 10.4, "p": "Oi"}, {"i": 10.5, "f": 11.0, "p": "tudo"}, {"i": 11.1, "f": 11.5, "p": "bem."},
            {"i": 13.0, "f": 13.4, "p": "Vamos"}, {"i": 13.5, "f": 14.0, "p": "jogar"}]  # fmt: skip


def test_mudar_tempo_da_linha_mantem_a_proporcao():
    p = _palavras()
    linhas = revisao.dividir_em_linhas(p)
    novas = revisao.mudar_tempo_da_linha(p, linhas[0], 9.0, 12.0)
    assert novas[0]["i"] == 9.0 and novas[2]["f"] == 12.0
    assert novas[0]["f"] < novas[1]["i"]  # a ordem das palavras continua
    assert novas[3] == p[3]  # a outra linha nao muda


@pytest.mark.parametrize("ini,fim", [(9.0, 13.5), (11.0, 11.05)])
def test_mudar_tempo_invalido(ini, fim):
    p = _palavras()
    with pytest.raises(ValueError):
        revisao.mudar_tempo_da_linha(p, revisao.dividir_em_linhas(p)[0], ini, fim)


def test_inserir_linha_no_espaco_e_sem_espaco():
    p = _palavras()
    linhas = revisao.dividir_em_linhas(p)
    novas, pos = revisao.inserir_linha_depois(p, linhas[0], "nova")
    assert pos == 3 and novas[3]["p"] == "nova" and 11.5 <= novas[3]["i"] < novas[3]["f"] <= 13.0
    assert len(revisao.dividir_em_linhas(novas)) == 3  # virou uma linha separada
    # sem espaco: a linha de baixo comeca logo depois -> encolhe a de cima
    p2 = [dict(w) for w in p]
    p2[3]["i"] = 11.55
    novas2, pos2 = revisao.inserir_linha_depois(p2, revisao.dividir_em_linhas(p2)[0], "x")
    assert novas2[pos2 - 1]["f"] <= novas2[pos2]["i"] < novas2[pos2]["f"] <= 11.5 + 0.001
    # editar o texto da linha nova (com outra quantidade de palavras) nao junta com a de cima
    linhas3 = revisao.dividir_em_linhas(novas)
    trocadas = revisao.trocar_texto_da_linha(novas, linhas3[1], "duas palavras")
    assert len(revisao.dividir_em_linhas(trocadas)) == 3


def test_excluir_linha():
    p = _palavras()
    linhas = revisao.dividir_em_linhas(p)
    assert [w["p"] for w in revisao.excluir_linha(p, linhas[0])] == ["Vamos", "jogar"]
    with pytest.raises(ValueError):
        revisao.excluir_linha(p[:3], [0, 1, 2])  # a unica linha


def test_short_descartado_nao_volta(tmp_path):
    import json

    (tmp_path / "cortes.json").write_text(json.dumps({"versao": 3, "cortes": [{"inicio": 1, "fim": 2},
                                                                              {"inicio": 3, "fim": 4}]}))  # fmt: skip
    assert descartar_corte(tmp_path, 1)
    cortes = ler_cortes(tmp_path)["cortes"]
    assert escolhidos(cortes, None) == {2}
    assert descartar_corte(tmp_path, 1, descartar=False)
    assert escolhidos(ler_cortes(tmp_path)["cortes"], None) == {1, 2}
    assert not descartar_corte(tmp_path, 9)


def test_excluir_short_vai_para_a_lixeira(tmp_path, monkeypatch):
    import json

    from nucleo import limpeza

    lixeira = []
    monkeypatch.setattr(limpeza, "mandar_para_lixeira", lambda c: (lixeira.extend(c), True)[1])
    (tmp_path / "prontos").mkdir()
    (tmp_path / "prontos" / "01 - Um.mp4").write_bytes(b"x")
    (tmp_path / "prontos" / "publicacao.json").write_text(json.dumps({"shorts": [{"n": 1, "arquivo": "01 - Um.mp4"},
                                                                                 {"n": 2, "arquivo": "02.mp4"}]}))  # fmt: skip
    (tmp_path / "cortes.json").write_text(json.dumps({"versao": 3, "cortes": [{"inicio": 1, "fim": 2},
                                                                              {"inicio": 3, "fim": 4}]}))  # fmt: skip
    limpeza.excluir_short(tmp_path, 1, "01 - Um.mp4")
    assert lixeira == [tmp_path / "prontos" / "01 - Um.mp4"]
    pub = json.loads((tmp_path / "prontos" / "publicacao.json").read_text())
    assert [s["n"] for s in pub["shorts"]] == [2]
    assert ler_cortes(tmp_path)["cortes"][0]["descartado"] is True


def test_lixeira_nunca_apaga_de_vez(tmp_path, monkeypatch):
    """Sem conseguir mandar para a Lixeira, o arquivo FICA (nada e apagado de vez)."""
    import send2trash

    from nucleo import limpeza

    arq = tmp_path / "a.mp4"
    arq.write_bytes(b"x")

    def falha(c):
        raise OSError("sem lixeira")

    monkeypatch.setattr(send2trash, "send2trash", falha)
    assert limpeza.mandar_para_lixeira([arq]) is False
    assert arq.exists()


# ------------------------------------------------------------------ Fase 4: excluir pelo app
def _projeto_para_excluir(tmp_path):
    import json

    video = tmp_path / "videos" / "live.mp4"
    video.parent.mkdir()
    video.write_bytes(b"v" * 1000)
    p = tmp_path / "shorts" / "live"
    (p / "prontos" / "antigos").mkdir(parents=True)
    (p / "episodio").mkdir()
    (p / "prontos" / "01 - Um.mp4").write_bytes(b"x" * 300)
    (p / "prontos" / "publicacao.json").write_text("{}")
    (p / "episodio" / "live - episodio.mp4").write_bytes(b"x" * 500)
    (p / "episodio" / "textos.txt").write_text("t")
    (p / "projeto.json").write_text(json.dumps({"video": str(video)}))
    (p / "transcricao.json").write_text("{}")
    return p, video


def test_o_que_cada_opcao_de_excluir_manda_para_a_lixeira(tmp_path):
    from nucleo.limpeza import itens_para_excluir, tamanho_dos_itens

    p, video = _projeto_para_excluir(tmp_path)
    shorts = itens_para_excluir(p, "shorts")
    assert sorted(f.name for f in shorts) == ["01 - Um.mp4", "antigos"]  # o publicacao.json fica
    assert [f.name for f in itens_para_excluir(p, "episodio")] == ["live - episodio.mp4"]  # os textos ficam
    assert itens_para_excluir(p, "projeto") == [p]  # o video original fica
    assert itens_para_excluir(p, "tudo") == [p, video]
    assert tamanho_dos_itens(itens_para_excluir(p, "tudo")) >= 1800
    with pytest.raises(ValueError):
        itens_para_excluir(p, "outra")


def test_excluir_projeto_usa_a_lixeira_e_avisa_se_falhar(tmp_path, monkeypatch):
    from nucleo import limpeza

    p, video = _projeto_para_excluir(tmp_path)
    lixeira = []
    monkeypatch.setattr(limpeza, "mandar_para_lixeira", lambda c: (lixeira.extend(c), True)[1])
    assert limpeza.excluir_projeto(p, "tudo") >= 1800
    assert lixeira == [p, video]
    monkeypatch.setattr(limpeza, "mandar_para_lixeira", lambda c: False)
    with pytest.raises(OSError, match="Lixeira"):
        limpeza.excluir_projeto(p, "projeto")
