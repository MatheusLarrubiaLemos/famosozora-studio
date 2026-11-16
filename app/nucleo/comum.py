# Base do programa: onde ficam as pastas, os ajustes e as configuracoes, mais pequenas funcoes de texto,
# tempo e arquivos .json usadas por todas as outras partes.
import json
import os
import re
import sys
from pathlib import Path

FERRAMENTAS = Path(__file__).resolve().parent.parent  # pasta do codigo (GitHub: app; instalado: ferramentas)
PASTA_APP = FERRAMENTAS.parent  # raiz do programa (app instalado ou pasta do GitHub)
# O programa e os seus arquivos ficam SEPARADOS:
#   - programa: instalado pelo .exe (ou a pasta do GitHub, no modo desenvolvedor)
#   - pasta de trabalho: videos e projetos em producao (padrao: Documentos\FamosoZora). E DESCARTAVEL:
#     depois de postar, pode limpar. Por isso as configuracoes e as musicas NAO ficam nela.
APP_INSTALADO = (FERRAMENTAS / "APP_INSTALADO").exists()  # False = rodando da pasta do GitHub
PASTA_BIN = PASTA_APP / "bin"  # app: ffmpeg.exe e ffprobe.exe
PASTA_PADRAO = FERRAMENTAS / "padrao"  # configuracoes iniciais (config.json etc.)
DADOS_APP = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".local" / "share") / "FamosoZora Studio"
ARQ_AJUSTES = DADOS_APP / "ajustes.json"
REPO_URL = "https://github.com/MatheusLarrubiaLemos/famosozora-studio"


def ler_ajustes() -> dict:
    try:
        return json.loads(ARQ_AJUSTES.read_text(encoding="utf-8"))
    except Exception:
        return {}


def salvar_ajustes(mudancas: dict):
    atual = ler_ajustes()
    atual.update(mudancas)
    DADOS_APP.mkdir(parents=True, exist_ok=True)
    ARQ_AJUSTES.write_text(json.dumps(atual, ensure_ascii=False, indent=2), encoding="utf-8")


def pasta_trabalho_padrao() -> Path:
    return Path.home() / "Documents" / "FamosoZora"


PASTA_CANAL = Path(ler_ajustes().get("pasta_trabalho") or pasta_trabalho_padrao())  # pasta de trabalho
PASTA_SHORTS = PASTA_CANAL / "shorts"
PASTA_VIDEOS = PASTA_CANAL / "videos"
# Configuracoes e musicas:
#   - pasta do GitHub (modo desenvolvedor): app\padrao e musicas\. O que mudar ali vai para o GitHub
#     no Commit + Push e chega aos outros PCs.
#   - app instalado: %LOCALAPPDATA%\FamosoZora Studio\configuracoes e \musicas. Valem JUNTO com as
#     que vem dentro do app (as do GitHub).
PASTA_CONFIG = (DADOS_APP / "configuracoes") if APP_INSTALADO else PASTA_PADRAO
PASTA_MUSICAS_APP = PASTA_APP / "musicas"
PASTA_MUSICAS = (DADOS_APP / "musicas") if APP_INSTALADO else PASTA_MUSICAS_APP
ARQUIVOS_CONFIG = ("config.json", "vocabulario.txt", "correcoes.txt", "censura.txt")

if PASTA_BIN.exists():  # ffmpeg que vem junto com o app
    os.environ["PATH"] = str(PASTA_BIN) + os.pathsep + os.environ.get("PATH", "")


def preparar_pasta_trabalho():
    """Cria a pasta de trabalho (so as pastas de producao) e garante as configuracoes deste PC."""
    for p in (PASTA_SHORTS, PASTA_VIDEOS):
        p.mkdir(parents=True, exist_ok=True)
    preparar_configuracoes()


