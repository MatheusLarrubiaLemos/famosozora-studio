# Teste de ponta a ponta (lento, ~1 a 3 minutos, so no Windows):
#   video de amostra de 20 s (imagem de teste + voz do Windows falando em portugues)
#   -> transcrever (Whisper no PROCESSADOR, modelo "tiny") -> cortes.json falso (sem chamar o Claude)
#   -> gerar o Short -> editar a legenda e censurar uma palavra -> renderizar de novo so esse Short.
# Nao usa nenhum video de verdade. Roda o programa como se estivesse INSTALADO, numa pasta temporaria,
# e sem placa de video (como no notebook). Rodar: python -m pytest -m lento
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import RAIZ, TEMP

FALA = (
    "Fala galera, beleza? Hoje a gente vai jogar Bully no controle. "
    "A missão é tirar uma foto da diretora sem ninguém ver. "
    "Olha só, deu tudo errado, a bicicleta caiu e explodiu tudo. "
    "Inscreva-se no canal para ver o próximo episódio."
)

pytestmark = [pytest.mark.lento, pytest.mark.skipif(os.name != "nt", reason="usa a voz e a Lixeira do Windows")]


def _ffmpeg():
    for candidato in (RAIZ / "bin" / "ffmpeg.exe", shutil.which("ffmpeg")):
        if candidato and Path(candidato).exists():
            return Path(candidato)
    pytest.skip("ffmpeg nao encontrado (rode o .bat de desenvolvedor uma vez)")


@pytest.fixture(scope="module")
def ambiente():
    """Monta um "app instalado" numa pasta temporaria: codigo, ffmpeg, musicas e configuracoes proprias."""
    base = TEMP / "ponta_a_ponta"
    instalado = base / "programa"
    shutil.copytree(RAIZ / "app", instalado / "ferramentas", ignore=shutil.ignore_patterns("__pycache__"))
    (instalado / "ferramentas" / "APP_INSTALADO").write_text("teste", encoding="utf-8")
    shutil.copytree(RAIZ / "musicas", instalado / "musicas")
    (instalado / "bin").mkdir()
    ffmpeg = _ffmpeg()
    for nome in ("ffmpeg.exe", "ffprobe.exe"):
        shutil.copy2(ffmpeg.with_name(nome), instalado / "bin" / nome)

    dados_app = base / "localappdata" / "FamosoZora Studio"
    (dados_app / "configuracoes").mkdir(parents=True)
    trabalho = base / "trabalho"
    (dados_app / "ajustes.json").write_text(json.dumps({"pasta_trabalho": str(trabalho)}), encoding="utf-8")
    # como no notebook: sem placa de video, modelo pequeno, sem identificar vozes (evita baixar modelos)
    config = {"dispositivo": "cpu", "modelo_cpu": "tiny", "codificar_na_gpu": False, "cor_por_falante": False,
              "retranscrever_cortes": "false", "musica": "nenhuma"}  # fmt: skip
    (dados_app / "configuracoes" / "config.json").write_text(json.dumps(config), encoding="utf-8")
    ambiente = dict(os.environ, LOCALAPPDATA=str(base / "localappdata"), PYTHONIOENCODING="utf-8",
                    HF_HUB_DISABLE_SYMLINKS_WARNING="1")  # fmt: skip
    return {"base": base, "codigo": instalado / "ferramentas", "trabalho": trabalho, "env": ambiente,
            "ffmpeg": instalado / "bin" / "ffmpeg.exe"}  # fmt: skip


def _rodar(amb, *args, entrada=None):
    r = subprocess.run([sys.executable, "-m", *args], cwd=amb["codigo"], env=amb["env"], input=entrada,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)  # fmt: skip
    saida = r.stdout + r.stderr
    assert r.returncode == 0, saida[-3000:]
    assert "Traceback" not in saida and "[ERRO]" not in saida, saida[-3000:]
    return saida


