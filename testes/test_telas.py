# Confere as telas botao por botao (lento, ~20 s): abre o Studio numa pasta de trabalho de teste, aperta cada
# botao das telas (Shorts, Videos longos, Inicio, Publicacao, Configuracoes) e os botoes de cada janela (Publicar, Revisar legendas, revisao do
# video longo). As perguntas sao respondidas sozinhas e nada e renderizado de verdade: o teste so registra
# o que cada botao FARIA. Se algum botao der erro, o teste falha e mostra qual.
# Rodar: python -m pytest -m lento -s testes/test_telas.py   (o -s mostra a tabela de resultados)
import json
import shutil
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from types import SimpleNamespace

import pytest
from conftest import PASTA_TRABALHO

pytestmark = pytest.mark.lento


def _projeto_de_teste():
    """Projeto falso com transcricao, 2 Shorts gerados, legendas e edicao do video longo."""
    p = PASTA_TRABALHO / "shorts" / "teste das telas"
    shutil.rmtree(p, ignore_errors=True)  # cada teste comeca com o projeto limpo
    (p / "prontos").mkdir(parents=True, exist_ok=True)
    (p / "legendas").mkdir(exist_ok=True)
    video = p / "video_falso.mp4"
    video.write_bytes(b"")
    palavras = [{"i": 10 + k * 0.4, "f": 10.3 + k * 0.4, "p": t}
                for k, t in enumerate("Mano, eu abri a água. Puta que pariu, velho.".split())]  # fmt: skip
    palavras[3]["inc"] = True
    for k, w in enumerate(palavras):  # duas vozes detectadas, para o painel Falantes ter o que mostrar
        w["s"] = 0 if k < 5 else 1

    def json_(nome, dados):
        (p / nome).write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")

    json_("projeto.json", {"video": str(video), "duracao": 600})
    json_("transcricao.json", {"segmentos": [{"inicio": 10, "fim": 14, "texto": "x", "palavras": palavras}]})
    json_(
        "cortes.json",
        {"cortes": [{"inicio": 10, "fim": 14, "titulo": "Um"}, {"inicio": 20, "fim": 24, "titulo": "Dois"}]},
    )
    json_("edicao.json", {"cortes": [{"inicio": "00:00:00", "fim": "00:01:00", "motivo": "menu"}],
                          "capitulos": [{"inicio": "00:01:00", "titulo": "Começo"}], "titulo": "Teste"})  # fmt: skip
    shorts = []
    for n, nome in ((1, "01 - Um.mp4"), (2, "02 - Dois.mp4")):
        (p / "prontos" / nome).write_bytes(b"x")
        (p / "legendas" / f"{n:02d}_original.json").write_text(
            json.dumps({"n": n, "arquivo": nome, "inicio": 10, "fim": 14, "palavras": palavras}), encoding="utf-8"
        )
        textos = {"youtube": {"titulo": nome, "descricao": "d {link}", "tags": ["a"], "titulo_en": "t", "descricao_en": "d"},
                  "tiktok": "tt", "instagram": "ig"}  # fmt: skip
        shorts.append({"n": n, "arquivo": nome, "duracao": 4, "textos": textos, "postado": {}})
    (p / "prontos" / "publicacao.json").write_text(json.dumps({"shorts": shorts}), encoding="utf-8")
    return p


