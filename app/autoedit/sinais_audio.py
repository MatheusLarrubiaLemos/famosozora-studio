# Sinais de AUDIO do Auto-Edit (Fase 1B), numa leitura so do som do video:
#   - volume a cada 0,1 s (0 a 1; 0 = -60 dB ou menos, 1 = 0 dB), para saber se o jogo esta fazendo barulho;
#   - onda de som para a timeline do editor (pico a cada 10 ms, guardado em base64 para o arquivo ficar pequeno);
#   - reforco da fala com o detector de voz (VAD Silero que ja vem no faster-whisper, licenca MIT), se existir.
# A fala principal vem dos tempos das palavras da transcricao (decidir_cortes.py junta as duas).
# Saida: analise\som.json (ou som_<ini>-<fim>.json numa janela de Short).
import base64
import math
from pathlib import Path

from autoedit.base import PASSO, cache_valido, gravar_cache, ler_cru, progresso
from nucleo.video import achar_programa

VERSAO = 1
TAXA = 16000  # amostras por segundo (o VAD precisa de 16 kHz)
PICO_MS = 10  # um pico da onda a cada 10 ms
BLOCO_VAD = 30.0  # segundos por pedaco mandado ao VAD


def _vad():
    """Funcao do VAD do faster-whisper, ou None se a biblioteca nao estiver instalada."""
    try:
        from faster_whisper.vad import VadOptions, get_speech_timestamps
    except Exception:
        return None

    def falas(audio):
        opcoes = VadOptions(min_silence_duration_ms=300, speech_pad_ms=100)
        return [(s["start"] / TAXA, s["end"] / TAXA) for s in get_speech_timestamps(audio, opcoes)]

    return falas


def nome_arquivo(inicio: float, fim: float | None) -> str:
    return "som.json" if not inicio and fim is None else f"som_{inicio:.1f}-{fim:.1f}.json"


def medir(video: Path, pasta_analise: Path, duracao: float, inicio: float = 0.0, fim: float | None = None,
          usar_vad: bool = True, cancelar=None, etapa=(1, 1)) -> dict:  # fmt: skip
    """Mede (ou le do cache) os sinais de audio de [inicio, fim] (fim None = ate o fim do video)."""
    import numpy as np

    arq = Path(pasta_analise) / nome_arquivo(inicio, fim)
    ajustes = {"inicio": round(inicio, 2), "fim": None if fim is None else round(fim, 2), "vad": bool(usar_vad)}
    pronto = cache_valido(arq, video, VERSAO, ajustes)
    if pronto:
        return pronto
    dur = (fim if fim is not None else duracao) - inicio
    cmd = [achar_programa("ffmpeg"), "-hide_banner", "-nostdin", "-loglevel", "error", "-ss", f"{inicio:.3f}"]
    if fim is not None:
        cmd += ["-t", f"{dur:.3f}"]
    cmd += ["-i", str(video), "-map", "0:a:0", "-vn", "-ac", "1", "-ar", str(TAXA), "-f", "s16le", "-"]

    por_passo = int(TAXA * PASSO)
    por_pico = int(TAXA * PICO_MS / 1000)
    volumes, picos, falas_vad = [], [], []
    vad = _vad() if usar_vad else None
    estado = {"lidos": 0, "buffer_vad": [], "base_vad": 0.0}
    nome = "Som do jogo e voz"

    def ao_ler(cru: bytes):
        a = np.frombuffer(cru, dtype=np.int16).astype(np.float32) / 32768.0
        for k in range(0, len(a) - por_passo + 1, por_passo):
            rms = float(np.sqrt(np.mean(a[k : k + por_passo] ** 2)) + 1e-9)
            volumes.append(round(min(1.0, max(0.0, (20 * math.log10(rms) + 60) / 60)), 3))
        n = len(a) // por_pico * por_pico
        if n:
            picos.extend(np.minimum(255, np.abs(a[:n]).reshape(-1, por_pico).max(axis=1) * 255).astype(np.uint8))
        if vad is not None:
            estado["buffer_vad"].append(a)
            if sum(len(b) for b in estado["buffer_vad"]) >= BLOCO_VAD * TAXA:
                _rodar_vad()
        estado["lidos"] += len(a)
        progresso(*etapa, nome, estado["lidos"] / TAXA / max(0.1, dur))

    def _rodar_vad():
        if not estado["buffer_vad"]:
            return
        bloco = np.concatenate(estado["buffer_vad"])
        try:
            for a, b in vad(bloco):
                falas_vad.append((round(estado["base_vad"] + a, 2), round(estado["base_vad"] + b, 2)))
        except Exception:
            pass  # o VAD falhou neste pedaco: fica so a transcricao
        estado["base_vad"] += len(bloco) / TAXA
        estado["buffer_vad"] = []

    ler_cru(cmd, por_passo * 2, ao_ler, cancelar)  # 2 bytes por amostra
    if vad is not None:
        _rodar_vad()
    dados = {
        "inicio": inicio,
        "passo": PASSO,
        "volume": volumes,
        "onda_ms": PICO_MS,
        "onda": base64.b64encode(bytes(picos)).decode("ascii"),
        "fala_vad": [[inicio + a, inicio + b] for a, b in falas_vad] if vad is not None else None,
    }
    gravar_cache(arq, video, VERSAO, dados, ajustes)
    progresso(*etapa, nome, 1.0)
    return {"versao": VERSAO, "ajustes": ajustes, **dados}


def onda(dados: dict):
    """Os picos da onda (bytes, 0 a 255), um a cada dados["onda_ms"] milissegundos."""
    return base64.b64decode(dados.get("onda") or b"")
