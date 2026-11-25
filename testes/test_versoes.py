# Testes das VERSOES da edicao do video longo (vem depois da 1.10.0): Padrao, Enxuto, Bem enxuto, Melhores momentos
# e Resumao, montadas na hora com os sinais ja medidos; e da escolha dos melhores momentos (autoedit/
# melhores_momentos.py: o Claude da nota a cada momento e o Studio escolhe pelo tempo que voce quer).
import json


def test_melhores_momentos_escolhe_pelas_notas_com_contexto():
    from autoedit import melhores_momentos as mm

    momentos = [{"inicio": 100, "fim": 160, "nota": 9, "titulo": "a"},  # 60 s
                {"inicio": 1000, "fim": 1090, "nota": 4, "titulo": "b"},  # nota baixa: fica de fora
                {"inicio": 2000, "fim": 2100, "nota": 10, "titulo": "c"},  # 100 s
                {"inicio": 2105, "fim": 2150, "nota": 7, "titulo": "d"}]  # fmt: skip
    ficam = mm.escolher(momentos, alvo=200, duracao=3600)
    # c (10), a (9) e d (7) entram; d estava a 5 s de c: viram um so; b (4) nao cabe mais
    assert ficam == [(98.0, 161.5), (1998.0, 2151.5)]
    cortes = mm.cortes_fora(ficam, 3600)
    assert [(c["inicio"], c["fim"]) for c in cortes] == [(0.0, 98.0), (161.5, 1998.0), (2151.5, 3600.0)]
    assert all(c["motivo"] == "fora_melhores" and c["acao"] == "cortar" for c in cortes)
    # a introducao (protegida) entra sempre
    assert mm.escolher(momentos, 100, 3600, protegidos=[(10, 40)])[0] == (10, 40)
    assert mm.alvo_automatico(9 * 3600) == 9 * 3600 * 0.08  # 9 h -> ~43 min
    assert mm.alvo_automatico(60 * 60) == 10 * 60  # live curta: no minimo 10 min


def test_resposta_do_claude_e_sem_claude():
    from autoedit import melhores_momentos as mm

    assert mm.validar({"momentos": [{"inicio": "00:01:00", "fim": "00:00:30"}]})  # fim antes do inicio
    assert not mm.validar({"momentos": [{"inicio": "00:01:00", "fim": "00:02:00", "nota": 8}]})
    juntos = mm.juntar_respostas([{"momentos": [{"inicio": "00:10:00", "fim": "00:11:00", "nota": 12}]},
                                  {"momentos": [{"inicio": "00:01:00", "fim": "00:02:00", "nota": "7"}]}])  # fmt: skip
    assert [(m["inicio"], m["nota"]) for m in juntos] == [(60.0, 7.0), (600.0, 10.0)]  # em ordem; nota ate 10
    # sem o Claude: onde mais se fala ganha nota maior
    sinais = mm.pelos_sinais([(5, 50), (65, 70)], 180)
    assert sinais[0]["nota"] == 10 and sinais[1]["nota"] < sinais[0]["nota"] and len(sinais) == 2


def test_versoes_com_duracao(tmp_path, monkeypatch):
    from autoedit import analisar, versoes

    def decidir(pasta, versao, duracao, linha=None, papo=None):  # Padrao corta 1 silencio; as mais rigidas, mais
        n = {"padrao": 1, "enxuto": 2, "bem_enxuto": 3}[versao]
        return [{"inicio": 100 * k, "fim": 100 * k + 50, "acao": "cortar", "motivo": "silencio", "origem": "auto"}
                for k in range(1, n + 1)]  # fmt: skip

    monkeypatch.setattr(versoes, "_decidir", decidir)
    linhas = []  # a linha do tempo e montada UMA vez so para todas as versoes (nao rele os arquivos grandes)
    monkeypatch.setattr(analisar, "carregar_sinais", lambda *a, **k: {"fala": {}})
    monkeypatch.setattr(analisar, "linha_do_tempo", lambda *a, **k: linhas.append(1) or "linha")
    r = versoes.todas(tmp_path, 3600.0)
    assert r["padrao"][1] == 3550 and r["enxuto"][1] == 3500 and r["bem_enxuto"][1] == 3450
    assert r["melhores"] == (None, None)  # o Claude ainda nao escolheu os momentos
    assert linhas == [1]
    (tmp_path / "analise").mkdir()
    momentos = [{"inicio": 90, "fim": 400, "nota": 9}, {"inicio": 2000, "fim": 2200, "nota": 8},
                {"inicio": 3000, "fim": 3500, "nota": 7}]  # 500 s: maior que 60% do alvo (10 min): nao entra
    (tmp_path / "analise" / "melhores.json").write_text(json.dumps({"momentos": momentos}), encoding="utf-8")
    r = versoes.todas(tmp_path, 3600.0)
    sug, dur = r["melhores"]
    # ficam os 2 momentos (com folga de contexto), menos os silencios do Padrao que caem dentro deles (100-150)
    assert abs(dur - ((401.5 - 88) + (2201.5 - 1998) - 50)) < 0.01, dur
    assert any(s["motivo"] == "fora_melhores" for s in sug) and any(s["motivo"] == "silencio" for s in sug)
    assert r["resumao"][1] <= 15 * 60 * 1.15  # "~15 min": no maximo 15% a mais


def test_trocar_de_versao_mantem_os_cortes_a_mao():
    from autoedit import predefinicoes
    from editor.estado import EstadoEditor

    trechos = [{"inicio": 10, "fim": 20, "acao": "cortar", "motivo": "silencio", "origem": "auto", "revisado": True},
               {"inicio": 30, "fim": 35, "acao": "cortar", "motivo": "manual", "origem": "manual"}]  # fmt: skip
    e = EstadoEditor("longo", 100.0, predefinicoes.da("longo"), trechos)
    e.trocar_versao("melhores", [{"inicio": 50, "fim": 100, "acao": "cortar", "motivo": "fora_melhores"}])
    assert [(t["inicio"], t["origem"]) for t in e.trechos] == [(30, "manual"), (50, "auto")]
    assert e.para_dict()["versao_edicao"] == "melhores"
    assert e.desfazer() and len(e.trechos) == 2 and e.trechos[0]["inicio"] == 10  # Ctrl+Z volta
