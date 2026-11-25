# Predefinicoes de corte do Auto-Edit: "Longo (TV)" e "Short (dinamico)".
# As de fabrica estao em FABRICA (e em padrao/predefinicoes_corte.json, que vai para o GitHub). As mudadas na tela
# Configuracoes > "Cortes automaticos" ficam em PASTA_CONFIG/predefinicoes_corte.json (no app instalado, so deste PC).
# Cada predefinicao tem versao: mudar uma regra aumenta a versao, e o edicao.json guarda com qual foi feito.
import copy
import json

from nucleo.comum import PASTA_CONFIG, PASTA_PADRAO, gravar_json

ARQUIVO = "predefinicoes_corte.json"
VERSAO_ARQUIVO = 1
TIPOS = ("longo", "short")

FABRICA = {
    "longo": {
        "nome": "Longo (TV)",
        "silencio_min": 3.0,  # silencio (sem fala e som baixo) maior que isso sai
        "silencio_so_sem_acao": True,  # ...e so se tambem nao tiver acao na tela
        "sem_jogo_min": 5.0,  # menu, loading, espera, area de trabalho
        "sem_acao_min": 6.0,  # sem fala e quase sem movimento na area do jogo
        "margem_antes": 0.4,  # segundos que ficam antes de cada trecho mantido
        "margem_depois": 0.8,  # segundos que ficam depois de cada trecho mantido
        "trecho_minimo": 2.0,  # trecho mantido menor que isso entre dois cortes (e sem fala) sai junto
        "juntar_menor_que": 1.5,  # dois cortes separados por menos que isso viram um so
        "nao_cortar_palavra": True,
        "ima_troca_cena": 1.0,  # encaixa a borda do corte numa troca de cena a menos disso
        "crossfade_ms": 60,  # fade de audio em cada emenda (tira o estalo)
        "corte_grande": 30.0,  # corte com mais que isso tirado...
        "fade_corte_grande": 0.2,  # ...ganha um fade curto na imagem (0 = corte seco)
        "acelerar_em_vez_de_cortar": False,
        "acelerar_velocidade": 2.0,
        "acelerar_motivos": ["sem_acao"],
        "volume_baixo": 0.25,  # volume do jogo (0 a 1) abaixo disso conta como silencio
        "movimento_baixo": 0.012,  # movimento (0 a 1) abaixo disso conta como "sem acao"
    },
    "short": {
        "nome": "Short (dinâmico)",
        "silencio_min": 0.6,
        "silencio_so_sem_acao": False,
        "sem_jogo_min": 1.0,
        "sem_acao_min": 1.5,
        "margem_antes": 0.15,
        "margem_depois": 0.25,
        "trecho_minimo": 0.8,
        "juntar_menor_que": 0.4,
        "nao_cortar_palavra": True,
        "ima_troca_cena": 0.3,
        "crossfade_ms": 30,
        "corte_grande": 30.0,
        "fade_corte_grande": 0.0,
        "acelerar_em_vez_de_cortar": False,
        "acelerar_velocidade": 2.0,
        "acelerar_motivos": ["sem_acao"],
        "volume_baixo": 0.25,
        "movimento_baixo": 0.012,
    },
}

# rotulos da tela Configuracoes > "Cortes automaticos": (chave, texto, tipo)
CAMPOS = [
    ("silencio_min", "Cortar silêncio a partir de (s)", float),
    ("silencio_so_sem_acao", "Silêncio só sai se também estiver sem ação", bool),
    ("sem_jogo_min", "Cortar \"sem jogo\" a partir de (s)", float),
    ("sem_acao_min", "Cortar \"sem ação\" a partir de (s)", float),
    ("margem_antes", "Margem antes de cada trecho mantido (s)", float),
    ("margem_depois", "Margem depois de cada trecho mantido (s)", float),
    ("trecho_minimo", "Trecho mantido mínimo (s)", float),
    ("juntar_menor_que", "Juntar cortes separados por menos de (s)", float),
    ("nao_cortar_palavra", "Nunca cortar no meio de palavra", bool),
    ("ima_troca_cena", "Encaixar na troca de cena se estiver a menos de (s)", float),
    ("crossfade_ms", "Fade de áudio em cada corte (ms)", float),
    ("corte_grande", "Corte grande: a partir de (s tirados)", float),
    ("fade_corte_grande", "Fade na imagem do corte grande (s; 0 = seco)", float),
    ("acelerar_em_vez_de_cortar", "Acelerar em vez de cortar (\"sem ação\")", bool),
    ("acelerar_velocidade", "Velocidade ao acelerar (x)", float),
    ("volume_baixo", "Volume do jogo que conta como silêncio (0 a 1)", float),
    ("movimento_baixo", "Movimento que conta como \"sem ação\" (0 a 1)", float),
]


