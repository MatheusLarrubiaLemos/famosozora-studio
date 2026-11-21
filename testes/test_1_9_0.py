# Testes da 1.9.0: Auto-Edit (analise, regras das predefinicoes, trechos, mapa de tempo), edicao.json versao 3,
# plano do episodio com os cortes do Auto-Edit, Short com cortes dentro dele e exportar para outro editor.
# Os testes marcados "lento" usam o ffmpeg de verdade num video de amostra (testes/amostra_autoedit.py).
import json
from fractions import Fraction

import pytest

# ------------------------------------------------------------------ ajudantes


def regras_longo(**mudar):
    from autoedit import predefinicoes

    r = dict(predefinicoes.FABRICA["longo"], versao=1, tipo="longo")
    r.update(mudar)
    return r


def regras_short(**mudar):
    from autoedit import predefinicoes

    r = dict(predefinicoes.FABRICA["short"], versao=1, tipo="short")
    r.update(mudar)
    return r


def linha_sintetica(duracao=120.0, falas=(), silencio=(), parado=(), preto=(), trocas=(), cenas=()):
    """Linha do tempo de mentira: volume alto e movimento alto, menos nos pedacos pedidos."""
    from autoedit.decidir_cortes import Linha

    n_som = int(duracao * 10)
    volume = [0.6] * n_som
    for a, b in silencio:
        for k in range(int(a * 10), int(b * 10)):
            volume[k] = 0.0
    n_img = int(duracao * 2)
    mov, brilho = [0.05] * n_img, [0.5] * n_img
    for a, b in parado:
        for k in range(int(a * 2), int(b * 2)):
            mov[k] = 0.0
    for a, b in preto:
        for k in range(int(a * 2), int(b * 2)):
            brilho[k] = 0.0
            mov[k] = 0.0
    palavras = []
    for a, b in falas:
        t = a
        while t + 0.3 <= b:
            palavras.append((t, t + 0.3))
            t += 0.4
    som = {"inicio": 0.0, "passo": 0.1, "volume": volume, "fala_vad": None}
    img = {"inicio": 0.0, "passo": 0.5, "movimento": mov, "brilho": brilho, "trocas": list(trocas)}
    return Linha(0.0, duracao, palavras, som, img, list(cenas))


def cortes(sugestoes, acao="cortar"):
    return [(s["inicio"], s["fim"], s["motivo"]) for s in sugestoes if s["acao"] == acao]


# ------------------------------------------------------------------ regras da predefinicao (Fase 2 / Fase 7)


def test_silencio_longo_so_sai_se_tambem_sem_acao():
    from autoedit.decidir_cortes import decidir

    # 10 s de silencio com o jogo mexendo: no Longo (TV) fica (pausa natural durante o jogo)
    linha = linha_sintetica(falas=[(0, 20), (30, 60)], silencio=[(20, 30)])
    assert cortes(decidir(linha, regras_longo())) == []
    # o mesmo silencio com a tela parada: sai
    linha = linha_sintetica(falas=[(0, 20), (30, 60)], silencio=[(20, 30)], parado=[(20, 30)])
    (a, b, motivo), = cortes(decidir(linha, regras_longo()))
    assert motivo == "silencio"
    assert a == pytest.approx(20 + 0.8, abs=0.11)  # margem depois do trecho mantido
    assert b == pytest.approx(30 - 0.4, abs=0.11)  # margem antes do proximo trecho mantido


def test_silencio_curto_nao_sai_e_short_corta_mais():
    from autoedit.decidir_cortes import decidir

    linha = linha_sintetica(falas=[(0, 10), (12, 30)], silencio=[(10, 12)], parado=[(10, 12)])
    assert cortes(decidir(linha, regras_longo())) == []  # 2 s < 3 s
    (a, b, motivo), = cortes(decidir(linha, regras_short()))
    assert motivo == "silencio" and b - a == pytest.approx(2 - 0.25 - 0.15, abs=0.25)


def test_nunca_corta_no_meio_da_palavra():
    from autoedit.decidir_cortes import decidir

    linha = linha_sintetica(falas=[(0, 10), (40, 60)], silencio=[(10, 40)], parado=[(10, 40)])
    for a, b, _ in cortes(decidir(linha, regras_longo(margem_depois=0, margem_antes=0))):
        for i, f in linha.palavras:
            assert not (i < a < f) and not (i < b < f)


