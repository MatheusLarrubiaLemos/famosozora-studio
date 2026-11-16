# Biblioteca de audio: as musicas de fundo (por clima) e os efeitos sonoros (por categoria).
# So usa o que voce colocar nas pastas (musica sem direitos autorais / licenciada): nada e baixado da internet.
#   musicas\<clima>\   engracado, epico, tenso, emocionante, calmo, caotico e geral (serve para qualquer clima)
#   efeitos\<categoria>\   risada, impacto, falha, suspense, vitoria, transicao (e outras que voce criar)
# Valem as pastas que vem com o programa (GitHub) e as deste PC (%LOCALAPPDATA%\FamosoZora Studio).
# Os arquivos sao guardados no projeto pelo caminho relativo, ex.: "epico/tema1.mp3" (funciona em outro PC).
import random
import shutil
from pathlib import Path

from nucleo.comum import (
    EXTENSOES_AUDIO,
    PASTA_EFEITOS,
    PASTA_EFEITOS_APP,
    PASTA_MUSICAS,
    PASTA_MUSICAS_APP,
    _sem_repetir,
)
from shorts.cortes import CLIMAS

GERAL = "geral"
CATEGORIAS_EFEITOS = ("risada", "impacto", "falha", "suspense", "vitoria", "transicao")

LEIA_ME_MUSICAS = """MUSICAS DE FUNDO DOS SHORTS (por clima)

Coloque aqui so musica que voce pode usar (sem direitos autorais ou licenciada, por exemplo a
Biblioteca de audio do YouTube Studio). O Studio NAO baixa nada da internet.

Uma pasta por clima do corte (o Claude escolhe o clima de cada corte):
  engracado\\   epico\\   tenso\\   emocionante\\   calmo\\   caotico\\
  geral\\  -> usada quando a pasta do clima estiver vazia

Formatos: .mp3 .m4a .wav .ogg .aac .flac
Sem nenhuma musica, o Short sai sem musica (e o Studio avisa).
"""

LEIA_ME_EFEITOS = """EFEITOS SONOROS DOS SHORTS (por categoria)

Coloque aqui so efeitos que voce pode usar (sem direitos autorais ou licenciados). O Studio NAO baixa
nada da internet. Uma pasta por categoria; o nome da pasta e o que o Claude ve:
  risada\\   impacto\\   falha\\   suspense\\   vitoria\\   transicao\\
Pode criar outras pastas (ex.: explosao\\). Pasta vazia nao aparece para o Claude.

Formatos: .mp3 .m4a .wav .ogg .aac .flac  -  de preferencia curtos (ate uns 3 segundos).
"""


def _bases(tipo: str) -> list:
    """Pastas onde procurar: primeiro a do programa, depois a deste PC (que vale por cima)."""
    if tipo == "musica":
        return _sem_repetir(PASTA_MUSICAS_APP, PASTA_MUSICAS)
    return _sem_repetir(PASTA_EFEITOS_APP, PASTA_EFEITOS)


def _pasta_deste_pc(tipo: str) -> Path:
    return PASTA_MUSICAS if tipo == "musica" else PASTA_EFEITOS


def preparar_pastas():
    """Cria as subpastas e o LEIA-ME.txt, e copia as musicas soltas (de antes da 1.4.0) para geral\\.
    Copia sem apagar: a musica solta continua onde estava."""
    for tipo, nomes, leia_me in (("musica", (*CLIMAS, GERAL), LEIA_ME_MUSICAS),
                                 ("efeito", CATEGORIAS_EFEITOS, LEIA_ME_EFEITOS)):  # fmt: skip
        base = _pasta_deste_pc(tipo)
        try:
            for nome in nomes:
                (base / nome).mkdir(parents=True, exist_ok=True)
            if not (base / "LEIA-ME.txt").exists():
                (base / "LEIA-ME.txt").write_text(leia_me, encoding="utf-8")
            if tipo == "musica":
                for m in base.iterdir():
                    destino = base / GERAL / m.name
                    if m.is_file() and m.suffix.lower() in EXTENSOES_AUDIO and not destino.exists():
                        shutil.copy2(m, destino)
        except OSError as e:  # pasta sem permissao: segue sem as pastas novas
            print(f"[AVISO] nao consegui preparar {base}: {e}")


