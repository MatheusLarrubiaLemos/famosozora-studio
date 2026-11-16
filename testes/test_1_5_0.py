# Testes da versao 1.5.0 (rapidos, sem abrir janelas): editor de legendas (inserir, excluir e mudar o tempo
# de uma linha), Short descartado, Lixeira.
import pytest

from shorts import revisao
from shorts.cortes import descartar_corte, escolhidos, ler_cortes


def _palavras():
    # duas linhas: "Oi tudo bem." (10 a 11.5) e "Vamos jogar" (13 a 14)
    return [{"i": 10.0, "f": 10.4, "p": "Oi"}, {"i": 10.5, "f": 11.0, "p": "tudo"}, {"i": 11.1, "f": 11.5, "p": "bem."},
            {"i": 13.0, "f": 13.4, "p": "Vamos"}, {"i": 13.5, "f": 14.0, "p": "jogar"}]  # fmt: skip


def test_mudar_tempo_da_linha_mantem_a_proporcao():
    p = _palavras()
    linhas = revisao.dividir_em_linhas(p)
    novas = revisao.mudar_tempo_da_linha(p, linhas[0], 9.0, 12.0)
    assert novas[0]["i"] == 9.0 and novas[2]["f"] == 12.0
    assert novas[0]["f"] < novas[1]["i"]  # a ordem das palavras continua
    assert novas[3] == p[3]  # a outra linha nao muda


@pytest.mark.parametrize("ini,fim", [(9.0, 13.5), (11.0, 11.05)])
def test_mudar_tempo_invalido(ini, fim):
    p = _palavras()
    with pytest.raises(ValueError):
        revisao.mudar_tempo_da_linha(p, revisao.dividir_em_linhas(p)[0], ini, fim)


def test_inserir_linha_no_espaco_e_sem_espaco():
    p = _palavras()
    linhas = revisao.dividir_em_linhas(p)
    novas, pos = revisao.inserir_linha_depois(p, linhas[0], "nova")
    assert pos == 3 and novas[3]["p"] == "nova" and 11.5 <= novas[3]["i"] < novas[3]["f"] <= 13.0
    assert len(revisao.dividir_em_linhas(novas)) == 3  # virou uma linha separada
    # sem espaco: a linha de baixo comeca logo depois -> encolhe a de cima
    p2 = [dict(w) for w in p]
    p2[3]["i"] = 11.55
    novas2, pos2 = revisao.inserir_linha_depois(p2, revisao.dividir_em_linhas(p2)[0], "x")
    assert novas2[pos2 - 1]["f"] <= novas2[pos2]["i"] < novas2[pos2]["f"] <= 11.5 + 0.001
    # editar o texto da linha nova (com outra quantidade de palavras) nao junta com a de cima
    linhas3 = revisao.dividir_em_linhas(novas)
    trocadas = revisao.trocar_texto_da_linha(novas, linhas3[1], "duas palavras")
    assert len(revisao.dividir_em_linhas(trocadas)) == 3


def test_excluir_linha():
    p = _palavras()
    linhas = revisao.dividir_em_linhas(p)
    assert [w["p"] for w in revisao.excluir_linha(p, linhas[0])] == ["Vamos", "jogar"]
    with pytest.raises(ValueError):
        revisao.excluir_linha(p[:3], [0, 1, 2])  # a unica linha


def test_short_descartado_nao_volta(tmp_path):
    import json

    (tmp_path / "cortes.json").write_text(json.dumps({"versao": 3, "cortes": [{"inicio": 1, "fim": 2},
                                                                              {"inicio": 3, "fim": 4}]}))  # fmt: skip
    assert descartar_corte(tmp_path, 1)
    cortes = ler_cortes(tmp_path)["cortes"]
    assert escolhidos(cortes, None) == {2}
    assert descartar_corte(tmp_path, 1, descartar=False)
    assert escolhidos(ler_cortes(tmp_path)["cortes"], None) == {1, 2}
    assert not descartar_corte(tmp_path, 9)


