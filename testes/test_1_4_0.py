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
    assert "Falante,,0,0,0,," not in sem_nome  # desligado por padrao
    com_nome = montar_ass(blocos, "", "t", 3.0, None, quem=pessoas.QuemFala({"1": "Pedro"}), mostrar_nome=True)
    etiquetas = [linha for linha in com_nome.splitlines() if ",Falante," in linha]
    assert len(etiquetas) == 1 and "Pedro" in etiquetas[0]  # so quem nao e o FamosoZora


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
