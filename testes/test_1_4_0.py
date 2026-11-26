# Testes rapidos da versao 1.4.0: pessoas e cores, edicao por Short, cortes sem numero fixo,
# musica por clima e efeitos sonoros. Rodar: python -m pytest
import pytest

from shorts import edicao, pessoas


@pytest.fixture
def cadastro(tmp_path, monkeypatch):
    """Cadastro de pessoas deste "PC" numa pasta temporaria (o de verdade nao e mexido)."""
    monkeypatch.setattr(pessoas, "PASTA_CONFIG", tmp_path / "configuracoes")
    return tmp_path / "configuracoes"


# ------------------------------------------------------------------ Fase 1: pessoas e cores
def test_cadastro_padrao_tem_so_o_famosozora_branco(cadastro):
    lista = pessoas.ler_pessoas()
    assert lista == [{"nome": "FamosoZora", "cor": "#FFFFFF", "padrao": True}]


def test_falante_sem_nome_e_famosozora_branco(cadastro):
    quem = pessoas.QuemFala({})
    assert quem.pessoa({"p": "oi", "s": 3})["nome"] == "FamosoZora"
    assert quem.pessoa({"p": "oi"})["cor"] == "#FFFFFF"  # sem detector de vozes


def test_voz_ligada_e_troca_na_linha(cadastro):
    pessoas.adicionar("Pedro", "#8CE6FF")
    quem = pessoas.QuemFala({"1": "Pedro"})
    assert quem.pessoa({"s": 1})["nome"] == "Pedro"
    assert quem.pessoa({"s": 0})["nome"] == "FamosoZora"
    assert quem.pessoa({"s": 0, "pessoa": "Pedro"})["nome"] == "Pedro"  # corrigido a mao na linha
    assert quem.pessoa({"s": 1, "pessoa": "Ninguem"})["nome"] == "FamosoZora"  # pessoa que nao existe mais


def test_padrao_nao_pode_ser_excluido_e_pode_ser_trocado(cadastro):
    pessoas.adicionar("Ana", "#FF96C8")
    with pytest.raises(ValueError):
        pessoas.excluir("FamosoZora")
    pessoas.definir_padrao("Ana")
    assert pessoas.pessoa_padrao()["nome"] == "Ana"
    pessoas.excluir("FamosoZora")
    assert [p["nome"] for p in pessoas.ler_pessoas()] == ["Ana"]


def test_nome_repetido_e_cor_invalida(cadastro):
    pessoas.adicionar("Pedro", "zzz")
    assert pessoas.achar("pedro")["cor"] == "#FFFFFF"
    with pytest.raises(ValueError):
        pessoas.adicionar("PEDRO")


def test_renomear_troca_nos_projetos(cadastro, tmp_path):
    from nucleo.comum import gravar_json

    projeto = tmp_path / "shorts" / "live 1"
    (projeto / "legendas").mkdir(parents=True)
    pessoas.adicionar("Pedro")
    pessoas.salvar_ligacoes(projeto, 1, {"0": "Pedro"})
    gravar_json(projeto / "legendas" / "01_editada.json", {"palavras": [{"p": "oi", "pessoa": "Pedro"}]})
    assert pessoas.renomear("Pedro", "Pedrão", tmp_path / "shorts") == 2
    assert pessoas.ler_ligacoes(projeto, 1) == {"0": "Pedrão"}
    assert (projeto / "legendas" / "01_editada.json").read_text(encoding="utf-8").count("Pedrão") == 1


@pytest.mark.parametrize("cor, dificil", [("#FFFFFF", False), ("#00008B", True), ("#8CE6FF", False), ("#000000", True)])
def test_aviso_de_contraste(cor, dificil):
    assert pessoas.dificil_de_ler(cor) == dificil


def test_cor_ass_inverte_para_bgr():
    assert pessoas.cor_ass("#8CE6FF") == "&HFFE68C&"


