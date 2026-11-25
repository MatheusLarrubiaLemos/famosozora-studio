# Passo 5: gera o episodio editado (video longo) a partir do edicao.json (escrito pelo Claude).
#   episodio sem as partes que sairam (SEM gancho: comeca normal, com a intro) -> outro padrao no final
# Cada trecho que fica e recodificado com corte exato (quadro a quadro), com uma transicao curta (fade) em cada
# emenda, e o audio vira PCM; depois tudo e juntado sem recodificar (concat) e o audio vira AAC uma vez so.
# O outro (pasta outro\ da pasta de trabalho) entra no ultimo trecho com xfade + acrossfade, ja convertido para a
# resolucao, o FPS e o audio do episodio.
# Os trechos sao renderizados AO MESMO TEMPO (2 por padrao; "episodio_partes_simultaneas" no config.json;
# 1 = um de cada vez): cada um e independente, e um ffmpeg sozinho nao usa o PC inteiro.
# O video original so e LIDO.
#
# Uso: editar_episodio.py <pasta do projeto>                -> episodio completo
#      editar_episodio.py <pasta do projeto> --previa [seg]  -> so os primeiros ~10 min + estimativa
#      editar_episodio.py <pasta do projeto> --emenda N      -> 5 s antes + 5 s depois do corte N
import os
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from nucleo import comum
from nucleo.comum import carregar_config, gravar_json, nome_seguro, pausar_e_sair, rodar, tempo_txt
from nucleo.video import achar_programa, dimensoes_video, nvenc_funciona
from videos_longos import outro as outro_mod
from videos_longos import pausas
from videos_longos.pedido_edicao import (
    autoedit_ativo,
    capitulos_editados,
    carregar_palavras,
    fps_fracao,
    info_video,
    ler_edicao,
    metadados_capitulos,
    montar_plano,
    textos_episodio,
)

CFG = carregar_config()
FADE_AUDIO = 0.015  # fade em cada emenda (tira o estalo)
PEDACO_MAX_S = 300.0  # trechos longos viram pedacos de ate 5 min (para continuar de onde parou se o app fechar)
TAXA_AUDIO = 48000


# ================================================================== codificador
def args_video(cod: str) -> list:
    crf = int(CFG.get("episodio_crf", 20))
    if cod == "nvenc":
        return [
            "-c:v",
            "h264_nvenc",
            "-preset",
            "p5",
            "-tune",
            "hq",
            "-rc",
            "vbr",
            "-cq",
            str(crf + 1),
            "-b:v",
            "0",
            "-profile:v",
            "high",
        ]
    return [
        "-c:v",
        "libx264",
        "-preset",
        str(CFG.get("episodio_preset", "veryfast")),
        "-crf",
        str(crf),
        "-profile:v",
        "high",
    ]


def testar_nvenc(ffmpeg) -> bool:
    return nvenc_funciona(ffmpeg, CFG, args_video("nvenc"), "1920x1080")


# ================================================================== progresso
class Progresso:
    """Mostra quanto do episodio ja foi feito e quanto falta. Funciona com varios trechos rodando ao mesmo tempo:
    cada trecho avisa o seu andamento (parte(k)) e, quando termina, entra no 'feito' (terminou(k, segundos))."""

    def __init__(self, total: float, rotulo: str):
        self.total = max(0.001, total)
        self.feito = 0.0
        self.inicio = time.time()
        self.rotulo = rotulo
        self._ultimo = 0.0
        self._andamento = {}  # trecho -> segundos ja feitos dele (os que estao rodando agora)
        self._trava = threading.Lock()

    def mostrar(self, atual: float = 0.0, forcar=False):
        with self._trava:
            agora = time.time()
            if not forcar and agora - self._ultimo < 0.5:
                return
            self._ultimo = agora
            pronto = min(self.total, self.feito + atual + sum(self._andamento.values()))
            dec = agora - self.inicio
            vel = pronto / dec if dec > 0 else 0
            falta = (self.total - pronto) / vel if vel > 0 else 0
            print(
                f"\r {self.rotulo} {pronto / self.total * 100:5.1f}%  |  {tempo_txt(pronto)} de {tempo_txt(self.total)}"
                f"  |  {vel:4.1f}x  |  falta ~{tempo_txt(falta)}   ",
                end="",
                flush=True,
            )

    def parte(self, k: int):
        """O 'progresso' que o ffmpeg do trecho k usa (ele avisa quantos segundos do trecho ja fez)."""
        geral = self

        class _Trecho:
            def mostrar(self, atual: float = 0.0, forcar=False):
                with geral._trava:
                    geral._andamento[k] = atual
                geral.mostrar(forcar=forcar)

        return _Trecho()

    def terminou(self, k: int, segundos: float, rotulo: str | None = None):
        with self._trava:
            self._andamento.pop(k, None)
            self.feito += segundos
            if rotulo is not None:
                self.rotulo = rotulo
        self.mostrar(forcar=True)

    def velocidade(self) -> float:
        dec = time.time() - self.inicio
        return self.feito / dec if dec > 0 else 0