@pytest.fixture
def studio(monkeypatch, tmp_path):
    """Studio aberto, com as perguntas respondidas sozinhas e as acoes externas so registradas."""
    from tkinter import colorchooser, filedialog, messagebox, simpledialog

    import interface.aba_base
    import interface.aba_shorts
    import interface.aba_videos_longos
    import interface.editor_legendas
    import interface.janela_edicao
    import interface.janela_principal
    import interface.janela_publicar
    import interface.utilidades
    from shorts import pessoas

    _projeto_de_teste()
    registro = []
    monkeypatch.setattr(messagebox, "showinfo", lambda t, m="", **k: registro.append(f"aviso: {t}"))
    monkeypatch.setattr(messagebox, "showerror", lambda t, m="", **k: registro.append(f"ERRO: {t}: {m[:120]}"))
    monkeypatch.setattr(messagebox, "askyesno", lambda t, m="", **k: (registro.append(f"pergunta: {t}"), False)[1])
    monkeypatch.setattr(messagebox, "askyesnocancel", lambda t, m="", **k: (registro.append(f"pergunta: {t}"), None)[1])
    monkeypatch.setattr(simpledialog, "askstring", lambda *a, **k: (registro.append("pergunta: link"), "youtu.be/x")[1])
    monkeypatch.setattr(
        colorchooser, "askcolor", lambda *a, **k: (registro.append("escolhe cor"), (None, "#00008b"))[1]
    )
    monkeypatch.setattr(pessoas, "PASTA_CONFIG", tmp_path)  # o cadastro de pessoas do teste fica numa pasta temporaria
    from shorts import biblioteca

    for nome in ("PASTA_MUSICAS_APP", "PASTA_MUSICAS", "PASTA_EFEITOS_APP", "PASTA_EFEITOS"):  # sons de teste
        monkeypatch.setattr(biblioteca, nome, tmp_path / nome.lower())
    for arq in ("pasta_musicas/geral/fundo.mp3", "pasta_musicas/epico/tema.mp3", "pasta_efeitos/impacto/soco.wav"):
        (tmp_path / arq).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / arq).write_bytes(b"x")
    monkeypatch.setattr(filedialog, "askdirectory", lambda *a, **k: (registro.append("escolher pasta"), "")[1])
    monkeypatch.setattr(filedialog, "askopenfilenames", lambda *a, **k: (registro.append("escolher vídeos"), ())[1])
    monkeypatch.setattr(filedialog, "askopenfilename", lambda *a, **k: (registro.append("escolher arquivo"), "")[1])

    def fazer(texto):
        """Funcao falsa que so anota no registro o que o botao faria."""
        return lambda *a, **k: registro.append(texto + (f" {a[0]}" if a and isinstance(a[0], str) else ""))

    for modulo in (interface.aba_shorts, interface.aba_videos_longos, interface.janela_edicao,
                   interface.editor_legendas, interface.janela_principal, interface.utilidades):  # fmt: skip
        if hasattr(modulo, "rodar_script"):
            monkeypatch.setattr(modulo, "rodar_script", fazer("roda"))
    for modulo in (interface.aba_base, interface.janela_edicao, interface.editor_legendas, interface.janela_principal,
                   interface.janela_publicar):  # fmt: skip
        for nome in ("abrir", "abrir_texto", "mostrar_na_pasta"):
            if hasattr(modulo, nome):
                monkeypatch.setattr(modulo, nome, fazer(f"abre ({nome})"))
    # troca so o "subprocess" destas telas (trocar o do Python inteiro quebraria o resto do programa)
    monkeypatch.setattr(interface.aba_videos_longos, "subprocess", SimpleNamespace(Popen=fazer("abre juntar vídeos")))
    # a janela principal tambem abre programas (o .bat de desenvolvedor, o Studio de novo): so registra
    monkeypatch.setattr(interface.janela_principal, "subprocess", SimpleNamespace(
        Popen=fazer("roda programa"), run=fazer("roda programa"), CREATE_NO_WINDOW=0))  # fmt: skip
    import interface.pagina_publicacao
    from publicacao import claude_pc, fila

    fila.arquivo().unlink(missing_ok=True)  # cada teste comeca com a fila vazia
    for modulo in (interface.janela_principal, interface.pagina_publicacao, claude_pc):
        monkeypatch.setattr(modulo, "webbrowser", SimpleNamespace(open=fazer("abre navegador")))
    # o Claude Code "existe" no teste, mas so registra o comando (nada abre de verdade)
    monkeypatch.setattr(claude_pc, "achar_claude_code", lambda: "/fake/claude")
    from nucleo import claude_local

    def claude_falso(pedido, cancelar, modelo="", **k):  # "responde" como o Claude, sem chamar nada
        registro.append("pergunta ao Claude (falso)")
        if "remover" in pedido:
            return json.dumps({"versao": 2, "remover": [{"inicio": "00:00:00", "fim": "00:00:40", "motivo": "menu"}],
                               "capitulos": [{"tempo": "00:00:41", "titulo": "Começo"}], "titulo": "Ep"})  # fmt: skip
        return json.dumps({"versao": 3, "cortes": [{"inicio": "00:00:10", "fim": "00:00:40", "titulo": "Novo"}]})

    monkeypatch.setattr(claude_local, "rodar_claude", claude_falso)
    monkeypatch.setattr(claude_pc, "subprocess", SimpleNamespace(
        Popen=lambda comando, **k: registro.append("abre o Claude Code: " + " ".join(map(str, comando))),
        run=fazer("roda programa"), CREATE_NO_WINDOW=0))  # fmt: skip
    monkeypatch.setattr(interface.pagina_publicacao, "abrir", fazer("abre (abrir)"))
    monkeypatch.setattr(interface.pagina_publicacao, "mostrar_na_pasta", fazer("abre (mostrar_na_pasta)"))
    monkeypatch.setattr(simpledialog, "askstring", lambda *a, **k: (registro.append("pergunta: link"), "youtu.be/x")[1])
    monkeypatch.setattr(interface.janela_principal.Studio, "boas_vindas", lambda self: None)
    monkeypatch.setattr(
        interface.janela_principal.Studio,
        "verificar_atualizacao",
        lambda self, manual=False: registro.append("procura atualização"),
    )

    def cortar(comando, *a, **k):  # finge que o ffmpeg cortou o trecho
        Path(comando[-1]).write_bytes(b"x")
        registro.append("corta o trecho no ffmpeg")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(interface.editor_legendas, "subprocess", SimpleNamespace(run=cortar, CREATE_NO_WINDOW=0))
    import interface.painel_audio

    monkeypatch.setattr(interface.painel_audio, "escolher_da_lista", lambda pai, titulo, opcoes, atual="": (
        registro.append(f"escolhe da lista: {titulo}"), opcoes[0] if opcoes else None)[1])  # fmt: skip

    monkeypatch.setattr(interface.janela_principal.Studio, "_aceitar_arquivos", lambda self, w: None)
    import interface.pagina_configuracoes

    for nome in ("abrir", "abrir_texto"):
        monkeypatch.setattr(interface.pagina_configuracoes, nome, fazer(f"abre ({nome})"))
    monkeypatch.setattr(interface.pagina_configuracoes, "rodar_script", fazer("roda"))
    st = interface.janela_principal.Studio()
    st.sem_miniaturas = True
    # area de transferencia so do teste (a de verdade nao e lida nem trocada)
    edicao_valida = json.dumps({"cortes": [{"inicio": "00:00:00", "fim": "00:01:00", "motivo": "menu"}]})
    area = {"texto": edicao_valida}
    monkeypatch.setattr(st, "copiar", lambda texto: (area.update(texto=edicao_valida), registro.append("copia texto")))
    monkeypatch.setattr(st.raiz, "clipboard_get", lambda *a, **k: area["texto"])
    erros = []
    st.raiz.report_callback_exception = lambda tipo, valor, tb: erros.append(f"{tipo.__name__}: {valor}")
    st.raiz.update()
    yield st, registro, erros
    st.raiz.destroy()


def _esperar(st, condicao, segundos=5.0):
    """Espera (deixando a tela trabalhar) ate a condicao ficar verdadeira: para o que roda em segundo plano."""
    import time

    fim = time.monotonic() + segundos
    while not condicao() and time.monotonic() < fim:
        st.raiz.update()
        time.sleep(0.02)
    return condicao()


def _botoes(widget):
    """Todos os botoes dentro de uma janela, na ordem em que aparecem."""
    achados = []
    for filho in widget.winfo_children():
        if isinstance(filho, (ttk.Button, tk.Button, tk.Checkbutton, ttk.Checkbutton)):
            achados.append(filho)
        achados += _botoes(filho)
    return achados


def _todos(widget):
    return [widget] + [w for filho in widget.winfo_children() for w in _todos(filho)]


def _apertar(st, botao, registro, erros, tabela, onde):
    if not botao.winfo_exists():  # o painel se redesenhou depois do botao anterior: esse botao ja foi trocado
        return []
    nome = str(botao.cget("text")).strip()
    antes_janelas = {str(w) for w in st.raiz.winfo_children() if isinstance(w, tk.Toplevel)}
    antes_reg, antes_err = len(registro), len(erros)
    botao.invoke()
    st.raiz.update()
    novas = [w for w in st.raiz.winfo_children() if isinstance(w, tk.Toplevel) and str(w) not in antes_janelas]
    feito = registro[antes_reg:] + [f"abre a janela: {w.title()}" for w in novas]
    tabela.append((onde, nome, not erros[antes_err:], "; ".join(feito + erros[antes_err:]) or "-"))
    return novas


