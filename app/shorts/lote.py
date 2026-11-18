# Motor do LOTE: gera os Shorts de varios videos de uma vez, um depois do outro, sem abrir janela nenhuma.
# Para cada video: transcrever (se ainda nao foi) -> pedir os cortes ao Claude (se ainda nao tem) -> gerar os Shorts.
# Cada video continua sendo um projeto separado (pasta, Shorts e cortes.json proprios): nada se mistura.
# O estado fica em configuracoes\lote.json (gravado a cada passo): se o app fechar ou o PC desligar,
# da para continuar de onde parou. Esta parte nao tem tela: a tela do lote (interface/janela_lote.py) so le o estado.
import copy
import os
import queue
import re
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from nucleo.comum import FERRAMENTAS, PASTA_APP, PASTA_FILA, gravar_json, ler_json

VERSAO_LOTE = 1  # formato do lote.json (mudou o formato = numero novo + migracao em migrar())

# etapas de cada video, com o simbolo que a tela mostra
ETAPAS = {
    "fila": ("⏳", "na fila"),
    "transcrevendo": ("🎙", "transcrevendo"),
    "cortando": ("✂", "cortando"),
    "renderizando": ("🎬", "renderizando"),
    "pronto": ("✅", "pronto"),
    "erro": ("❌", "erro"),
    "pulado": ("⏭", "pulado (já tinha Shorts)"),
}
TRABALHANDO = ("transcrevendo", "cortando", "renderizando")
TERMINADAS = ("pronto", "erro", "pulado")
SEM_JANELA = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class ErroLote(Exception):
    """Erro de um video do lote, ja em portugues simples (aparece na tela e no resumo)."""


class Cancelado(Exception):
    """Voce clicou em Cancelar."""


_um_lote_por_vez = threading.Lock()  # nao deixa comecar dois lotes ao mesmo tempo


# ================================================================== arquivo lote.json
def arquivo() -> Path:
    return PASTA_FILA / "lote.json"


def agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def montar_lote(projetos: list, refazer: dict | None = None) -> dict:
    """Monta o lote com os projetos escolhidos (na ordem da lista). refazer = {nome: True} para os que ja tem
    Shorts e devem ser gerados de novo; os outros que ja tem Shorts ficam como "pulado"."""
    refazer = refazer or {}
    videos = []
    for info in projetos:
        tem_shorts = bool(info.get("n_shorts"))
        de_novo = bool(refazer.get(info["nome"])) and tem_shorts
        videos.append({
            "nome": info["nome"],
            "pasta": str(info["pasta"]),
            "etapa": "pulado" if tem_shorts and not de_novo else "fila",
            "refazer": de_novo,
            "lixeira_feita": False,
            "progresso": 0.0,
            "detalhe": "",
            "erro": "",
            "avisos": [],
            "n_shorts": int(info.get("n_shorts") or 0) if tem_shorts and not de_novo else 0,
            "segundos": 0.0,
        })  # fmt: skip
    return {"versao": VERSAO_LOTE, "criado_em": agora(), "situacao": "preparado", "segundos": 0.0,
            "terminado_em": None, "videos": videos}  # fmt: skip


def migrar(dados: dict, arq: Path | None = None) -> dict:
    """Formato antigo do lote.json -> formato atual. Antes de mudar, guarda uma copia em lote.bak.json."""
    versao = dados.get("versao", 0) if isinstance(dados, dict) else 0
    if versao >= VERSAO_LOTE:
        return dados
    if arq is not None and arq.exists():
        gravar_json(arq.with_name(arq.stem + ".bak.json"), dados)
    # versao 0 (sem numero): so tinha nome, pasta e etapa de cada video
    videos = []
    for v in dados.get("videos", []) if isinstance(dados, dict) else []:
        if not isinstance(v, dict) or not v.get("pasta"):
            continue
        etapa = v.get("etapa") if v.get("etapa") in ETAPAS else "fila"
        videos.append({"nome": v.get("nome") or Path(v["pasta"]).name, "pasta": v["pasta"], "etapa": etapa,
                       "refazer": bool(v.get("refazer")), "lixeira_feita": bool(v.get("lixeira_feita")),
                       "progresso": 0.0, "detalhe": "", "erro": str(v.get("erro") or ""), "avisos": [],
                       "n_shorts": int(v.get("n_shorts") or 0), "segundos": float(v.get("segundos") or 0)})  # fmt: skip
    novo = {"versao": VERSAO_LOTE, "criado_em": dados.get("criado_em") or agora(),
            "situacao": dados.get("situacao") or "rodando", "segundos": float(dados.get("segundos") or 0),
            "terminado_em": dados.get("terminado_em"), "videos": videos}  # fmt: skip
    if arq is not None:
        gravar_json(arq, novo)
    return novo


