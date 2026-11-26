# Testes da TELA do editor de video (1.9.0), botao a botao e tecla a tecla, sem o player de verdade (o editor abre
# com as miniaturas). Usa o Studio de mentira do test_telas.py. Roda com: python -m pytest -m lento (com tkinter).
import json
import shutil

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
    ed.jan.update()  # o foco chega um instante depois (a tela fica dentro da janela principal desde a 1.9.2)
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
    from interface import telas

    assert any(w.title() == "Atalhos do editor" for w in telas.janelas(ed.studio) + ed.jan.winfo_children()
               if hasattr(w, "title"))  # fmt: skip
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


def test_editor_analisa_sozinho_ou_acompanha_a_analise_que_ja_roda(studio):  # noqa: F811
    """Live sem analise: o editor comeca a analise sozinho (antes abria vazio e era preciso clicar e confirmar).
    Se a analise ja esta rodando (a que vem depois de "Transcrever a live"), ele so acompanha e nao comeca outra."""
    import time as _time

    from nucleo.comum import gravar_json

    st, registro, erros = studio
    pasta = st.aba_longos.projetos["teste das telas"]["pasta"]
    shutil.rmtree(pasta / "analise", ignore_errors=True)
    ed = _abrir_longo(st)
    assert _esperar(st, lambda: any(r.startswith("analisa a live: autoedit.analisar") for r in registro), 5)
    assert not any(r.startswith("pergunta") for r in registro)  # comecou sozinha, sem perguntar "Começar?"
    ed.fechar()  # fechar o editor nao cancela a analise (ela continua em segundo plano)
    st.raiz.update()

    # agora a analise "ja esta rodando" em outro processo: o editor acompanha
    registro.clear()
    (pasta / "analise").mkdir(exist_ok=True)
    gravar_json(pasta / "analise" / "analisando.json", {"linha": "[1/7] Versão leve para o editor   40.0%",
                                                        "inicio": _time.time() - 60, "atualizado": _time.time()})  # fmt: skip
    ed = _abrir_longo(st)
    assert _esperar(st, lambda: "Etapa 1 de 7: Versão leve para o editor 40%" in ed.lbl_status.cget("text"), 5)
    assert not any(r.startswith("analisa a live") for r in registro)  # nao comecou outra
    (pasta / "analise" / "analisando.json").unlink()  # "terminou"
    gravar_json(pasta / "analise" / "analise.json", {"avisos": []})
    assert _esperar(st, lambda: ed._processo_cancelar is None, 6)
    ed.fechar()
    st.raiz.update()
    assert not erros, erros


def test_aceitar_todas_mostra_como_ficou_e_cortar_mais(studio, monkeypatch):  # noqa: F811
    """Aceitou as sugestoes: a linha do tempo ja mostra o video cortado ("como ficou") e o video toca pulando os
    cortes. "Cortar mais" traz uma rodada nova, mais rigida, so no que ficou."""
    from tkinter import messagebox

    from autoedit import analisar

    st, registro, erros = studio
    pasta = st.aba_longos.projetos["teste das telas"]["pasta"]
    edicao = json.loads((pasta / "edicao.json").read_text(encoding="utf-8"))
    edicao["trechos"] = [{"inicio": 50, "fim": 80, "acao": "cortar", "motivo": "silencio", "origem": "auto"},
                         {"inicio": 300, "fim": 330, "acao": "cortar", "motivo": "sem_acao", "origem": "auto"}]  # fmt: skip
    (pasta / "edicao.json").write_text(json.dumps(edicao), encoding="utf-8")
    (pasta / "analise").mkdir(exist_ok=True)
    (pasta / "analise" / "som.json").write_text("{}", encoding="utf-8")
    ed = _abrir_longo(st)
    monkeypatch.setattr(messagebox, "askyesno", lambda *a, **k: True)
    ed.combo_filtro.current(0)
    ed.aceitar_tipo()
    assert ed.timeline.como_ficou and ed.var_como_ficou.get() and ed.modo.get() == "previa"
    assert "Como ficou: 0:10:00 → 0:09:00" in ed.lbl_status.cget("text") or "Como ficou:" in ed.lbl_status.cget("text")
    # na linha do tempo "como ficou" o que sai some: 50 s e 80 s caem no mesmo ponto da tela
    assert abs(ed.timeline.x_de(50) - ed.timeline.x_de(80)) < 1
    assert abs(ed.timeline.t_de(ed.timeline.x_de(100)) - 100) < 1  # e clicar leva ao ponto certo do original

    pedidos = []
    monkeypatch.setattr(analisar, "sugerir", lambda pasta, tipo, regras, *a, **k: (pedidos.append(regras), [
        {"inicio": 60, "fim": 70, "acao": "cortar", "motivo": "silencio"},  # ja sai: nao entra
        {"inicio": 120, "fim": 125, "acao": "cortar", "motivo": "silencio"}])[1])  # fmt: skip
    ed.cortar_mais()
    assert _esperar(st, lambda: any(t.get("rodada") == 2 for t in ed.estado.trechos), 5)
    assert "rodada 2" in pedidos[0]["nome"] and [t["inicio"] for t in ed.estado.trechos if t.get("rodada")] == [120]
    assert "Rodada 2: 1 sugestão(ões) nova(s)" in ed.lbl_status.cget("text")
    ed._ver_como_ficou(False)
    assert not ed.timeline.como_ficou and ed.modo.get() == "original"
    ed.fechar()
    st.raiz.update()
    assert not erros, erros


