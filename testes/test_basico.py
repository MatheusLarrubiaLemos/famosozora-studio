# Testes rapidos (segundos): tempos, versoes, pastas, correcoes, censura, cortes.json v2,
# duracao do Short, legendas editadas, edicao do video longo e limpeza de projeto.
# Rodar: python -m pytest            (na pasta do repositorio)
import json
from fractions import Fraction
from pathlib import Path

import pytest
from conftest import PASTA_TRABALHO

from nucleo import comum
from nucleo.atualizacao import eh_mais_nova, numero_versao
from nucleo.limpeza import midia_do_projeto, tamanho_txt


# ------------------------------------------------------------------ tempos e textos
@pytest.mark.parametrize(
    "valor, segundos",
    [(123.4, 123.4), ("123.4", 123.4), ("02:03.5", 123.5), ("01:02:03.5", 3723.5), ("1:02,5", 62.5), (7, 7.0)],
)
def test_ler_tempo(valor, segundos):
    assert comum.ler_tempo(valor) == pytest.approx(segundos)


def test_tempo_txt():
    assert comum.tempo_txt(3723.5) == "01:02:03"
    assert comum.tempo_txt(3723.5, ms=True) == "01:02:03.500"
    assert comum.tempo_txt(-5) == "00:00:00"


def test_nome_seguro_tira_simbolos_proibidos_e_emoji():
    assert comum.nome_seguro('Ele explodiu? "Sim" / não 😂') == "Ele explodiu Sim não"
    assert comum.nome_seguro("   ") == "sem_nome"


# ------------------------------------------------------------------ versoes (aviso de atualizacao)
@pytest.mark.parametrize(
    "remota, local, nova",
    [("1.10.0", "1.9.9", True), ("v1.3.0", "1.3.0", False), ("1.3.1", "1.3.0", True), ("1.2.0", "1.3.0", False),
     ("2", "1.9", True), ("1.3", "1.3.0", False)],
)  # fmt: skip
def test_comparar_versoes(remota, local, nova):
    assert eh_mais_nova(remota, local) is nova


def test_numero_versao():
    assert numero_versao("v1.10.2") == (1, 10, 2)
    assert numero_versao("1.3") == (1, 3, 0)


# ------------------------------------------------------------------ pastas
def test_pasta_de_trabalho_vem_do_ajustes_json():
    assert comum.PASTA_CANAL == PASTA_TRABALHO
    assert comum.PASTA_SHORTS == PASTA_TRABALHO / "shorts"
    assert comum.PASTA_VIDEOS == PASTA_TRABALHO / "videos"


def test_configuracoes_nao_ficam_na_pasta_de_trabalho():
    assert PASTA_TRABALHO not in comum.PASTA_CONFIG.parents
    assert PASTA_TRABALHO not in comum.PASTA_MUSICAS.parents


def test_modo_desenvolvedor_usa_as_configuracoes_do_github():
    assert not comum.APP_INSTALADO
    assert comum.PASTA_CONFIG == comum.PASTA_PADRAO
    assert (comum.PASTA_PADRAO / "config.json").exists()


def test_preparar_pasta_de_trabalho_cria_so_as_pastas_de_producao():
    comum.preparar_pasta_trabalho()
    assert (PASTA_TRABALHO / "shorts").is_dir() and (PASTA_TRABALHO / "videos").is_dir()
    assert not (PASTA_TRABALHO / "configuracoes").exists()


def test_gravar_json_a_prova_de_queda(tmp_path):
    arq = tmp_path / "x.json"
    comum.gravar_json(arq, {"a": 1})
    comum.gravar_json(arq, {"a": 2, "texto": "ação"})
    assert comum.ler_json(arq) == {"a": 2, "texto": "ação"}
    assert not list(tmp_path.glob("*.gravando"))


def test_ler_json_com_erro_devolve_o_padrao(tmp_path):
    (tmp_path / "ruim.json").write_text("{ isso nao e json", encoding="utf-8")
    assert comum.ler_json(tmp_path / "ruim.json", "padrao") == "padrao"


