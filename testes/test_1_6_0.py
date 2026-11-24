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


# ================================================================== lote
import json  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402

import pytest  # noqa: E402

from shorts import lote as L  # noqa: E402


@pytest.fixture(autouse=True)
def _sem_lote_no_fim():
    """Cada teste comeca e termina sem lote.json (e sem a pasta configuracoes, se ela ficou vazia)."""
    yield
    for arq in (L.arquivo(), L.arquivo().with_name("lote.bak.json")):
        arq.unlink(missing_ok=True)
    try:
        L.arquivo().parent.rmdir()
    except OSError:
        pass


def _projeto(raiz, nome, transcrito=False, cortes=None, shorts=0):
    p = raiz / nome
    (p / "prontos").mkdir(parents=True, exist_ok=True)
    (p / "projeto.json").write_text(json.dumps({"video": str(p / "video.mp4"), "duracao": 60}), encoding="utf-8")
    if transcrito:
        (p / "transcricao.json").write_text('{"segmentos": []}', encoding="utf-8")
        (p / "transcricao_para_claude.txt").write_text("[00:00-00:10] oi", encoding="utf-8")
    if cortes is not None:
        lista = [{"inicio": f"00:00:{10 * k:02d}", "fim": f"00:00:{10 * k + 8:02d}", "titulo": f"C{k}"}
                 for k in range(cortes)]  # fmt: skip
        (p / "cortes.json").write_text(json.dumps({"versao": 3, "cortes": lista}), encoding="utf-8")
    for k in range(shorts):
        (p / "prontos" / f"{k + 1:02d} - antigo.mp4").write_bytes(b"velho")
    return {"nome": nome, "pasta": p, "n_shorts": shorts}


class EtapasFalsas:
    """Faz de conta: transcrever escreve a transcricao, o "Claude" devolve 2 cortes e renderizar cria os mp4."""

    def __init__(self, erro_em=(), ao_renderizar=None):
        self.erro_em, self.ao_renderizar, self.feito = set(erro_em), ao_renderizar, []

    def transcrever(self, v, cancelar, progresso):
        self.feito.append(("transcrever", v["nome"]))
        p = L.Path(v["pasta"])
        progresso(0.5, "metade")
        (p / "transcricao.json").write_text('{"segmentos": []}', encoding="utf-8")
        (p / "transcricao_para_claude.txt").write_text("[00:00-00:10] oi", encoding="utf-8")

    def pedir_cortes(self, v, cancelar, progresso):
        self.feito.append(("cortes", v["nome"]))
        if v["nome"] in self.erro_em:
            raise L.ErroLote("O Claude não conseguiu escolher os cortes: sem internet")
        resposta = {"versao": 3, "cortes": [{"inicio": "00:00:01", "fim": "00:00:09", "titulo": "A"},
                                           {"inicio": "00:00:11", "fim": "00:00:19", "titulo": "B"}]}  # fmt: skip
        (L.Path(v["pasta"]) / "cortes.json").write_text(json.dumps(resposta), encoding="utf-8")

    def renderizar(self, v, cancelar, progresso):
        self.feito.append(("renderizar", v["nome"]))
        p = L.Path(v["pasta"])
        if self.ao_renderizar:
            self.ao_renderizar(v, cancelar)
        for k in range(L.n_cortes(p)):
            destino = p / "prontos" / f"{k + 1:02d} - novo.mp4"
            if not destino.exists():  # igual ao gerar_shorts: pula o que ja existe
                destino.write_bytes(b"novo")
        return 0


def test_montar_lote_na_ordem_e_pular_ou_gerar_de_novo(tmp_path):
    a = _projeto(tmp_path, "a")
    b = _projeto(tmp_path, "b", transcrito=True, cortes=2, shorts=2)
    c = _projeto(tmp_path, "c", transcrito=True, cortes=2, shorts=2)
    lote = L.montar_lote([c, a, b], refazer={"c": True})
    assert [v["nome"] for v in lote["videos"]] == ["c", "a", "b"]
    assert [v["etapa"] for v in lote["videos"]] == ["fila", "fila", "pulado"]
    assert lote["videos"][0]["refazer"] and not lote["videos"][1]["refazer"]
    assert lote["versao"] == L.VERSAO_LOTE