def test_excluir_short_vai_para_a_lixeira(tmp_path, monkeypatch):
    import json

    from nucleo import limpeza

    lixeira = []
    monkeypatch.setattr(limpeza, "mandar_para_lixeira", lambda c: (lixeira.extend(c), True)[1])
    (tmp_path / "prontos").mkdir()
    (tmp_path / "prontos" / "01 - Um.mp4").write_bytes(b"x")
    (tmp_path / "prontos" / "publicacao.json").write_text(json.dumps({"shorts": [{"n": 1, "arquivo": "01 - Um.mp4"},
                                                                                 {"n": 2, "arquivo": "02.mp4"}]}))  # fmt: skip
    (tmp_path / "cortes.json").write_text(json.dumps({"versao": 3, "cortes": [{"inicio": 1, "fim": 2},
                                                                              {"inicio": 3, "fim": 4}]}))  # fmt: skip
    limpeza.excluir_short(tmp_path, 1, "01 - Um.mp4")
    assert lixeira == [tmp_path / "prontos" / "01 - Um.mp4"]
    pub = json.loads((tmp_path / "prontos" / "publicacao.json").read_text())
    assert [s["n"] for s in pub["shorts"]] == [2]
    assert ler_cortes(tmp_path)["cortes"][0]["descartado"] is True


def test_lixeira_nunca_apaga_de_vez(tmp_path, monkeypatch):
    """Sem conseguir mandar para a Lixeira, o arquivo FICA (nada e apagado de vez)."""
    import send2trash

    from nucleo import limpeza

    arq = tmp_path / "a.mp4"
    arq.write_bytes(b"x")

    def falha(c):
        raise OSError("sem lixeira")

    monkeypatch.setattr(send2trash, "send2trash", falha)
    assert limpeza.mandar_para_lixeira([arq]) is False
    assert arq.exists()


# ------------------------------------------------------------------ Fase 4: excluir pelo app
def _projeto_para_excluir(tmp_path):
    import json

    video = tmp_path / "videos" / "live.mp4"
    video.parent.mkdir()
    video.write_bytes(b"v" * 1000)
    p = tmp_path / "shorts" / "live"
    (p / "prontos" / "antigos").mkdir(parents=True)
    (p / "episodio").mkdir()
    (p / "prontos" / "01 - Um.mp4").write_bytes(b"x" * 300)
    (p / "prontos" / "publicacao.json").write_text("{}")
    (p / "episodio" / "live - episodio.mp4").write_bytes(b"x" * 500)
    (p / "episodio" / "textos.txt").write_text("t")
    (p / "projeto.json").write_text(json.dumps({"video": str(video)}))
    (p / "transcricao.json").write_text("{}")
    return p, video


def test_o_que_cada_opcao_de_excluir_manda_para_a_lixeira(tmp_path):
    from nucleo.limpeza import itens_para_excluir, tamanho_dos_itens

    p, video = _projeto_para_excluir(tmp_path)
    shorts = itens_para_excluir(p, "shorts")
    assert sorted(f.name for f in shorts) == ["01 - Um.mp4", "antigos"]  # o publicacao.json fica
    assert [f.name for f in itens_para_excluir(p, "episodio")] == ["live - episodio.mp4"]  # os textos ficam
    assert itens_para_excluir(p, "projeto") == [p]  # o video original fica
    assert itens_para_excluir(p, "tudo") == [p, video]
    assert tamanho_dos_itens(itens_para_excluir(p, "tudo")) >= 1800
    with pytest.raises(ValueError):
        itens_para_excluir(p, "outra")


def test_excluir_projeto_usa_a_lixeira_e_avisa_se_falhar(tmp_path, monkeypatch):
    from nucleo import limpeza

    p, video = _projeto_para_excluir(tmp_path)
    lixeira = []
    monkeypatch.setattr(limpeza, "mandar_para_lixeira", lambda c: (lixeira.extend(c), True)[1])
    assert limpeza.excluir_projeto(p, "tudo") >= 1800
    assert lixeira == [p, video]
    monkeypatch.setattr(limpeza, "mandar_para_lixeira", lambda c: False)
    with pytest.raises(OSError, match="Lixeira"):
        limpeza.excluir_projeto(p, "projeto")


