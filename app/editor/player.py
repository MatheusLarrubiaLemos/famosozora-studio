# Player de video do editor, DENTRO da janela do Studio:
#   - PlayerMpv: o mpv (libmpv-2.dll em bin\, pela biblioteca python-mpv) desenha dentro de um quadro do Tkinter.
#     Toca de 0,5x a 4x com a voz normal (o filtro scaletempo2 do mpv corrige o tom sozinho) e pula rapido.
#   - PlayerMiniaturas: sem o mpv (download falhou, PC sem a DLL...). Mostra a miniatura do ponto atual e anda o
#     relogio sozinho, sem som. Da para cortar, mas nao para ouvir; a tela avisa.
# Os dois tem os mesmos comandos: carregar, tocar, pausar, ir, tempo, velocidade, filtro (previa vertical) e fechar.
import os
import time
import tkinter as tk

from nucleo.comum import PASTA_BIN
from nucleo.registro import registrar


def mpv_disponivel() -> bool:
    return _carregar_mpv() is not None


def _carregar_mpv():
    """O modulo mpv (python-mpv) com a DLL achada, ou None."""
    if os.name == "nt" and PASTA_BIN.exists():
        try:
            os.add_dll_directory(str(PASTA_BIN))
        except (OSError, AttributeError):
            pass
        os.environ["PATH"] = str(PASTA_BIN) + os.pathsep + os.environ.get("PATH", "")
    try:
        import mpv  # noqa: F401

        return mpv
    except Exception:
        return None


def saida_de_video() -> str:
    """Saida de video do mpv. Windows: a padrao (gpu/d3d11). Linux: x11 (a padrao, com EGL, as vezes abre uma
    janela solta em vez de ficar dentro do editor). Da para trocar com "editor_mpv_vo" no config.json."""
    from nucleo.comum import carregar_config

    escolhida = str(carregar_config().get("editor_mpv_vo") or "").strip()
    if escolhida:
        return escolhida
    return "" if os.name == "nt" else "x11"


def _log_do_mpv(nivel, parte, texto):
    registrar(f"mpv [{nivel}] {parte}: {str(texto).strip()}")


class PlayerBase:
    tem_som = False

    def __init__(self, quadro: tk.Widget):
        self.quadro = quadro
        self._vel = 1.0

    def velocidade(self, v: float | None = None) -> float:
        if v is not None:
            self._vel = float(v)
        return self._vel


