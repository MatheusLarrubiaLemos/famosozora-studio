# Testes da versao 1.6.0 (rapidos, sem abrir janelas): selecionar varios videos (caixinha, Ctrl, Shift, todos),
# estado de cada video na lista e o lote (montar, rodar, pular erro, pular/gerar de novo, cancelar, retomar).
from nucleo import selecao
from nucleo.projetos import estado_video

ITENS = ["a", "b", "c", "d", "e"]


def test_clique_simples_seleciona_so_ele():
    assert selecao.clicar(ITENS, ["a", "b"], "a", "c") == (["c"], "c")


def test_ctrl_clique_marca_e_desmarca_um_a_um():
    sel, anc = selecao.clicar(ITENS, ["a"], "a", "c", ctrl=True)
    assert sel == ["a", "c"] and anc == "c"
    sel, anc = selecao.clicar(ITENS, sel, anc, "a", ctrl=True)
    assert sel == ["c"]


def test_caixinha_funciona_como_ctrl():
    sel, _ = selecao.clicar(ITENS, ["b"], "b", "d", caixinha=True)
    assert sel == ["b", "d"]
    sel, _ = selecao.clicar(ITENS, sel, "d", "d", caixinha=True)
    assert sel == ["b"]


def test_shift_clique_seleciona_o_intervalo_nos_dois_sentidos():
    assert selecao.clicar(ITENS, ["b"], "b", "d", shift=True)[0] == ["b", "c", "d"]
    assert selecao.clicar(ITENS, ["d"], "d", "a", shift=True)[0] == ["a", "b", "c", "d"]
    # a ancora fica no primeiro clique: outro Shift + clique muda o intervalo a partir dela
    assert selecao.clicar(ITENS, ["b", "c", "d"], "b", "c", shift=True)[0] == ["b", "c"]


def test_ctrl_shift_soma_o_intervalo():
    assert selecao.clicar(ITENS, ["a"], "c", "e", ctrl=True, shift=True)[0] == ["a", "c", "d", "e"]


def test_shift_sem_ancora_vira_clique_simples():
    assert selecao.clicar(ITENS, [], None, "c", shift=True) == (["c"], "c")


def test_todos_nenhum_e_contador():
    assert selecao.todos(ITENS) == ITENS and selecao.nenhum() == []
    assert selecao.texto_contador(0) == "Nenhum vídeo selecionado"
    assert selecao.texto_contador(1) == "1 vídeo selecionado"
    assert selecao.texto_contador(3) == "3 vídeos selecionados"


def test_item_que_nao_existe_nao_muda_nada():
    assert selecao.clicar(ITENS, ["a"], "a", "z") == (["a"], "a")


def test_estado_do_video_na_lista():
    assert estado_video({"transcrito": False, "tem_cortes": False, "n_shorts": 0}) == "nao_transcrito"
    assert estado_video({"transcrito": True, "tem_cortes": False, "n_shorts": 0}) == "transcrito"
    assert estado_video({"transcrito": True, "tem_cortes": True, "n_shorts": 0}) == "com_cortes"
    assert estado_video({"transcrito": True, "tem_cortes": True, "n_shorts": 4}) == "com_shorts"