def test_ima_na_troca_de_cena():
    from autoedit.decidir_cortes import decidir

    linha = linha_sintetica(falas=[(0, 10), (40, 60)], silencio=[(10, 40)], parado=[(10, 40)], trocas=[11.3, 39.0])
    (a, b, _), = cortes(decidir(linha, regras_longo()))
    assert a == pytest.approx(11.3) and b == pytest.approx(39.0)
    # Alt (sem ima): a borda fica nas margens
    (a, b, _), = cortes(decidir(linha, regras_longo(ima_troca_cena=0)))
    assert a == pytest.approx(10.8, abs=0.11)


def test_juntar_cortes_proximos_e_trecho_minimo():
    from autoedit.decidir_cortes import decidir

    # dois silencios separados por 1 s de jogo SEM fala: viram um corte so
    linha = linha_sintetica(falas=[(0, 10), (40, 60)], silencio=[(10, 24), (25, 40)], parado=[(10, 40)])
    assert len(cortes(decidir(linha, regras_longo()))) == 1
    # com fala no meio: a fala fica (nada de cortar a palavra para juntar)
    linha = linha_sintetica(falas=[(0, 10), (24, 25.5), (40, 60)], silencio=[(10, 24), (25.5, 40)],
                            parado=[(10, 40)])  # fmt: skip
    cs = cortes(decidir(linha, regras_longo()))
    assert len(cs) == 2 and cs[0][1] <= 24 and cs[1][0] >= 25.5


def test_sem_jogo_tela_preta_e_claude():
    from autoedit.decidir_cortes import decidir

    linha = linha_sintetica(falas=[(0, 10), (30, 60)], preto=[(10, 30)])
    sug = decidir(linha, regras_longo())
    assert [s["motivo"] for s in sug if s["acao"] == "cortar"] == ["sem_jogo"]
    assert sug[0]["confianca"] == "alta"
    # menu visto pelo Claude (sem fala): sai como sem_jogo
    linha = linha_sintetica(falas=[(0, 10), (30, 60)], cenas=[(10, 20, "alta"), (20, 30, "alta")])
    assert [s["motivo"] for s in decidir(linha, regras_longo()) if s["acao"] == "cortar"] == ["sem_jogo"]


def test_confianca_baixa_e_papo_fora_so_sugerem():
    from autoedit.decidir_cortes import decidir

    linha = linha_sintetica(falas=[(0, 10), (60, 90)])
    papo = [{"inicio": 10, "fim": 60, "motivo": "esperando amigo"}]
    sug = decidir(linha, regras_longo(), papo)
    amarelos = [s for s in sug if s["motivo"] == "papo_fora"]
    assert amarelos and all(s["acao"] == "manter" and s["confianca"] == "baixa" for s in amarelos)


def test_acelerar_em_vez_de_cortar():
    from autoedit.decidir_cortes import decidir

    linha = linha_sintetica(falas=[(0, 10), (40, 60)], parado=[(10, 40)])  # som do jogo alto, tela parada
    sug = [s for s in decidir(linha, regras_longo(acelerar_em_vez_de_cortar=True)) if s["acao"] != "manter"]
    assert sug and sug[0]["acao"] == "acelerar" and sug[0]["velocidade"] == 2.0


def test_mesma_entrada_mesmo_resultado():
    from autoedit.decidir_cortes import decidir

    def uma():
        linha = linha_sintetica(falas=[(0, 10), (40, 60), (70, 80)], silencio=[(10, 40), (60, 70)],
                                parado=[(10, 40), (85, 100)], preto=[(100, 110)], trocas=[12.0, 55.5])  # fmt: skip
        return decidir(linha, regras_longo())

    assert json.dumps(uma()) == json.dumps(uma())


# ------------------------------------------------------------------ trechos, mapa de tempo, desfazer