def partes_simultaneas() -> int:
    """Quantos trechos renderizar ao mesmo tempo ("episodio_partes_simultaneas" no config.json; padrao 2)."""
    try:
        return max(1, min(4, int(CFG.get("episodio_partes_simultaneas") or 2)))
    except (TypeError, ValueError):
        return 2


def rodar_ffmpeg(cmd, prog: Progresso | None):
    """Roda o ffmpeg lendo o -progress para mostrar o tempo que falta."""
    p = subprocess.Popen(
        cmd + ["-progress", "pipe:1", "-nostats"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    for linha in p.stdout:
        if prog and linha.startswith("out_time_us="):
            try:
                prog.mostrar(int(linha.split("=")[1]) / 1e6)
            except ValueError:
                pass
    err = p.stderr.read()
    p.wait()
    if p.returncode != 0:
        print("\n" + err[-1500:])
    return p.returncode


# ================================================================== partes
def render_parte(ffmpeg, video, q_ini, n_quadros, fps, base: Path, cod, prog=None, fade_in=0.0, fade_out=0.0,
                 vel=1.0, fade_audio=None, continua_ini=False, continua_fim=False):  # fmt: skip
    """Recodifica um trecho com corte exato: base.mp4 (video) + base.wav (audio PCM com a mesma duracao).
    vel > 1 = trecho acelerado (Auto-Edit): a imagem e o som ficam 'vel' vezes mais rapidos, a voz sem esquilo.
    continua_ini / continua_fim: o pedaco emenda no anterior / no proximo sem corte (trecho longo dividido em
    pedacos para dar para continuar de onde parou): ali o som nao ganha fade, para a emenda nao aparecer."""
    ini = float(q_ini / fps)
    vel = float(vel or 1.0)
    n_saida = max(1, int(round(n_quadros / vel))) if vel != 1.0 else n_quadros
    dur = float(n_saida / fps)
    amostras = int(round(n_saida / fps * TAXA_AUDIO))
    fade_a = FADE_AUDIO if fade_audio is None else max(0.005, float(fade_audio))
    vf = [f"setpts=PTS/{vel:.4f}"] if vel != 1.0 else []
    if fade_in > 0:
        vf.append(f"fade=t=in:st=0:d={fade_in:.3f}")
    if fade_out > 0:
        vf.append(f"fade=t=out:st={max(0.0, dur - fade_out):.4f}:d={fade_out:.3f}")
    fi = max(fade_a, fade_in)
    fo = max(fade_a, fade_out)
    af = (
        f"atempo={vel:.4f}," if vel != 1.0 else ""
    ) + f"aresample={TAXA_AUDIO},aformat=sample_fmts=s16:channel_layouts=stereo,apad,atrim=end_sample={amostras}"
    if not continua_ini:
        af += f",afade=t=in:st=0:d={fi:.3f}"
    if not continua_fim:
        af += f",afade=t=out:st={max(0.0, dur - fo):.4f}:d={fo:.3f}"
    escala = fps.numerator * (1000 if fps.denominator == 1 else 1)
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-nostdin",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        f"{ini:.6f}",
        "-t",
        f"{float(n_quadros / fps) + 1:.3f}",
        "-i",
        str(video),
        "-map",
        "0:v:0",
        "-frames:v",
        str(n_saida),
    ]
    if vf:
        cmd += ["-vf", ",".join(vf)]
    cmd += [
        *args_video(cod),
        "-pix_fmt",
        "yuv420p",
        "-fps_mode",
        "cfr",
        "-r",
        str(fps),
        "-video_track_timescale",
        str(escala),
        "-an",
        str(base.with_suffix(".mp4")),
        "-map",
        "0:a:0",
        "-vn",
        "-af",
        af,
        "-c:a",
        "pcm_s16le",
        str(base.with_suffix(".wav")),
    ]
    return rodar_ffmpeg(cmd, prog)


def render_ultima_com_outro(ffmpeg, video, q_ini, n_quadros, fps, base: Path, cod, outro, prog=None, fade_in=0.0,
                            continua=False):  # fmt: skip
    """O ultimo trecho do episodio ja com o outro no fim (xfade + acrossfade)."""
    arq, info = outro
    largura, altura = dimensoes_video(video)
    cmd, _, _ = outro_mod.comando_com_outro(ffmpeg, video, float(q_ini / fps), n_quadros, fps, arq, info, largura,
                                            altura, args_video(cod), base, TAXA_AUDIO, fade_in,
                                            float(CFG.get("outro_transicao", outro_mod.TRANSICAO)),
                                            continua)  # fmt: skip
    return rodar_ffmpeg(cmd, prog)


def _parte(p) -> tuple:
    """(q, n, fade_in, fade_out, velocidade, continua_ini, continua_fim): as partes antigas tinham menos campos
    (sem velocidade = 1.0; sem os 'continua' = False, ou seja, cada parte e um trecho inteiro)."""
    p = tuple(p)
    if len(p) == 4:
        p += (1.0,)
    if len(p) == 5:
        p += (False, False)
    return p


def render_lista(ffmpeg, video, partes, fps, temp: Path, cod, prog: Progresso, outro=None, fade_audio=None,
                 retomar=False):  # fmt: skip
    """partes = [(q_ini, n_quadros, fade_in, fade_out[, velocidade])]. outro = (arquivo, info) ou None: entra no
    ultimo trecho. Renderiza ate partes_simultaneas() trechos ao mesmo tempo. retomar=True: os trechos ja prontos
    de uma vez anterior (o app fechou no meio) nao sao refeitos. Retorna a lista de bases (na ordem) ou None."""
    total = len(partes)
    bases = [temp / f"parte_{k:04d}" for k in range(1, total + 1)]
    arq_feitas = temp / "feitas.json"
    prontas = set(comum.ler_json(arq_feitas, []) or []) if retomar else set()
    prontas = {
        k for k in prontas if bases[k - 1].with_suffix(".mp4").exists() and bases[k - 1].with_suffix(".wav").exists()
    }
    if prontas:
        print(f"Continuando de onde parou: {len(prontas)} de {total} trecho(s) já estavam prontos.")
    feitas = [len(prontas)]
    trava = threading.Lock()
    prog.rotulo = f"[{feitas[0]}/{total}]"
    for k in prontas:
        q, n, _, _, vel, _, _ = _parte(partes[k - 1])
        prog.feito += float(n / fps) / vel

    def render_um(k: int) -> int:
        q, n, fin, fout, vel, cont_ini, cont_fim = _parte(partes[k - 1])
        base, andamento = bases[k - 1], prog.parte(k)

        def render(codificador):
            if outro and k == total:
                return render_ultima_com_outro(ffmpeg, video, q, n, fps, base, codificador, outro, andamento, fin,
                                               cont_ini)  # fmt: skip
            if vel == 1.0 and fade_audio is None and not cont_ini and not cont_fim:  # trecho inteiro e simples
                return render_parte(ffmpeg, video, q, n, fps, base, codificador, andamento, fin, fout)
            return render_parte(ffmpeg, video, q, n, fps, base, codificador, andamento, fin, fout, vel, fade_audio,
                                cont_ini, cont_fim)  # fmt: skip

        r = render(cod)
        if r != 0 and cod == "nvenc":
            print(f"\n   [AVISO] a placa de vídeo falhou no trecho {k}; tentando no processador...")
            r = render("x264")
        if r == 0:
            with trava:
                feitas[0] += 1
                rotulo = f"[{feitas[0]}/{total}]" + (" + outro" if outro else "")
                if retomar:
                    prontas.add(k)
                    comum.gravar_json(arq_feitas, sorted(prontas))
            prog.terminou(k, float(n / fps) / vel, rotulo)
        return r

    juntas = min(partes_simultaneas(), max(1, total))
    falhou = None
    with ThreadPoolExecutor(max_workers=juntas) as linhas:
        futuros = {linhas.submit(render_um, k): k for k in range(1, total + 1) if k not in prontas}
        for futuro in as_completed(futuros):
            k = futuros[futuro]
            try:
                r = futuro.result()
            except Exception as e:  # erro inesperado num trecho: conta como falha
                print(f"\n[ERRO] o trecho {k} deu erro: {e}")
                r = 1
            if r != 0 and falhou is None:
                falhou = k
                for outro_futuro in futuros:  # os que ainda nao comecaram nem comecam
                    outro_futuro.cancel()
    if falhou is not None:
        print(f"\n[ERRO] o trecho {falhou} falhou.")
        return None
    print()
    return bases


def juntar(ffmpeg, bases, temp: Path, saida: Path, capitulos_txt: str | None = None):
    """Junta as partes sem recodificar o video; o audio PCM vira AAC uma vez so."""

    def linha(arq: Path) -> str:
        return "file '" + arq.as_posix().replace("'", "'\\''") + "'\n"  # aspas no nome da pasta

    lv, la = temp / "lista_video.txt", temp / "lista_audio.txt"
    lv.write_text("".join(linha(b.with_suffix(".mp4")) for b in bases), encoding="utf-8")
    la.write_text("".join(linha(b.with_suffix(".wav")) for b in bases), encoding="utf-8")
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-nostdin",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(lv),
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(la),
    ]
    if capitulos_txt:
        meta = temp / "capitulos.txt"
        meta.write_text(capitulos_txt, encoding="utf-8")
        cmd += ["-i", str(meta), "-map_metadata", "2", "-map_chapters", "2"]
    cmd += [
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        str(saida),
    ]
    print("Juntando as partes (sem recodificar o vídeo)...")
    return subprocess.run(cmd).returncode


