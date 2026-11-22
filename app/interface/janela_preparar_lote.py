# Janela "Preparar lote": aparece antes de gerar os Shorts de varios videos de uma vez. Tudo o que o lote
# precisaria perguntar e resolvido AQUI, no comeco: a area da camera (a padrao, para todos), o que fazer com
# os videos que ja tem Shorts (Pular ou Gerar de novo) e a ordem (arrastar ou Subir/Descer).
# Depois do clique em "Comecar", o lote nao pergunta mais nada.
import tkinter as tk
from tkinter import messagebox, ttk

from interface import tema
from interface.telas import nova_janela
from nucleo.comum import carregar_config
from shorts import lote as motor

PULAR, DE_NOVO = "Pular", "Gerar de novo"


class JanelaPrepararLote:
    def __init__(self, studio, projetos: list):
        self.studio = studio
        self.projetos = {i["nome"]: i for i in projetos}
        self.escolha = {i["nome"]: PULAR for i in projetos if i.get("n_shorts")}  # so quem ja tem Shorts
        self.arrastando = None

        self.jan = nova_janela(studio.raiz)
        self.jan.title("Preparar lote")
        self.jan.configure(bg=tema.FUNDO)
        self.jan.minsize(860, 420)
        self.jan.transient(studio.raiz)
        q = tk.Frame(self.jan, bg=tema.FUNDO, padx=22, pady=16)
        q.pack(fill="both", expand=True)
        tema.rotulo(q, f"Gerar os Shorts de {len(projetos)} vídeos", "subtitulo").pack(fill="x")
        tema.rotulo(q, "Confira tudo aqui. Depois de clicar em Começar, o lote não pergunta mais nada e você "
                    "pode continuar usando o Studio.", "secundario", wraplength=800).pack(fill="x", pady=(2, 8))  # fmt: skip

        self.avisos = tk.Frame(q, bg=tema.FUNDO)
        self.avisos.pack(fill="x")

        # ---- lista dos videos (na ordem em que vao rodar)
        tema.rotulo(q, "ORDEM  (arraste para mudar, ou use Subir/Descer)", "secao").pack(fill="x", pady=(8, 3))
        meio = tk.Frame(q, bg=tema.FUNDO)
        meio.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(meio, columns=("n", "plano", "shorts"), show="tree headings", height=8,
                                 selectmode="browse")  # fmt: skip
        self.tree.heading("#0", text="Vídeo", anchor="w")
        self.tree.column("#0", width=250, anchor="w")
        self.tree.heading("n", text="#")
        self.tree.column("n", width=34, anchor="center", stretch=False)
        self.tree.heading("plano", text="O que vai ser feito", anchor="w")
        self.tree.column("plano", width=330, anchor="w")
        self.tree.heading("shorts", text="Já tem Shorts?")
        self.tree.column("shorts", width=150, anchor="center", stretch=False)
        barra = ttk.Scrollbar(meio, command=self.tree.yview)
        self.tree.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        for i in projetos:
            self.tree.insert("", "end", iid=i["nome"], text="  " + i["nome"],
                             values=("", motor.plano_do_video(i["pasta"]), ""))  # fmt: skip
        self.tree.bind("<ButtonPress-1>", self.apertar)
        self.tree.bind("<B1-Motion>", self.arrastar)
        self.tree.bind("<ButtonRelease-1>", self.soltar)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.atualizar_botoes())

        acoes = tk.Frame(q, bg=tema.FUNDO)
        acoes.pack(fill="x", pady=(6, 0))
        ttk.Button(acoes, text="▲ Subir", style="Extra.TButton", command=lambda: self.mover(-1)).pack(side="left")
        ttk.Button(acoes, text="▼ Descer", style="Extra.TButton", command=lambda: self.mover(1)).pack(
            side="left", padx=(4, 16)
        )
        self.btn_pular = ttk.Button(acoes, text="Pular este", style="Extra.TButton",
                                    command=lambda: self.escolher(PULAR))  # fmt: skip
        self.btn_pular.pack(side="left")
        self.btn_de_novo = ttk.Button(acoes, text="Gerar este de novo", style="Extra.TButton",
                                      command=lambda: self.escolher(DE_NOVO))  # fmt: skip
        self.btn_de_novo.pack(side="left", padx=(4, 0))
        self.aplicar_todos = tk.BooleanVar(value=False)
        self.chk_todos = ttk.Checkbutton(acoes, text="aplicar a todos", variable=self.aplicar_todos,
                                         command=self.atualizar_botoes)  # fmt: skip
        self.chk_todos.pack(side="left", padx=(8, 0))
        tema.rotulo(q, '"Gerar de novo" manda os Shorts antigos para a Lixeira (dá para restaurar).', "pequeno").pack(
            fill="x", pady=(4, 0)
        )

        # ---- botoes de baixo
        baixo = tk.Frame(q, bg=tema.FUNDO)
        baixo.pack(fill="x", pady=(14, 0))
        self.lbl_resumo = tema.rotulo(baixo, "", "secundario")
        self.lbl_resumo.pack(side="left")
        self.btn_comecar = ttk.Button(baixo, text="Começar", style="Passo.TButton", command=self.comecar)
        self.btn_comecar.pack(side="right")
        ttk.Button(baixo, text="Cancelar", style="Extra.TButton", command=self.fechar).pack(side="right", padx=(0, 8))

        self.claude_ok = self._achar_claude()
        self.montar_avisos()
        self.atualizar_tudo()
        if self.tree.get_children():
            self.tree.selection_set(self.tree.get_children()[0])
        self.jan.protocol("WM_DELETE_WINDOW", self.fechar)
        self.jan.grab_set()

    def fechar(self):
        """Fecha a janela e solta a variavel do tkinter aqui mesmo (se ela fosse recolhida depois, pela linha
        do lote, o tkinter reclamaria e a tela podia travar por alguns segundos)."""
        self.jan.destroy()
        self.aplicar_todos = None

    # ---------------------------------------------------------- avisos do comeco
    def _achar_claude(self) -> bool:
        if not motor.precisa_do_claude(list(self.projetos.values())):
            return True  # todos ja tem cortes: o Claude nao vai ser chamado
        from nucleo import claude_local

        return claude_local.disponivel()

    def montar_avisos(self):
        for w in self.avisos.winfo_children():
            w.destroy()
        from nucleo.video import tem_placa_nvidia

        if not self.claude_ok:
            self._aviso("✕  Não achei o Claude Code neste computador. Ele escolhe os cortes, então o lote não pode "
                        "começar. Instale o Claude Code, abra o terminal, digite claude, entre na sua conta e "
                        "abra esta janela de novo.", tema.VERMELHO)  # fmt: skip
        cfg = carregar_config()
        if cfg.get("layout") == "camera":
            if cfg.get("camera_area"):
                self._aviso("✓  Área da câmera: a padrão (a mesma para todos os vídeos).", tema.VERDE,
                            ("Mudar...", self.marcar_camera))  # fmt: skip
            else:
                self._aviso("!  A área da câmera ainda não foi marcada. Marque agora (vale para todos) ou os Shorts "
                            "saem com o fundo desfocado.", tema.AMARELO, ("Marcar agora", self.marcar_camera))  # fmt: skip
        if not tem_placa_nvidia():
            self._aviso("!  Este computador não tem placa NVIDIA: o lote vai demorar mais (transcrever e gerar os "
                        "Shorts usam só o processador).", tema.AMARELO)  # fmt: skip

    def _aviso(self, texto, cor, botao=None):
        linha = tk.Frame(self.avisos, bg=tema.PAINEL, highlightbackground=cor, highlightthickness=1)
        linha.pack(fill="x", pady=2)
        tk.Label(linha, text=texto, bg=tema.PAINEL, fg=cor, font=tema.F_TEXTO, justify="left", anchor="w",
                 wraplength=700, padx=10, pady=6).pack(side="left", fill="x", expand=True)  # fmt: skip
        if botao:
            ttk.Button(linha, text=botao[0], style="Extra.TButton", command=botao[1]).pack(side="right", padx=6)

    def marcar_camera(self):
        """Abre o "Marcar camera" com o primeiro video; quando a area for salva, os avisos se atualizam sozinhos."""
        from interface.marcar_camera import abrir_no_studio
        from nucleo.miniatura import video_do_projeto

        video = next((v for v in (video_do_projeto(i["pasta"]) for i in self.projetos.values()) if v), None)
        abrir_no_studio(self.studio, video)
        antes = carregar_config().get("camera_area")
        self._esperar_camera(antes, 0)

    def _esperar_camera(self, antes, voltas):
        if not self.jan.winfo_exists() or voltas > 600:  # para de olhar depois de ~10 minutos
            return
        if carregar_config().get("camera_area") != antes:
            self.montar_avisos()
            self.studio.notificar("Área da câmera salva. Ela vale para todos os vídeos do lote.", "ok")
            return
        self.jan.after(1000, lambda: self._esperar_camera(antes, voltas + 1))

    # ---------------------------------------------------------- ordem (arrastar e Subir/Descer)
    def apertar(self, evento):
        linha = self.tree.identify_row(evento.y)
        self.arrastando = linha or None
        if linha and self.tree.identify_column(evento.x) == "#3" and linha in self.escolha:
            self.tree.selection_set(linha)  # clique na coluna "Ja tem Shorts?": troca Pular <-> Gerar de novo
            self.escolher(DE_NOVO if self.escolha[linha] == PULAR else PULAR, so_este=True)
            self.arrastando = None
            return "break"
        return None

    def arrastar(self, evento):
        if not self.arrastando:
            return
        alvo = self.tree.identify_row(evento.y)
        if alvo and alvo != self.arrastando:
            self.tree.move(self.arrastando, "", self.tree.index(alvo))
            self.atualizar_tudo()

    def soltar(self, _evento):
        self.arrastando = None

    def mover(self, passo: int):
        sel = self.tree.selection()
        if not sel:
            return
        k = self.tree.index(sel[0]) + passo
        if 0 <= k < len(self.tree.get_children()):
            self.tree.move(sel[0], "", k)
            self.tree.see(sel[0])
            self.atualizar_tudo()

    # ---------------------------------------------------------- Pular / Gerar de novo
    def escolher(self, escolha: str, so_este: bool = False):
        if self.aplicar_todos is not None and self.aplicar_todos.get() and not so_este:
            for nome in self.escolha:
                self.escolha[nome] = escolha
        else:
            for nome in self.tree.selection():
                if nome in self.escolha:
                    self.escolha[nome] = escolha
        self.atualizar_tudo()

    def atualizar_botoes(self):
        sel = self.tree.selection()
        tem = bool(self.escolha) and (self.aplicar_todos.get() or any(n in self.escolha for n in sel))
        for b in (self.btn_pular, self.btn_de_novo):
            b.config(state="normal" if tem else "disabled")
        self.chk_todos.config(state="normal" if self.escolha else "disabled")

    def ordem(self) -> list:
        return list(self.tree.get_children())

    def atualizar_tudo(self):
        for k, nome in enumerate(self.ordem(), 1):
            i = self.projetos[nome]
            if nome in self.escolha:
                texto = f"{i['n_shorts']} · {'⟳ gerar de novo' if self.escolha[nome] == DE_NOVO else '⏭ pular'}"
            else:
                texto = "não"
            plano = "(pulado)" if self.escolha.get(nome) == PULAR else motor.plano_do_video(i["pasta"])
            self.tree.item(nome, values=(k, plano, texto))
        vao = [n for n in self.ordem() if self.escolha.get(n) != PULAR]
        pulados = len(self.ordem()) - len(vao)
        self.lbl_resumo.config(text=f"{len(vao)} vídeo(s) no lote" + (f", {pulados} pulado(s)" if pulados else ""))
        pode = bool(vao) and self.claude_ok
        self.btn_comecar.config(state="normal" if pode else "disabled")
        self.atualizar_botoes()

    # ---------------------------------------------------------- comecar
    def montar(self) -> dict:
        """O lote do jeito que esta na tela (ordem e escolhas)."""
        refazer = {n: e == DE_NOVO for n, e in self.escolha.items()}
        return motor.montar_lote([self.projetos[n] for n in self.ordem()], refazer)

    def comecar(self):
        if str(self.btn_comecar.cget("state")) == "disabled":
            return None
        cfg = carregar_config()
        if cfg.get("layout") == "camera" and not cfg.get("camera_area"):
            if not messagebox.askyesno("Preparar lote", "A área da câmera não foi marcada.\n\n"
                                       "Gerar os Shorts com o fundo desfocado mesmo assim?", parent=self.jan):  # fmt: skip
                return None
        lote = self.montar()
        self.fechar()
        return self.studio.comecar_lote(lote)