def _video_de_amostra(amb) -> Path:
    """20 s: imagem de teste 1920x1080 + a voz do Windows lendo a FALA."""
    voz = amb["base"] / "voz.wav"
    script = (
        "Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$v = $s.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -eq 'pt-BR' } | Select-Object -First 1; "
        "if ($v) { $s.SelectVoice($v.VoiceInfo.Name) }; "
        f"$s.SetOutputToWaveFile('{voz}'); $s.Speak('{FALA}'); $s.Dispose()"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True, capture_output=True)
    video = amb["trabalho"] / "videos" / "amostra bully.mp4"
    video.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [str(amb["ffmpeg"]), "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
         "testsrc2=size=1920x1080:rate=30:duration=20", "-i", str(voz), "-filter_complex", "[1:a]apad[a]",
         "-map", "0:v", "-map", "[a]", "-t", "20", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac",
         "-shortest", str(video)],
        check=True,
    )  # fmt: skip
    return video


def _md5_video(amb, arquivo: Path) -> str:
    r = subprocess.run([str(amb["ffmpeg"]), "-hide_banner", "-loglevel", "error", "-i", str(arquivo), "-map", "0:v",
                        "-f", "md5", "-"], capture_output=True, text=True, check=True)  # fmt: skip
    return r.stdout.strip()


def test_do_video_ao_short_revisado(ambiente):
    amb = ambiente
    video = _video_de_amostra(amb)

    # 1) transcrever (processador)
    saida = _rodar(amb, "nucleo.transcrever", str(video))
    assert "Usando o PROCESSADOR" in saida
    projeto = amb["trabalho"] / "shorts" / "amostra bully"
    transcricao = json.loads((projeto / "transcricao.json").read_text(encoding="utf-8"))
    texto = " ".join(s["texto"] for s in transcricao["segmentos"]).lower()
    palavras = [w for s in transcricao["segmentos"] for w in s["palavras"]]
    assert len(palavras) > 20, texto
    assert any(p in texto for p in ("bully", "galera", "bicicleta", "inscreva")), texto
    assert (projeto / "transcricao_para_claude.txt").exists() and (projeto / "legenda_video_completo.srt").exists()

    # 2) cortes falsos, no formato v2 (sem chamar o Claude)
    cortes = {"versao": 2, "cortes": [{
        "inicio": round(palavras[3]["i"], 2), "fim": round(palavras[-5]["f"], 2), "titulo": "A bicicleta EXPLODIU",
        "abertura": {"inicio": round(palavras[-12]["i"], 2), "fim": round(palavras[-9]["f"], 2)},
        "youtube_titulo": "A bicicleta EXPLODIU no Bully", "tiktok": "teste #bully"}]}  # fmt: skip
    (projeto / "cortes.json").write_text(json.dumps(cortes, ensure_ascii=False), encoding="utf-8")

    # 3) gerar o Short (processador)
    saida = _rodar(amb, "shorts.gerar_shorts", str(projeto))
    assert "PROCESSADOR (x264)" in saida and "1 criado(s)" in saida
    short = projeto / "prontos" / "01 - A bicicleta EXPLODIU.mp4"
    assert short.exists() and short.stat().st_size > 50_000
    publicacao = json.loads((projeto / "prontos" / "publicacao.json").read_text(encoding="utf-8"))
    assert publicacao["shorts"][0]["textos"]["youtube"]["titulo"] == "A bicicleta EXPLODIU no Bully"
    original = json.loads((projeto / "legendas" / "01_original.json").read_text(encoding="utf-8"))
    assert len(original["palavras"]) > 10
    imagem_antes = _md5_video(amb, short)

    # 4) editar a legenda: troca a primeira palavra e censura a ultima (como no editor)
    editadas = [dict(w) for w in original["palavras"]]
    editadas[0]["p"] = "EDITADO"
    editadas[-1]["cx"] = True
    (projeto / "legendas" / "01_editada.json").write_text(
        json.dumps({"n": 1, "palavras": editadas, "censurar_lista": False}, ensure_ascii=False), encoding="utf-8"
    )

    # 5) renderizar de novo so esse Short (sem transcrever de novo nem chamar o Claude)
    saida = _rodar(amb, "shorts.gerar_shorts", str(projeto), "--so", "1")
    assert "usando a legenda revisada a mao" in saida and "1 criado(s)" in saida
    assert _md5_video(amb, short) != imagem_antes  # a legenda nova esta no video
    assert json.loads((projeto / "legendas" / "01_original.json").read_text(encoding="utf-8")) == original
    assert not list(projeto.glob("temp_legenda*.ass"))  # temporarios apagados
