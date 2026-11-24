# Testes do caminho "Juntar videos" -> "Transcrever": depois de juntar as partes da live, a janela de escolher
# o video do Transcrever abre na pasta onde o video juntado foi salvo (com o nome dele ja escrito).


def test_transcrever_abre_na_pasta_do_ultimo_video_juntado(tmp_path, monkeypatch):
    from nucleo import comum, transcrever

    anotacao = tmp_path / "ultimo_video_juntado.txt"
    monkeypatch.setattr(comum, "ARQ_ULTIMO_JUNTADO", anotacao)
    monkeypatch.setattr(transcrever, "PASTA_SHORTS", tmp_path / "shorts")
    padrao = transcrever.pasta_inicial()

    # nada juntado ainda: abre na pasta de videos (ou de shorts) de sempre, sem nome escrito
    assert padrao[1] == ""

    # o "Juntar" anotou um video (o PowerShell grava em UTF-8): abre na pasta dele, com o nome ja escrito
    pasta_das_partes = tmp_path / "partes da live"
    pasta_das_partes.mkdir()
    video = pasta_das_partes / "Live de sábado - completo.mp4"
    video.write_bytes(b"x")
    anotacao.write_text(str(video), encoding="utf-8")
    assert comum.ultimo_video_juntado() == video
    assert transcrever.pasta_inicial() == (pasta_das_partes, video.name)

    # depois de transcrito, volta para a pasta de sempre
    projeto = tmp_path / "shorts" / comum.nome_seguro(video.stem)
    projeto.mkdir(parents=True)
    (projeto / "transcricao.json").write_text("{}", encoding="utf-8")
    assert transcrever.pasta_inicial() == padrao

    # o video sumiu do PC: ignora a anotacao
    video.unlink()
    assert comum.ultimo_video_juntado() is None
