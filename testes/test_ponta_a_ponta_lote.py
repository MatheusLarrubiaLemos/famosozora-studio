# Teste de ponta a ponta do LOTE (lento, alguns minutos): 3 videos de amostra de 20 s feitos com o ffmpeg
# (imagem de teste + um tom), rodando o lote de verdade como se o programa estivesse INSTALADO, sem placa de video
# (como no notebook) e sem area da camera marcada:
#   - "video a": ainda nao transcrito  -> transcrever -> cortes (Claude falso) -> Shorts
#   - "video b": transcrito, sem cortes -> cortes (Claude falso) -> Shorts
#   - "video c": ja tem Shorts e foi escolhido "Gerar de novo" -> o Short antigo vai para a Lixeira -> Shorts novos
# Depois, um 4o video e cancelado no meio da geracao: nao pode sobrar arquivo quebrado.
# O Claude e sempre falso (nao gasta a assinatura). O Whisper e o de verdade (modelo "tiny") quando der para
# baixar o modelo; se nao der (sem internet), a transcricao e falsa e o resto continua de verdade.
# Rodar: python -m pytest -m lento testes/test_ponta_a_ponta_lote.py
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import RAIZ, TEMP

pytestmark = pytest.mark.lento

# roda DENTRO do programa "instalado" (outro processo): Claude falso e, se pedido, transcricao falsa
SCRIPT = r"""
import json, sys, threading, time
from pathlib import Path
from nucleo import claude_local
from nucleo.projetos import listar_projetos
from shorts import lote as L

def claude_falso(pedido, cancelar, modelo="", **k):
    return json.dumps({"versao": 3, "cortes": [
        {"inicio": "00:00:02", "fim": "00:00:09", "titulo": "Primeiro corte", "nota": 9},
        {"inicio": "00:00:11", "fim": "00:00:18", "titulo": "Segundo corte", "nota": 8}]})

claude_local.rodar_claude = claude_falso
etapas = L.Etapas()
if "--whisper-falso" in sys.argv:
    def transcrever_falso(v, cancelar, progresso):
        p = Path(v["pasta"])
        palavras = [{"i": 1.0 + k, "f": 1.6 + k, "p": f"palavra{k}"} for k in range(18)]
        (p / "transcricao.json").write_text(json.dumps({"segmentos": [
            {"inicio": 1.0, "fim": 18.6, "texto": " ".join(w["p"] for w in palavras), "palavras": palavras}]}))
        (p / "transcricao_para_claude.txt").write_text("[00:01-00:18] palavras de teste", encoding="utf-8")
    etapas.transcrever = transcrever_falso

infos = {i["nome"]: i for i in listar_projetos()}
if sys.argv[1] == "lote":
    lote = L.montar_lote([infos[n] for n in ("video a", "video b", "video c")], refazer={"video c": True})
    L.RodarLote(lote, etapas).rodar_aqui()
else:  # cancelar no meio da geracao dos Shorts do "video d"
    rodar = L.RodarLote(L.montar_lote([infos["video d"]]), etapas)
    rodar.iniciar()
    for _ in range(600):
        v = rodar.retrato()["videos"][0]
        if v["etapa"] == "renderizando" and list((Path(v["pasta"]) / "prontos").glob("_gerando_*.mp4")):
            break  # um Short esta pela metade agora
        time.sleep(0.1)
    rodar.cancelar()
    rodar.terminou.wait(60)
print("LOTE=" + json.dumps(L.carregar(), ensure_ascii=False))
"""


def _ffmpeg():
    for candidato in (RAIZ / "bin" / "ffmpeg.exe", shutil.which("ffmpeg")):
        if candidato and Path(candidato).exists():
            return Path(candidato)
    pytest.skip("ffmpeg nao encontrado (rode o .bat de desenvolvedor uma vez)")


@pytest.fixture(scope="module")
def amb():
    """Monta um "app instalado" numa pasta temporaria, com 4 videos de amostra e os projetos de cada um."""
    base = TEMP / "ponta_a_ponta_lote"
    shutil.rmtree(base, ignore_errors=True)
    instalado = base / "programa"
    shutil.copytree(RAIZ / "app", instalado / "ferramentas", ignore=shutil.ignore_patterns("__pycache__"))
    (instalado / "ferramentas" / "APP_INSTALADO").write_text("teste", encoding="utf-8")
    shutil.copytree(RAIZ / "musicas", instalado / "musicas")
    ffmpeg = _ffmpeg()
    if os.name == "nt":
        (instalado / "bin").mkdir()
        for nome in ("ffmpeg.exe", "ffprobe.exe"):
            shutil.copy2(ffmpeg.with_name(nome), instalado / "bin" / nome)
    dados_app = base / "localappdata" / "FamosoZora Studio"
    (dados_app / "configuracoes").mkdir(parents=True)
    trabalho = base / "trabalho"
    (dados_app / "ajustes.json").write_text(json.dumps({"pasta_trabalho": str(trabalho)}), encoding="utf-8")
    # como no notebook: sem placa de video e sem area da camera marcada (sai com o fundo desfocado)
    config = {"dispositivo": "cpu", "modelo_cpu": "tiny", "codificar_na_gpu": False, "cor_por_falante": False,
              "retranscrever_cortes": "false", "musica": "nenhuma", "layout": "camera", "camera_area": None}  # fmt: skip
    (dados_app / "configuracoes" / "config.json").write_text(json.dumps(config), encoding="utf-8")
    env = dict(os.environ, LOCALAPPDATA=str(base / "localappdata"), PYTHONIOENCODING="utf-8",
               HF_HUB_DISABLE_SYMLINKS_WARNING="1")  # fmt: skip
    env.pop("PYTEST_CURRENT_TEST", None)
    a = {"base": base, "codigo": instalado / "ferramentas", "trabalho": trabalho, "env": env, "ffmpeg": ffmpeg}
    for nome in ("video a", "video b", "video c", "video d"):
        _projeto(a, nome)
    return a


