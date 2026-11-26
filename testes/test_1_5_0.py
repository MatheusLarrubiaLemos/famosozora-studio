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
    assert "NÃO tente enviar nenhum arquivo" in pedido and "Ctrl+A" in pedido  # limite de ~10 MB do Chrome
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
    pastas = []
    monkeypatch.setattr(claude_pc, "abrir_pasta_dos_videos", lambda itens: pastas.append(len(itens)))
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
    assert pastas == [1]  # so no Cowork o Studio abre a pasta (no Claude Code, ele mesmo abre na hora certa)
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
    k = cmd.index("C:/claude.exe")
    assert "pedido.txt" in cmd[k + 1]  # o pedido logo depois do claude (antes de qualquer opcao)
    # o --add-dir engolia tudo o que vinha depois dele: agora fica no fim, so com a pasta publicar
    assert cmd[-2] == "--add-dir" and cmd[-1] == str(claude_pc.PASTA_PUBLICAR)
    # 1.11.3: o Claude pode abrir a pasta dos videos sem pedir licenca (e so o explorer.exe)
    assert cmd[cmd.index("--allowedTools") + 1] == "Bash(explorer.exe:*)"


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


# ------------------------------------------------------------------ Fase 5: pedir ao Claude com um clique
import threading  # noqa: E402


def _claude_falso(tmp_path, resposta: dict, espera: float = 0, codigo: int = 0):
    """Um 'claude' de mentira (script Python) que le o pedido e devolve um JSON como o 'claude -p'."""
    import os
    import sys

    script = tmp_path / "claude_falso.py"
    script.write_text(
        "import sys, time, json\n"
        "pedido = sys.stdin.read()\n"
        f"time.sleep({espera})\n"
        f"print(json.dumps({resposta!r}))\n"
        f"sys.exit({codigo})\n",
        encoding="utf-8",
    )
    if os.name == "nt":
        return [sys.executable, str(script)]
    exe = tmp_path / "claude"
    exe.write_text(f"#!{sys.executable}\nimport runpy\nrunpy.run_path({str(script)!r}, run_name='__main__')\n")
    exe.chmod(0o755)
    return str(exe)


def test_rodar_claude_de_verdade_com_um_programa_falso(tmp_path, monkeypatch):
    import os

    from nucleo import claude_local
    from publicacao import claude_pc

    if os.name == "nt":
        pytest.skip("o 'claude' falso deste teste e um script de Linux")
    exe = _claude_falso(tmp_path, {"type": "result", "subtype": "success", "is_error": False, "result": '{"ok": 1}'})
    monkeypatch.setattr(claude_pc, "achar_claude_code", lambda: exe)
    assert claude_local.rodar_claude("oi", threading.Event()) == '{"ok": 1}'
    # o Claude avisou erro
    exe = _claude_falso(tmp_path, {"type": "result", "subtype": "error_during_execution", "is_error": True,
                                   "result": "sem rede"})  # fmt: skip
    monkeypatch.setattr(claude_pc, "achar_claude_code", lambda: exe)
    with pytest.raises(claude_local.ErroClaude, match="sem rede"):
        claude_local.rodar_claude("oi", threading.Event())
    # Cancelar fecha o programa na hora
    exe = _claude_falso(tmp_path, {"result": "{}"}, espera=30)
    monkeypatch.setattr(claude_pc, "achar_claude_code", lambda: exe)
    cancelar = threading.Event()
    threading.Timer(0.5, cancelar.set).start()
    with pytest.raises(claude_local.Cancelado):
        claude_local.rodar_claude("oi", cancelar)


def test_tenta_de_novo_ate_3_vezes(monkeypatch):
    from nucleo import claude_local

    monkeypatch.setattr(claude_local, "ESPERA_ENTRE_TENTATIVAS", (0, 0))
    chamadas = []

    def falha_duas(pedido, cancelar, modelo=""):
        chamadas.append(1)
        if len(chamadas) < 3:
            raise claude_local.ErroClaude("rede caiu")
        return "deu"

    avisos = []
    monkeypatch.setattr(claude_local, "rodar_claude", falha_duas)
    assert claude_local.com_tentativas("x", threading.Event(), avisos.append) == "deu" and len(chamadas) == 3
    assert "3 de 3" in avisos[-1]
    chamadas.clear()
    monkeypatch.setattr(claude_local, "rodar_claude", lambda *a, **k: (_ for _ in ()).throw(
        claude_local.ErroClaude("rede caiu")))  # fmt: skip
    with pytest.raises(claude_local.ErroClaude, match="Tentei 3 vezes"):
        claude_local.com_tentativas("x", threading.Event())