def _arq_pc():
    return PASTA_CONFIG / ARQUIVO


def _ler(arq) -> dict:
    try:
        dados = json.loads(arq.read_text(encoding="utf-8"))
        return dados.get("predefinicoes") or {} if isinstance(dados, dict) else {}
    except Exception:
        return {}


def carregar() -> dict:
    """{"longo": {...}, "short": {...}}: fabrica + padrao/ + a deste PC por cima (cada regra separada)."""
    out = copy.deepcopy(FABRICA)
    arquivos = [PASTA_PADRAO / ARQUIVO]
    if _arq_pc() != arquivos[0]:
        arquivos.append(_arq_pc())
    versoes = {}
    for arq in arquivos:
        if not arq.exists():
            continue
        for tipo, regras in _ler(arq).items():
            if tipo in out and isinstance(regras, dict):
                out[tipo].update({k: v for k, v in regras.items() if k in out[tipo] or k == "versao"})
                versoes[tipo] = regras.get("versao", versoes.get(tipo, 1))
    for tipo in out:
        out[tipo]["versao"] = int(versoes.get(tipo, 1) or 1)
        out[tipo]["tipo"] = tipo
    return out


def da(tipo: str) -> dict:
    return carregar()[tipo if tipo in TIPOS else "longo"]


def validar(regras: dict, tipo: str) -> tuple[dict, list]:
    """Confere os numeros digitados. Devolve (regras limpas, erros em portugues simples)."""
    limpo, erros = {}, []
    for chave, texto, conv in CAMPOS:
        if chave not in regras:
            continue
        v = regras[chave]
        if conv is bool:
            limpo[chave] = bool(v)
            continue
        try:
            n = float(str(v).replace(",", "."))
        except ValueError:
            erros.append(f"{texto}: \"{v}\" não é um número.")
            continue
        if n < 0 or n > 600:
            erros.append(f"{texto}: use um número entre 0 e 600.")
            continue
        limpo[chave] = n
    if not 1.1 <= limpo.get("acelerar_velocidade", 2.0) <= 4:
        erros.append("Velocidade ao acelerar: use de 1.1 a 4.")
    if limpo.get("volume_baixo", 0) > 1 or limpo.get("movimento_baixo", 0) > 1:
        erros.append("Volume e movimento vão de 0 a 1.")
    return limpo, erros


def salvar(tipo: str, regras: dict) -> int:
    """Grava as regras deste tipo neste PC e aumenta a versao (so se algo mudou). Devolve a versao nova."""
    atual = da(tipo)
    mudou = any(atual.get(k) != v for k, v in regras.items())
    arq = _arq_pc()
    dados = {"versao": VERSAO_ARQUIVO, "predefinicoes": _ler(arq) if arq.exists() else {}}
    base = dict(dados["predefinicoes"].get(tipo) or {})
    base.update(regras)
    base["versao"] = atual["versao"] + 1 if mudou else atual["versao"]
    dados["predefinicoes"][tipo] = base
    arq.parent.mkdir(parents=True, exist_ok=True)
    gravar_json(arq, dados)
    return base["versao"]


def voltar_ao_padrao(tipo: str) -> int:
    """Volta este tipo para as regras de fabrica (a versao continua subindo, para o relatorio saber)."""
    versao = da(tipo)["versao"] + 1
    regras = {k: v for k, v in FABRICA[tipo].items() if k != "nome"}
    arq = _arq_pc()
    dados = {"versao": VERSAO_ARQUIVO, "predefinicoes": _ler(arq) if arq.exists() else {}}
    dados["predefinicoes"][tipo] = {**regras, "versao": versao}
    arq.parent.mkdir(parents=True, exist_ok=True)
    gravar_json(arq, dados)
    return versao


def mais_rigida(regras: dict, rodada: int) -> dict:
    """Regras da rodada 2, 3... do "Cortar mais" do editor: cada rodada aperta os tempos minimos (60% da anterior) e,
    a partir da 2a, tambem corta silencio durante o jogo. Assim da para ir tirando mais ate o video ficar bom."""
    r = dict(regras)
    fator = 0.6 ** max(0, rodada - 1)
    for chave, minimo in (("silencio_min", 0.8), ("sem_jogo_min", 1.5), ("sem_acao_min", 2.0)):
        r[chave] = round(max(minimo, float(regras[chave]) * fator), 2)
    if rodada >= 2:
        r["silencio_so_sem_acao"] = False
    r["nome"] = f"{regras.get('nome', 'Longo')} · rodada {rodada}"
    return r