def test_legenda_usa_cor_da_pessoa_e_mostra_nome(cadastro):
    from shorts.legendas import montar_ass

    pessoas.adicionar("Pedro", "#8CE6FF")
    palavras = [{"i": 0.0, "f": 0.4, "p": "fala", "s": 0}, {"i": 0.5, "f": 0.9, "p": "mano", "s": 0},
                {"i": 1.5, "f": 1.9, "p": "oi", "s": 1}]  # fmt: skip
    blocos = [(0.0, palavras, 3.0)]
    sem_nome = montar_ass(blocos, "", "t", 3.0, None, quem=pessoas.QuemFala({"1": "Pedro"}))
    assert "&HFFE68C&" in sem_nome and "&HFFFFFF&" in sem_nome
    assert "Pedro" not in sem_nome  # nome desligado por padrao
    com_nome = montar_ass(blocos, "", "t", 3.0, None, quem=pessoas.QuemFala({"1": "Pedro"}), mostrar_nome=True)
    falas = [linha for linha in com_nome.splitlines() if linha.startswith("Dialogue: 1,")]
    assert [("Pedro\\N" in linha) for linha in falas] == [False, False, True]  # so quem nao e o FamosoZora


def test_linhas_do_editor_quebram_na_troca_de_pessoa():
    from shorts.revisao import dividir_em_linhas

    palavras = [{"i": 0, "f": 0.3, "p": "a", "s": 0}, {"i": 0.3, "f": 0.6, "p": "b", "s": 0, "pessoa": "Pedro"}]
    assert dividir_em_linhas(palavras) == [[0], [1]]


def test_abertura_separada_ganha_vozes_proprias():
    from shorts.falantes import marcar_palavras

    pa = marcar_palavras([{"i": 0.0, "f": 0.5, "p": "x"}], [(0.0, 1.0, 1)], prefixo="a")
    assert pa[0]["s"] == "a1"


# ------------------------------------------------------------------ edicao por Short
def test_edicao_salvar_restaurar_e_trecho_diferente(tmp_path):
    sug = edicao.vazia(10.0, 40.0)
    edicao.salvar_sugestao(tmp_path, 1, sug)
    minha = edicao.vazia(10.0, 40.0)
    minha["mostrar_nome_falante"] = True
    edicao.salvar_edicao(tmp_path, 1, minha)
    assert edicao.valendo(tmp_path, 1, 10.0, 40.0)["mostrar_nome_falante"] is True
    assert edicao.valendo(tmp_path, 1, 50.0, 80.0) is None  # o Short 01 virou outro trecho: ignora
    edicao.restaurar_sugestao(tmp_path, 1)
    assert edicao.valendo(tmp_path, 1, 10.0, 40.0)["mostrar_nome_falante"] is False


def test_edicao_normaliza_arquivo_incompleto():
    d = edicao.normalizar({"efeitos": [{"tempo": "3"}, {"tempo": None}, {"tempo": 1}], "musica": {"volume": 0.3}})
    assert [e["tempo"] for e in d["efeitos"]] == [1, "3"]
    assert d["musica"] == {"ligada": True, "arquivo": "", "volume": 0.3}


# ------------------------------------------------------------------ Fase 2: cortes sem numero fixo
def _projeto(pasta, cortes):
    import json

    from nucleo.comum import gravar_json

    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "video.mp4").write_bytes(b"")
    gravar_json(pasta / "projeto.json", {"video": str(pasta / "video.mp4")})
    gravar_json(pasta / "transcricao.json", {"segmentos": []})
    (pasta / "cortes.json").write_text(json.dumps(cortes), encoding="utf-8")
    return pasta


@pytest.mark.parametrize(
    "antigo",
    [
        [{"inicio": 1, "fim": 9}],
        {"cortes": [{"inicio": 1, "fim": 9}]},
        {"versao": 2, "cortes": [{"inicio": 1, "fim": 9}]},
    ],
)
def test_migracao_do_cortes_json_guarda_backup(tmp_path, antigo):
    import json

    from shorts.cortes import VERSAO, ler_cortes

    p = _projeto(tmp_path / "p", antigo)
    dados = ler_cortes(p)
    assert dados["versao"] == VERSAO == 3 and dados["cortes"] == [{"inicio": 1, "fim": 9}]
    assert json.loads((p / "cortes.bak.json").read_text(encoding="utf-8")) == antigo  # backup do formato antigo
    assert json.loads((p / "cortes.json").read_text(encoding="utf-8"))["versao"] == 3
    (p / "cortes.json").write_text(json.dumps([{"inicio": 5, "fim": 6}]), encoding="utf-8")
    ler_cortes(p)
    assert json.loads((p / "cortes.bak.json").read_text(encoding="utf-8")) == antigo  # o 1o backup nao e apagado