def test_cada_botao_de_cada_tela(studio):
    st, registro, erros = studio
    tabela = []
    for codigo, aba, nome_aba in (
        ("shorts", st.aba_shorts, "Aba Shorts"),
        ("longos", st.aba_longos, "Aba Vídeos longos"),
    ):
        st.mostrar(codigo)
        aba.tree.selection_set("teste das telas")
        st.raiz.update()
        for botao in _botoes(aba.direita):
            nome = str(botao.cget("text"))
            for janela in _apertar(st, botao, registro, erros, tabela, nome_aba):
                for b in _botoes(janela):
                    if not b.winfo_exists() or str(b.cget("text")).strip() in ("Depois", "Mandar para a Lixeira"):
                        continue
                    _apertar(st, b, registro, erros, tabela, f"  janela {janela.title()[:28]}")
                janela.destroy()
    for codigo, nome_tela in (("inicio", "Início"), ("publicacao", "Publicação"), ("configuracoes", "Configurações")):
        st.mostrar(codigo)
        st.raiz.update()
        for botao in _botoes(st.telas[codigo]):
            for janela in _apertar(st, botao, registro, erros, tabela, nome_tela):
                janela.destroy()
    print("\n\n| Onde | Botão | Funcionou? | O que fez |\n|---|---|---|---|")
    for onde, nome, ok, feito in tabela:
        print(f"| {onde} | {nome} | {'sim' if ok else 'NÃO'} | {feito} |")
    assert not erros, erros
    assert not [r for r in registro if r.startswith("ERRO")], registro
    assert len(tabela) > 40


def test_painel_falantes_e_janela_de_pessoas(studio):
    """Aperta os botoes de cada voz (ouvir, cor), liga uma voz a uma pessoa nova, troca quem fala numa linha
    e usa cada botao da janela Pessoas e cores."""
    from interface.editor_legendas import EditorLegendas
    from interface.janela_pessoas import JanelaPessoas
    from shorts import pessoas

    st, registro, erros = studio
    st.mostrar("shorts")
    st.aba_shorts.tree.selection_set("teste das telas")
    st.raiz.update()
    ed = EditorLegendas(st, st.aba_shorts.selecionado())
    st.raiz.update()
    linhas = ed.painel_falantes.linhas.winfo_children()
    assert len(linhas) == 2  # as duas vozes do projeto de teste
    for k in range(2):
        for b in _botoes(ed.painel_falantes.linhas.winfo_children()[k]):
            b.invoke()
            st.raiz.update()
    assert _esperar(st, lambda: "corta o trecho no ffmpeg" in registro) and "escolhe cor" in registro
    ed.painel_falantes.escolheu("1", "+ nova pessoa...")  # askstring do teste responde "youtu.be/x"
    assert ed.ligacoes == {"1": "youtu.be/x"} and ed.mudou
    ed.tree.selection_set("0")
    ed.trocar_quem_da_linha("youtu.be/x")
    assert all(ed.palavras[p].get("pessoa") == "youtu.be/x" for p in ed.linhas[0])
    ed.desfazer()
    assert not any(w.get("pessoa") for w in ed.palavras)
    assert ed.salvar()
    assert pessoas.ler_ligacoes(ed.pasta, ed.n) == {"1": "youtu.be/x"}
    ed.jan.destroy()

    jan = JanelaPessoas(st.raiz)
    jan.lista.selection_set(0)
    for b in _botoes(jan.jan):
        jan.lista.selection_set(0)
        b.invoke()
        st.raiz.update()
    assert not erros, erros
    assert pessoas.pessoa_padrao()["nome"]  # sempre sobra uma pessoa padrao
    jan.jan.destroy()


def test_audio_e_edicao_de_um_short(studio):
    """Aba Audio e edicao: troca a musica, adiciona, muda e exclui um efeito, desliga a musica, desfaz,
    salva (vai para o NN_edicao.json) e restaura a sugestao do Claude."""
    from interface.editor_legendas import EditorLegendas
    from shorts import edicao

    st, registro, erros = studio
    st.mostrar("shorts")
    st.aba_shorts.tree.selection_set("teste das telas")
    st.raiz.update()
    ed = EditorLegendas(st, st.aba_shorts.selecionado())
    st.raiz.update()
    pa = ed.painel_audio
    assert ed.edicao["musica"]["arquivo"] == "geral/fundo.mp3"  # Short antigo: a sugestao foi montada na hora
    assert edicao.ler_sugestao(ed.pasta, ed.n) is not None
    pa.trocar_musica()  # a lista do teste escolhe a primeira
    assert ed.edicao["musica"]["arquivo"] != "" and ed.mudou
    ed.tree.selection_set("1")
    pa.adicionar_efeito()
    assert ed.edicao["efeitos"][0]["arquivo"] == "impacto/soco.wav"
    for item in [i for i in pa.itens_efeito() + pa.itens_musica() if i]:  # cada item do botao direito
        if pa.tree.exists("0"):
            pa.tree.selection_set("0")
        if item[1]:
            item[1]()
            st.raiz.update()
    assert _esperar(st, lambda: "corta o trecho no ffmpeg" in registro)  # "Trecho com o efeito" montou a previa
    ed.desfazer()
    assert ed.salvar() and edicao.ler_edicao(ed.pasta, ed.n) is not None
    pa.restaurar()
    assert ed.salvar() and edicao.ler_edicao(ed.pasta, ed.n) is None  # igual a sugestao: nao guarda edicao
    assert not erros, erros
    ed.jan.destroy()


