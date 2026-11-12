# Pega do CHANGELOG.md so a parte de uma versao (vira o texto do Release no GitHub).
# Uso: python build/notas_da_versao.py 1.0.0 > notas.md
import re
import sys
from pathlib import Path

versao = sys.argv[1]
texto = (Path(__file__).resolve().parent.parent / "CHANGELOG.md").read_text(encoding="utf-8")
partes = re.split(r"(?m)^## ", texto)
for p in partes[1:]:
    if re.match(rf"\[?v?{re.escape(versao)}\]?\b", p):
        corpo = p.split("\n", 1)[1].strip() if "\n" in p else ""
        sys.stdout.reconfigure(encoding="utf-8")
        print(corpo + "\n\n---\nComo instalar: baixe o `FamosoZora-Studio-Setup-" + versao + ".exe` abaixo e abra. "
              "Se o Windows avisar \"O Windows protegeu o computador\", clique em **Mais informações → Executar assim mesmo**.")
        break
else:
    sys.exit(f"Versao {versao} nao encontrada no CHANGELOG.md")
