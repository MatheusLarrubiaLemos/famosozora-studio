# Janela do EDITOR DE VIDEO do Studio (desde a 1.9.0), a mesma para os dois estudios:
#   - Longo ("Editar" na aba Videos longos): a live inteira, predefinicao "Longo (TV)", introducao, capitulos,
#     marcador de Short e "Gerar o episodio".
#   - Short ("Ajustar corte" no editor de Shorts): so a janela do Short (com 10 s antes e depois), predefinicao
#     "Short (dinamico)", previa vertical, bordas arrastaveis e "Renderizar este Short".
# Em cima o player (ate 4x, a voz sem esquilo), embaixo a timeline e do lado a lista das sugestoes.
# O "cerebro" (cortes, desfazer, ima) fica em editor/estado.py; o que e lido e gravado, em editor/arquivos.py.
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

from autoedit import predefinicoes
from autoedit import trechos as tr
from editor import arquivos
from editor import player as player_mod
from editor.estado import VELOCIDADES, EstadoEditor, proxima_velocidade
from editor.timeline import CORES, Timeline
from interface import tema
from interface.utilidades import em_segundo_plano, janela_ja_aberta, lembrar_janela, rodar_script
from nucleo.comum import carregar_config, ler_json, tempo_txt
from nucleo.registro import registrar

ATALHOS = [
    ("Espaço / K", "tocar / pausar"), ("L", "mais rápido (1 → 1,5 → 2 → 3 → 4x)"), ("J", "mais devagar"),
    ("I / O", "marcar início / fim"), ("X", "cortar o trecho marcado (I até O)"), ("C", "dividir no ponto atual"),
    ("Delete", "cortar o trecho selecionado"), ("R", "restaurar (volta a manter)"),
    ("N / B", "próxima / anterior sugestão"), ("Enter", "aceitar a sugestão"), ("Backspace", "recusar a sugestão"),
    ("← / →", "um quadro"), ("Shift + ← / →", "5 segundos"), ("Ctrl + ← / →", "próxima / anterior troca de cena"),
    ("M", "adicionar marcador (Short, capítulo, nota)"), ("Ctrl + Z", "desfazer"), ("Ctrl + Shift + Z", "refazer"),
    ("Ctrl + roda do mouse", "zoom na timeline"), ("Alt + arrastar borda", "ajustar sem ímã"),
    ("Ctrl + S", "salvar agora (ele já salva sozinho)"), ("?", "esta lista"),
]  # fmt: skip
MODOS = [("original", "Original"), ("previa", "Prévia do resultado"), ("so_sai", "Só o que vai sair")]
NOMES_FILTRO = [("todos", "Todas"), ("silencio", "Silêncio"), ("sem_jogo", "Sem jogo"), ("sem_acao", "Sem ação"),
                ("papo_fora", "Papo fora / dúvida")]  # fmt: skip
CHAVE_DICA = "editor_dica_vista"


def quando_pronto(funcao):
    """Botao apertado enquanto o editor ainda esta abrindo: so avisa (em vez de dar erro)."""

    def rodar(self, *a, **k):
        if self.estado is None or self.timeline is None:
            try:
                self.lbl_status.configure(text="Ainda abrindo o vídeo... espere um instante.")
            except tk.TclError:
                pass
            return None
        return funcao(self, *a, **k)

    rodar.__name__ = funcao.__name__
    rodar.__doc__ = funcao.__doc__
    return rodar


