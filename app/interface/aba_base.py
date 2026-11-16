# Base das telas de projetos (Shorts e Videos longos): os cartoes dos projetos (miniatura, nome, quantos Shorts
# e status) a esquerda, e a direita o projeto selecionado com UM botao laranja (o proximo passo) e as outras
# acoes discretas. Cada tela (Shorts, Videos longos) so diz quais colunas, passos e acoes tem.
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from interface import tema
from interface.menus import ligar_botao_direito, montar_menu
from interface.utilidades import abrir
from nucleo.miniatura import gerar_miniatura, miniatura


class AbaProjetos(tk.Frame):
    TITULO = ""
    TELA = "shorts"  # codigo da tela (para a janela Excluir saber o que oferecer)
    SUBTITULO = ""
    COLUNAS = []  # [(id, titulo, largura)] - cada tela define as suas
    PASSOS = {}  # codigo do proximo passo -> (texto do botao laranja, nome do metodo)
    TEXTO_VAZIO = "Nenhum vídeo ainda.\nArraste um vídeo para esta janela ou clique em Adicionar vídeo."

    def __init__(self, studio, pai):
        super().__init__(pai, bg=tema.FUNDO)
        self.studio = studio
        self.projetos = {}
        self.imagens = {}  # miniaturas carregadas (o tkinter precisa guardar a referencia)
        self.gerando = set()  # miniaturas sendo feitas agora
        self._montar_cabecalho()
        corpo = tema.quadro(self)
        corpo.pack(fill="both", expand=True, padx=tema.ESPACO * 2, pady=(0, tema.ESPACO))
        self.direita = tema.quadro(corpo)
        self.direita.pack(side="right", fill="y", padx=(tema.ESPACO, 0))
        esquerda = tema.quadro(corpo)
        esquerda.pack(side="left", fill="both", expand=True)
        self._montar_lista(esquerda)
        self._montar_detalhe()
        self.montar_botoes()

    # ---------------------------------------------------------- montagem
    def _montar_cabecalho(self):
        topo = tema.quadro(self)
        topo.pack(fill="x", padx=tema.ESPACO * 2, pady=(tema.ESPACO * 1.5, tema.ESPACO))
        tema.rotulo(topo, self.TITULO, "titulo").pack(side="left")
        tema.rotulo(topo, "   " + self.SUBTITULO, "secundario").pack(side="left", pady=(8, 0))

    def _montar_lista(self, pai):
        quadro = tema.quadro(pai)
        quadro.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(quadro, columns=[c[0] for c in self.COLUNAS], show="tree headings",
                                 selectmode="extended", style="Cartoes.Treeview")  # fmt: skip
        self.tree.heading("#0", text="Vídeo", anchor="w")
        self.tree.column("#0", width=300, minwidth=220, anchor="w", stretch=True)
        for col, titulo, largura in self.COLUNAS:
            self.tree.heading(col, text=titulo)
            self.tree.column(col, width=largura, anchor="w" if col == "status" else "center", stretch=False)
        barra = ttk.Scrollbar(quadro, command=self.tree.yview)
        self.tree.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.atualizar_passo())
        self.tree.bind("<Double-1>", lambda e: self.acao_principal())
        self.tree.bind("<Delete>", lambda e: self.excluir())
        self.tree.bind("<Return>", lambda e: self.acao_principal())
        ligar_botao_direito(self.tree, self.menu_do_projeto)  # Ctrl/Shift + clique seleciona varios
        self.lbl_vazio = tk.Label(quadro, text=self.TEXTO_VAZIO, bg=tema.PAINEL, fg=tema.TEXTO_2,
                                  font=tema.F_GRANDE, justify="center")  # fmt: skip

    def _montar_detalhe(self):
        """O projeto selecionado: miniatura, nome, proximo passo e o botao laranja."""
        self.cartao = tema.cartao(self.direita, padx=14, pady=14)
        self.cartao.pack(fill="x")
        self.lbl_imagem = tk.Label(self.cartao, bg=tema.PAINEL)
        self.lbl_imagem.pack(anchor="w")
        self.lbl_nome = tema.rotulo(self.cartao, "", "subtitulo", fundo=tema.PAINEL, wraplength=290)
        self.lbl_nome.pack(fill="x", pady=(8, 2))
        self.lbl_passo = tema.rotulo(self.cartao, "", "secundario", fundo=tema.PAINEL, wraplength=290)
        self.lbl_passo.pack(fill="x")
        self.btn_principal = ttk.Button(self.cartao, text="", style="Passo.TButton", command=self.acao_principal)
        self.btn_principal.pack(fill="x", pady=(12, 0))

    def secao(self, texto):
        ttk.Label(self.direita, text=texto, style="Sec.TLabel").pack(anchor="w", pady=(12, 3))

    def botao(self, texto, comando, estilo="Extra.TButton"):
        b = ttk.Button(self.direita, text=texto, command=comando, style=estilo, width=32)
        b.pack(fill="x", pady=1)
        return b

    # ---------------------------------------------------------- o que cada aba define
    def montar_botoes(self):
        raise NotImplementedError

    def valores(self, info: dict) -> tuple:
        """O que aparece em cada coluna para um projeto."""
        raise NotImplementedError

    def texto_passo(self, info: dict) -> str:
        raise NotImplementedError

    def codigo_passo(self, info: dict) -> str:
        return info.get("proximo", "")

    # ---------------------------------------------------------- lista
    def preencher(self, projetos: dict):
        selecionados = [n for n in self.tree.selection() if n in self.projetos]
        self.projetos = projetos
        self.tree.delete(*self.tree.get_children())
        for n, info in projetos.items():
            self.tree.insert("", "end", iid=n, text="   " + n, values=self.valores(info), image=self.imagem(info))
        manter = [n for n in selecionados if n in projetos]
        if manter:
            self.tree.selection_set(manter)
        elif projetos:
            self.tree.selection_set(next(iter(projetos)))
        if projetos:
            self.lbl_vazio.place_forget()
        else:
            self.lbl_vazio.place(relx=0.5, rely=0.45, anchor="center")
        self.atualizar_passo()

    def imagem(self, info: dict):
        """Miniatura do projeto. Se ainda nao existe, cria em segundo plano e mostra na proxima atualizacao."""
        arq = miniatura(info["pasta"])
        if arq is None:
            self._gerar_miniatura(info["pasta"])
            return ""
        chave = (str(arq), arq.stat().st_mtime)
        if chave not in self.imagens:
            try:
                self.imagens[chave] = tk.PhotoImage(file=str(arq))
            except tk.TclError:
                return ""
        return self.imagens[chave]

    def _gerar_miniatura(self, pasta):
        if str(pasta) in self.gerando or getattr(self.studio, "sem_miniaturas", False):
            return
        self.gerando.add(str(pasta))

        def trabalho():
            if gerar_miniatura(pasta):
                self.studio.pedir_atualizacao()

        threading.Thread(target=trabalho, daemon=True).start()

    def selecionado(self):
        try:
            sel = self.tree.selection()
        except tk.TclError:
            return None
        return self.projetos.get(sel[0]) if sel else None

    def selecionados(self) -> list:
        try:
            return [self.projetos[n] for n in self.tree.selection() if n in self.projetos]
        except tk.TclError:
            return []

    def atualizar_passo(self):
        info = self.selecionado()
        if not info:
            self.lbl_nome.config(text="Nenhum vídeo selecionado")
            self.lbl_passo.config(text=self.TEXTO_VAZIO.replace("\n", " "))
            self.lbl_imagem.config(image="")
            self.btn_principal.config(text="Adicionar vídeo", command=self.studio.adicionar_video)
            return
        self.lbl_nome.config(text=info["nome"])
        self.lbl_passo.config(text=self.texto_passo(info))
        self.lbl_imagem.config(image=self.imagem(info))
        texto, _ = self.PASSOS.get(self.codigo_passo(info), ("Abrir pasta", "abrir_pasta"))
        self.btn_principal.config(text=texto, command=self.acao_principal)

    def acao_principal(self):
        """O botao laranja: faz o proximo passo do projeto selecionado."""
        info = self.selecionado()
        if not info:
            self.studio.adicionar_video()
            return
        _, metodo = self.PASSOS.get(self.codigo_passo(info), ("", "abrir_pasta"))
        getattr(self, metodo)()

    def exigir(self):
        info = self.selecionado()
        if not info:
            messagebox.showinfo("FamosoZora Studio", "Selecione um vídeo na lista primeiro.")
        return info

    # ---------------------------------------------------------- acoes que as duas abas tem
    def abrir_pasta(self):
        info = self.exigir()
        if info:
            abrir(self.pasta_para_abrir(info))

    def pasta_para_abrir(self, info: dict):
        return info["pasta"]

    # ---------------------------------------------------------- botao direito e excluir
    def menu_do_projeto(self, evento):
        linha = self.tree.identify_row(evento.y)
        if not linha:
            return montar_menu(self, [("+  Adicionar vídeo...", self.studio.adicionar_video)])
        if linha not in self.tree.selection():
            self.tree.selection_set(linha)
        self.tree.update_idletasks()
        sel = self.selecionados()
        if len(sel) > 1:
            return montar_menu(self, [(f"🗑  Excluir {len(sel)} projetos...", self.excluir, "Delete")])
        return montar_menu(self, self.itens_do_menu(sel[0]) + [None, ("🗑  Excluir...", self.excluir, "Delete")])

    def itens_do_menu(self, info: dict) -> list:
        """Itens do botao direito de um projeto (cada tela define os seus)."""
        return [("📁  Abrir pasta", self.abrir_pasta)]

    def excluir(self):
        """Excluir o(s) projeto(s) selecionado(s): pergunta o que excluir e manda para a Lixeira."""
        from interface.janela_excluir import JanelaExcluir

        sel = self.selecionados()
        if not sel:
            messagebox.showinfo("Excluir", "Selecione um vídeo na lista primeiro.")
            return None
        return JanelaExcluir(self.studio, sel, self.TELA)