def test_cortes_json_atual_nao_e_regravado(tmp_path):
    from shorts.cortes import ler_cortes

    p = _projeto(tmp_path / "p", {"versao": 3, "cortes": [], "correcoes": {}})
    ler_cortes(p)
    assert not (p / "cortes.bak.json").exists()


@pytest.mark.parametrize("valor, clima", [("Engraçado", "engracado"), ("ÉPICO", "epico"), ("triste", ""), (None, "")])
def test_clima_normalizado(valor, clima):
    from shorts.cortes import clima_do

    assert clima_do({"clima": valor}) == clima


def test_maximo_e_so_teto_e_fica_com_as_melhores_notas():
    from shorts.cortes import escolhidos, maximo_de_shorts

    cortes = [{"nota": 3}, {"nota": 9}, {"nota": 7}, {}]
    assert escolhidos(cortes, None) == {1, 2, 3, 4}
    assert escolhidos(cortes, 2) == {2, 3}
    assert escolhidos(cortes, 10) == {1, 2, 3, 4}
    assert maximo_de_shorts({"maximo_shorts": None}) is None
    assert maximo_de_shorts({"maximo_shorts": ""}) is None
    assert maximo_de_shorts({"maximo_shorts": 0}) is None
    assert maximo_de_shorts({"maximo_shorts": "8"}) == 8


def test_zero_cortes_sem_erro(tmp_path, monkeypatch, capsys):
    import sys

    from nucleo import projetos
    from shorts import gerar_shorts

    p = _projeto(tmp_path / "vazio", {"versao": 3, "cortes": []})
    monkeypatch.setattr(sys, "argv", ["gerar_shorts", str(p)])
    gerar_shorts.main()  # nao pode dar erro nem chamar o ffmpeg
    assert "Nenhum trecho forte o bastante nesse vídeo" in capsys.readouterr().out
    monkeypatch.setattr(projetos, "PASTA_SHORTS", tmp_path)
    info = {i["nome"]: i for i in projetos.listar_projetos()}["vazio"]
    assert "Nenhum trecho forte o bastante" in info["passo"] and "Tudo postado" not in info["passo"]


def test_pedido_sem_numero_fixo_e_com_teto_opcional(tmp_path):
    import re

    from shorts.pedido_cortes import texto_pedido

    sem = texto_pedido("live", tmp_path, tmp_path / "d.md", {"maximo_shorts": None})
    assert "Pode ser 0, 3 ou 15" in sem and '"clima"' in sem and '"nota"' in sem and '"motivo"' in sem
    assert "No máximo" not in sem and not re.search(r"\b(?:entre|mínimo de) \d+", sem)
    assert "No máximo 6 cortes" in texto_pedido("live", tmp_path, tmp_path / "d.md", {"maximo_shorts": 6})


# ------------------------------------------------------------------ Fase 3: musica por clima
@pytest.fixture
def sons(tmp_path, monkeypatch):
    """Pastas de musica e de efeitos "do programa" e "deste PC" vazias, numa pasta temporaria."""
    from shorts import biblioteca

    pastas = {}
    for nome in ("PASTA_MUSICAS_APP", "PASTA_MUSICAS", "PASTA_EFEITOS_APP", "PASTA_EFEITOS"):
        pastas[nome] = tmp_path / nome.lower()
        monkeypatch.setattr(biblioteca, nome, pastas[nome])
    return pastas


def _arquivo(pasta, nome):
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / nome).write_bytes(b"x")
    return pasta / nome


def test_musica_do_clima_ou_geral_ou_nenhuma(sons, monkeypatch):
    from nucleo import comum
    from shorts import biblioteca

    assert biblioteca.opcoes_de_musica("epico") == []  # sem nenhuma musica
    _arquivo(sons["PASTA_MUSICAS_APP"] / "geral", "fundo.mp3")
    # 1.11.4: a geral (as musicas calmas de espera) so entra no clima calmo; os outros ficam sem musica
    assert biblioteca.opcoes_de_musica("epico") == [] and biblioteca.opcoes_de_musica("engracado") == []
    assert biblioteca.opcoes_de_musica("calmo") == ["geral/fundo.mp3"]
    monkeypatch.setitem(comum.config_compartilhada(), "musica_geral_serve_para", ["todos"])  # o jeito antigo
    assert biblioteca.opcoes_de_musica("epico") == ["geral/fundo.mp3"]
    _arquivo(sons["PASTA_MUSICAS"] / "epico", "tema.m4a")
    assert biblioteca.opcoes_de_musica("epico") == ["epico/tema.m4a"]
    assert biblioteca.caminho("musica", "epico/tema.m4a") == sons["PASTA_MUSICAS"] / "epico" / "tema.m4a"
    assert biblioteca.caminho("musica", "epico/sumiu.mp3") is None


