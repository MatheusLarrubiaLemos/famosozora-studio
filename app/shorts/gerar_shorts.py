# Passo 3: gera os Shorts no estilo "trailer" a partir do cortes.json (escrito pelo Claude):
#   gancho no inicio  ->  trecho com legenda precisa  ->  final borrado com INSCREVA-SE
#   + musica de fundo que abaixa sozinha quando alguem fala.
# Enquanto o ffmpeg monta um Short, a legenda do proximo (Whisper e detector de vozes) ja vai sendo preparada
# ("shorts_preparar_enquanto_renderiza" no config.json; false = um de cada vez, como antes).
# O video original so e LIDO.
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
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
from shorts import audio_short, biblioteca
from shorts import edicao as edicao_short
from shorts.censura import aplicar as censurar
from shorts.censura import trechos_para_calar
from shorts.cortes import MENSAGEM_ZERO, clima_do, escolhidos, ler_cortes, maximo_de_shorts
from shorts.falantes import Falantes, marcar_palavras
from shorts.legendas import Retranscritor, montar_ass, palavras_do_trecho, relativas
from shorts.montagem import duracao_transicao, montar_comando, testar_nvenc
from shorts.pessoas import quem_fala
from shorts.revisao import editada_do_trecho, salvar_original
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
    dados = ler_cortes(pasta)  # None = arquivo com erro de formatacao; formato antigo e migrado sozinho
    if dados is None:
        print("\n[ERRO] O cortes.json esta com erro de formatacao. Peca pro Claude conferir.")
        pausar_e_sair(1)
    cortes = dados["cortes"] if isinstance(dados["cortes"], list) else []
    correcoes = {**ler_correcoes(), **(dados.get("correcoes") or {})}
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

    editada = editada_do_trecho(proj["pasta"], m["n"], ini, fim)  # so a deste trecho (cortes novos: nao vale)
    if editada:  # revisada a mao no editor de legendas: vale ela, sem refazer transcricao nem alinhamento
        print("   usando a legenda revisada a mao")
        palavras = [dict(w) for w in editada["palavras"]]
    else:
        palavras = palavras_do_trecho(segmentos, retrans, video, ini, fim, c.get("legenda", ""), correcoes)
        marcar_palavras(palavras, falantes.trechos(video, ini, fim))
        salvar_original(proj["pasta"], m["n"], m["nome"], ini, fim, palavras)
    palavras = censurar(palavras, bool(editada and editada.get("censurar_lista")))
    blocos, off = [], 0.0
    if abertura:
        a_ini, a_dur = abertura
        if a_ini >= ini - 0.05 and a_ini + a_dur <= fim + 0.05:
            pa = [w for w in palavras if w["f"] > a_ini and w["i"] < a_ini + a_dur]
        else:
            pa = palavras_do_trecho(
                segmentos, retrans, video, a_ini, a_ini + a_dur, c.get("legenda_abertura", ""), correcoes
            )
            marcar_palavras(pa, falantes.trechos(video, a_ini, a_ini + a_dur), prefixo="a")
        # na transicao (D segundos) as duas cenas se misturam: cada legenda fica com metade
        blocos.append((0.0, relativas(pa, a_ini, a_dur - D / 2), a_dur - D / 2))
        off = a_dur - D / 2
        blocos.append((off, relativas(palavras, ini + D / 2, dur - D / 2), dur - D / 2))
    else:
        blocos.append((off, relativas(palavras, ini, dur), dur))
    t_final = off + (dur - D / 2 if abertura else dur) if m["final"] > 0 else None
    return blocos, t_final


def edicao_do_corte(proj: dict, c: dict, m: dict, refazer_sugestao: bool) -> dict:
    """Grava a sugestao do Short (musica do clima e efeitos do Claude) e devolve a edicao que vale:
    a sua (feita no editor), se for deste trecho; senao a sugestao.
    refazer_sugestao=False (render de um Short so): mantem a sugestao que ja existe."""
    pasta, n = proj["pasta"], m["n"]
    sug = edicao_short.ler_sugestao(pasta, n)
    if refazer_sugestao or sug is None or not edicao_short.mesmo_corte(sug, m["ini"], m["fim"]):
        sug = audio_short.sugestao(c, m, proj["plano_musicas"].get(n, ""), pasta.name)
        edicao_short.salvar_sugestao(pasta, n, sug)
    return edicao_short.valendo(pasta, n, m["ini"], m["fim"]) or sug


