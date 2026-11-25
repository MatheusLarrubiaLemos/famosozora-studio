# "Editar com o Claude" (video longo): manda a transcricao (em partes, se a live for longa) para o Claude Code do
# PC, confere cada resposta, junta o que sai e os capitulos e, se veio em partes, pede no fim o titulo, a
# descricao e as tags com o resumo de todas. Salva o edicao.json (o anterior vira edicao_anterior.json).
# As partes vao ao mesmo tempo (claude_local.pedir_partes), nao uma depois da outra.
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
    pedido_textos,
)

LIMITE_TEXTOS = 120_000  # caracteres da amostra da transcricao no pedido so dos textos (rapido)
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
    pedidos = [pedido_automatico(nome, duracao, texto_diretrizes, parte, k, len(partes),
                                 claude_local.intervalo_da_parte(parte)) for k, parte in enumerate(partes, 1)]  # fmt: skip
    juntas = claude_local.simultaneos(cfg)
    if progresso:
        progresso(
            0,
            total,
            "Pedindo a edição ao Claude"
            + (f" ({len(partes)} partes, {min(juntas, len(partes))} ao mesmo tempo)..." if len(partes) > 1 else "..."),
        )

    def parte_pronta(feitas):
        if progresso and len(partes) > 1:
            progresso(feitas, total, f"Pedindo a edição ao Claude ({feitas} de {len(partes)} partes prontas)...")

    respostas = claude_local.pedir_partes(pedidos, validador(duracao), cancelar, avisar, modelo, parte_pronta,
                                          juntas)  # fmt: skip
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


def textos_longo(pasta: Path, nome: str, cfg: dict, cancelar, progresso=None, avisar=None) -> dict:
    """So os textos do episodio (titulo, descricao, tags, ingles...), sem mexer nos cortes. Um pedido so."""
    from videos_longos.pedido_edicao import amostra_da_transcricao

    arq = pasta / "transcricao_para_claude.txt"
    if not arq.exists():
        raise claude_local.ErroClaude("Essa live ainda não foi transcrita (falta o transcricao_para_claude.txt).")
    limite = min(int(cfg.get("claude_limite_caracteres") or claude_local.LIMITE_PARTE), LIMITE_TEXTOS)
    if progresso:
        progresso(0, 1, "Pedindo o título, a descrição e as tags ao Claude...")
    resposta = claude_local.pedir_json(pedido_textos(nome, amostra_da_transcricao(arq.read_text(encoding="utf-8"), limite)),
                                       validar_resumo, cancelar, avisar, str(cfg.get("modelo_claude") or ""))  # fmt: skip
    if progresso:
        progresso(1, 1, "Pronto.")
    return {k: resposta[k] for k in TEXTOS if resposta.get(k)}


def salvar_textos(pasta: Path, textos: dict):
    """Poe os textos no edicao.json sem mexer no resto (cortes, trechos do Auto-Edit, capitulos)."""
    from nucleo.comum import ler_json
    from videos_longos.pedido_edicao import gravar_edicao

    arq = pasta / "edicao.json"
    dados = para_interno(ler_json(arq, {}) or {})
    if not isinstance(dados, dict):
        dados = {}
    dados.update(textos)
    gravar_edicao(arq, dados)


def salvar_edicao(pasta: Path, dados: dict):
    """Grava o edicao.json. Se ja tinha um, ele vira edicao_anterior.json (nada se perde).
    O que veio do Auto-Edit e do editor (trechos, marcadores, introducao...) continua: o Claude so troca a parte dele."""
    from nucleo.comum import ler_json
    from videos_longos.pedido_edicao import CAMPOS_AUTOEDIT

    arq = pasta / "edicao.json"
    if arq.exists():
        shutil.copy2(arq, pasta / "edicao_anterior.json")
        antigo = ler_json(arq, {}) or {}
        dados = {**dados, **{k: antigo[k] for k in CAMPOS_AUTOEDIT if k in antigo and antigo[k] not in (None, [])}}
    gravar_edicao(arq, dados)