def test_rodar_lote_cada_video_no_seu_projeto(tmp_path, monkeypatch):
    from nucleo import limpeza

    lixeira = []
    monkeypatch.setattr(limpeza, "mandar_para_lixeira", lambda c: (lixeira.extend(c), [f.unlink() for f in c], True)[2])
    a = _projeto(tmp_path, "a")  # nao transcrito
    b = _projeto(tmp_path, "b", transcrito=True)  # sem cortes
    c = _projeto(tmp_path, "c", transcrito=True, cortes=3, shorts=1)  # ja tem Shorts: gerar de novo
    d = _projeto(tmp_path, "d", transcrito=True, cortes=2, shorts=2)  # ja tem Shorts: pular
    etapas = EtapasFalsas()
    lote = L.montar_lote([a, b, c, d], refazer={"c": True})
    L.RodarLote(lote, etapas).rodar_aqui()
    # as duas linhas se misturam, mas cada video segue a sua ordem e as linhas seguem a ordem do lote
    assert sorted(etapas.feito) == sorted([("transcrever", "a"), ("cortes", "a"), ("renderizar", "a"),
                                           ("cortes", "b"), ("renderizar", "b"), ("renderizar", "c")])  # fmt: skip
    pos = {passo: k for k, passo in enumerate(etapas.feito)}
    assert pos[("transcrever", "a")] < pos[("cortes", "a")] < pos[("renderizar", "a")]
    assert pos[("cortes", "a")] < pos[("cortes", "b")] < pos[("renderizar", "b")]
    assert pos[("renderizar", "a")] < pos[("renderizar", "b")] < pos[("renderizar", "c")]
    assert [v["etapa"] for v in lote["videos"]] == ["pronto", "pronto", "pronto", "pulado"]
    assert [v["n_shorts"] for v in lote["videos"]] == [2, 2, 3, 2]
    # cada projeto ficou com os seus arquivos: nada se misturou
    for info in (a, b, c):
        assert (info["pasta"] / "cortes.json").exists()
        assert all(f.parent == info["pasta"] / "prontos" for f in L.shorts_prontos(info["pasta"]))
    assert [f.name for f in lixeira] == ["01 - antigo.mp4"]  # "gerar de novo": os antigos foram para a Lixeira
    assert sorted(f.name for f in L.shorts_prontos(d["pasta"])) == ["01 - antigo.mp4", "02 - antigo.mp4"]
    assert lote["situacao"] == "terminado" and L.progresso_geral(lote) == 1.0
    assert L.texto_notificacao(lote) == "Lote pronto: 7 Shorts de 3 vídeos"
    salvo = json.loads(L.arquivo().read_text(encoding="utf-8"))
    assert salvo["situacao"] == "terminado" and not L.retomavel(salvo)


def test_video_com_erro_e_pulado_e_tentar_de_novo(tmp_path):
    a = _projeto(tmp_path, "a", transcrito=True)
    b = _projeto(tmp_path, "b", transcrito=True)
    etapas = EtapasFalsas(erro_em={"a"})
    lote = L.montar_lote([a, b])
    L.RodarLote(lote, etapas).rodar_aqui()
    assert [v["etapa"] for v in lote["videos"]] == ["erro", "pronto"]
    assert "sem internet" in lote["videos"][0]["erro"]
    assert [v["nome"] for v in L.resumo(lote)["erros"]] == ["a"]
    assert L.texto_notificacao(lote) == "Lote pronto: 2 Shorts de 1 vídeo (1 com erro)"
    # "Tentar de novo so este": so o video com erro roda de novo
    etapas.erro_em.clear()
    etapas.feito.clear()
    L.tentar_de_novo(lote, "a")
    L.RodarLote(lote, etapas).rodar_aqui()
    assert etapas.feito == [("cortes", "a"), ("renderizar", "a")]
    assert [v["etapa"] for v in lote["videos"]] == ["pronto", "pronto"]


