# Testes da versao 1.9.0: contas do player embutido (o que pular, em que linha esta), corte "exato" marcado no
# player (sem o ajuste para o silencio) e a atualizacao automatica (instalador ja baixado, comando que espera o
# Studio fechar e instala sem telas). As telas com o player de verdade estao no test_telas.py (lento).
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

import pytest

from nucleo import reproducao


# ------------------------------------------------------------------ player: o que fica e o que sai
def test_mantidos_do_plano_em_segundos():
    plano = {"fps": Fraction(10), "trechos": [(0, 100), (300, 50), (500, 0)]}
    assert reproducao.mantidos_do_plano(plano) == [(0.0, 10.0), (30.0, 35.0)]
    assert reproducao.mantidos_do_plano(None) == []


@pytest.mark.parametrize(
    "t, esperado",
    [(5.0, None), (9.99, 30.0), (12.0, 30.0), (30.0, None), (34.0, None), (35.5, 35.0), (40.0, None), (-1, None)],
)  # fmt: skip
def test_pulo_vai_para_o_proximo_pedaco_que_fica(t, esperado):
    mantidos = [(0.0, 10.0), (30.0, 35.0)]
    if t == -1:  # o video comeca com um pedaco que sai: pula para o primeiro que fica
        assert reproducao.pulo(1.0, [(5.0, 10.0)]) == 5.0
        return
    assert reproducao.pulo(t, mantidos) == esperado


def test_pulo_sem_plano_nao_pula():
    assert reproducao.pulo(12.0, []) is None


def test_situacao_diz_se_fica_sai_ou_e_pausa():
    cortes = [{"n": 1, "ini_aj": 10.0, "fim_aj": 20.0, "ativo": True},
              {"n": 2, "ini_aj": 40.0, "fim_aj": 45.0, "ativo": False}]  # fmt: skip
    mantidos = [(0.0, 10.0), (20.0, 25.0), (28.0, 60.0)]
    assert reproducao.situacao(15.0, cortes, mantidos) == ("sai", 1)
    assert reproducao.situacao(26.0, cortes, mantidos) == ("pausa", None)
    assert reproducao.situacao(42.0, cortes, mantidos) == ("fica", None)  # trecho que voce mandou manter


def test_linha_da_legenda_no_tempo():
    inicios, fins = [10.0, 12.0, 20.0], [11.5, 13.5, 21.0]
    assert reproducao.linha_no_tempo(inicios, fins, 9.0) is None
    assert reproducao.linha_no_tempo(inicios, fins, 12.5) == 1
    assert reproducao.linha_no_tempo(inicios, fins, 15.0) == 1  # entre linhas: a ultima que ja comecou
    assert reproducao.dentro_da_linha(inicios, fins, 15.0) is None  # ...mas a legenda nao aparece
    assert reproducao.dentro_da_linha(inicios, fins, 20.5) == 2


def test_relogio_e_limites_do_player():
    assert reproducao.texto_do_tempo(65.43) == "1:05.4"
    assert reproducao.texto_do_tempo(3725.0) == "1:02:05.0"
    assert reproducao.limitar(5.0, 10.0, 20.0) == 10.0
    assert reproducao.limitar(25.0, None, 20.0) == 20.0
    assert reproducao.limitar(-3.0, None, None) == 0.0


# ------------------------------------------------------------------ corte exato (marcado no player)
def test_corte_exato_nao_vai_para_o_silencio():
    from videos_longos.pedido_edicao import montar_plano, normalizar

    palavras = [(0.0, 9.0), (11.0, 30.0), (33.0, 60.0)]  # pausas em 9-11 e 30-33
    cfg = {"episodio_ajuste_silencio": 2.0, "cortar_pausas": False}
    bruto = {"remover": [{"inicio": "00:00:10.50", "fim": "00:00:31.20", "motivo": "a"}], "cortar_pausas": False}
    dados, erros, _ = normalizar(bruto, 60.0)
    assert not erros and "exato" not in dados["cortes"][0]
    auto = montar_plano(dados, 60.0, Fraction(10), palavras, cfg)["cortes"][0]
    assert (auto["ini_aj"], auto["fim_aj"]) != (10.5, 31.2)  # o programa leva as bordas para as pausas
    bruto["remover"][0]["exato"] = True
    dados, erros, _ = normalizar(bruto, 60.0)
    assert dados["cortes"][0]["exato"] is True  # o "exato" e gravado de volta no edicao.json
    exato = montar_plano(dados, 60.0, Fraction(10), palavras, cfg)["cortes"][0]
    assert (exato["ini_aj"], exato["fim_aj"]) == (10.5, 31.2)


