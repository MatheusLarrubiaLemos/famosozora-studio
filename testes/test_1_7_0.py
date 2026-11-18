# Testes da versao 1.7.0: reportar bug, excluir na primeira tentativa (Lixeira tenta de novo sozinha) e o editor de
# legendas abrindo uma janela so por video.


def test_lixeira_tenta_de_novo_quando_o_arquivo_esta_preso(tmp_path, monkeypatch):
    """No Windows o arquivo pode ficar preso um instante (Explorer, antivirus). O Studio tenta de novo sozinho."""
    import send2trash

    from nucleo import limpeza

    monkeypatch.setattr(limpeza, "ESPERAS_LIXEIRA", (0, 0, 0))
    a, b = tmp_path / "a.mp4", tmp_path / "b.mp4"
    a.write_bytes(b"x")
    b.write_bytes(b"x")
    tentativas = []

    def preso_nas_duas_primeiras(c):
        tentativas.append(c)
        if c.endswith("a.mp4") and tentativas.count(c) < 3:
            raise OSError("arquivo em uso")
        __import__("os").remove(c)  # faz de conta que foi para a Lixeira

    monkeypatch.setattr(send2trash, "send2trash", preso_nas_duas_primeiras)
    assert limpeza.mandar_para_lixeira([a, b]) is True
    assert not a.exists() and not b.exists()
    assert tentativas.count(str(b.resolve())) == 1  # o "b" foi logo, mesmo com o "a" preso


def test_lixeira_desiste_depois_de_algumas_tentativas(tmp_path, monkeypatch):
    import send2trash

    from nucleo import limpeza

    monkeypatch.setattr(limpeza, "ESPERAS_LIXEIRA", (0, 0, 0))
    arq = tmp_path / "a.mp4"
    arq.write_bytes(b"x")
    vezes = []
    monkeypatch.setattr(send2trash, "send2trash", lambda c: vezes.append(c) or (_ for _ in ()).throw(OSError()))
    assert limpeza.mandar_para_lixeira([arq]) is False
    assert arq.exists() and len(vezes) == 4  # nada apagado de vez


# ------------------------------------------------------------------ Reportar bug
def test_relato_tem_contexto_trilha_erros_e_log(tmp_path, monkeypatch):
    from nucleo import relato_bug
    from versao import VERSAO

    log = tmp_path / "studio.log"
    log.write_text("\n".join(f"linha {k}" for k in range(100)), encoding="utf-8")
    monkeypatch.setattr(relato_bug, "ARQ_LOG", log)
    monkeypatch.setattr(relato_bug, "PASTA_BUGS", tmp_path / "bugs")
    relato_bug.trilha.clear()
    relato_bug.erros_recentes.clear()
    relato_bug.anotar('clicou em "Publicar"')
    relato_bug.anotar('clicou em "Publicar"')  # repetido seguido: anota uma vez so
    relato_bug.anotar_erro("Traceback: KeyError 'nome'")
    contexto = {"Tela aberta": "Shorts", "Vídeos selecionados": ["BULLY FINAL", "BULLY9"]}
    texto = relato_bug.montar_texto("Publicar só puxa alguns\nselecionei 5", contexto)
    assert f"Versão: {VERSAO}" in texto and "Tela aberta: Shorts" in texto and "  - BULLY9" in texto
    assert texto.count('clicou em "Publicar"') == 1 and "KeyError 'nome'" in texto
    assert "linha 99" in texto and "linha 39" not in texto  # so as ultimas 60 linhas do log
    titulo = relato_bug.titulo_do_relato("\n  Publicar só puxa alguns\nselecionei 5")
    assert titulo == f"[{VERSAO}] Publicar só puxa alguns"
    arq = relato_bug.salvar(titulo, texto)
    assert arq.read_text(encoding="utf-8").startswith(f"# {titulo}")


def test_endereco_da_issue_cabe_no_navegador(tmp_path, monkeypatch):
    import urllib.parse

    from nucleo import relato_bug

    log = tmp_path / "studio.log"
    log.write_text("\n".join("erro comprido " * 20 for _ in range(200)), encoding="utf-8")
    monkeypatch.setattr(relato_bug, "ARQ_LOG", log)
    for k in range(40):
        relato_bug.anotar(f"clique numero {k} " + "x" * 100)
    url = relato_bug.endereco_que_cabe("Deu erro ao publicar", {"Tela aberta": "Shorts"})
    assert len(url) <= relato_bug.TAMANHO_MAXIMO_URL
    assert url.startswith(relato_bug.REPO_URL + "/issues/new?")
    campos = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    assert campos["labels"] == ["bug-do-app"] and "Deu erro ao publicar" in campos["body"][0]
    enorme = relato_bug.endereco_que_cabe("a" * 20000, {})
    assert len(enorme) <= relato_bug.TAMANHO_MAXIMO_URL


