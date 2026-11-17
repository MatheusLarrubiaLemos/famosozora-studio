# Passo 1: transcreve um video com o Whisper e salva tudo numa pasta dentro de "shorts".
# O video original so e LIDO.
import sys
import time
from datetime import datetime
from pathlib import Path

from nucleo.comum import (
    PASTA_SHORTS,
    PASTA_VIDEOS,
    carregar_config,
    escolher_arquivos,
    gravar_json,
    ler_json,
    ler_vocabulario,
    nome_seguro,
    pausar_e_sair,
    rodar,
    tempo_txt,
)
from nucleo.video import duracao_video, extrair_audio
from nucleo.whisper import carregar_whisper

CFG = carregar_config()
SEM_PERGUNTAS = "--sem-perguntas" in sys.argv  # usado pelo lote: nao pergunta nada no meio do caminho
if SEM_PERGUNTAS:
    sys.argv.remove("--sem-perguntas")


def srt_tempo(seg: float) -> str:
    return tempo_txt(seg, ms=True).replace(".", ",")


def escolher_videos() -> list:
    """Os videos vem da linha de comando (um ou varios, ex.: arrastados para o Studio) ou de uma janela."""
    if len(sys.argv) > 1:
        videos = [Path(a) for a in sys.argv[1:]]
    else:
        print("Escolha o video (ou varios: Ctrl + clique) na janela que abriu...")
        videos = escolher_arquivos(
            "Escolha o vídeo para transcrever (ou vários: Ctrl + clique, Shift + clique ou Ctrl + A)",
            PASTA_VIDEOS if PASTA_VIDEOS.exists() else PASTA_SHORTS,
        )
    videos = [v for v in videos if v and v.exists()]
    if not videos:
        print("Nenhum video escolhido.")
        pausar_e_sair(0)
    return videos


def pasta_do_projeto(video: Path) -> Path:
    """Pasta do projeto (dentro de shorts). Pergunta antes de substituir uma transcricao que ja existe."""
    pasta = PASTA_SHORTS / nome_seguro(video.stem)
    pasta.mkdir(parents=True, exist_ok=True)
    video_anterior = (ler_json(pasta / "projeto.json", {}) or {}).get("video")
    if video_anterior and Path(video_anterior) != video.resolve():
        print(f"\n[AVISO] Ja existe um projeto chamado '{pasta.name}', feito de OUTRO video:\n        {video_anterior}")
        print("        Se continuar, a transcricao dele sera substituida. Para manter os dois, renomeie este video.")
        if SEM_PERGUNTAS:
            print("[ERRO] Outro video ja usa esse nome de projeto. Renomeie o video e tente de novo.")
            pausar_e_sair(1)
        if input("Continuar mesmo assim? (s/N): ").strip().lower() != "s":
            return None
    if (pasta / "transcricao.json").exists() and SEM_PERGUNTAS:
        print("Transcrevendo de novo (pedido pelo lote).")
    elif (pasta / "transcricao.json").exists():
        r = input(f"\nEsse video ja foi transcrito em '{pasta.name}'. Transcrever de novo? (s/N): ").strip().lower()
        if r != "s":
            print("Ok, mantive a transcricao existente.")
            return None
    return pasta


def transcrever_audio(video: Path, total: float) -> list:
    """Roda o Whisper e devolve os segmentos (com o tempo de cada palavra), mostrando o progresso."""
    modelo, _ = carregar_whisper(CFG, [CFG["modelo_gpu"]])
    vocab = ler_vocabulario()
    inicio = time.time()
    print("Extraindo o audio do video (pode levar 1-2 minutos)...")
    audio = extrair_audio(video)
    print(f"Audio pronto ({tempo_txt(len(audio) / 16000)}). Transcrevendo...\n")
    opcoes = dict(
        language=CFG["idioma"],
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
        word_timestamps=True,
        beam_size=5,
        condition_on_previous_text=False,
    )
    if vocab:
        opcoes["hotwords"] = ", ".join(vocab)
    try:
        segmentos, _ = modelo.transcribe(audio, **opcoes)
    except TypeError:  # versao antiga sem 'hotwords'
        opcoes.pop("hotwords", None)
        segmentos, _ = modelo.transcribe(audio, **opcoes)

    dados = []
    for s in segmentos:
        palavras = [
            {"i": round(w.start, 3), "f": round(w.end, 3), "p": w.word.strip()}
            for w in (s.words or [])
            if w.word.strip()
        ]
        dados.append(
            {"inicio": round(s.start, 3), "fim": round(s.end, 3), "texto": s.text.strip(), "palavras": palavras}
        )
        pct = (s.end / total * 100) if total else 0
        decorrido = time.time() - inicio
        resta = (decorrido / s.end * (total - s.end)) if s.end > 0 and total else 0
        print(
            f"[{tempo_txt(s.end)} / {tempo_txt(total)}] {pct:5.1f}%  (falta ~{tempo_txt(resta)})  {s.text.strip()[:70]}"
        )
    return dados


def gravar_arquivos(pasta: Path, video: Path, total: float, dados: list):
    """transcricao.json, legenda .srt do video completo, texto para o Claude e projeto.json."""
    gravar_json(pasta / "transcricao.json", {"segmentos": dados})

    with open(pasta / "legenda_video_completo.srt", "w", encoding="utf-8") as f:
        for n, s in enumerate(dados, 1):
            f.write(f"{n}\n{srt_tempo(s['inicio'])} --> {srt_tempo(s['fim'])}\n{s['texto']}\n\n")

    with open(pasta / "transcricao_para_claude.txt", "w", encoding="utf-8") as f:
        f.write(f"VIDEO: {video.name}\nDURACAO: {tempo_txt(total)}\n")
        f.write("Formato: [inicio-fim] fala\n\n")
        for s in dados:
            f.write(f"[{tempo_txt(s['inicio'])}-{tempo_txt(s['fim'])}] {s['texto']}\n")

    projeto = ler_json(pasta / "projeto.json", {}) or {}
    projeto.update(
        {
            "video": str(video.resolve()),
            "duracao": total,
            "transcrito_em": datetime.now().isoformat(timespec="seconds"),
            "idioma": CFG["idioma"],
        }
    )
    gravar_json(pasta / "projeto.json", projeto)


def main():
    videos = escolher_videos()
    for k, video in enumerate(videos, 1):
        if len(videos) > 1:
            print(f"\n##### Video {k} de {len(videos)} #####")
        transcrever_video(video)


def transcrever_video(video: Path):
    pasta = pasta_do_projeto(video)
    if pasta is None:
        return
    total = duracao_video(video)
    print("=" * 60)
    print(f" Video:   {video.name}")
    print(f" Duracao: {tempo_txt(total)}")
    print(f" Saida:   {pasta}")
    print("=" * 60 + "\n")

    inicio = time.time()
    dados = transcrever_audio(video, total)
    gravar_arquivos(pasta, video, total, dados)

    print("\n" + "=" * 60)
    print(f" PRONTO em {tempo_txt(time.time() - inicio)}!")
    print(f" Pasta: {pasta}")
    print("  - legenda_video_completo.srt  (pode importar no CapCut)")
    print("  - transcricao_para_claude.txt (o Claude usa pra escolher os cortes)")
    print("\n Proximo passo: no Studio, clique em 'Pedir cortes ao Claude'.")
    print("=" * 60)


if __name__ == "__main__":
    rodar(main)