def _video(a, nome: str) -> Path:
    video = a["trabalho"] / "videos" / f"{nome}.mp4"
    video.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [str(a["ffmpeg"]), "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
         "testsrc2=size=1920x1080:rate=30:duration=20", "-f", "lavfi", "-i", "sine=frequency=440:duration=20",
         "-t", "20", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-shortest", str(video)],
        check=True,
    )  # fmt: skip
    return video


def _projeto(a, nome: str):
    """a: so o projeto.json; b: transcrito; c: transcrito, com cortes e 1 Short antigo; d: transcrito, com cortes."""
    video = _video(a, nome)
    p = a["trabalho"] / "shorts" / nome
    (p / "prontos").mkdir(parents=True)
    (p / "projeto.json").write_text(json.dumps({"video": str(video), "duracao": 20.0}), encoding="utf-8")
    if nome == "video a":
        return
    palavras = [{"i": 1.0 + k, "f": 1.6 + k, "p": f"palavra{k}"} for k in range(18)]
    (p / "transcricao.json").write_text(json.dumps({"segmentos": [
        {"inicio": 1.0, "fim": 18.6, "texto": " ".join(w["p"] for w in palavras), "palavras": palavras}]}))  # fmt: skip
    (p / "transcricao_para_claude.txt").write_text("[00:01-00:18] palavras de teste", encoding="utf-8")
    if nome in ("video c", "video d"):
        cortes = [{"inicio": "00:00:02", "fim": "00:00:09", "titulo": "Antigo um"},
                  {"inicio": "00:00:11", "fim": "00:00:18", "titulo": "Antigo dois"}]  # fmt: skip
        (p / "cortes.json").write_text(json.dumps({"versao": 3, "cortes": cortes}), encoding="utf-8")
    if nome == "video c":
        (p / "prontos" / "01 - Antigo um.mp4").write_bytes(b"short antigo")


def _whisper_disponivel(a) -> bool:
    r = subprocess.run([sys.executable, "-c", "from nucleo.whisper import _baixar_modelo as b; print(b('tiny'))"],
                       cwd=a["codigo"], env=a["env"], capture_output=True, text=True, timeout=600)  # fmt: skip
    return r.returncode == 0


def _rodar_script(a, *args) -> dict:
    r = subprocess.run([sys.executable, "-c", SCRIPT, *args], cwd=a["codigo"], env=a["env"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=1800)  # fmt: skip
    saida = r.stdout + r.stderr
    assert r.returncode == 0, saida[-3000:]
    linha = next((x for x in r.stdout.splitlines() if x.startswith("LOTE=")), None)
    assert linha, saida[-3000:]
    return json.loads(linha[5:])


def test_lote_de_3_videos_de_ponta_a_ponta(amb):
    extra = [] if _whisper_disponivel(amb) else ["--whisper-falso"]
    lote = _rodar_script(amb, "lote", *extra)
    etapas = {v["nome"]: (v["etapa"], v["erro"]) for v in lote["videos"]}
    assert etapas == {"video a": ("pronto", ""), "video b": ("pronto", ""), "video c": ("pronto", "")}, etapas
    assert lote["situacao"] == "terminado" and lote["versao"] == 1
    shorts = amb["trabalho"] / "shorts"
    for nome in ("video a", "video b", "video c"):
        p = shorts / nome
        prontos = sorted(f.name for f in (p / "prontos").glob("*.mp4"))
        assert prontos == ["01 - Primeiro corte.mp4", "02 - Segundo corte.mp4"] or (
            nome == "video c" and prontos == ["01 - Antigo um.mp4", "02 - Antigo dois.mp4"]
        ), (nome, prontos)
        assert all((p / "prontos" / f).stat().st_size > 20_000 for f in prontos), nome
        assert (p / "transcricao.json").exists() and (p / "cortes.json").exists(), nome
        assert (p / "prontos" / "publicacao.json").exists(), nome
        assert not list(p.rglob("_gerando_*")) and not list(p.glob("temp_legenda_*")), nome
    # o "video c" ja tinha cortes: foram mantidos; o Short antigo (falso, de 12 bytes) foi para a Lixeira
    antigo = shorts / "video c" / "prontos" / "01 - Antigo um.mp4"
    assert antigo.stat().st_size > 20_000
    assert lote["videos"][2]["lixeira_feita"] is True
    # cada projeto com os seus cortes: o "c" nao recebeu os cortes do Claude falso
    cortes_c = json.loads((shorts / "video c" / "cortes.json").read_text(encoding="utf-8"))
    assert cortes_c["cortes"][0]["titulo"] == "Antigo um"


def test_cancelar_no_meio_da_geracao_de_verdade(amb):
    lote = _rodar_script(amb, "cancelar")
    v = lote["videos"][0]
    assert lote["situacao"] == "cancelado" and v["etapa"] == "fila"
    p = amb["trabalho"] / "shorts" / "video d"
    assert not list(p.rglob("_gerando_*")) and not list(p.glob("temp_legenda_*"))
    for f in (p / "prontos").glob("*.mp4"):  # o que ficou pronto antes de cancelar e um video inteiro
        r = subprocess.run([str(amb["ffmpeg"]), "-v", "error", "-i", str(f), "-f", "null", "-"], capture_output=True)
        assert r.returncode == 0, f.name
