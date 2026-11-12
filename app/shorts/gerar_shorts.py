# Passo 3: gera os Shorts no estilo "trailer" a partir do cortes.json (escrito pelo Claude):
#   gancho no inicio  ->  trecho com legenda precisa  ->  final borrado com INSCREVA-SE
#   + musica de fundo que abaixa sozinha quando alguem fala.
# O video original so e LIDO.
import subprocess
import sys
from pathlib import Path

from nucleo.comum import (
    PASTA_SHORTS,
    config_compartilhada,
    escolher_pasta,
    ler_correcoes,
    ler_json,
    ler_tempo,
    nome_seguro,
    pausar_e_sair,
    rodar,
    tempo_txt,
)
from nucleo.video import achar_programa, dimensoes_video, duracao_video, fps_video
from shorts.falantes import Falantes, marcar_palavras
from shorts.legendas import Retranscritor, montar_ass, palavras_do_trecho, relativas
from shorts.montagem import duracao_transicao, escolher_musica, montar_comando, testar_nvenc
from shorts.textos import salvar_publicacao

CFG = config_compartilhada()


# ================================================================== principal
def escolher_projeto():
    if len(sys.argv) > 1:
        return Path(sys.argv[1])
    candidatas = sorted(
        [p for p in PASTA_SHORTS.iterdir() if (p / "cortes.json").exists()],
        key=lambda p: (p / "cortes.json").stat().st_mtime,
        reverse=True,
    )
    if len(candidatas) == 1:
        return candidatas[0]
    if candidatas:
        print("Videos com cortes prontos:\n")
        for i, p in enumerate(candidatas, 1):
            print(f"  [{i}] {p.name}")
        r = input("\nNumero (ENTER = o mais recente): ").strip()
        return candidatas[int(r) - 1] if r.isdigit() and 1 <= int(r) <= len(candidatas) else candidatas[0]
    print("Nenhuma pasta com cortes.json encontrada. Escolha a pasta do video...")
    return escolher_pasta("Escolha a pasta do video (dentro de shorts)", PASTA_SHORTS)


def carregar_projeto(pasta: Path) -> dict:
    """Le tudo o que o projeto tem: video original, transcricao, cortes e correcoes."""
    if not pasta or not (pasta / "cortes.json").exists():
        print("\n[ERRO] Essa pasta nao tem cortes.json. Peca pro Claude escolher os cortes primeiro.")
        pausar_e_sair(1)
    projeto = ler_json(pasta / "projeto.json", {}) or {}
    video = Path(projeto.get("video", ""))
    if not video.exists():
        print(f"\n[ERRO] Nao achei o video original: {video}\nEle foi movido ou renomeado?")
        pausar_e_sair(1)
    segmentos = (ler_json(pasta / "transcricao.json", {}) or {}).get("segmentos", [])
    dados = ler_json(pasta / "cortes.json", {})
    if dados is None:
        print("\n[ERRO] O cortes.json esta com erro de formatacao. Peca pro Claude conferir.")
        pausar_e_sair(1)
    cortes = dados.get("cortes", []) if isinstance(dados, dict) else dados
    correcoes = {**ler_correcoes(), **(dados.get("correcoes", {}) if isinstance(dados, dict) else {})}
    return {
        "pasta": pasta,
        "projeto": projeto,
        "video": video,
        "segmentos": segmentos,
        "cortes": cortes,
        "correcoes": correcoes,
    }


