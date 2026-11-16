# Teste de ponta a ponta do video longo da 1.5.0 (lento, ~1 minuto; roda no Windows e no Linux, sem placa de video):
#   video de amostra de 20 s (1280x720, 30 fps, audio 44,1 kHz) e um OUTRO de amostra diferente de proposito
#   (640x360, 25 fps, SEM audio), tudo gerado com o ffmpeg
#   -> edicao.json no formato ANTIGO (com gancho): o Studio migra (edicao.bak.json) e tira o gancho
#   -> gera o episodio: sai o trecho marcado, emendas com transicao, outro no fim com xfade (convertido na hora)
#   -> confere duracao, resolucao, FPS, audio e capitulos; depois "Incluir outro" desligado.
# Roda o programa como se estivesse INSTALADO, numa pasta temporaria. Rodar: python -m pytest -m lento
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import RAIZ, TEMP

pytestmark = pytest.mark.lento
DUR_VIDEO, DUR_OUTRO = 20.0, 6.0
SAI = (5.0, 9.0)  # trecho que o "Claude" mandou tirar


def _ffmpeg():
    for candidato in (RAIZ / "bin" / "ffmpeg.exe", shutil.which("ffmpeg")):
        if candidato and Path(candidato).exists():
            return str(candidato)
    pytest.skip("ffmpeg nao encontrado")


def _ffprobe():
    return str(Path(_ffmpeg()).with_name("ffprobe" + (".exe" if _ffmpeg().endswith(".exe") else "")))


def _gerar(*args):
    subprocess.run([_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", *map(str, args)], check=True)


def _sonda(arquivo, *args) -> str:
    r = subprocess.run([_ffprobe(), "-v", "error", *args, str(arquivo)], capture_output=True, text=True)
    return r.stdout.strip()


@pytest.fixture(scope="module")
def amb():
    base = TEMP / "ponta_a_ponta_longo"
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
              "episodio_preset": "ultrafast"}  # fmt: skip
    (dados / "configuracoes" / "config.json").write_text(json.dumps(config), encoding="utf-8")

    video = trabalho / "videos" / "live.mp4"
    video.parent.mkdir(parents=True)
    _gerar("-f", "lavfi", "-i", f"testsrc2=size=1280x720:rate=30:duration={DUR_VIDEO}", "-f", "lavfi", "-i",
           "sine=frequency=440:sample_rate=44100", "-t", DUR_VIDEO, "-c:v", "libx264", "-preset", "ultrafast",
           "-c:a", "aac", "-shortest", video)  # fmt: skip
    (trabalho / "outro").mkdir(parents=True)
    _gerar("-f", "lavfi", "-i", f"color=c=0xD97757:size=640x360:rate=25:duration={DUR_OUTRO}", "-c:v", "libx264",
           "-preset", "ultrafast", trabalho / "outro" / "outro.mp4")  # fmt: skip

    projeto = trabalho / "shorts" / "live"
    projeto.mkdir(parents=True)
    (projeto / "projeto.json").write_text(json.dumps({"video": str(video), "duracao": DUR_VIDEO}), encoding="utf-8")
    (projeto / "transcricao.json").write_text(json.dumps({"segmentos": []}), encoding="utf-8")
    antigo = {  # formato da 1.4.0: "cortes" + "abertura" (gancho) + capitulos com "inicio"
        "cortes": [{"inicio": "00:00:05", "fim": "00:00:09", "motivo": "tela parada"}],
        "abertura": {"inicio": "00:00:15", "fim": "00:00:18"},
        "capitulos": [{"inicio": "00:00:00", "titulo": "Começo"}, {"inicio": "00:00:15", "titulo": "Meio"}],
        "titulo": "Episódio de teste", "descricao": "d", "tags": ["a"],
    }  # fmt: skip
    (projeto / "edicao.json").write_text(json.dumps(antigo, ensure_ascii=False), encoding="utf-8")
    env = dict(os.environ, LOCALAPPDATA=str(base / "localappdata"), PYTHONIOENCODING="utf-8")
    return {"codigo": codigo, "env": env, "projeto": projeto, "trabalho": trabalho}


def _gerar_episodio(amb) -> str:
    r = subprocess.run([sys.executable, "-m", "videos_longos.editar_episodio", str(amb["projeto"])],
                       cwd=amb["codigo"], env=amb["env"], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=900)  # fmt: skip
    saida = r.stdout + r.stderr
    assert r.returncode == 0 and "Traceback" not in saida and "[ERRO]" not in saida, saida[-3000:]
    return saida


def _episodio(amb) -> Path:
    ep = amb["projeto"] / "episodio"
    return next(f for f in ep.glob("*.mp4") if not f.name.startswith("_"))


def test_episodio_sem_gancho_com_outro_convertido(amb):
    saida = _gerar_episodio(amb)
    edicao = json.loads((amb["projeto"] / "edicao.json").read_text(encoding="utf-8"))
    assert edicao["versao"] == 2 and "abertura" not in edicao and edicao["remover"][0]["motivo"] == "tela parada"
    assert (amb["projeto"] / "edicao.bak.json").exists()  # copia do formato antigo
    assert "outro.mp4" in saida
    arq = _episodio(amb)
    duracao = float(_sonda(arq, "-show_entries", "format=duration", "-of", "default=nw=1:nk=1"))
    esperado = DUR_VIDEO - (SAI[1] - SAI[0]) + DUR_OUTRO - 0.6  # sem gancho; o outro entra com 0,6 s de transicao
    assert abs(duracao - esperado) < 0.4, (duracao, esperado)
    video = _sonda(arq, "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate", "-of", "csv=p=0")
    assert video.split(",")[:3] == ["1280", "720", "30/1"]  # o outro (640x360, 25 fps) foi convertido
    audio = _sonda(arq, "-select_streams", "a:0", "-show_entries", "stream=codec_name", "-of", "csv=p=0")
    assert audio == "aac"  # o outro nao tinha audio: ganhou silencio, e o audio continua ate o fim
    dur_audio = float(_sonda(arq, "-select_streams", "a:0", "-show_entries", "stream=duration", "-of", "csv=p=0"))
    assert abs(dur_audio - duracao) < 0.3
    capitulos = _sonda(arq, "-show_chapters", "-of", "json")
    assert "Começo" in capitulos and "Meio" in capitulos
    # no fim do episodio aparece o laranja do outro
    r = subprocess.run([_ffmpeg(), "-v", "error", "-ss", f"{duracao - 1:.2f}", "-i", str(arq), "-frames:v", "1",
                        "-vf", "scale=1:1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)  # fmt: skip
    vermelho, verde, azul = r.stdout[:3]
    assert vermelho > 150 and 90 < verde < 150 and azul < 120, (vermelho, verde, azul)
    info = json.loads((amb["projeto"] / "episodio" / "episodio.json").read_text(encoding="utf-8"))
    assert info["outro"] == "outro.mp4"


def test_episodio_com_o_outro_desligado(amb):
    arq_edicao = amb["projeto"] / "edicao.json"
    edicao = json.loads(arq_edicao.read_text(encoding="utf-8"))
    edicao["incluir_outro"] = False
    arq_edicao.write_text(json.dumps(edicao, ensure_ascii=False), encoding="utf-8")
    shutil.rmtree(amb["projeto"] / "episodio")
    saida = _gerar_episodio(amb)
    assert "Sem outro neste vídeo" in saida
    duracao = float(_sonda(_episodio(amb), "-show_entries", "format=duration", "-of", "default=nw=1:nk=1"))
    assert abs(duracao - (DUR_VIDEO - (SAI[1] - SAI[0]))) < 0.4