def test_cancelar_no_meio_nao_deixa_arquivo_quebrado(tmp_path):
    a = _projeto(tmp_path, "a", transcrito=True, cortes=2)
    b = _projeto(tmp_path, "b", transcrito=True, cortes=2)
    rodar = None

    def no_meio(v, cancelar):  # o primeiro Short fica pronto, o segundo estava sendo gerado quando cancelou
        (L.Path(v["pasta"]) / "prontos" / "01 - novo.mp4").write_bytes(b"novo")
        (L.Path(v["pasta"]) / "prontos" / "_gerando_02.mp4").write_bytes(b"pela metade")
        (L.Path(v["pasta"]) / "temp_legenda_02.ass").write_text("x")
        rodar.cancelar()
        raise L.Cancelado()

    lote = L.montar_lote([a, b])
    rodar = L.RodarLote(lote, EtapasFalsas(ao_renderizar=no_meio))
    rodar.rodar_aqui()
    assert lote["situacao"] == "cancelado"
    assert [v["etapa"] for v in lote["videos"]] == ["fila", "fila"]
    assert not list(a["pasta"].rglob("_gerando_*")) and not list(a["pasta"].glob("temp_legenda_*"))
    assert [f.name for f in L.shorts_prontos(a["pasta"])] == ["01 - novo.mp4"]  # o que ficou pronto, fica
    assert not L.retomavel(L.carregar())  # cancelado de proposito: nao pergunta "continuar?" ao abrir


def test_salvar_e_retomar_depois_de_fechar_o_app(tmp_path):
    a = _projeto(tmp_path, "a", transcrito=True, cortes=2)
    b = _projeto(tmp_path, "b", transcrito=True, cortes=2)
    lote = L.montar_lote([a, b])
    # o app fechou com o video "a" renderizando (sobrou um temporario) e o "b" na fila
    lote["situacao"] = "rodando"
    lote["videos"][0]["etapa"] = "renderizando"
    (a["pasta"] / "prontos" / "01 - novo.mp4").write_bytes(b"novo")
    (a["pasta"] / "prontos" / "_gerando_02.mp4").write_bytes(b"pela metade")
    L.salvar(lote)
    salvo = L.carregar()
    assert L.retomavel(salvo)
    etapas = EtapasFalsas()
    L.RodarLote(salvo, etapas).rodar_aqui()
    assert [v["etapa"] for v in salvo["videos"]] == ["pronto", "pronto"]
    assert not list(a["pasta"].rglob("_gerando_*"))
    assert (a["pasta"] / "prontos" / "01 - novo.mp4").read_bytes() == b"novo"  # nao refez o que estava pronto


def test_nao_deixa_dois_lotes_ao_mesmo_tempo(tmp_path):
    a = _projeto(tmp_path, "a", transcrito=True, cortes=1)
    liberar = threading.Event()

    def segurar(v, cancelar):
        liberar.wait(5)

    primeiro = L.RodarLote(L.montar_lote([a]), EtapasFalsas(ao_renderizar=segurar), gravar=False)
    assert primeiro.iniciar()
    segundo = L.RodarLote(L.montar_lote([a]), EtapasFalsas(), gravar=False)
    assert not segundo.iniciar()
    with pytest.raises(RuntimeError):
        segundo.rodar_aqui()
    liberar.set()
    assert primeiro.terminou.wait(5)
    terceiro = L.RodarLote(L.montar_lote([a]), EtapasFalsas(), gravar=False)
    assert terceiro.iniciar() and terceiro.terminou.wait(5)


def test_pausar_espera_e_continuar_segue(tmp_path):
    a = _projeto(tmp_path, "a", transcrito=True, cortes=1)
    b = _projeto(tmp_path, "b", transcrito=True, cortes=1)
    rodar = L.RodarLote(L.montar_lote([a, b]), EtapasFalsas(), gravar=False)
    rodar.pausar()
    assert rodar.iniciar()
    time.sleep(0.5)
    assert rodar.retrato()["situacao"] == "pausado" and not rodar.terminou.is_set()
    assert [v["etapa"] for v in rodar.retrato()["videos"]] == ["fila", "fila"]
    rodar.continuar()
    assert rodar.terminou.wait(5)
    assert [v["etapa"] for v in rodar.retrato()["videos"]] == ["pronto", "pronto"]


