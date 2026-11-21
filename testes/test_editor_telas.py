# Testes da TELA do editor de video (1.9.0), botao a botao e tecla a tecla, sem o player de verdade (o editor abre
# com as miniaturas). Usa o Studio de mentira do test_telas.py. Roda com: python -m pytest -m lento (com tkinter).
import json
import tkinter as tk

import pytest
from test_telas import _esperar, studio  # noqa: F401  (o "studio" e uma fixture do pytest)

pytestmark = pytest.mark.lento


def _abrir_longo(st):
    from editor.janela_editor import JanelaEditor

    st.mostrar("longos")
    st.aba_longos.tree.selection_set("teste das telas")
    st.raiz.update()
    ed = st.aba_longos.editor()
    assert ed is not None
    assert _esperar(st, lambda: ed.estado is not None and ed.timeline is not None, 10)
    assert isinstance(ed, JanelaEditor)
    return ed


def _tecla(ed, tecla):
    ed.jan.focus_force()
    ed.jan.event_generate(tecla)
    ed.jan.update()


def test_editor_longo_atalhos_desfazer_e_salva_sozinho(studio):  # noqa: F811
    st, registro, erros = studio
    pasta = st.aba_longos.projetos["teste das telas"]["pasta"]
    ed = _abrir_longo(st)
    assert "Estilo TV" in ed.lbl_aviso.cget("text")  # aviso das diretrizes do canal
    assert "ainda não foi analisada" in ed.lbl_aviso.cget("text")
    e = ed.estado
    # I / O / X: corta um pedaco
    ed.pular(100)
    _tecla(ed, "<Key-i>")
    ed.pular(130)
    _tecla(ed, "<Key-o>")
    _tecla(ed, "<Key-x>")
    assert [(t["inicio"], t["fim"], t["origem"]) for t in e.trechos] == [(100, 130, "manual")]
    assert e.duracao_final() == pytest.approx(600 - 30)
    # Ctrl+Z / Ctrl+Shift+Z
    _tecla(ed, "<Control-z>")
    assert e.trechos == []
    _tecla(ed, "<Control-Z>")
    assert len(e.trechos) == 1
    # C divide, R restaura (volta a manter) o trecho selecionado
    ed.pular(115)
    _tecla(ed, "<Key-c>")
    assert len(e.trechos) == 2
    ed.selecionar(0)
    _tecla(ed, "<Key-r>")
    assert e.trechos[0]["acao"] == "manter" and e.duracao_final() == pytest.approx(600 - 15)
    # L acelera ate 4x, J desacelera
    for _ in range(6):
        _tecla(ed, "<Key-l>")
    assert ed._vel_base == 4.0
    _tecla(ed, "<Key-j>")
    assert ed._vel_base == 3.0
    # salva sozinho (no maximo 1 s depois)
    assert _esperar(st, lambda: json.loads((pasta / "edicao.json").read_text(encoding="utf-8")).get("trechos"), 4)
    dados = json.loads((pasta / "edicao.json").read_text(encoding="utf-8"))
    assert dados["versao"] == 3 and len(dados["trechos"]) == 2 and dados["tipo"] == "longo"
    assert (pasta / "edicao.anterior.json").exists()  # copia de seguranca da 1a gravacao
    # marcador de capitulo vira capitulo do edicao.json; Short daqui vira corte no cortes.json
    ed.adicionar_marcador("capitulo", 200.0)  # askstring do teste responde "youtu.be/x"
    ed.criar_short(300.0)
    ed.salvar()
    dados = json.loads((pasta / "edicao.json").read_text(encoding="utf-8"))
    assert any(c.get("tempo") == "00:03:20" for c in dados["capitulos"])
    cortes = json.loads((pasta / "cortes.json").read_text(encoding="utf-8"))["cortes"]
    assert cortes[-1]["origem"] == "editor"
    # menu do botao direito
    itens = [i[0] for i in ed.itens_do_menu(105.0, 0) if i]
    assert "Cortar" in itens and "⭐ Mandar para Shorts (criar Short daqui)" in itens
    # ? mostra os atalhos
    _tecla(ed, "<question>")
    assert any(isinstance(w, tk.Toplevel) and w.title() == "Atalhos do editor" for w in ed.jan.winfo_children())
    # abrir de novo traz a mesma janela
    assert st.aba_longos.editor() is ed
    ed.fechar()
    st.raiz.update()
    assert not erros, erros