# ------------------------------------------------------------------ Fase 1: publicacao
from datetime import datetime, timedelta  # noqa: E402

from publicacao.horario import BRASILIA  # noqa: E402


def _br(texto):
    return datetime.fromisoformat(texto).replace(tzinfo=BRASILIA)


@pytest.mark.parametrize("agora,ocupados,esperado", [
    ("2026-11-16T09:00", [], "2026-11-16T12:00"),  # nada agendado, de manha: hoje ao meio-dia
    ("2026-11-16T11:30", [], "2026-11-17T12:00"),  # menos de 1 hora para o meio-dia: amanha
    ("2026-11-16T15:00", [], "2026-11-17T12:00"),  # depois do meio-dia: amanha
    ("2026-11-16T09:00", ["2026-11-16T12:00", "2026-11-17T12:00"], "2026-11-18T12:00"),
    ("2026-11-16T09:00", ["2026-11-20T12:00"], "2026-11-21T12:00"),  # depois do ULTIMO agendado
    ("2026-11-16T09:00", ["2026-11-10T12:00"], "2026-11-16T12:00"),  # agendamento antigo nao conta
    ("2026-12-31T15:00", ["2026-12-31T12:00"], "2027-01-01T12:00"),  # virada de ano
])  # fmt: skip
def test_proximo_dia_livre_ao_meio_dia_de_brasilia(agora, ocupados, esperado):
    from publicacao.horario import proximo_dia_livre

    r = proximo_dia_livre([_br(o) for o in ocupados], "12:00", _br(agora))
    assert r == _br(esperado) and r.utcoffset() == timedelta(hours=-3)


def test_varios_shorts_um_por_dia_e_textos_de_data():
    from publicacao.horario import ler_caixa, para_caixa, proximos_dias_livres, sugestao_longo, texto_horario

    dias = proximos_dias_livres([_br("2026-11-17T12:00")], 3, "12:00", _br("2026-11-16T09:00"))
    assert [d.day for d in dias] == [18, 19, 20]
    assert texto_horario(dias[0]) == "qua 18/11 às 12:00"
    assert ler_caixa(para_caixa(dias[0])) == dias[0]
    assert ler_caixa("18/11/26 às 9:05").hour == 9
    with pytest.raises(ValueError, match="não é uma data"):
        ler_caixa("amanhã")
    assert sugestao_longo({"publicar_longo_hora": "19:30"}, _br("2026-11-16T09:00")) == _br("2026-11-17T19:30")


@pytest.fixture
def fila_temp(tmp_path, monkeypatch):
    from publicacao import claude_pc, fila, pacote

    monkeypatch.setattr(fila, "PASTA_FILA", tmp_path / "configuracoes")
    monkeypatch.setattr(pacote, "PASTA_PUBLICAR", tmp_path / "publicar")
    monkeypatch.setattr(claude_pc, "PASTA_PUBLICAR", tmp_path / "publicar")
    video = tmp_path / "01 - Um.mp4"
    video.write_bytes(b"video falso")
    return fila, video


def test_fila_status_e_retomada_depois_de_fechar_o_app(fila_temp, tmp_path):
    import json

    fila, video = fila_temp
    item = fila.novo_item("short", "proj", video, "Um", _br("2026-11-18T12:00"))
    fila.adicionar([item])
    # "fecha o app": tudo esta no arquivo, e ler de novo traz igual
    assert fila.itens()[0]["status"] == "na fila" and fila.na_fila(video)["id"] == item["id"]
    pacote = tmp_path / "pacote"
    pacote.mkdir()
    fila.atualizar(item["id"], status="enviando", pacote=str(pacote), enviado_em=datetime.now().isoformat())
    assert fila.conferir(_br("2026-11-17T09:00")) == []  # o Claude ainda nao respondeu
    (pacote / "resultado.json").write_text(json.dumps({"status": "agendado", "link": "https://youtu.be/abc"}))
    mudou = fila.conferir(_br("2026-11-17T09:00"))
    assert mudou[0][0]["status"] == "agendado" and fila.pegar(item["id"])["link"] == "https://youtu.be/abc"
    assert [i["id"] for i in fila.proximos()] == [item["id"]]
    assert fila.horarios_de_shorts() == [_br("2026-11-18T12:00")]
    fila.conferir(_br("2026-11-18T12:01"))  # passou do horario: esta no ar
    assert fila.pegar(item["id"])["status"] == "publicado" and fila.proximos() == []
    assert fila.na_fila(video) is None


