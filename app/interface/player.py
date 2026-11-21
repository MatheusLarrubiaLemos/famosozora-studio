# Player de video embutido nas telas (revisao do video longo e editor de legendas dos Shorts).
# Usa o mpv (o arquivo libmpv-2.dll fica na pasta bin\, junto com o ffmpeg): o video e desenhado dentro de um
# quadro da propria janela, abre na hora (sem recortar nem recodificar nada) e pula para qualquer ponto exato.
# Sem o mpv (DLL faltando, PC sem suporte), o quadro mostra um aviso e as telas voltam ao jeito antigo
# (cortar o trecho com o ffmpeg e abrir no player do Windows): nada deixa de funcionar.
#
# Quem usa: Player(pai, ao_tempo=funcao) e depois abrir(video), ir(segundos), tocar(de, ate), pausar()...
#   - ao_tempo(t) e chamado varias vezes por segundo com o tempo atual (sempre na linha da tela);
#   - pular = funcao t -> tempo para onde pular (ou None): usado para "ver como fica" sem o que sai;
#   - janela = (inicio, fim): a barra mostra so esse pedaco e o video para no fim (trecho de um Short);
#   - faixas = [(inicio, fim, cor)]: pedacos pintados na barra (o que sai, por exemplo);
#   - self.extras: quadro a direita dos controles, onde cada tela poe os botoes dela.
# Atalhos (ligar_atalhos): K ou Ctrl+Espaco = tocar/pausar, J/L = 5 s para tras/frente,
# virgula/ponto = quadro anterior/seguinte. Nao valem enquanto voce digita numa caixa de texto.
import os
import time
import tkinter as tk
from tkinter import ttk

from interface import tema
from nucleo import reproducao
from nucleo.comum import PASTA_BIN  # noqa: F401  (importar o comum poe a pasta bin\, com a libmpv-2.dll, no PATH)
from nucleo.registro import registrar

VELOCIDADES = ("0.5x", "1x", "1.5x", "2x")
INTERVALO_MS = 50  # de quanto em quanto tempo o player confere onde o video esta (pular e acompanhar a lista)
# jeitos de desenhar o video que sabem ficar DENTRO de um quadro da janela (o primeiro que funcionar vale)
SAIDA_DE_VIDEO = os.environ.get("FAMOSOZORA_PLAYER_VO") or ("gpu-next,gpu,direct3d" if os.name == "nt" else "gpu,x11")
_mpv = {"modulo": None, "erro": ""}


def carregar_mpv():
    """O modulo mpv pronto para usar, ou None (o motivo fica em motivo_indisponivel())."""
    if _mpv["modulo"] is None:
        if os.environ.get("FAMOSOZORA_SEM_PLAYER") == "1":  # os testes de tela usam o jeito antigo
            _mpv["modulo"], _mpv["erro"] = False, "desligado (FAMOSOZORA_SEM_PLAYER)"
        else:
            try:
                import mpv  # a pasta bin\ (onde fica a libmpv-2.dll) ja entrou no PATH pelo nucleo.comum

                _mpv["modulo"] = mpv
            except Exception as e:  # OSError: a DLL nao foi achada; ImportError: falta o python-mpv
                _mpv["modulo"], _mpv["erro"] = False, str(e)
                registrar(f"player: mpv indisponivel ({e})")
    return _mpv["modulo"] or None


def disponivel() -> bool:
    """O player embutido funciona neste PC?"""
    return carregar_mpv() is not None


def motivo_indisponivel() -> str:
    return _mpv["erro"]


def _estilos():
    estilo = ttk.Style()
    estilo.configure("Player.TButton", font=tema.F_TEXTO, padding=(7, 2), background=tema.BOTAO, foreground=tema.TEXTO)
    estilo.map("Player.TButton", background=[("active", tema.BOTAO_HOVER), ("disabled", tema.PAINEL)])