def test_json_quebrado_pede_de_novo_uma_vez(monkeypatch):
    from nucleo import claude_local

    respostas = ['aqui vai: {"cortes": [', '```json\n{"cortes": []}\n```']
    pedidos = []
    monkeypatch.setattr(claude_local, "com_tentativas", lambda p, *a, **k: (pedidos.append(p), respostas.pop(0))[1])
    dados = claude_local.pedir_json("PEDIDO", lambda d: [] if isinstance(d.get("cortes"), list) else ["x"],
                                    threading.Event())  # fmt: skip
    assert dados == {"cortes": []} and "ATENÇÃO" in pedidos[1]
    respostas[:] = ["{ruim", "{ruim de novo"]
    with pytest.raises(claude_local.ErroClaude, match="duas vezes"):
        claude_local.pedir_json("P", lambda d: [], threading.Event())


def test_dividir_transcricao_em_partes():
    from nucleo.claude_local import dividir_transcricao, intervalo_da_parte

    texto = "VIDEO: live.mp4\nDURACAO: 03:00:00\nFormato: [inicio-fim] fala\n\n" + "\n".join(
        f"[00:{k:02d}:00-00:{k:02d}:30] fala numero {k}" for k in range(60))  # fmt: skip
    partes = dividir_transcricao(texto, 600)
    assert len(partes) > 2 and all(p.startswith("VIDEO: live.mp4") for p in partes)
    assert sum(p.count("fala numero") for p in partes) == 60  # nenhuma fala perdida nem repetida
    assert intervalo_da_parte(partes[0])[0] == "00:00:00"
    assert dividir_transcricao(texto, 10**6) == [texto.strip()]


def test_cortes_do_claude_validar_e_juntar_partes(tmp_path, monkeypatch):
    import json

    from nucleo import claude_local
    from shorts import cortes_com_claude as cc

    validar = cc.validador(600)
    assert validar({"cortes": [{"inicio": "00:01:00", "fim": "00:01:40"}]}) == []
    erros = validar({"cortes": [{"inicio": "00:02:00", "fim": "00:01:00"}, {"inicio": "00:00:00", "fim": "00:05:00"},
                                {"inicio": "00:09:50", "fim": "00:10:30"}, {"fim": 3}]})  # fmt: skip
    assert len(erros) == 4 and "3 minutos" in erros[1]
    # duas partes, com um corte repetido na emenda: fica o de nota maior
    juntos = cc.juntar([{"cortes": [{"inicio": 10, "fim": 40, "nota": 5}, {"inicio": 100, "fim": 130, "nota": 6}]},
                        {"cortes": [{"inicio": 105, "fim": 135, "nota": 9}], "correcoes": {"a": "b"}}])  # fmt: skip
    assert [c["nota"] for c in juntos["cortes"]] == [5, 9] and juntos["correcoes"] == {"a": "b"}
    # gerar_cortes de ponta a ponta (com o Claude falso), em 2 partes
    (tmp_path / "transcricao_para_claude.txt").write_text(
        "VIDEO: x\n\n" + "\n".join(f"[00:0{k}:00-00:0{k}:30] fala {k}" for k in range(8)), encoding="utf-8"
    )
    (tmp_path / "projeto.json").write_text(json.dumps({"duracao": 600}))
    pedidos = []

    def falso(pedido, validar, cancelar, avisar=None, modelo=""):
        pedidos.append(pedido)
        k = int(pedido.split("PARTE ")[1].split(" ")[0])  # (as partes vem ao mesmo tempo: o numero vem do pedido)
        return {"cortes": [{"inicio": f"00:0{k}:00", "fim": f"00:0{k}:30"}]}

    monkeypatch.setattr(claude_local, "pedir_json", falso)
    dados = cc.gerar_cortes(tmp_path, "live", {"claude_limite_caracteres": 80}, [], tmp_path / "nao_tem.md",
                            threading.Event())  # fmt: skip
    # (as partes vao ao mesmo tempo: a ordem em que chegam ao Claude pode variar)
    assert len(pedidos) > 1 and any("PARTE 1 de" in p for p in pedidos) and len(dados["cortes"]) == len(pedidos)
    (tmp_path / "cortes.json").write_text("{}")
    cc.salvar_cortes(tmp_path, dados)
    assert (tmp_path / "cortes_anterior.json").read_text() == "{}"
    assert json.loads((tmp_path / "cortes.json").read_text())["versao"] == 3