def test_fila_erro_do_claude_e_sem_resposta(fila_temp, tmp_path):
    import json

    fila, video = fila_temp
    a = fila.novo_item("short", "p", video, "A", _br("2026-11-18T12:00"), status="enviando",
                       enviado_em=(datetime.now() - timedelta(hours=13)).isoformat())  # fmt: skip
    b = fila.novo_item("longo", "p", video, "B", _br("2026-11-19T18:00"), status="enviando",
                       enviado_em=datetime.now().isoformat(), pacote=str(tmp_path))  # fmt: skip
    (tmp_path / "resultado.json").write_text(json.dumps({"status": "erro", "motivo": "login caiu"}))
    fila.adicionar([a, b])
    fila.conferir(_br("2026-11-17T09:00"))
    assert fila.pegar(a["id"])["status"] == "erro" and "não respondeu" in fila.pegar(a["id"])["erro"]
    assert fila.pegar(b["id"])["erro"] == "login caiu"
    assert fila.pendentes_em([video.parent]) == []  # erro nao conta como pendente
    assert fila.remover(a["id"]) and not fila.remover("nao-existe")


def test_fila_migracao_e_arquivo_estragado(fila_temp):
    import json

    fila, video = fila_temp
    arq = fila.arquivo()
    arq.parent.mkdir(parents=True)
    arq.write_text(json.dumps([{"id": "x", "status": "na fila"}]))  # formato sem versao
    assert fila.ler()["versao"] == fila.VERSAO and arq.with_suffix(".bak.json").exists()
    arq.write_text("{ quebrado")
    assert fila.ler()["itens"] == [] and arq.with_suffix(".estragado.json").exists()


def test_pacote_de_postagem_e_pedido(fila_temp):
    from publicacao import fila as _f
    from publicacao.pacote import montar_pacote, problemas_do_item, texto_pedido

    fila, video = fila_temp
    item = _f.novo_item("short", "proj", video, "Explodi a bicicleta", _br("2026-11-18T12:00"),
                        descricao="Vídeo completo: https://x", tags=["bully", "gameplay"], playlist="Bully")  # fmt: skip
    assert problemas_do_item(item) == []
    pasta = montar_pacote(item)
    assert (pasta / video.name).read_bytes() == b"video falso"  # o video esta no pacote (ligado ou copiado)
    dados = (pasta / "dados.txt").read_text(encoding="utf-8")
    for trecho in ("Explodi a bicicleta", "qua 18/11/2026 às 12:00", "bully, gameplay", "Bully", "TIPO: Short"):
        assert trecho in dados
    assert (pasta / "dados.json").exists()
    pedido = texto_pedido([item])
    assert "AGENDAR" in pedido and "resultado.json" in pedido and str(pasta) in pedido and "NUNCA publique" in pedido
    ruim = dict(item, titulo="x" * 101, video="/nao/existe.mp4")
    assert len(problemas_do_item(ruim)) == 2