def preparar_ferramentas(proj: dict) -> dict:
    """Mede o video e liga o que a geracao usa: ffmpeg, retranscricao, falantes e codificador."""
    video, pasta = proj["video"], proj["pasta"]
    ffmpeg = achar_programa("ffmpeg")
    src_w, src_h = dimensoes_video(video)
    dur_video = duracao_video(video)
    if CFG["layout"] == "camera" and not CFG.get("camera_area"):
        print("[AVISO] layout 'camera' escolhido, mas a camera ainda nao foi marcada.")
        print("        Use 'Marcar camera' no Studio. Usando o fundo desfocado por enquanto.\n")
        CFG["layout"] = "desfocado"
    retrans = Retranscritor(pasta)
    falantes = Falantes(pasta, CFG)
    fps = fps_video(video)
    cod = "nvenc" if testar_nvenc(ffmpeg) else "x264"
    return {
        "ffmpeg": ffmpeg,
        "src_w": src_w,
        "src_h": src_h,
        "dur_video": dur_video,
        "retrans": retrans,
        "falantes": falantes,
        "fps": fps,
        "cod": cod,
    }


def medir_corte(c: dict, n: int, dur_video: float) -> dict:
    """Tempos de um corte: inicio, fim, abertura, final e duracao total do Short.
    Da ValueError/KeyError se os tempos do corte forem invalidos."""
    ini, fim = ler_tempo(c["inicio"]), ler_tempo(c["fim"])
    titulo = c.get("titulo") or f"Corte {n}"
    nome = f"{n:02d} - {nome_seguro(titulo, 60)}.mp4"
    dur = fim - ini

    abertura = None
    ab = c.get("abertura")
    if ab and CFG.get("usar_abertura", True):
        try:
            a_ini, a_fim = ler_tempo(ab["inicio"]), ler_tempo(ab["fim"])
            if a_fim > a_ini:
                abertura = (a_ini, a_fim - a_ini)
        except Exception:
            print("   [AVISO] abertura com tempo invalido; ignorando.")
    final = float(CFG.get("duracao_final", 0) or 0)
    if dur_video > 0:
        final = max(0.0, min(final, dur_video - fim))
    D = duracao_transicao() if abertura else 0.0
    total = (abertura[1] if abertura else 0) + dur + final - D
    return {
        "n": n,
        "ini": ini,
        "fim": fim,
        "dur": dur,
        "titulo": titulo,
        "nome": nome,
        "abertura": abertura,
        "final": final,
        "D": D,
        "total": total,
    }


def legendas_do_corte(proj: dict, ferr: dict, c: dict, m: dict):
    """Palavras da legenda ja no tempo do Short. Retorna (blocos, instante em que comeca o final)."""
    video, segmentos, correcoes = proj["video"], proj["segmentos"], proj["correcoes"]
    retrans, falantes = ferr["retrans"], ferr["falantes"]
    ini, fim, dur, abertura, D = m["ini"], m["fim"], m["dur"], m["abertura"], m["D"]

    palavras = palavras_do_trecho(segmentos, retrans, video, ini, fim, c.get("legenda", ""), correcoes)
    marcar_palavras(palavras, falantes.trechos(video, ini, fim))
    blocos, off = [], 0.0
    if abertura:
        a_ini, a_dur = abertura
        if a_ini >= ini - 0.05 and a_ini + a_dur <= fim + 0.05:
            pa = [w for w in palavras if w["f"] > a_ini and w["i"] < a_ini + a_dur]
        else:
            pa = palavras_do_trecho(
                segmentos, retrans, video, a_ini, a_ini + a_dur, c.get("legenda_abertura", ""), correcoes
            )
            marcar_palavras(pa, falantes.trechos(video, a_ini, a_ini + a_dur))
        # na transicao (D segundos) as duas cenas se misturam: cada legenda fica com metade
        blocos.append((0.0, relativas(pa, a_ini, a_dur - D / 2), a_dur - D / 2))
        off = a_dur - D / 2
        blocos.append((off, relativas(palavras, ini + D / 2, dur - D / 2), dur - D / 2))
    else:
        blocos.append((off, relativas(palavras, ini, dur), dur))
    t_final = off + (dur - D / 2 if abertura else dur) if m["final"] > 0 else None
    return blocos, t_final