def preparar_configuracoes():
    """App instalado: cria a pasta de configuracoes deste PC, aproveitando as que ficavam na pasta de trabalho.
    No modo desenvolvedor nao faz nada: as configuracoes sao as da pasta do GitHub (app\\padrao)."""
    import shutil

    if not APP_INSTALADO:
        return
    PASTA_CONFIG.mkdir(parents=True, exist_ok=True)
    PASTA_MUSICAS.mkdir(parents=True, exist_ok=True)
    antigas = [PASTA_CANAL / "configuracoes", PASTA_SHORTS / "ferramentas"]  # ate a 1.2.0 / antes da 1.0
    for nome in ARQUIVOS_CONFIG:
        destino = PASTA_CONFIG / nome
        if destino.exists():
            continue
        origem = next((a / nome for a in antigas if (a / nome).exists()), None)
        if origem:
            shutil.copy2(origem, destino)
        elif nome == "config.json":
            shutil.copy2(PASTA_PADRAO / nome, destino)
        else:  # listas: as do programa ja valem; este arquivo e so para o que for acrescentado neste PC
            destino.write_text(
                "# Acrescente aqui o que vale so neste PC (um por linha).\n"
                "# O que vem com o programa (do GitHub) ja esta valendo e nao precisa repetir.\n",
                encoding="utf-8",
            )
    musicas_antigas = PASTA_SHORTS / "musicas"  # ate a 1.2.0 as musicas ficavam na pasta de trabalho
    if musicas_antigas.exists():
        do_app = {m.name.lower() for m in PASTA_MUSICAS_APP.glob("*")}
        for m in musicas_antigas.iterdir():
            if m.is_file() and m.name.lower() not in do_app and not (PASTA_MUSICAS / m.name).exists():
                shutil.copy2(m, PASTA_MUSICAS / m.name)


def listar_musicas() -> list:
    """Musicas de fundo: as que vem com o programa mais as deste PC, em ordem alfabetica."""
    achadas = {}
    for pasta in _sem_repetir(PASTA_MUSICAS_APP, PASTA_MUSICAS):
        if pasta.exists():
            for p in pasta.iterdir():
                if p.suffix.lower() in EXTENSOES_AUDIO:
                    achadas[p.name.lower()] = p
    return [achadas[k] for k in sorted(achadas)]


def mover_para_antigos(pasta: Path, arquivos) -> Path:
    """Move arquivos para <pasta>\\antigos\\<data e hora> (nada e apagado). Devolve a pasta criada."""
    import shutil
    from datetime import datetime

    destino = pasta / "antigos" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    destino.mkdir(parents=True, exist_ok=True)
    for f in arquivos:
        if Path(f).exists():
            shutil.move(str(f), str(destino / Path(f).name))
    return destino


EXTENSOES_VIDEO = {".mp4", ".mov", ".mkv", ".m4v", ".avi", ".ts", ".flv"}
EXTENSOES_AUDIO = {".mp3", ".m4a", ".wav", ".ogg", ".aac", ".flac"}
CANAL_URL = "https://www.youtube.com/@famosozora"

PAUSAR = "--pausar" in sys.argv
if PAUSAR:
    sys.argv.remove("--pausar")


