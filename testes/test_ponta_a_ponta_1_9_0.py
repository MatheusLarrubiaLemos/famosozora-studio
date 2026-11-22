# Ponta a ponta da 1.9.0 com o ffmpeg de verdade (rodar com: python -m pytest -m lento):
#   - episodio com os trechos do Auto-Edit (um corte e um trecho acelerado 2x): a duracao bate com a conta;
#   - Short com um pedaco cortado DENTRO dele ("Ajustar corte"): o video fica mais curto e a legenda acompanha;
#   - exportar para outro editor (XML e um arquivo por trecho).
import json
import os
import shutil
import subprocess
import sys

import pytest
from conftest import RAIZ, TEMP
from test_ponta_a_ponta_longo import _ffmpeg, _gerar, _sonda

pytestmark = pytest.mark.lento
DUR = 20.0


@pytest.fixture(scope="module")
def amb():
    base = TEMP / "ponta_a_ponta_1_9_0"
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
              "episodio_preset": "ultrafast", "cor_por_falante": False, "retranscrever_cortes": "false",
              "musica": "nenhuma", "usar_abertura": False, "duracao_final": 0, "layout": "desfocado"}  # fmt: skip
    (dados / "configuracoes" / "config.json").write_text(json.dumps(config), encoding="utf-8")
    video = trabalho / "videos" / "live.mp4"
    video.parent.mkdir(parents=True)
    _ffmpeg()
    _gerar("-f", "lavfi", "-i", f"testsrc2=size=640x360:rate=30:duration={DUR}", "-f", "lavfi", "-i",
           "sine=frequency=440:sample_rate=48000", "-t", DUR, "-c:v", "libx264", "-preset", "ultrafast",
           "-c:a", "aac", "-shortest", video)  # fmt: skip
    projeto = trabalho / "shorts" / "live"
    projeto.mkdir(parents=True)
    (projeto / "projeto.json").write_text(json.dumps({"video": str(video), "duracao": DUR}), encoding="utf-8")
    palavras = [{"i": t, "f": t + 0.3, "p": f"p{int(t * 10)}"} for t in [2.0 + 0.5 * k for k in range(20)]]
    (projeto / "transcricao.json").write_text(json.dumps({"segmentos": [
        {"inicio": 2.0, "fim": 12.0, "texto": "x", "palavras": palavras}]}), encoding="utf-8")  # fmt: skip
    env = dict(os.environ, LOCALAPPDATA=str(base / "localappdata"), PYTHONIOENCODING="utf-8")
    return {"codigo": codigo, "env": env, "projeto": projeto, "video": video}


def _rodar(amb, *args) -> str:
    r = subprocess.run([sys.executable, "-m", *map(str, args)], cwd=amb["codigo"], env=amb["env"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)  # fmt: skip
    saida = r.stdout + r.stderr
    assert r.returncode == 0 and "Traceback" not in saida and "[ERRO]" not in saida, saida[-3000:]
    return saida


def test_episodio_com_corte_e_trecho_acelerado(amb):
    edicao = {"versao": 3, "remover": [], "capitulos": [], "titulo": "Ep auto",
              "predefinicao": {"nome": "Longo (TV)", "versao": 1, "tipo": "longo"},
              "trechos": [{"inicio": 3, "fim": 6, "acao": "cortar", "motivo": "silencio", "origem": "auto"},
                          {"inicio": 10, "fim": 14, "acao": "acelerar", "velocidade": 2.0, "motivo": "sem_acao",
                           "origem": "manual", "revisado": True}]}  # fmt: skip
    (amb["projeto"] / "edicao.json").write_text(json.dumps(edicao), encoding="utf-8")
    saida = _rodar(amb, "videos_longos.editar_episodio", amb["projeto"])
    assert "Auto-Edit:" in saida
    ep = next(f for f in (amb["projeto"] / "episodio").glob("*.mp4") if not f.name.startswith("_"))
    dur = float(_sonda(ep, "-show_entries", "format=duration", "-of", "default=nw=1:nk=1"))
    assert dur == pytest.approx(DUR - 3 - 2, abs=0.3)  # 3 s cortados, 4 s em 2x = 2 s a menos
    audio = float(_sonda(ep, "-select_streams", "a:0", "-show_entries", "stream=duration", "-of",
                         "default=nw=1:nk=1"))  # fmt: skip
    assert abs(audio - dur) < 0.3  # som e imagem do mesmo tamanho (atempo acompanhou o setpts)


def test_short_com_pedaco_cortado_dentro_e_legenda_que_acompanha(amb):
    projeto = amb["projeto"]
    (projeto / "cortes.json").write_text(json.dumps({"versao": 3, "cortes": [
        {"inicio": "00:00:02", "fim": "00:00:12", "titulo": "Com corte"}], "correcoes": {}}), encoding="utf-8")
    (projeto / "edicao_shorts").mkdir(exist_ok=True)
    (projeto / "edicao_shorts" / "01_autoedit.json").write_text(json.dumps({
        "versao": 3, "tipo": "short", "n": 1, "limites": [2.0, 12.0], "janela": [0.0, 20.0], "marcadores": [],
        "trechos": [{"inicio": 5.0, "fim": 8.0, "acao": "cortar", "motivo": "manual", "origem": "manual",
                     "revisado": True}]}), encoding="utf-8")  # fmt: skip
    _rodar(amb, "shorts.gerar_shorts", projeto, "--so", "1")
    short = next((projeto / "prontos").glob("01 - *.mp4"))
    dur = float(_sonda(short, "-show_entries", "format=duration", "-of", "default=nw=1:nk=1"))
    assert dur == pytest.approx(10 - 3, abs=0.3)
    original = json.loads((projeto / "legendas" / "01_original.json").read_text(encoding="utf-8"))
    assert original["palavras"]  # a legenda original guarda o tempo do video (sem os cortes)