def test_enviar_para_o_claude_code_e_para_o_cowork(fila_temp, monkeypatch):
    from types import SimpleNamespace

    from nucleo import comum
    from publicacao import claude_pc

    fila, video = fila_temp
    item = fila.novo_item("short", "proj", video, "Um", _br("2026-11-18T12:00"))
    fila.adicionar([item])
    comandos, copiado, navegador = [], [], []
    monkeypatch.setattr(claude_pc, "subprocess", SimpleNamespace(Popen=lambda c, **k: comandos.append(c)))
    monkeypatch.setattr(claude_pc, "webbrowser", SimpleNamespace(open=navegador.append))
    monkeypatch.setattr(claude_pc, "achar_app_claude", lambda: None)
    # automatico com Claude Code instalado: abre o "claude --chrome" com o pedido
    monkeypatch.setattr(claude_pc, "achar_claude_code", lambda: "/bin/claude")
    monkeypatch.setattr(claude_pc, "ler_ajustes", lambda: {"publicar_modo": "auto"})
    claude_pc.preparar([item])
    r = claude_pc.enviar([item], copiar=copiado.append)
    assert r["modo"] == "claude_code" and "--chrome" in comandos[0] and r["pedido"].exists()
    assert fila.pegar(item["id"])["status"] == "enviando"
    # sem Claude Code: Cowork (copia o pedido e abre o Claude)
    monkeypatch.setattr(claude_pc, "achar_claude_code", lambda: None)
    r = claude_pc.enviar([item], copiar=copiado.append)
    assert r["modo"] == "cowork" and "AGENDAR" in copiado[0] and navegador == ["https://claude.ai/new"]
    # escolheu Claude Code mas ele nao esta instalado: erro em portugues
    monkeypatch.setattr(claude_pc, "ler_ajustes", lambda: {"publicar_modo": "claude_code"})
    with pytest.raises(RuntimeError, match="Não achei o Claude Code"):
        claude_pc.enviar([item])
    assert comum  # (so para o import nao sobrar)


def test_comando_do_claude_code_no_windows(monkeypatch, tmp_path):
    from publicacao import claude_pc

    monkeypatch.setattr(claude_pc.os, "name", "nt")
    cmd = claude_pc.comando_claude_code("C:/claude.exe", tmp_path / "pedido.txt")
    assert cmd[:4] == ["cmd", "/c", "start", "Claude - publicando no YouTube"] and "--chrome" in cmd
    assert "pedido.txt" in cmd[-1]


def test_rascunhos_dos_shorts_e_marcar_publicado(fila_temp, tmp_path, monkeypatch):
    import json

    from nucleo import comum
    from publicacao import rascunhos

    fila, _ = fila_temp
    pasta = tmp_path / "shorts" / "proj"
    (pasta / "prontos").mkdir(parents=True)
    shorts = []
    for n in (1, 2, 3):
        (pasta / "prontos" / f"0{n}.mp4").write_bytes(b"x")
        shorts.append({"n": n, "arquivo": f"0{n}.mp4", "postado": {"youtube": n == 3},
                       "textos": {"youtube": {"titulo": f"T{n}", "descricao": "veja {link}", "tags": ["a"]}}})  # fmt: skip
    (pasta / "prontos" / "publicacao.json").write_text(json.dumps({"shorts": shorts}))
    (pasta / "projeto.json").write_text(json.dumps({"link_video_completo": "https://youtu.be/longo"}))
    info = {"pasta": pasta, "nome": "proj"}
    assert rascunhos.shorts_prontos(info) == [1, 2]  # o 3 ja foi publicado
    r = rascunhos.rascunhos_de_shorts(info, [1, 2], ocupados=[_br("2099-01-01T12:00")])
    assert [x["horario"][:10] for x in r] == ["2099-01-02", "2099-01-03"]
    assert r[0]["descricao"] == "veja https://youtu.be/longo" and r[0]["tags"] == ["a"]
    fila.adicionar([r[0]])
    assert rascunhos.shorts_prontos(info) == [2]  # o 1 esta na fila
    monkeypatch.setattr(comum, "PASTA_SHORTS", tmp_path / "shorts")
    rascunhos.marcar_no_projeto(dict(r[0], link="https://youtu.be/s1"))
    pub = json.loads((pasta / "prontos" / "publicacao.json").read_text())
    assert pub["shorts"][0]["postado"]["youtube"] is True and pub["shorts"][0]["link_youtube"] == "https://youtu.be/s1"


def test_short_conta_como_publicado_so_com_as_redes_ativas():
    from nucleo.projetos import redes_ativas

    assert redes_ativas({}) == ["youtube"]
    assert redes_ativas({"redes": ["youtube", "tiktok"]}) == ["youtube", "tiktok"]
    assert redes_ativas({"redes": ["orkut"]}) == ["youtube"]
