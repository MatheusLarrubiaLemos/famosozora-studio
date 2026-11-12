# Carrega o Whisper (transcricao): tenta a placa de video NVIDIA e, se nao der, usa o processador.
import glob
import os
import site

from nucleo.comum import DADOS_APP


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
    import numpy as np
    from faster_whisper import WhisperModel

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
    return (
        WhisperModel(
            _baixar_modelo(cfg["modelo_cpu"]),
            device="cpu",
            compute_type="int8",
            cpu_threads=max(1, os.cpu_count() or 4),
        ),
        "cpu",
    )