def carregar_config() -> dict:
    padrao = {
        # transcricao
        "idioma": "pt",
        "dispositivo": "auto",
        "modelo_gpu": "large-v3-turbo",
        "modelo_cpu": "small",
        "modelo_precisao": "large-v3",
        "retranscrever_cortes": "auto",
        # layout
        "layout": "camera",
        "altura_camera": 600,
        "camera_area": None,
        "gameplay_area": None,
        # legenda
        "palavras_por_legenda": 3,
        "legenda_maiuscula": True,
        "fonte": "Arial Black",
        "tamanho_legenda": 96,
        "borda_legenda": 4,
        "posicao_legenda": 520,
        "cor_por_falante": True,
        "sensibilidade_falantes": 0.9,
        "mostrar_titulo": True,
        "tamanho_titulo": 64,
        # gancho (inicio)
        "usar_abertura": True,
        "transicao": "fade",
        "duracao_transicao": 0.45,
        "mostrar_texto_gancho": False,
        "duracao_gancho": 3.5,
        "tamanho_gancho": 72,
        # final (inscreva-se)
        "duracao_final": 3.5,
        "final_linha_1": "VÍDEO COMPLETO NO CANAL",
        "final_linha_2": "INSCREVA-SE",
        "final_linha_3": "youtube.com/famosozora",
        # musica
        "musica": "aleatoria",
        "volume_musica": 0.18,
        "volume_musica_final": 0.55,
        # video
        "qualidade_crf": 20,
        "codificar_na_gpu": "auto",
        # censura (as palavras sao escolhidas no editor de legendas, Short por Short)
        "censura_audio": "nenhum",  # "nenhum" = so a legenda vira p***; "silencio" ou "bip" mexem no audio
        # video longo (episodio editado)
        "episodio_preset": "veryfast",  # x264 sem NVIDIA: ultrafast/superfast/veryfast/faster/fast/medium
        "episodio_crf": 20,
        "episodio_ajuste_silencio": 2.0,  # leva cada borda de corte para a pausa mais proxima (s; 0 desliga)
        "episodio_usar_abertura": True,
        "episodio_fade_preto": 0.35,  # fade para preto entre a abertura e o episodio (s)
    }
    # primeiro o config.json que vem com o programa (GitHub); depois o deste PC, que tem a palavra final
    for arq in _sem_repetir(PASTA_PADRAO / "config.json", PASTA_CONFIG / "config.json"):
        if arq.exists():
            try:
                padrao.update(json.loads(arq.read_text(encoding="utf-8")))
            except Exception as e:
                print(f"[AVISO] {arq} com erro ({e}). Usando valores padrao.")
    return padrao


def _sem_repetir(*arquivos: Path) -> list:
    """No modo desenvolvedor a pasta padrao e a pasta de configuracoes sao a mesma: le uma vez so."""
    vistos, out = set(), []
    for a in arquivos:
        chave = str(a).lower()
        if chave not in vistos:
            vistos.add(chave)
            out.append(a)
    return out


_CONFIG_COMPARTILHADA = None


def config_compartilhada() -> dict:
    """A mesma configuracao para todos os arquivos de um programa (quem muda um valor, muda para todos)."""
    global _CONFIG_COMPARTILHADA
    if _CONFIG_COMPARTILHADA is None:
        _CONFIG_COMPARTILHADA = carregar_config()
    return _CONFIG_COMPARTILHADA


def salvar_config(mudancas: dict):
    PASTA_CONFIG.mkdir(parents=True, exist_ok=True)
    arq = PASTA_CONFIG / "config.json"
    atual = {}
    if arq.exists():
        try:
            atual = json.loads(arq.read_text(encoding="utf-8"))
        except Exception:
            pass
    atual.update(mudancas)
    gravar_json(arq, atual)


def ler_json(arq: Path, padrao=None):
    try:
        return json.loads(Path(arq).read_text(encoding="utf-8"))
    except Exception:
        return padrao


def gravar_json(arq: Path, dados):
    """Grava num arquivo temporario e so depois troca: se o PC desligar no meio, o arquivo antigo fica inteiro."""
    arq = Path(arq)
    tmp = arq.with_name(arq.name + ".gravando")
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, arq)


# ------------------------------------------------------------------ internet
def abrir_url(endereco: str, tempo: int = 30, cabecalhos: dict | None = None):
    """Abre um endereco da internet conferindo o certificado do jeito do Windows (biblioteca truststore).
    Sem ela, o Python as vezes recusava o GitHub ("certificate verify failed"), dependendo do servidor."""
    import ssl
    import urllib.request

    try:
        import truststore

        contexto = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except Exception:
        contexto = None  # sem a biblioteca: usa a conferencia normal do Python
    pedido = urllib.request.Request(endereco, headers={"User-Agent": "FamosoZora-Studio", **(cabecalhos or {})})
    return urllib.request.urlopen(pedido, timeout=tempo, context=contexto)


