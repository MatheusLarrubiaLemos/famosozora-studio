# Confere as telas botao por botao (lento, ~20 s): abre o Studio numa pasta de trabalho de teste, aperta cada
# botao das duas abas, cada item do Menu e os botoes de cada janela (Publicar, Revisar legendas, revisao do
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
    for modulo in (interface.janela_principal, interface.janela_publicar):
        monkeypatch.setattr(modulo, "webbrowser", SimpleNamespace(open=fazer("abre navegador")))
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

    st = interface.janela_principal.Studio()
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
        if isinstance(filho, (ttk.Button, tk.Button, tk.Checkbutton)):
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
    for aba, nome_aba in ((st.aba_shorts, "Aba Shorts"), (st.aba_longos, "Aba Vídeos longos")):
        st.abas.select(aba)
        aba.tree.selection_set("teste das telas")
        st.raiz.update()
        for botao in _botoes(aba.direita):
            nome = str(botao.cget("text"))
            if "Limpar projeto" in nome:  # respondido NAO/CANCELAR: nao manda nada para a Lixeira
                _apertar(st, botao, registro, erros, tabela, nome_aba)
                continue
            for janela in _apertar(st, botao, registro, erros, tabela, nome_aba):
                for b in _botoes(janela):
                    if not b.winfo_exists() or str(b.cget("text")).strip() in ("Depois",):
                        continue
                    _apertar(st, b, registro, erros, tabela, f"  janela {janela.title()[:28]}")
                janela.destroy()
    botao_menu = next(w for w in _todos(st.raiz) if isinstance(w, ttk.Menubutton))
    menu = st.raiz.nametowidget(botao_menu.cget("menu"))
    for k in range(menu.index("end") + 1):
        if menu.type(k) in ("command", "checkbutton"):
            rotulo = menu.entrycget(k, "label")
            antes_reg, antes_err = len(registro), len(erros)
            menu.invoke(k)
            st.raiz.update()
            novas = [w for w in st.raiz.winfo_children() if isinstance(w, tk.Toplevel)]
            feito = registro[antes_reg:] + [f"abre a janela: {w.title()}" for w in novas]
            tabela.append(("Menu", rotulo, not erros[antes_err:], "; ".join(feito + erros[antes_err:]) or "-"))
            for w in novas:
                w.destroy()
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
    st.abas.select(st.aba_shorts)
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
    st.abas.select(st.aba_shorts)
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
    pa.tree.selection_set("0")
    for b in _botoes(pa.tree.master.master):  # todos os botoes da aba, com o efeito selecionado
        if b.winfo_exists() and "Restaurar" not in str(b.cget("text")):
            pa.tree.selection_set("0") if pa.tree.exists("0") else None
            b.invoke()
            st.raiz.update()
    assert "corta o trecho no ffmpeg" in registro  # "Trecho com o efeito" montou a previa
    ed.desfazer()
    assert ed.salvar() and edicao.ler_edicao(ed.pasta, ed.n) is not None
    pa.restaurar()
    assert ed.salvar() and edicao.ler_edicao(ed.pasta, ed.n) is None  # igual a sugestao: nao guarda edicao
    assert not erros, erros
    ed.jan.destroy()
