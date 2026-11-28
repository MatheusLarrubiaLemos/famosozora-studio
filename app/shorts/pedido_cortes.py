# Texto do pedido de cortes que vai para o Claude: o de copiar e colar (texto_pedido) e o automatico, com a
# transcricao junto e o formato completo do cortes.json (pedido_automatico, usado pelo "Gerar cortes com o Claude").
# Sem numero fixo de Shorts: so os cortes que valem a pena (pode ser 0). Cada corte traz clima, motivo e nota
# e, se houver efeitos na pasta, as sugestoes de efeitos sonoros (so as categorias que tem arquivo).
from pathlib import Path

from shorts import duracao as tamanho
from shorts.cortes import CLIMAS, VERSAO, maximo_de_shorts


def texto_sons(categorias: list, maximo_efeitos: int) -> str:
    """Parte do pedido sobre efeitos sonoros e troca de musica. So oferece as categorias que tem arquivo."""
    troca = (
        "  Pode sugerir trocar a música num momento-chave (ex.: virada épica): "
        '{"tempo": "...", "tipo": "musica", "clima": "epico", "motivo": "virada"} (no máximo 1 por Short).\n'
    )
    if not categorias or maximo_efeitos <= 0:
        return '- "sons" (opcional): não há efeitos sonoros na pasta, então nenhum efeito.\n' + troca
    return (
        f'- "sons" (opcional): efeitos sonoros. Categorias disponíveis: {", ".join(categorias)}. '
        'Formato: [{"tempo": "00:12:15.4", "categoria": "impacto", "motivo": "tomou o soco"}] '
        "(tempo do vídeo original, como inicio e fim).\n"
        "  Regras: efeito só quando combina com o momento; nada de som em todo segundo (o canal não quer cara de "
        f"edição frenética); no máximo {maximo_efeitos} por Short; nunca em cima de uma fala. "
        "Na maioria dos cortes, 0 ou 1 efeito basta.\n" + troca
    )


def texto_pedido(nome: str, pasta: Path, diretrizes: Path, cfg: dict, categorias: list | None = None) -> str:
    return (
        f'Claude, escolhe os cortes do projeto "{nome}".\n'
        f"Pasta: {pasta}\n"
        f"Siga as DIRETRIZES DO CANAL ({diretrizes}). Resumo:\n"
        + regras(cfg, categorias)
        + texto_duracao(cfg)
        + "Salva o cortes.json na pasta."
    )


def regras(cfg: dict, categorias: list | None = None) -> str:
    """As regras dos cortes (iguais no pedido de copiar e colar e no automatico)."""
    maximo = maximo_de_shorts(cfg)
    try:
        maximo_efeitos = max(0, int(cfg.get("maximo_efeitos", 3)))
    except (TypeError, ValueError):
        maximo_efeitos = 3
    teto = f"- No máximo {maximo} cortes (é só um teto, não uma meta: se só 2 forem bons, mande 2).\n" if maximo else ""
    return (
        "- O vídeo é a versão bruta da live: escolha momentos em que estou JOGANDO "
        "(nada de espera, menu, intro ou papo fora do jogo).\n"
        "- O Short apresenta, o vídeo longo aprofunda: cada corte se entende sozinho, com começo, "
        "meio e fim, sem picotar, e deixa vontade de ver o vídeo completo.\n"
        "- Título honesto e chamativo, só sobre o que acontece no corte (sem mentir). "
        "NÃO coloque o nome do vídeo, da live, do episódio nem do canal no título (nem no fim, nem depois de "
        '" - ", " | " ou entre parênteses): o título é só a frase do momento.\n'
        "- Falas naturais, palavrão pode ficar. Pouca hashtag; o conteúdo é que vende.\n"
        "- Inclua também título e descrição em inglês (youtube_titulo_en, youtube_descricao_en).\n"
        "QUANTOS CORTES: gere só os cortes que valem a pena: chamativos e/ou engraçados. "
        'Pode ser 0, 3 ou 15. Qualidade acima de quantidade. Se nada prestar, salve "cortes": [].\n'
        f"{teto}"
        "Em cada corte, além do que já vai:\n"
        f'- "clima": um de {" | ".join(CLIMAS)} (escolhe a música de fundo);\n'
        '- "motivo": 1 frase dizendo por que o trecho prende;\n'
        '- "nota": de 1 a 10, a força do corte;\n'
        f"{texto_sons(categorias or [], maximo_efeitos)}"
        f'Use "versao": {VERSAO} no arquivo.\n'
        "Legenda corrigida e textos pro YouTube (por enquanto só publico no YouTube): youtube_titulo (até 100 "
        "caracteres), youtube_descricao (use {link} onde vai o link do vídeo completo) e tags. "
    )


