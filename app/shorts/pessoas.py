# Pessoas e cores da legenda: o cadastro global (pessoas.json) e, em cada projeto, qual voz detectada
# e de qual pessoa (falantes.json). Regra: voz sem pessoa = a pessoa "padrao" (FamosoZora, branco).
#   cadastro (vale para todos os projetos):  app\padrao\pessoas.json  ou, no app instalado,
#                                            %LOCALAPPDATA%\FamosoZora Studio\configuracoes\pessoas.json
#   por projeto:                             <projeto>\falantes.json  {"shorts": {"01": {"0": "Pedro"}},
#                                                                     "trechos": {"01": [inicio, fim]}}
#   (o trecho diz de qual corte e a ligacao: com cortes novos, o Short 01 vira outro trecho e ela nao vale mais)
# A voz e ligada Short por Short porque o detector de vozes roda em cada corte separado
# (a "voz 0" de um Short pode ser outra pessoa no Short seguinte).
import re
from pathlib import Path

from nucleo.comum import PASTA_CONFIG, PASTA_PADRAO, PASTA_SHORTS, gravar_json, ler_json

NOME_PADRAO = "FamosoZora"
COR_PADRAO = "#FFFFFF"


# ------------------------------------------------------------------ cores
def cor_valida(cor) -> str:
    """'#ffffff', 'ffffff' ou '#fff' -> '#FFFFFF'. Cor invalida vira branco."""
    c = str(cor or "").strip().lstrip("#")
    if re.fullmatch(r"[0-9a-fA-F]{3}", c):
        c = "".join(x * 2 for x in c)
    return f"#{c.upper()}" if re.fullmatch(r"[0-9a-fA-F]{6}", c) else COR_PADRAO


def cor_ass(cor) -> str:
    """Cor do jeito da legenda .ass: '#RRGGBB' -> '&HBBGGRR&'."""
    c = cor_valida(cor)[1:]
    return f"&H{c[4:6]}{c[2:4]}{c[0:2]}&"


def contraste_com_preto(cor) -> float:
    """Quanto a cor se destaca da borda preta da legenda (1 = nada, 21 = branco)."""

    def canal(x):
        x = x / 255
        return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4

    c = cor_valida(cor)[1:]
    r, g, b = (canal(int(c[k : k + 2], 16)) for k in (0, 2, 4))
    luz = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return (luz + 0.05) / 0.05


def dificil_de_ler(cor) -> bool:
    return contraste_com_preto(cor) < 4.5


# ------------------------------------------------------------------ cadastro de pessoas
def arq_pessoas() -> Path:
    return PASTA_CONFIG / "pessoas.json"


def _limpar(lista) -> list:
    """Tira repetidas e sem nome, arruma as cores e garante exatamente uma pessoa padrao."""
    out, vistos = [], set()
    for p in lista if isinstance(lista, list) else []:
        nome = str((p or {}).get("nome", "")).strip() if isinstance(p, dict) else ""
        if not nome or nome.lower() in vistos:
            continue
        vistos.add(nome.lower())
        out.append({"nome": nome, "cor": cor_valida(p.get("cor")), "padrao": bool(p.get("padrao"))})
    if not out:
        out = [{"nome": NOME_PADRAO, "cor": COR_PADRAO, "padrao": True}]
    padroes = [p for p in out if p["padrao"]]
    for p in out:
        p["padrao"] = False
    (padroes[0] if padroes else out[0])["padrao"] = True
    return out


def ler_pessoas() -> list:
    """O cadastro deste PC; se ainda nao existe, o que vem com o programa."""
    for arq in (arq_pessoas(), PASTA_PADRAO / "pessoas.json"):
        dados = ler_json(arq, None)
        if isinstance(dados, dict) and isinstance(dados.get("pessoas"), list):
            return _limpar(dados["pessoas"])
    return _limpar([])


def salvar_pessoas(lista: list):
    arq_pessoas().parent.mkdir(parents=True, exist_ok=True)
    gravar_json(arq_pessoas(), {"versao": 1, "pessoas": _limpar(lista)})


def pessoa_padrao(lista=None) -> dict:
    lista = lista if lista is not None else ler_pessoas()
    return next(p for p in lista if p["padrao"])


def achar(nome, lista=None):
    lista = lista if lista is not None else ler_pessoas()
    nome = str(nome or "").strip().lower()
    return next((p for p in lista if p["nome"].lower() == nome), None)


def adicionar(nome: str, cor: str = COR_PADRAO) -> dict:
    nome = str(nome or "").strip()
    if not nome:
        raise ValueError("A pessoa precisa de um nome.")
    lista = ler_pessoas()
    if achar(nome, lista):
        raise ValueError(f'Já existe uma pessoa chamada "{nome}".')
    lista.append({"nome": nome, "cor": cor_valida(cor), "padrao": False})
    salvar_pessoas(lista)
    return achar(nome, ler_pessoas())


def mudar_cor(nome: str, cor: str):
    lista = ler_pessoas()
    p = achar(nome, lista)
    if not p:
        raise ValueError(f'Não achei a pessoa "{nome}".')
    p["cor"] = cor_valida(cor)
    salvar_pessoas(lista)


def definir_padrao(nome: str):
    """Quem fica com as falas que nao foram ligadas a ninguem."""
    lista = ler_pessoas()
    p = achar(nome, lista)
    if not p:
        raise ValueError(f'Não achei a pessoa "{nome}".')
    for x in lista:
        x["padrao"] = x is p
    salvar_pessoas(lista)