def test_versoes_da_edicao_no_editor(studio, monkeypatch):  # noqa: F811
    """A lista "Versão da edição" mostra a duração de cada versão; trocar põe as sugestões dela (os cortes à mão
    ficam) e já mostra como ficou. Versão que precisa do Claude pergunta antes de pedir."""
    from tkinter import messagebox

    from autoedit import versoes

    st, registro, erros = studio
    pasta = st.aba_longos.projetos["teste das telas"]["pasta"]
    edicao = json.loads((pasta / "edicao.json").read_text(encoding="utf-8"))
    edicao["trechos"] = [{"inicio": 5, "fim": 8, "acao": "cortar", "motivo": "manual", "origem": "manual"},
                         {"inicio": 50, "fim": 80, "acao": "cortar", "motivo": "silencio", "origem": "auto"}]  # fmt: skip
    (pasta / "edicao.json").write_text(json.dumps(edicao), encoding="utf-8")
    (pasta / "analise").mkdir(exist_ok=True)
    (pasta / "analise" / "som.json").write_text("{}", encoding="utf-8")
    melhores = [{"inicio": 100, "fim": 600, "acao": "cortar", "motivo": "fora_melhores", "origem": "auto"}]
    falsas = {c: ([], 600.0) for c, _ in versoes.VERSOES}
    falsas["melhores"] = (melhores, 100.0)
    falsas["resumao"] = (None, None)  # o Claude ainda nao escolheu
    monkeypatch.setattr(versoes, "todas", lambda *a, **k: falsas)
    ed = _abrir_longo(st)
    assert _esperar(st, lambda: str(ed.combo_versao.cget("state")) == "readonly", 5)
    valores = list(ed.combo_versao.cget("values"))
    assert "Melhores momentos · 1 min" in valores and "Resumão (~15 min) · (pedir ao Claude)" in valores
    monkeypatch.setattr(messagebox, "askyesno", lambda *a, **k: (registro.append("pergunta: versão"), False)[1])
    ed.combo_versao.current(valores.index("Resumão (~15 min) · (pedir ao Claude)"))
    ed._escolheu_versao()  # pergunta se pede ao Claude; "nao": volta para a versao de antes
    assert registro[-1] == "pergunta: versão" and ed.combo_versao.get().startswith("Padrão")
    ed.combo_versao.current(valores.index("Melhores momentos · 1 min"))
    ed._escolheu_versao()
    assert ed.estado.versao == "melhores" and ed.timeline.como_ficou
    assert [(t["inicio"], t["origem"]) for t in ed.estado.trechos] == [(5, "manual"), (100, "auto")]
    ed.salvar()
    assert json.loads((pasta / "edicao.json").read_text(encoding="utf-8"))["versao_edicao"] == "melhores"
    ed.fechar()
    st.raiz.update()
    assert not erros, erros