def test_video_sem_corte_bom_fica_pronto_com_aviso(tmp_path):
    a = _projeto(tmp_path, "a", transcrito=True, cortes=0)
    lote = L.montar_lote([a])
    L.RodarLote(lote, EtapasFalsas(), gravar=False).rodar_aqui()
    assert lote["videos"][0]["etapa"] == "pronto" and lote["videos"][0]["n_shorts"] == 0
    assert "nenhum corte" in lote["videos"][0]["avisos"][0]


def test_migracao_do_lote_antigo_com_backup(tmp_path):
    antigo = {"videos": [{"nome": "a", "pasta": str(tmp_path / "a"), "etapa": "cortando"},
                         {"pasta": str(tmp_path / "b"), "etapa": "inventada"}], "situacao": "rodando"}  # fmt: skip
    L.arquivo().parent.mkdir(parents=True, exist_ok=True)
    L.arquivo().write_text(json.dumps(antigo), encoding="utf-8")
    novo = L.carregar()
    assert novo["versao"] == L.VERSAO_LOTE
    assert [v["nome"] for v in novo["videos"]] == ["a", "b"]
    assert [v["etapa"] for v in novo["videos"]] == ["cortando", "fila"]
    bak = L.arquivo().with_name("lote.bak.json")
    assert json.loads(bak.read_text(encoding="utf-8")) == antigo
    assert json.loads(L.arquivo().read_text(encoding="utf-8"))["versao"] == L.VERSAO_LOTE
    L.arquivo().unlink()
    bak.unlink()


def test_cancelar_processo_de_verdade_para_na_hora():
    cancelar = threading.Event()
    threading.Timer(0.5, cancelar.set).start()
    inicio = time.monotonic()
    with pytest.raises(L.Cancelado):
        L.rodar_processo(["timeit", "-n", "1", "-r", "1", "import time; time.sleep(30)"], cancelar)
    assert time.monotonic() - inicio < 10


def test_processo_le_a_saida_e_o_codigo():
    linhas = []
    codigo, ultimas = L.rodar_processo(["json.tool", "--help"], threading.Event(), linhas.append)
    assert codigo == 0 and linhas and ultimas[-1] == linhas[-1]


def test_tempo_estimado():
    lote = {"segundos": 600, "videos": [{"etapa": "pronto"}, {"etapa": "fila", "progresso": 0.0}]}
    assert L.progresso_geral(lote) == 0.5
    assert L.tempo_restante(lote) == 600
    assert L.texto_tempo(600) == "10 min" and L.texto_tempo(3900) == "1 h 05 min"
    assert L.texto_tempo(None) == "calculando..." and L.texto_tempo(20) == "menos de 1 minuto"


def test_fechar_o_app_no_meio_deixa_o_lote_para_continuar(tmp_path):
    a = _projeto(tmp_path, "a", transcrito=True, cortes=1)
    b = _projeto(tmp_path, "b", transcrito=True, cortes=1)
    comecou = threading.Event()

    def demorado(v, cancelar):  # renderizando ate o app fechar
        (L.Path(v["pasta"]) / "prontos" / "_gerando_01.mp4").write_bytes(b"pela metade")
        comecou.set()
        cancelar.wait(5)
        raise L.Cancelado()

    rodar = L.RodarLote(L.montar_lote([a, b]), EtapasFalsas(ao_renderizar=demorado))
    assert rodar.iniciar() and comecou.wait(5)
    rodar.parar_para_fechar()
    assert rodar.terminou.is_set()
    salvo = L.carregar()
    assert salvo["situacao"] == "rodando" and L.retomavel(salvo)
    assert [v["etapa"] for v in salvo["videos"]] == ["fila", "fila"]
    assert not list(a["pasta"].rglob("_gerando_*"))
    L.arquivo().unlink()


def test_erros_tecnicos_viram_portugues_simples():
    assert "sem internet" in L.explicar_erro("403 Forbidden")
    assert "memória" in L.explicar_erro("CUDA failed: out of memory")
    assert "disco" in L.explicar_erro("[Errno 28] No space left on device")
    assert L.explicar_erro("Nao achei o video original") == "Nao achei o video original"
    assert L._primeiro_erro(["ok", "[ERRO] 403 Forbidden"]).startswith("Não consegui baixar o modelo")