def excluir(nome: str):
    """A pessoa padrao nao pode ser excluida. As falas da pessoa excluida voltam para a padrao."""
    lista = ler_pessoas()
    p = achar(nome, lista)
    if not p:
        return
    if p["padrao"]:
        raise ValueError(f'"{p["nome"]}" é a pessoa padrão e não pode ser excluída.')
    salvar_pessoas([x for x in lista if x is not p])


def renomear(antigo: str, novo: str, pasta_shorts: Path | None = None) -> int:
    """Troca o nome no cadastro e nos projetos (falantes.json e legendas editadas). Devolve quantos arquivos mudaram."""
    novo = str(novo or "").strip()
    lista = ler_pessoas()
    p = achar(antigo, lista)
    if not p:
        raise ValueError(f'Não achei a pessoa "{antigo}".')
    if not novo:
        raise ValueError("O nome novo não pode ficar vazio.")
    outra = achar(novo, lista)
    if outra and outra is not p:
        raise ValueError(f'Já existe uma pessoa chamada "{novo}".')
    velho = p["nome"]
    p["nome"] = novo
    salvar_pessoas(lista)
    return _renomear_nos_projetos(velho, novo, pasta_shorts or PASTA_SHORTS)


def _renomear_nos_projetos(velho: str, novo: str, pasta_shorts: Path) -> int:
    mudou = 0
    if not pasta_shorts.exists():
        return 0
    for proj in pasta_shorts.iterdir():
        arq = proj / "falantes.json"
        dados = ler_json(arq, None)
        if isinstance(dados, dict) and isinstance(dados.get("shorts"), dict):
            trocou = False
            for vozes in dados["shorts"].values():
                for voz, nome in list(vozes.items()):
                    if str(nome).lower() == velho.lower():
                        vozes[voz] = novo
                        trocou = True
            if trocou:
                gravar_json(arq, dados)
                mudou += 1
        for leg in (proj / "legendas").glob("*_editada.json") if (proj / "legendas").exists() else []:
            dados = ler_json(leg, None)
            if not isinstance(dados, dict):
                continue
            trocou = False
            for w in dados.get("palavras", []):
                if str(w.get("pessoa", "")).lower() == velho.lower():
                    w["pessoa"] = novo
                    trocou = True
            if trocou:
                gravar_json(leg, dados)
                mudou += 1
    return mudou


# ------------------------------------------------------------------ vozes do projeto (falantes.json)
def arq_falantes(pasta: Path) -> Path:
    return pasta / "falantes.json"


def ler_ligacoes(pasta: Path, n: int, ini=None, fim=None) -> dict:
    """{"0": "Pedro", "a1": "Ana"}: voz detectada -> nome da pessoa, so do Short n.
    Com ini/fim (o trecho do corte): se a ligacao foi feita em outro trecho (cortes novos), devolve {}."""
    dados = ler_json(arq_falantes(pasta), {}) or {}
    if not isinstance(dados, dict):
        return {}
    vozes = (dados.get("shorts") or {}).get(f"{n:02d}", {})
    trecho = (dados.get("trechos") or {}).get(f"{n:02d}") if isinstance(dados.get("trechos"), dict) else None
    if ini is not None and fim is not None and isinstance(trecho, list) and len(trecho) == 2:
        try:
            if abs(float(trecho[0]) - float(ini)) >= 0.05 or abs(float(trecho[1]) - float(fim)) >= 0.05:
                return {}
        except (TypeError, ValueError):
            return {}
    return {str(k): str(v) for k, v in vozes.items()} if isinstance(vozes, dict) else {}


def salvar_ligacoes(pasta: Path, n: int, ligacoes: dict, ini=None, fim=None):
    """Grava as ligacoes voz -> pessoa do Short n (com o trecho do corte, quando ele e conhecido)."""
    dados = ler_json(arq_falantes(pasta), {}) or {}
    if not isinstance(dados, dict) or not isinstance(dados.get("shorts"), dict):
        dados = {"versao": 1, "shorts": {}}
    if not isinstance(dados.get("trechos"), dict):
        dados["trechos"] = {}
    chave = f"{n:02d}"
    limpas = {str(k): str(v) for k, v in ligacoes.items() if v}
    if limpas:
        dados["shorts"][chave] = limpas
        if ini is not None and fim is not None:
            dados["trechos"][chave] = [round(float(ini), 3), round(float(fim), 3)]
    else:
        dados["shorts"].pop(chave, None)
        dados["trechos"].pop(chave, None)
    gravar_json(arq_falantes(pasta), dados)


def chave_voz(w: dict):
    """Quem fala nesta palavra, para quebrar a legenda: a pessoa escolhida a mao ou a voz detectada."""
    return ("p", w["pessoa"].lower()) if w.get("pessoa") else ("s", w.get("s"))


class QuemFala:
    """Diz quem fala em cada palavra: a pessoa escolhida na linha, senao a ligada a voz, senao a padrao."""

    def __init__(self, ligacoes: dict | None = None, lista: list | None = None):
        self.lista = lista if lista is not None else ler_pessoas()
        self.padrao = pessoa_padrao(self.lista)
        self.ligacoes = ligacoes or {}

    def nome_escolhido(self, w: dict) -> str:
        if w.get("pessoa"):
            return w["pessoa"]
        return self.ligacoes.get(str(w["s"]), "") if "s" in w else ""

    def pessoa(self, w: dict) -> dict:
        return achar(self.nome_escolhido(w), self.lista) or self.padrao

    def eh_padrao(self, w: dict) -> bool:
        return self.pessoa(w) is self.padrao


def quem_fala(pasta: Path, n: int, ini=None, fim=None) -> QuemFala:
    return QuemFala(ler_ligacoes(pasta, n, ini, fim))
