# Pedir ao Claude com um clique, sem copiar e colar: usa o Claude Code instalado no PC no modo sem janela
# ("claude -p"), com a sua assinatura. Manda o pedido + a transcricao e recebe o JSON de volta.
# - Live grande demais para um pedido so: divide a transcricao em partes e junta as respostas.
# - Erro de rede (ou o Claude Code falhou): tenta de novo sozinho, ate 3 vezes.
# - JSON quebrado ou com tempos errados: pede de novo UMA vez, explicando o erro; se vier errado de novo, avisa.
# - Da para cancelar a qualquer momento (o processo do Claude e fechado).
# - Live dividida em partes: as partes sao pedidas AO MESMO TEMPO (2 por padrao; "claude_pedidos_simultaneos"
#   no config.json; 1 = uma de cada vez). Se uma parte der erro, as outras param.
import json
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from publicacao import claude_pc

TENTATIVAS = 3
ESPERA_ENTRE_TENTATIVAS = (5, 20)  # segundos antes da 2a e da 3a tentativa
LIMITE_PARTE = 250_000  # caracteres de transcricao por pedido (uma live de ~3 h cabe num pedido so)
TEMPO_MAXIMO = 30 * 60  # um pedido nao pode passar de 30 minutos
SEM_JANELA = getattr(subprocess, "CREATE_NO_WINDOW", 0)
SIMULTANEOS = 2  # partes pedidas ao Claude ao mesmo tempo (padrao)


class Cancelado(Exception):
    """Voce apertou Cancelar."""


class ErroClaude(Exception):
    """Algo deu errado conversando com o Claude. A mensagem ja vem em portugues simples."""


def disponivel() -> bool:
    return claude_pc.achar_claude_code() is not None


def comando(claude: str, modelo: str = "", ler_pasta=None) -> list:
    """claude -p, resposta em JSON, SEM ferramentas (ele so le o pedido e responde) e sem guardar a conversa.
    ler_pasta = pasta com imagens para ele olhar (Auto-Edit): libera SO a ferramenta Read, so nessa pasta.
    O pedido vai pela entrada do programa, por isso as opcoes de varios valores (--add-dir) podem ficar no fim."""
    if ler_pasta:
        cmd = [claude, "-p", "--output-format", "json", "--tools", "Read", "--no-session-persistence"]
    else:
        cmd = [claude, "-p", "--output-format", "json", "--tools", "", "--no-session-persistence"]
    if modelo:
        cmd += ["--model", modelo]
    if ler_pasta:
        cmd += ["--allowedTools", "Read", "--add-dir", str(ler_pasta)]
    return cmd


def rodar_claude(pedido: str, cancelar: threading.Event, modelo: str = "", tempo_maximo: float = TEMPO_MAXIMO,
                 ler_pasta=None) -> str:  # fmt: skip
    """Manda o pedido (pela entrada do programa, sem limite de tamanho) e devolve o texto da resposta."""
    claude = claude_pc.achar_claude_code()
    if not claude:
        raise ErroClaude("Não achei o Claude Code neste computador.")
    try:
        proc = subprocess.Popen(comando(claude, modelo, ler_pasta), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
                                creationflags=SEM_JANELA)  # fmt: skip
    except OSError as e:
        raise ErroClaude(f"Não consegui abrir o Claude Code ({e}).") from e
    caixa = {}
    leitor = threading.Thread(target=lambda: caixa.update(saida=proc.communicate(pedido)), daemon=True)
    leitor.start()
    inicio = time.monotonic()
    while leitor.is_alive():
        if cancelar.is_set() or time.monotonic() - inicio > tempo_maximo:
            proc.kill()
            leitor.join(5)
            if cancelar.is_set():
                raise Cancelado()
            raise ErroClaude(f"O Claude demorou mais de {tempo_maximo // 60:.0f} minutos e eu parei.")
        leitor.join(0.2)
    saida, erro = caixa.get("saida", ("", ""))
    return ler_resposta(saida, erro, proc.returncode)