def test_corte_exato_juntado_com_um_automatico_deixa_de_ser_exato():
    from videos_longos.pedido_edicao import normalizar

    bruto = {"remover": [{"inicio": "00:00:10", "fim": "00:00:20", "motivo": "a", "exato": True},
                         {"inicio": "00:00:15", "fim": "00:00:25", "motivo": "b"}]}  # fmt: skip
    dados, _, _ = normalizar(bruto, 60.0)
    assert len(dados["cortes"]) == 1 and "exato" not in dados["cortes"][0]


# ------------------------------------------------------------------ atualizacao automatica
def test_comando_de_instalacao_espera_o_studio_e_instala_sem_telas():
    from nucleo.atualizacao import comando_de_instalacao

    pasta = Path("C:/Programas/FamosoZora Studio")
    cmd = comando_de_instalacao(Path("C:/temp/FamosoZora-Studio-Setup-9.9.9.exe"), 4321, reabrir=False,
                                mostrar_progresso=False, pasta_app=pasta)  # fmt: skip
    assert cmd[0] == "powershell.exe" and "Hidden" in cmd
    script = cmd[-1]
    assert "Wait-Process -Id 4321" in script  # espera o Studio fechar
    assert "/VERYSILENT" in script and "/SUPPRESSMSGBOXES" in script and "/REABRIR" not in script
    assert str(pasta / "python") in script  # e as janelas pretas (o Python do app) terminarem
    assert "if (-not (Ocupado))" in script  # ainda ocupado depois da espera: nao instala (tenta na proxima)
    agora = comando_de_instalacao(Path("C:/temp/x.exe"), 1, reabrir=True, mostrar_progresso=True, pasta_app=pasta)
    assert "/SILENT" in agora[-1] and "/VERYSILENT" not in agora[-1] and "/REABRIR=1" in agora[-1]


def test_comando_de_instalacao_com_aspas_no_caminho():
    from nucleo.atualizacao import comando_de_instalacao

    cmd = comando_de_instalacao(Path("C:/Users/d'Avila/temp/setup.exe"), 1, False, False, Path("C:/app"))
    assert "d''Avila" in cmd[-1]  # aspas simples dobradas: o PowerShell le o caminho certo


def test_instalador_ja_baixado_e_limpeza_dos_velhos(monkeypatch, tmp_path):
    from nucleo import atualizacao

    monkeypatch.setattr(atualizacao, "DADOS_APP", tmp_path)
    (tmp_path / "temp").mkdir()
    release = {"nome_instalador": "FamosoZora-Studio-Setup-9.9.9.exe", "tamanho": 3}
    assert atualizacao.instalador_ja_baixado(release) is None
    (tmp_path / "temp" / "FamosoZora-Studio-Setup-9.9.9.exe").write_bytes(b"xy")  # pela metade
    assert atualizacao.instalador_ja_baixado(release) is None
    (tmp_path / "temp" / "FamosoZora-Studio-Setup-9.9.9.exe").write_bytes(b"xyz")
    assert atualizacao.instalador_ja_baixado(release).name == release["nome_instalador"]
    assert atualizacao.baixar_instalador(release) == tmp_path / "temp" / release["nome_instalador"]  # nao baixa de novo
    (tmp_path / "temp" / "FamosoZora-Studio-Setup-1.0.0.exe").write_bytes(b"velho")
    (tmp_path / "temp" / "trecho_que_sai_001.mp4").write_bytes(b"outro arquivo")
    atualizacao.limpar_instaladores_velhos(manter=release["nome_instalador"])
    assert sorted(f.name for f in (tmp_path / "temp").iterdir()) == [
        release["nome_instalador"],
        "trecho_que_sai_001.mp4",
    ]


def test_instalar_ao_fechar_fora_do_windows_nao_faz_nada(monkeypatch, tmp_path):
    from nucleo import atualizacao

    monkeypatch.setattr(atualizacao, "os", SimpleNamespace(name="posix", getpid=lambda: 99))
    (tmp_path / "setup.exe").write_bytes(b"x")
    assert atualizacao.instalar_ao_fechar(tmp_path / "setup.exe") is False


def test_instalar_ao_fechar_no_windows_abre_o_powershell_escondido(monkeypatch, tmp_path):
    from nucleo import atualizacao

    chamados = []
    monkeypatch.setattr(atualizacao, "os", SimpleNamespace(name="nt", getpid=lambda: 99))  # finge que e o Windows
    monkeypatch.setattr(atualizacao.subprocess, "Popen", lambda cmd, **k: chamados.append(cmd))
    (tmp_path / "setup.exe").write_bytes(b"x")
    assert atualizacao.instalar_ao_fechar(tmp_path / "setup.exe", reabrir=True, mostrar_progresso=True)
    assert chamados and chamados[0][0] == "powershell.exe" and "/REABRIR=1" in chamados[0][-1]
    assert not atualizacao.instalar_ao_fechar(tmp_path / "nao_existe.exe")