def sugestao_sem_render(pasta: Path, n: int):
    """Sugestao do Short n montada do mesmo jeito que o render faz (para o editor, em Short gerado antes da 1.4.0).
    Grava o NN_sugestao.json e devolve a sugestao, ou None se o corte nao existe ou tem tempo invalido."""
    dados = ler_cortes(pasta, gravar_migracao=False) or {"cortes": []}
    cortes = dados["cortes"] if isinstance(dados["cortes"], list) else []
    if not 0 < n <= len(cortes) or not isinstance(cortes[n - 1], dict):
        return None
    try:
        m = medir_corte(cortes[n - 1], n, float((ler_json(pasta / "projeto.json", {}) or {}).get("duracao") or 0))
    except (KeyError, TypeError, ValueError):
        return None
    biblioteca.preparar_pastas()
    plano = biblioteca.planejar_musicas(
        cortes, [clima_do(c) if isinstance(c, dict) else "" for c in cortes], pasta.name, CFG.get("musica")
    )
    sug = audio_short.sugestao(cortes[n - 1], m, plano.get(n, ""), pasta.name)
    edicao_short.salvar_sugestao(pasta, n, sug)
    return sug


def renderizar_corte(proj: dict, ferr: dict, c: dict, m: dict, blocos, t_final, destino: Path, ed=None) -> bool:
    """Escreve a legenda .ass e roda o ffmpeg. Retorna True se o Short ficou pronto."""
    pasta, video = proj["pasta"], proj["video"]
    arq_ass = pasta / f"temp_legenda_{m['n']:02d}.ass"  # um por Short: da para gerar dois ao mesmo tempo
    ed = ed or edicao_short.vazia()
    arq_ass.write_text(
        montar_ass(blocos, c.get("texto_gancho", ""), m["titulo"], m["total"], t_final,
                   quem=quem_fala(pasta, m["n"], m["ini"], m["fim"]), mostrar_nome=ed["mostrar_nome_falante"]),
        encoding="utf-8",
    )  # fmt: skip
    audio = audio_short.para_mixagem(ed, m["total"])
    for aviso in audio["avisos"]:
        print(f"   [AVISO] {aviso}")
    for k, fx in enumerate(audio["faixas"]):
        print(
            f"   musica: {fx['arquivo'].parent.name}/{fx['arquivo'].name}"
            + (f" (troca em {fx['inicio']:.1f}s)" if k else "")
        )
    if audio["efeitos"]:
        print(f"   efeitos sonoros: {len(audio['efeitos'])}")
    # censura no audio (desligada por padrao): "silencio" cala a palavra, "bip" poe um bip no lugar
    modo_audio = str(CFG.get("censura_audio", "nenhum")).lower()
    calar = trechos_para_calar(blocos) if modo_audio in ("silencio", "silêncio", "bip") else None
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
            None,
            m["total"],
            temp_saida,
            cod,
            ferr["fps"],
            legenda=arq_ass.name,
            calar=calar,
            bip=(modo_audio == "bip"),
            audio=audio,
        )
        return subprocess.run(cmd, cwd=str(pasta))

    try:
        r = rodar_ffmpeg(ferr["cod"])
        if r.returncode != 0 and ferr["cod"] == "nvenc":
            print("   [AVISO] a placa de video falhou nesse corte; tentando no processador...")
            r = rodar_ffmpeg("x264")
    finally:
        arq_ass.unlink(missing_ok=True)
    if r.returncode == 0 and temp_saida.exists():
        temp_saida.replace(destino)
        return True
    if temp_saida.exists():
        temp_saida.unlink()
    print("   [ERRO] esse corte falhou.")
    return False


def ler_so_este():
    """'--so N' na linha de comando: renderiza de novo apenas o Short N (usado pelo editor de legendas)."""
    if "--so" not in sys.argv:
        return None
    k = sys.argv.index("--so")
    numero = int(sys.argv[k + 1])
    del sys.argv[k : k + 2]
    return numero


