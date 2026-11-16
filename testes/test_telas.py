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
    assert "corta o trecho no ffmpeg" in registro and "escolhe cor" in registro
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
    assert "corta o trecho no ffmpeg" in registro  # "Trecho com o efeito" montou a previa
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
    assert "corta o trecho no ffmpeg" in registro  # "Assistir este trecho" / "Ouvir" montou o trecho
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
    # o menu do botao direito com 2 selecionados so tem "Excluir 2 projetos..."
    evento = type("E", (), {"y": aba.tree.bbox("segundo projeto")[1] + 5})()
    itens = todos_os_itens(aba.menu_do_projeto(evento))
    assert [r for r, *_ in itens] == ["🗑  Excluir 2 projetos..."]
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
