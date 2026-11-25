# VERSOES da edicao do video longo (desde a 1.11.0): com a live analisada, o Studio monta varias versoes na hora
# (os sinais ja estao medidos; so a conta muda) e o editor mostra quanto cada uma dura, para voce escolher:
#   Padrao (TV)        -> tira so o que e morto (silencio sem acao, tela sem jogo, jogo parado): fica quase tudo
#   Enxuto             -> rodada 2 de regras (tempos menores e silencio tambem durante o jogo)
#   Bem enxuto         -> rodada 3 (ainda mais rigida)
#   Melhores momentos  -> so os melhores trechos que o Claude escolheu (~8% da live, entre 10 e 45 min)
#   Resumao            -> so os melhores dos melhores (~15 min)
# Nos melhores momentos, dentro de cada momento ainda saem os silencios mortos (regras do Padrao).
from pathlib import Path

from autoedit import melhores_momentos, predefinicoes
from autoedit import trechos as tr

VERSOES = [("padrao", "Padrão (TV)"), ("enxuto", "Enxuto"), ("bem_enxuto", "Bem enxuto"),
           ("melhores", "Melhores momentos"), ("resumao", "Resumão (~15 min)")]  # fmt: skip
NOMES = dict(VERSOES)
PADRAO = "padrao"
PRECISA_CLAUDE = ("melhores", "resumao")  # usam os momentos escolhidos pelo Claude (analise\melhores.json)


def regras_da_versao(versao: str) -> dict:
    base = predefinicoes.da("longo")
    rodada = {"enxuto": 2, "bem_enxuto": 3}.get(versao, 1)
    return predefinicoes.mais_rigida(base, rodada) if rodada > 1 else base


def alvo(versao: str, duracao: float) -> float:
    return 15 * 60.0 if versao == "resumao" else melhores_momentos.alvo_automatico(duracao)


def _decidir(pasta: Path, versao: str, duracao: float, linha=None, papo=None) -> list:
    """As sugestoes da conta fixa (sem os melhores momentos). linha/papo ja prontos = nao le nada de novo."""
    from autoedit import analisar, decidir_cortes

    if linha is None:
        return analisar.sugerir(Path(pasta), "longo", regras_da_versao(versao), 0.0, duracao, duracao)
    return decidir_cortes.decidir(linha, regras_da_versao(versao), papo or [])


def sugestoes(pasta: Path, versao: str, duracao: float, protegidos=(), momentos=None, base=None, linha=None,
              papo=None) -> list | None:  # fmt: skip
    """As sugestoes de corte desta versao. None = precisa dos melhores momentos e eles ainda nao foram escolhidos.
    base = as sugestoes do Padrao, se ja calculadas (os melhores momentos usam elas dentro de cada momento)."""
    if versao not in PRECISA_CLAUDE:
        return _decidir(pasta, versao, duracao, linha, papo)
    momentos = melhores_momentos.guardados(pasta) if momentos is None else momentos
    if momentos is None:
        return None
    padrao = base if base is not None else _decidir(pasta, PADRAO, duracao, linha, papo)
    ficam = melhores_momentos.escolher(momentos, alvo(versao, duracao), duracao, protegidos)
    dentro = [s for s in padrao if any(a <= (s["inicio"] + s["fim"]) / 2 < b for a, b in ficam)]
    return sorted(melhores_momentos.cortes_fora(ficam, duracao) + dentro, key=lambda s: (s["inicio"], s["fim"]))


def duracao_final(sugestoes_da_versao: list, duracao: float, protegidos=()) -> float:
    return tr.duracao_final(sugestoes_da_versao, duracao, protegidos)


def todas(pasta: Path, duracao: float, protegidos=(), sinais=None, palavras=None) -> dict:
    """{versao: (sugestoes ou None, duracao final ou None)} de todas as versoes (para a lista do editor).
    sinais / palavras = os que o editor ja leu: monta a linha do tempo UMA vez para todas as versoes (antes cada
    versao relia os arquivos grandes de som, imagem e transcricao, e a tela travava numa live de 9 h)."""
    from autoedit import analisar

    sinais = sinais or analisar.carregar_sinais(Path(pasta))
    linha = analisar.linha_do_tempo(Path(pasta), 0.0, duracao, sinais, palavras)
    papo = (sinais.get("fala") or {}).get("papo_fora") or []
    momentos = melhores_momentos.guardados(pasta)
    out, base = {}, None
    for versao, _ in VERSOES:
        s = sugestoes(pasta, versao, duracao, protegidos, momentos, base, linha, papo)
        if versao == PADRAO:
            base = s
        out[versao] = (s, duracao_final(s, duracao, protegidos) if s is not None else None)
    return out