def listar(tipo: str) -> dict:
    """{categoria: {"epico/tema1.mp3": Path, ...}} de musicas ("musica") ou efeitos ("efeito").
    Musica solta na pasta (de antes da 1.4.0) conta como geral."""
    achados = {}
    for base in _bases(tipo):
        if not base.exists():
            continue
        for item in sorted(base.iterdir()):
            if item.is_dir():
                arquivos = [(item.name.lower(), f) for f in sorted(item.iterdir())]
            elif tipo == "musica":
                arquivos = [(GERAL, item)]
            else:
                continue
            for cat, f in arquivos:
                if f.is_file() and f.suffix.lower() in EXTENSOES_AUDIO:
                    rel = f"{cat}/{f.name}"
                    achados.setdefault(cat, {})
                    # a mesma musica solta e em geral\ (copiada na migracao) conta uma vez so
                    achados[cat][rel.lower()] = (rel, f)
    return {cat: {rel: f for rel, f in sorted(v.values(), key=lambda x: x[0].lower())} for cat, v in achados.items()}


def categorias_com_arquivos(tipo: str = "efeito") -> list:
    return sorted(cat for cat, arquivos in listar(tipo).items() if arquivos)


def caminho(tipo: str, rel: str):
    """'epico/tema1.mp3' -> o arquivo (o deste PC primeiro). None se nao existe mais."""
    if not rel:
        return None
    rel = rel.replace("\\", "/")
    for base in reversed(_bases(tipo)):
        f = base / rel
        if f.is_file():
            return f
    cat, _, nome = rel.partition("/")
    if tipo == "musica" and cat == GERAL:  # musica solta de antes da 1.4.0
        for base in reversed(_bases(tipo)):
            if (base / nome).is_file():
                return base / nome
    return None


def opcoes_de_musica(clima: str) -> list:
    """Musicas para o clima: as da pasta do clima; se ela estiver vazia, as de geral."""
    todas = listar("musica")
    return list((todas.get(clima) or todas.get(GERAL) or {}).keys())


def achar_musica_por_nome(nome: str):
    """Musica pedida pelo nome (o campo "musica" do corte ou do config): 'tema1', 'tema1.mp3' ou 'epico/tema1.mp3'."""
    alvo = str(nome or "").strip().replace("\\", "/").lower()
    for arquivos in listar("musica").values():
        for rel in arquivos:
            arquivo = rel.split("/", 1)[1].lower()
            if alvo in (rel.lower(), arquivo, arquivo.rsplit(".", 1)[0]):
                return rel
    return None


def sortear(opcoes: list, semente: str, evitar=()) -> str:
    """Sorteia uma opcao (sempre a mesma para a mesma semente), evitando as de 'evitar' se der."""
    if not opcoes:
        return ""
    livres = [o for o in opcoes if o not in evitar] or list(opcoes)
    return random.Random(semente).choice(livres)


def planejar_musicas(cortes: list, climas: list, semente: str, escolha_cfg: str) -> dict:
    """Musica de cada Short {n: "epico/tema1.mp3" ou ""}, sem repetir a do Short anterior se houver outra.
    escolha_cfg = "aleatoria" (por clima), o nome de uma musica, ou "nenhuma"."""
    escolha_cfg = str(escolha_cfg or "aleatoria").strip()
    sem = ("", "nenhuma", "sem", "false", "off", "nao", "não")
    plano, anterior, usadas = {}, "", {}
    for n, (c, clima) in enumerate(zip(cortes, climas), 1):
        pedida = str((c or {}).get("musica") or "").strip() if isinstance(c, dict) else ""
        if pedida.lower() in sem[1:]:
            plano[n] = ""
            continue
        if pedida or escolha_cfg.lower() not in ("aleatoria", *sem):
            nome = pedida or escolha_cfg
            rel = achar_musica_por_nome(nome)
            if not rel:
                print(f"   [AVISO] musica '{nome}' nao encontrada; usando uma do clima.")
            else:
                plano[n] = anterior = rel
                continue
        elif escolha_cfg.lower() in sem:
            plano[n] = ""
            continue
        opcoes = opcoes_de_musica(clima)
        # nao repete a do Short anterior e, se der, nem as ja usadas neste projeto
        ja = usadas.get(tuple(opcoes), [])
        evitar = set(ja) | {anterior} if len(set(ja) | {anterior}) < len(opcoes) else {anterior}
        rel = sortear(opcoes, f"{semente}-{n}", evitar)
        usadas.setdefault(tuple(opcoes), []).append(rel)
        plano[n] = anterior = rel
    return plano
