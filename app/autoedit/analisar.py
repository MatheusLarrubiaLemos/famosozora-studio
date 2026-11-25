# "Analisar a live" (Auto-Edit, Fase 1): roda as etapas em ordem, guardando cada uma em <projeto>\analise\
# (se o app fechar, as etapas prontas nao sao refeitas) e grava as SUGESTOES no edicao.json (versao 3).
#   Longo: 1 versao leve (proxy) -> 2 som -> 3 imagem -> 4 miniaturas -> 5 Claude olha as cenas
#          -> 6 Claude le a conversa -> 7 Claude escolhe os melhores momentos -> 8 decide os cortes (versoes.py)
#   Short (so a janela do Short, sem proxy nem Claude): som -> imagem -> decide
# Mudar a predefinicao depois e instantaneo: sugerir() so refaz a conta com os sinais guardados.
#
# Uso (a tela roda escondido e le o progresso):
#   python -m autoedit.analisar <pasta do projeto> [--sem-claude]
import sys
import threading
import time
from pathlib import Path

from autoedit import (
    classificar_cenas,
    classificar_fala,
    decidir_cortes,
    melhores_momentos,
    predefinicoes,
    proxy,
    sinais_audio,
    sinais_video,
    trechos,
)
from autoedit.base import Cancelado, areas_do_projeto, pasta_analise
from nucleo.comum import carregar_config, gravar_json, ler_json, rodar

ETAPAS_LONGO = 8


def info_projeto(pasta: Path) -> tuple:
    """(video original, duracao)."""
    from videos_longos.pedido_edicao import info_video

    return info_video(pasta)


def palavras_do_projeto(pasta: Path) -> list:
    from videos_longos.pedido_edicao import carregar_palavras

    return carregar_palavras(pasta)


def fonte_dos_sinais(pasta: Path, video: Path) -> Path:
    """O proxy (rapido de ler) se estiver pronto; senao o original."""
    pa = pasta_analise(pasta)
    return proxy.arq_proxy(pa) if proxy.proxy_pronto(pa, video) else video


def carregar_sinais(pasta: Path, inicio: float = 0.0, fim: float | None = None) -> dict:
    """Os sinais ja guardados (sem medir nada). Faltando algum, vem None."""
    from nucleo.comum import ler_json as ler

    pa = Path(pasta) / "analise"
    som = ler(pa / sinais_audio.nome_arquivo(inicio, fim))
    img = ler(pa / sinais_video.nome_arquivo(inicio, fim))
    if (som is None or img is None) and (inicio or fim is not None):  # janela de Short: usa a analise da live toda
        som = som or ler(pa / "som.json")
        img = img or ler(pa / "imagem.json")
    return {"som": som, "imagem": img, "cenas": ler(pa / "cenas.json"), "fala": ler(pa / "fala.json")}


def linha_do_tempo(pasta: Path, inicio: float, fim: float, sinais: dict | None = None,
                   palavras=None) -> decidir_cortes.Linha:  # fmt: skip
    """sinais / palavras ja lidos (o editor ja tem): nao le os arquivos grandes de novo."""
    sinais = sinais or carregar_sinais(pasta)
    cenas = (sinais.get("cenas") or {}).get("cenas") or []
    palavras = palavras if palavras is not None else palavras_do_projeto(pasta)
    return decidir_cortes.Linha(inicio, fim, palavras, sinais.get("som"), sinais.get("imagem"),
                                classificar_cenas.sem_jogo(cenas))  # fmt: skip


def sugerir(pasta: Path, tipo: str, regras: dict | None = None, inicio: float = 0.0, fim: float | None = None,
            duracao: float | None = None) -> list:  # fmt: skip
    """Sugestoes de corte com os sinais guardados e a predefinicao (instantaneo, nao mede nada de novo)."""
    regras = regras or predefinicoes.da(tipo)
    if fim is None:
        fim = duracao if duracao else info_projeto(pasta)[1]
    sinais = carregar_sinais(pasta, inicio, None if tipo == "longo" else fim)
    linha = linha_do_tempo(pasta, inicio, fim, sinais)
    papo = ((sinais.get("fala") or {}).get("papo_fora") or []) if tipo == "longo" else []
    return decidir_cortes.decidir(linha, regras, papo)