def renderizar_corte(proj: dict, ferr: dict, c: dict, m: dict, blocos, t_final, destino: Path) -> bool:
    """Escreve a legenda .ass e roda o ffmpeg. Retorna True se o Short ficou pronto."""
    pasta, video = proj["pasta"], proj["video"]
    (pasta / "temp_legenda.ass").write_text(
        montar_ass(blocos, c.get("texto_gancho", ""), m["titulo"], m["total"], t_final), encoding="utf-8"
    )
    musica = escolher_musica(c, m["n"], pasta.name)
    if musica:
        print(f"   musica: {musica.name}")
    temp_saida = destino.parent / f"_gerando_{m['n']:02d}.mp4"

    def rodar_ffmpeg(cod):
        cmd = montar_comando(
            ferr["ffmpeg"],
            video,
            ferr["src_w"],
            ferr["src_h"],
            m["ini"],
            m["dur"],
            m["abertura"],
            m["final"],
            musica,
            m["total"],
            temp_saida,
            cod,
            ferr["fps"],
        )
        return subprocess.run(cmd, cwd=str(pasta))

    r = rodar_ffmpeg(ferr["cod"])
    if r.returncode != 0 and ferr["cod"] == "nvenc":
        print("   [AVISO] a placa de video falhou nesse corte; tentando no processador...")
        r = rodar_ffmpeg("x264")
    if r.returncode == 0 and temp_saida.exists():
        temp_saida.replace(destino)
        return True
    if temp_saida.exists():
        temp_saida.unlink()
    print("   [ERRO] esse corte falhou.")
    return False


def main():
    proj = carregar_projeto(escolher_projeto())
    pasta, video, cortes = proj["pasta"], proj["video"], proj["cortes"]
    saida = pasta / "prontos"
    saida.mkdir(exist_ok=True)
    ferr = preparar_ferramentas(proj)

    print("=" * 60)
    print(f" Video:  {video.name}")
    print(f" Cortes: {len(cortes)}   Layout: {CFG['layout']}")
    print(" Codificando na: " + ("PLACA DE VIDEO (NVENC)" if ferr["cod"] == "nvenc" else "PROCESSADOR (x264)"))
    print(f" Saida:  {saida}")
    print("=" * 60 + "\n")

    feitos, pulados, erros = 0, 0, 0
    itens = []
    for n, c in enumerate(cortes, 1):
        try:
            m = medir_corte(c, n, ferr["dur_video"])
        except Exception:
            print(f"[{n}/{len(cortes)}] [ERRO] tempos invalidos: {c.get('inicio')} -> {c.get('fim')}")
            erros += 1
            continue
        itens.append((n, m["nome"], c, m["total"]))
        destino = saida / m["nome"]
        if destino.exists():
            print(f"[{n}/{len(cortes)}] ja existe, pulando: {m['nome']}")
            pulados += 1
            continue
        if m["dur"] <= 0:
            print(f"[{n}/{len(cortes)}] [ERRO] tempos invalidos ({c['inicio']} -> {c['fim']})")
            erros += 1
            continue
        print(
            f"[{n}/{len(cortes)}] {tempo_txt(m['ini'])} -> {tempo_txt(m['fim'])} ({m['dur']:.0f}s + final)  {m['titulo']}"
        )
        blocos, t_final = legendas_do_corte(proj, ferr, c, m)
        if renderizar_corte(proj, ferr, c, m, blocos, t_final, destino):
            feitos += 1
        else:
            erros += 1
    (pasta / "temp_legenda.ass").unlink(missing_ok=True)

    salvar_publicacao(pasta, saida, itens, proj["projeto"])

    print("\n" + "=" * 60)
    print(f" PRONTO! {feitos} criado(s), {pulados} ja existia(m), {erros} com erro.")
    print(f" Pasta: {saida}")
    print(" Textos pra postar: textos_para_postar.txt (ou botao 'Publicar' no Studio)")
    print("=" * 60)


if __name__ == "__main__":
    rodar(main)