def test_transcrever_aceita_varios_videos_na_janela(tmp_path, monkeypatch):
    """O botao "1 Transcrever video novo" abre uma janela que aceita escolher varios videos de uma vez."""
    from nucleo import transcrever

    videos = [tmp_path / "a.mp4", tmp_path / "b.mp4", tmp_path / "c.mp4"]
    for v in videos:
        v.write_bytes(b"x")
    monkeypatch.setattr(transcrever.sys, "argv", ["transcrever"])
    monkeypatch.setattr(transcrever, "escolher_arquivos", lambda titulo, pasta, arquivo="": videos + [tmp_path / "sumiu.mp4"])
    assert transcrever.escolher_videos() == videos


def test_relogio_anda_mesmo_sem_noticia_da_etapa(tmp_path):
    """O Claude passa minutos sem dar noticia: o tempo do lote e do video tem que andar sozinho."""
    a = _projeto(tmp_path, "a", transcrito=True)
    liberar = threading.Event()

    class ClaudeDemorado(EtapasFalsas):
        def pedir_cortes(self, v, cancelar, progresso):
            liberar.wait(5)  # "pensando", sem chamar progresso()
            super().pedir_cortes(v, cancelar, progresso)

    rodar = L.RodarLote(L.montar_lote([a]), ClaudeDemorado(), gravar=False)
    assert rodar.iniciar()
    time.sleep(2.5)
    agora = rodar.retrato()
    assert agora["videos"][0]["etapa"] == "cortando"
    assert agora["segundos"] >= 1.5 and agora["videos"][0]["segundos"] >= 1.5
    liberar.set()
    assert rodar.terminou.wait(5)
    fim = rodar.retrato()
    assert fim["videos"][0]["etapa"] == "pronto"
    assert abs(fim["segundos"] - fim["videos"][0]["segundos"]) < 0.5  # o tempo do video nao foi contado 2 vezes


def test_duas_linhas_claude_do_proximo_enquanto_renderiza(tmp_path):
    """Enquanto o video "a" renderiza, o Claude ja escolhe os cortes do "b" (o PC nao fica parado)."""
    a = _projeto(tmp_path, "a", transcrito=True, cortes=1)
    b = _projeto(tmp_path, "b", transcrito=True)
    claude_do_b = threading.Event()
    vistos = []

    def renderizando_a(v, cancelar):
        if v["nome"] == "a":
            vistos.append(claude_do_b.wait(5))  # so termina de renderizar o "a" depois que o Claude do "b" rodou

    class Etapas(EtapasFalsas):
        def pedir_cortes(self, v, cancelar, progresso):
            super().pedir_cortes(v, cancelar, progresso)
            if v["nome"] == "b":
                claude_do_b.set()

    lote = L.montar_lote([a, b])
    L.RodarLote(lote, Etapas(ao_renderizar=renderizando_a), gravar=False).rodar_aqui()
    assert vistos == [True]
    assert [v["etapa"] for v in lote["videos"]] == ["pronto", "pronto"]


def test_cancelar_com_as_duas_linhas_rodando(tmp_path):
    """Cancelar com um video renderizando e outro no Claude: os dois param e voltam para a fila."""
    a = _projeto(tmp_path, "a", transcrito=True, cortes=1)
    b = _projeto(tmp_path, "b", transcrito=True)
    c = _projeto(tmp_path, "c", transcrito=True)
    no_claude = threading.Event()
    rodar = None

    class Etapas(EtapasFalsas):
        def pedir_cortes(self, v, cancelar, progresso):
            no_claude.set()
            cancelar.wait(5)
            raise L.Cancelado()

    def renderizando(v, cancelar):
        no_claude.wait(5)
        rodar.cancelar()
        raise L.Cancelado()

    lote = L.montar_lote([a, b, c])
    rodar = L.RodarLote(lote, Etapas(ao_renderizar=renderizando), gravar=False)
    rodar.rodar_aqui()
    assert lote["situacao"] == "cancelado"
    assert [v["etapa"] for v in lote["videos"]] == ["fila", "fila", "fila"]
    assert not (b["pasta"] / "cortes.json").exists()