def gravar_no_edicao(pasta: Path, sugestoes: list, regras: dict, introducao, video: Path, duracao: float,
                     versao: str | None = None):  # fmt: skip
    """Junta as sugestoes no edicao.json (cria se nao existir), sem perder os seus cortes manuais."""
    from videos_longos.pedido_edicao import VERSAO_EDICAO, campos_novos, gravar_edicao, migrar_arquivo, para_interno

    arq = Path(pasta) / "edicao.json"
    if arq.exists():
        migrar_arquivo(pasta)
        dados = para_interno(ler_json(arq, {}) or {})
    else:
        dados = {"versao": VERSAO_EDICAO, "cortes": [], "capitulos": []}
    dados.update({k: v for k, v in campos_novos(dados).items() if k not in dados})
    antigos = trechos.normalizar(dados.get("trechos"), duracao)
    dados["trechos"] = trechos.mesclar_reanalise(antigos, sugestoes)
    dados["predefinicao"] = {"nome": regras["nome"], "versao": regras["versao"], "tipo": regras["tipo"]}
    dados["tipo"] = "longo"
    dados["video_original"] = str(video)
    if versao:
        dados["versao_edicao"] = versao  # qual versao (Padrao, Enxuto, Melhores momentos...) esta no editor
    if introducao and not dados.get("introducao"):
        dados["introducao"] = introducao
    gravar_edicao(arq, dados)
    return dados


def analisar_longo(pasta: Path, usar_claude: bool = True, cancelar=None, avisar=print, pedir_cenas=None,
                   pedir_fala=None, pedir_melhores=None) -> dict:  # fmt: skip
    """Todas as etapas da live. Devolve {"sugestoes", "introducao", "avisos", "tempos"}."""
    pasta = Path(pasta)
    video, dur = info_projeto(pasta)
    if not video.exists():
        raise RuntimeError(f"Não achei o vídeo original: {video}. Ele foi movido ou renomeado?")
    pa = pasta_analise(pasta)
    cfg = carregar_config()
    camera, jogo = areas_do_projeto(pasta, cfg)
    evento = threading.Event()
    parar = (lambda: cancelar() or False) if cancelar else (lambda: False)
    avisos, tempos, n = [], {}, ETAPAS_LONGO
    if not camera and not jogo:
        avisos.append("A área da câmera não está marcada: o movimento é medido na imagem inteira "
                      "(a câmera pode esconder trechos sem ação). Marque em Configurações.")  # fmt: skip

    def etapa(nome, funcao):
        t = time.monotonic()
        r = funcao()
        tempos[nome] = round(time.monotonic() - t, 1)
        return r

    px = etapa("proxy", lambda: proxy.gerar_proxy(video, pa, dur, parar, (1, n)))
    som = etapa("som", lambda: sinais_audio.medir(px, pa, dur, cancelar=parar, etapa=(2, n)))
    img = etapa("imagem", lambda: sinais_video.medir(px, pa, dur, camera, jogo, cancelar=parar, etapa=(3, n)))
    etapa("miniaturas", lambda: proxy.gerar_miniaturas(px, video, pa, dur, parar, (4, n)))
    linha = decidir_cortes.Linha(0.0, dur, palavras_do_projeto(pasta), som, img)
    cenas = {"cenas": []}
    fala = {"papo_fora": [], "introducao": None}
    if usar_claude:
        if parar():
            raise Cancelado()
        cenas = etapa("cenas", lambda: classificar_cenas.classificar(
            video, px, pa, dur, linha.sem_certeza, camera, jogo, evento, avisar, (5, n), pedir_cenas))  # fmt: skip
        if parar():
            raise Cancelado()
        fala = etapa("fala", lambda: classificar_fala.classificar(video, pasta, pa, evento, avisar, (6, n),
                                                                     pedir_fala))  # fmt: skip
        if parar():
            raise Cancelado()
        melhores = etapa("melhores", lambda: melhores_momentos.classificar(video, pasta, pa, evento, avisar, (7, n),
                                                                           pedir_melhores))  # fmt: skip
        avisos += [a for a in (cenas.get("aviso"), fala.get("aviso"), melhores.get("aviso")) if a]
    else:
        avisos.append("Análise sem o Claude: menu/loading só pela tela preta, sem 'papo fora do jogo' e sem os "
                      "melhores momentos.")  # fmt: skip
    # as sugestoes que entram no edicao.json: as da versao padrao (Configuracoes; "padrao" se nao tiver escolhido).
    # O editor mostra as outras versoes com a duracao de cada uma, para trocar na hora.
    from autoedit import versoes

    versao = str(cfg.get("autoedit_versao_padrao") or versoes.PADRAO)
    intro = fala.get("introducao")
    protegidos = [(intro["inicio"], intro["fim"])] if intro else []
    sugestoes = versoes.sugestoes(pasta, versao, dur, protegidos) if versao in versoes.NOMES else None
    if sugestoes is None:
        versao = versoes.PADRAO
        sugestoes = versoes.sugestoes(pasta, versao, dur, protegidos)
    regras = predefinicoes.da("longo")
    gravar_no_edicao(pasta, sugestoes, regras, intro, video, dur, versao)
    gravar_json(pa / "analise.json", {"tempos": tempos, "avisos": avisos, "duracao": dur,
                                      "predefinicao": {"nome": regras["nome"], "versao": regras["versao"]}})  # fmt: skip
    print(f"[{n}/{n}] Decidindo os cortes  100.0%", flush=True)
    return {"sugestoes": sugestoes, "introducao": fala.get("introducao"), "avisos": avisos, "tempos": tempos}