def test_editor_duplo_clique_menus_e_atalhos(studio):
    """Fase 2 da 1.5.0: editar o texto e o tempo ali mesmo, cada item do botao direito (linha, caixa, Short),
    inserir e excluir linha, e os atalhos de teclado."""
    from interface.editor_legendas import EditorLegendas
    from interface.menus import todos_os_itens
    from shorts import revisao

    st, registro, erros = studio
    st.mostrar("shorts")
    st.aba_shorts.tree.selection_set("teste das telas")
    st.raiz.update()
    ed = EditorLegendas(st, st.aba_shorts.selecionado())
    st.raiz.update()
    assert [str(b.cget("text")) for b in _botoes(ed.jan) if "Salvar" in str(b.cget("text"))]
    # duplo clique no texto: a caixinha abre com o texto da linha; Enter grava
    ed.tree.selection_set("0")
    ent = ed.editar_celula("texto")
    assert ent is not None and ent.get() == revisao.texto_da_linha(ed.palavras, ed.linhas[0])
    ent.delete(0, "end")
    ent.insert(0, "Mano, eu abri a porta.")
    ed.fechar_edicao(True)
    assert revisao.texto_da_linha(ed.palavras, ed.linhas[0]) == "Mano, eu abri a porta." and ed.mudou
    # Esc cancela
    ent = ed.editar_celula("texto")
    ent.insert(0, "lixo ")
    ed.fechar_edicao(False)
    assert revisao.texto_da_linha(ed.palavras, ed.linhas[0]) == "Mano, eu abri a porta."
    # tempo: o fim da linha 0 vai para 11.5 s
    ent = ed.editar_celula("fim")
    ent.delete(0, "end")
    ent.insert(0, "00:11.5")
    ed.fechar_edicao(True)
    assert abs(ed.palavras[ed.linhas[0][-1]]["f"] - 11.5) < 0.01
    # tempo invalido (invade a linha de baixo): avisa e nao muda
    ent = ed.editar_celula("fim")
    ent.delete(0, "end")
    ent.insert(0, "59:00")
    ed.fechar_edicao(True)
    assert abs(ed.palavras[ed.linhas[0][-1]]["f"] - 11.5) < 0.01 and "aviso: Tempo" in registro
    # inserir linha abaixo da 0 e digitar o texto dela
    n_linhas = len(ed.linhas)
    ed.tree.selection_set("0")
    ed.inserir_linha()
    ent = ed.editando[0]
    ent.delete(0, "end")
    ent.insert(0, "linha nova")
    ed.fechar_edicao(True)
    assert len(ed.linhas) == n_linhas + 1
    assert revisao.texto_da_linha(ed.palavras, ed.linhas[1]) == "linha nova"
    # excluir a linha nova; Ctrl+Z traz de volta
    ed.tree.selection_set("1")
    ed.excluir_linha()
    assert len(ed.linhas) == n_linhas
    ed.desfazer()
    assert len(ed.linhas) == n_linhas + 1
    # cada item do botao direito da linha, da caixa e do Short da lista
    ed.tree.selection_set("0")
    ed.mostrar_linha()
    for rotulo, k, menu in todos_os_itens(montar(ed, ed.itens_da_linha(0))):
        if "Excluir" in rotulo or "nova pessoa" in rotulo:
            continue
        ed.tree.selection_set("0")
        ed.mostrar_linha()
        menu.invoke(k)
        st.raiz.update()
        ed.fechar_edicao(False)
    assert _esperar(
        st, lambda: "corta o trecho no ffmpeg" in registro
    )  # "Assistir este trecho" / "Ouvir" montou o trecho
    for rotulo, k, menu in todos_os_itens(montar(ed, ed.itens_do_short())):
        if "Excluir" in rotulo:
            continue
        menu.invoke(k)
        st.raiz.update()
    # atalhos
    ed.tree.focus_set()
    ed.tree.selection_set("0")
    ed.tree.event_generate("<F2>")
    st.raiz.update()
    assert ed.editando is not None
    ed.fechar_edicao(False)
    assert ed.salvar()
    assert not erros, erros
    ed.jan.destroy()


def montar(ed, itens):
    from interface.menus import montar_menu

    return montar_menu(ed.jan, itens)


def test_excluir_varios_projetos_pelo_botao_direito(studio, monkeypatch):
    """Fase 4: seleciona 2 projetos (Ctrl+clique), abre o Excluir e confere cada opcao. Nada vai de verdade
    para a Lixeira: a funcao da Lixeira so anota o que mandaria."""
    import shutil

    from interface.menus import todos_os_itens
    from nucleo import limpeza

    st, registro, erros = studio
    origem = PASTA_TRABALHO / "shorts" / "teste das telas"
    copia = PASTA_TRABALHO / "shorts" / "segundo projeto"
    shutil.rmtree(copia, ignore_errors=True)
    shutil.copytree(origem, copia)
    lixeira = []
    monkeypatch.setattr(limpeza, "mandar_para_lixeira", lambda c: (lixeira.extend(c), True)[1])
    st.atualizar()
    st.mostrar("shorts")
    aba = st.aba_shorts
    aba.tree.selection_set(["teste das telas", "segundo projeto"])
    st.raiz.update()
    assert len(aba.selecionados()) == 2
    # o menu do botao direito com 2 selecionados: "Publicar os Shorts dos 2" e "Excluir 2 projetos..."
    evento = type("E", (), {"y": aba.tree.bbox("segundo projeto")[1] + 5})()
    itens = todos_os_itens(aba.menu_do_projeto(evento))
    assert [r for r, *_ in itens] == ["📅  Publicar os Shorts dos 2 selecionados", "🗑  Excluir 2 projetos..."]
    jan = aba.excluir()
    assert jan.modos == ["shorts", "projeto", "tudo"]
    jan.modo.set("shorts")
    jan.mudou()
    jan.confirmar()
    assert sorted(f.name for f in lixeira) == ["01 - Um.mp4", "01 - Um.mp4", "02 - Dois.mp4", "02 - Dois.mp4"]
    lixeira.clear()
    jan = aba.excluir()
    jan.modo.set("projeto")
    jan.mudou()
    jan.confirmar()
    assert sorted(f.name for f in lixeira) == ["segundo projeto", "teste das telas"]
    # um so projeto, no menu: todos os itens funcionam (menos o Excluir, ja testado)
    aba.tree.selection_set("teste das telas")
    st.raiz.update()
    evento = type("E", (), {"y": aba.tree.bbox("teste das telas")[1] + 5})()
    for rotulo, k, menu in todos_os_itens(aba.menu_do_projeto(evento)):
        if "Excluir" not in rotulo:
            menu.invoke(k)
            st.raiz.update()
    for w in st.raiz.winfo_children():
        if isinstance(w, tk.Toplevel):
            w.destroy()
    # na tela de videos longos, a 1a opcao e "so o episodio"
    st.mostrar("longos")
    st.aba_longos.tree.selection_set("teste das telas")
    jan = st.aba_longos.excluir()
    assert jan.modos[0] == "episodio"
    jan.jan.destroy()
    shutil.rmtree(copia, ignore_errors=True)
    assert not erros, erros


