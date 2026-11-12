# Mostra a versao do app (lida de app/versao.py). Usado pelo GitHub Actions.
import re
from pathlib import Path

texto = (Path(__file__).resolve().parent.parent / "app" / "versao.py").read_text(encoding="utf-8")
print(re.search(r'VERSAO\s*=\s*"([^"]+)"', texto).group(1))