def ler_resposta(saida: str, erro: str, codigo: int) -> str:
    """Tira o texto da resposta do JSON que o 'claude -p --output-format json' devolve."""
    try:
        dados = json.loads(saida)
    except (json.JSONDecodeError, TypeError):
        dica = (erro or saida or "").strip()[-400:]
        if "login" in dica.lower() or "auth" in dica.lower():
            raise ErroClaude(
                "O Claude Code não está logado. Abra o terminal, digite claude e entre na sua conta."
            ) from None
        raise ErroClaude(f"O Claude Code não respondeu direito (código {codigo}). {dica}") from None
    if dados.get("is_error") or dados.get("subtype") not in (None, "success"):
        raise ErroClaude(f"O Claude Code avisou um erro: {str(dados.get('result') or dados.get('subtype'))[:400]}")
    return str(dados.get("result") or "")


def com_tentativas(pedido: str, cancelar: threading.Event, avisar=None, modelo: str = "", ler_pasta=None) -> str:
    """rodar_claude, tentando de novo sozinho ate 3 vezes se der erro (rede, Claude ocupado...)."""
    ultimo = None
    for k in range(TENTATIVAS):
        if cancelar.is_set():
            raise Cancelado()
        if k and avisar:
            avisar(f"Tentando de novo ({k + 1} de {TENTATIVAS})... motivo: {ultimo}")
        try:
            if ler_pasta:
                return rodar_claude(pedido, cancelar, modelo, ler_pasta=ler_pasta)
            return rodar_claude(pedido, cancelar, modelo)
        except ErroClaude as e:
            ultimo = e
            if "não está logado" in str(e) or "Não achei" in str(e):
                raise
            if k < TENTATIVAS - 1:
                fim = time.monotonic() + ESPERA_ENTRE_TENTATIVAS[min(k, len(ESPERA_ENTRE_TENTATIVAS) - 1)]
                while time.monotonic() < fim:
                    if cancelar.is_set():
                        raise Cancelado() from None
                    time.sleep(0.2)
    raise ErroClaude(f"Tentei {TENTATIVAS} vezes e não deu. Último erro: {ultimo}")


def extrair_json(texto: str):
    from videos_longos.pedido_edicao import extrair_json as extrair

    return extrair(texto)


def pedir_json(pedido: str, validar, cancelar: threading.Event, avisar=None, modelo: str = "", ler_pasta=None):
    """Pede, le o JSON e confere com validar(dados) -> lista de erros. Se vier quebrado, pede de novo uma vez."""
    texto = com_tentativas(pedido, cancelar, avisar, modelo, ler_pasta)
    for vez in (1, 2):
        try:
            dados = extrair_json(texto)
            erros = validar(dados)
        except (json.JSONDecodeError, ValueError) as e:
            erros = [f"o JSON não abre ({e})"]
            dados = None
        if not erros:
            return dados
        if vez == 2:
            raise ErroClaude("O Claude mandou a resposta com problemas duas vezes:\n- " + "\n- ".join(erros[:8]))
        if avisar:
            avisar("A resposta veio com problemas; pedindo de novo ao Claude...")
        texto = com_tentativas(
            pedido + "\n\nATENÇÃO: a sua resposta anterior veio com estes problemas:\n- " + "\n- ".join(erros[:12])
            + "\nResponda de novo SÓ com o JSON corrigido, completo e válido.",
            cancelar, avisar, modelo, ler_pasta,
        )  # fmt: skip
    return None


def simultaneos(cfg: dict | None) -> int:
    """Quantas partes pedir ao Claude ao mesmo tempo ("claude_pedidos_simultaneos" no config.json; padrao 2)."""
    try:
        return max(1, min(4, int((cfg or {}).get("claude_pedidos_simultaneos") or SIMULTANEOS)))
    except (TypeError, ValueError):
        return SIMULTANEOS