def test_publicar_shorts_revisar_confirmar_e_fila(studio):
    """Fase 1: abre a revisao com os 2 Shorts (um por dia), muda o titulo, confirma; o pacote e montado,
    o pedido vai para o "Claude Code" (falso) e a fila mostra. Depois o "Claude" grava o resultado.json."""
    import json

    from interface.menus import todos_os_itens
    from publicacao import fila

    st, registro, erros = studio
    info = st.projetos["teste das telas"]
    jan = st.publicar_shorts(info)
    assert len(jan.itens) == 2
    d1, d2 = (i["horario"][:10] for i in jan.itens)
    assert d1 < d2  # um por dia
    jan.titulo.delete(0, "end")
    jan.titulo.insert(0, "x" * 120)  # titulo grande demais: nao deixa publicar
    jan.confirmar()
    assert "aviso: Antes de publicar, arrume:" in registro and not fila.itens()
    jan.titulo.delete(0, "end")
    jan.titulo.insert(0, "Abri a água e deu ruim")
    jan.confirmar()
    for _ in range(100):  # espera montar os pacotes (em segundo plano)
        st.raiz.update()
        if not jan.enviando:
            break
        st.raiz.after(50)
    itens = fila.itens()
    assert [i["status"] for i in itens] == ["enviando", "enviando"] and itens[0]["titulo"] == "Abri a água e deu ruim"
    assert any("abre o Claude Code" in r and "--chrome" in r for r in registro)
    assert st.tela_atual == "publicacao"
    # de novo: nada para publicar (os 2 ja estao na fila)
    assert st.publicar_shorts(info) is None
    # o "Claude" terminou o primeiro
    pacote = itens[0]["pacote"]
    (Path(pacote) / "resultado.json").write_text(json.dumps({"status": "agendado", "link": "https://youtu.be/a"}))
    st.pagina_publicacao.conferir()
    assert fila.pegar(itens[0]["id"])["status"] == "agendado"
    pub = json.loads((info["pasta"] / "prontos" / "publicacao.json").read_text())
    assert pub["shorts"][0]["postado"]["youtube"] is True
    # cada item do botao direito da fila
    pag = st.pagina_publicacao
    pag.atualizar_lista()
    for id_ in pag.tree.get_children():
        pag.tree.selection_set(id_)
        evento = type("E", (), {"y": pag.tree.bbox(id_)[1] + 5})()
        for rotulo, k, menu in todos_os_itens(pag.menu_do_item(evento)):
            if "Tirar da fila" in rotulo:
                continue
            pag.tree.selection_set(id_)
            menu.invoke(k)
            st.raiz.update()
    assert any("abre navegador" in r for r in registro)
    assert not erros, erros


def test_gerar_cortes_e_editar_com_o_claude_num_clique(studio, monkeypatch):
    """Fase 5: os botoes mandam para o Claude (falso), mostram o progresso e salvam o resultado,
    guardando o arquivo anterior. Sem o Claude Code, cai no jeito antigo (copiar o pedido)."""
    from tkinter import messagebox

    from publicacao import claude_pc

    st, registro, erros = studio
    monkeypatch.setattr(messagebox, "askyesno", lambda *a, **k: True)
    pasta = PASTA_TRABALHO / "shorts" / "teste das telas"
    (pasta / "transcricao_para_claude.txt").write_text("VIDEO: x\n\n[00:00:10-00:00:40] fala", encoding="utf-8")

    def esperar():
        for _ in range(200):
            st.raiz.update()
            janelas = [w for w in st.raiz.winfo_children() if isinstance(w, tk.Toplevel)
                       and w.title() in ("Gerar cortes com o Claude", "Editar com o Claude")]  # fmt: skip
            if not janelas:
                return
            st.raiz.after(30)
        raise AssertionError("o Claude falso nao terminou")

    st.mostrar("shorts")
    st.aba_shorts.tree.selection_set("teste das telas")
    st.aba_shorts.pedir_cortes()
    esperar()
    assert json.loads((pasta / "cortes.json").read_text(encoding="utf-8"))["cortes"][0]["titulo"] == "Novo"
    assert (pasta / "cortes_anterior.json").exists() and "pergunta ao Claude (falso)" in registro
    st.mostrar("longos")
    st.aba_longos.tree.selection_set("teste das telas")
    st.aba_longos.editar_com_claude()
    esperar()
    edicao = json.loads((pasta / "edicao.json").read_text(encoding="utf-8"))
    assert edicao["versao"] == 2 and edicao["remover"][0]["motivo"] == "menu"
    assert (pasta / "edicao_anterior.json").exists()
    assert any(isinstance(w, tk.Toplevel) and "Editar vídeo longo" in w.title() for w in st.raiz.winfo_children())
    # sem o Claude Code: copia o pedido (jeito antigo)
    monkeypatch.setattr(claude_pc, "achar_claude_code", lambda: None)
    st.mostrar("shorts")
    st.aba_shorts.tree.selection_set("teste das telas")
    st.aba_shorts.pedir_cortes()
    assert "copia texto" in registro
    assert not erros, erros


def test_revisao_do_video_longo_linha_do_tempo_outro_e_publicar(studio):
    """Fase 6: linha do tempo, botao direito (manter/remover), outro ligado/desligado e publicar o episodio."""
    from interface.janela_edicao import JanelaEdicao
    from interface.menus import todos_os_itens
    from videos_longos.pedido_edicao import para_interno

    st, registro, erros = studio
    pasta = PASTA_TRABALHO / "shorts" / "teste das telas"
    info = st.projetos["teste das telas"]
    jan = JanelaEdicao(st, info)
    st.raiz.update()
    assert jan.dados is not None
    assert str(jan.btn_publicar.cget("state")) == "disabled"  # ainda nao tem episodio
    jan.tree.selection_set("1")
    for _rotulo, k, menu in todos_os_itens(montar(jan, jan.itens_do_trecho(1))):  # inclui "Manter este trecho"
        jan.tree.selection_set("1")
        menu.invoke(k)
        st.raiz.update()
    assert "roda" in " ".join(registro)  # "Ouvir a emenda"

    def corte():
        return para_interno(json.loads((pasta / "edicao.json").read_text(encoding="utf-8")))["cortes"][0]

    assert corte()["ativo"] is False  # o trecho vai ficar no episodio
    jan.tree.selection_set("1")
    jan.alternar()  # "Remover" de novo
    assert "ativo" not in corte()
    jan.incluir_outro.set(False)
    jan.mudou_outro()
    assert json.loads((pasta / "edicao.json").read_text(encoding="utf-8"))["incluir_outro"] is False
    assert "Sem outro" in jan.lbl_outro.cget("text")
    jan.linha.event_generate("<Configure>")
    jan.desenhar_linha()
    jan.jan.destroy()
    # com o episodio gerado: Publicar abre a revisao com o titulo e a sugestao de horario
    (pasta / "episodio").mkdir(exist_ok=True)
    (pasta / "episodio" / "Teste.mp4").write_bytes(b"x")
    (pasta / "episodio" / "episodio.json").write_text(json.dumps({"arquivo": "Teste.mp4", "capitulos": []}))
    st.atualizar()
    info = st.projetos["teste das telas"]
    assert info["proximo_longo"] == "publicar"
    pub = st.publicar_longo(info)
    assert pub.itens[0]["tipo"] == "longo" and pub.itens[0]["titulo"] == "Teste"
    pub.jan.destroy()
    assert not erros, erros