class JanelaEditor:
    @classmethod
    def abrir_longo(cls, studio, info: dict):
        chave = ("editor", "longo", str(info["pasta"]))
        return janela_ja_aberta(chave) or lembrar_janela(chave, cls(studio, info, "longo"))

    @classmethod
    def abrir_short(cls, studio, info: dict, n: int, parent=None):
        chave = ("editor", "short", str(info["pasta"]), n)
        return janela_ja_aberta(chave) or lembrar_janela(chave, cls(studio, info, "short", n, parent))

    def __init__(self, studio, info: dict, tipo: str, n: int | None = None, parent=None, container=None,
                 container_baixo=None):  # fmt: skip
        """container = um quadro de OUTRA janela: o editor fica encaixado nele, numa versao compacta (desde a
        1.9.1, o Short e editado dentro da propria janela "Revisar legendas")."""
        self.studio, self.info, self.tipo, self.n = studio, info, tipo, n
        self.embutido = container is not None
        self.ao_tique = None  # funcao(t) chamada a cada atualizacao do player (a janela de legendas usa)
        self.ao_carregar = None  # funcao() chamada quando o video e a timeline ficam prontos
        self.container_baixo = container_baixo  # encaixado: a timeline vai aqui (embaixo, na largura toda)
        self.pasta = Path(info["pasta"])
        self.cfg = carregar_config()
        self.regras = predefinicoes.da(tipo)
        self.estado = None
        self.timeline = None
        self.dados_abertos = None
        self.video, self.duracao = None, 0.0
        self.player = None
        self.modo = tk.StringVar(value="original")
        self.serie = tk.BooleanVar(value=False)
        self.vertical = tk.BooleanVar(value=True)
        self.filtro = tk.StringVar(value="todos")
        self._previa_var = tk.BooleanVar(value=False)
        self._salvar_id = None
        self._parar_em = None
        self._vel_base = 1.0
        self._acelerando = False
        self._fechada = False
        self._processo_cancelar = None
        self.gravador = arquivos.GravadorLongo(self.pasta) if tipo == "longo" else None
        self._mini_cache, self._folhas = {}, {}

        if self.embutido:
            self.jan = container.winfo_toplevel()
            self.raiz = tk.Frame(container, bg=tema.FUNDO)
            self.raiz.pack(fill="both", expand=True)
        else:
            self.jan = tk.Toplevel(parent or studio.raiz)
            self.raiz = self.jan
            self.jan.title(("Editar: " if tipo == "longo" else f"Ajustar corte do Short {n}: ") + info.get("nome", ""))
            self.jan.configure(bg=tema.FUNDO)
            largura = min(1320, self.jan.winfo_screenwidth() - 40)  # cabe numa tela de 1366x768
            altura = min(820, self.jan.winfo_screenheight() - 70)
            self.jan.geometry(f"{largura}x{altura}+10+10")
            self.jan.minsize(min(1000, largura), min(600, altura))
            self.jan.protocol("WM_DELETE_WINDOW", self.fechar)
        if self.embutido:
            self._montar_compacto()
        else:
            self._montar()
        self._ligar_atalhos()
        self.lbl_status.configure(text="Abrindo...")
        em_segundo_plano(self.studio.raiz, self._carregar, self._carregou)

    # ================================================================ montagem da tela
    def _montar(self):
        topo = tk.Frame(self.raiz, bg=tema.FUNDO)
        topo.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(topo, text="Editor de vídeo" + (" — vídeo longo" if self.tipo == "longo" else " — Short"),
                 bg=tema.FUNDO, fg=tema.TEXTO, font=tema.F_SUBTITULO).pack(side="left")  # fmt: skip
        self.lbl_predef = tk.Label(topo, text="", bg=tema.FUNDO, fg=tema.TEXTO_2, font=tema.F_PEQUENA)
        self.lbl_predef.pack(side="left", padx=12)
        ttk.Button(topo, text="?  Atalhos", style="Extra.TButton", command=self.mostrar_atalhos).pack(side="right")
        if self.tipo == "longo":
            ttk.Button(topo, text="Gerar o episódio", style="Passo.TButton", command=self.exportar).pack(
                side="right", padx=6)
            self.btn_outro_editor = ttk.Button(topo, text="Outro editor ▾", style="Extra.TButton",
                                               command=self.exportar_outro_editor)  # fmt: skip
            self.btn_outro_editor.pack(side="right", padx=2)
            ttk.Checkbutton(topo, text="Episódio de série", variable=self.serie, command=self._mudou).pack(
                side="right", padx=6)
        else:
            ttk.Button(topo, text="Renderizar este Short", style="Passo.TButton", command=self.exportar).pack(
                side="right", padx=6)
            ttk.Checkbutton(topo, text="Prévia vertical", variable=self.vertical, command=self._aplicar_filtro).pack(
                side="right", padx=6)
        self.btn_analisar = ttk.Button(topo, text="Analisar", style="Extra.TButton", command=self.analisar)
        self.btn_analisar.pack(side="right", padx=6)

        self.lbl_aviso = tk.Label(self.raiz, text="", bg=tema.FUNDO, fg=tema.AMARELO, font=tema.F_PEQUENA,
                                  anchor="w", justify="left", wraplength=1200)  # fmt: skip
        self.lbl_aviso.pack(fill="x", padx=12)
        self.lbl_relatorio = tk.Label(self.raiz, text="", bg=tema.FUNDO, fg=tema.TEXTO_2, font=tema.F_PEQUENA,
                                      anchor="w")  # fmt: skip
        self.lbl_relatorio.pack(fill="x", padx=12)

        self.lbl_dica = tk.Label(self.raiz, text="", bg=tema.FUNDO, fg=tema.TEXTO_2, font=tema.F_PEQUENA, anchor="w")
        self.lbl_dica.pack(side="bottom", fill="x", padx=12, pady=(0, 6))
        baixo = tk.Frame(self.raiz, bg=tema.FUNDO)  # a timeline tem o lugar dela garantido (empacotada antes)
        baixo.pack(side="bottom", fill="x", padx=12, pady=(0, 4))
        zoom = tk.Frame(baixo, bg=tema.FUNDO)
        zoom.pack(fill="x")
        ttk.Button(zoom, text="−", width=3, style="Extra.TButton", command=lambda: self.timeline and self.timeline.zoom(0.6)).pack(
            side="left")
        ttk.Button(zoom, text="+", width=3, style="Extra.TButton", command=lambda: self.timeline and self.timeline.zoom(1.6)).pack(
            side="left", padx=2)
        ttk.Button(zoom, text="Ver tudo", style="Extra.TButton", command=self._ver_tudo).pack(side="left", padx=2)
        self.lbl_status = tk.Label(zoom, text="", bg=tema.FUNDO, fg=tema.TEXTO_2, font=tema.F_PEQUENA)
        self.lbl_status.pack(side="left", padx=10)
        self.barra = ttk.Progressbar(zoom, length=220, mode="determinate", maximum=100)
        self.btn_cancelar = ttk.Button(zoom, text="Cancelar", style="Extra.TButton", command=self.cancelar_analise)
        self.quadro_timeline = tk.Frame(baixo, bg=tema.FUNDO)
        self.quadro_timeline.pack(fill="x", pady=(4, 0))

        meio = tk.PanedWindow(self.raiz, orient="horizontal", bg=tema.FUNDO, sashwidth=6, bd=0)
        meio.pack(fill="both", expand=True, padx=12, pady=6)
        esquerda = tk.Frame(meio, bg=tema.FUNDO)
        self.tela = tk.Frame(esquerda, bg="black", height=300)
        self.tela.pack(fill="both", expand=True)
        self.tela_video = tk.Frame(self.tela, bg="black")  # o mpv desenha aqui dentro
        self.tela_video.pack(fill="both", expand=True)
        self.canvas_mini = tk.Canvas(self.tela, bg="black", highlightthickness=0)  # usado so sem o mpv
        controles = tk.Frame(esquerda, bg=tema.FUNDO)
        controles.pack(fill="x", pady=(6, 0))
        self.btn_tocar = ttk.Button(controles, text="▶", width=4, style="Extra.TButton", command=self.alternar)
        self.btn_tocar.pack(side="left")
        for v in VELOCIDADES:
            ttk.Button(controles, text=f"{v:g}x".replace(".", ","), width=5, style="Extra.TButton",
                       command=lambda v=v: self.mudar_velocidade(v)).pack(side="left", padx=1)  # fmt: skip
        for valor, texto in MODOS:
            ttk.Radiobutton(controles, text=texto, value=valor, variable=self.modo).pack(side="left", padx=4)
        self.lbl_tempo = tk.Label(esquerda, text="", bg=tema.FUNDO, fg=tema.TEXTO, font=tema.F_TEXTO, anchor="w")
        self.lbl_tempo.pack(fill="x", pady=(4, 0))
        meio.add(esquerda, stretch="always", minsize=560)

        direita = tk.Frame(meio, bg=tema.FUNDO)
        tk.Label(direita, text="Sugestões (clique para ir até ela)", bg=tema.FUNDO, fg=tema.TEXTO,
                 font=tema.F_TEXTO_NEGRITO).pack(anchor="w")  # fmt: skip
        linha_filtro = tk.Frame(direita, bg=tema.FUNDO)
        linha_filtro.pack(fill="x", pady=2)
        self.combo_filtro = ttk.Combobox(linha_filtro, state="readonly", width=18,
                                         values=[t for _, t in NOMES_FILTRO])  # fmt: skip
        self.combo_filtro.current(0)
        self.combo_filtro.bind("<<ComboboxSelected>>", lambda e: self._preencher_lista())
        self.combo_filtro.pack(side="left")
        ttk.Button(linha_filtro, text="Aceitar todas deste tipo", style="Extra.TButton",
                   command=self.aceitar_tipo).pack(side="left", padx=6)  # fmt: skip
        quadro_lista = tk.Frame(direita, bg=tema.FUNDO)
        quadro_lista.pack(fill="both", expand=True)
        self.lista = ttk.Treeview(quadro_lista, columns=("tempo", "dur", "motivo", "conf", "estado"), show="headings",
                                  selectmode="browse", height=14)  # fmt: skip
        for col, texto, larg in (("tempo", "Tempo", 70), ("dur", "Duração", 60), ("motivo", "Motivo", 90),
                                 ("conf", "Confiança", 70), ("estado", "Situação", 90)):  # fmt: skip
            self.lista.heading(col, text=texto)
            self.lista.column(col, width=larg, anchor="w")
        barra = ttk.Scrollbar(quadro_lista, command=self.lista.yview)
        self.lista.configure(yscrollcommand=barra.set)
        self.lista.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        self.lista.bind("<<TreeviewSelect>>", self._clicou_lista)
        botoes = tk.Frame(direita, bg=tema.FUNDO)
        botoes.pack(fill="x", pady=4)
        ttk.Button(botoes, text="✔ Aceitar (Enter)", style="Extra.TButton", command=self.aceitar).pack(side="left")
        ttk.Button(botoes, text="✖ Recusar (Backspace)", style="Extra.TButton", command=self.recusar).pack(
            side="left", padx=4)
        self.btn_reanalisar = ttk.Button(direita, text="Analisar de novo com esta predefinição (mantém os seus cortes)",
                                         style="Extra.TButton", command=self.reanalisar)  # fmt: skip
        self.btn_reanalisar.pack(fill="x", pady=(2, 0))
        legenda = tk.Frame(direita, bg=tema.FUNDO)
        legenda.pack(fill="x", pady=(6, 0))
        for nome, cor in (("silêncio", CORES["silencio"]), ("sem jogo", CORES["sem_jogo"]),
                          ("sem ação", CORES["sem_acao"]), ("dúvida", CORES["duvida"]), ("seu corte", CORES["manual"])):
            tk.Label(legenda, text="■ " + nome, bg=tema.FUNDO, fg=cor, font=tema.F_PEQUENA).pack(side="left", padx=3)
        meio.add(direita, minsize=360)


    def _montar_compacto(self):
        """Versao encaixada (Short dentro da janela de legendas): player vertical, controles e timeline, numa coluna."""
        r = self.raiz
        topo = tk.Frame(r, bg=tema.FUNDO)
        topo.pack(fill="x")
        tk.Label(topo, text="Vídeo do Short", bg=tema.FUNDO, fg=tema.TEXTO, font=tema.F_TEXTO_NEGRITO).pack(side="left")
        ttk.Button(topo, text="?", width=1, style="Extra.TButton", command=self.mostrar_atalhos).pack(side="right")
        ttk.Checkbutton(topo, text="Vertical", variable=self.vertical, command=self._aplicar_filtro).pack(side="right")
        self.btn_analisar = ttk.Button(topo, text="Sugerir", width=1, style="Extra.TButton", command=self.analisar)
        self.btn_analisar.pack(side="right", padx=4, fill="x", expand=True)
        self.lbl_predef = tk.Label(r, text="", bg=tema.FUNDO, fg=tema.TEXTO_2, font=tema.F_PEQUENA, anchor="w")
        self.lbl_aviso = tk.Label(r, text="", bg=tema.FUNDO, fg=tema.AMARELO, font=tema.F_PEQUENA, anchor="w",
                                  justify="left", wraplength=380)  # fmt: skip
        self.lbl_aviso.pack(fill="x")
        self.lbl_dica = tk.Label(r, text="", bg=tema.FUNDO, fg=tema.TEXTO_2, font=tema.F_PEQUENA, anchor="w",
                                 justify="left", wraplength=380)  # fmt: skip
        self.lbl_dica.pack(side="bottom", fill="x")
        if self.container_baixo is not None:
            self.baixo = baixo = tk.Frame(self.container_baixo, bg=tema.FUNDO)  # estilo CapCut: timeline embaixo de tudo
            baixo.pack(fill="x")
        else:
            self.baixo = baixo = tk.Frame(r, bg=tema.FUNDO)
            baixo.pack(side="bottom", fill="x", pady=(2, 0))
        zoom = tk.Frame(baixo, bg=tema.FUNDO)
        zoom.pack(fill="x")
        ttk.Button(zoom, text="−", width=3, style="Extra.TButton",
                   command=lambda: self.timeline and self.timeline.zoom(0.6)).pack(side="left")  # fmt: skip
        ttk.Button(zoom, text="+", width=3, style="Extra.TButton",
                   command=lambda: self.timeline and self.timeline.zoom(1.6)).pack(side="left", padx=2)  # fmt: skip
        ttk.Button(zoom, text="Tudo", style="Extra.TButton", command=self._ver_tudo).pack(side="left")
        self.lbl_status = tk.Label(zoom, text="", bg=tema.FUNDO, fg=tema.TEXTO_2, font=tema.F_PEQUENA, anchor="w")
        self.lbl_status.pack(side="left", padx=6, fill="x", expand=True)
        self.barra = ttk.Progressbar(zoom, length=120, mode="determinate", maximum=100)
        self.btn_cancelar = ttk.Button(zoom, text="Cancelar", style="Extra.TButton", command=self.cancelar_analise)
        largo = self.container_baixo is not None  # timeline na largura toda: tudo numa linha so (economiza altura)
        self.lbl_relatorio = tk.Label(zoom if largo else baixo, text="", bg=tema.FUNDO, fg=tema.TEXTO_2,
                                      font=tema.F_PEQUENA, anchor="w", justify="left", wraplength=380)  # fmt: skip
        self.lbl_relatorio.pack(side="left", padx=8) if largo else self.lbl_relatorio.pack(fill="x")
        sugestoes = tk.Frame(zoom if largo else baixo, bg=tema.FUNDO, width=420 if largo else 0)
        self.quadro_timeline = tk.Frame(baixo, bg=tema.FUNDO)
        self.quadro_timeline.pack(fill="x", pady=(2, 0))
        if largo:
            sugestoes.pack(side="right")
        else:
            sugestoes.pack(fill="x", pady=(2, 0))
        tk.Label(sugestoes, text="Sugestões:", bg=tema.FUNDO, fg=tema.TEXTO_2, font=tema.F_PEQUENA).grid(
            row=0, column=0, padx=(0, 2))
        botoes = (("◀", lambda: self.ir_sugestao(True)), ("▶", lambda: self.ir_sugestao(False)),
                  ("✔", self.aceitar), ("✖", self.recusar), ("Todas", self.aceitar_tipo))
        for k, (texto, comando) in enumerate(botoes, 1):  # grade: os botoes encolhem juntos numa tela pequena
            ttk.Button(sugestoes, text=texto, width=len(texto) if len(texto) > 1 else 1, style="Extra.TButton",
                       command=comando).grid(
                row=0, column=k, sticky="ew", padx=1)
            sugestoes.columnconfigure(k, weight=2 if k == len(botoes) else 1, uniform="sug" if k < len(botoes) else "")
        self.tela = tk.Frame(r, bg="black", height=260)
        self.tela.pack(fill="both", expand=True, pady=(4, 0))
        self.tela_video = tk.Frame(self.tela, bg="black")
        self.tela_video.pack(fill="both", expand=True)
        self.canvas_mini = tk.Canvas(self.tela, bg="black", highlightthickness=0)
        controles = tk.Frame(r, bg=tema.FUNDO)
        controles.pack(fill="x", pady=(4, 0))
        self.btn_tocar = ttk.Button(controles, text="▶", width=1, style="Extra.TButton", command=self.alternar)
        self.btn_tocar.grid(row=0, column=0, sticky="ew")
        controles.columnconfigure(0, weight=1, uniform="vel")
        for k, v in enumerate((1.0, 1.5, 2.0, 4.0), 1):
            ttk.Button(controles, text=f"{v:g}x".replace(".", ","), width=1, style="Extra.TButton",
                       command=lambda v=v: self.mudar_velocidade(v)).grid(row=0, column=k, sticky="ew", padx=1)  # fmt: skip
            controles.columnconfigure(k, weight=1, uniform="vel")
        ttk.Checkbutton(controles, text="Prévia", variable=self._previa_var,
                        command=lambda: self.modo.set("previa" if self._previa_var.get() else "original")
                        ).grid(row=0, column=5, padx=(4, 0))  # fmt: skip
        self.lbl_tempo = tk.Label(r, text="", bg=tema.FUNDO, fg=tema.TEXTO, font=tema.F_PEQUENA, anchor="w",
                                  justify="left", wraplength=380)  # fmt: skip
        self.lbl_tempo.pack(fill="x")
        escondido = tk.Frame(r)  # o que a versao grande tem e a compacta nao mostra (as funcoes continuam iguais)
        self.combo_filtro = ttk.Combobox(escondido, state="readonly", values=[t for _, t in NOMES_FILTRO])
        self.combo_filtro.current(0)
        self.lista = ttk.Treeview(escondido, columns=("tempo", "dur", "motivo", "conf", "estado"), show="headings")
        self.btn_reanalisar = ttk.Button(escondido, text="", command=self.reanalisar)

    # ================================================================ carregar
    def _carregar(self) -> dict:
        """Em segundo plano: le tudo do disco (nada de tela aqui)."""
        from autoedit import analisar
        from autoedit.base import pasta_analise
        from autoedit.proxy import arq_proxy, proxy_pronto
        from videos_longos.pedido_edicao import carregar_palavras, info_video

        video, dur = info_video(self.pasta)
        pa = self.pasta / "analise"
        palavras = carregar_palavras(self.pasta)
        r = {"video": video, "duracao": dur, "palavras": palavras, "avisos": []}
        if not video.exists():
            r["avisos"].append(f"Não achei o vídeo original ({video.name}). Ele foi movido ou renomeado?")
        r["proxy"] = arq_proxy(pa) if pa.exists() and proxy_pronto(pa, video) else None
        r["mini"] = ler_json(pa / "miniaturas" / "miniaturas.json") if pa.exists() else None
        if self.tipo == "longo":
            dados = arquivos.ler_edicao_longo(self.pasta)
            r["dados"] = dados
            r["analisado"] = bool(dados.get("predefinicao"))
            sinais = analisar.carregar_sinais(self.pasta)
            r["inicio"], r["fim"], r["limites"] = 0.0, dur, None
        else:
            corte = arquivos.corte_do_short(self.pasta, self.n)
            if corte is None:
                raise RuntimeError(f"O Short {self.n} não existe mais no cortes.json.")
            from nucleo.comum import ler_tempo

            a, b = ler_tempo(corte["inicio"]), ler_tempo(corte["fim"])
            salvo = arquivos.ler_short(self.pasta, self.n)
            if salvo and salvo.get("limites"):
                a2, b2 = salvo["limites"]
                if abs(a2 - a) > 0.06 or abs(b2 - b) > 0.06:
                    salvo = None  # o corte mudou depois: comeca de novo
            r["salvo"] = salvo
            r["inicio"], r["fim"] = max(0.0, a - arquivos.FOLGA_SHORT), min(dur or b + 10, b + arquivos.FOLGA_SHORT)
            r["limites"] = (a, b)
            r["corte"] = corte
            try:
                sinais = analisar.analisar_janela(self.pasta, r["inicio"], r["fim"])
                pasta_analise(self.pasta)
            except Exception as e:
                registrar("editor: análise da janela do Short", e)
                sinais = {}
                r["avisos"].append(f"Não consegui medir o som e a imagem do Short ({e}).")
            r["sugestoes"] = (analisar.sugerir(self.pasta, "short", self.regras, r["inicio"], r["fim"], dur)
                              if sinais.get("som") else [])  # fmt: skip
        r["sinais"] = sinais
        return r

    def _viva(self) -> bool:
        """A janela ainda esta aberta? (algo em segundo plano pode terminar depois de voce fechar)"""
        try:
            return not self._fechada and bool(self.raiz.winfo_exists())
        except tk.TclError:
            return False

    def _carregou(self, r):
        if not self._viva():
            return
        if isinstance(r, Exception):
            registrar("editor: não consegui abrir", r)
            messagebox.showerror("Editor", f"Não consegui abrir o editor.\n\n{r}", parent=self.jan)
            self.fechar()
            return
        self.dados_abertos = r
        self.video, self.duracao = r["video"], r["duracao"] or 1.0
        sinais = r.get("sinais") or {}
        trocas = (sinais.get("imagem") or {}).get("trocas") or []
        if self.tipo == "longo":
            dados = r["dados"]
            self.serie.set(bool(dados.get("serie")))
            self.estado = EstadoEditor("longo", self.duracao, self.regras, dados.get("trechos") or [],
                                       dados.get("marcadores") or [], dados.get("introducao"), palavras=r["palavras"],
                                       trocas=trocas, protegidos_extra=arquivos.protegidos_do_claude(dados))  # fmt: skip
        else:
            salvo = r.get("salvo")
            trechos = salvo["trechos"] if salvo else r.get("sugestoes") or []
            self.estado = EstadoEditor("short", self.duracao, self.regras, trechos, (salvo or {}).get("marcadores") or [],
                                       inicio=r["inicio"], fim=r["fim"], palavras=r["palavras"], trocas=trocas,
                                       limites=r["limites"])  # fmt: skip
        baixa = self.embutido and self.jan.winfo_screenheight() < 950  # notebook: timeline mais fina
        self.timeline = Timeline(self.quadro_timeline, self.estado, self.pular, self.selecionar, self.menu_trecho,
                                 self._mudou, baixa=baixa)  # fmt: skip
        self.timeline.pack(fill="x")
        if self.embutido:
            self._ligar_atalhos(self.timeline)
            for w in (self.tela_video, self.canvas_mini):
                w.bind("<Button-1>", lambda e: self.timeline.focus_set(), add="+")
        som = sinais.get("som")
        if som:
            from autoedit.sinais_audio import onda

            self.timeline.onda = onda(som)
            self.timeline.onda_ms = som.get("onda_ms", 10)
            self.timeline.estado_inicio_onda = float(som.get("inicio", 0.0))
        if r.get("mini"):
            self.timeline.mini = (r["mini"], self._miniatura)
        avisos = list(r["avisos"])
        fonte = r.get("proxy") or (self.video if self.video.exists() else None)
        self.jan.update_idletasks()  # o quadro do video precisa existir na tela antes do mpv entrar nele
        self.player, aviso_player = player_mod.criar(self.tela_video, self._mostrar_miniatura)
        if aviso_player:
            avisos.append(aviso_player)
            self.tela_video.pack_forget()
            self.canvas_mini.pack(fill="both", expand=True)
        if fonte:
            self.player.carregar(fonte, self.estado.limites[0] if self.estado.limites else 0.0)
            self._aplicar_filtro()
        if self.tipo == "longo":
            avisos.insert(0, "Estilo TV: pausas naturais durante o jogo ficam. Isso segue as diretrizes do canal.")
            if not r.get("analisado"):
                avisos.append("Esta live ainda não foi analisada: clique em \"Analisar\" para o Studio sugerir os "
                              "cortes (silêncio, sem jogo, sem ação).")  # fmt: skip
            elif not r.get("proxy"):
                avisos.append("A versão leve do vídeo ainda não existe: o editor usa o original (pode pular mais "
                              "devagar). \"Analisar\" cria a versão leve.")  # fmt: skip
            if self.serie.get() and not self.estado.introducao:
                avisos.append("Episódio de série sem introdução marcada: marque com I e O e use o botão direito → "
                              "\"Marcar como introdução\".")  # fmt: skip
        if self.tipo == "short":
            self.btn_analisar.configure(text="Sugerir de novo" if not self.embutido else "Sugerir")
        else:
            self.btn_analisar.configure(text="Analisar a live" if not r.get("analisado") else "Analisar de novo")
        self.lbl_aviso.configure(text="\n".join("• " + a for a in avisos))
        self.lbl_status.configure(text="")
        self._dica_inicial()
        self.atualizar_tudo()
        if self.ao_carregar:
            self.ao_carregar()
        self.jan.after(300, self.timeline.ajustar_tudo)
        self.jan.after(320, self.timeline.desenhar)
        self._tique()

    # ================================================================ miniaturas (timeline e player sem mpv)
    def _folha(self, nome: str):
        if nome not in self._folhas:
            arq = self.pasta / "analise" / "miniaturas" / nome
            try:
                self._folhas[nome] = tk.PhotoImage(master=self.jan, file=str(arq))
            except tk.TclError:
                self._folhas[nome] = None
        return self._folhas[nome]

    def _miniatura(self, t: float, reduzir: int = 2):
        from autoedit.proxy import onde_esta_miniatura

        info = (self.dados_abertos or {}).get("mini")
        lugar = onde_esta_miniatura(info, t) if info else None
        if not lugar:
            return None
        chave = (lugar, reduzir)
        if chave not in self._mini_cache:
            folha = self._folha(lugar[0])
            if folha is None:
                return None
            img = tk.PhotoImage(master=self.jan)
            x, y = lugar[1], lugar[2]
            img.tk.call(img, "copy", folha, "-from", x, y, x + info["largura"], y + info["altura"],
                        "-subsample", reduzir, reduzir)  # fmt: skip
            if len(self._mini_cache) > 600:
                self._mini_cache.clear()
            self._mini_cache[chave] = img
        return self._mini_cache[chave]

    def _mostrar_miniatura(self, t: float):
        img = self._miniatura(t, 1)
        self.canvas_mini.delete("all")
        if img is not None:
            w, h = self.canvas_mini.winfo_width(), self.canvas_mini.winfo_height()
            self.canvas_mini.create_image(w / 2, h / 2, image=img)
        self.canvas_mini.create_text(10, 10, anchor="nw", fill=tema.TEXTO_2, font=tema.F_PEQUENA,
                                     text="(sem o player de vídeo: só a miniatura, sem som)")  # fmt: skip

    def _aplicar_filtro(self):
        """Short: previa vertical (camera em cima, jogo embaixo, igual ao render)."""
        if not self.player or self.tipo != "short":
            return
        grafo = None
        if self.vertical.get():
            try:
                from nucleo.video import dimensoes_video, filtro_layout

                fonte = (self.dados_abertos or {}).get("proxy") or self.video
                w, h = dimensoes_video(fonte)
                cfg = dict(self.cfg, altura_camera=int(self.cfg.get("altura_camera", 600)) // 2)
                grafo = filtro_layout(cfg, w, h, 540, 960, "entrada")
                grafo = grafo.replace("[entrada]", "", 1)
            except Exception as e:
                registrar("editor: prévia vertical", e)
        self.player.filtro(grafo)

    # ================================================================ laco do player
    def _tique(self):
        if not self._viva() or not self.player:
            return
        try:
            t = self.player.tempo()
            if self.player.tocando():
                t = self._regras_do_modo(t)
            if isinstance(self.player, player_mod.PlayerMiniaturas):
                self._mostrar_miniatura(t)
            self.timeline.mover_cursor(t)
            if self.player.tocando():
                self.timeline.seguir(t)
            self._mostrar_tempo(t)
            if self.ao_tique:
                self.ao_tique(t, self.player.tocando())
        except Exception as e:
            registrar("editor: atualização do player", e)
        self.jan.after(50, self._tique)

    def _regras_do_modo(self, t: float) -> float:
        """Previa pula os cortes (e acelera o que acelera); 'Só o que vai sair' toca so os cortes."""
        if self._parar_em is not None and t >= self._parar_em:
            self.player.pausar()
            self._parar_em = None
            return t
        lim = self.estado.limites
        if t >= (lim[1] if lim and self.modo.get() == "previa" else self.estado.fim) - 0.02:
            self.player.pausar()
            return t
        modo = self.modo.get()
        if modo == "previa":
            if lim and t < lim[0] - 0.05:
                self.player.ir(lim[0])
                return lim[0]
            acao = self.estado.acao_em(t)
            if acao and acao[0] == "cortar":
                alvo = acao[2][1]
                if lim and alvo >= lim[1]:  # Short: o corte vai ate o fim do Short -> acabou
                    self.player.pausar()
                    return t
                self.player.ir(alvo)
                return alvo
            vel = acao[1] if acao and acao[0] == "acelerar" else 1.0
            alvo = min(4.0, self._vel_base * vel)
            if abs(self.player.velocidade() - alvo) > 0.01:
                self.player.velocidade(alvo)
        elif modo == "so_sai":
            cortes = [(a, b) for a, b, acao, _ in self.estado.resolvidos() if acao == "cortar"]
            if not any(a <= t < b for a, b in cortes):
                proximos = [a for a, b in cortes if a > t]
                if proximos:
                    self.player.ir(proximos[0])
                    return proximos[0]
                self.player.pausar()
        elif abs(self.player.velocidade() - self._vel_base) > 0.01:
            self.player.velocidade(self._vel_base)
        return t

    def _mostrar_tempo(self, t: float):
        if not self.estado:
            return
        mapa_t = self.estado.mapa().final(t)
        txt = (f"{tempo_txt(t)}  /  original {tempo_txt(self.estado.duracao_bruta())}  →  final "
               f"{tempo_txt(self.estado.duracao_final())}   ·   no vídeo final: {tempo_txt(mapa_t)}   ·   "
               f"velocidade {self._vel_base:g}x")  # fmt: skip
        if self.embutido:  # coluna estreita: so o essencial
            txt = (f"{tempo_txt(t)}  ·  Short: {self.estado.duracao_final():.1f} s (era "
                   f"{self.estado.duracao_bruta():.1f} s)  ·  {self._vel_base:g}x")  # fmt: skip
        if self.estado.marca_in is not None or self.estado.marca_out is not None:
            txt += f"   ·   I {tempo_txt(self.estado.marca_in or 0)}  O {tempo_txt(self.estado.marca_out or 0)}"
        self.lbl_tempo.configure(text=txt)
        self.btn_tocar.configure(text="⏸" if self.player.tocando() else "▶")

    # ================================================================ comandos do player
    def tempo(self) -> float:
        return self.player.tempo() if self.player else 0.0

    def pular(self, t: float):
        if self.player:
            self.player.ir(t)
            self.timeline.mover_cursor(t)

    @quando_pronto
    def alternar(self):
        if not self.player:
            return
        if self.player.tocando():
            self.player.pausar()
        else:
            self._parar_em = None
            self.player.tocar()

    @quando_pronto
    def mudar_velocidade(self, v: float):
        self._vel_base = v
        if self.player:
            self.player.velocidade(v)

    def acelerar(self, mais: bool):
        self.mudar_velocidade(proxima_velocidade(self._vel_base, mais))
        if mais and self.player and not self.player.tocando():
            self.player.tocar()

    def ouvir_trecho(self, k):
        if k is None or not self.player:
            return
        x = self.estado.trechos[k]
        self.modo.set("original")
        self.player.ir(x["inicio"])
        self._parar_em = x["fim"]
        self.player.tocar()

    # ================================================================ edicao
    def _mudou(self):
        """Algo mudou: redesenha e agenda a gravacao (no maximo 1 s depois)."""
        if not self.estado:
            return
        self.estado.mudou_desde_salvar = True
        self.atualizar_tudo()
        if self._salvar_id:
            self.jan.after_cancel(self._salvar_id)
        self._salvar_id = self.jan.after(1000, self.salvar)  # salva sozinho (no maximo 1 s depois)

    def salvar(self):
        self._salvar_id = None
        if not self.estado:
            return
        try:
            if self.tipo == "longo":
                self.gravador.gravar(self.estado, self.serie.get(), self.regras, self.video)
            else:
                arquivos.gravar_short(self.pasta, self.n, self.estado, self.regras)
            self.lbl_status.configure(text="Salvo.")
        except Exception as e:
            registrar("editor: não consegui salvar", e)
            self.lbl_status.configure(text=f"Não consegui salvar ({e}). Feche o arquivo em outro programa.")

    def _confirma_protegido(self, a: float, b: float) -> bool | None:
        """True = cortar mesmo assim (forcar); None = desistiu; False = nao toca protegido."""
        if not self.estado.toca_protegido(a, b):
            return False
        ok = messagebox.askyesno("Trecho protegido", "Esse pedaço tem a INTRODUÇÃO do episódio (ou um momento que o "
                                 "Claude mandou manter).\n\nCortar mesmo assim?", parent=self.jan)  # fmt: skip
        return True if ok else None

    @quando_pronto
    def cortar_marcado(self):
        e = self.estado
        if e.marca_in is None or e.marca_out is None:
            self.lbl_status.configure(text="Marque o início com I e o fim com O antes de cortar (X).")
            return
        forcar = self._confirma_protegido(min(e.marca_in, e.marca_out), max(e.marca_in, e.marca_out))
        if forcar is None:
            return
        e.cortar_marcado(forcar)
        self._mudou()

    @quando_pronto
    def definir(self, acao: str, vel: float | None = None):
        k = self.estado.selecionado
        if k is None:
            self.lbl_status.configure(text="Selecione um trecho na timeline ou na lista.")
            return
        x = self.estado.trechos[k]
        forcar = False
        if acao in ("cortar", "acelerar"):
            forcar = self._confirma_protegido(x["inicio"], x["fim"])
            if forcar is None:
                return
        self.estado.definir_acao(k, acao, vel, forcar)
        self._mudou()

    @quando_pronto
    def aceitar(self):
        k = self.estado.selecionado if self.estado else None
        if k is None:
            return
        self.estado.aceitar(k)
        self._mudou()
        self.ir_sugestao(False)

    @quando_pronto
    def recusar(self):
        k = self.estado.selecionado if self.estado else None
        if k is None:
            return
        self.estado.recusar(k)
        self._mudou()
        self.ir_sugestao(False)

    @quando_pronto
    def aceitar_tipo(self):
        motivo = self._filtro_atual()
        if motivo == "todos":
            if not messagebox.askyesno("Aceitar todas", "Aceitar TODAS as sugestões que você ainda não revisou?",
                                       parent=self.jan):  # fmt: skip
                return
            motivo = None
        n = self.estado.aceitar_tipo(motivo)
        if motivo == "papo_fora":
            n += self.estado.aceitar_tipo("duvida")
        self.lbl_status.configure(text=f"{n} sugestão(ões) aceita(s).")
        self._mudou()

    @quando_pronto
    def ir_sugestao(self, para_tras: bool):
        k = self.estado.proxima_sugestao(self.tempo(), para_tras, None if self._filtro_atual() == "todos"
                                         else self._filtro_atual())  # fmt: skip
        if k is not None:
            self.selecionar(k)
            self.pular(self.estado.trechos[k]["inicio"])
            self.timeline.seguir(self.estado.trechos[k]["inicio"])

    def selecionar(self, k):
        self.estado.selecionado = k
        self.timeline.desenhar()
        if k is not None and self.lista.exists(str(k)):
            self.lista.selection_set(str(k))
            self.lista.see(str(k))

    def itens_do_menu(self, t: float, k) -> list:
        itens = []
        e = self.estado
        if k is not None:
            itens += [("Manter", lambda: self.definir("manter")), ("Cortar", lambda: self.definir("cortar")),
                      ("Acelerar 2x", lambda: self.definir("acelerar", 2.0)),
                      ("Ouvir só este trecho", lambda: self.ouvir_trecho(k))]  # fmt: skip
            if e.trechos[k]["origem"] == "manual":
                itens.append(("Apagar este corte seu", lambda: (e.apagar_trecho(k), self._mudou())))
            itens.append(None)
        if self.tipo == "longo":
            itens += [("⭐ Mandar para Shorts (criar Short daqui)", lambda: self.criar_short(t)),
                      ("📑 Virar capítulo aqui", lambda: self.adicionar_marcador("capitulo", t))]  # fmt: skip
            if e.marca_in is not None and e.marca_out is not None:
                itens.append(("Marcar I–O como introdução do episódio", self.marcar_introducao))
            if e.introducao:
                itens.append(("Tirar a marca de introdução", lambda: (e.definir_introducao(None), self._mudou())))
        itens.append(("📝 Nota aqui", lambda: self.adicionar_marcador("nota", t)))
        return itens

    def menu_trecho(self, evento, t: float, k):
        from interface.menus import abrir_menu, montar_menu
        from interface.reportar_bug import item_do_menu

        menu = montar_menu(self.jan, self.itens_do_menu(t, k))
        menu.add_separator()
        texto, acao = item_do_menu(self.jan)
        menu.add_command(label=texto, command=acao)
        abrir_menu(evento, menu)

    def marcar_introducao(self):
        e = self.estado
        e.definir_introducao(min(e.marca_in, e.marca_out), max(e.marca_in, e.marca_out))
        e.marca_in = e.marca_out = None
        self._mudou()

    @quando_pronto
    def adicionar_marcador(self, tipo: str | None = None, t: float | None = None):
        t = self.tempo() if t is None else t
        if tipo is None:
            menu = tk.Menu(self.jan, tearoff=0)
            for tp, nome in (("short", "⭐ Short"), ("capitulo", "📑 Capítulo"), ("nota", "📝 Nota")):
                if tp == "short" and self.tipo != "longo":
                    continue
                menu.add_command(label=nome, command=lambda tp=tp: self.adicionar_marcador(tp, t))
            x, y = self.jan.winfo_pointerxy()
            menu.tk_popup(x, y)
            return
        texto = ""
        if tipo in ("capitulo", "nota"):
            texto = simpledialog.askstring("Marcador", "Título do capítulo:" if tipo == "capitulo" else "Nota:",
                                           parent=self.jan) or ""  # fmt: skip
        self.estado.adicionar_marcador(t, tipo, texto)
        self._mudou()
        if tipo == "short":
            self.lbl_status.configure(text="Marcador ⭐ adicionado. Botão direito nele → \"Mandar para Shorts\".")

    @quando_pronto
    def criar_short(self, t: float):
        n = arquivos.criar_short_daqui(self.pasta, t, self.duracao, "", self.estado.palavras)
        if not any(m["tipo"] == "short" and abs(m["tempo"] - t) < 1 for m in self.estado.marcadores):
            self.estado.adicionar_marcador(t, "short", f"Short {n}")
        self._mudou()
        self.studio.notificar(f"Short {n} criado no projeto. Ele aparece no estúdio de Shorts para ajustar e gerar.",
                              "ok", 6)  # fmt: skip
        try:
            self.studio.atualizar()
        except Exception:
            pass

    # ================================================================ lista lateral
    def _filtro_atual(self) -> str:
        texto = self.combo_filtro.get()
        return next((k for k, t in NOMES_FILTRO if t == texto), "todos")

    def _preencher_lista(self):
        filtro = self._filtro_atual()
        self.lista.delete(*self.lista.get_children())
        for k, t in enumerate(self.estado.trechos):
            if filtro != "todos" and t["motivo"] != filtro and not (filtro == "papo_fora" and t["motivo"] == "duvida"):
                continue
            if t["origem"] == "manual":
                situacao = {"cortar": "seu corte", "acelerar": "seu (acelera)", "manter": "você manteve"}[t["acao"]]
            elif not t["revisado"]:
                situacao = {"cortar": "sai (sugestão)", "acelerar": "acelera (sug.)", "manter": "só sugestão"}[t["acao"]]
            else:
                situacao = {"cortar": "aceita", "acelerar": "acelera", "manter": "recusada"}[t["acao"]]
            self.lista.insert("", "end", iid=str(k), values=(
                tempo_txt(t["inicio"]), f"{t['fim'] - t['inicio']:.1f} s", tr.NOMES_MOTIVO.get(t["motivo"], t["motivo"]),
                t["confianca"], situacao))  # fmt: skip
        if self.estado.selecionado is not None and self.lista.exists(str(self.estado.selecionado)):
            self.lista.selection_set(str(self.estado.selecionado))

    def _clicou_lista(self, _evento=None):
        sel = self.lista.selection()
        if not sel:
            return
        k = int(sel[0])
        if k == self.estado.selecionado:
            return
        self.estado.selecionado = k
        t = self.estado.trechos[k]["inicio"]
        self.pular(t)
        self.timeline.seguir(t)
        self.timeline.desenhar()

    def atualizar_tudo(self):
        if not self.estado:
            return
        p = self.regras
        self.lbl_predef.configure(text=f"Predefinição: {p['nome']} (versão {p['versao']})")
        texto = self.estado.texto_relatorio()
        dica = self.estado.dica_de_regra()
        self.lbl_relatorio.configure(text=texto + (f"   ·   💡 {dica}" if dica else ""))
        self._preencher_lista()
        self.timeline.desenhar()
        self._mostrar_tempo(self.tempo())

    @quando_pronto
    def _ver_tudo(self):
        self.timeline.ajustar_tudo()
        self.timeline.desenhar()

    # ================================================================ analise
    @quando_pronto
    def analisar(self):
        if self.tipo == "short":
            self.reanalisar()
            return
        if self._processo_cancelar is not None:
            return
        from autoedit.classificar_cenas import SEGUNDOS_POR_MOSAICO
        from nucleo import claude_local

        dur = self.duracao
        estimativa = ("O Studio vai criar a versão leve do vídeo, medir o som e a imagem e"
                      + (" pedir ao Claude para olhar as cenas e ler a conversa" if claude_local.disponivel() else
                         " (sem o Claude Code neste PC: sem olhar as cenas nem ler a conversa)")
                      + f".\n\nLive de {tempo_txt(dur)}: leva uns {max(1, round(dur / 60 / 6))} a "
                      f"{max(2, round(dur / 60 / 2))} min (sem placa NVIDIA, mais perto do maior), mais até "
                      f"~{max(1, round(dur / 160 * SEGUNDOS_POR_MOSAICO / 60))} min do Claude.\nA janela não trava; "
                      "dá para cancelar.\n\nComeçar?")  # fmt: skip
        if not messagebox.askyesno("Analisar a live", estimativa, parent=self.jan):
            return
        if self.estado and self.estado.mudou_desde_salvar:
            self.salvar()
        cancelar = threading.Event()
        self._processo_cancelar = cancelar
        self.barra.pack(side="left", padx=6)
        self.btn_cancelar.pack(side="left")
        self.btn_analisar.state(["disabled"])
        progresso = {"texto": "Começando...", "pct": 0.0, "avisos": []}

        def ao_ler(linha: str):
            import re

            m = re.match(r"\[(\d+)/(\d+)\]\s+(.*?)\s+([\d.]+)%", linha)
            if m:
                k, n, nome, pct = int(m[1]), int(m[2]), m[3], float(m[4])
                progresso["texto"] = f"Etapa {k} de {n}: {nome}"
                progresso["pct"] = ((k - 1) + pct / 100) / n * 100
            elif "[AVISO]" in linha or "Claude" in linha:
                progresso["avisos"].append(linha.replace("[AVISO]", "").strip())

        def trabalho():
            from shorts.lote import rodar_processo

            return rodar_processo(["autoedit.analisar", str(self.pasta)], cancelar, ao_ler)

        def mostrar():
            if self._processo_cancelar is cancelar and self._viva():
                self.lbl_status.configure(text=progresso["texto"])
                self.barra.configure(value=progresso["pct"])
                self.jan.after(300, mostrar)

        mostrar()
        em_segundo_plano(self.studio.raiz, trabalho, lambda r: self._analise_terminou(r, progresso))

    def _analise_terminou(self, r, progresso):
        self._processo_cancelar = None
        if not self._viva():
            return
        self.barra.pack_forget()
        self.btn_cancelar.pack_forget()
        self.btn_analisar.state(["!disabled"])
        if isinstance(r, Exception):
            self.lbl_status.configure(text="Análise cancelada." if type(r).__name__ == "Cancelado" else
                                      f"A análise deu erro: {r}")  # fmt: skip
            return
        codigo, ultimas = r
        if codigo != 0:
            erro = next((linha for linha in reversed(ultimas) if "[ERRO]" in linha or "Error" in linha), "")
            registrar("editor: análise falhou\n" + "\n".join(ultimas[-15:]))
            messagebox.showerror("Analisar a live", "A análise não terminou.\n\n" + (erro or "Veja o studio.log.")
                                 + "\n\nTente de novo: as etapas prontas não são refeitas.", parent=self.jan)  # fmt: skip
            return
        dados = arquivos.ler_edicao_longo(self.pasta)
        self.estado.trechos = tr.normalizar(dados.get("trechos"), self.duracao)
        if dados.get("introducao") and not self.estado.introducao:
            self.estado.introducao = dados["introducao"]
        self.estado._mudou()
        self.studio.notificar("Análise pronta: revise as sugestões (N = próxima, Enter = aceitar).", "ok", 6)
        em_segundo_plano(self.studio.raiz, self._carregar, self._recarregar_midia)

    def _recarregar_midia(self, r):
        """Depois da analise: proxy, onda e miniaturas novas (sem perder a edicao)."""
        if not self._viva() or isinstance(r, Exception):
            return
        self.dados_abertos = r
        sinais = r.get("sinais") or {}
        som = sinais.get("som")
        if som:
            from autoedit.sinais_audio import onda

            self.timeline.onda = onda(som)
        self.estado.trocas = sorted((sinais.get("imagem") or {}).get("trocas") or [])
        if r.get("mini"):
            self._folhas.clear()
            self._mini_cache.clear()
            self.timeline.mini = (r["mini"], self._miniatura)
        if r.get("proxy") and self.player:
            t = self.tempo()
            self.player.carregar(r["proxy"], t)
        self.btn_analisar.configure(text="Analisar de novo")
        avisos = [a for a in (ler_json(self.pasta / "analise" / "analise.json", {}) or {}).get("avisos", [])]
        self.lbl_aviso.configure(text="\n".join("• " + a for a in
                                               ["Estilo TV: pausas naturais durante o jogo ficam. Isso segue as "
                                                "diretrizes do canal."] + avisos))  # fmt: skip
        self.atualizar_tudo()

    def cancelar_analise(self):
        if self._processo_cancelar is not None:
            self._processo_cancelar.set()
            self.lbl_status.configure(text="Cancelando...")

    @quando_pronto
    def reanalisar(self):
        """Refaz as sugestoes com a predefinicao atual (instantaneo: usa os sinais guardados)."""
        from autoedit import analisar

        if self.tipo == "longo" and not (self.pasta / "analise" / "som.json").exists():
            self.analisar()
            return
        self.regras = predefinicoes.da(self.tipo)
        self.lbl_status.configure(text="Refazendo as sugestões...")

        def trabalho():
            return analisar.sugerir(self.pasta, self.tipo, self.regras, self.estado.inicio, self.estado.fim,
                                    self.duracao)  # fmt: skip

        def pronto(r):
            if not self._viva():
                return
            if isinstance(r, Exception):
                registrar("editor: refazer sugestões", r)
                self.lbl_status.configure(text=f"Não deu para refazer as sugestões: {r}")
                return
            self.estado.reanalisar(r)
            self.lbl_status.configure(text=f"{len(r)} sugestão(ões) com a predefinição {self.regras['nome']}. "
                                           "Os seus cortes ficaram.")  # fmt: skip
            self._mudou()

        em_segundo_plano(self.studio.raiz, trabalho, pronto)

    # ================================================================ exportar
    @quando_pronto
    def exportar(self):
        if self.estado and self.estado.mudou_desde_salvar:
            self.salvar()
        if self.tipo == "short":
            rodar_script("shorts.gerar_shorts", self.pasta, "--so", self.n)
            self.studio.notificar(f"Renderizando o Short {self.n} com os cortes de dentro dele.", "ok")
            return
        from videos_longos import outro as outro_mod

        arq, info, texto, _ = outro_mod.situacao(True)
        if not arq and not messagebox.askyesno("Gerar o episódio", f"{texto}\n\nGerar sem o outro?", parent=self.jan):
            return
        if self.serie.get() and not self.estado.introducao and not messagebox.askyesno(
                "Gerar o episódio", "É episódio de série e não tem introdução marcada.\n\nGerar assim mesmo?",
                parent=self.jan):  # fmt: skip
            return
        rodar_script("videos_longos.editar_episodio", self.pasta)
        self.studio.notificar("Gerando o episódio a partir do vídeo ORIGINAL (janela preta mostra o andamento).", "ok")

    @quando_pronto
    def exportar_outro_editor(self, tipo: str | None = None):
        """XML para Premiere/DaVinci ou um arquivo por trecho (CapCut). Nao gera projeto do CapCut."""
        if tipo is None:
            from interface.menus import montar_menu

            menu = montar_menu(self.jan, [("XML para Premiere / DaVinci Resolve", lambda: self.exportar_outro_editor("--xml")),
                                          ("Um arquivo por trecho (para arrastar no CapCut)",
                                           lambda: self.exportar_outro_editor("--trechos"))])  # fmt: skip
            b = self.btn_outro_editor
            menu.tk_popup(b.winfo_rootx(), b.winfo_rooty() + b.winfo_height())
            return
        if self.estado.mudou_desde_salvar:
            self.salvar()
        rodar_script("videos_longos.exportar_outro_editor", self.pasta, tipo)
        self.studio.notificar("Exportando para outro editor: fica em episodio\\outro_editor.", "ok")

    # ================================================================ atalhos
    def _ligar_atalhos(self, alvo=None):
        """Atalhos de teclado. Na janela propria: valem na janela toda. Encaixado na janela de legendas: so com o
        foco no editor (clique na timeline ou no video), para nao brigar com os atalhos da lista de legendas."""
        if self.embutido and alvo is None:
            return  # liga depois, na timeline (_carregou)
        j = alvo or self.jan

        def atalho(funcao):
            def rodar(evento):
                if isinstance(evento.widget, (tk.Entry, ttk.Entry, ttk.Combobox, tk.Text)) or not self.estado:
                    return None
                funcao(evento)
                return "break"

            return rodar

        def passo(seg):
            return lambda e: self.pular(self.estado.limitar(self.tempo() + seg))

        def troca(para_frente):
            def ir(e):
                t = self.tempo()
                lista = [x for x in self.estado.trocas if (x > t + 0.1 if para_frente else x < t - 0.1)]
                if lista:
                    self.pular(lista[0] if para_frente else lista[-1])

            return ir

        def marca(lado):
            def marcar(e):
                setattr(self.estado, "marca_in" if lado == "I" else "marca_out", round(self.tempo(), 3))
                self.timeline.desenhar()

            return marcar

        mapa = {
            "<space>": lambda e: self.alternar(), "<Key-k>": lambda e: self.alternar(),
            "<Key-l>": lambda e: self.acelerar(True), "<Key-j>": lambda e: self.acelerar(False),
            "<Key-i>": marca("I"), "<Key-o>": marca("O"), "<Key-x>": lambda e: self.cortar_marcado(),
            "<Key-c>": lambda e: (self.estado.dividir(self.tempo()) and self._mudou()),
            "<Delete>": lambda e: self.definir("cortar"), "<Key-r>": lambda e: self.definir("manter"),
            "<Key-n>": lambda e: self.ir_sugestao(False), "<Key-b>": lambda e: self.ir_sugestao(True),
            "<Return>": lambda e: self.aceitar(), "<BackSpace>": lambda e: self.recusar(),
            "<Left>": lambda e: self.player and self.player.quadro_a_quadro(False),
            "<Right>": lambda e: self.player and self.player.quadro_a_quadro(True),
            "<Shift-Left>": passo(-5), "<Shift-Right>": passo(5),
            "<Control-Left>": troca(False), "<Control-Right>": troca(True),
            "<Key-m>": lambda e: self.adicionar_marcador(), "<Control-z>": lambda e: self.desfazer(),
            "<Control-Z>": lambda e: self.refazer(), "<Control-Shift-Z>": lambda e: self.refazer(),
            "<Control-y>": lambda e: self.refazer(), "<Control-s>": lambda e: self.salvar(),
            "<question>": lambda e: self.mostrar_atalhos(),
        }  # fmt: skip
        for tecla, funcao in mapa.items():
            j.bind(tecla, atalho(funcao))

    @quando_pronto
    def desfazer(self):
        if self.estado.desfazer():
            self._mudou()
            self.lbl_status.configure(text="Desfeito.")

    @quando_pronto
    def refazer(self):
        if self.estado.refazer():
            self._mudou()
            self.lbl_status.configure(text="Refeito.")

    def mostrar_atalhos(self):
        jan = tk.Toplevel(self.jan)
        jan.title("Atalhos do editor")
        jan.configure(bg=tema.FUNDO)
        jan.transient(self.jan)
        for k, (tecla, o_que) in enumerate(ATALHOS):
            tk.Label(jan, text=tecla, bg=tema.FUNDO, fg=tema.LARANJA, font=tema.F_TEXTO_NEGRITO, anchor="w").grid(
                row=k, column=0, sticky="w", padx=(14, 10), pady=1)
            tk.Label(jan, text=o_que, bg=tema.FUNDO, fg=tema.TEXTO, font=tema.F_TEXTO, anchor="w").grid(
                row=k, column=1, sticky="w", padx=(0, 14), pady=1)
        ttk.Button(jan, text="Fechar", style="Extra.TButton", command=jan.destroy).grid(
            row=len(ATALHOS), column=0, columnspan=2, pady=10)
        jan.bind("<Escape>", lambda e: jan.destroy())

    def _dica_inicial(self):
        """Dica discreta nas primeiras 5 vezes que o editor abre."""
        from nucleo.comum import ler_ajustes, salvar_ajustes

        try:
            vezes = int(ler_ajustes().get(CHAVE_DICA, 0) or 0)
        except (TypeError, ValueError):
            vezes = 0
        if vezes < 5:
            self.lbl_dica.configure(text="Dica: Espaço toca · L acelera até 4x · N vai para a próxima sugestão, Enter "
                                         "aceita, Backspace recusa · I e O marcam, X corta · Ctrl+Z desfaz · ? mostra "
                                         "todos os atalhos")  # fmt: skip
            salvar_ajustes({CHAVE_DICA: vezes + 1})

    # ================================================================ fechar
    def fechar(self):
        if self._fechada:
            return
        if self._processo_cancelar is not None:
            if not messagebox.askyesno("Editor", "A análise ainda está rodando. Cancelar e fechar?", parent=self.jan):
                return
            self._processo_cancelar.set()
        if self._salvar_id:
            self.jan.after_cancel(self._salvar_id)
        if self.estado and self.estado.mudou_desde_salvar:
            self.salvar()
        self._fechada = True
        import os

        alvo = self.raiz  # encaixado: some so o quadro do editor (a janela de legendas continua)
        if self.embutido and getattr(self, "baixo", None) is not None and self.container_baixo is not None:
            self.baixo.destroy()
        if os.name == "nt" or not isinstance(self.player, player_mod.PlayerMpv):
            if self.player:
                self.player.fechar()  # Windows: o mpv sai antes da janela sumir
            alvo.destroy()
        else:  # Linux (X11): fechar o mpv com a janela ainda la da erro de "janela invalida" e derruba o app
            player = self.player
            alvo.destroy()
            self.studio.raiz.after(200, player.fechar)
        if self.embutido:
            return
        try:
            self.studio.atualizar()
        except Exception:
            pass