def abrir_player(arq: Path):
    if hasattr(os, "startfile"):
        try:
            os.startfile(str(arq))
        except OSError:
            pass


# ================================================================== modos
def partes_do_plano(plano, limite: float | None = None):
    """Lista de partes (q_ini, n, fade_in, fade_out) do episodio; com limite, corta nos primeiros 'limite' s.
    Cada emenda (onde saiu um trecho) ganha uma transicao curta: o trecho de antes some e o de depois aparece
    ("episodio_fade_emenda" no config.json, em segundos; 0 desliga). Sem gancho: comeca do comeco."""
    fps = plano["fps"]
    fade = max(0.0, float(CFG.get("episodio_fade_emenda", 0.2) or 0))
    partes = []
    trechos = plano["trechos"]
    secas = plano.get("secas") or set()  # emendas de pausa cortada: corte seco (fade so no audio, bem curto)
    velocidades = plano.get("velocidades") or {}
    for k, (q, n) in enumerate(trechos):
        curto = n / fps < fade * 4  # trecho muito curto: sem fade, para nao piscar
        fin = fade if k > 0 and not curto and k not in secas else 0.0
        fout = fade if k < len(trechos) - 1 and not curto and (k + 1) not in secas else 0.0
        partes.append([q, n, fin, fout, float(velocidades.get(k, 1.0))])
    if limite:
        resta = int(limite * fps)
        cortadas = []
        for p in partes:
            if resta <= 0:
                break
            usa = int(p[1] / p[4])  # quadros do episodio que este trecho ocupa
            if usa > resta:
                p = [p[0], int(resta * p[4]), p[2], 0.0, p[4]]
                usa = resta
            cortadas.append(p)
            resta -= usa
        partes = cortadas
    return dividir_em_pedacos([tuple(p) for p in partes], fps, pedaco_maximo())