def test_sem_musica_renderiza_sem_e_avisa(sons):
    from shorts import audio_short, biblioteca

    plano = biblioteca.planejar_musicas([{"clima": "calmo"}], ["calmo"], "proj", "aleatoria")
    assert plano == {1: ""}
    mix = audio_short.para_mixagem(audio_short.sugestao({}, {"ini": 0, "fim": 10}, plano[1]), 10)
    assert mix["faixas"] == [] and "sem musica" in mix["avisos"][0]


def test_nao_repete_musica_em_shorts_seguidos(sons):
    from shorts import biblioteca

    for nome in ("a.mp3", "b.mp3", "c.mp3"):
        _arquivo(sons["PASTA_MUSICAS"] / "engracado", nome)
    cortes = [{"clima": "engracado"}] * 6
    plano = biblioteca.planejar_musicas(cortes, ["engracado"] * 6, "live 12", "aleatoria")
    seguidas = list(plano.values())
    assert all(a != b for a, b in zip(seguidas, seguidas[1:]))
    assert set(seguidas[:3]) == {"engracado/a.mp3", "engracado/b.mp3", "engracado/c.mp3"}  # usa todas antes de repetir
    assert plano == biblioteca.planejar_musicas(cortes, ["engracado"] * 6, "live 12", "aleatoria")  # sempre igual


def test_musica_pedida_pelo_nome_e_nenhuma(sons):
    from shorts import biblioteca

    _arquivo(sons["PASTA_MUSICAS"] / "epico", "Tema Final.mp3")
    plano = biblioteca.planejar_musicas([{"musica": "tema final"}, {"musica": "nenhuma"}], ["", ""], "p", "aleatoria")
    assert plano == {1: "epico/Tema Final.mp3", 2: ""}
    assert biblioteca.planejar_musicas([{}], [""], "p", "nenhuma") == {1: ""}


def test_migracao_copia_musicas_soltas_para_geral_sem_apagar(sons):
    from shorts import biblioteca

    solta = _arquivo(sons["PASTA_MUSICAS"], "antiga.mp3")
    biblioteca.preparar_pastas()
    assert solta.exists()  # nada e apagado
    assert (sons["PASTA_MUSICAS"] / "geral" / "antiga.mp3").exists()
    for pasta in ("engracado", "epico", "tenso", "emocionante", "calmo", "caotico", "geral"):
        assert (sons["PASTA_MUSICAS"] / pasta).is_dir()
    assert (sons["PASTA_EFEITOS"] / "LEIA-ME.txt").exists() and (sons["PASTA_EFEITOS"] / "risada").is_dir()
    assert biblioteca.listar("musica") == {
        "geral": {"geral/antiga.mp3": sons["PASTA_MUSICAS"] / "geral" / "antiga.mp3"}
    }


def test_musica_curta_entra_emendada_com_crossfade(tmp_path):
    from shorts.montagem import montar_comando

    audio = {"faixas": [{"arquivo": tmp_path / "m.wav", "inicio": 0.0, "dur": 6.0}], "volume": 0.3, "efeitos": []}
    cmd = montar_comando("ffmpeg", tmp_path / "v.mp4", 1920, 1080, 0, 16, None, 3.5, None, 19.5, tmp_path / "s.mp4",
                         audio=audio)  # fmt: skip
    filtros = cmd[cmd.index("-filter_complex") + 1]
    assert cmd.count(str(tmp_path / "m.wav")) == 4  # 6 s emendada 4 vezes cobre 19,5 s
    assert filtros.count("acrossfade=d=1.5") == 3 and "sidechaincompress" in filtros and "-stream_loop" not in cmd
    assert "volume='0.300+" in filtros


