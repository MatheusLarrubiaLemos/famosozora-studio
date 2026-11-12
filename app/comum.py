# Funcoes compartilhadas pelas ferramentas de Shorts do FamosoZora.
import glob
import json
import os
import re
import site
import subprocess
import sys
from pathlib import Path

from versao import VERSAO

FERRAMENTAS = Path(__file__).resolve().parent       # onde estao os scripts (app instalado: ...\ferramentas)
PASTA_APP = FERRAMENTAS.parent                       # raiz do programa (app instalado ou pasta do GitHub)
# O programa e os seus arquivos ficam SEPARADOS:
#   - programa: instalado pelo .exe (ou a pasta do GitHub, no modo desenvolvedor)
#   - pasta de trabalho: videos, Shorts e configuracoes (padrao: Documentos\FamosoZora)
APP_INSTALADO = (FERRAMENTAS / "APP_INSTALADO").exists()   # False = rodando da pasta do GitHub
PASTA_BIN = PASTA_APP / "bin"                        # app: ffmpeg.exe e ffprobe.exe
PASTA_PADRAO = FERRAMENTAS / "padrao"                # configuracoes iniciais (config.json etc.)
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


PASTA_CANAL = Path(ler_ajustes().get("pasta_trabalho") or pasta_trabalho_padrao())   # pasta de trabalho
PASTA_CONFIG = PASTA_CANAL / "configuracoes"
PASTA_SHORTS = PASTA_CANAL / "shorts"
PASTA_VIDEOS = PASTA_CANAL / "videos"
PASTA_MUSICAS = PASTA_SHORTS / "musicas"

if PASTA_BIN.exists():                                # ffmpeg que vem junto com o app
    os.environ["PATH"] = str(PASTA_BIN) + os.pathsep + os.environ.get("PATH", "")


def preparar_pasta_trabalho():
    """Cria a pasta de trabalho e copia as configuracoes e musicas padrao (nunca apaga nada)."""
    import shutil
    for p in (PASTA_CONFIG, PASTA_SHORTS, PASTA_VIDEOS, PASTA_MUSICAS):
        p.mkdir(parents=True, exist_ok=True)
    antiga = PASTA_SHORTS / "ferramentas"            # onde ficavam antes da versao 1.0
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
        "episodio_preset": "veryfast",          # x264 sem NVIDIA: ultrafast/superfast/veryfast/faster/fast/medium
        "episodio_crf": 20,
        "episodio_ajuste_silencio": 2.0,        # leva cada borda de corte para a pausa mais proxima (s; 0 desliga)
        "episodio_usar_abertura": True,
        "episodio_fade_preto": 0.35,            # fade para preto entre a abertura e o episodio (s)
    }
    arq = PASTA_CONFIG / "config.json"
    if arq.exists():
        try:
            padrao.update(json.loads(arq.read_text(encoding="utf-8")))
        except Exception as e:
            print(f"[AVISO] config.json com erro ({e}). Usando valores padrao.")
    return padrao


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
    texto = "".join(ch for ch in texto if ord(ch) < 0x2000)   # tira emojis e simbolos
    texto = re.sub(r'[\\/:*?"<>|\r\n\t]', "", texto).strip().rstrip(".")
    texto = re.sub(r"\s+", " ", texto)
    return (texto[:limite].strip() or "sem_nome")


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


# ------------------------------------------------------------------ programas e videos
def achar_programa(nome: str) -> str:
    from shutil import which
    for ext in (".exe", ""):
        if (PASTA_BIN / f"{nome}{ext}").exists():
            return str(PASTA_BIN / f"{nome}{ext}")
    caminho = which(nome)
    if caminho:
        return caminho
    links = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Links" / f"{nome}.exe"
    if links.exists():
        return str(links)
    print(f"\n[ERRO] Nao encontrei o {nome}. Rode o instalador (botao 'Instalar / atualizar' no Studio).")
    pausar_e_sair(1)


def duracao_video(video: Path) -> float:
    ffprobe = achar_programa("ffprobe")
    r = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(video)],
        capture_output=True, text=True,
    )
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def dimensoes_video(video: Path) -> tuple[int, int]:
    ffprobe = achar_programa("ffprobe")
    r = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
         "-of", "csv=p=0:s=x", str(video)],
        capture_output=True, text=True,
    )
    try:
        w, h = r.stdout.strip().split("x")[:2]
        return int(w), int(h)
    except Exception:
        return 1920, 1080