def carregar() -> dict | None:
    """Le o lote.json (migrando se for de um formato antigo). None se nao existe ou esta estragado."""
    arq = arquivo()
    dados = ler_json(arq, None)
    if not isinstance(dados, dict):
        return None
    return migrar(dados, arq)


def salvar(lote: dict):
    PASTA_FILA.mkdir(parents=True, exist_ok=True)
    gravar_json(arquivo(), lote)


def pendentes(lote: dict) -> list:
    return [v for v in lote.get("videos", []) if v.get("etapa") not in TERMINADAS]


def retomavel(lote: dict | None) -> bool:
    """True se o lote parou no meio sem voce cancelar (app fechou, PC desligou): da para continuar."""
    return bool(lote) and lote.get("situacao") in ("rodando", "pausado") and bool(pendentes(lote))


def preparar_para_retomar(lote: dict) -> dict:
    """Video que estava no meio de uma etapa volta para a fila (a etapa recomeca; o que ja ficou pronto, fica)."""
    for v in lote.get("videos", []):
        if v.get("etapa") in TRABALHANDO:
            v["etapa"] = "fila"
            v["progresso"] = 0.0
            v["detalhe"] = "continuando de onde parou"
        limpar_temporarios(Path(v["pasta"]))
    return lote


def tentar_de_novo(lote: dict, nome: str) -> dict:
    """Botao "Tentar de novo so este": o video com erro volta para a fila."""
    for v in lote.get("videos", []):
        if v["nome"] == nome and v.get("etapa") == "erro":
            v.update(etapa="fila", erro="", progresso=0.0, detalhe="", avisos=[])
    lote["situacao"] = "preparado"
    lote["terminado_em"] = None
    return lote


def resumo(lote: dict) -> dict:
    """Numeros para a tela do fim: Shorts por video, tempo e erros."""
    videos = lote.get("videos", [])
    feitos = [v for v in videos if v.get("etapa") == "pronto"]
    return {
        "n_videos": len(feitos),
        "n_shorts": sum(int(v.get("n_shorts") or 0) for v in feitos),
        "erros": [v for v in videos if v.get("etapa") == "erro"],
        "pulados": [v for v in videos if v.get("etapa") == "pulado"],
        "segundos": float(lote.get("segundos") or 0),
    }


def texto_notificacao(lote: dict) -> str:
    r = resumo(lote)
    texto = f"Lote pronto: {r['n_shorts']} Shorts de {r['n_videos']} vídeo{'s' if r['n_videos'] != 1 else ''}"
    if r["erros"]:
        texto += f" ({len(r['erros'])} com erro)"
    return texto


def progresso_geral(lote: dict) -> float:
    """De 0 a 1: quanto do lote ja foi feito (os pulados nao contam)."""
    videos = [v for v in lote.get("videos", []) if v.get("etapa") != "pulado"]
    if not videos:
        return 1.0
    feito = sum(1.0 if v.get("etapa") in ("pronto", "erro") else float(v.get("progresso") or 0) for v in videos)
    return min(1.0, feito / len(videos))


def tempo_restante(lote: dict) -> float | None:
    """Segundos que faltam (estimativa pelo ritmo ate agora). None enquanto e cedo demais para saber."""
    feito, gasto = progresso_geral(lote), float(lote.get("segundos") or 0)
    if feito < 0.03 or gasto < 20:
        return None
    return max(0.0, gasto / feito - gasto)


def texto_tempo(segundos: float | None) -> str:
    if segundos is None:
        return "calculando..."
    minutos = int(round(segundos / 60))
    if minutos < 1:
        return "menos de 1 minuto"
    if minutos < 60:
        return f"{minutos} min"
    return f"{minutos // 60} h {minutos % 60:02d} min"