# ------------------------------------------------------------------ correcoes
def test_correcoes_do_pc_valem_por_cima_das_do_programa(config_temporaria):
    (config_temporaria / "correcoes.txt").write_text(
        "sacolhou = chacoalhou\nvelhu = velho  # comentario\n", encoding="utf-8"
    )
    correcoes = comum.ler_correcoes()
    assert correcoes["sacolhou"] == "chacoalhou"  # o padrao do programa diz "sacudiu"
    assert correcoes["velhu"] == "velho"
    assert correcoes["becicleta"] == "bicicleta"  # continua valendo a do programa


def test_aplicar_correcoes_mantem_a_pontuacao():
    from shorts.legendas import aplicar_correcoes

    palavras = [{"i": 0, "f": 1, "p": "Becicleta,"}, {"i": 1, "f": 2, "p": "nova"}]
    assert [w["p"] for w in aplicar_correcoes(palavras, {"becicleta": "bicicleta"})] == ["bicicleta,", "nova"]


def test_sugestoes_e_gravacao_no_correcoes_txt(config_temporaria):
    from shorts.revisao import gravar_correcoes, sugestoes_de_correcao

    antes = [{"i": 0, "f": 1, "p": "Mano,"}, {"i": 1, "f": 2, "p": "becicleta"}, {"i": 2, "f": 3, "p": "nova"}]
    depois = [{"i": 0, "f": 1, "p": "Mano,"}, {"i": 1, "f": 2, "p": "bicicleta"}, {"i": 2, "f": 3, "p": "nova"}]
    pares = sugestoes_de_correcao(antes, depois)
    assert pares == [("becicleta", "bicicleta")]
    assert gravar_correcoes(pares) == 1
    assert gravar_correcoes(pares) == 0  # nao repete
    assert "becicleta = bicicleta" in (config_temporaria / "correcoes.txt").read_text(encoding="utf-8")


# ------------------------------------------------------------------ censura
def test_mascarar_mantem_pontuacao():
    from shorts.censura import mascarar

    assert mascarar("porra!") == "p***!"
    assert mascarar('"Caralho,') == '"C***,'
    assert mascarar("...") == "..."


def test_censura_pela_lista_so_quando_ligada(config_temporaria):
    from shorts.censura import adicionar_a_lista, aplicar

    assert adicionar_a_lista("Puta que pariu") is True
    assert adicionar_a_lista("puta que PARIU!") is False  # ja estava
    palavras = [{"i": 0, "f": 1, "p": "Puta"}, {"i": 1, "f": 2, "p": "que"}, {"i": 2, "f": 3, "p": "pariu,"},
                {"i": 3, "f": 4, "p": "mano"}]  # fmt: skip
    assert [w["p"] for w in aplicar(palavras, usar_lista=False)] == ["Puta", "que", "pariu,", "mano"]
    assert [w["p"] for w in aplicar(palavras, usar_lista=True)] == ["P***", "q***", "p***,", "mano"]
    assert palavras[0]["p"] == "Puta"  # nao muda a lista original


def test_censura_avulsa_e_trechos_para_calar():
    from shorts.censura import aplicar, trechos_para_calar

    palavras = [{"i": 1.0, "f": 1.3, "p": "essa"}, {"i": 1.3, "f": 1.6, "p": "porra", "cx": True},
                {"i": 1.6, "f": 2.0, "p": "aqui", "cx": True}]  # fmt: skip
    censuradas = aplicar(palavras, usar_lista=False)
    assert [w["p"] for w in censuradas] == ["essa", "p***", "a***"]
    trechos = trechos_para_calar([(10.0, censuradas, 5.0)])
    assert len(trechos) == 1  # palavras vizinhas viram um trecho so
    assert trechos[0] == pytest.approx((11.26, 12.04))


# ------------------------------------------------------------------ cortes.json v2 e duracao do Short
def _projeto_falso(pasta: Path, cortes) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    video = pasta / "video.mp4"
    video.write_bytes(b"")
    comum.gravar_json(pasta / "projeto.json", {"video": str(video)})
    comum.gravar_json(pasta / "transcricao.json", {"segmentos": []})
    (pasta / "cortes.json").write_text(cortes if isinstance(cortes, str) else json.dumps(cortes), encoding="utf-8")
    return pasta


