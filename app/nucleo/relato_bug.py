# Relato de bug: monta o texto de um bug reportado pelo app (botao direito > "Reportar bug" em qualquer tela).
# Junta sozinho o contexto que ajuda a achar o problema: versao, Windows, tela aberta, videos selecionados,
# janelas abertas, os ultimos cliques (a "trilha"), os ultimos erros e o fim do registro (studio.log).
# O relato e guardado num arquivo em %LOCALAPPDATA%\FamosoZora Studio\bugs e vira uma "issue" no GitHub
# (o navegador abre com tudo preenchido; e so clicar em enviar). Antes de cada versao nova, o Claude le
# essas issues e corrige o que der (ver CLAUDE.md).
import os
import platform
import re
import urllib.parse
from collections import deque
from datetime import datetime
from pathlib import Path

from nucleo.comum import DADOS_APP, REPO_URL
from nucleo.registro import ARQ_LOG
from versao import VERSAO

PASTA_BUGS = DADOS_APP / "bugs"
ETIQUETA = "bug-do-app"  # etiqueta das issues que vem do app (o Claude procura por ela)
MARCA = "<!-- relato-do-app: bug-do-app -->"  # vai no texto tambem: acha a issue mesmo se a etiqueta nao existir
LINHAS_DO_LOG = 60
TAMANHO_MAXIMO_URL = 7500  # o navegador/GitHub nao aceita endereco muito grande: o resto fica so no arquivo

# ultimos cliques e trocas de tela (so na memoria; some quando fecha o Studio)
trilha = deque(maxlen=40)
# ultimos erros que aconteceram na tela (o texto do erro completo)
erros_recentes = deque(maxlen=5)


def anotar(acao: str):
    """Guarda uma acao na trilha (ex.: 'clicou em "Publicar os Shorts prontos"')."""
    acao = " ".join(str(acao).split())[:160]
    if acao and (not trilha or trilha[-1][1] != acao):
        trilha.append((datetime.now().strftime("%H:%M:%S"), acao))


def anotar_erro(texto: str):
    erros_recentes.append((datetime.now().strftime("%H:%M:%S"), str(texto).strip()[-4000:]))


# coisas com cara de senha/chave: tokens do GitHub, Google, Anthropic/OpenAI, "Bearer ...", "senha=..." etc.
_SEGREDOS = [
    re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{16,}|AIza[0-9A-Za-z_-]{30,}"
               r"|ya29\.[0-9A-Za-z_.-]{20,}|xox[abpr]-[0-9A-Za-z-]{10,})"),  # fmt: skip
    re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\b(senha|password|passwd|pwd|token|api[_-]?key|secret|chave|access_token|refresh_token|cookie)"
               r"(\s*[=:]\s*)[\"']?[^\s\"'&,;]+"),  # fmt: skip
]
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def sem_dados_pessoais(texto: str) -> str:
    """O repositorio e PUBLICO: nada pessoal pode ir no relato. Troca a pasta do usuario (que tem o nome dele
    no Windows) por %USERPROFILE%, o nome de usuario e do computador, e-mails e qualquer coisa com cara de
    senha ou chave."""
    casa = str(Path.home())
    for variante in {casa, casa.replace("\\", "/"), casa.replace("/", "\\")}:
        if len(variante) > 3:
            texto = texto.replace(variante, "%USERPROFILE%")
    pc = os.environ.get("COMPUTERNAME") or ""
    if len(pc) >= 3:
        texto = re.sub(rf"(?i)(?<![A-Za-z0-9]){re.escape(pc)}(?![A-Za-z0-9])", "%COMPUTERNAME%", texto)
    nome = os.environ.get("USERNAME") or os.environ.get("USER") or ""
    if len(nome) >= 3:
        texto = re.sub(rf"(?i)(?<![A-Za-z0-9]){re.escape(nome)}(?![A-Za-z0-9])", "%USERNAME%", texto)
    texto = _EMAIL.sub("[e-mail escondido]", texto)
    texto = _SEGREDOS[2].sub(lambda m: f"{m.group(1)}{m.group(2)}[escondido]", texto)
    texto = _SEGREDOS[1].sub(lambda m: f"{m.group(1)} [chave escondida]", texto)
    texto = _SEGREDOS[0].sub("[chave escondida]", texto)
    return texto


