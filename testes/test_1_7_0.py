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
