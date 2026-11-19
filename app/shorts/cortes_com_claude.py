# "Gerar cortes com o Claude": manda a transcricao (dividida em partes, se a live for longa) para o Claude Code
# do PC, confere cada resposta, junta tudo num cortes.json so e salva (o anterior vira cortes_anterior.json).
# As partes vao ao mesmo tempo (claude_local.pedir_partes), nao uma depois da outra.
import shutil
from pathlib import Path

from nucleo import claude_local
from nucleo.comum import gravar_json, ler_json, ler_tempo
from shorts.cortes import VERSAO, limpar_titulos, nota_do
from shorts.pedido_cortes import pedido_automatico

DURACAO_MAXIMA = 180.0  # Short do YouTube: ate 3 minutos
DURACAO_MINIMA = 5.0


def validador(duracao: float):
    """Funcao que confere a resposta do Claude e devolve a lista de problemas (vazia = tudo certo)."""

    def validar(dados) -> list:
        if not isinstance(dados, dict) or not isinstance(dados.get("cortes"), list):
            return ['a resposta precisa ser um objeto { ... } com a lista "cortes"']
        erros = []
        for k, c in enumerate(dados["cortes"], 1):
            if not isinstance(c, dict):
                erros.append(f"corte {k}: não é um objeto {{ ... }}")
                continue
            try:
                ini, fim = ler_tempo(c["inicio"]), ler_tempo(c["fim"])
            except (KeyError, TypeError, ValueError):
                erros.append(f'corte {k}: "inicio" e "fim" precisam ser tempos como 00:12:03.5')
                continue
            if fim <= ini:
                erros.append(f"corte {k}: o fim vem antes do início")
            elif fim - ini > DURACAO_MAXIMA + 0.5:
                erros.append(f"corte {k}: tem {fim - ini:.0f} s, passa de 3 minutos (limite do Short)")
            elif fim - ini < DURACAO_MINIMA:
                erros.append(f"corte {k}: tem só {fim - ini:.1f} s")
            if duracao and fim > duracao + 1:
                erros.append(f"corte {k}: termina depois do fim do vídeo")
            ab = c.get("abertura")
            if ab:
                try:
                    a0, a1 = ler_tempo(ab["inicio"]), ler_tempo(ab["fim"])
                    if a1 <= a0 or (duracao and a1 > duracao + 1):
                        erros.append(f"corte {k}: a abertura tem tempos errados")
                except (KeyError, TypeError, ValueError):
                    erros.append(f'corte {k}: "abertura" precisa de "inicio" e "fim"')
            if len(str(c.get("youtube_titulo") or c.get("titulo") or "")) > 100:
                erros.append(f"corte {k}: o youtube_titulo passa de 100 caracteres")
        if dados.get("correcoes") is not None and not isinstance(dados["correcoes"], dict):
            erros.append('"correcoes" precisa ser um objeto {"errada": "certa"}')
        return erros

    return validar


def juntar(respostas: list) -> dict:
    """Junta as respostas das partes: todos os cortes em ordem de tempo; se dois se sobrepuserem muito
    (na emenda entre duas partes), fica o de nota maior."""
    cortes, correcoes = [], {}
    for r in respostas:
        cortes += [c for c in r.get("cortes", []) if isinstance(c, dict)]
        correcoes.update(r.get("correcoes") or {})
    cortes.sort(key=lambda c: ler_tempo(c["inicio"]))
    final = []
    for c in cortes:
        if final:
            a = final[-1]
            ini, fim = ler_tempo(c["inicio"]), ler_tempo(c["fim"])
            a_ini, a_fim = ler_tempo(a["inicio"]), ler_tempo(a["fim"])
            sobra = min(fim, a_fim) - max(ini, a_ini)
            if sobra > 0.5 * min(fim - ini, a_fim - a_ini):
                if nota_do(c) > nota_do(a):
                    final[-1] = c
                continue
        final.append(c)
    return {"versao": VERSAO, "correcoes": correcoes, "cortes": final}


def gerar_cortes(pasta: Path, nome: str, cfg: dict, categorias: list, diretrizes: Path, cancelar,
                 progresso=None, avisar=None) -> dict:  # fmt: skip
    """Pede os cortes ao Claude e devolve o cortes.json pronto (ainda nao salvo).
    progresso(parte, total, texto). Da claude_local.ErroClaude ou claude_local.Cancelado."""
    arq = pasta / "transcricao_para_claude.txt"
    if not arq.exists():
        raise claude_local.ErroClaude("Esse vídeo ainda não foi transcrito (falta o transcricao_para_claude.txt).")
    transcricao = arq.read_text(encoding="utf-8")
    duracao = float((ler_json(pasta / "projeto.json", {}) or {}).get("duracao") or 0)
    texto_diretrizes = diretrizes.read_text(encoding="utf-8") if diretrizes.exists() else ""
    limite = int(cfg.get("claude_limite_caracteres") or claude_local.LIMITE_PARTE)
    partes = claude_local.dividir_transcricao(transcricao, limite)
    pedidos = [pedido_automatico(nome, cfg, categorias, texto_diretrizes, parte, k, len(partes),
                                 claude_local.intervalo_da_parte(parte)) for k, parte in enumerate(partes, 1)]  # fmt: skip
    juntas = claude_local.simultaneos(cfg)
    if progresso:
        progresso(
            0,
            len(partes),
            "Pedindo os cortes ao Claude"
            + (f" ({len(partes)} partes, {min(juntas, len(partes))} ao mesmo tempo)..." if len(partes) > 1 else "..."),
        )

    def parte_pronta(feitas):
        if progresso and len(partes) > 1:
            progresso(feitas, len(partes), f"Pedindo os cortes ao Claude ({feitas} de {len(partes)} partes prontas)...")

    respostas = claude_local.pedir_partes(pedidos, validador(duracao), cancelar, avisar,
                                          str(cfg.get("modelo_claude") or ""), parte_pronta, juntas)  # fmt: skip
    if progresso:
        progresso(len(partes), len(partes), "Juntando as respostas...")
    dados = juntar(respostas)
    limpar_titulos(dados["cortes"], nome)  # seguranca: titulo sem o nome do video colado no fim
    return dados


def salvar_cortes(pasta: Path, dados: dict):
    """Grava o cortes.json. Se ja tinha um, ele vira cortes_anterior.json (nada se perde)."""
    arq = pasta / "cortes.json"
    if arq.exists():
        shutil.copy2(arq, pasta / "cortes_anterior.json")
    gravar_json(arq, dados)