def pedaco_maximo() -> float:
    """Tamanho maximo de cada pedaco renderizado, em segundos ("episodio_pedaco_max_s" no config.json; 0 desliga)."""
    try:
        return max(0.0, float(CFG.get("episodio_pedaco_max_s", PEDACO_MAX_S)))
    except (TypeError, ValueError):
        return PEDACO_MAX_S


def dividir_em_pedacos(partes, fps, maximo: float) -> list:
    """Divide os trechos longos em pedacos de no maximo 'maximo' segundos. Cada pedaco pronto fica guardado no
    _temp: se o app fechar no meio, o episodio continua do ultimo pedaco pronto (antes, uma live sem cortes era um
    trecho so de horas e voltava do zero). Os pedacos de um mesmo trecho emendam sem fade (nem na imagem nem no
    som), entao nao da para ver a divisao. Trechos acelerados nao sao divididos (o atempo mudaria nas emendas)."""
    if not maximo:
        return list(partes)
    limite = max(1, int(maximo * fps))
    saida = []
    for p in partes:
        q, n, fin, fout, vel, cont_ini, cont_fim = _parte(p)
        if vel != 1.0 or n <= limite * 1.5:  # trecho curto (ou ate 1,5x o pedaco): fica inteiro
            saida.append((q, n, fin, fout, vel, cont_ini, cont_fim))
            continue
        k = -(-n // limite)  # quantos pedacos (arredonda para cima) e todos do mesmo tamanho
        tamanho = -(-n // k)
        inicio = 0
        while inicio < n:
            m = min(tamanho, n - inicio)
            primeiro, ultimo = inicio == 0, inicio + m >= n
            saida.append((q + inicio, m, fin if primeiro else 0.0, fout if ultimo else 0.0, vel,
                          cont_ini if primeiro else True, cont_fim if ultimo else True))  # fmt: skip
            inicio += m
    return saida


def limpar_temp(temp: Path):
    """Apaga uma subpasta de episodio\\_temp (cada modo tem a sua, pra um nao apagar o outro)."""
    if temp.exists() and temp.parent.name == "_temp":
        shutil.rmtree(temp, ignore_errors=True)


def limpar_tudo(temp_raiz: Path):
    """Fim do episodio: apaga o _temp inteiro (o que estiver aberto no player fica)."""
    if temp_raiz.exists() and temp_raiz.name == "_temp":
        shutil.rmtree(temp_raiz, ignore_errors=True)


def ler_argumentos(args):
    """Devolve (pasta, modo, valor). modo = 'episodio', 'previa' (valor = segundos) ou 'emenda' (valor = corte)."""
    if not args:
        print("Uso: editar_episodio <pasta do projeto> [--previa] [--emenda N]")
        pausar_e_sair(1)
    pasta = Path(args[0])
    if "--previa" in args:
        i = args.index("--previa")
        tem_valor = i + 1 < len(args) and args[i + 1].replace(".", "").isdigit()
        return pasta, "previa", float(args[i + 1]) if tem_valor else 600.0
    if "--emenda" in args:
        return pasta, "emenda", int(args[args.index("--emenda") + 1])
    return pasta, "episodio", None


def conferir_se_cortou(plano: dict, dur: float):
    """Se quase nada sai (menos de 1% da live), avisa e pergunta antes de gastar horas renderizando a live inteira."""
    if dur <= 0 or plano["dur_final"] < dur * 0.99:
        return
    print("\n[AVISO] Quase nada vai ser cortado: o episódio vai sair praticamente do tamanho da live "
          f"({tempo_txt(plano['dur_final'])} de {tempo_txt(dur)}).")  # fmt: skip
    print("        Para o Studio sugerir os cortes: abra o editor e clique em \"✨ Analisar a live\" (ou use a "
          "\"Edição do Claude\"). Depois gere de novo.")  # fmt: skip
    try:
        resposta = input("Gerar assim mesmo? (s/N): ")
    except EOFError:  # sem ninguem para responder (rodando sozinho): segue como antes
        return
    if resposta.strip().lower() not in ("s", "sim", "y"):
        print("Cancelado: nada foi gerado.")
        comum.PAUSAR = False
        pausar_e_sair(0)


def preparar(pasta: Path, modo: str) -> dict:
    """Le o projeto e o edicao.json, monta o plano do episodio e escolhe o codificador."""
    video, dur = info_video(pasta)
    if not video.exists():
        print(f"\n[ERRO] Não achei o vídeo original: {video}\nEle foi movido ou renomeado?")
        pausar_e_sair(1)
    dados, erros, avisos = ler_edicao(pasta, dur)
    if erros:
        print("\n[ERRO] O edicao.json tem problemas:\n- " + "\n- ".join(erros))
        pausar_e_sair(1)
    for a in avisos:
        print(f"[AVISO] {a}")

    ffmpeg = achar_programa("ffmpeg")
    fps = fps_fracao(video)
    acao = None
    if pausas.ligado(CFG, dados) and not autoedit_ativo(dados):  # os momentos de acao nunca saem nas pausas
        try:
            atividade = pausas.medir_atividade(ffmpeg, video, pasta)
            acao = pausas.momentos_de_acao(atividade, pausas.ajuste(CFG, "episodio_acao_sensibilidade"))
        except Exception as e:
            print(f"[AVISO] Não consegui medir o som do jogo ({e}); as pausas são cortadas só pela fala.")
    plano = montar_plano(dados, dur, fps, carregar_palavras(pasta), CFG, acao=acao)
    if plano["pausas"]["n"]:
        print(f"Pausas sem fala cortadas: {plano['pausas']['n']} ({tempo_txt(plano['pausas']['segundos'])} a menos)")
    if modo == "episodio":
        conferir_se_cortou(plano, dur)
    pasta_ep = pasta / "episodio"
    temp_raiz = pasta_ep / "_temp"
    cod = "nvenc" if testar_nvenc(ffmpeg) else "x264"
    outro, dur_outro = None, 0.0
    if modo == "episodio":
        arq, info, texto, _ = outro_mod.situacao(dados.get("incluir_outro", True) is not False)
        if arq and info:
            outro = (arq, info)
            d = min(float(CFG.get("outro_transicao", outro_mod.TRANSICAO)), plano["dur_final"] / 2, info["duracao"] / 2)
            dur_outro = info["duracao"] - d
        print(("[AVISO] " if not outro and dados.get("incluir_outro", True) is not False else "") + texto)
    nome_cod = (
        "PLACA DE VIDEO (NVENC)" if cod == "nvenc" else f"PROCESSADOR (x264 {CFG.get('episodio_preset', 'veryfast')})"
    )
    return {
        "pasta": pasta,
        "video": video,
        "dur": dur,
        "dados": dados,
        "ffmpeg": ffmpeg,
        "fps": fps,
        "plano": plano,
        "pasta_ep": pasta_ep,
        "temp_raiz": temp_raiz,
        "temp": temp_raiz / modo,
        "cod": cod,
        "nome_cod": nome_cod,
        "outro": outro,
        "dur_outro": dur_outro,
    }


def modo_emenda(ctx: dict, numero: int):
    """Clipe de ~10 s: 5 s antes do corte + 5 s depois, ja emendados. Abre no player."""
    video, dur, fps, temp = ctx["video"], ctx["dur"], ctx["fps"], ctx["temp"]
    cortes = ctx["plano"]["cortes"]
    if not 1 <= numero <= len(cortes):
        print(f"[ERRO] Corte {numero} não existe.")
        pausar_e_sair(1)
    c = cortes[numero - 1]
    q_a = int(round(c["ini_aj"] * fps)) if c["ini_aj"] > 0.05 else 0
    q_b = int(round(c["fim_aj"] * fps))
    n5 = int(5 * fps)
    total_q = int(round(dur * fps))
    partes = []
    if q_a > 0:
        partes.append((max(0, q_a - n5), q_a - max(0, q_a - n5), 0.0, 0.0))
    if q_b < total_q:
        partes.append((q_b, min(n5, total_q - q_b), 0.0, 0.0))
    print(
        f"Emenda do corte {numero}: sai {tempo_txt(c['ini_aj'], ms=True)} → {tempo_txt(c['fim_aj'], ms=True)}"
        f" ({c['dur']:.1f} s)  {c['motivo']}"
    )
    limpar_temp(temp)
    temp.mkdir(parents=True, exist_ok=True)
    prog = Progresso(sum(p[1] for p in partes) / float(fps), "")
    bases = render_lista(ctx["ffmpeg"], video, partes, fps, temp, ctx["cod"], prog)
    saida = temp / f"emenda_{numero:02d}_{datetime.now():%H%M%S}.mp4"
    if bases is None or juntar(ctx["ffmpeg"], bases, temp, saida) != 0:
        print("[ERRO] não consegui gerar a emenda.")
        pausar_e_sair(1)
    print(f"Pronto: {saida}")
    abrir_player(saida)
    comum.PAUSAR = False  # deu certo: fecha a janela sozinha


def renderizar_partes(ctx: dict, limite: float | None):
    """Mostra o resumo e renderiza os trechos do episodio (ou so os primeiros 'limite' segundos).
    Retorna (bases, progresso)."""
    video, dur, fps, plano, temp = ctx["video"], ctx["dur"], ctx["fps"], ctx["plano"], ctx["temp"]
    partes = partes_do_plano(plano, limite)
    outro = None if limite else ctx.get("outro")
    if outro and partes:  # o ultimo trecho termina no outro (com a transicao), sem fade para preto
        q, n, fin, _, _, cont_ini, _ = _parte(partes[-1])
        partes[-1] = (q, n, fin, 0.0, 1.0, cont_ini, False)  # com o outro: velocidade normal
    total = sum(_parte(p)[1] / _parte(p)[4] for p in partes) / float(fps) + (ctx["dur_outro"] if outro else 0)
    print("=" * 64)
    print(f" Vídeo:      {video.name}  ({fps} fps)")
    print(f" Original:   {tempo_txt(dur)}  →  episódio: {tempo_txt(plano['dur_final'])}")
    ativos = sum(1 for c in plano["cortes"] if c["ativo"])
    print(f" Cortes:     {ativos} de {len(plano['cortes'])} marcados (sem gancho: começa do começo)")
    if plano.get("autoedit", {}).get("n"):
        print(f" Auto-Edit:  {plano['autoedit']['n']} corte(s), {tempo_txt(plano['autoedit']['segundos'])} a menos")
    print(" Outro:      " + (f"{ctx['outro'][0].name} ({ctx['dur_outro']:.1f} s)" if outro else "não"))
    print(f" Codificando no: {ctx['nome_cod']}")
    if limite:
        print(f" PRÉVIA: só os primeiros {tempo_txt(total)} do episódio")
    print(f" Saída:      {ctx['pasta_ep']}")
    print("=" * 64 + "\n")

    # episodio inteiro: se o app fechou no meio com ESTE mesmo plano, continua de onde parou
    retomar = limite is None and _mesmo_plano(temp, partes, ctx)
    if not retomar:
        limpar_temp(temp)
    temp.mkdir(parents=True, exist_ok=True)
    if limite is None:
        gravar_json(temp / "plano.json", _assinatura_plano(partes, ctx))
    prog = Progresso(total, "")
    bases = render_lista(ctx["ffmpeg"], video, partes, fps, temp, ctx["cod"], prog, outro,
                         plano.get("fade_audio"), retomar=limite is None)  # fmt: skip
    if bases is None:
        print("[ERRO] a renderização falhou. Os temporários ficaram em", temp)
        pausar_e_sair(1)
    return bases, prog


def _assinatura_plano(partes, ctx: dict) -> dict:
    """O que define o resultado de cada trecho: se nada mudou, os trechos prontos servem."""
    from autoedit.base import assinatura

    return {"partes": [[int(p[0]), int(p[1]), round(p[2], 3), round(p[3], 3), round(p[4], 3), bool(p[5]), bool(p[6])]
                       for p in map(_parte, partes)],
            "video": assinatura(ctx["video"]), "codificador": ctx["cod"], "fade_audio": ctx["plano"].get("fade_audio"),
            "outro": str(ctx["outro"][0]) if ctx.get("outro") else ""}  # fmt: skip


def _mesmo_plano(temp: Path, partes, ctx: dict) -> bool:
    return (temp / "plano.json").exists() and comum.ler_json(temp / "plano.json") == _assinatura_plano(partes, ctx)


def modo_previa(ctx: dict, limite: float):
    """Renderiza so o comeco do episodio e estima o tempo do episodio inteiro."""
    bases, prog = renderizar_partes(ctx, limite)
    vel = prog.velocidade()
    plano, temp = ctx["plano"], ctx["temp"]
    saida = temp / "previa_10min.mp4"
    if juntar(ctx["ffmpeg"], bases, temp, saida) != 0:
        print("[ERRO] não consegui juntar a prévia.")
        pausar_e_sair(1)
    decorrido = time.time() - prog.inicio
    estimativa = plano["dur_final"] / vel if vel > 0 else 0
    print("\n" + "=" * 64)
    print(f" PRÉVIA PRONTA em {tempo_txt(decorrido)}  ({vel:.1f}x o tempo real)")
    print(f" Estimativa do episódio inteiro ({tempo_txt(plano['dur_final'])}): ~{tempo_txt(estimativa * 1.03)}")
    print(f" Arquivo: {saida}")
    print("=" * 64)
    abrir_player(saida)


def modo_episodio(ctx: dict):
    """Renderiza o episodio inteiro, grava os capitulos no .mp4 e escreve o textos_episodio.txt."""
    bases, prog = renderizar_partes(ctx, None)
    vel = prog.velocidade()
    pasta, dados, plano, pasta_ep, dur = ctx["pasta"], ctx["dados"], ctx["plano"], ctx["pasta_ep"], ctx["dur"]

    dur_total = plano["dur_final"] + (ctx["dur_outro"] if ctx.get("outro") else 0.0)
    caps, avisos_caps = capitulos_editados(dados, plano, dur_total)
    titulo = str(dados.get("titulo") or "").strip()
    nome = (nome_seguro(titulo, 90) if titulo else f"{pasta.name} - episodio") + ".mp4"
    meta = metadados_capitulos(caps, dur_total, titulo) if caps else None
    temp_saida = pasta_ep / "_gerando_episodio.mp4"
    if juntar(ctx["ffmpeg"], bases, ctx["temp"], temp_saida, meta) != 0 or not temp_saida.exists():
        print("[ERRO] não consegui juntar o episódio. Os temporários ficaram em", ctx["temp"])
        pausar_e_sair(1)
    destino = pasta_ep / nome
    temp_saida.replace(destino)
    (pasta_ep / "textos_episodio.txt").write_text(
        textos_episodio(dados, caps, avisos_caps, nome, dur_total, pasta.name), encoding="utf-8"
    )
    gravar_json(
        pasta_ep / "episodio.json",
        {
            "arquivo": nome,
            "gerado_em": datetime.now().isoformat(timespec="seconds"),
            "duracao": round(dur_total, 3),
            "outro": ctx["outro"][0].name if ctx.get("outro") else "",
            "duracao_original": round(dur, 3),
            "capitulos": [{"inicio": round(t, 3), "titulo": a, "titulo_en": b} for t, a, b in caps],
        },
    )
    limpar_tudo(ctx["temp_raiz"])
    decorrido = time.time() - prog.inicio
    print("\n" + "=" * 64)
    print(f" PRONTO em {tempo_txt(decorrido)}!  ({vel:.1f}x o tempo real)")
    print(f" Episódio:  {destino}")
    print(
        f" Duração:   {tempo_txt(dur_total)} (o original tinha {tempo_txt(dur)})"
        + (f", com o outro {ctx['outro'][0].name}" if ctx.get("outro") else "")
    )
    print(" Textos:    textos_episodio.txt (título, descrição, capítulos, inglês, miniatura)")
    for a in avisos_caps:
        print(f" [AVISO] {a}")
    print("=" * 64)


def main():
    pasta, modo, valor = ler_argumentos(sys.argv[1:])
    ctx = preparar(pasta, modo)
    if modo == "emenda":
        modo_emenda(ctx, valor)
    elif modo == "previa":
        modo_previa(ctx, valor)
    else:
        modo_episodio(ctx)


if __name__ == "__main__":
    rodar(main)
