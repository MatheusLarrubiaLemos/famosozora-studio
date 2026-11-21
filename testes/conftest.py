# Preparacao dos testes: antes de abrir qualquer parte do Studio, troca a pasta do app
# (%LOCALAPPDATA%\FamosoZora Studio) e a pasta de trabalho por pastas temporarias.
# Assim os testes nunca mexem nos seus videos, projetos, ajustes ou configuracoes de verdade.
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
TEMP = Path(tempfile.mkdtemp(prefix="famosozora_testes_"))
os.environ["LOCALAPPDATA"] = str(TEMP / "localappdata")
PASTA_TRABALHO = TEMP / "pasta_de_trabalho"
(TEMP / "localappdata" / "FamosoZora Studio").mkdir(parents=True)
(TEMP / "localappdata" / "FamosoZora Studio" / "ajustes.json").write_text(
    json.dumps({"pasta_trabalho": str(PASTA_TRABALHO), "ultima_versao_vista": "teste", "perguntou_gpu": True}),
    encoding="utf-8",
)
sys.path.insert(0, str(RAIZ / "app"))
# as telas usam o jeito antigo (sem o player embutido): os testes do player ligam ele de proposito
os.environ.setdefault("FAMOSOZORA_SEM_PLAYER", "1")


def pytest_configure(config):
    config.addinivalue_line("markers", "lento: teste demorado (usa ffmpeg e Whisper; rode com -m lento)")


@pytest.fixture
def pasta_temp(tmp_path):
    return tmp_path


@pytest.fixture
def config_temporaria(tmp_path, monkeypatch):
    """Faz as listas (correcoes, censura) deste "PC" ficarem numa pasta temporaria."""
    from nucleo import comum
    from shorts import censura, revisao

    pasta = tmp_path / "configuracoes"
    pasta.mkdir()
    for modulo in (comum, censura, revisao):
        monkeypatch.setattr(modulo, "PASTA_CONFIG", pasta)
    return pasta