def test_editor_sugestoes_aceitar_recusar_e_introducao_protegida(studio, monkeypatch):  # noqa: F811
    from tkinter import messagebox

    st, registro, erros = studio
    pasta = st.aba_longos.projetos["teste das telas"]["pasta"]
    edicao = json.loads((pasta / "edicao.json").read_text(encoding="utf-8"))
    edicao.update({"introducao": {"inicio": 0, "fim": 30}, "predefinicao": {"nome": "Longo (TV)", "versao": 1,
                                                                             "tipo": "longo"},
                   "trechos": [{"inicio": 50, "fim": 80, "acao": "cortar", "motivo": "silencio", "origem": "auto",
                                "confianca": "alta"},
                               {"inicio": 200, "fim": 260, "acao": "manter", "motivo": "papo_fora", "origem": "auto",
                                "confianca": "baixa"},
                               {"inicio": 300, "fim": 330, "acao": "cortar", "motivo": "sem_acao", "origem": "auto",
                                "confianca": "media"}]})  # fmt: skip
    (pasta / "edicao.json").write_text(json.dumps(edicao), encoding="utf-8")
    ed = _abrir_longo(st)
    e = ed.estado
    assert len(ed.lista.get_children()) == 3
    ed.pular(0)
    _tecla(ed, "<Key-n>")  # proxima sugestao
    assert e.selecionado == 0
    _tecla(ed, "<BackSpace>")  # recusa (fica) e vai para a proxima
    assert e.trechos[0]["acao"] == "manter" and e.trechos[0]["revisado"]
    assert e.selecionado == 1
    _tecla(ed, "<Return>")  # aceita o papo fora (que era so sugestao)
    assert e.trechos[1]["acao"] == "cortar"
    assert "Recusadas: 1 de silêncio" in ed.lbl_relatorio.cget("text")
    # filtro + "Aceitar todas deste tipo"
    ed.combo_filtro.set("Sem ação")
    ed._preencher_lista()
    assert len(ed.lista.get_children()) == 1
    ed.aceitar_tipo()
    assert e.trechos[2]["revisado"]
    # introducao protegida: cortar dentro dela pergunta (o teste responde "nao") e nao corta
    monkeypatch.setattr(messagebox, "askyesno", lambda *a, **k: (registro.append("pergunta: protegido"), False)[1])
    e.marca_in, e.marca_out = 5.0, 20.0
    ed.cortar_marcado()
    assert "pergunta: protegido" in registro and not any(t["inicio"] == 5.0 for t in e.trechos)
    monkeypatch.setattr(messagebox, "askyesno", lambda *a, **k: True)
    e.marca_in, e.marca_out = 5.0, 20.0
    ed.cortar_marcado()
    assert any(t["inicio"] == 5.0 and t.get("forcar") for t in e.trechos)
    # modos de reprodução: previa pula o que sai; "so o que vai sair" vai para o proximo corte
    ed.modo.set("previa")
    assert ed._regras_do_modo(60.0) == pytest.approx(60.0)  # 50-80 foi recusado: fica
    ed.player.tocar()
    assert ed._regras_do_modo(210.0) == pytest.approx(260.0)  # papo fora aceito: pula
    ed.modo.set("so_sai")
    assert ed._regras_do_modo(100.0) == pytest.approx(200.0)
    ed.player.pausar()
    ed.fechar()
    assert not erros, erros


def test_ajustar_corte_do_short_abre_o_editor_no_modo_short(studio):  # noqa: F811
    from editor import arquivos
    from interface.editor_legendas import EditorLegendas

    st, registro, erros = studio
    st.mostrar("shorts")
    st.aba_shorts.tree.selection_set("teste das telas")
    st.raiz.update()
    st.aba_shorts.revisar_legendas()
    st.raiz.update()
    leg = next(iter(EditorLegendas.abertos.values()))
    assert _esperar(st, lambda: leg.n is not None, 5)
    ed = leg.ajustar_corte()
    assert _esperar(st, lambda: ed.estado is not None, 10)
    e = ed.estado
    assert e.tipo == "short" and e.limites == (10.0, 14.0) and e.inicio == 0.0 and e.fim == 24.0
    e.mover_limite("fim", 16.0, com_ima=False)
    e.fim_do_arrasto()
    e.cortar(11.0, 12.0)
    ed.salvar()
    pasta = leg.pasta
    cortes = json.loads((pasta / "cortes.json").read_text(encoding="utf-8"))["cortes"]
    assert cortes[0]["fim"] == "00:00:16"
    assert arquivos.cortes_internos(pasta, 1, 10.0, 16.0) == [(11.0, 12.0)]
    ed.exportar()
    assert any("roda" in r for r in registro)
    ed.fechar()
    leg.fechar()
    st.raiz.update()
    assert not erros, erros


def test_configuracoes_cortes_automaticos(studio, monkeypatch, tmp_path):  # noqa: F811
    from autoedit import predefinicoes

    monkeypatch.setattr(predefinicoes, "PASTA_CONFIG", tmp_path)
    st, registro, erros = studio
    st.mostrar("configuracoes")
    st.raiz.update()
    jan = st.telas["configuracoes"].abrir_predefinicoes()
    jan.campos["longo"]["sem_acao_min"].set("8")
    jan.salvar("longo")
    assert predefinicoes.da("longo")["sem_acao_min"] == 8.0
    jan.campos["longo"]["sem_acao_min"].set("abc")
    jan.salvar("longo")
    assert any(r.startswith("ERRO: Cortes automáticos") for r in registro)
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *a, **k: True)
    jan.voltar("longo")
    assert predefinicoes.da("longo")["sem_acao_min"] == 6.0
    jan.jan.destroy()
    assert not erros, erros