def test_resolver_manual_vence_sugestao_e_introducao_protegida():
    from autoedit import trechos as tr

    lista = tr.normalizar([
        {"inicio": 10, "fim": 30, "acao": "cortar", "motivo": "silencio", "origem": "auto"},
        {"inicio": 15, "fim": 20, "acao": "manter", "motivo": "manual", "origem": "manual"},
        {"inicio": 50, "fim": 60, "acao": "cortar", "motivo": "sem_acao", "origem": "auto"},
    ])  # fmt: skip
    res = tr.resolver(lista, 100, protegidos=[(55, 70)])
    assert res == [(10, 15, "cortar", 1.0), (20, 30, "cortar", 1.0), (50, 55, "cortar", 1.0)]
    # corte manual na introducao so vale com "forcar" (voce confirmou)
    lista.append({"inicio": 56, "fim": 58, "acao": "cortar", "motivo": "manual", "origem": "manual", "forcar": True,
                  "revisado": True, "confianca": "alta"})  # fmt: skip
    assert (56, 58, "cortar", 1.0) in tr.resolver(lista, 100, protegidos=[(55, 70)])


def test_mapa_de_tempo_e_legenda_remapeada():
    from autoedit.trechos import MapaTempo

    mapa = MapaTempo([(12, 14, "cortar", 1.0), (20, 24, "acelerar", 2.0)], inicio=10, fim=30)
    assert mapa.final(10) == 0 and mapa.final(12) == 2 and mapa.final(13) == 2 and mapa.final(15) == 3
    assert mapa.final(24) == pytest.approx(14 - 2 - 2)  # 14 s andados, 2 s cortados, 4 s em 2x = 2 s
    palavras = [{"i": 11.0, "f": 11.5, "p": "fica"}, {"i": 12.5, "f": 13.0, "p": "some"},
                {"i": 15.0, "f": 15.5, "p": "anda"}]  # fmt: skip
    novas = mapa.palavras(palavras)
    assert [w["p"] for w in novas] == ["fica", "anda"]
    assert novas[1]["i"] == pytest.approx(3.0)


def test_reanalise_mantem_os_cortes_manuais():
    from autoedit.trechos import mesclar_reanalise

    meus = [{"inicio": 5, "fim": 8, "acao": "cortar", "motivo": "manual", "origem": "manual"},
            {"inicio": 20, "fim": 30, "acao": "manter", "motivo": "silencio", "origem": "auto", "revisado": True},
            {"inicio": 40, "fim": 45, "acao": "cortar", "motivo": "silencio", "origem": "auto"}]  # fmt: skip
    novos = [{"inicio": 21, "fim": 29, "acao": "cortar", "motivo": "silencio", "origem": "auto"},
             {"inicio": 50, "fim": 55, "acao": "cortar", "motivo": "sem_acao", "origem": "auto"}]  # fmt: skip
    out = mesclar_reanalise(meus, novos)
    assert [(t["inicio"], t["origem"]) for t in out] == [(5, "manual"), (20, "auto"), (50, "auto")]


def test_desfazer_refazer_sem_limite():
    from autoedit.trechos import Historico

    h = Historico([])
    for k in range(50):
        h.mudar(h.atual + [k])
    for _ in range(50):
        h.desfazer()
    assert h.atual == [] and not h.pode_desfazer()
    assert h.refazer() == [0]
    h.mudar([9])
    assert not h.pode_refazer()


# ------------------------------------------------------------------ predefinicoes e edicao.json v3


def test_predefinicoes_salvar_versao_e_voltar_ao_padrao(tmp_path, monkeypatch):
    from autoedit import predefinicoes as p

    monkeypatch.setattr(p, "PASTA_CONFIG", tmp_path)  # no modo desenvolvedor seria a pasta padrao do GitHub

    antes = p.da("longo")
    assert antes["nome"] == "Longo (TV)" and antes["silencio_min"] == 3.0
    limpo, erros = p.validar({"sem_acao_min": "8", "nao_cortar_palavra": True}, "longo")
    assert not erros and limpo["sem_acao_min"] == 8.0
    assert p.validar({"sem_acao_min": "abc"}, "longo")[1]
    v = p.salvar("longo", limpo)
    assert v == antes["versao"] + 1 and p.da("longo")["sem_acao_min"] == 8.0
    assert p.salvar("longo", limpo) == v  # nada mudou: mesma versao
    p.voltar_ao_padrao("longo")
    assert p.da("longo")["sem_acao_min"] == 6.0 and p.da("short")["silencio_min"] == 0.6