def test_edicao_longa_formato_novo_e_migracao(tmp_path):
    import json

    from videos_longos.pedido_edicao import ler_edicao, migrar_arquivo, para_disco, para_interno

    antigo = {"cortes": [{"inicio": "00:00:00", "fim": "00:01:00", "motivo": "menu"}],
              "abertura": {"inicio": "00:10:00", "fim": "00:10:20"},
              "capitulos": [{"inicio": "00:01:00", "titulo": "A"}], "titulo": "T"}  # fmt: skip
    (tmp_path / "edicao.json").write_text(json.dumps(antigo))
    assert migrar_arquivo(tmp_path)
    novo = json.loads((tmp_path / "edicao.json").read_text())
    assert novo["versao"] == 3 and novo["remover"][0]["motivo"] == "menu" and "abertura" not in novo
    assert novo["capitulos"] == [{"tempo": "00:01:00", "titulo": "A"}]
    assert json.loads((tmp_path / "edicao.bak.json").read_text()) == antigo  # copia de seguranca
    assert not migrar_arquivo(tmp_path)  # ja esta na versao atual (3 desde a 1.9.0)
    dados, erros, _ = ler_edicao(tmp_path, 3600)
    assert not erros and dados["cortes"][0]["fim"] == "00:01:00" and "abertura" not in dados
    assert para_interno(para_disco(dados))["cortes"] == dados["cortes"]


def test_edicao_com_claude_em_partes_pede_o_resumo(tmp_path, monkeypatch):
    from nucleo import claude_local
    from videos_longos import edicao_com_claude as ec

    (tmp_path / "transcricao_para_claude.txt").write_text(
        "VIDEO: x\n\n" + "\n".join(f"[00:{k:02d}:00-00:{k:02d}:30] fala {k}" for k in range(0, 40, 5))
    )
    monkeypatch.setattr(ec, "info_video", lambda pasta: (tmp_path / "v.mp4", 3600.0))
    pedidos = []

    def falso(pedido, validar, cancelar, avisar=None, modelo=""):
        pedidos.append(pedido)
        if "Escreva o título" in pedido:
            return {"titulo": "Episódio inteiro", "tags": ["a"]}
        k = int(pedido.split("PARTE ")[1].split(" ")[0])  # (as partes vem ao mesmo tempo: o numero vem do pedido)
        return {"remover": [{"inicio": f"00:{k * 5:02d}:00", "fim": f"00:{k * 5:02d}:40", "motivo": "parado"}],
                "capitulos": [{"tempo": f"00:{k * 5 + 1:02d}:00", "titulo": f"Cap {k}"}], "titulo": f"parte {k}"}  # fmt: skip

    monkeypatch.setattr(claude_local, "pedir_json", falso)
    dados, avisos = ec.editar_longo(tmp_path, "live", {"claude_limite_caracteres": 90}, tmp_path / "x.md",
                                    threading.Event())  # fmt: skip
    partes = len(pedidos) - 1
    assert partes > 1 and dados["titulo"] == "Episódio inteiro"
    assert len(dados["cortes"]) == partes and len(dados["capitulos"]) == partes
    assert "SEM GANCHO" in pedidos[0] and "A intro" in pedidos[0]


