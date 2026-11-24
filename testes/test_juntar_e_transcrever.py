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


def test_transcrever_da_aba_longos_ja_analisa_a_live(tmp_path, monkeypatch, capsys):
    """'Transcrever a live' (aba Videos longos) roda com --analisar: depois de transcrever, ja analisa a live, para o
    editor abrir com as sugestoes de corte. Se a analise der erro, a transcricao continua valendo."""
    from autoedit import analisar
    from nucleo import transcrever

    feitos = []
    monkeypatch.setattr(analisar, "analisar_com_andamento", lambda pasta: (feitos.append(pasta), {
        "sugestoes": [{"acao": "cortar", "inicio": 0, "fim": 600}, {"acao": "manter", "inicio": 700, "fim": 800}],
        "avisos": []})[1])  # fmt: skip
    transcrever.analisar_depois(tmp_path)
    assert feitos == [tmp_path] and "1 cortes sugeridos (10 min a menos)" in capsys.readouterr().out

    def quebra(pasta):
        raise RuntimeError("sem placa")

    monkeypatch.setattr(analisar, "analisar_com_andamento", quebra)
    transcrever.analisar_depois(tmp_path)  # nao levanta erro
    assert "A análise não terminou (sem placa)" in capsys.readouterr().out


def test_andamento_da_analise(tmp_path):
    """O editor sabe se a analise esta rodando (em outro processo) pelo analisando.json atualizado ha pouco."""
    import time

    from autoedit import analisar
    from nucleo.comum import gravar_json

    (tmp_path / "analise").mkdir()
    arq = tmp_path / "analise" / analisar.ARQ_ANDAMENTO
    assert analisar.andamento(tmp_path) is None
    gravar_json(arq, {"linha": "[2/7] Som  10.0%", "inicio": time.time(), "atualizado": time.time()})
    assert analisar.andamento(tmp_path)["linha"] == "[2/7] Som  10.0%"
    gravar_json(arq, {"linha": "x", "inicio": 0, "atualizado": time.time() - 120})  # parou (app fechado)
    assert analisar.andamento(tmp_path) is None