def test_migracao_v2_para_v3_com_backup(tmp_path):
    from videos_longos.pedido_edicao import ler_edicao, migrar_arquivo

    v2 = {"versao": 2, "remover": [{"inicio": "00:00:00", "fim": "00:01:00", "motivo": "menu"}],
          "capitulos": [{"tempo": "00:01:00", "titulo": "A"}], "titulo": "T"}  # fmt: skip
    (tmp_path / "edicao.json").write_text(json.dumps(v2))
    assert migrar_arquivo(tmp_path)
    novo = json.loads((tmp_path / "edicao.json").read_text())
    assert novo["versao"] == 3 and novo["trechos"] == [] and novo["marcadores"] == [] and novo["tipo"] == "longo"
    assert novo["remover"][0]["motivo"] == "menu" and novo["titulo"] == "T"
    assert json.loads((tmp_path / "edicao.bak.json").read_text()) == v2
    dados, erros, _ = ler_edicao(tmp_path, 3600)
    assert not erros and dados["trechos"] == []


def test_pedir_de_novo_ao_claude_nao_perde_os_trechos(tmp_path):
    from videos_longos.edicao_com_claude import salvar_edicao
    from videos_longos.pedido_edicao import gravar_edicao

    gravar_edicao(tmp_path / "edicao.json", {"cortes": [], "capitulos": [], "trechos": [
        {"inicio": 1, "fim": 5, "acao": "cortar", "motivo": "manual", "origem": "manual"}],
        "predefinicao": {"nome": "Longo (TV)", "versao": 1, "tipo": "longo"}})  # fmt: skip
    salvar_edicao(tmp_path, {"cortes": [{"inicio": "00:10:00", "fim": "00:11:00", "motivo": "x"}], "capitulos": []})
    novo = json.loads((tmp_path / "edicao.json").read_text())
    assert novo["remover"] and novo["trechos"][0]["origem"] == "manual" and novo["predefinicao"]["tipo"] == "longo"


def test_plano_com_autoedit_capitulos_e_velocidade():
    from videos_longos.pedido_edicao import capitulos_editados, montar_plano

    fps = Fraction(30)
    dados = {"cortes": [], "capitulos": [{"inicio": "00:00:00", "titulo": "A"}, {"inicio": "00:01:00", "titulo": "B"},
                                         {"inicio": "00:02:00", "titulo": "C"}],
             "predefinicao": {"nome": "Longo (TV)", "versao": 1, "tipo": "longo"},
             "introducao": {"inicio": 0, "fim": 20},
             "trechos": [{"inicio": 10, "fim": 18, "acao": "cortar", "motivo": "silencio", "origem": "auto"},
                         {"inicio": 30, "fim": 50, "acao": "cortar", "motivo": "silencio", "origem": "auto"},
                         {"inicio": 70, "fim": 90, "acao": "acelerar", "velocidade": 2.0, "motivo": "sem_acao",
                          "origem": "auto"}]}  # fmt: skip
    plano = montar_plano(dados, 180.0, fps, palavras=[], cfg={})
    # a introducao (0-20) e protegida: o corte de 10-18 nao vale; o de 30-50 vale; 70-90 vira 10 s
    assert plano["dur_final"] == pytest.approx(180 - 20 - 10, abs=0.1)
    assert plano["pausas"]["n"] == 0  # o corte de pausas da 1.8.0 fica desligado com o Auto-Edit
    assert 2.0 in plano["velocidades"].values()
    caps, _ = capitulos_editados(dados, plano)
    assert [round(c[0]) for c in caps] == [0, 40, 90]  # 60 - 20 cortados; 120 - 20 - 10 da aceleracao
    assert plano["secas"]  # corte pequeno do Auto-Edit: corte seco