def test_ler_cortes_json_v2(tmp_path):
    from shorts.gerar_shorts import carregar_projeto

    cortes = {
        "versao": 2,
        "correcoes": {"zora": "Zora"},
        "cortes": [{"inicio": "00:26:27", "fim": "00:26:41.5", "titulo": "A água EXPLODIU",
                    "abertura": {"inicio": "00:26:35", "fim": "00:26:37"}, "legenda": "Mano, eu abri [[água]]"}],
    }  # fmt: skip
    proj = carregar_projeto(_projeto_falso(tmp_path / "p", cortes))
    assert len(proj["cortes"]) == 1 and proj["cortes"][0]["titulo"] == "A água EXPLODIU"
    assert proj["correcoes"]["zora"] == "Zora" and proj["correcoes"]["becicleta"] == "bicicleta"


def test_cortes_json_antigo_lista_simples(tmp_path):
    from shorts.gerar_shorts import carregar_projeto

    proj = carregar_projeto(_projeto_falso(tmp_path / "p", [{"inicio": 10, "fim": 20}]))
    assert proj["cortes"] == [{"inicio": 10, "fim": 20}]


def test_cortes_json_com_erro_para_com_mensagem(tmp_path, capsys):
    from shorts.gerar_shorts import carregar_projeto

    with pytest.raises(SystemExit):
        carregar_projeto(_projeto_falso(tmp_path / "p", '{"cortes": [ {"inicio": 1 "fim": 2} ]}'))
    assert "erro de formatacao" in capsys.readouterr().out


def test_lista_de_projetos_mostra_cortes_json_com_erro(tmp_path, monkeypatch):
    from nucleo import projetos

    _projeto_falso(tmp_path / "quebrado", "{ nao e json")
    monkeypatch.setattr(projetos, "PASTA_SHORTS", tmp_path)
    info = {i["nome"]: i for i in projetos.listar_projetos()}["quebrado"]
    assert "erro de formatação" in info["passo"]


def test_duracao_do_short_abertura_corte_final_menos_transicao():
    from shorts.gerar_shorts import CFG, medir_corte
    from shorts.montagem import duracao_transicao

    c = {"inicio": "00:01:00", "fim": "00:01:30", "titulo": "x", "abertura": {"inicio": "00:01:10", "fim": "00:01:14"}}
    m = medir_corte(c, 1, dur_video=3600)
    D = duracao_transicao()
    final = float(CFG["duracao_final"])
    assert m["dur"] == 30 and m["abertura"] == (70, 4)
    assert m["total"] == pytest.approx(4 + 30 + final - D)
    sem_abertura = medir_corte({"inicio": 60, "fim": 90}, 2, dur_video=3600)
    assert sem_abertura["total"] == pytest.approx(30 + final)


def test_final_nao_passa_do_fim_do_video():
    from shorts.gerar_shorts import medir_corte

    assert medir_corte({"inicio": 50, "fim": 59}, 1, dur_video=60)["final"] == pytest.approx(1.0)


# ------------------------------------------------------------------ legendas editadas
def _palavras():
    textos = ["Mano,", "eu", "abri", "a", "água.", "Explodiu", "tudo,", "velho."]
    return [{"i": k * 0.4, "f": k * 0.4 + 0.3, "p": t} for k, t in enumerate(textos)]


def test_dividir_em_linhas_quebra_no_fim_da_frase():
    from shorts.revisao import dividir_em_linhas, texto_da_linha

    palavras = _palavras()
    linhas = dividir_em_linhas(palavras)
    assert [texto_da_linha(palavras, x) for x in linhas] == ["Mano, eu abri a água.", "Explodiu tudo, velho."]


def test_trocar_texto_mesma_quantidade_mantem_os_tempos():
    from shorts.revisao import dividir_em_linhas, trocar_texto_da_linha

    palavras = _palavras()
    palavras[4]["inc"] = True
    novas = trocar_texto_da_linha(palavras, dividir_em_linhas(palavras)[0], "Cara, eu abri a garrafa.")
    assert [w["p"] for w in novas[:5]] == ["Cara,", "eu", "abri", "a", "garrafa."]
    assert [(w["i"], w["f"]) for w in novas] == [(w["i"], w["f"]) for w in palavras]
    assert "inc" not in novas[4]  # conferida a mao: deixa de ser incerta


