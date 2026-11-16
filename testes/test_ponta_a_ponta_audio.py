# Teste de ponta a ponta da 1.4.0 (lento, uns 2 a 4 minutos; roda no Windows e no Linux, sem placa de video):
#   video de amostra de 20 s e sons de teste, TUDO gerado com o ffmpeg (tons e ruido, nada baixado)
#   -> gerar o Short (musica do clima, efeito e troca de musica sugeridos pelo "Claude" num cortes.json falso)
#   -> nomear um falante e ligar o nome no video -> trocar a musica -> adicionar um efeito e excluir o outro
#   -> renderizar de novo so este Short -> medir o audio (ducking, efeito no lugar certo, sem estourar)
# Roda o programa como se estivesse INSTALADO, numa pasta temporaria. Rodar: python -m pytest -m lento
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest
from conftest import RAIZ, TEMP

pytestmark = pytest.mark.lento
VOZ = [(3.0, 7.0, 0), (10.0, 13.0, 1)]  # (inicio, fim, voz) no video original: voz 0 = FamosoZora, voz 1 = Pedro
INICIO, FIM = 2.0, 16.0  # o corte; no Short a voz fica em 1-5 s e 8-11 s
TOM_A, TOM_B, TOM_VOZ = 880, 1320, 300  # Hz: musica A, musica B e a "voz"


def _ffmpeg():
    for candidato in (RAIZ / "bin" / "ffmpeg.exe", shutil.which("ffmpeg")):
        if candidato and Path(candidato).exists():
            return str(candidato)
    pytest.skip("ffmpeg nao encontrado")