def test_capitulos_recalculados_depois_dos_cortes():
    from videos_longos.pedido_edicao import capitulos_editados, montar_plano

    dados = {"cortes": [], "capitulos": [{"inicio": "00:00:00", "titulo": "A"}, {"inicio": "00:02:00", "titulo": "B"},
                                         {"inicio": "00:04:00", "titulo": "C"}],
             "trechos": [{"inicio": 60, "fim": 90, "acao": "cortar", "motivo": "manual", "origem": "manual"}]}
    plano = montar_plano(dados, 300.0, Fraction(30), palavras=[], cfg={})
    caps, _ = capitulos_editados(dados, plano)
    assert [round(c[0]) for c in caps] == [0, 90, 210]


# ------------------------------------------------------------------ com o ffmpeg de verdade (amostra)


@pytest.fixture(scope="module")
def amostra(tmp_path_factory):
    import amostra_autoedit

    pasta = tmp_path_factory.mktemp("amostra")
    return amostra_autoedit.gerar(pasta / "live.mp4")


def _projeto(tmp_path, amostra):
    pasta = tmp_path / "projeto"
    pasta.mkdir()
    (pasta / "projeto.json").write_text(json.dumps({"video": str(amostra["video"]), "duracao": amostra["duracao"],
                                                    "camera_area": amostra["camera_area"]}))  # fmt: skip
    segs = [{"inicio": w["i"], "fim": w["f"], "texto": w["p"], "palavras": [w]} for w in amostra["palavras"]]
    (pasta / "transcricao.json").write_text(json.dumps({"segmentos": segs}))
    (pasta / "transcricao_para_claude.txt").write_text("[00:00:00-00:00:30] fala\n")
    return pasta


@pytest.mark.lento
def test_amostra_cada_tipo_e_detectado(tmp_path, amostra):
    from autoedit import analisar

    pasta = _projeto(tmp_path, amostra)

    def cenas_falsas(pedido, validar):  # o "Claude" diz que 80-110 s e menu
        return {"cenas": [{"tempo": t, "tipo": "menu" if 80 <= t < 110 else "gameplay", "confianca": "alta"}
                          for t in range(0, 180, 10)]}  # fmt: skip

    def fala_falsa(pedido, validar):
        return {"papo_fora": [], "introducao": {"inicio": "00:00:00", "fim": "00:00:10"}}

    r = analisar.analisar_longo(pasta, pedir_cenas=cenas_falsas, pedir_fala=fala_falsa)
    cs = [(s["inicio"], s["fim"], s["motivo"]) for s in r["sugestoes"] if s["acao"] == "cortar"]
    # um corte grande do silencio (30 s) ate o fim do menu (110 s), nada no jogo sem fala (110-150 s)
    assert cs, r["sugestoes"]
    assert any(a <= 31.5 and b >= 108 for a, b, _ in cs)
    assert not any(a < 148 and b > 112 for a, b, _ in cs)  # jogo sem fala mas com som e movimento: fica
    assert not any(a < 29 for a, b, _ in cs)  # a fala do comeco fica
    edicao = json.loads((pasta / "edicao.json").read_text())
    assert edicao["versao"] == 3 and edicao["predefinicao"]["tipo"] == "longo" and edicao["introducao"]
    assert (pasta / "analise" / "proxy.mp4").exists() and (pasta / "analise" / "miniaturas" / "folha_001.png").exists()
    # a camera (que sempre mexe) ficou de fora: a tela congelada tem movimento quase zero
    img = json.loads((pasta / "analise" / "imagem.json").read_text())
    assert max(img["movimento"][62:118]) < 0.004
    # mudar a predefinicao e instantaneo e sem analisar de novo
    sug_short = analisar.sugerir(pasta, "short", inicio=0, fim=amostra["duracao"])
    assert len([s for s in sug_short if s["acao"] == "cortar"]) >= 1
    # rodar de novo (cache) da o mesmo resultado
    r2 = analisar.analisar_longo(pasta, pedir_cenas=cenas_falsas, pedir_fala=fala_falsa)
    assert r2["sugestoes"] == r["sugestoes"] and r2["tempos"]["proxy"] < r["tempos"]["proxy"] + 1


@pytest.mark.lento
def test_amostra_sem_camera_o_movimento_engana(tmp_path, amostra):
    from autoedit import sinais_video

    img = sinais_video.medir(amostra["video"], tmp_path, amostra["duracao"], camera=None)
    assert max(img["movimento"][62:118]) > 0.0005  # a camera mexendo aparece como "acao"