# ------------------------------------------------------------------ textos
def nome_seguro(texto: str, limite: int = 80) -> str:
    texto = "".join(ch for ch in texto if ord(ch) < 0x2000)  # tira emojis e simbolos
    texto = re.sub(r'[\\/:*?"<>|\r\n\t]', "", texto).strip().rstrip(".")
    texto = re.sub(r"\s+", " ", texto)
    return texto[:limite].strip() or "sem_nome"


def tempo_txt(seg: float, ms: bool = False) -> str:
    seg = max(0.0, float(seg))
    h = int(seg // 3600)
    m = int(seg % 3600 // 60)
    s = seg % 60
    if ms:
        return f"{h:02d}:{m:02d}:{s:06.3f}"
    return f"{h:02d}:{m:02d}:{int(s):02d}"


def ler_tempo(valor) -> float:
    """Aceita 123.4, "123.4", "02:03.5" ou "01:02:03.5"."""
    if isinstance(valor, (int, float)):
        return float(valor)
    partes = str(valor).strip().replace(",", ".").split(":")
    total = 0.0
    for p in partes:
        total = total * 60 + float(p)
    return total


def _linhas_uteis(arq: Path) -> list:
    """Linhas de um arquivo de lista, sem comentarios (#) e sem linhas vazias."""
    if not arq.exists():
        return []
    linhas = (linha.split("#")[0].strip() for linha in arq.read_text(encoding="utf-8").splitlines())
    return [linha for linha in linhas if linha]


def ler_vocabulario() -> list[str]:
    """Nomes e termos do canal (vocabulario.txt), um por linha: os do programa mais os deste PC."""
    itens = []
    for arq in _sem_repetir(PASTA_PADRAO / "vocabulario.txt", PASTA_CONFIG / "vocabulario.txt"):
        for linha in _linhas_uteis(arq):
            if linha not in itens:
                itens.append(linha)
    return itens


def ler_correcoes() -> dict:
    """Correcoes automaticas (correcoes.txt): 'errado = certo'. As deste PC valem por cima das do programa."""
    out = {}
    for arq in _sem_repetir(PASTA_PADRAO / "correcoes.txt", PASTA_CONFIG / "correcoes.txt"):
        for linha in _linhas_uteis(arq):
            if "=" in linha:
                a, b = linha.split("=", 1)
                if a.strip():
                    out[a.strip().lower()] = b.strip()
    return out


# ------------------------------------------------------------------ janelas simples
def escolher_arquivo(titulo: str, pasta_inicial: Path) -> Path | None:
    import tkinter as tk
    from tkinter import filedialog

    raiz = tk.Tk()
    raiz.withdraw()
    raiz.attributes("-topmost", True)
    tipos = [("Videos", " ".join(f"*{e}" for e in sorted(EXTENSOES_VIDEO))), ("Todos", "*.*")]
    arq = filedialog.askopenfilename(title=titulo, initialdir=str(pasta_inicial), filetypes=tipos)
    raiz.destroy()
    return Path(arq) if arq else None


def escolher_pasta(titulo: str, pasta_inicial: Path) -> Path | None:
    import tkinter as tk
    from tkinter import filedialog

    raiz = tk.Tk()
    raiz.withdraw()
    raiz.attributes("-topmost", True)
    p = filedialog.askdirectory(title=titulo, initialdir=str(pasta_inicial))
    raiz.destroy()
    return Path(p) if p else None


def pausar_e_sair(codigo: int = 0):
    sys.exit(codigo)


def rodar(main):
    """Roda o main mostrando erros de forma amigavel e pausando no fim se pedido."""
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelado.")
    except SystemExit:
        pass
    except Exception as e:
        import traceback

        traceback.print_exc()
        from nucleo.registro import ARQ_LOG, registrar

        registrar(f"erro em {sys.argv[0]}", e)
        print(f"\n[ERRO] {e}\nTire um print desta janela e mande pro Claude.\n(detalhes em {ARQ_LOG})")
    finally:
        if PAUSAR:
            try:
                input("\nPressione ENTER para fechar...")
            except Exception:
                pass