# ================================================================== olhando o projeto no disco
def precisa_transcrever(pasta: Path) -> bool:
    """Sem transcricao, ou sem o texto que o Claude le quando ainda faltam os cortes."""
    if not (pasta / "transcricao.json").exists():
        return True
    return not (pasta / "transcricao_para_claude.txt").exists() and precisa_cortes(pasta)


def precisa_cortes(pasta: Path) -> bool:
    from shorts.cortes import ler_cortes

    return ler_cortes(pasta, gravar_migracao=False) is None


def n_cortes(pasta: Path) -> int:
    from nucleo.comum import carregar_config
    from shorts.cortes import escolhidos, ler_cortes, maximo_de_shorts

    dados = ler_cortes(pasta, gravar_migracao=False) or {}
    lista = dados.get("cortes") if isinstance(dados.get("cortes"), list) else []
    return len(escolhidos(lista, maximo_de_shorts(carregar_config())))


def shorts_prontos(pasta: Path) -> list:
    prontos = pasta / "prontos"
    return sorted(f for f in prontos.glob("*.mp4") if not f.name.startswith("_")) if prontos.exists() else []


def plano_do_video(pasta: Path) -> str:
    """O que o lote vai fazer com esse video (aparece na janela Preparar lote)."""
    pasta = Path(pasta)
    passos = []
    if precisa_transcrever(pasta):
        passos.append("transcrever")
    if precisa_transcrever(pasta) or precisa_cortes(pasta):
        passos.append("cortes com o Claude")
    passos.append("gerar Shorts")
    return " → ".join(passos)


def precisa_do_claude(projetos: list) -> bool:
    """True se algum video ainda vai pedir os cortes ao Claude."""
    return any(precisa_transcrever(Path(i["pasta"])) or precisa_cortes(Path(i["pasta"])) for i in projetos)


def limpar_temporarios(pasta: Path):
    """Apaga o que sobra de um Short que estava sendo renderizado (nunca um Short pronto)."""
    for f in list((pasta / "prontos").glob("_gerando_*.mp4")) + list(pasta.glob("temp_legenda_*.ass")):
        try:
            f.unlink()
        except OSError:
            pass


# ================================================================== processos escondidos
def python_sem_janela() -> str:
    """O Python do app (no Windows, o python.exe: o pythonw.exe nao escreve a saida que o lote le)."""
    py = Path(sys.executable)
    if py.name.lower() == "pythonw.exe" and py.with_name("python.exe").exists():
        py = py.with_name("python.exe")
    return str(py)


def matar_arvore(proc: subprocess.Popen):
    """Para o processo E os que ele abriu (o ffmpeg), para nao sobrar nada rodando nem arquivo preso."""
    if proc.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True,
                           creationflags=SEM_JANELA)  # fmt: skip
        else:
            os.killpg(proc.pid, signal.SIGTERM)
    except Exception:
        proc.kill()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()


