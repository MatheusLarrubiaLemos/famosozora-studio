# Texto do pedido de cortes que vai para o Claude (botao "2 Pedir cortes ao Claude").
# Sem numero fixo de Shorts: so os cortes que valem a pena (pode ser 0). Cada corte traz clima, motivo e nota.
from pathlib import Path

from shorts.cortes import CLIMAS, VERSAO, maximo_de_shorts


def texto_pedido(nome: str, pasta: Path, diretrizes: Path, cfg: dict) -> str:
    maximo = maximo_de_shorts(cfg)
    teto = f"- No máximo {maximo} cortes (é só um teto, não uma meta: se só 2 forem bons, mande 2).\n" if maximo else ""
    return (
        f'Claude, escolhe os cortes do projeto "{nome}".\n'
        f"Pasta: {pasta}\n"
        f"Siga as DIRETRIZES DO CANAL ({diretrizes}). Resumo:\n"
        "- O vídeo é a versão bruta da live: escolha momentos em que estou JOGANDO "
        "(nada de espera, menu, intro ou papo fora do jogo).\n"
        "- O Short apresenta, o vídeo longo aprofunda: cada corte se entende sozinho, com começo, "
        "meio e fim, sem picotar, e deixa vontade de ver o vídeo completo.\n"
        "- Título honesto e chamativo, alinhado ao que acontece no corte (sem mentir). "
        "Se for série, cite o episódio.\n"
        "- Falas naturais, palavrão pode ficar. Pouca hashtag; o conteúdo é que vende.\n"
        "- Inclua também título e descrição em inglês (youtube_titulo_en, youtube_descricao_en).\n"
        "QUANTOS CORTES: gere só os cortes que valem a pena: chamativos e/ou engraçados. "
        'Pode ser 0, 3 ou 15. Qualidade acima de quantidade. Se nada prestar, salve "cortes": [].\n'
        f"{teto}"
        "Em cada corte, além do que já vai:\n"
        f'- "clima": um de {" | ".join(CLIMAS)} (escolhe a música de fundo);\n'
        '- "motivo": 1 frase dizendo por que o trecho prende;\n'
        '- "nota": de 1 a 10, a força do corte.\n'
        f'Use "versao": {VERSAO} no arquivo.\n'
        "Legenda corrigida e textos pra YouTube, TikTok e Instagram. Salva o cortes.json na pasta."
    )