# ------------------------------------------------------------------ Fase 6: video longo (outro, emendas, publicar)
def test_outro_pasta_vazia_duracao_e_comando(tmp_path, monkeypatch):
    from fractions import Fraction

    from nucleo import comum
    from videos_longos import outro

    monkeypatch.setattr(comum, "PASTA_OUTRO", tmp_path / "outro")
    arq, info, texto, ok = outro.situacao(True)
    assert arq is None and not ok and "vazia" in texto
    assert outro.situacao(False)[2].startswith("Sem outro")
    (tmp_path / "outro").mkdir()
    (tmp_path / "outro" / "LEIA-ME.txt").write_text("x")
    (tmp_path / "outro" / "b.mp4").write_bytes(b"x")
    (tmp_path / "outro" / "a.mov").write_bytes(b"x")
    assert outro.achar_outro().name == "a.mov"  # o primeiro em ordem alfabetica, so videos
    # qualquer duracao serve (o aviso de "5 a 20 s" saiu: a tela final do YouTube cabe num outro longo)
    assert outro.avisos_do_outro({"duracao": 3.0}) == outro.avisos_do_outro({"duracao": 29.0}) == []
    assert outro.avisos_do_outro(None)  # so avisa se nao deu para abrir o video do outro
    info = {"duracao": 6.0, "largura": 640, "altura": 360, "fps": Fraction(25), "tem_audio": False}
    cmd, quadros, segundos = outro.comando_com_outro("ffmpeg", tmp_path / "v.mp4", 10.0, 300, Fraction(30), tmp_path /
                                                     "o.mp4", info, 1920, 1080, ["-c:v", "libx264"], tmp_path / "p")  # fmt: skip
    filtro = cmd[cmd.index("-filter_complex") + 1]
    assert "xfade=transition=fade" in filtro and "acrossfade" in filtro and "anullsrc" in filtro
    assert "scale=1920:1080" in filtro and "fps=30/1" in filtro
    assert quadros == 300 + 180 - 18 and abs(segundos - quadros / 30) < 1e-6


def test_emendas_com_transicao_e_sem_gancho(monkeypatch):
    from fractions import Fraction

    from videos_longos import editar_episodio as ee

    monkeypatch.setitem(ee.CFG, "episodio_fade_emenda", 0.2)
    plano = {"fps": Fraction(30), "trechos": [(0, 300), (450, 300), (900, 3)], "abertura": None}
    partes = ee.partes_do_plano(plano)
    assert partes[0][2] == 0.0 and partes[0][3] == 0.2  # comeca do comeco, sem fade de entrada
    assert partes[1][2] == 0.2 and partes[1][3] == 0.2  # emenda: some e aparece
    assert partes[2][2:4] == (0.0, 0.0)  # trecho curtinho: sem fade (nao pisca)
    monkeypatch.setitem(ee.CFG, "episodio_fade_emenda", 0)
    assert all(p[2] == p[3] == 0 for p in ee.partes_do_plano(plano))


def test_rascunho_do_video_longo_com_capitulos(fila_temp, tmp_path):
    import json

    from publicacao import rascunhos

    pasta = tmp_path / "live"
    (pasta / "episodio").mkdir(parents=True)
    info = {"pasta": pasta, "nome": "live"}
    assert rascunhos.rascunho_longo(info) is None  # ainda sem episodio
    (pasta / "episodio" / "Ep 4.mp4").write_bytes(b"x")
    caps = [{"inicio": 0, "titulo": "Começo", "titulo_en": "Start"}, {"inicio": 75, "titulo": "Missão"},
            {"inicio": 3725, "titulo": "Final"}]  # fmt: skip
    (pasta / "episodio" / "episodio.json").write_text(json.dumps({"arquivo": "Ep 4.mp4", "capitulos": caps}))
    (pasta / "edicao.json").write_text(json.dumps({"versao": 2, "remover": [], "titulo": "Bully ep 4",
                                                   "descricao": "Zerando.", "tags": "bully, rpg"}))  # fmt: skip
    r = rascunhos.rascunho_longo(info)
    assert r["tipo"] == "longo" and r["titulo"] == "Bully ep 4" and r["tags"] == ["bully", "rpg"]
    assert r["descricao"] == "Zerando.\n\n0:00 Começo\n1:15 Missão\n1:02:05 Final"


