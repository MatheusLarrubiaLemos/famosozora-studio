# Teste de ponta a ponta do "continuar de onde parou" do episodio (lento; ffmpeg de verdade, sem placa de video):
#   live de amostra SEM nenhum corte (antes era um trecho so: fechar o app no meio = comecar do zero)
#   -> o Studio divide em pedacos pequenos; o episodio sai com a duracao certa e o som SEM falha nas emendas;
#   -> o processo e morto no meio (como fechar o app); rodando de novo, ele continua dos pedacos prontos.
# Tambem tem o teste rapido da conta que divide os trechos (dividir_em_pedacos).
import json
import os
import shutil
import subprocess
import sys
import time
from fractions import Fraction
from pathlib import Path

import pytest
from conftest import RAIZ, TEMP

DUR_VIDEO = 12.0


def test_dividir_em_pedacos():
    """Conta pura: trecho longo vira pedacos iguais que emendam sem fade; curto e acelerado ficam inteiros."""
    from videos_longos.editar_episodio import dividir_em_pedacos

    fps = Fraction(30)
    # 1 trecho de 100 s, pedacos de ate 30 s -> 4 pedacos de 25 s, colados um no outro
    pedacos = dividir_em_pedacos([(0, 3000, 0.2, 0.2, 1.0)], fps, 30)
    assert [(q, n) for q, n, *_ in pedacos] == [(0, 750), (750, 750), (1500, 750), (2250, 750)]
    assert [p[2] for p in pedacos] == [0.2, 0, 0, 0] and [p[3] for p in pedacos] == [0, 0, 0, 0.2]  # fade so nas pontas
    assert [p[5] for p in pedacos] == [False, True, True, True]  # continua do anterior (sem fade de som)
    assert [p[6] for p in pedacos] == [True, True, True, False]  # continua no proximo
    assert sum(p[1] for p in pedacos) == 3000
    # curto (ate 1,5x o pedaco) e acelerado ficam inteiros; 0 desliga
    assert len(dividir_em_pedacos([(0, 1200, 0, 0, 1.0)], fps, 30)) == 1
    assert len(dividir_em_pedacos([(0, 30000, 0, 0, 2.0)], fps, 30)) == 1
    assert len(dividir_em_pedacos([(0, 30000, 0, 0, 1.0)], fps, 0)) == 1


def test_so_a_predefinicao_nao_desliga_o_corte_de_pausas():
    """O editor grava a "predefinicao" ao salvar, mesmo sem a live ter sido analisada. Antes isso desligava o corte
    de pausas sem o Auto-Edit cortar nada: a live de 9 h virava um episodio de 9 h. Agora so trechos contam."""
    from videos_longos.pedido_edicao import autoedit_ativo, montar_plano

    pre = {"nome": "Longo (TV)", "versao": 1, "tipo": "longo"}
    assert not autoedit_ativo({"predefinicao": pre}) and not autoedit_ativo({"predefinicao": pre, "trechos": []})
    assert autoedit_ativo({"trechos": [{"inicio": 1, "fim": 2, "acao": "cortar", "origem": "manual"}]})
    # fala aos 0-5 s e aos 60-65 s: a pausa de ~55 s no meio sai, mesmo com a predefinicao gravada
    palavras = [(t, t + 0.4) for t in [k * 0.5 for k in range(10)] + [60 + k * 0.5 for k in range(10)]]
    plano = montar_plano({"cortes": [], "predefinicao": pre}, 70.0, Fraction(30), palavras,
                         {"episodio_ajuste_silencio": 0})  # fmt: skip
    assert plano["pausas"]["n"] >= 1 and plano["dur_final"] < 30, plano["dur_final"]


def _ffmpeg():
    for candidato in (RAIZ / "bin" / "ffmpeg.exe", shutil.which("ffmpeg")):
        if candidato and Path(candidato).exists():
            return str(candidato)
    pytest.skip("ffmpeg nao encontrado")


def _ffprobe():
    return str(Path(_ffmpeg()).with_name("ffprobe" + (".exe" if _ffmpeg().endswith(".exe") else "")))


def _duracao(arq) -> float:
    r = subprocess.run([_ffprobe(), "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1",
                        str(arq)], capture_output=True, text=True)  # fmt: skip
    return float(r.stdout.strip())


