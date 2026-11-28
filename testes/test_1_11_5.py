# Testes da 1.11.5: o Short pronto tem no maximo 1 minuto (gancho + corte + final). Passou = acelera ate 1,25x.
import pytest

CFG = {"duracao_final": 3.5, "usar_abertura": True, "transicao": "fade", "duracao_transicao": 0.45}


def test_limites_do_corte_contam_gancho_e_final():
    from shorts import duracao as tamanho

    ideal, acelerado = tamanho.limites_do_corte(CFG)
    assert ideal == pytest.approx(60 - 3.5 - (5 - 0.45))  # cabe sem acelerar, mesmo com gancho de 5 s
    assert acelerado == pytest.approx(75 - 3.5 - (5 - 0.45))  # 60 s x 1,25 = 75 s de conteudo
    sem_gancho = tamanho.limites_do_corte({**CFG, "usar_abertura": False})
    assert sem_gancho[0] == pytest.approx(56.5)
    # 0 = o limite do YouTube (3 minutos); velocidade 1 = nunca acelera
    assert tamanho.duracao_maxima({"shorts_duracao_maxima": 0}) == 180
    assert tamanho.velocidade_maxima({"shorts_velocidade_maxima": 1}) == 1


def test_velocidade_para_caber():
    from shorts import duracao as tamanho

    assert tamanho.velocidade_para_caber(55, CFG) == 1.0  # ja cabe
    k = tamanho.velocidade_para_caber(66, CFG)
    assert 66 / k <= 60 and k == pytest.approx(1.1, abs=0.001)
    assert tamanho.velocidade_para_caber(90, CFG) == 1.25  # nao passa da velocidade maxima
    assert tamanho.velocidade_para_caber(66, {**CFG, "shorts_velocidade_maxima": 1}) == 1.0


def test_claude_nao_pode_mandar_corte_que_nao_cabe():
    from shorts import cortes_com_claude as cc

    validar = cc.validador(3600, CFG)
    assert validar({"cortes": [{"inicio": "00:01:00", "fim": "00:01:50"}]}) == []  # 50 s
    assert validar({"cortes": [{"inicio": "00:01:00", "fim": "00:02:05"}]}) == []  # 65 s: cabe acelerado
    erros = validar({"cortes": [{"inicio": "00:01:00", "fim": "00:02:15"}]})  # 75 s + final: nao cabe
    assert len(erros) == 1 and "passa de 60 s" in erros[0]
    # o gancho tambem conta: 70 s sozinho cabe acelerado; com gancho de 5 s, nao
    longo = {"inicio": "00:01:00", "fim": "00:02:10"}
    assert validar({"cortes": [longo]}) == []
    com_gancho = {**longo, "abertura": {"inicio": "00:01:30", "fim": "00:01:35"}}
    assert len(validar({"cortes": [com_gancho]})) == 1


def test_pedido_fala_do_tamanho():
    from shorts.pedido_cortes import pedido_automatico, texto_pedido

    texto = pedido_automatico("live", CFG, [], "", "[00:00:00-00:00:05] oi")
    assert "MÁXIMO 60 segundos" in texto and "de 15 a 51 segundos" in texto and "até 1,25x" in texto
    assert "3 minutos" not in texto
    assert "MÁXIMO 60 segundos" in texto_pedido("live", "pasta", "diretrizes.txt", CFG)


def test_short_acelerado_no_ffmpeg(tmp_path):
    from shorts.montagem import montar_comando

    args = ("ffmpeg", tmp_path / "v.mp4", 1920, 1080, 0, 66, None, 3.5, None, 69.5, tmp_path / "s.mp4")
    normal = montar_comando(*args)
    assert "setpts=PTS/" not in normal[normal.index("-filter_complex") + 1] and "[v]" in normal
    rapido = montar_comando(*args, velocidade=1.1583)
    filtros = rapido[rapido.index("-filter_complex") + 1]
    assert "[v]setpts=PTS/1.1583[vrapido]" in filtros and "[a]atempo=1.1583[arapido]" in filtros
    assert rapido[rapido.index("-map") + 1] == "[vrapido]"
    assert float(rapido[rapido.index("-t", rapido.index("-filter_complex")) + 1]) == pytest.approx(60, abs=0.01)


def test_medir_corte_acelera_o_que_passa(monkeypatch):
    from shorts import gerar_shorts

    monkeypatch.setattr(gerar_shorts, "CFG", {**gerar_shorts.CFG, **CFG, "shorts_duracao_maxima": 60})
    m = gerar_shorts.medir_corte({"inicio": "00:01:00", "fim": "00:02:00", "titulo": "x"}, 1, 3600)
    assert m["total"] == pytest.approx(63.5) and m["velocidade"] > 1 and m["total_final"] <= 60
    curto = gerar_shorts.medir_corte({"inicio": "00:01:00", "fim": "00:01:40", "titulo": "x"}, 1, 3600)
    assert curto["velocidade"] == 1.0 and curto["total_final"] == pytest.approx(43.5)
