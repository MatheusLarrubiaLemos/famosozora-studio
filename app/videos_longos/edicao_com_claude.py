# "Editar com o Claude" (video longo): manda a transcricao (em partes, se a live for longa) para o Claude Code do
# PC, confere cada resposta, junta o que sai e os capitulos e, se veio em partes, pede no fim o titulo, a
# descricao e as tags com o resumo de todas. Salva o edicao.json (o anterior vira edicao_anterior.json).
import shutil
from pathlib import Path

from nucleo import claude_local
from videos_longos.pedido_edicao import (
    gravar_edicao,
    info_video,
    normalizar,
    para_interno,
    pedido_automatico,
    pedido_resumo,
)

TEXTOS = ("titulo", "descricao", "titulo_en", "descricao_en", "opcoes_titulo", "ideia_miniatura", "tags")


def validador(duracao: float):
    def validar(dados) -> list:
        if not isinstance(dados, dict):
            return ['a resposta precisa ser um objeto { ... } com a lista "remover"']
        if "remover" not in dados and "cortes" not in dados:
            return ['falta a lista "remover" (pode ser vazia: [])']
        _, erros, _ = normalizar(dados, duracao)
        return erros

    return validar


def validar_resumo(dados) -> list:
    if not isinstance(dados, dict) or not str(dados.get("titulo", "")).strip():
        return ['a resposta precisa ser {"titulo": "...", ...} com o título']
    return []


def juntar(respostas: list, resumo: dict | None = None) -> dict:
    """Junta as partes: tudo o que sai e todos os capitulos, em ordem; os textos vem do resumo (ou da parte 1)."""
    from nucleo.comum import ler_tempo

    internas = [para_interno(r) for r in respostas]
    saida = {"cortes": [], "capitulos": []}
    for r in internas:
        saida["cortes"] += [c for c in r.get("cortes") or [] if isinstance(c, dict)]
        saida["capitulos"] += [c for c in r.get("capitulos") or [] if isinstance(c, dict)]
    saida["cortes"].sort(key=lambda c: ler_tempo(c["inicio"]))
    saida["capitulos"].sort(key=lambda c: ler_tempo(c["inicio"]))
    fonte = resumo or (internas[0] if internas else {})
    for chave in TEXTOS:
        if fonte.get(chave):
            saida[chave] = fonte[chave]
    return saida


def editar_longo(pasta: Path, nome: str, cfg: dict, diretrizes: Path, cancelar, progresso=None, avisar=None):
    """Pede a edicao ao Claude. Devolve (dados normalizados, avisos). Da ErroClaude ou Cancelado."""
    arq = pasta / "transcricao_para_claude.txt"
    if not arq.exists():
        raise claude_local.ErroClaude("Essa live ainda não foi transcrita (falta o transcricao_para_claude.txt).")
    _, duracao = info_video(pasta)
    texto_diretrizes = diretrizes.read_text(encoding="utf-8") if diretrizes.exists() else ""
    limite = int(cfg.get("claude_limite_caracteres") or claude_local.LIMITE_PARTE)
    modelo = str(cfg.get("modelo_claude") or "")
    partes = claude_local.dividir_transcricao(arq.read_text(encoding="utf-8"), limite)
    total = len(partes) + (1 if len(partes) > 1 else 0)
    respostas = []
    for k, parte in enumerate(partes, 1):
        if progresso:
            progresso(k - 1, total, f"Pedindo a edição ao Claude (parte {k} de {len(partes)})...")
        pedido = pedido_automatico(nome, duracao, texto_diretrizes, parte, k, len(partes),
                                   claude_local.intervalo_da_parte(parte))  # fmt: skip
        respostas.append(claude_local.pedir_json(pedido, validador(duracao), cancelar, avisar, modelo))
    resumo = None
    if len(partes) > 1:
        if progresso:
            progresso(len(partes), total, "Pedindo o título, a descrição e as tags...")
        juntos = juntar(respostas)
        resumo = claude_local.pedir_json(pedido_resumo(nome, juntos["capitulos"], len(juntos["cortes"])),
                                         validar_resumo, cancelar, avisar, modelo)  # fmt: skip
    if progresso:
        progresso(total, total, "Juntando as respostas...")
    dados, erros, avisos = normalizar(juntar(respostas, resumo), duracao)
    if erros:
        raise claude_local.ErroClaude("A edição juntada ficou com problemas:\n- " + "\n- ".join(erros[:8]))
    return dados, avisos


def salvar_edicao(pasta: Path, dados: dict):
    """Grava o edicao.json. Se ja tinha um, ele vira edicao_anterior.json (nada se perde)."""
    arq = pasta / "edicao.json"
    if arq.exists():
        shutil.copy2(arq, pasta / "edicao_anterior.json")
    gravar_edicao(arq, dados)