def _gerar(*args):
    subprocess.run([_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", *map(str, args)], check=True)


@pytest.fixture(scope="module")
def amb():
    """ "App instalado" numa pasta temporaria, com biblioteca de sons de teste e um projeto com cortes.json falso."""
    base = TEMP / "ponta_a_ponta_audio"
    shutil.rmtree(base, ignore_errors=True)
    codigo = base / "programa" / "ferramentas"
    shutil.copytree(RAIZ / "app", codigo, ignore=shutil.ignore_patterns("__pycache__"))
    (codigo / "APP_INSTALADO").write_text("teste", encoding="utf-8")
    if (RAIZ / "bin").exists():
        shutil.copytree(RAIZ / "bin", base / "programa" / "bin")
    dados = base / "localappdata" / "FamosoZora Studio"
    trabalho = base / "trabalho"
    (dados / "configuracoes").mkdir(parents=True)
    (dados / "ajustes.json").write_text(json.dumps({"pasta_trabalho": str(trabalho)}), encoding="utf-8")
    config = {"dispositivo": "cpu", "codificar_na_gpu": False, "cor_por_falante": False, "layout": "desfocado",
              "retranscrever_cortes": "false", "musica": "aleatoria", "qualidade_crf": 28}  # fmt: skip
    (dados / "configuracoes" / "config.json").write_text(json.dumps(config), encoding="utf-8")

    # biblioteca deste "PC": 2 musicas epicas (uma curta, para testar o crossfade) e 1 efeito de impacto
    (dados / "musicas" / "epico").mkdir(parents=True)
    (dados / "efeitos" / "impacto").mkdir(parents=True)
    _gerar("-f", "lavfi", "-i", f"sine=frequency={TOM_A}:sample_rate=44100", "-t", "6", "-ac", "1",
           dados / "musicas" / "epico" / "a_curta.wav")  # fmt: skip
    _gerar("-f", "lavfi", "-i", f"sine=frequency={TOM_B}", "-t", "30", dados / "musicas" / "epico" / "b_longa.mp3")
    _gerar("-f", "lavfi", "-i", "anoisesrc=d=0.5:c=white:a=0.6", dados / "efeitos" / "impacto" / "estalo.wav")

    # video de 20 s: fundo cinza (sem ciano, para conferir a cor da legenda) + "voz" (tom de 300 Hz, volume de fala normal) nos trechos de VOZ
    video = trabalho / "videos" / "amostra.mp4"
    video.parent.mkdir(parents=True)
    liga = "+".join(f"between(t,{a},{b})" for a, b, _ in VOZ)
    _gerar("-f", "lavfi", "-i", "color=c=0x505050:size=1920x1080:rate=30:duration=20", "-f", "lavfi", "-i",
           f"sine=frequency={TOM_VOZ}:sample_rate=48000", "-filter_complex",
           f"[1:a]volume='if({liga},2,0)':eval=frame[a]", "-map", "0:v", "-map", "[a]", "-t", "20",
           "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", video)  # fmt: skip

    projeto = trabalho / "shorts" / "amostra"
    projeto.mkdir(parents=True)
    palavras = [{"i": round(a + k * 0.5, 2), "f": round(a + k * 0.5 + 0.4, 2), "p": f"fala{voz}_{k}", "s": voz}
                for a, b, voz in VOZ for k in range(int((b - a) / 0.5))]  # fmt: skip
    segmentos = [{"inicio": a, "fim": b, "texto": "x", "palavras": [w for w in palavras if a <= w["i"] < b]}
                 for a, b, _ in VOZ]  # fmt: skip
    (projeto / "projeto.json").write_text(json.dumps({"video": str(video), "duracao": 20}), encoding="utf-8")
    (projeto / "transcricao.json").write_text(json.dumps({"segmentos": segmentos}), encoding="utf-8")
    cortes = {"versao": 3, "cortes": [{
        "inicio": INICIO, "fim": FIM, "titulo": "Teste de audio", "clima": "Épico", "nota": 8,
        "motivo": "teste", "sons": [{"tempo": 8.5, "categoria": "impacto", "motivo": "pancada"},
                                    {"tempo": 9.0, "tipo": "musica", "clima": "epico", "motivo": "virada"}]}]}  # fmt: skip
    (projeto / "cortes.json").write_text(json.dumps(cortes, ensure_ascii=False), encoding="utf-8")
    env = dict(os.environ, LOCALAPPDATA=str(base / "localappdata"), PYTHONIOENCODING="utf-8")
    return {"codigo": codigo, "env": env, "dados": dados, "projeto": projeto}


def _rodar(amb, *args):
    t = time.time()
    r = subprocess.run([sys.executable, "-m", *args], cwd=amb["codigo"], env=amb["env"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=900)  # fmt: skip
    saida = r.stdout + r.stderr
    assert r.returncode == 0 and "Traceback" not in saida and "[ERRO]" not in saida, saida[-3000:]
    return saida, time.time() - t


def _nivel(arquivo, ini, dur, freq=None, passa_alta=None) -> float:
    """Volume (dB RMS) do audio do Short entre ini e ini+dur, so na frequencia freq (ou acima de passa_alta)."""
    filtro = f"bandpass=f={freq}:width_type=q:w=12," if freq else (f"highpass=f={passa_alta}," if passa_alta else "")
    r = subprocess.run([_ffmpeg(), "-hide_banner", "-ss", str(ini), "-t", str(dur), "-i", str(arquivo), "-af",
                        f"{filtro}astats=metadata=0", "-f", "null", "-"], capture_output=True, text=True)  # fmt: skip
    linha = [x for x in r.stderr.splitlines() if "RMS level dB" in x][-1]
    valor = linha.rsplit(":", 1)[1].strip()
    return -120.0 if "inf" in valor else float(valor)


def _pico(arquivo) -> float:
    r = subprocess.run([_ffmpeg(), "-hide_banner", "-i", str(arquivo), "-af", "astats=metadata=0", "-f", "null", "-"],
                       capture_output=True, text=True)  # fmt: skip
    return float([x for x in r.stderr.splitlines() if "Peak level dB" in x][-1].rsplit(":", 1)[1])


def _pixels_ciano(arquivo, t) -> int:
    """Quantos pixels ciano (a cor do Pedro) aparecem na faixa da legenda no instante t do Short."""
    r = subprocess.run([_ffmpeg(), "-hide_banner", "-loglevel", "error", "-ss", str(t), "-i", str(arquivo),
                        "-frames:v", "1", "-vf", "crop=1080:330:0:1130", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       capture_output=True, check=True)  # fmt: skip
    px = r.stdout
    return sum(1 for k in range(0, len(px), 3) if px[k] < 175 and px[k + 1] > 200 and px[k + 2] > 225)


def test_audio_falantes_e_edicao_de_ponta_a_ponta(amb):
    projeto, resultados = amb["projeto"], []
    short = projeto / "prontos" / "01 - Teste de audio.mp4"

    # 1) gerar: musica do clima (epico), efeito em 8.5 s (6.5 s no Short) e troca de musica em 9 s (7 s no Short)
    saida, tempo_com_audio = _rodar(amb, "shorts.gerar_shorts", str(projeto))
    assert "1 criado(s)" in saida and "PROCESSADOR (x264)" in saida and "efeitos sonoros: 1" in saida, saida
    sug = json.loads((projeto / "edicao_shorts" / "01_sugestao.json").read_text(encoding="utf-8"))
    assert sug["musica"]["arquivo"].startswith("epico/")
    assert sug["efeitos"][0]["arquivo"] == "impacto/estalo.wav" and sug["efeitos"][0]["tempo"] == 6.5
    assert len(sug["trocas_musica"]) == 1 and sug["trocas_musica"][0]["tempo"] == 7.0
    tom_1 = TOM_A if sug["musica"]["arquivo"] == "epico/a_curta.wav" else TOM_B
    sem_fala, com_fala = _nivel(short, 5.6, 0.7, tom_1), _nivel(short, 1.5, 3.0, tom_1)
    resultados.append(("ducking: a musica abaixa na fala", f"{sem_fala:.1f} dB sem fala -> {com_fala:.1f} dB com fala"))
    assert com_fala < sem_fala - 4, (sem_fala, com_fala)
    antes, no_efeito = _nivel(short, 5.6, 0.7, passa_alta=6000), _nivel(short, 6.5, 0.45, passa_alta=6000)
    resultados.append(("efeito no tempo certo (6.5 s)", f"agudos {antes:.1f} dB -> {no_efeito:.1f} dB"))
    assert no_efeito > antes + 15, (antes, no_efeito)
    pico = _pico(short)
    resultados.append(("sem estourar", f"pico {pico:.1f} dBFS"))
    assert pico < -0.1
    assert _pixels_ciano(short, 9.0) < 50  # ainda sem nomes: todo mundo branco

    # 2) como no editor: o Pedro e a voz 1 (com nome no video), troca a musica, poe um efeito em 2 s e exclui o de 6.5 s
    (amb["dados"] / "configuracoes" / "pessoas.json").write_text(json.dumps({"versao": 1, "pessoas": [
        {"nome": "FamosoZora", "cor": "#FFFFFF", "padrao": True}, {"nome": "Pedro", "cor": "#8CE6FF"}]}),
        encoding="utf-8")  # fmt: skip
    (projeto / "falantes.json").write_text(
        json.dumps({"versao": 1, "shorts": {"01": {"1": "Pedro"}}}), encoding="utf-8"
    )
    ed = json.loads(json.dumps(sug))
    outra = "epico/b_longa.mp3" if tom_1 == TOM_A else "epico/a_curta.wav"
    ed["musica"] = {"ligada": True, "arquivo": outra, "volume": 0.25}
    ed["trocas_musica"] = []
    ed["efeitos"] = [{"tempo": 2.0, "categoria": "impacto", "arquivo": "impacto/estalo.wav", "volume": 0.5}]
    ed["mostrar_nome_falante"] = True
    (projeto / "edicao_shorts" / "01_edicao.json").write_text(json.dumps(ed), encoding="utf-8")

    # 3) renderizar de novo so este Short
    saida, _ = _rodar(amb, "shorts.gerar_shorts", str(projeto), "--so", "1")
    assert "Renderizando de novo SO o Short 1" in saida and f"musica: {outra}" in saida, saida
    tom_2 = TOM_B if tom_1 == TOM_A else TOM_A
    assert _nivel(short, 12.0, 1.0, tom_2) > _nivel(short, 12.0, 1.0, tom_1) + 15  # musica trocada, sem a troca no meio
    assert _nivel(short, 6.5, 0.45, passa_alta=6000) < -60  # efeito excluido
    assert _nivel(short, 2.0, 0.45, passa_alta=6000) > -45  # efeito novo
    ciano = _pixels_ciano(short, 9.0)
    resultados.append(("cor e nome do Pedro na legenda", f"{ciano} pixels ciano na faixa da legenda"))
    assert ciano > 300
    assert json.loads((projeto / "edicao_shorts" / "01_sugestao.json").read_text(encoding="utf-8")) == sug  # intacta

    # 4) musica e efeitos desligados: compara o tempo de render (tudo no processador)
    ed["musica"]["ligada"], ed["efeitos_ligados"] = False, False
    (projeto / "edicao_shorts" / "01_edicao.json").write_text(json.dumps(ed), encoding="utf-8")
    _, tempo_sem_audio = _rodar(amb, "shorts.gerar_shorts", str(projeto), "--so", "1")
    assert _nivel(short, 12.0, 1.0, tom_2) < -70 and _nivel(short, 2.0, 0.45, passa_alta=6000) < -60
    resultados.append(("tempo de render", f"{tempo_com_audio:.0f} s com musica+efeitos, {tempo_sem_audio:.0f} s sem"))
    print("\n" + "\n".join(f"| {a} | sim | {b} |" for a, b in resultados))


def test_previa_do_trecho_com_efeito(amb):
    """O botao "Trecho com o efeito" do editor: 5 s de audio com a fala, a musica e o efeito no meio (2 s)."""
    projeto = amb["projeto"]
    if not (projeto / "edicao_shorts" / "01_sugestao.json").exists():
        _rodar(amb, "shorts.gerar_shorts", str(projeto))
    saida = projeto / "previa.m4a"
    script = (
        "import json, subprocess, sys; from pathlib import Path; from shorts import audio_short, biblioteca; "
        f"p = Path(r'{projeto}'); sug = json.loads((p / 'edicao_shorts' / '01_sugestao.json').read_text(encoding='utf-8')); "
        "efeito = {'arquivo': biblioteca.caminho('efeito', 'impacto/estalo.wav'), 'volume': 0.8}; "
        f"cmd = audio_short.comando_previa(sys.argv[1], Path(r'{projeto.parent.parent / 'videos' / 'amostra.mp4'}'), "
        f"sug, 6.5, efeito, saida=Path(r'{saida}')); sys.exit(subprocess.run(cmd).returncode)"
    )
    r = subprocess.run([sys.executable, "-c", script, _ffmpeg()], cwd=amb["codigo"], env=amb["env"])
    assert r.returncode == 0 and saida.exists()
    assert _nivel(saida, 1.9, 0.5, passa_alta=6000) > _nivel(saida, 0.5, 1.0, passa_alta=6000) + 15