class Player(tk.Frame):
    """Video + barra de tempo + controles. Veja o comeco do arquivo."""

    def __init__(
        self, pai, altura: int = 220, ao_tempo=None, texto_vazio: str = "Nenhum vídeo aberto", compacto: bool = False
    ):
        """compacto=True: para colunas estreitas (o tempo, a velocidade e os extras vao para uma segunda linha)."""
        super().__init__(pai, bg=tema.FUNDO)
        _estilos()
        self.ao_tempo = ao_tempo
        self.mp = None
        self.arquivo = None
        self.duracao = 0.0
        self.janela = None  # (inicio, fim) ou None = o video todo
        self.faixas = []
        self.marcas = []  # [(tempo, cor)]: risquinhos na barra (inicio marcado, por exemplo)
        self.pular = None
        self.parar_em = None
        self._sem_pular_ate_parar = False
        self._ultimo_pulo = (None, 0.0)
        self._inicio_pendente = None
        self._tempo = 0.0
        self._tique_id = None

        self.tela = tk.Frame(self, bg="black", height=altura, width=200)
        self.tela.pack(fill="both", expand=True)
        self.aviso = tk.Label(self.tela, text=texto_vazio, bg="black", fg=tema.TEXTO_2, font=tema.F_TEXTO,
                              justify="center")  # fmt: skip
        self.aviso.place(relx=0.5, rely=0.5, anchor="center")

        self.barra = tk.Canvas(self, height=16, width=200, bg=tema.FUNDO, highlightthickness=0, cursor="hand2")
        self.barra.pack(fill="x", pady=(4, 0))
        self.barra.bind("<Configure>", lambda e: self.desenhar_barra())
        self.barra.bind("<Button-1>", self._clique_barra)
        self.barra.bind("<B1-Motion>", self._arrastar_barra)
        self.barra.bind("<ButtonRelease-1>", self._soltar_barra)

        controles = tk.Frame(self, bg=tema.FUNDO)
        controles.pack(fill="x", pady=(4, 0))
        self.botoes = []
        for texto, comando, _tecla in (("⏪ 5s", lambda: self.andar(-5), "J"), ("◀|", lambda: self.quadro(-1), ","),
                                     ("▶", self.alternar, "K"), ("|▶", lambda: self.quadro(1), "."),
                                     ("5s ⏩", lambda: self.andar(5), "L")):  # fmt: skip
            b = ttk.Button(controles, text=texto, style="Player.TButton", command=comando, width=len(texto) + 1)
            b.pack(side="left", padx=(0, 3))
            self.botoes.append(b)
            if texto == "▶":
                self.btn_tocar = b
        if compacto:  # coluna estreita: tempo e velocidade na 2a linha, extras na 3a
            controles = tk.Frame(self, bg=tema.FUNDO)
            controles.pack(fill="x", pady=(4, 0))
        self.lbl_tempo = tk.Label(controles, text="0:00.0 / 0:00.0", bg=tema.FUNDO, fg=tema.TEXTO,
                                  font=(tema.FONTE, 10, "bold"), width=19, anchor="w")  # fmt: skip
        self.lbl_tempo.pack(side="left", padx=(0 if compacto else 6, 4))
        self.velocidade = tk.StringVar(value="1x")
        caixa = ttk.Combobox(controles, textvariable=self.velocidade, values=VELOCIDADES, width=5, state="readonly")
        caixa.pack(side="left")
        caixa.bind("<<ComboboxSelected>>", lambda e: self.mudar_velocidade())
        self.caixa_velocidade = caixa
        if compacto:
            self.extras = tk.Frame(self, bg=tema.FUNDO)
            self.extras.pack(fill="x", pady=(4, 0))
        else:
            self.extras = tk.Frame(controles, bg=tema.FUNDO)
            self.extras.pack(side="left", fill="x", expand=True, padx=(10, 0))

        self.bind("<Destroy>", self._destruido, add="+")
        if disponivel():
            self.after_idle(self._iniciar)
        else:
            self._mostrar_indisponivel()

    # ---------------------------------------------------------- liga e desliga o mpv
    def _mostrar_indisponivel(self):
        self.aviso.config(text="Player embutido indisponível neste PC.\nOs botões de ouvir/assistir abrem o trecho "
                          "no player do Windows.", fg=tema.TEXTO_2)  # fmt: skip
        for b in self.botoes:
            b.state(["disabled"])
        self.caixa_velocidade.state(["disabled"])

    def _iniciar(self):
        mpv = carregar_mpv()
        if not mpv or not self.winfo_exists():
            return
        try:
            self.tela.update_idletasks()
            self.mp = mpv.MPV(
                wid=str(int(self.tela.winfo_id())), keep_open="yes", idle="yes", pause=True, hr_seek="yes",
                input_default_bindings=False, input_vo_keyboard=False, input_cursor=False, cursor_autohide="no",
                load_scripts=False, ytdl=False, osd_level=0, hwdec="auto-safe", force_window="yes",
                vo=SAIDA_DE_VIDEO,
            )  # fmt: skip
        except Exception as e:
            try:  # opcoes que alguma versao do mpv nao conhece: tenta so com o essencial
                self.mp = mpv.MPV(wid=str(int(self.tela.winfo_id())), keep_open="yes", idle="yes", pause=True,
                                  hr_seek="yes", input_default_bindings=False, input_vo_keyboard=False)  # fmt: skip
            except Exception as e2:
                registrar(f"player: nao consegui abrir o mpv ({e}; {e2})")
                self.mp = None
                _mpv["erro"] = str(e2)
                self._mostrar_indisponivel()
                return
        if self.arquivo:
            arquivo, self.arquivo = self.arquivo, None
            self.abrir(arquivo, self._inicio_pendente or 0.0, self.janela)
        self._tique()

    def _destruido(self, evento):
        if evento.widget is not self:
            return
        self.fechar()

    def fechar(self):
        """Desliga o mpv (a janela vai fechar). Pode chamar mais de uma vez."""
        if self._tique_id:
            try:
                self.after_cancel(self._tique_id)
            except tk.TclError:
                pass
            self._tique_id = None
        mp, self.mp = self.mp, None
        if mp is not None:
            try:
                mp.terminate()
            except Exception as e:
                registrar(f"player: erro ao fechar o mpv ({e})")

    @property
    def pronto(self) -> bool:
        """O mpv esta ligado (o video aparece aqui dentro)."""
        return self.mp is not None

    # ---------------------------------------------------------- abrir e mover
    def abrir(self, arquivo, inicio: float = 0.0, janela=None):
        """Abre o video (pausado) no tempo 'inicio'. janela=(ini, fim) limita a barra e o fim do toque."""
        self.janela = janela
        self.parar_em = None
        inicio = reproducao.limitar(inicio, *(janela or (None, None)))
        if self.mp is None:  # o mpv ainda esta ligando (ou nao existe): abre quando ligar
            self.arquivo, self._inicio_pendente = str(arquivo), inicio
            if not disponivel():
                self._mostrar_indisponivel()
            return
        if self.arquivo == str(arquivo):
            self.ir(inicio)
            self.desenhar_barra()
            return
        self.arquivo = str(arquivo)
        self.duracao = 0.0
        self._tempo = inicio
        self.aviso.place_forget()
        try:
            self.mp.pause = True
            self.mp["start"] = f"{inicio:.3f}"
            self.mp.play(self.arquivo)
        except Exception as e:
            registrar(f"player: nao consegui abrir {arquivo} ({e})")
            self.aviso.config(text=f"Não consegui abrir o vídeo:\n{arquivo}")
            self.aviso.place(relx=0.5, rely=0.5, anchor="center")
        self.desenhar_barra()

    def tempo(self) -> float:
        return self._tempo

    @property
    def tocando(self) -> bool:
        try:
            return self.mp is not None and not self.mp.pause
        except Exception:
            return False

    def ir(self, t: float, exato: bool = True):
        """Vai para o tempo t (segundos do arquivo aberto), sem mudar se esta tocando ou pausado."""
        t = reproducao.limitar(t, *(self.janela or (None, self.duracao or None)))
        self._tempo = t
        if self.mp is None:
            self._inicio_pendente = t
            return
        try:
            self.mp.seek(t, "absolute", "exact" if exato else "keyframes")
        except Exception:  # o arquivo ainda esta carregando: comeca ali quando terminar
            try:
                self.mp["start"] = f"{t:.3f}"
            except Exception:
                pass
        self._mostrar_tempo(t)

    def tocar(self, de: float | None = None, ate: float | None = None, pulando: bool = True):
        """Toca a partir de 'de' (ou de onde esta) ate 'ate' (ou ate o fim). pulando=False: toca tudo, mesmo o que
        a tela mandou pular (para assistir o trecho que sai), ate parar."""
        if self.mp is None:
            return False
        if de is not None:
            self.ir(de)
        self.parar_em = ate
        self._sem_pular_ate_parar = not pulando
        try:
            self.mp.pause = False
        except Exception:
            return False
        self.btn_tocar.config(text="⏸")
        return True

    def pausar(self):
        self.parar_em = None
        self._sem_pular_ate_parar = False
        if self.mp is not None:
            try:
                self.mp.pause = True
            except Exception:
                pass
        self.btn_tocar.config(text="▶")

    def alternar(self):
        if self.tocando:
            self.pausar()
        else:
            ini, fim = self.janela if self.janela else (0.0, self.duracao)
            de = ini if fim and self._tempo >= fim - 0.1 else None  # chegou ao fim: comeca de novo
            self.tocar(de)

    def andar(self, segundos: float):
        self.ir(self._tempo + segundos)

    def quadro(self, direcao: int):
        """Um quadro para frente (1) ou para tras (-1). Pausa o video."""
        if self.mp is None:
            return
        try:
            if direcao > 0:
                self.mp.frame_step()
            else:
                self.mp.frame_back_step()
        except Exception:
            pass
        self.btn_tocar.config(text="▶")

    def mudar_velocidade(self):
        if self.mp is not None:
            try:
                self.mp.speed = float(self.velocidade.get().rstrip("x"))
            except Exception:
                pass

    # ---------------------------------------------------------- acompanhar o video
    def _tique(self):
        """Confere onde o video esta: para no fim, pula o que sai e avisa a tela."""
        if self.mp is None or not self.winfo_exists():
            return
        try:
            t = self.mp.time_pos
            pausado = self.mp.pause
            if not self.duracao:
                self.duracao = float(self.mp.duration or 0)
                if self.duracao:
                    self.desenhar_barra()
        except Exception:
            t, pausado = None, True
        if t is not None:
            self._tempo = float(t)
            if not pausado:
                self._ao_tocar(self._tempo)
            self._mostrar_tempo(self._tempo)
            self.btn_tocar.config(text="▶" if pausado or not self.tocando else "⏸")
            if self.ao_tempo:
                try:
                    self.ao_tempo(self._tempo)
                except Exception as e:
                    registrar("player: erro em ao_tempo", e)
        self._tique_id = self.after(INTERVALO_MS, self._tique)

    def _ao_tocar(self, t: float):
        fim = self.janela[1] if self.janela else None
        if self.parar_em is not None and t >= self.parar_em:
            self.pausar()
            return
        if fim is not None and t >= fim:
            self.pausar()
            self.ir(fim)
            return
        if self.pular and not self._sem_pular_ate_parar:
            alvo = self.pular(t)
            ultimo, quando = self._ultimo_pulo
            if alvo is not None and not (ultimo == alvo and time.monotonic() - quando < 1.0):
                self._ultimo_pulo = (alvo, time.monotonic())
                if self.duracao and alvo >= self.duracao - 0.05:
                    self.pausar()
                self.ir(alvo)

    def _mostrar_tempo(self, t: float):
        # o mesmo relogio das listas (tempo do video original), mesmo quando a barra mostra so um pedaco dele
        self.lbl_tempo.config(text=f"{reproducao.texto_do_tempo(t)} / {reproducao.texto_do_tempo(self.duracao)}")
        self._mover_cabeca(t)

    # ---------------------------------------------------------- barra de tempo
    def _limites(self):
        if self.janela:
            return self.janela
        return 0.0, self.duracao or 0.0

    def _x(self, t: float) -> float:
        ini, fim = self._limites()
        largura = max(10, self.barra.winfo_width() - 2)
        if fim <= ini:
            return 1
        return 1 + (largura - 1) * max(0.0, min(1.0, (t - ini) / (fim - ini)))

    def _t(self, x: float) -> float:
        ini, fim = self._limites()
        largura = max(10, self.barra.winfo_width() - 2)
        return ini + max(0.0, min(1.0, (x - 1) / (largura - 1))) * (fim - ini)

    def desenhar_barra(self):
        cv = self.barra
        cv.delete("all")
        largura = max(10, cv.winfo_width() - 2)
        cv.create_rectangle(1, 4, largura, 12, fill=tema.PAINEL, outline=tema.BORDA)
        ini, fim = self._limites()
        if fim <= ini:
            return
        for a, b, cor in self.faixas:
            if b > ini and a < fim:
                cv.create_rectangle(self._x(a), 4, max(self._x(b), self._x(a) + 1), 12, fill=cor, outline="")
        for t, cor in self.marcas:
            if ini <= t <= fim:
                cv.create_line(self._x(t), 0, self._x(t), 16, fill=cor, width=2)
        cv.create_rectangle(0, 0, 0, 0, tags=("feito",), fill=tema.LARANJA, outline="")
        cv.create_oval(0, 0, 0, 0, tags=("cabeca",), fill=tema.TEXTO, outline=tema.FUNDO)
        self._mover_cabeca(self._tempo)

    def _mover_cabeca(self, t: float):
        ini, fim = self._limites()
        if fim <= ini:
            return
        x = self._x(t)
        self.barra.coords("feito", 1, 7, x, 9)
        self.barra.coords("cabeca", x - 6, 2, x + 6, 14)

    def _clique_barra(self, evento):
        self._tocava = self.tocando
        if self._tocava and self.mp is not None:
            try:
                self.mp.pause = True
            except Exception:
                pass
        self.ir(self._t(evento.x), exato=False)

    def _arrastar_barra(self, evento):
        self.ir(self._t(evento.x), exato=False)

    def _soltar_barra(self, evento):
        self.ir(self._t(evento.x))
        if getattr(self, "_tocava", False):
            self.tocar()

    # ---------------------------------------------------------- teclado
    def ligar_atalhos(self, janela: tk.Misc):
        """Atalhos do player na janela inteira (nao atrapalham quando voce digita numa caixa de texto)."""

        def atalho(funcao):
            def rodar(evento):
                if isinstance(evento.widget, (tk.Entry, ttk.Entry, tk.Text, ttk.Combobox)):
                    return None
                if not self.pronto:
                    return None
                funcao()
                return "break"

            return rodar

        for tecla, funcao in (("<Control-space>", self.alternar), ("<k>", self.alternar), ("<K>", self.alternar),
                              ("<j>", lambda: self.andar(-5)), ("<J>", lambda: self.andar(-5)),
                              ("<l>", lambda: self.andar(5)), ("<L>", lambda: self.andar(5)),
                              ("<comma>", lambda: self.quadro(-1)), ("<period>", lambda: self.quadro(1))):  # fmt: skip
            janela.bind(tecla, atalho(funcao), add="+")