def test_relato_nao_leva_nada_pessoal(monkeypatch):
    """O GitHub e publico: pasta e nome do usuario, nome do PC, e-mails e chaves nunca vao no relato."""
    from pathlib import Path

    from nucleo import relato_bug

    monkeypatch.setattr(Path, "home", staticmethod(lambda: Path("C:\\Users\\Fulano")))
    monkeypatch.setenv("USERNAME", "Fulano")
    monkeypatch.setenv("COMPUTERNAME", "PC-DO-FULANO")
    texto = relato_bug.sem_dados_pessoais(
        "erro em C:\\Users\\Fulano\\AppData\\x.json e D:\\Lives\\Fulano\\live.mp4 e C:/Users/Fulano/a\n"
        "maquina PC-DO-FULANO, contato fulano.silva@exemplo.com\n"
        "token=abc123def456 Authorization: Bearer abcdefghijklmnop1234 chave ghp_" + "a" * 30 + "\n"
        "api_key: 'sk-ant-" + "b" * 30 + "' senha=minhasenha"
    )
    for pessoal in ("Fulano", "FULANO", "exemplo.com", "abc123def456", "abcdefghijklmnop1234", "aaaaaaaa",
                    "bbbbbbbb", "minhasenha"):  # fmt: skip
        assert pessoal not in texto, (pessoal, texto)
    assert "%USERPROFILE%\\AppData\\x.json" in texto and "%USERPROFILE%/a" in texto
    assert "%COMPUTERNAME%" in texto and "[e-mail escondido]" in texto
    titulo = relato_bug.titulo_do_relato("Erro com fulano.silva@exemplo.com")
    assert "exemplo.com" not in titulo


# ------------------------------------------------------------------ legenda editada de outro corte
def test_editada_de_outro_trecho_nao_vale_e_vai_para_antigas(tmp_path):
    """Pediu cortes novos ao Claude: o Short 01 virou outro trecho. A legenda editada do corte antigo nao pode
    entrar no Short novo (antes entrava, com o texto e os tempos errados)."""
    from shorts import revisao

    palavras = [{"i": 10.0, "f": 10.4, "p": "Oi"}]
    revisao.salvar_editada(tmp_path, 1, palavras, False, 10.0, 20.0)
    assert revisao.editada_do_trecho(tmp_path, 1, 10.0, 20.0)["palavras"] == palavras  # mesmo corte: vale
    assert revisao.editada_do_trecho(tmp_path, 1, 10.02, 19.98) is not None  # arredondado diferente: vale
    assert revisao.editada_do_trecho(tmp_path, 1, 50.0, 70.0) is None  # outro corte: nao vale
    assert revisao.ler_editada(tmp_path, 1) is None
    guardadas = list((tmp_path / "legendas" / "antigas").glob("01_editada_*.json"))
    assert len(guardadas) == 1  # nada se perde


def test_editada_antiga_sem_trecho_confere_com_o_original(tmp_path):
    from shorts import revisao

    revisao.salvar_original(tmp_path, 2, "02 - X.mp4", 30.0, 40.0, [{"i": 30, "f": 31, "p": "a"}])
    revisao.salvar_editada(tmp_path, 2, [{"i": 30, "f": 31, "p": "A"}], False)  # do jeito antigo (sem trecho)
    assert revisao.editada_do_trecho(tmp_path, 2, 30.0, 40.0) is not None  # e do corte que foi gerado
    assert revisao.editada_do_trecho(tmp_path, 2, 100.0, 120.0) is None  # corte novo: vai para antigas
    assert revisao.editada_do_trecho(tmp_path, 2, None, None) is None  # (ja foi guardada)


def test_ligacoes_de_voz_de_outro_trecho_nao_valem(tmp_path):
    from shorts import pessoas

    pessoas.salvar_ligacoes(tmp_path, 1, {"0": "Pedro"}, 10.0, 20.0)
    assert pessoas.ler_ligacoes(tmp_path, 1, 10.0, 20.0) == {"0": "Pedro"}
    assert pessoas.ler_ligacoes(tmp_path, 1, 50.0, 70.0) == {}  # cortes novos: a voz 0 e outra pessoa
    assert pessoas.ler_ligacoes(tmp_path, 1) == {"0": "Pedro"}  # sem trecho para conferir
    pessoas.salvar_ligacoes(tmp_path, 2, {"1": "Ana"})  # do jeito antigo (sem trecho): continua valendo
    assert pessoas.ler_ligacoes(tmp_path, 2, 5.0, 9.0) == {"1": "Ana"}
    pessoas.salvar_ligacoes(tmp_path, 1, {}, 10.0, 20.0)
    assert pessoas.ler_ligacoes(tmp_path, 1) == {}