class PlayerMpv(PlayerBase):
    tem_som = True

    def __init__(self, quadro: tk.Widget):
        super().__init__(quadro)
        mpv = _carregar_mpv()
        quadro.update_idletasks()
        opcoes = dict(wid=str(quadro.winfo_id()), keep_open="yes", hr_seek="yes", osc="no", input_default_bindings="no",
                      input_vo_keyboard="no", audio_pitch_correction="yes", idle="yes", pause="yes")  # fmt: skip
        vo = saida_de_video()
        if vo:
            opcoes["vo"] = vo
        # erros do proprio mpv (arquivo que nao abre, filtro errado...) vao para o studio.log
        self.mpv = mpv.MPV(log_handler=_log_do_mpv, loglevel="error", **opcoes)
        self._duracao = 0.0
        self._legenda_ligada = False  # ja pus a legenda da previa neste arquivo (sub-add)?

    def carregar(self, arquivo, inicio: float = 0.0):
        self._legenda_ligada = False  # arquivo novo: a legenda entra junto pelo "sub-files"
        # O ponto de partida vai pela opcao "start" e NAO dentro do loadfile: no mpv 0.38+ o 3o valor do loadfile
        # virou a posicao na lista, e o "start=..." ali fazia o video nunca abrir (tela preta, relogio parado).
        # Assim funciona em qualquer versao do mpv.
        try:
            self.mpv.start = f"{max(0.0, inicio):.3f}"
            self.mpv.command("loadfile", str(arquivo), "replace")
        except Exception as e:
            registrar(f"editor: o mpv não abriu o vídeo {arquivo}", e)

    def tocar(self):
        self.mpv.pause = False

    def pausar(self):
        self.mpv.pause = True

    def tocando(self) -> bool:
        try:
            return not self.mpv.pause
        except Exception:
            return False

    def ir(self, t: float, exato: bool = True):
        try:
            self.mpv.command("seek", f"{max(0.0, t):.3f}", "absolute+exact" if exato else "absolute+keyframes")
        except Exception:
            pass  # arquivo ainda abrindo: o proximo pulo vale

    def tempo(self) -> float:
        try:
            return float(self.mpv.time_pos or 0.0)
        except Exception:
            return 0.0

    def velocidade(self, v: float | None = None) -> float:
        if v is not None:
            self._vel = float(v)
            try:
                self.mpv.speed = self._vel
            except Exception:
                pass
        return self._vel

    def quadro_a_quadro(self, para_frente: bool = True):
        try:
            self.mpv.command("frame-step" if para_frente else "frame-back-step")
        except Exception:
            pass

    def filtro(self, grafo: str | None):
        """Filtro de imagem do ffmpeg (previa vertical do Short); None tira."""
        try:
            self.mpv.vf = f"lavfi=[{grafo}]" if grafo else ""
        except Exception as e:
            registrar("editor: filtro da prévia vertical", e)

    def legenda(self, arquivo):
        """Legenda da previa (1.11.4): o .ass do Short (mesmo estilo do render, com os tempos do video original)
        desenhada pelo mpv em cima do video. None esconde. Editou a legenda? Chame de novo com o mesmo arquivo."""
        try:
            self.mpv["sub-files"] = [str(arquivo)] if arquivo else []  # vale para o proximo arquivo aberto
            self.mpv.sub_visibility = bool(arquivo)
            if not arquivo:
                return
            if self._legenda_ligada:
                self.mpv.command("sub-reload")
            else:
                self.mpv.command("sub-add", str(arquivo), "select")
                self._legenda_ligada = True
        except Exception:
            pass  # o video ainda esta abrindo: o "sub-files" poe a legenda quando ele abrir

    def fechar(self):
        try:
            self.mpv.terminate()
        except Exception:
            pass


class PlayerMiniaturas(PlayerBase):
    """Sem mpv: um relogio que anda na velocidade escolhida e a miniatura do ponto atual num Canvas."""

    def __init__(self, quadro: tk.Widget, mostrar_miniatura=None):
        super().__init__(quadro)
        self._t = 0.0
        self._tocando = False
        self._desde = 0.0
        self.mostrar_miniatura = mostrar_miniatura  # funcao (t) que desenha a miniatura

    def carregar(self, arquivo, inicio: float = 0.0):
        self._t = inicio

    def tocar(self):
        if not self._tocando:
            self._desde = time.monotonic()
            self._tocando = True

    def pausar(self):
        self._t = self.tempo()
        self._tocando = False

    def tocando(self) -> bool:
        return self._tocando

    def ir(self, t: float, exato: bool = True):
        self._t = max(0.0, t)
        self._desde = time.monotonic()

    def tempo(self) -> float:
        if self._tocando:
            agora = time.monotonic()
            self._t += (agora - self._desde) * self._vel
            self._desde = agora
        return self._t

    def velocidade(self, v: float | None = None) -> float:
        if v is not None:
            self.tempo()
            self._vel = float(v)
        return self._vel

    def quadro_a_quadro(self, para_frente: bool = True):
        self.pausar()
        self.ir(self._t + (1 / 30 if para_frente else -1 / 30))

    def legenda(self, arquivo):
        pass

    def filtro(self, grafo):
        pass

    def fechar(self):
        self._tocando = False


def criar(quadro: tk.Widget, mostrar_miniatura=None):
    """O melhor player que der: mpv; sem ele, as miniaturas. Devolve (player, aviso ou "")."""
    if _carregar_mpv() is not None and os.environ.get("FAMOSOZORA_SEM_MPV") != "1":
        try:
            return PlayerMpv(quadro), ""
        except Exception as e:
            registrar("editor: não consegui abrir o mpv", e)
    aviso = ("Player de vídeo indisponível (falta o libmpv-2.dll em bin\\): mostrando só as miniaturas, sem som. "
             "Dá para cortar normalmente.")  # fmt: skip
    return PlayerMiniaturas(quadro, mostrar_miniatura), aviso