def analisar_janela(pasta: Path, inicio: float, fim: float, cancelar=None) -> dict:
    """Janela de um Short (com folga): som e imagem so desse pedaco, do video original. Sem Claude."""
    pasta = Path(pasta)
    video, dur = info_projeto(pasta)
    if not video.exists():
        raise RuntimeError(f"Não achei o vídeo original: {video}.")
    inicio, fim = max(0.0, inicio), min(dur, fim) if dur else fim
    pa = pasta_analise(pasta)
    parar = cancelar or (lambda: False)
    camera, jogo = areas_do_projeto(pasta)
    if not (pa / "som.json").exists():
        sinais_audio.medir(video, pa, dur, inicio, fim, cancelar=parar, etapa=(1, 2))
    if not (pa / "imagem.json").exists():
        sinais_video.medir(video, pa, dur, camera, jogo, inicio, fim, cancelar=parar, etapa=(2, 2))
    return carregar_sinais(pasta, inicio, fim)


ARQ_ANDAMENTO = "analisando.json"  # em <projeto>\analise\: existe (e e atualizado) enquanto a analise roda
SEGUNDOS_VIVO = 30  # andamento mais velho que isso = a analise parou (app fechado, PC desligou)


def andamento(pasta: Path) -> dict | None:
    """A analise desta live esta rodando agora (em qualquer processo)? Devolve {"linha", "inicio", "atualizado"}
    com a ultima linha de progresso ("[k/n] etapa xx%"), ou None se nao estiver rodando."""
    dados = ler_json(Path(pasta) / "analise" / ARQ_ANDAMENTO, None)
    if not isinstance(dados, dict) or time.time() - float(dados.get("atualizado") or 0) > SEGUNDOS_VIVO:
        return None
    return dados


def _anotar_andamento(pasta: Path, parar: threading.Event):
    """Enquanto a analise roda, grava a ultima linha de progresso a cada 3 s (para o editor acompanhar)."""
    from autoedit.base import ultima_linha_de_progresso

    arq = pasta_analise(pasta) / ARQ_ANDAMENTO
    inicio = time.time()
    while True:
        try:
            gravar_json(arq, {"linha": ultima_linha_de_progresso(), "inicio": inicio, "atualizado": time.time()})
        except OSError:
            pass
        if parar.wait(3):
            break
    try:
        arq.unlink()
    except OSError:
        pass


def analisar_com_andamento(pasta: Path, usar_claude: bool = True) -> dict:
    """analisar_longo + o arquivo de andamento (o editor ve que esta rodando e mostra onde esta)."""
    pasta = Path(pasta)
    parar = threading.Event()
    anotador = threading.Thread(target=_anotar_andamento, args=(pasta, parar), daemon=True)
    anotador.start()
    try:
        return analisar_longo(pasta, usar_claude=usar_claude)
    finally:
        parar.set()
        anotador.join(5)


def main():
    args = sys.argv[1:]
    if not args:
        print("Uso: python -m autoedit.analisar <pasta do projeto> [--sem-claude]")
        sys.exit(1)
    pasta = Path(args[0])
    r = analisar_com_andamento(pasta, usar_claude="--sem-claude" not in args)
    cortes = [s for s in r["sugestoes"] if s["acao"] == "cortar"]
    print(f"\nPronto: {len(r['sugestoes'])} sugestões ({len(cortes)} cortes, "
          f"{sum(s['fim'] - s['inicio'] for s in cortes) / 60:.1f} min a menos).")  # fmt: skip
    for a in r["avisos"]:
        print(f"[AVISO] {a}")
    print("Tempo de cada etapa (s): " + ", ".join(f"{k} {v}" for k, v in r["tempos"].items()))


if __name__ == "__main__":
    rodar(main)
