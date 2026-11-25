# Episodio pela metade: o "Gerar o episodio" guarda cada pedaco pronto em episodio\_temp\episodio (plano.json +
# feitas.json). Se o Studio fechou (ou o PC desligou) no meio, ao abrir de novo o Studio usa isto para perguntar se
# quer continuar de onde parou. Rodar o "Gerar o episodio" de novo ja continua sozinho (editar_episodio.py).
from pathlib import Path

from nucleo.comum import ler_json


def pasta_temp(pasta_projeto: Path) -> Path:
    return Path(pasta_projeto) / "episodio" / "_temp" / "episodio"


def pela_metade(pasta_projeto: Path) -> tuple | None:
    """(pedacos prontos, total de pedacos) se o episodio deste projeto ficou pela metade; senao None."""
    temp = pasta_temp(pasta_projeto)
    plano = ler_json(temp / "plano.json", None)
    if not isinstance(plano, dict) or not plano.get("partes"):
        return None
    total = len(plano["partes"])
    feitas = ler_json(temp / "feitas.json", []) or []
    prontos = sum(1 for k in feitas if (temp / f"parte_{int(k):04d}.mp4").exists())
    return prontos, total


def marca(pasta_projeto: Path) -> str:
    """Identifica ESTA vez que ficou pela metade (para nao perguntar de novo se a pessoa disse "agora nao")."""
    arq = pasta_temp(pasta_projeto) / "plano.json"
    try:
        return f"{Path(pasta_projeto).name}|{arq.stat().st_mtime_ns}"
    except OSError:
        return ""