@pytest.fixture
def amb(tmp_path):
    base = TEMP / f"retomar_{tmp_path.name}"
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
    config = {"codificar_na_gpu": False, "episodio_ajuste_silencio": 0, "episodio_crf": 30,
              "episodio_preset": "ultrafast", "episodio_pedaco_max_s": 1, "episodio_partes_simultaneas": 1}  # fmt: skip
    (dados / "configuracoes" / "config.json").write_text(json.dumps(config), encoding="utf-8")
    video = trabalho / "videos" / "live.mp4"
    video.parent.mkdir(parents=True)
    subprocess.run([_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    f"testsrc2=size=640x360:rate=30:duration={DUR_VIDEO}", "-f", "lavfi", "-i",
                    "sine=frequency=440:sample_rate=48000", "-t", str(DUR_VIDEO), "-c:v", "libx264", "-preset",
                    "ultrafast", "-c:a", "aac", "-shortest", str(video)], check=True)  # fmt: skip
    projeto = trabalho / "shorts" / "live"
    projeto.mkdir(parents=True)
    (projeto / "projeto.json").write_text(json.dumps({"video": str(video), "duracao": DUR_VIDEO}), encoding="utf-8")
    (projeto / "transcricao.json").write_text(json.dumps({"segmentos": []}), encoding="utf-8")
    edicao = {"remover": [], "capitulos": [], "titulo": "Sem cortes", "incluir_outro": False, "cortar_pausas": False}
    (projeto / "edicao.json").write_text(json.dumps(edicao), encoding="utf-8")
    env = dict(os.environ, LOCALAPPDATA=str(base / "localappdata"), PYTHONIOENCODING="utf-8")
    return {"codigo": codigo, "env": env, "projeto": projeto}


def _comando(amb):
    return [sys.executable, "-m", "videos_longos.editar_episodio", str(amb["projeto"])]


def _rodar(amb) -> str:
    r = subprocess.run(_comando(amb), cwd=amb["codigo"], env=amb["env"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=900, stdin=subprocess.DEVNULL)  # fmt: skip
    saida = r.stdout + r.stderr
    assert r.returncode == 0 and "Traceback" not in saida and "[ERRO]" not in saida, saida[-3000:]
    return saida


def _episodio(amb) -> Path:
    return next(f for f in (amb["projeto"] / "episodio").glob("*.mp4") if not f.name.startswith("_"))


def _volumes(arq) -> list:
    """Volume (RMS) do som do episodio em janelas de 5 ms."""
    r = subprocess.run([_ffmpeg(), "-v", "error", "-i", str(arq), "-ac", "1", "-ar", "48000", "-f", "s16le", "-"],
                       capture_output=True, check=True)  # fmt: skip
    import array

    amostras = array.array("h", r.stdout)
    janela = 240
    return [(sum(x * x for x in amostras[k : k + janela]) / janela) ** 0.5
            for k in range(0, len(amostras) - janela, janela)]  # fmt: skip


@pytest.mark.lento
def test_live_sem_cortes_vira_pedacos_sem_emenda_no_som(amb):
    saida = _rodar(amb)
    assert "/12]" in saida  # 12 s em pedacos de 1 s: 12 pedacos (antes era [0/1])
    assert "Quase nada vai ser cortado" in saida  # sem nenhum corte: avisa (sem ninguem para responder, segue)
    arq = _episodio(amb)
    assert abs(_duracao(arq) - DUR_VIDEO) < 0.2
    vol = _volumes(arq)
    meio = vol[10:-10]  # sem o fade do comeco e do fim do episodio
    assert min(meio) > 0.6 * max(meio), "o som tem uma falha (fade) numa emenda entre pedacos"


@pytest.mark.lento
def test_fechar_no_meio_continua_dos_pedacos_prontos(amb):
    feitas = amb["projeto"] / "episodio" / "_temp" / "episodio" / "feitas.json"
    p = subprocess.Popen(_comando(amb), cwd=amb["codigo"], env=amb["env"], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)  # fmt: skip
    limite = time.time() + 300
    while time.time() < limite and p.poll() is None:
        try:
            if len(json.loads(feitas.read_text(encoding="utf-8"))) >= 3:
                break
        except (OSError, ValueError):
            pass
        time.sleep(0.02)
    assert p.poll() is None, "terminou antes de dar para fechar no meio"
    p.kill()  # como fechar o app no meio
    p.wait()
    prontos = len(json.loads(feitas.read_text(encoding="utf-8")))
    saida = _rodar(amb)
    assert f"Continuando de onde parou: {prontos} de 12" in saida
    assert abs(_duracao(_episodio(amb)) - DUR_VIDEO) < 0.2