def test_cabe_numa_tela_de_1366x768(studio):
    """Cada tela e cada janela cabem num notebook de 1366x768 (descontando ~50 px da barra de tarefas)."""
    from interface.editor_legendas import EditorLegendas
    from interface.janela_edicao import JanelaEdicao

    st, registro, erros = studio
    limite_altura, limite_largura = 768 - 50, 1366
    for codigo, tela in st.telas.items():
        st.mostrar(codigo)
        st.raiz.update_idletasks()
        lateral = 220
        assert tela.winfo_reqheight() <= limite_altura, (codigo, tela.winfo_reqheight())
        assert tela.winfo_reqwidth() + lateral <= limite_largura, (codigo, tela.winfo_reqwidth())
    st.mostrar("shorts")
    st.aba_shorts.tree.selection_set("teste das telas")
    info = st.aba_shorts.selecionado()
    janelas = [EditorLegendas(st, info).jan, JanelaEdicao(st, info).jan, st.publicar_shorts(info).jan]
    for jan in janelas:
        jan.update_idletasks()
        assert jan.winfo_reqheight() <= limite_altura, (jan.title(), jan.winfo_reqheight())
        assert jan.winfo_reqwidth() <= limite_largura, (jan.title(), jan.winfo_reqwidth())
        jan.destroy()
    assert not erros, erros