def rodar_processo(args: list, cancelar: threading.Event, ao_ler_linha=None) -> tuple:
    """Roda "python -m ..." escondido, passando cada linha da saida para ao_ler_linha.
    Devolve (codigo de saida, ultimas linhas). Da Cancelado se cancelar for ligado no meio."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1", HF_HUB_DISABLE_SYMLINKS_WARNING="1")
    extra = {"creationflags": SEM_JANELA} if os.name == "nt" else {"start_new_session": True}
    proc = subprocess.Popen([python_sem_janela(), "-m", *map(str, args)], stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True, encoding="utf-8",
                            errors="replace", env=env, cwd=str(FERRAMENTAS), **extra)  # fmt: skip
    linhas = queue.Queue()

    def ler():
        for linha in proc.stdout:
            linhas.put(linha.rstrip())
        linhas.put(None)

    threading.Thread(target=ler, daemon=True).start()
    ultimas, acabou = [], False
    while not acabou:
        if cancelar.is_set():
            matar_arvore(proc)
            raise Cancelado()
        try:
            linha = linhas.get(timeout=0.3)
        except queue.Empty:
            continue
        if linha is None:
            acabou = True
            continue
        ultimas = (ultimas + [linha])[-40:]
        if ao_ler_linha:
            ao_ler_linha(linha)
    return proc.wait(), ultimas


def _primeiro_erro(linhas: list) -> str:
    for linha in linhas:
        if "[ERRO]" in linha:
            return explicar_erro(linha.split("[ERRO]", 1)[1].strip())
    return ""


def explicar_erro(texto: str) -> str:
    """Troca os erros tecnicos mais comuns por uma explicacao em portugues simples, dizendo o que fazer."""
    baixo = texto.lower()
    if any(p in baixo for p in ("403", "forbidden", "connection", "conex", "proxy", "resolve", "timed out",
                                "getaddrinfo", "huggingface")):  # fmt: skip
        return "Não consegui baixar o modelo do Whisper (sem internet?). Conecte na internet e tente de novo só este."
    if "out of memory" in baixo or "memoryerror" in baixo or "memória" in baixo:
        return "Faltou memória. Feche outros programas pesados e tente de novo só este."
    if "no space" in baixo or "espaço" in baixo:
        return "O disco está cheio. Libere espaço e tente de novo só este."
    return texto


# ================================================================== as 3 etapas de verdade
class Etapas:
    """O que cada etapa faz de verdade. Nos testes, troca-se por uma versao falsa (sem Whisper nem Claude)."""

    def __init__(self, diretrizes: Path | None = None):
        if diretrizes is None:
            nomes = (PASTA_APP / "DIRETRIZES DO CANAL.md", PASTA_APP / "docs" / "DIRETRIZES DO CANAL.md")
            diretrizes = next((n for n in nomes if n.exists()), nomes[0])
        self.diretrizes = diretrizes

    def transcrever(self, v: dict, cancelar, progresso):
        from nucleo.miniatura import video_do_projeto

        video = video_do_projeto(Path(v["pasta"]))
        if not video:
            raise ErroLote("Não achei o vídeo original desse projeto (foi movido ou renomeado?). "
                           "Transcreva este vídeo pelo botão 1 da tela Shorts.")  # fmt: skip

        def linha(texto):
            achou = re.search(r"(\d+(?:\.\d+)?)%", texto)
            if achou and texto.startswith("["):
                progresso(float(achou.group(1)) / 100, "transcrevendo " + achou.group(0))
            elif "Extraindo" in texto or "Carregando" in texto or "modelo" in texto.lower():
                progresso(0.0, "preparando a transcrição...")

        codigo, ultimas = rodar_processo(["nucleo.transcrever", video, "--sem-perguntas"], cancelar, linha)
        if codigo != 0 or precisa_transcrever(Path(v["pasta"])):
            raise ErroLote("A transcrição falhou. " + (_primeiro_erro(ultimas) or "Veja o registro de erros."))

    def pedir_cortes(self, v: dict, cancelar, progresso):
        from nucleo import claude_local
        from nucleo.comum import carregar_config
        from shorts.biblioteca import categorias_com_arquivos
        from shorts.cortes_com_claude import gerar_cortes, salvar_cortes

        pasta = Path(v["pasta"])

        def prog(parte, total, texto):
            progresso(parte / max(1, total), texto.rstrip(".") + " (costuma levar de 1 a 5 min por parte)")

        try:
            dados = gerar_cortes(pasta, v["nome"], carregar_config(), categorias_com_arquivos("efeito"),
                                 self.diretrizes, cancelar, prog)  # fmt: skip
        except claude_local.Cancelado as e:
            raise Cancelado() from e
        except claude_local.ErroClaude as e:
            raise ErroLote(f"O Claude não conseguiu escolher os cortes: {e}") from e
        salvar_cortes(pasta, dados)

    def renderizar(self, v: dict, cancelar, progresso):
        pasta = Path(v["pasta"])
        info = {"erros": 0}

        def linha(texto):
            achou = re.match(r"\[(\d+)/(\d+)\]", texto)
            if achou:
                n, total = int(achou.group(1)), int(achou.group(2))
                progresso((n - 1) / max(1, total), f"Short {n} de {total}")
            fim = re.search(r"(\d+) com erro", texto)
            if "PRONTO!" in texto and fim:
                info["erros"] = int(fim.group(1))

        try:
            codigo, ultimas = rodar_processo(["shorts.gerar_shorts", pasta], cancelar, linha)
        finally:
            limpar_temporarios(pasta)
        if codigo != 0:
            raise ErroLote("A geração dos Shorts falhou. " + (_primeiro_erro(ultimas) or "Veja o registro de erros."))
        return info["erros"]


# ================================================================== rodar o lote
class RodarLote:
    """Roda o lote numa linha separada (a tela nao trava). A tela chama retrato() de tempos em tempos para
    mostrar o progresso, e pausar(), continuar() e cancelar() pelos botoes."""

    def __init__(self, lote: dict, etapas: Etapas | None = None, gravar: bool = True):
        self.lote = lote
        self.etapas = etapas or Etapas()
        self.gravar = gravar
        self.trava = threading.Lock()
        self.evento_pausa = threading.Event()
        self.evento_cancelar = threading.Event()
        self.linha = None
        self.terminou = threading.Event()
        self.fechando = False  # o app esta fechando: para tudo, mas o lote fica para continuar depois

    # ------------------------------------------------ comandos da tela
    def iniciar(self) -> bool:
        """Comeca em segundo plano. False se ja tem outro lote rodando."""
        if not _um_lote_por_vez.acquire(blocking=False):
            return False
        self.linha = threading.Thread(target=self._rodar_e_soltar, daemon=True)
        self.linha.start()
        return True

    def rodar_aqui(self):
        """Roda na mesma linha (usado nos testes). Da RuntimeError se ja tem outro lote rodando."""
        if not _um_lote_por_vez.acquire(blocking=False):
            raise RuntimeError("Já tem um lote rodando.")
        self._rodar_e_soltar()

    def pausar(self):
        self.evento_pausa.set()
        self._mudar(situacao="pausado")

    def continuar(self):
        self.evento_pausa.clear()
        self._mudar(situacao="rodando")

    def cancelar(self):
        self.evento_cancelar.set()
        self.evento_pausa.clear()

    def parar_para_fechar(self, espera: float = 20.0):
        """O Studio vai fechar: para a etapa atual (sem arquivo quebrado) e deixa o lote para continuar depois."""
        self.fechando = True
        self.cancelar()
        self.terminou.wait(espera)

    def retrato(self) -> dict:
        """Copia do estado agora (para a tela ler sem atrapalhar o lote)."""
        with self.trava:
            return copy.deepcopy(self.lote)

    # ------------------------------------------------ por dentro
    def _mudar(self, video: dict | None = None, **campos):
        with self.trava:
            (video if video is not None else self.lote).update(campos)
            if self.gravar:
                salvar(self.lote)

    def _rodar_e_soltar(self):
        try:
            self._rodar()
        finally:
            _um_lote_por_vez.release()
            self.terminou.set()

    def _rodar(self):
        preparar_para_retomar(self.lote)
        self._mudar(situacao="pausado" if self.evento_pausa.is_set() else "rodando", terminado_em=None)
        relogio = time.monotonic()
        atual = {"video": None}  # o video que esta rodando agora (o tempo dele tambem anda)

        def contar_tempo():
            nonlocal relogio
            with self.trava:
                agora_ = time.monotonic()
                passou = agora_ - relogio
                relogio = agora_
                self.lote["segundos"] = float(self.lote.get("segundos") or 0) + passou
                if atual["video"] is not None:
                    atual["video"]["segundos"] = float(atual["video"].get("segundos") or 0) + passou

        self._contar_tempo = contar_tempo
        # o relogio anda sozinho a cada segundo (o Claude passa minutos pensando sem dar noticia)
        parar_relogio = threading.Event()

        def relogio_andando():
            while not parar_relogio.wait(1.0):
                contar_tempo()

        threading.Thread(target=relogio_andando, daemon=True).start()
        try:
            self._cada_video(contar_tempo, atual)
        finally:
            parar_relogio.set()
        contar_tempo()
        if self.evento_cancelar.is_set():
            self._mudar(situacao="rodando" if self.fechando else "cancelado")
        else:
            self._mudar(situacao="terminado", terminado_em=agora())

    def _cada_video(self, contar_tempo, atual: dict):
        for v in list(self.lote["videos"]):
            if v.get("etapa") in TERMINADAS:
                continue
            if self._esperar_se_pausado():
                break
            contar_tempo()
            atual["video"] = v
            try:
                self._um_video(v)
            except Cancelado:
                self._mudar(v, etapa="fila", progresso=0.0, detalhe="cancelado: recomeça esta etapa")
                limpar_temporarios(Path(v["pasta"]))
                break
            except ErroLote as e:
                self._mudar(v, etapa="erro", erro=str(e), detalhe="")
            except Exception as e:  # erro inesperado: guarda no registro e segue para o proximo video
                from nucleo.registro import registrar

                registrar(f"erro no lote ({v['nome']})", e)
                self._mudar(v, etapa="erro", erro=f"Erro inesperado: {e}", detalhe="")
            finally:
                contar_tempo()
                atual["video"] = None
                self._mudar()  # grava o tempo no lote.json

    def _esperar_se_pausado(self) -> bool:
        """Espera enquanto estiver pausado. True se foi cancelado."""
        while self.evento_pausa.is_set() and not self.evento_cancelar.is_set():
            time.sleep(0.2)
        return self.evento_cancelar.is_set()

    def _um_video(self, v: dict):
        pasta = Path(v["pasta"])
        if not pasta.exists():
            raise ErroLote("A pasta desse projeto não existe mais (foi excluída?).")
        transcrever, cortes = precisa_transcrever(pasta), precisa_cortes(pasta)
        # pedacos da barra de cada video: transcrever pesa mais; renderizar fica com o resto
        partes = []
        if transcrever:
            partes.append(("transcrevendo", 0.5))
        if cortes:
            partes.append(("cortando", 0.15))
        partes.append(("renderizando", 1.0 - sum(p for _, p in partes)))
        comeco = {}
        acumulado = 0.0
        for etapa, peso in partes:
            comeco[etapa] = (acumulado, peso)
            acumulado += peso

        def progresso_de(etapa):
            ini, peso = comeco[etapa]

            def progresso(fracao, detalhe=""):
                self._contar_tempo()
                self._mudar(v, progresso=round(ini + peso * max(0.0, min(1.0, fracao)), 4), detalhe=detalhe)

            return progresso

        self._mudar(v, erro="", avisos=[])
        if transcrever:
            self._passo(v, "transcrevendo", "transcrevendo...")
            self.etapas.transcrever(v, self.evento_cancelar, progresso_de("transcrevendo"))
            self._pausa_e_cancelar()
        if precisa_cortes(pasta):
            if "cortando" not in comeco:  # a transcricao foi feita agora, mas sem cortes previstos (nao acontece)
                comeco["cortando"] = (comeco["renderizando"][0], 0.0)
            self._passo(v, "cortando", "pedindo os cortes ao Claude...")
            self.etapas.pedir_cortes(v, self.evento_cancelar, progresso_de("cortando"))
            self._pausa_e_cancelar()
        if n_cortes(pasta) == 0:
            self._mudar(v, etapa="pronto", progresso=1.0, n_shorts=0,
                        avisos=["O Claude não achou nenhum corte bom nesse vídeo."], detalhe="")  # fmt: skip
            return
        if v.get("refazer") and not v.get("lixeira_feita"):
            from nucleo.limpeza import mandar_para_lixeira

            if not mandar_para_lixeira(shorts_prontos(pasta)):
                raise ErroLote("Não consegui mandar os Shorts antigos para a Lixeira. "
                               "Feche os vídeos abertos em outros programas e tente de novo.")  # fmt: skip
            self._mudar(v, lixeira_feita=True)
        self._parar_se_cancelado()
        self._passo(v, "renderizando", "gerando os Shorts...")
        erros = self.etapas.renderizar(v, self.evento_cancelar, progresso_de("renderizando"))
        self._parar_se_cancelado()
        feitos = len(shorts_prontos(pasta))
        if feitos == 0:
            raise ErroLote("Nenhum Short ficou pronto. Veja o registro de erros e tente de novo só este.")
        avisos = [f"{erros} corte(s) deram erro e ficaram de fora."] if erros else []
        self._mudar(v, etapa="pronto", progresso=1.0, n_shorts=feitos, avisos=avisos, detalhe="")

    def _passo(self, v: dict, etapa: str, detalhe: str):
        self._mudar(v, etapa=etapa, detalhe=detalhe)

    def _pausa_e_cancelar(self):
        """Entre uma etapa e outra: para se foi cancelado; espera se esta pausado."""
        self._parar_se_cancelado()
        if self._esperar_se_pausado():
            raise Cancelado()

    def _parar_se_cancelado(self):
        if self.evento_cancelar.is_set():
            raise Cancelado()