def fim_do_log(linhas: int = LINHAS_DO_LOG) -> str:
    try:
        return "\n".join(ARQ_LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-linhas:])
    except OSError:
        return ""


def montar_texto(descricao: str, contexto: dict, incluir_log: bool = True, linhas_log: int = LINHAS_DO_LOG,
                 cliques: int = 40, com_erros: bool = True) -> str:  # fmt: skip
    """O relato em Markdown (o mesmo texto vai para o arquivo e para a issue)."""
    partes = [MARCA, "## O que aconteceu", descricao.strip() or "(sem descrição)", "", "## Contexto"]
    partes.append(f"- Versão: {VERSAO}")
    partes.append(f"- Sistema: {platform.system()} {platform.release()} ({platform.version()})")
    partes.append(f"- Quando: {datetime.now():%d/%m/%Y %H:%M:%S}")
    for chave, valor in contexto.items():
        if isinstance(valor, list):
            partes.append(f"- {chave}:" + ("" if valor else " nenhum"))
            partes += [f"  - {v}" for v in valor]
        else:
            partes.append(f"- {chave}: {valor}")
    if cliques and trilha:
        partes += ["", "## Últimos cliques", *[f"- {h}  {a}" for h, a in list(trilha)[-cliques:]]]
    if com_erros and erros_recentes:
        partes += ["", "## Erros recentes na tela"]
        for h, texto in erros_recentes:
            partes += [f"{h}", "```", texto, "```"]
    if incluir_log and linhas_log:
        log = fim_do_log(linhas_log)
        if log:
            partes += ["", f"## Fim do registro (studio.log, últimas {linhas_log} linhas)", "```", log, "```"]
    return sem_dados_pessoais("\n".join(partes) + "\n")


def titulo_do_relato(descricao: str) -> str:
    primeira = next((linha.strip() for linha in descricao.splitlines() if linha.strip()), "Bug reportado pelo app")
    return sem_dados_pessoais(f"[{VERSAO}] {primeira[:90]}")


def salvar(titulo: str, texto: str):
    """Guarda o relato completo num arquivo .md. Devolve o caminho (ou None se nao conseguiu)."""
    try:
        PASTA_BUGS.mkdir(parents=True, exist_ok=True)
        arq = PASTA_BUGS / f"{datetime.now():%Y-%m-%d_%H%M%S}.md"
        arq.write_text(f"# {titulo}\n\n{texto}", encoding="utf-8")
        return arq
    except OSError:
        return None


def endereco_da_issue(titulo: str, texto: str) -> str:
    return f"{REPO_URL}/issues/new?" + urllib.parse.urlencode({"title": titulo, "body": texto, "labels": ETIQUETA})


def endereco_que_cabe(descricao: str, contexto: dict, incluir_log: bool = True) -> str:
    """O endereco da issue, cortando o log, os cliques e os erros ate caber (o arquivo guarda tudo)."""
    titulo = titulo_do_relato(descricao)
    tentativas = [(LINHAS_DO_LOG, 40, True), (30, 25, True), (15, 15, True), (0, 10, True), (0, 0, False)]
    for linhas, cliques, erros in tentativas:
        texto = montar_texto(descricao, contexto, incluir_log, linhas, cliques, erros)
        url = endereco_da_issue(titulo, texto)
        if len(url) <= TAMANHO_MAXIMO_URL:
            return url
    aviso = "\n\n_(o relato completo ficou grande demais: o resto está no arquivo salvo no PC)_\n"
    corte = len(descricao)
    while corte > 200:
        corte = int(corte * 0.7)
        url = endereco_da_issue(titulo, montar_texto(descricao[:corte] + aviso, contexto, False, 0, 0, False))
        if len(url) <= TAMANHO_MAXIMO_URL:
            return url
    return endereco_da_issue(titulo, descricao[:200] + aviso)