# ------------------------------------------------------------------ episodio: continuar de onde parou


def test_episodio_continua_de_onde_parou(tmp_path, monkeypatch):
    from videos_longos import editar_episodio as ep

    feitos, falhar = [], {"no": 3}

    def falso(ffmpeg, video, q, n, fps, base, cod, prog=None, fade_in=0.0, fade_out=0.0):
        if base.name == f"parte_{falhar['no']:04d}":
            return 1  # "o app fechou" no trecho 3
        base.with_suffix(".mp4").write_bytes(b"v")
        base.with_suffix(".wav").write_bytes(b"a")
        feitos.append(base.name)
        return 0

    monkeypatch.setattr(ep, "render_parte", falso)
    monkeypatch.setitem(ep.CFG, "episodio_partes_simultaneas", 1)
    partes = [(k * 100, 50, 0.0, 0.0, 1.0) for k in range(5)]
    assert ep.render_lista("ffmpeg", tmp_path / "v.mp4", partes, Fraction(25), tmp_path, "x264", ep.Progresso(10, ""),
                           retomar=True) is None  # fmt: skip
    assert feitos[:2] == ["parte_0001", "parte_0002"] and "parte_0003" not in feitos
    prontos = set(feitos)
    falhar["no"] = 0
    feitos.clear()
    prog = ep.Progresso(10, "")
    bases = ep.render_lista("ffmpeg", tmp_path / "v.mp4", partes, Fraction(25), tmp_path, "x264", prog, retomar=True)
    assert len(bases) == 5 and "parte_0003" in feitos and not prontos & set(feitos)  # os prontos nao refaz
    assert abs(prog.feito - 10.0) < 1e-6


def test_xml_para_outro_editor_tem_um_clipe_por_trecho(tmp_path):
    from videos_longos.exportar_outro_editor import xml_fcp7

    plano = {"fps": Fraction(30000, 1001), "dur_original": 60.0, "trechos": [(0, 300), (600, 450)],
             "velocidades": {1: 2.0}}  # fmt: skip
    xml = xml_fcp7(plano, tmp_path / "live & cia.mp4", "Ep <1>", 1920, 1080)
    assert xml.count("<clipitem") == 4 and "<ntsc>TRUE</ntsc>" in xml and "acelerar 2x" in xml
    assert "&amp;" in xml and "Ep &lt;1&gt;" in xml and "<in>600</in><out>1050</out>" in xml


def test_descricao_padrao_do_canal_vai_no_fim_do_video_longo(tmp_path, monkeypatch):
    """Issues #7 e #8: a descricao do video longo nao seguia o padrao do canal."""
    from nucleo import comum
    from publicacao import rascunhos
    from videos_longos import pedido_edicao

    monkeypatch.setattr(comum, "PASTA_CONFIG", tmp_path / "config")
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "descricao_padrao.txt").write_text(
        "// comentario\nSe inscreva: {canal}\n#gameplay #famosozora\n", encoding="utf-8")
    assert comum.ler_descricao_padrao() == f"Se inscreva: {comum.CANAL_URL}\n#gameplay #famosozora"
    assert "PADRÃO DO CANAL" in pedido_edicao.criterios() and "#gameplay" in pedido_edicao.criterios()
    pasta = tmp_path / "proj"
    (pasta / "episodio").mkdir(parents=True)
    (pasta / "episodio" / "Ep.mp4").write_bytes(b"x")
    (pasta / "episodio" / "episodio.json").write_text(json.dumps({"arquivo": "Ep.mp4", "capitulos": [
        {"inicio": 0, "titulo": "A"}, {"inicio": 60, "titulo": "B"}, {"inicio": 120, "titulo": "C"}]}))
    (pasta / "edicao.json").write_text(json.dumps({"versao": 3, "titulo": "Ep", "descricao": "Hoje tem chefe."}))
    item = rascunhos.rascunho_longo({"pasta": pasta})
    assert item["descricao"].startswith("Hoje tem chefe.") and item["descricao"].endswith("#gameplay #famosozora")
    assert "0:00 A" in item["descricao"]