# ------------------------------------------------------------------ Fase 4: efeitos sonoros
def _medida(ini=100.0, fim=130.0, abertura=None, D=0.0):
    return {"n": 1, "ini": ini, "fim": fim, "abertura": abertura, "D": D}


def test_tempo_do_efeito_vira_tempo_do_short():
    from shorts.audio_short import tempo_no_short

    assert tempo_no_short(112.4, _medida()) == 12.4
    assert tempo_no_short(140.0, _medida()) is None  # fora do corte
    m = _medida(abertura=(120.0, 4.0), D=0.45)  # abertura de 4 s antes do corte
    assert tempo_no_short(100.0, m) == pytest.approx(3.55)  # o corte comeca depois da abertura
    m = _medida(abertura=(200.0, 4.0), D=0.45)
    assert tempo_no_short(201.0, m) == 1.0  # momento que so esta na abertura


def test_limite_de_efeitos_e_categoria_inexistente(sons, capsys):
    from shorts import audio_short

    for nome in ("soco.wav", "tapa.wav"):
        _arquivo(sons["PASTA_EFEITOS"] / "impacto", nome)
    corte = {"sons": [{"tempo": 101 + k, "categoria": "impacto"} for k in range(5)]
             + [{"tempo": 102.5, "categoria": "explosao"}, {"tempo": "nada", "categoria": "impacto"}]}  # fmt: skip
    ed = audio_short.sugestao(corte, _medida(), "", "proj")
    assert len(ed["efeitos"]) == 3  # maximo_efeitos padrao
    assert [e["tempo"] for e in ed["efeitos"]] == [1.0, 2.0, 3.0]
    assert {e["arquivo"] for e in ed["efeitos"][:2]} == {"impacto/soco.wav", "impacto/tapa.wav"}  # nao repete se da
    saida = capsys.readouterr().out
    assert "explosao" in saida and "fiquei com os 3 primeiros" in saida


def test_efeito_entra_na_mixagem_com_volume_proprio(sons, monkeypatch):
    from shorts import audio_short

    monkeypatch.setattr(audio_short, "duracao_arquivo", lambda arq: 30.0)
    _arquivo(sons["PASTA_EFEITOS"] / "risada", "haha.wav")
    _arquivo(sons["PASTA_MUSICAS"] / "geral", "fundo.mp3")
    _arquivo(sons["PASTA_MUSICAS"] / "epico", "virada.mp3")
    corte = {"clima": "engracado", "sons": [{"tempo": 105, "categoria": "risada"},
                                             {"tempo": 115, "tipo": "musica", "clima": "epico"}]}  # fmt: skip
    ed = audio_short.sugestao(corte, _medida(), "geral/fundo.mp3", "proj")
    assert ed["trocas_musica"][0]["arquivo"] == "epico/virada.mp3" and ed["trocas_musica"][0]["tempo"] == 15.0
    mix = audio_short.para_mixagem(ed, 33.0)
    assert [f["inicio"] for f in mix["faixas"]] == [0.0, 15.0]
    assert mix["efeitos"][0]["tempo"] == 5.0 and mix["efeitos"][0]["volume"] == 0.8
    ed["efeitos_ligados"] = False
    ed["musica"]["ligada"] = False
    assert audio_short.para_mixagem(ed, 33.0)["efeitos"] == [] and audio_short.para_mixagem(ed, 33.0)["faixas"] == []


def test_pedido_manda_so_categorias_com_arquivo(sons):
    from shorts.biblioteca import categorias_com_arquivos, preparar_pastas
    from shorts.pedido_cortes import texto_pedido

    preparar_pastas()  # cria as pastas vazias: nenhuma conta
    assert categorias_com_arquivos("efeito") == []
    _arquivo(sons["PASTA_EFEITOS"] / "risada", "haha.wav")
    assert categorias_com_arquivos("efeito") == ["risada"]
    texto = texto_pedido("live", sons["PASTA_EFEITOS"], sons["PASTA_EFEITOS"], {}, ["risada"])
    assert "Categorias disponíveis: risada." in texto and "no máximo 3 por Short" in texto
    assert "nenhum efeito" in texto_pedido("live", sons["PASTA_EFEITOS"], sons["PASTA_EFEITOS"], {}, [])