# ------------------------------------------------------------------ 1.5.1: legenda adiantada e titulo
def test_palavra_esticada_pelo_whisper_nao_aparece_no_silencio():
    from shorts.legendas import encurtar_esticadas

    # "agora" foi falada perto de 15 s, mas o Whisper marcou o comeco em 11.2 (logo depois da fala anterior)
    p = encurtar_esticadas([{"i": 10.0, "f": 10.4, "p": "Oi"}, {"i": 11.2, "f": 15.0, "p": "agora"},
                            {"i": 15.0, "f": 15.3, "p": "vai"}])  # fmt: skip
    assert p[0] == {"i": 10.0, "f": 10.4, "p": "Oi"} and p[2]["i"] == 15.0  # palavras normais nao mudam
    assert 14.0 < p[1]["i"] < 15.0 and p[1]["f"] == 15.0


def test_palavra_que_o_claude_acrescentou_cola_na_fala_seguinte():
    from shorts.legendas import alinhar

    brutas = [
        {"i": 10.0, "f": 10.4, "p": "Oi"},
        {"i": 18.0, "f": 18.4, "p": "vamos"},
        {"i": 18.5, "f": 19.0, "p": "jogar"},
    ]
    p = alinhar(brutas, "Oi. Então vamos jogar")
    entao = next(w for w in p if w["p"] == "Então")
    assert entao["i"] >= 17.5  # antes ia para 10.4 (7 segundos de antecedencia)
    # sem silencio, continua repartindo o espaco que existe
    brutas[1]["i"], brutas[1]["f"] = 10.9, 11.2
    p = alinhar(brutas, "Oi. Então vamos jogar")
    assert 10.4 <= next(w for w in p if w["p"] == "Então")["i"] < 10.9


def test_trecho_reescrito_nao_cobre_a_pausa():
    from shorts.legendas import alinhar

    brutas = [{"i": 9.0, "f": 9.4, "p": "mano"}, {"i": 9.5, "f": 10.0, "p": "olha"},
              {"i": 10.0, "f": 10.5, "p": "eu"}, {"i": 10.5, "f": 11.0, "p": "abre"},  # ... 5 s de silencio ...
              {"i": 16.0, "f": 16.5, "p": "porta"}, {"i": 16.5, "f": 17.0, "p": "ja"},
              {"i": 17.0, "f": 17.4, "p": "era"}, {"i": 17.5, "f": 18.0, "p": "velho"}]  # fmt: skip
    p = alinhar(brutas, "mano olha nós abrimos aquela portona era velho")
    assert [w["p"] for w in p] == ["mano", "olha", "nós", "abrimos", "aquela", "portona", "era", "velho"]
    for w in p:
        assert not (11.0 < w["i"] < 16.0), w  # nenhuma palavra comeca dentro do silencio
    assert p[2]["i"] == 10.0 and p[5]["f"] <= 17.0 + 0.001


@pytest.mark.parametrize("titulo,esperado", [
    ("Explodi a bike - Bully ep 4", "Explodi a bike"),
    ("Explodi a bike | BULLY EP 4", "Explodi a bike"),
    ("Explodi a bike (Bully ép 4)", "Explodi a bike"),
    ("Explodi a bike #bullyep4", "Explodi a bike"),
    ("Explodi a bike no Bully ep 4", "Explodi a bike no Bully ep 4"),  # faz parte da frase: fica
    ("Bully ep 4", "Bully ep 4"),  # o titulo e so o nome: fica
    ("Explodi a bike", "Explodi a bike"),
])  # fmt: skip
def test_titulo_sem_o_nome_do_video_no_final(titulo, esperado):
    from shorts.cortes import limpar_titulos, sem_nome_do_video

    assert sem_nome_do_video(titulo, "Bully ep 4") == esperado
    cortes = [{"titulo": titulo, "youtube_titulo": titulo}]
    assert limpar_titulos(cortes, "Bully ep 4") == (2 if titulo != esperado else 0)


def test_pedido_de_cortes_proibe_o_nome_do_video_no_titulo():
    from pathlib import Path

    from shorts.pedido_cortes import pedido_automatico, texto_pedido

    for pedido in (pedido_automatico("Live X", {}, [], "", "[00:00:00-00:00:05] oi"),
                   texto_pedido("Live X", Path("p"), Path("d.md"), {})):  # fmt: skip
        assert "NÃO coloque o nome do vídeo" in pedido and "cite o episódio" not in pedido