def test_gerar_nao_usa_a_editada_do_corte_antigo(tmp_path):
    """Na geracao, o Short novo usa a transcricao do trecho NOVO, nao a editada do corte antigo."""
    from shorts import gerar_shorts, revisao

    revisao.salvar_editada(tmp_path, 1, [{"i": 10.0, "f": 10.5, "p": "ANTIGA"}], False, 10.0, 20.0)
    palavras = [{"i": 50.5, "f": 51.0, "p": "nova"}, {"i": 51.2, "f": 51.6, "p": "fala"}]
    proj = {
        "pasta": tmp_path,
        "video": tmp_path / "v.mp4",
        "correcoes": {},
        "segmentos": [{"inicio": 50.0, "fim": 52.0, "texto": "nova fala", "palavras": palavras}],
    }

    class Nada:
        def palavras(self, *a, **k):
            return None

        def trechos(self, *a, **k):
            return []

    ferr = {"retrans": Nada(), "falantes": Nada()}
    m = gerar_shorts.medir_corte({"inicio": 50.0, "fim": 60.0, "titulo": "Novo"}, 1, 0)
    blocos, _ = gerar_shorts.legendas_do_corte(proj, ferr, {"inicio": 50.0, "fim": 60.0}, m)
    textos = [w["p"] for _, ws, _ in blocos for w in ws]
    assert textos == ["nova", "fala"] and revisao.ler_editada(tmp_path, 1) is None
    assert revisao.ler_original(tmp_path, 1)["inicio"] == 50.0  # o original agora e do trecho novo


# ------------------------------------------------------------------ partes ao Claude ao mesmo tempo
def test_partes_vao_ao_claude_ao_mesmo_tempo_e_voltam_na_ordem(monkeypatch):
    import threading
    import time

    from nucleo import claude_local

    rodando, maximo, trava = [0], [0], threading.Lock()

    def falso(pedido, validar, cancelar, avisar=None, modelo=""):
        with trava:
            rodando[0] += 1
            maximo[0] = max(maximo[0], rodando[0])
        time.sleep(0.05 if pedido != "p0" else 0.15)  # a parte 1 demora mais: termina depois das outras
        with trava:
            rodando[0] -= 1
        return {"parte": pedido}

    monkeypatch.setattr(claude_local, "pedir_json", falso)
    feitas = []
    r = claude_local.pedir_partes(["p0", "p1", "p2", "p3"], None, threading.Event(), ao_terminar_parte=feitas.append,
                                  quantas_juntas=2)  # fmt: skip
    assert [x["parte"] for x in r] == ["p0", "p1", "p2", "p3"]  # na ordem das partes
    assert maximo[0] == 2 and feitas == [1, 2, 3, 4]  # 2 ao mesmo tempo, nunca mais que isso
    assert claude_local.simultaneos({"claude_pedidos_simultaneos": 1}) == 1
    assert claude_local.simultaneos({}) == 2 and claude_local.simultaneos({"claude_pedidos_simultaneos": "x"}) == 2


def test_parte_com_erro_para_as_outras(monkeypatch):
    import threading
    import time

    import pytest

    from nucleo import claude_local

    comecaram = []

    def falso(pedido, validar, cancelar, avisar=None, modelo=""):
        comecaram.append(pedido)
        if pedido == "p0":
            raise claude_local.ErroClaude("deu ruim na parte 1")
        for _ in range(100):  # as outras esperam e param quando uma da erro
            if cancelar.is_set():
                raise claude_local.Cancelado()
            time.sleep(0.01)
        return {}

    monkeypatch.setattr(claude_local, "pedir_json", falso)
    with pytest.raises(claude_local.ErroClaude, match="parte 1"):
        claude_local.pedir_partes(["p0", "p1", "p2", "p3", "p4"], None, threading.Event(), quantas_juntas=2)
    assert len(comecaram) < 5  # nao ficou pedindo as que faltavam depois do erro
    cancelar = threading.Event()
    cancelar.set()
    with pytest.raises(claude_local.Cancelado):
        claude_local.pedir_partes(["a", "b"], None, cancelar, quantas_juntas=2)


