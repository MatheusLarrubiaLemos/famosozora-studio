# Base das telas de projetos (Shorts e Videos longos): os cartoes dos projetos (miniatura, nome, quantos Shorts
# e status) a esquerda, e a direita o projeto selecionado com UM botao laranja (o proximo passo) e as outras
# acoes discretas. Cada tela (Shorts, Videos longos) so diz quais colunas, passos e acoes tem.
# Da para selecionar varios: caixinha em cada linha, Ctrl + clique, Shift + clique, "Selecionar todos".
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from interface import tema
from interface.menus import ligar_botao_direito, montar_menu
from interface.utilidades import abrir
from nucleo import selecao
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
        self.ancora = None  # ultimo item clicado (para o Shift + clique)
        self._ja_preencheu = False
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
        topo.pack(fill="x", padx=tema.ESPACO * 2, pady=(tema.ESPACO, tema.ESPACO / 2))
        tema.rotulo(topo, self.TITULO, "titulo").pack(side="left")
        tema.rotulo(topo, "   " + self.SUBTITULO, "secundario").pack(side="left", pady=(8, 0))

    def _montar_lista(self, pai):
        barra_sel = tema.quadro(pai)
        barra_sel.pack(fill="x", pady=(0, 4))
        self.lbl_contador = tema.rotulo(barra_sel, selecao.texto_contador(0), "pequeno")
        self.lbl_contador.pack(side="left")
        ttk.Button(barra_sel, text="Limpar seleção", style="Extra.TButton", command=self.limpar_selecao).pack(
            side="right"
        )
        ttk.Button(barra_sel, text="Selecionar todos", style="Extra.TButton", command=self.selecionar_todos).pack(
            side="right", padx=(0, 4)
        )
        quadro = tema.quadro(pai)
        quadro.pack(fill="both", expand=True)
        colunas = [("marcar", "☐", 38)] + list(self.COLUNAS)  # a caixinha de marcar vem antes das outras
        self.tree = ttk.Treeview(quadro, columns=[c[0] for c in colunas], show="tree headings",
                                 selectmode="extended", style="Cartoes.Treeview", height=4)  # fmt: skip
        self.tree.heading("#0", text="Vídeo", anchor="w")
        self.tree.column("#0", width=250, minwidth=200, anchor="w", stretch=True)
        self.tree.heading("marcar", text="☐", command=self.alternar_todos)
        self.tree.column("marcar", width=38, minwidth=38, anchor="center", stretch=False)
        for col, titulo, largura in self.COLUNAS:
            self.tree.heading(col, text=titulo)
            self.tree.column(col, width=largura, anchor="w" if col == "status" else "center", stretch=False)
        barra = ttk.Scrollbar(quadro, command=self.tree.yview)
        self.tree.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.selecao_mudou())
        for evento, ctrl, shift in (("<Button-1>", False, False), ("<Control-Button-1>", True, False),
                                    ("<Shift-Button-1>", False, True), ("<Control-Shift-Button-1>", True, True)):  # fmt: skip
            self.tree.bind(evento, lambda e, c=ctrl, s=shift: self.clique(e, c, s))
        self.tree.bind("<Double-1>", self.duplo_clique)
        self.tree.bind("<Delete>", lambda e: (self.excluir(), "break")[1])  # "break": nao exclui duas vezes
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
        self.lbl_extra = tk.Label(self.cartao, text="", bg=tema.PAINEL, fg=tema.TEXTO_2, font=tema.F_PEQUENA,
                                  anchor="w", justify="left", wraplength=290, cursor="hand2")  # fmt: skip
        self.lbl_extra.pack(fill="x", pady=(4, 0))
        self.lbl_extra.bind("<Button-1>", lambda e: self.clique_extra())
        self.btn_principal = ttk.Button(self.cartao, text="", style="Passo.TButton", command=self.acao_principal)
        self.btn_principal.pack(fill="x", pady=(12, 0))

    def secao(self, texto):
        ttk.Label(self.direita, text=texto, style="Sec.TLabel").pack(anchor="w", pady=(12, 3))

    def linha_de_botoes(self, botoes: list):
        """Varios botoes discretos lado a lado (ocupa menos altura: cabe em telas de 1366x768)."""
        linha = tema.quadro(self.direita)
        linha.pack(fill="x", pady=1)
        for k, (texto, comando) in enumerate(botoes):
            ttk.Button(linha, text=texto, command=comando, style="Extra.TButton").pack(
                side="left", fill="x", expand=True, padx=(0 if k == 0 else 2, 0)
            )

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

    def texto_extra(self, info: dict) -> str:
        """Linha pequena e clicavel no cartao do projeto (cada tela decide se usa)."""
        return ""

    def clique_extra(self):
        pass

    def codigo_passo(self, info: dict) -> str:
        return info.get("proximo", "")

    # ---------------------------------------------------------- lista
    def preencher(self, projetos: dict):
        selecionados = [n for n in self.tree.selection() if n in self.projetos]
        self.projetos = projetos
        self.tree.delete(*self.tree.get_children())
        for n, info in projetos.items():
            self.tree.insert("", "end", iid=n, text="   " + n, values=("☐",) + tuple(self.valores(info)),
                             image=self.imagem(info))  # fmt: skip
        manter = [n for n in selecionados if n in projetos]
        if manter:
            self.tree.selection_set(manter)
        elif projetos and not self._ja_preencheu:  # so na primeira vez (respeita o "Limpar")
            self.tree.selection_set(next(iter(projetos)))
        if projetos:
            self._ja_preencheu = True
        if projetos:
            self.lbl_vazio.place_forget()
        else:
            self.lbl_vazio.place(relx=0.5, rely=0.45, anchor="center")
        self.selecao_mudou()

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

    # ---------------------------------------------------------- selecionar varios
    def clique(self, evento, ctrl=False, shift=False):
        """Clique na lista: caixinha, Ctrl (um a um), Shift (intervalo) ou clique simples (so ele)."""
        if self.tree.identify_region(evento.x, evento.y) not in ("cell", "tree"):
            return None  # cabecalho, barra: deixa o tkinter cuidar
        linha = self.tree.identify_row(evento.y)
        if not linha:
            return "break"
        caixinha = self.tree.identify_column(evento.x) == "#1"  # a primeira coluna depois do nome
        nova, self.ancora = selecao.clicar(list(self.tree.get_children()), list(self.tree.selection()),
                                           self.ancora, linha, ctrl, shift, caixinha)  # fmt: skip
        self.tree.selection_set(nova)
        self.tree.focus(linha)
        self.tree.focus_set()
        return "break"

    def duplo_clique(self, evento):
        """Duplo clique no projeto faz o proximo passo (na caixinha, nao: la e so marcar e desmarcar)."""
        if self.tree.identify_column(evento.x) == "#1" or not self.tree.identify_row(evento.y):
            return "break"
        self.acao_principal()
        return "break"

    def selecionar_todos(self):
        self.tree.selection_set(selecao.todos(list(self.tree.get_children())))

    def limpar_selecao(self):
        self.tree.selection_set(selecao.nenhum())
        self.ancora = None

    def alternar_todos(self):
        """Clique na caixinha do cabecalho: marca todos (ou desmarca, se ja estavam todos marcados)."""
        itens = list(self.tree.get_children())
        if itens and len(self.tree.selection()) == len(itens):
            self.limpar_selecao()
        else:
            self.selecionar_todos()

    def selecao_mudou(self):
        """Atualiza as caixinhas, o contador e o cartao do projeto."""
        try:
            sel = set(self.tree.selection())
            itens = self.tree.get_children()
        except tk.TclError:
            return
        for n in itens:
            marca = "☑" if n in sel else "☐"
            if self.tree.set(n, "marcar") != marca:
                self.tree.set(n, "marcar", marca)
        self.tree.heading("marcar", text="☑" if itens and len(sel) == len(itens) else "☐")
        self.lbl_contador.config(text=selecao.texto_contador(len(sel)))
        self.atualizar_passo()

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

    def acao_varios(self, selecionados: list):
        """Botao laranja quando 2 ou mais estao selecionados: (texto, comando) ou None (cada tela decide)."""
        return None

    def acao_especial(self):
        """Botao laranja que vale acima de tudo (ex.: "Ver o lote em andamento"): (texto, comando) ou None."""
        return None

    def _acao_do_botao(self, sel: list):
        return self.acao_especial() or (self.acao_varios(sel) if len(sel) >= 2 else None)

    def atualizar_passo(self):
        sel = self.selecionados()
        varios = self._acao_do_botao(sel)
        if varios and len(sel) >= 2:
            nomes = [i["nome"] for i in sel]
            lista = "\n".join("•  " + n for n in nomes[:6]) + (
                f"\n... e mais {len(nomes) - 6}" if len(nomes) > 6 else ""
            )
            self.lbl_nome.config(text=selecao.texto_contador(len(sel)))
            self.lbl_passo.config(text=lista)
            self.lbl_extra.config(text="")
            self.lbl_imagem.config(image="")
            self.btn_principal.config(text=varios[0], command=self.acao_principal)
            return
        info = self.selecionado()
        if varios:  # 0 ou 1 selecionado, mas tem uma acao especial (ex.: lote rodando)
            self.btn_principal.config(text=varios[0], command=self.acao_principal)
        if not info:
            self.lbl_nome.config(text="Nenhum vídeo selecionado")
            self.lbl_passo.config(text=self.TEXTO_VAZIO.replace("\n", " "))
            self.lbl_extra.config(text="")
            self.lbl_imagem.config(image="")
            if not varios:
                self.btn_principal.config(text="Adicionar vídeo", command=self.studio.adicionar_video)
            return
        self.lbl_nome.config(text=info["nome"])
        self.lbl_passo.config(text=self.texto_passo(info))
        self.lbl_extra.config(text=self.texto_extra(info))
        self.lbl_imagem.config(image=self.imagem(info))
        if not varios:
            texto, _ = self.PASSOS.get(self.codigo_passo(info), ("Abrir pasta", "abrir_pasta"))
            self.btn_principal.config(text=texto, command=self.acao_principal)

    def acao_principal(self):
        """O botao laranja: faz o proximo passo do projeto selecionado (ou a acao dos varios selecionados)."""
        varios = self._acao_do_botao(self.selecionados())
        if varios:
            varios[1]()
            return
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
            return montar_menu(self, self.itens_do_menu_varios(sel)
                               + [(f"🗑  Excluir {len(sel)} projetos...", self.excluir, "Delete")])  # fmt: skip
        return montar_menu(self, self.itens_do_menu(sel[0]) + [None, ("🗑  Excluir...", self.excluir, "Delete")])

    def itens_do_menu_varios(self, selecionados: list) -> list:
        """Itens do botao direito com varios projetos selecionados (antes do Excluir; cada tela define os seus)."""
        return []

    def itens_do_menu(self, info: dict) -> list:
        """Itens do botao direito de um projeto (cada tela define os seus)."""
        return [("📁  Abrir pasta", self.abrir_pasta)]

    def excluir(self):
        """Excluir o(s) projeto(s) selecionado(s): pergunta o que excluir e manda para a Lixeira."""
        from interface.janela_excluir import JanelaExcluir
        from interface.utilidades import janela_ja_aberta, lembrar_janela

        aberta = janela_ja_aberta("excluir")  # uma de cada vez (a do Delete apertado duas vezes, por exemplo)
        if aberta is not None:
            return aberta
        sel = self.selecionados()
        if not sel:
            messagebox.showinfo("Excluir", "Selecione um vídeo na lista primeiro.")
            return None
        return lembrar_janela("excluir", JanelaExcluir(self.studio, sel, self.TELA))
