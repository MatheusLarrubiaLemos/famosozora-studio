# "Exportar para outro editor" (desde a 1.9.0): a mesma edicao do episodio, para terminar em outro programa.
#   --xml     -> episodio\outro_editor\episodio.xml (FCP7 XML / xmeml): abre no Premiere ("Importar") e no
#                DaVinci Resolve ("File > Import > Timeline"), ja com os cortes, apontando para o video ORIGINAL;
#   --trechos -> episodio\outro_editor\trecho_001.mp4, trecho_002.mp4... um arquivo por trecho que fica, com corte
#                exato (para arrastar no CapCut na ordem).
# NAO gera projeto do CapCut: o formato dele muda e as vezes vem criptografado (explicado no COMO USAR).
# Trecho acelerado vai na velocidade normal, com "(acelerar 2x)" no nome: a velocidade fica com voce no outro editor.
#
# Uso: python -m videos_longos.exportar_outro_editor <pasta do projeto> [--xml] [--trechos]
import subprocess
import sys
from fractions import Fraction
from pathlib import Path
from urllib.parse import quote
from xml.sax.saxutils import escape

from nucleo.comum import carregar_config, rodar, tempo_txt
from nucleo.video import achar_programa, dimensoes_video
from videos_longos.pedido_edicao import carregar_palavras, fps_fracao, info_video, ler_edicao, montar_plano


def _pathurl(arq: Path) -> str:
    caminho = Path(arq).resolve().as_posix()
    if not caminho.startswith("/"):
        caminho = "/" + caminho  # C:/... -> /C:/...
    return "file://localhost" + quote(caminho, safe="/:")


def _taxa(fps: Fraction) -> tuple[int, str]:
    """(timebase, ntsc) do xmeml: 29.97 = 30 + ntsc TRUE."""
    base = round(float(fps))
    ntsc = "TRUE" if abs(float(fps) - base) > 0.001 else "FALSE"
    return base, ntsc


def xml_fcp7(plano: dict, video: Path, titulo: str, largura: int, altura: int) -> str:
    """O XML (xmeml versao 5) com um clipe por trecho que fica, em sequencia."""
    fps = plano["fps"]
    base, ntsc = _taxa(fps)
    rate = f"<rate><timebase>{base}</timebase><ntsc>{ntsc}</ntsc></rate>"
    total_orig = int(round(plano["dur_original"] * float(fps)))
    vel = plano.get("velocidades") or {}
    trilhas = {"video": [], "audio": []}
    pos = 0
    for k, (q, n) in enumerate(plano["trechos"]):
        nome = f"trecho {k + 1}" + (f" (acelerar {vel[k]:g}x)" if k in vel else "")
        for tipo in ("video", "audio"):
            arquivo = (f'<file id="original"><name>{escape(video.name)}</name><pathurl>{escape(_pathurl(video))}'
                       f"</pathurl>{rate}<duration>{total_orig}</duration><media><video><samplecharacteristics>"
                       f"<width>{largura}</width><height>{altura}</height></samplecharacteristics></video><audio>"
                       "<channelcount>2</channelcount></audio></media></file>"
                       if k == 0 and tipo == "video" else '<file id="original"/>')  # fmt: skip
            extra = "<sourcetrack><mediatype>audio</mediatype><trackindex>1</trackindex></sourcetrack>" if (
                tipo == "audio") else ""  # fmt: skip
            trilhas[tipo].append(
                f'<clipitem id="{tipo}_{k + 1}"><name>{escape(nome)}</name><enabled>TRUE</enabled>'
                f"<duration>{total_orig}</duration>{rate}<start>{pos}</start><end>{pos + n}</end>"
                f"<in>{q}</in><out>{q + n}</out>{arquivo}{extra}</clipitem>"
            )
        pos += n
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n<xmeml version="5">'
        f'<sequence id="episodio"><name>{escape(titulo)}</name><duration>{pos}</duration>{rate}'
        f"<media><video><format><samplecharacteristics>{rate}<width>{largura}</width><height>{altura}</height>"
        f"</samplecharacteristics></format><track>{''.join(trilhas['video'])}</track></video>"
        f"<audio><track>{''.join(trilhas['audio'])}</track></audio></media></sequence></xmeml>\n"
    )


def exportar_trechos(plano: dict, video: Path, pasta: Path, cfg: dict) -> list:
    """Um MP4 por trecho que fica (corte exato, recodificado). Devolve os arquivos."""
    ffmpeg = achar_programa("ffmpeg")
    fps = plano["fps"]
    vel = plano.get("velocidades") or {}
    for velho in pasta.glob("trecho_*.mp4"):
        velho.unlink(missing_ok=True)
    feitos = []
    total = len(plano["trechos"])
    for k, (q, n) in enumerate(plano["trechos"], 0):
        nome = f"trecho_{k + 1:03d}" + (f" (acelerar {vel[k]:g}x)" if k in vel else "") + ".mp4"
        destino = pasta / nome
        cmd = [ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{float(q / fps):.6f}",
               "-i", str(video), "-frames:v", str(n), "-t", f"{float(n / fps):.6f}", "-map", "0:v:0", "-map", "0:a:0?",
               "-c:v", "libx264", "-preset", str(cfg.get("episodio_preset", "veryfast")), "-crf", "18",
               "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", str(destino)]  # fmt: skip
        r = subprocess.run(cmd)
        if r.returncode != 0:
            print(f"[ERRO] o trecho {k + 1} falhou.")
            sys.exit(1)
        feitos.append(destino)
        print(f"[{k + 1}/{total}] {nome}  ({tempo_txt(float(n / fps))})", flush=True)
    return feitos


def main():
    args = sys.argv[1:]
    if not args:
        print("Uso: python -m videos_longos.exportar_outro_editor <pasta do projeto> [--xml] [--trechos]")
        sys.exit(1)
    pasta = Path(args[0])
    fazer_xml = "--xml" in args or "--trechos" not in args
    fazer_trechos = "--trechos" in args
    video, dur = info_video(pasta)
    if not video.exists():
        print(f"[ERRO] Não achei o vídeo original: {video}")
        sys.exit(1)
    dados, erros, _ = ler_edicao(pasta, dur)
    if erros:
        print("[ERRO] O edicao.json tem problemas:\n- " + "\n- ".join(erros))
        sys.exit(1)
    cfg = carregar_config()
    plano = montar_plano(dados, dur, fps_fracao(video), carregar_palavras(pasta), cfg)
    saida = pasta / "episodio" / "outro_editor"
    saida.mkdir(parents=True, exist_ok=True)
    titulo = str(dados.get("titulo") or pasta.name)
    print(f"{len(plano['trechos'])} trecho(s) ficam: {tempo_txt(plano['dur_final'])} (o original tem {tempo_txt(dur)})")
    if fazer_xml:
        largura, altura = dimensoes_video(video)
        (saida / "episodio.xml").write_text(xml_fcp7(plano, video, titulo, largura, altura), encoding="utf-8")
        print(f"XML pronto: {saida / 'episodio.xml'}  (Premiere: Arquivo > Importar; DaVinci: File > Import > "
              "Timeline)")  # fmt: skip
    if fazer_trechos:
        exportar_trechos(plano, video, saida, cfg)
        print(f"Trechos prontos em: {saida}  (arraste no CapCut na ordem dos números)")


if __name__ == "__main__":
    rodar(main)