# ------------------------------------------------------------------ episodio: trechos ao mesmo tempo
def test_episodio_renderiza_trechos_ao_mesmo_tempo(tmp_path, monkeypatch):
    import threading
    import time
    from fractions import Fraction

    from videos_longos import editar_episodio as ep

    rodando, maximo, trava, feitos = [0], [0], threading.Lock(), []

    def falso(ffmpeg, video, q, n, fps, base, cod, prog=None, fade_in=0.0, fade_out=0.0):
        with trava:
            rodando[0] += 1
            maximo[0] = max(maximo[0], rodando[0])
        prog.mostrar(n / fps / 2)  # o ffmpeg avisa o andamento do trecho
        time.sleep(0.03)
        with trava:
            rodando[0] -= 1
            feitos.append(base.name)
        return 0

    monkeypatch.setattr(ep, "render_parte", falso)
    monkeypatch.setitem(ep.CFG, "episodio_partes_simultaneas", 2)
    partes = [(k * 100, 50, 0.0, 0.0) for k in range(6)]
    prog = ep.Progresso(6 * 2.0, "")
    bases = ep.render_lista("ffmpeg", tmp_path / "v.mp4", partes, Fraction(25), tmp_path, "x264", prog)
    assert [b.name for b in bases] == [f"parte_{k:04d}" for k in range(1, 7)]  # na ordem, para juntar certo
    assert maximo[0] == 2 and len(feitos) == 6
    assert abs(prog.feito - 12.0) < 1e-6 and prog.rotulo == "[6/6]"

    def falha_no_3(ffmpeg, video, q, n, fps, base, cod, prog=None, fade_in=0.0, fade_out=0.0):
        return 1 if base.name == "parte_0003" else 0

    monkeypatch.setattr(ep, "render_parte", falha_no_3)
    assert ep.render_lista("ffmpeg", tmp_path / "v.mp4", partes, Fraction(25), tmp_path, "x264",
                           ep.Progresso(12.0, "")) is None  # fmt: skip
    monkeypatch.setitem(ep.CFG, "episodio_partes_simultaneas", "x")
    assert ep.partes_simultaneas() == 2


# ------------------------------------------------------------------ Shorts: legenda do proximo enquanto renderiza
def test_gerar_prepara_a_proxima_legenda_enquanto_renderiza(tmp_path, monkeypatch, capsys):
    import threading
    import time

    from shorts import gerar_shorts as gs

    eventos, trava, rodando = [], threading.Lock(), [0]
    cortes = [{"inicio": 10 * k, "fim": 10 * k + 6, "titulo": f"C{k}"} for k in range(1, 4)]
    cortes.append({"inicio": 100, "fim": 90, "titulo": "invalido"})  # fim antes do inicio: nao vira Short
    proj = {"pasta": tmp_path, "video": tmp_path / "v.mp4", "cortes": cortes, "projeto": {}, "segmentos": [],
            "correcoes": {}}  # fmt: skip
    monkeypatch.setattr(gs, "escolher_projeto", lambda: tmp_path)
    monkeypatch.setattr(gs, "carregar_projeto", lambda pasta: proj)
    monkeypatch.setattr(gs, "preparar_ferramentas", lambda p: {"dur_video": 0, "cod": "x264"})
    monkeypatch.setattr(gs.biblioteca, "preparar_pastas", lambda: None)
    monkeypatch.setattr(gs.biblioteca, "planejar_musicas", lambda *a: {})
    monkeypatch.setattr(gs, "edicao_do_corte", lambda *a, **k: None)
    publicados = []
    monkeypatch.setattr(gs, "salvar_publicacao", lambda pasta, saida, itens, projeto: publicados.extend(itens))

    def legenda(proj, ferr, c, m):
        with trava:
            eventos.append(("legenda", m["n"], rodando[0]))
        return [], None

    def render(proj, ferr, c, m, blocos, t_final, destino, ed):
        with trava:
            rodando[0] += 1
            assert rodando[0] == 1  # nunca dois ffmpeg ao mesmo tempo
        time.sleep(0.1)
        with trava:
            rodando[0] -= 1
            eventos.append(("render", m["n"], 0))
        return m["n"] != 2  # o Short 2 "falha"

    monkeypatch.setattr(gs, "legendas_do_corte", legenda)
    monkeypatch.setattr(gs, "renderizar_corte", render)
    monkeypatch.setattr(gs.sys, "argv", ["gerar_shorts"])
    gs.main()
    saida = capsys.readouterr().out
    assert "2 criado(s), 0 ja existia(m), 2 com erro" in saida  # 1 e 3 prontos; 2 falhou; o invalido deu erro
    assert ("legenda", 2, 1) in eventos and ("legenda", 3, 1) in eventos  # preparou enquanto o anterior renderizava
    assert [e[1] for e in eventos if e[0] == "render"] == [1, 2, 3]  # renderiza na ordem
    assert [n for n, *_ in publicados] == [1, 2, 3]  # o corte invalido nao entra nos textos para postar
    # desligado no config: um de cada vez, como antes
    eventos.clear()
    monkeypatch.setitem(gs.CFG, "shorts_preparar_enquanto_renderiza", False)
    gs.main()
    assert all(e[2] == 0 for e in eventos if e[0] == "legenda")