def main():
    so_este = ler_so_este()
    proj = carregar_projeto(escolher_projeto())
    pasta, video, cortes = proj["pasta"], proj["video"], proj["cortes"]
    saida = pasta / "prontos"
    saida.mkdir(exist_ok=True)
    if not cortes:
        print("=" * 60)
        print(f" {MENSAGEM_ZERO}")
        print(" O Claude nao achou nenhum corte chamativo ou engracado o bastante (cortes: []).")
        print("=" * 60)
        return
    maximo = maximo_de_shorts(CFG)
    vale = escolhidos(cortes, maximo)
    ferr = preparar_ferramentas(proj)
    biblioteca.preparar_pastas()
    proj["plano_musicas"] = biblioteca.planejar_musicas(
        cortes, [clima_do(c) if isinstance(c, dict) else "" for c in cortes], pasta.name, CFG.get("musica")
    )

    print("=" * 60)
    print(f" Video:  {video.name}")
    print(f" Cortes: {len(cortes)}   Layout: {CFG['layout']}")
    if len(vale) < len(cortes):
        print(f" Maximo de Shorts: {maximo}. Ficam de fora os {len(cortes) - len(vale)} de nota mais baixa.")
    print(" Codificando na: " + ("PLACA DE VIDEO (NVENC)" if ferr["cod"] == "nvenc" else "PROCESSADOR (x264)"))
    if so_este:
        print(f" Renderizando de novo SO o Short {so_este}")
    print(f" Saida:  {saida}")
    print("=" * 60 + "\n")

    contagem = {"feitos": 0, "erros": 0}
    pulados = 0
    itens = []
    juntos = bool(CFG.get("shorts_preparar_enquanto_renderiza", True)) and not so_este
    anterior = None  # o render do Short anterior, rodando em segundo plano enquanto a legenda deste e preparada

    def esperar_anterior():
        """Espera o Short anterior ficar pronto (so um render por vez: o ffmpeg ja usa o PC quase todo)."""
        nonlocal anterior
        if anterior is not None:
            contagem["feitos" if anterior.result() else "erros"] += 1
            anterior = None

    with ThreadPoolExecutor(max_workers=1) as linha_do_render:
        for n, c in enumerate(cortes, 1):
            if n not in vale:
                print(
                    f"[{n}/{len(cortes)}] fora do maximo de Shorts (nota {c.get('nota', '-')}): {c.get('titulo', '')}"
                )
                continue
            try:
                m = medir_corte(c, n, ferr["dur_video"])
            except Exception:
                print(f"[{n}/{len(cortes)}] [ERRO] tempos invalidos: {c.get('inicio')} -> {c.get('fim')}")
                contagem["erros"] += 1
                continue
            if m["dur"] <= 0:  # (antes de entrar nos textos para postar: esse corte nao vira Short)
                print(f"[{n}/{len(cortes)}] [ERRO] tempos invalidos ({c['inicio']} -> {c['fim']})")
                contagem["erros"] += 1
                continue
            itens.append((n, m["nome"], c, m["total"]))
            destino = saida / m["nome"]
            if so_este and n != so_este:
                continue
            if destino.exists() and not so_este:
                print(f"[{n}/{len(cortes)}] ja existe, pulando: {m['nome']}")
                pulados += 1
                continue
            print(
                f"[{n}/{len(cortes)}] {tempo_txt(m['ini'])} -> {tempo_txt(m['fim'])} ({m['dur']:.0f}s + final)  "
                f"{m['titulo']}"
            )
            blocos, t_final = legendas_do_corte(proj, ferr, c, m)  # (o Short anterior segue renderizando)
            ed = edicao_do_corte(proj, c, m, refazer_sugestao=not so_este)
            esperar_anterior()
            if juntos:
                anterior = linha_do_render.submit(renderizar_corte, proj, ferr, c, m, blocos, t_final, destino, ed)
            else:
                contagem["feitos" if renderizar_corte(proj, ferr, c, m, blocos, t_final, destino, ed) else "erros"] += 1
        esperar_anterior()
    feitos, erros = contagem["feitos"], contagem["erros"]

    salvar_publicacao(pasta, saida, itens, proj["projeto"])

    print("\n" + "=" * 60)
    print(f" PRONTO! {feitos} criado(s), {pulados} ja existia(m), {erros} com erro.")
    print(f" Pasta: {saida}")
    print(" Textos pra postar: textos_para_postar.txt (ou botao 'Publicar' no Studio)")
    print("=" * 60)


if __name__ == "__main__":
    rodar(main)
