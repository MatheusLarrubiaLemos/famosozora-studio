# Registro (log): guarda os erros num arquivo para dar para descobrir o que aconteceu depois.
# Fica em %LOCALAPPDATA%\\FamosoZora Studio\\logs\\studio.log (um por PC, fora do GitHub).
import traceback
from datetime import datetime

from nucleo.comum import DADOS_APP

ARQ_LOG = DADOS_APP / "logs" / "studio.log"
TAMANHO_MAXIMO = 1_000_000  # 1 MB: passou disso, o arquivo antigo vira studio.log.antigo


def registrar(mensagem: str, erro: BaseException | None = None):
    """Escreve uma linha no log. Nunca da erro: se nao conseguir gravar, simplesmente nao grava."""
    try:
        ARQ_LOG.parent.mkdir(parents=True, exist_ok=True)
        if ARQ_LOG.exists() and ARQ_LOG.stat().st_size > TAMANHO_MAXIMO:
            ARQ_LOG.replace(ARQ_LOG.with_name("studio.log.antigo"))
        linhas = [f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {mensagem}"]
        if erro is not None:
            linhas.append("".join(traceback.format_exception(type(erro), erro, erro.__traceback__)).rstrip())
        with open(ARQ_LOG, "a", encoding="utf-8") as f:
            f.write("\n".join(linhas) + "\n")
    except Exception:
        pass