FORMATO = """{
  "versao": 3,
  "correcoes": {"palavra que o Whisper errou": "palavra certa"},
  "cortes": [
    {
      "inicio": "00:12:03.5",
      "fim": "00:12:58.0",
      "titulo": "título curto, sem o nome do vídeo (vira o nome do arquivo e aparece no topo do Short)",
      "abertura": {"inicio": "00:12:40.0", "fim": "00:12:44.0"},
      "legenda": "o que é falado no corte, corrigido e fiel à fala; [[assim]] na palavra que você não tem certeza",
      "youtube_titulo": "até 100 caracteres, sem o nome do vídeo no final",
      "youtube_descricao": "1 ou 2 frases + ▶ Vídeo completo: {link} + 2 a 4 hashtags",
      "tags": ["...", "..."],
      "youtube_titulo_en": "...",
      "youtube_descricao_en": "...",
      "clima": "engracado",
      "motivo": "por que o trecho prende",
      "nota": 8,
      "sons": []
    }
  ]
}"""


def texto_duracao(cfg: dict) -> str:
    """Parte do pedido sobre o tamanho do corte (o Short pronto tem um maximo; shorts/duracao.py)."""
    maxima = tamanho.duracao_maxima(cfg)
    ideal, acelerado = (int(x) for x in tamanho.limites_do_corte(cfg))  # para baixo: assim cabe de verdade
    final = f"{tamanho.duracao_do_final(cfg):g}".replace(".", ",")
    vel = f"{tamanho.velocidade_maxima(cfg):g}".replace(".", ",")
    texto = (
        f"- TAMANHO: o Short pronto (gancho + corte + final de {final} s) tem no MÁXIMO "
        f"{maxima:.0f} segundos. Então cada corte tem de 15 a {ideal} segundos. Corte bem enxuto: comece "
        "direto na ação (sem aquecimento nem explicação antes) e termine logo depois do ponto alto ou da risada.\n"
    )
    if acelerado > ideal + 1:
        texto += (
            f"  Só se o momento for muito bom e não der para encurtar sem estragar, o corte pode ir até "
            f"{acelerado} s: o Studio acelera o Short (até {vel}x) para caber.\n"
        )
    return texto


def pedido_automatico(nome: str, cfg: dict, categorias: list, diretrizes: str, transcricao: str,
                      parte: int = 1, total: int = 1, intervalo=("", "")) -> str:  # fmt: skip
    """Pedido completo para o 'claude -p': regras, diretrizes do canal, formato e a transcricao (ou uma parte)."""
    sobre_parte = ""
    if total > 1:
        sobre_parte = (f"\nATENÇÃO: a live é longa e veio dividida. Esta é a PARTE {parte} de {total} "
                       f"(de {intervalo[0]} a {intervalo[1]}). Escolha cortes só desta parte; as outras partes vão "
                       "em outros pedidos. Os tempos são do vídeo inteiro.\n")  # fmt: skip
    return (
        f'Você vai escolher os cortes (Shorts) da live "{nome}" do canal FamosoZora.\n'
        "Regras:\n"
        + regras(cfg, categorias)
        + "\n"
        + texto_duracao(cfg)
        + "- Todo corte começa e termina em fim de frase. O 'abertura' (gancho) é opcional: o melhor momento do "
        "corte, de 2 a 5 s, que passa no começo.\n"
        "- Tempos no formato HH:MM:SS.d, do vídeo original (os da transcrição).\n"
        + sobre_parte
        + "\n=== DIRETRIZES DO CANAL ===\n"
        + diretrizes.strip()
        + "\n\n=== FORMATO DA RESPOSTA ===\n"
        "Responda SÓ com um JSON válido neste formato (sem texto antes ou depois, sem comentários):\n"
        + FORMATO
        + "\n\n=== TRANSCRIÇÃO ([início-fim] fala) ===\n"
        + transcricao
    )