def test_selecionar_varios_com_caixinha_ctrl_shift_e_todos(studio):
    """1.6.0: caixinha, Ctrl + clique, Shift + clique, Selecionar todos, Limpar e o botao laranja do lote."""
    import shutil

    st, registro, erros = studio
    origem = PASTA_TRABALHO / "shorts" / "teste das telas"
    copias = [PASTA_TRABALHO / "shorts" / n for n in ("segundo projeto", "terceiro projeto")]
    for c in copias:
        shutil.rmtree(c, ignore_errors=True)
        shutil.copytree(origem, c)
    st.atualizar()
    st.mostrar("shorts")
    aba = st.aba_shorts
    st.raiz.update()
    itens = list(aba.tree.get_children())
    assert len(itens) == 3

    def clicar(item, coluna="#0", **tecla):
        x0, y0, w, h = aba.tree.bbox(item, coluna)
        evento = type("E", (), {"x": x0 + w // 2, "y": y0 + h // 2})()
        aba.clique(evento, tecla.get("ctrl", False), tecla.get("shift", False))
        st.raiz.update()

    clicar(itens[0])
    assert list(aba.tree.selection()) == [itens[0]]
    assert aba.btn_principal.cget("text") != "" and "selecionados" not in aba.btn_principal.cget("text")
    clicar(itens[2], ctrl=True)
    assert list(aba.tree.selection()) == [itens[0], itens[2]]
    assert aba.btn_principal.cget("text") == "Gerar Shorts dos selecionados (2)"
    assert aba.lbl_contador.cget("text") == "2 vídeos selecionados"
    assert aba.tree.set(itens[0], "marcar") == "☑" and aba.tree.set(itens[1], "marcar") == "☐"
    clicar(itens[0])
    clicar(itens[2], shift=True)
    assert list(aba.tree.selection()) == itens
    clicar(itens[1], coluna="marcar")  # a caixinha desmarca so ele
    assert list(aba.tree.selection()) == [itens[0], itens[2]]
    aba.limpar_selecao()
    st.raiz.update()
    assert aba.selecionados() == [] and aba.lbl_contador.cget("text") == "Nenhum vídeo selecionado"
    aba.selecionar_todos()
    st.raiz.update()
    assert len(aba.selecionados()) == 3 and aba.tree.heading("marcar")["text"] == "☑"
    aba.alternar_todos()
    st.raiz.update()
    assert aba.selecionados() == []
    st.atualizar()  # a lista se atualiza sozinha e nao volta a selecionar o primeiro depois do "Limpar"
    assert aba.selecionados() == []
    for c in copias:
        shutil.rmtree(c, ignore_errors=True)
    assert not erros, erros


def test_lote_preparar_rodar_resumo_e_tentar_de_novo(studio, monkeypatch):
    """1.6.0: Preparar lote (ordem, Pular / Gerar de novo, avisos), tela do lote, resumo, Revisar, erro e
    "Tentar de novo so este". As etapas sao falsas (sem Whisper, Claude ou ffmpeg)."""
    import shutil
    import time

    from interface.janela_lote import JanelaLote
    from nucleo import limpeza
    from shorts import lote as motor

    st, registro, erros = studio
    origem = PASTA_TRABALHO / "shorts" / "teste das telas"
    novos = [PASTA_TRABALHO / "shorts" / n for n in ("video sem cortes", "video novo")]
    for c in novos:
        shutil.rmtree(c, ignore_errors=True)
        shutil.copytree(origem, c)
        shutil.rmtree(c / "prontos")
        (c / "cortes.json").unlink()
        (c / "transcricao_para_claude.txt").write_text("x", encoding="utf-8")
    (novos[1] / "transcricao.json").unlink()  # "video novo" nem foi transcrito
    lixeira = []
    monkeypatch.setattr(limpeza, "mandar_para_lixeira",
                        lambda c: (lixeira.extend(c), [Path(f).unlink() for f in c], True)[2])  # fmt: skip
    falhar = {"video sem cortes"}
    import threading

    segura = threading.Event()  # o lote falso espera o teste conferir a tela "durante" o lote

    class Falsas:
        def transcrever(self, v, cancelar, progresso):
            registro.append(f"lote: transcreve {v['nome']}")
            p = Path(v["pasta"])
            (p / "transcricao.json").write_text('{"segmentos": []}', encoding="utf-8")
            (p / "transcricao_para_claude.txt").write_text("x", encoding="utf-8")

        def pedir_cortes(self, v, cancelar, progresso):
            registro.append(f"lote: cortes {v['nome']}")
            if v["nome"] in falhar:
                raise motor.ErroLote("O Claude não conseguiu escolher os cortes: sem internet")
            (Path(v["pasta"]) / "cortes.json").write_text(
                json.dumps({"cortes": [{"inicio": 1, "fim": 9, "titulo": "A"}]}), encoding="utf-8"
            )

        def renderizar(self, v, cancelar, progresso):
            segura.wait(5)
            registro.append(f"lote: renderiza {v['nome']}")
            (Path(v["pasta"]) / "prontos").mkdir(exist_ok=True)
            (Path(v["pasta"]) / "prontos" / "01 - A.mp4").write_bytes(b"x")
            return 0

    monkeypatch.setattr(motor, "Etapas", Falsas)
    st.atualizar()
    st.mostrar("shorts")
    aba = st.aba_shorts
    aba.selecionar_todos()
    st.raiz.update()
    assert aba.btn_principal.cget("text") == "Gerar Shorts dos selecionados (3)"
    aba.btn_principal.invoke()
    st.raiz.update()
    assert any(isinstance(w, tk.Toplevel) and w.title() == "Preparar lote" for w in st.raiz.winfo_children())
    # a janela: o projeto com Shorts comeca como "Pular"; os outros mostram o que vai ser feito
    instancia = _instancias_preparar(st)[0]
    assert instancia.escolha == {"teste das telas": "Pular"}
    assert instancia.tree.item("video novo")["values"][1] == "transcrever → cortes com o Claude → gerar Shorts"
    assert instancia.tree.item("video sem cortes")["values"][1] == "cortes com o Claude → gerar Shorts"
    assert instancia.tree.item("teste das telas")["values"][1] == "(pulado)"
    assert "2 vídeo(s) no lote, 1 pulado(s)" == instancia.lbl_resumo.cget("text")
    textos = " ".join(str(w.cget("text")) for w in _todos(instancia.avisos) if isinstance(w, tk.Label))
    assert "NVIDIA" in textos or "câmera" in textos
    # Gerar de novo (por clique na coluna) e ordem (Subir)
    instancia.tree.selection_set("teste das telas")
    instancia.escolher("Gerar de novo")
    assert instancia.escolha["teste das telas"] == "Gerar de novo"
    ordem = instancia.ordem()
    instancia.tree.selection_set(ordem[-1])
    instancia.mover(-1)
    assert instancia.ordem() == ordem[:-2] + [ordem[-1], ordem[-2]]
    assert [str(instancia.tree.item(n)["values"][0]) for n in instancia.ordem()] == ["1", "2", "3"]
    instancia.jan.update_idletasks()
    assert instancia.jan.winfo_reqheight() <= 768 - 50 and instancia.jan.winfo_reqwidth() <= 1366
    instancia.comecar()
    st.raiz.update()
    rodar = st.lote_atual
    assert rodar is not None and isinstance(st.janela_lote, JanelaLote)
    assert aba.btn_principal.cget("text") == "Ver o lote em andamento"
    segura.set()
    for _ in range(100):
        st.raiz.update()
        if rodar.terminou.is_set():
            break
        time.sleep(0.05)
    st.raiz.update()
    st._vigiar_lote()
    lote = rodar.retrato()
    assert {v["nome"]: v["etapa"] for v in lote["videos"]} == {
        "teste das telas": "pronto", "video novo": "pronto", "video sem cortes": "erro"}  # fmt: skip
    assert [f.name for f in lixeira] == ["01 - Um.mp4", "02 - Dois.mp4"]  # "gerar de novo" foi para a Lixeira
    jl = st.janela_lote
    jl.conferir()
    st.raiz.update()
    assert "Lote pronto: 2 Shorts de 2 vídeo(s)" == jl.lbl_titulo.cget("text")
    assert jl.tree.selection() == ("video sem cortes",)
    assert "sem internet" in jl.lbl_erro.cget("text")
    assert str(jl.btn_tentar.cget("state")) == "normal"
    jl.jan.update_idletasks()
    assert jl.jan.winfo_reqheight() <= 768 - 50 and jl.jan.winfo_reqwidth() <= 1366
    # Revisar abre o editor de Shorts do projeto
    jl.tree.selection_set("video novo")
    st.raiz.update()
    antes = {str(w) for w in st.raiz.winfo_children()}
    jl.revisar()
    st.raiz.update()
    assert any(isinstance(w, tk.Toplevel) and str(w) not in antes for w in st.raiz.winfo_children())
    # Tentar de novo so este: so o video com erro roda
    falhar.clear()
    jl.tree.selection_set("video sem cortes")
    st.raiz.update()
    registro.clear()
    jl.tentar_de_novo()
    for _ in range(100):
        st.raiz.update()
        if st.lote_atual.terminou.is_set():
            break
        time.sleep(0.05)
    st.raiz.update()
    assert [r for r in registro if r.startswith("lote:")] == ["lote: cortes video sem cortes",
                                                               "lote: renderiza video sem cortes"]  # fmt: skip
    assert all(v["etapa"] == "pronto" for v in st.lote_atual.retrato()["videos"])
    import gc

    st._vigiar_lote()  # o lote terminou: a limpeza automatica da memoria volta a ficar ligada
    assert gc.isenabled()
    for w in st.raiz.winfo_children():
        if isinstance(w, tk.Toplevel):
            w.destroy()
    for c in novos:
        shutil.rmtree(c, ignore_errors=True)
    motor.arquivo().unlink(missing_ok=True)
    assert not erros, erros


def _instancias_preparar(_st):
    """A janela Preparar lote aberta (achada pelo coletor de lixo: o Studio nao guarda referencia)."""
    import gc

    from interface.janela_preparar_lote import JanelaPrepararLote

    return [o for o in gc.get_objects() if isinstance(o, JanelaPrepararLote) and o.jan.winfo_exists()]


def test_lote_parado_pergunta_se_continua_ao_abrir(studio, monkeypatch):
    """1.6.0: ao abrir, um lote que parou no meio pergunta "Continuar o lote de onde parou?"."""
    from tkinter import messagebox

    from shorts import lote as motor

    st, registro, erros = studio
    info = st.projetos["teste das telas"]
    salvo = motor.montar_lote([info], refazer={"teste das telas": True})
    salvo["situacao"] = "rodando"
    motor.salvar(salvo)
    comecados = []
    monkeypatch.setattr(st, "comecar_lote", lambda lote, janela=None: comecados.append(lote))
    perguntas = []
    monkeypatch.setattr(messagebox, "askyesno", lambda t, m="", **k: (perguntas.append(m), True)[1])
    st.perguntar_retomar_lote()
    assert "Continuar o lote de onde parou?" in perguntas[0] and len(comecados) == 1
    # respondendo "nao": o lote fica como cancelado e nao pergunta mais
    monkeypatch.setattr(messagebox, "askyesno", lambda t, m="", **k: (perguntas.append(m), False)[1])
    st.perguntar_retomar_lote()
    assert motor.carregar()["situacao"] == "cancelado"
    st.perguntar_retomar_lote()
    assert len(perguntas) == 2
    motor.arquivo().unlink(missing_ok=True)
    assert not erros, erros


def test_editor_de_legendas_abre_uma_janela_so(studio):
    """Clicar varias vezes em Revisar legendas nao abre varias janelas: so traz a que ja esta aberta."""
    from interface.editor_legendas import EditorLegendas

    st, registro, erros = studio
    st.mostrar("shorts")
    st.aba_shorts.tree.selection_set("teste das telas")
    st.raiz.update()
    st.aba_shorts.revisar_legendas()
    st.aba_shorts.revisar_legendas()
    st.aba_shorts.revisar_legendas()
    st.raiz.update()
    editores = [j for j in st.raiz.winfo_children()
                if isinstance(j, tk.Toplevel) and j.title().startswith("Revisar legendas")]  # fmt: skip
    assert len(editores) == 1
    ed = next(iter(EditorLegendas.abertos.values()))
    ed.fechar()
    st.raiz.update()
    assert not EditorLegendas.abertos
    st.aba_shorts.revisar_legendas()  # depois de fechar, abre de novo
    st.raiz.update()
    assert len(EditorLegendas.abertos) == 1
    next(iter(EditorLegendas.abertos.values())).fechar()


def test_tecla_delete_exclui_mesmo_sem_foco_na_lista(studio, monkeypatch):
    """Delete na janela principal abre o Excluir do projeto selecionado, mesmo com o foco fora da lista.
    Numa caixa de texto, o Delete so apaga a letra."""
    from types import SimpleNamespace

    st, registro, erros = studio
    st.mostrar("shorts")
    st.aba_shorts.tree.selection_set("teste das telas")
    st.raiz.update()
    chamadas = []
    monkeypatch.setattr(st.aba_shorts, "excluir", lambda: chamadas.append("excluir"))
    assert st.tecla_delete(SimpleNamespace(widget=st.raiz)) == "break"
    assert chamadas == ["excluir"]
    caixa = tk.Entry(st.raiz)
    assert st.tecla_delete(SimpleNamespace(widget=caixa)) is None
    caixa.destroy()
    assert chamadas == ["excluir"]
    st.mostrar("inicio")
    st.tecla_delete(SimpleNamespace(widget=st.raiz))
    assert chamadas == ["excluir"]  # fora das telas de projetos, nao faz nada


def test_publicar_com_varios_selecionados_junta_todos(studio):
    """Com 2 videos selecionados, Publicar mostra os Shorts prontos dos DOIS (antes so vinha o primeiro)."""
    st, registro, erros = studio
    copia = PASTA_TRABALHO / "shorts" / "teste das telas 2"
    shutil.rmtree(copia, ignore_errors=True)
    shutil.copytree(PASTA_TRABALHO / "shorts" / "teste das telas", copia)
    try:
        st.atualizar()
        st.mostrar("shorts")
        st.aba_shorts.tree.selection_set(["teste das telas", "teste das telas 2"])
        st.raiz.update()
        jan = st.aba_shorts.publicar()
        assert jan is not None
        assert sorted(i["projeto"] for i in jan.itens) == ["teste das telas"] * 2 + ["teste das telas 2"] * 2
        assert len({i["horario"] for i in jan.itens}) == 4  # um dia para cada Short
        jan.jan.destroy()
        rotulos = [r[0] for r in st.aba_shorts.itens_do_menu_varios(st.aba_shorts.selecionados())]
        assert rotulos == ["📅  Publicar os Shorts dos 2 selecionados"]
    finally:
        shutil.rmtree(copia, ignore_errors=True)


def test_reportar_bug_em_qualquer_menu_e_janela(studio, monkeypatch):
    """Todo menu de botao direito termina com "Reportar bug"; a janela junta o contexto e abre a issue."""
    import webbrowser

    from interface import reportar_bug
    from interface.menus import todos_os_itens
    from nucleo import relato_bug

    st, registro, erros = studio
    monkeypatch.setattr(relato_bug, "PASTA_BUGS", PASTA_TRABALHO / "bugs_teste")
    st.mostrar("shorts")
    st.aba_shorts.tree.selection_set("teste das telas")
    st.raiz.update()
    abertos = []
    monkeypatch.setattr(webbrowser, "open", lambda url: abertos.append(url))
    monkeypatch.setattr(tk.Menu, "tk_popup", lambda self, x, y: None)  # nao mostra o menu de verdade
    menus = []
    monkeypatch.setattr("interface.menus.abrir_menu", lambda evento, menu: menus.append(menu))
    aba = st.aba_shorts
    evento = SimpleNamespace(x=5, y=aba.tree.bbox("teste das telas")[1] + 5, x_root=0, y_root=0, widget=aba.tree)
    aba.tree.event_generate("<Button-3>", x=evento.x, y=evento.y)
    st.raiz.update()
    assert menus, "o botao direito nao abriu menu"
    rotulos = [r for r, *_ in todos_os_itens(menus[-1])]
    assert rotulos[-1] == reportar_bug.ITEM_DO_MENU and "📅  Publicar" in rotulos
    jan = reportar_bug.abrir(aba.tree)
    assert reportar_bug.abrir(aba.tree) is jan  # so uma janela de cada vez
    assert jan.contexto["Tela aberta"] == "Shorts"
    assert jan.contexto["Vídeos selecionados"][0].startswith("teste das telas")
    jan.texto.insert("1.0", "O botão X não funciona\nCliquei e nada")
    url = jan.enviar()
    assert abertos == [url] and "bug-do-app" in url and not jan.jan.winfo_exists()
    assert list((PASTA_TRABALHO / "bugs_teste").glob("*.md"))
    shutil.rmtree(PASTA_TRABALHO / "bugs_teste", ignore_errors=True)


def test_publicar_abre_uma_revisao_so_e_nao_agenda_duas_vezes(studio):
    """Duas revisoes de publicacao abertas podiam agendar o mesmo Short duas vezes (subia 2x no YouTube)."""
    from publicacao import fila

    st, registro, erros = studio
    info = st.projetos["teste das telas"]
    j1 = st.publicar_shorts(info)
    j2 = st.publicar_shorts(info)
    assert j1 is not None and j2 is j1  # a segunda so traz a primeira para a frente
    assert st.publicar_todos_os_shorts() is j1
    fila.adicionar([dict(j1.itens[0], id="outro")])  # outra revisao (ou o lote) ja mandou para a fila
    assert any("já está na fila" in e for e in j1.problemas())
    j1.jan.destroy()
    st.raiz.update()
    j3 = st.publicar_shorts(info)
    assert j3 is not None and j3 is not j1 and len(j3.itens) == 1  # so o que ainda nao esta na fila
    j3.jan.destroy()


def test_janelas_que_abrem_uma_vez_so(studio):
    """Revisao do video longo e Excluir: clicar de novo traz a janela aberta (antes abria outra igual)."""
    from interface.utilidades import janela_ja_aberta, lembrar_janela

    st, registro, erros = studio
    info = st.projetos["teste das telas"]
    r1 = st.aba_longos.abrir_revisao(info)
    assert st.aba_longos.abrir_revisao(info) is r1
    r1.jan.destroy()
    st.raiz.update()
    assert st.aba_longos.abrir_revisao(info) is not r1
    st.mostrar("shorts")
    st.aba_shorts.tree.selection_set("teste das telas")
    st.raiz.update()
    e1 = st.aba_shorts.excluir()
    assert st.aba_shorts.excluir() is e1
    e1.jan.destroy()
    # janela que ja fechou sozinha (ex.: o Claude respondeu um erro na hora) nao fica anotada
    obj = SimpleNamespace(jan=tk.Toplevel(st.raiz))
    obj.jan.destroy()
    assert lembrar_janela("teste", obj) is obj and janela_ja_aberta("teste") is None