# ================================================================== legenda fora do tempo em Short longo (1.6.2)
def _falas(n, inicio=100.0, passo=1.0, escorrega=0.0):
    """n palavras, uma por segundo; escorrega = quanto cada palavra vai se atrasando (o Whisper "se perdendo")."""
    return [{"i": round(inicio + k * passo + k * escorrega, 3), "f": round(inicio + k * passo + k * escorrega + 0.5, 3),
             "p": f"palavra{k % 7}x{k}"} for k in range(n)]  # fmt: skip


def test_retranscricao_que_escorrega_nao_combina():
    from shorts.legendas import combina_com_a_original

    originais = _falas(130)  # Short de ~2 minutos
    assert combina_com_a_original(_falas(130), originais)
    assert combina_com_a_original([dict(w, i=w["i"] + 0.3) for w in originais], originais)  # diferenca pequena: ok
    assert not combina_com_a_original(_falas(130, escorrega=0.05), originais)  # no fim ja esta 6 s atrasada
    assert not combina_com_a_original([{"i": 1, "f": 2, "p": "outra"}] * 50, originais)  # nada bate
    assert combina_com_a_original(_falas(3), _falas(3))  # pouca fala: nao da para comparar, aceita


class _ModeloFalso:
    """Whisper falso: devolve palavras com o tempo que o teste quiser e guarda as opcoes usadas."""

    def __init__(self, palavras):
        self.palavras, self.opcoes = palavras, None

    def transcribe(self, audio, **op):
        from types import SimpleNamespace

        self.opcoes = op
        words = [SimpleNamespace(start=w["i"], end=w["f"], word=w["p"]) for w in self.palavras]
        return [SimpleNamespace(words=words)], None


def test_retranscritor_usa_o_filtro_de_silencio_e_descarta_tempos_errados(tmp_path, monkeypatch):
    from shorts import legendas

    originais = _falas(130)
    relativas = [dict(w, i=w["i"] - 100, f=w["f"] - 100) for w in _falas(130, escorrega=0.05)]
    modelo = _ModeloFalso(relativas)
    monkeypatch.setitem(legendas.CFG, "retranscrever_cortes", "true")
    monkeypatch.setattr(legendas, "carregar_whisper", lambda *a, **k: (modelo, "cuda"))
    monkeypatch.setattr(legendas, "extrair_audio", lambda *a, **k: [0.0])
    r = legendas.Retranscritor(tmp_path)
    assert r.palavras(tmp_path / "v.mp4", 100.0, 230.0, originais) == []  # escorregou: fica a original
    assert modelo.opcoes["vad_filter"] is True and modelo.opcoes["condition_on_previous_text"] is False
    cache = json.loads((tmp_path / "retranscricao_cache.json").read_text(encoding="utf-8"))
    assert cache["versao"] == legendas.VERSAO_CACHE and cache["trechos"]["100.00-230.00"] == []
    # com os tempos certos, a retranscricao vale
    modelo.palavras = [dict(w, i=w["i"] - 100, f=w["f"] - 100) for w in originais]
    novas = r.palavras(tmp_path / "v.mp4", 300.0, 430.0, [dict(w, i=w["i"] + 200, f=w["f"] + 200) for w in originais])
    assert len(novas) == 130 and novas[0]["i"] == 300.0


def test_cache_antigo_da_retranscricao_e_refeito_com_backup(tmp_path, monkeypatch):
    from shorts import legendas

    antigo = {"10.00-20.00": [{"i": 50.0, "f": 51.0, "p": "errado"}]}  # formato antigo (versao 1, sem numero)
    (tmp_path / "retranscricao_cache.json").write_text(json.dumps(antigo), encoding="utf-8")
    monkeypatch.setitem(legendas.CFG, "retranscrever_cortes", "false")
    r = legendas.Retranscritor(tmp_path)
    assert r.cache == {} and r.palavras(tmp_path / "v.mp4", 10.0, 20.0) is None  # nao reaproveita o antigo
    assert json.loads((tmp_path / "retranscricao_cache.bak.json").read_text(encoding="utf-8")) == antigo
