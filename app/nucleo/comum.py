# Funcoes compartilhadas pelas ferramentas de Shorts do FamosoZora.
import json
import os
import re
import sys
from pathlib import Path

FERRAMENTAS = Path(__file__).resolve().parent.parent  # pasta do codigo (GitHub: app; instalado: ferramentas)
PASTA_APP = FERRAMENTAS.parent  # raiz do programa (app instalado ou pasta do GitHub)
# O programa e os seus arquivos ficam SEPARADOS:
#   - programa: instalado pelo .exe (ou a pasta do GitHub, no modo desenvolvedor)
#   - pasta de trabalho: videos, Shorts e configuracoes (padrao: Documentos\FamosoZora)
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
PASTA_CONFIG = PASTA_CANAL / "configuracoes"
PASTA_SHORTS = PASTA_CANAL / "shorts"
PASTA_VIDEOS = PASTA_CANAL / "videos"
PASTA_MUSICAS = PASTA_SHORTS / "musicas"

if PASTA_BIN.exists():  # ffmpeg que vem junto com o app
    os.environ["PATH"] = str(PASTA_BIN) + os.pathsep + os.environ.get("PATH", "")


def preparar_pasta_trabalho():
    """Cria a pasta de trabalho e copia as configuracoes e musicas padrao (nunca apaga nada)."""
    import shutil

    for p in (PASTA_CONFIG, PASTA_SHORTS, PASTA_VIDEOS, PASTA_MUSICAS):
        p.mkdir(parents=True, exist_ok=True)
    antiga = PASTA_SHORTS / "ferramentas"  # onde ficavam antes da versao 1.0
    for nome in ("config.json", "vocabulario.txt", "correcoes.txt"):
        destino = PASTA_CONFIG / nome
        if destino.exists():
            continue
        origem = antiga / nome if (antiga / nome).exists() else PASTA_PADRAO / nome
        if origem.exists():
            shutil.copy2(origem, destino)
    if not any(PASTA_MUSICAS.iterdir()):
        for m in (PASTA_APP / "musicas").glob("*"):
            shutil.copy2(m, PASTA_MUSICAS / m.name)


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
        "layout": "desfocado",
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
        "cores_falantes": ["branco", "ciano", "rosa", "verde", "laranja"],
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
        # video longo (episodio editado)
        "episodio_preset": "veryfast",  # x264 sem NVIDIA: ultrafast/superfast/veryfast/faster/fast/medium
        "episodio_crf": 20,
        "episodio_ajuste_silencio": 2.0,  # leva cada borda de corte para a pausa mais proxima (s; 0 desliga)
        "episodio_usar_abertura": True,
        "episodio_fade_preto": 0.35,  # fade para preto entre a abertura e o episodio (s)
    }
    arq = PASTA_CONFIG / "config.json"
    if arq.exists():
        try:
            padrao.update(json.loads(arq.read_text(encoding="utf-8")))
        except Exception as e:
            print(f"[AVISO] config.json com erro ({e}). Usando valores padrao.")
    return padrao


_CONFIG_COMPARTILHADA = None


def config_compartilhada() -> dict:
    """A mesma configuracao para todos os arquivos de um programa (quem muda um valor, muda para todos)."""
    global _CONFIG_COMPARTILHADA
    if _CONFIG_COMPARTILHADA is None:
        _CONFIG_COMPARTILHADA = carregar_config()
    return _CONFIG_COMPARTILHADA


def salvar_config(mudancas: dict):
    arq = PASTA_CONFIG / "config.json"
    atual = {}
    if arq.exists():
        try:
            atual = json.loads(arq.read_text(encoding="utf-8"))
        except Exception:
            pass
    atual.update(mudancas)
    arq.write_text(json.dumps(atual, ensure_ascii=False, indent=2), encoding="utf-8")


def ler_json(arq: Path, padrao=None):
    try:
        return json.loads(Path(arq).read_text(encoding="utf-8"))
    except Exception:
        return padrao


def gravar_json(arq: Path, dados):
    Path(arq).write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


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


def ler_vocabulario() -> list[str]:
    """Nomes e termos do canal (shorts\\ferramentas\\vocabulario.txt), um por linha."""
    arq = PASTA_CONFIG / "vocabulario.txt"
    if not arq.exists():
        return []
    itens = []
    for linha in arq.read_text(encoding="utf-8").splitlines():
        linha = linha.split("#")[0].strip()
        if linha:
            itens.append(linha)
    return itens


def ler_correcoes() -> dict:
    """Correcoes automaticas (shorts\\ferramentas\\correcoes.txt): 'errado = certo'."""
    arq = PASTA_CONFIG / "correcoes.txt"
    out = {}
    if arq.exists():
        for linha in arq.read_text(encoding="utf-8").splitlines():
            linha = linha.split("#")[0]
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
        print(f"\n[ERRO] {e}\nTire um print desta janela e mande pro Claude.")
    finally:
        if PAUSAR:
            try:
                input("\nPressione ENTER para fechar...")
            except Exception:
                pass