def extrair_audio(video: Path, inicio: float | None = None, duracao: float | None = None):
    """Audio 16 kHz mono como numpy float32 (sem depender do PyAV)."""
    import numpy as np
    ffmpeg = achar_programa("ffmpeg")
    cmd = [ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error"]
    if inicio is not None:
        cmd += ["-ss", f"{max(0.0, inicio):.3f}"]
    cmd += ["-i", str(video)]
    if duracao is not None:
        cmd += ["-t", f"{duracao:.3f}"]
    cmd += ["-map", "0:a:0", "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0 or not r.stdout:
        raise RuntimeError("ffmpeg nao conseguiu extrair o audio: " + r.stderr.decode("utf-8", "ignore")[-300:])
    return np.frombuffer(r.stdout, dtype=np.int16).astype(np.float32) / 32768.0


# ------------------------------------------------------------------ whisper
def _liberar_dlls_cuda():
    pastas = list(site.getsitepackages())
    try:
        pastas.append(site.getusersitepackages())
    except Exception:
        pass
    pastas.append(str(DADOS_APP / "gpu"))
    for sp in pastas:
        for b in glob.glob(os.path.join(sp, "nvidia", "*", "bin")):
            try:
                os.add_dll_directory(b)
            except Exception:
                pass
            os.environ["PATH"] = b + os.pathsep + os.environ.get("PATH", "")


_PADROES_MODELO = ["config.json", "preprocessor_config.json", "model.bin", "tokenizer.json", "vocabulary.*"]


def _baixar_modelo(nome: str) -> str:
    """Baixa o modelo mostrando a barra de progresso (o faster-whisper esconde a barra).
    Se ja estiver baixado, so devolve a pasta, sem usar a internet."""
    try:
        from faster_whisper.utils import _MODELS
        from huggingface_hub import snapshot_download
    except Exception:
        return nome
    repo = _MODELS.get(nome)
    if not repo:
        return nome
    try:
        return snapshot_download(repo, allow_patterns=_PADROES_MODELO, local_files_only=True)
    except Exception:
        pass
    print(f"Baixando o modelo {nome} (so na primeira vez; pode ter alguns GB, aguarde)...")
    return snapshot_download(repo, allow_patterns=_PADROES_MODELO)


def carregar_whisper(cfg: dict, modelos_gpu: list[str], permitir_cpu: bool = True):
    """Tenta a placa de video com cada modelo da lista; se nao der, usa o processador.
    Retorna (modelo, 'cuda'|'cpu') ou (None, None)."""
    from faster_whisper import WhisperModel
    import numpy as np

    if cfg.get("dispositivo", "auto") in ("auto", "cuda", "gpu"):
        _liberar_dlls_cuda()
        for nome in modelos_gpu:
            try:
                print(f"Carregando o modelo {nome} na placa de video...")
                m = WhisperModel(_baixar_modelo(nome), device="cuda", compute_type="float16")
                segs, _ = m.transcribe(np.zeros(16000, dtype=np.float32), language=cfg["idioma"], vad_filter=False)
                list(segs)
                print("-> Usando a PLACA DE VIDEO.\n")
                return m, "cuda"
            except Exception as e:
                print(f"-> Nao deu com {nome} na placa de video ({str(e).splitlines()[0][:100]}).")
    if not permitir_cpu:
        return None, None
    print(f"Usando o PROCESSADOR (modelo {cfg['modelo_cpu']}). Isso e mais lento.\n")
    return WhisperModel(_baixar_modelo(cfg["modelo_cpu"]), device="cpu", compute_type="int8",
                        cpu_threads=max(1, os.cpu_count() or 4)), "cpu"


# ------------------------------------------------------------------ layout 9:16
def _crop_area(area, src_w: int, src_h: int) -> str:
    """area = [x, y, w, h] normalizados (0 a 1). Retorna 'crop=w:h:x:y' em pixels pares."""
    x, y, w, h = area
    pw = max(2, int(w * src_w) // 2 * 2)
    ph = max(2, int(h * src_h) // 2 * 2)
    px = min(max(0, int(x * src_w)), src_w - pw)
    py = min(max(0, int(y * src_h)), src_h - ph)
    return f"crop={pw}:{ph}:{px}:{py}"


def filtro_layout(cfg: dict, src_w: int, src_h: int, larg: int = 1080, alt: int = 1920,
                  entrada: str = "0:v", sufixo: str = "") -> str:
    """Monta o filtro de video 9:16 (sem o rotulo de saida)."""
    s = sufixo
    layout = cfg.get("layout", "desfocado")
    if layout == "camera" and cfg.get("camera_area"):
        hc = int(cfg.get("altura_camera", 600)) // 2 * 2
        hj = alt - hc
        cam = _crop_area(cfg["camera_area"], src_w, src_h)
        jogo = _crop_area(cfg["gameplay_area"], src_w, src_h) + "," if cfg.get("gameplay_area") else ""
        return (f"[{entrada}]split=2[c{s}][g{s}];"
                f"[c{s}]{cam},scale={larg}:{hc}:force_original_aspect_ratio=increase,crop={larg}:{hc},setsar=1[cam{s}];"
                f"[g{s}]{jogo}scale={larg}:{hj}:force_original_aspect_ratio=increase,crop={larg}:{hj},setsar=1[jogo{s}];"
                f"[cam{s}][jogo{s}]vstack=inputs=2")
    if layout == "recorte":
        return f"[{entrada}]scale=-2:{alt},crop={larg}:{alt}"
    return (f"[{entrada}]split=2[a{s}][b{s}];"
            f"[a{s}]scale={larg}:{alt}:force_original_aspect_ratio=increase,crop={larg}:{alt},"
            f"boxblur=20:2,eq=brightness=-0.10[fundo{s}];"
            f"[b{s}]scale={larg}:-2[frente{s}];"
            f"[fundo{s}][frente{s}]overlay=(W-w)/2:(H-h)/2")


# ------------------------------------------------------------------ janelas simples
def escolher_arquivo(titulo: str, pasta_inicial: Path) -> Path | None:
    import tkinter as tk
    from tkinter import filedialog
    raiz = tk.Tk(); raiz.withdraw(); raiz.attributes("-topmost", True)
    tipos = [("Videos", " ".join(f"*{e}" for e in sorted(EXTENSOES_VIDEO))), ("Todos", "*.*")]
    arq = filedialog.askopenfilename(title=titulo, initialdir=str(pasta_inicial), filetypes=tipos)
    raiz.destroy()
    return Path(arq) if arq else None


def escolher_pasta(titulo: str, pasta_inicial: Path) -> Path | None:
    import tkinter as tk
    from tkinter import filedialog
    raiz = tk.Tk(); raiz.withdraw(); raiz.attributes("-topmost", True)
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