class _Parar:
    """Junta o Cancelar da tela com o "uma parte deu erro": qualquer um dos dois faz as outras partes pararem."""

    def __init__(self, cancelar: threading.Event):
        self.cancelar = cancelar
        self.erro = threading.Event()

    def is_set(self) -> bool:
        return self.cancelar.is_set() or self.erro.is_set()


def pedir_partes(pedidos: list, validar, cancelar: threading.Event, avisar=None, modelo: str = "",
                 ao_terminar_parte=None, quantas_juntas: int = SIMULTANEOS) -> list:  # fmt: skip
    """Pede varias partes (pedir_json de cada uma), ate 'quantas_juntas' AO MESMO TEMPO. Antes era uma depois da
    outra: uma live de 6 h esperava o Claude terminar a parte 1 para comecar a 2. Devolve as respostas na ordem
    das partes. ao_terminar_parte(feitas) avisa o progresso. Se uma parte der erro, as outras param e o erro sobe."""
    if len(pedidos) <= 1 or quantas_juntas <= 1:
        respostas = []
        for k, pedido in enumerate(pedidos, 1):
            respostas.append(pedir_json(pedido, validar, cancelar, avisar, modelo))
            if ao_terminar_parte:
                ao_terminar_parte(k)
        return respostas
    parar = _Parar(cancelar)
    respostas = [None] * len(pedidos)
    primeiro_erro, feitas = None, 0

    def uma(k):
        if parar.is_set():  # cancelou ou outra parte ja deu erro: nem chama o Claude
            raise Cancelado()
        try:
            respostas[k] = pedir_json(pedidos[k], validar, parar, avisar, modelo)
        except Cancelado:
            raise
        except Exception:
            parar.erro.set()  # avisa as outras partes na hora
            raise

    with ThreadPoolExecutor(max_workers=min(quantas_juntas, len(pedidos))) as linhas:
        futuros = [linhas.submit(uma, k) for k in range(len(pedidos))]
        for futuro in as_completed(futuros):
            try:
                futuro.result()
            except Cancelado:
                continue  # parou porque voce cancelou ou porque outra parte deu erro (esse erro e o que sobe)
            except Exception as e:
                if primeiro_erro is None:
                    primeiro_erro = e
                parar.erro.set()
                continue
            feitas += 1
            if ao_terminar_parte:
                ao_terminar_parte(feitas)
    if cancelar.is_set():
        raise Cancelado()
    if primeiro_erro is not None:
        raise primeiro_erro
    return respostas


def dividir_transcricao(texto: str, limite: int = LIMITE_PARTE) -> list:
    """Divide a transcricao ([inicio-fim] fala, uma por linha) em partes de ate 'limite' caracteres.
    O cabecalho (VIDEO, DURACAO, Formato) vai em todas as partes. Nunca corta uma fala no meio."""
    linhas = texto.splitlines()
    cabecalho = []
    while linhas and not linhas[0].startswith("["):
        cabecalho.append(linhas.pop(0))
    topo = "\n".join(cabecalho).strip()
    partes, atual, tamanho = [], [], 0
    for linha in linhas:
        if atual and tamanho + len(linha) + 1 > limite:
            partes.append(atual)
            atual, tamanho = [], 0
        atual.append(linha)
        tamanho += len(linha) + 1
    if atual or not partes:
        partes.append(atual)
    return [(topo + "\n\n" if topo else "") + "\n".join(p) for p in partes]


def intervalo_da_parte(parte: str) -> tuple:
    """(inicio, fim) em texto, da primeira e da ultima fala da parte. Ex.: ('00:00:00', '01:12:30')."""
    falas = [linha for linha in parte.splitlines() if linha.startswith("[") and "-" in linha]
    if not falas:
        return ("?", "?")
    ini = falas[0][1:].split("-")[0]
    fim = falas[-1].split("]")[0].split("-")[-1]
    return ini, fim
