# Testes da versao 1.6.2: excluir na primeira tentativa (Lixeira tenta de novo sozinha) e o editor de
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
