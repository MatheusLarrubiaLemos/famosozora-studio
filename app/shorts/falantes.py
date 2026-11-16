# Descobre QUEM esta falando em cada parte do corte (diarizacao), para pintar a legenda
# com uma cor por pessoa. Roda no processador, com modelos pequenos (~50 MB, baixados 1 vez).
import shutil
import tarfile
from pathlib import Path

from nucleo.comum import DADOS_APP, abrir_url, gravar_json, ler_json
from nucleo.video import extrair_audio

PASTA_MODELOS = DADOS_APP / "modelos" / "falantes"
_BASE = "https://github.com/k2-fsa/sherpa-onnx/releases/download"
URL_SEGMENTACAO = f"{_BASE}/speaker-segmentation-models/sherpa-onnx-pyannote-segmentation-3-0.tar.bz2"
URL_VOZES = f"{_BASE}/speaker-recongition-models/3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx"
ARQ_SEGMENTACAO = PASTA_MODELOS / "sherpa-onnx-pyannote-segmentation-3-0" / "model.int8.onnx"
ARQ_VOZES = PASTA_MODELOS / "vozes_eres2net.onnx"


def _baixar(url: str, destino: Path):
    tmp = destino.with_name(destino.name + ".baixando")
    print(f"   baixando {destino.name} (so na primeira vez)...")
    with abrir_url(url, 60) as resposta, open(tmp, "wb") as saida:
        shutil.copyfileobj(resposta, saida)
    tmp.replace(destino)


def _garantir_modelos():
    PASTA_MODELOS.mkdir(parents=True, exist_ok=True)
    if not ARQ_SEGMENTACAO.exists():
        tar = PASTA_MODELOS / "segmentacao.tar.bz2"
        _baixar(URL_SEGMENTACAO, tar)
        with tarfile.open(tar) as t:
            t.extractall(PASTA_MODELOS, filter="data")
        tar.unlink(missing_ok=True)
    if not ARQ_VOZES.exists():
        _baixar(URL_VOZES, ARQ_VOZES)


class Falantes:
    """Uso: f = Falantes(pasta, cfg); trechos = f.trechos(video, ini, fim) -> [(i, f, id), ...]"""

    def __init__(self, pasta: Path, cfg: dict):
        self.ativo = bool(cfg.get("cor_por_falante", True))
        self.limiar = float(cfg.get("sensibilidade_falantes", 0.9))
        self.arq = pasta / "falantes_cache.json"
        self.cache = ler_json(self.arq, {}) or {}
        self.sd = None
        self.falhou = False

    def _carregar(self):
        import sherpa_onnx

        _garantir_modelos()
        cfg = sherpa_onnx.OfflineSpeakerDiarizationConfig(
            segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
                pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(model=str(ARQ_SEGMENTACAO))
            ),
            embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(ARQ_VOZES)),
            clustering=sherpa_onnx.FastClusteringConfig(num_clusters=-1, threshold=self.limiar),
            min_duration_on=0.3,
            min_duration_off=0.5,
        )
        if not cfg.validate():
            raise RuntimeError("configuracao dos modelos de voz invalida")
        self.sd = sherpa_onnx.OfflineSpeakerDiarization(cfg)

    def trechos(self, video: Path, ini: float, fim: float):
        if not self.ativo or self.falhou:
            return []
        chave = f"{ini:.2f}-{fim:.2f}-{self.limiar}"
        if chave in self.cache:
            return [tuple(t) for t in self.cache[chave]]
        try:
            if self.sd is None:
                print("   identificando quem fala (cor da legenda por pessoa)...")
                self._carregar()
            audio = extrair_audio(video, ini, fim - ini)
            res = self.sd.process(audio).sort_by_start_time()
            out = [(round(ini + r.start, 3), round(ini + r.end, 3), int(r.speaker)) for r in res]
        except Exception as e:
            print(f"   [AVISO] nao consegui separar as vozes ({str(e)[:120]}); legenda numa cor so.")
            self.falhou = True
            return []
        self.cache[chave] = out
        gravar_json(self.arq, self.cache)
        return out


def marcar_palavras(palavras, trechos, prefixo: str = ""):
    """Coloca w['s'] (id do falante) em cada palavra, pelo trecho que mais se sobrepoe a ela.
    prefixo "a" = abertura detectada a parte: as vozes viram "a0", "a1"... para nao se misturar com as do corte."""
    if not trechos:
        return palavras
    for w in palavras:
        melhor, sobra = None, 0.0
        meio = (w["i"] + w["f"]) / 2
        for a, b, spk in trechos:
            sob = min(b, w["f"]) - max(a, w["i"])
            if sob > sobra:
                melhor, sobra = spk, sob
        if melhor is None:  # palavra num buraco: pega o trecho mais perto
            melhor = min(trechos, key=lambda t: min(abs(meio - t[0]), abs(meio - t[1])))[2]
        w["s"] = f"{prefixo}{melhor}" if prefixo else melhor
    return palavras