def test_trocar_texto_com_mais_palavras_reparte_o_tempo():
    from shorts.revisao import dividir_em_linhas, trocar_texto_da_linha

    palavras = _palavras()
    novas = trocar_texto_da_linha(palavras, dividir_em_linhas(palavras)[1], "Explodiu tudo aqui, velho.")
    assert len(novas) == len(palavras) + 1
    assert novas[5]["i"] == pytest.approx(palavras[5]["i"]) and novas[-1]["f"] == pytest.approx(palavras[-1]["f"])
    assert all(a["i"] <= b["i"] for a, b in zip(novas, novas[1:]))


def test_legenda_original_e_editada_ficam_separadas(tmp_path):
    from shorts import revisao

    revisao.salvar_original(tmp_path, 3, "03 - x.mp4", 10.0, 20.0, _palavras())
    assert revisao.ler_editada(tmp_path, 3) is None
    editadas = _palavras()
    editadas[0]["p"] = "Cara,"
    revisao.salvar_editada(tmp_path, 3, editadas, censurar_lista=True)
    assert revisao.ler_original(tmp_path, 3)["palavras"][0]["p"] == "Mano,"
    assert revisao.ler_editada(tmp_path, 3)["palavras"][0]["p"] == "Cara,"
    revisao.apagar_editada(tmp_path, 3)
    assert revisao.ler_editada(tmp_path, 3) is None


# ------------------------------------------------------------------ video longo (edicao.json)
def test_edicao_junta_cortes_sobrepostos_e_recusa_tempo_fora_do_video():
    from videos_longos.pedido_edicao import normalizar

    dados, erros, avisos = normalizar(
        {
            "cortes": [
                {"inicio": "00:01:00", "fim": "00:03:00"},
                {"inicio": "00:02:00", "fim": "00:04:00", "motivo": "b"},
            ]
        },
        3600,
    )
    assert not erros and dados["cortes"] == [{"inicio": "00:01:00", "fim": "00:04:00", "motivo": "b"}]
    _, erros, _ = normalizar({"cortes": [{"inicio": "02:00:00", "fim": "02:01:00"}]}, 3600)
    assert "fora do vídeo" in erros[0]


def test_edicao_json_colado_com_bloco_de_codigo():
    from videos_longos.pedido_edicao import extrair_json

    assert extrair_json('Aqui está:\n```json\n{"cortes": []}\n```\nAbraço') == {"cortes": []}


def test_capitulos_seguem_as_regras_do_youtube():
    from videos_longos.pedido_edicao import capitulos_editados, montar_plano

    dados = {
        "cortes": [{"inicio": "00:00:00", "fim": "00:01:00"}],
        "capitulos": [{"inicio": "00:01:10", "titulo": "Começo"}, {"inicio": "00:05:00", "titulo": "Meio"},
                      {"inicio": "00:05:05", "titulo": "Colado"}, {"inicio": "00:09:58", "titulo": "Fim"}],
    }  # fmt: skip
    plano = montar_plano(dados, 600, Fraction(30), palavras=None, cfg={"episodio_ajuste_silencio": 0})
    caps, avisos = capitulos_editados(dados, plano)
    assert [c[1] for c in caps] == ["Começo", "Meio"]  # "Colado" (5 s depois do Meio) e "Fim" (<10 s do fim) saem
    assert caps[0][0] == 0.0 and caps[1][0] == pytest.approx(240.0)
    assert any("3 ou mais" in a for a in avisos)


# ------------------------------------------------------------------ limpar projeto
def test_limpeza_so_pega_a_midia_e_guarda_o_resumo(tmp_path):
    p = tmp_path / "proj"
    (p / "prontos" / "antigos" / "2026").mkdir(parents=True)
    (p / "episodio" / "_temp").mkdir(parents=True)
    (p / "prontos" / "01 - a.mp4").write_bytes(b"x" * 1000)
    (p / "prontos" / "publicacao.json").write_text("{}", encoding="utf-8")
    (p / "episodio" / "ep.mp4").write_bytes(b"x" * 500)
    (p / "episodio" / "textos_episodio.txt").write_text("t", encoding="utf-8")
    (p / "cortes.json").write_text("{}", encoding="utf-8")
    nomes = sorted(f.name for f, _ in midia_do_projeto(p))
    assert nomes == ["01 - a.mp4", "_temp", "antigos", "ep.mp4"]
    assert tamanho_txt(2_500_000_000) == "2,5 GB" and tamanho_txt(6_000_000) == "6 MB"