def test_editor_do_short_nao_fica_parado_em_abrindo(studio, monkeypatch):  # noqa: F811
    """1.11.4: erro ao montar a tela aparece na propria tela (antes ficava "Abrindo..." sem timeline nem video), e
    abrir que demora mostra a etapa e anota no studio.log onde parou."""
    import threading

    from editor import janela_editor
    from editor.janela_editor import JanelaEditor
    from nucleo import registro as reg

    st, registro, erros = studio
    anotado = []
    monkeypatch.setattr(janela_editor, "registrar", lambda texto, erro=None: anotado.append((texto, erro)))
    info = st.projetos["teste das telas"]
    # 1) erro ao montar a tela
    monkeypatch.setattr(JanelaEditor, "_montar_carregado", lambda self, r: 1 / 0)
    ed = JanelaEditor(st, info, "short", 1)
    assert _esperar(st, lambda: "Não consegui abrir" in ed.lbl_status.cget("text"), 10)
    assert any("erro ao montar a tela" in t and isinstance(e, ZeroDivisionError) for t, e in anotado)
    ed.fechar()
    monkeypatch.undo()
    # 2) abrir que demora: mostra a etapa e anota onde a linha parou
    monkeypatch.setattr(janela_editor, "registrar", lambda texto, erro=None: anotado.append((texto, erro)))
    monkeypatch.setattr(janela_editor, "SEGUNDOS_ANOTAR_DEMORA", 1)
    solta = threading.Event()
    original = JanelaEditor._carregar

    def devagar(self):
        self._linha_abrindo = threading.get_ident()
        self._etapa_abrindo = "medindo o som e a imagem do Short"
        solta.wait(20)
        return original(self)

    monkeypatch.setattr(JanelaEditor, "_carregar", devagar)
    ed = JanelaEditor(st, info, "short", 1)
    assert _esperar(st, lambda: any("parado em: medindo o som" in t for t, _ in anotado), 10)
    texto = next(t for t, _ in anotado if "parado em" in t)
    assert "solta.wait" in texto  # a pilha mostra a linha exata onde travou
    assert "medindo o som" in ed.lbl_status.cget("text")
    solta.set()
    assert _esperar(st, lambda: ed.estado is not None, 10)
    ed.fechar()
    st.raiz.update()
    assert reg  # (o registro de verdade nao foi usado: tudo foi para "anotado")


def test_previa_do_short_tem_a_legenda_e_acompanha_a_edicao(studio):  # noqa: F811
    """1.11.4: a previa do Short mostra a legenda (mesmo .ass do render, com os tempos do video original) e ela
    muda quando a fala e editada."""
    from interface.editor_legendas import EditorLegendas

    st, registro, erros = studio
    leg = EditorLegendas.abrir(st, st.projetos["teste das telas"])
    assert _esperar(st, lambda: leg.painel is not None and leg.painel.estado is not None, 10)
    st.raiz.update()
    arq = leg.painel._arq_legenda
    texto = arq.read_text(encoding="utf-8")
    assert "Style: Legenda" in texto and "0:00:10.00" in texto  # tempo do video original (a fala comeca em 10 s)
    leg.trocar_texto(0, "troquei a fala")
    assert "TROQUEI" in arq.read_text(encoding="utf-8").upper()
    assert not erros, erros


def test_palavra_falada_nao_cresce_mais(monkeypatch):
    """1.11.4: a palavra falada so fica mais forte (a cor mostra); crescer so com "legenda_palavra_maior"."""
    from shorts import legendas

    palavras = [{"i": 0.0, "f": 0.4, "p": "oi"}, {"i": 0.5, "f": 0.9, "p": "gente"}]
    monkeypatch.setitem(legendas.CFG, "legenda_palavra_maior", False)
    texto = legendas.montar_ass([(0.0, palavras, 2.0)], "", "", 2.0, None)
    assert "\\fscx112" not in texto and "\\1a&H00&}OI" in texto.upper().replace("\\1A", "\\1a")
    monkeypatch.setitem(legendas.CFG, "legenda_palavra_maior", True)
    assert "\\fscx112" in legendas.montar_ass([(0.0, palavras, 2.0)], "", "", 2.0, None)
