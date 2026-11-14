# Base das duas abas do Studio: a lista de projetos a esquerda, a faixa "proximo passo" embaixo
# e a coluna de botoes a direita. Cada aba (Shorts, Videos longos) so diz quais colunas e botoes tem.
import tkinter as tk
from tkinter import messagebox, ttk

from interface.utilidades import COR_FUNDO, COR_TEXTO, abrir
from nucleo.limpeza import apagar_projeto, limpar_midia, midia_do_projeto, tamanho_txt


class AbaProjetos(tk.Frame):
    COLUNAS = []  # [(id, titulo, largura)] - cada aba define as suas

    def __init__(self, studio, pai):
        super().__init__(pai, bg=COR_FUNDO)
        self.studio = studio
        self.projetos = {}

        esquerda = tk.Frame(self, bg=COR_FUNDO)
        esquerda.pack(side="left", fill="both", expand=True, pady=(8, 0))
        self._montar_lista(esquerda)

        self.direita = tk.Frame(self, bg=COR_FUNDO)
        self.direita.pack(side="right", fill="y", padx=(16, 0))
        self.montar_botoes()

    # ---------------------------------------------------------- montagem
    def _montar_lista(self, pai):
        self.tree = ttk.Treeview(pai, columns=[c[0] for c in self.COLUNAS], show="tree headings", selectmode="browse")
        self.tree.heading("#0", text="Vídeo")
        self.tree.column("#0", width=380, anchor="w")
        for col, titulo, largura in self.COLUNAS:
            self.tree.heading(col, text=titulo)
            self.tree.column(col, width=largura, anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.atualizar_passo())
        self.tree.bind("<Double-1>", lambda e: self.abrir_pasta())
        self.lbl_passo = tk.Label(
            pai,
            text="",
            bg="#232336",
            fg=COR_TEXTO,
            anchor="w",
            justify="left",
            font=("Segoe UI", 11),
            padx=12,
            pady=10,
        )
        self.lbl_passo.pack(fill="x", pady=(8, 0))

    def secao(self, texto):
        ttk.Label(self.direita, text=texto, style="Sec.TLabel").pack(anchor="w", pady=(10, 3))

    def botao(self, texto, comando, estilo="Extra.TButton"):
        b = ttk.Button(self.direita, text=texto, command=comando, style=estilo, width=30)
        b.pack(fill="x", pady=2)
        return b

    # ---------------------------------------------------------- o que cada aba define
    def montar_botoes(self):
        raise NotImplementedError

    def valores(self, info: dict) -> tuple:
        """O que aparece em cada coluna para um projeto."""
        raise NotImplementedError

    def texto_passo(self, info: dict) -> str:
        raise NotImplementedError

    TEXTO_VAZIO = "Nenhum vídeo ainda."

    # ---------------------------------------------------------- lista
    def preencher(self, projetos: dict):
        selecionado = self.selecionado()
        nome = selecionado["nome"] if selecionado else None
        self.projetos = projetos
        self.tree.delete(*self.tree.get_children())
        for n, info in projetos.items():
            self.tree.insert("", "end", iid=n, text="  " + n, values=self.valores(info))
        if nome in projetos:
            self.tree.selection_set(nome)
        elif projetos:
            self.tree.selection_set(next(iter(projetos)))
        self.atualizar_passo()

    def selecionado(self):
        try:
            sel = self.tree.selection()
        except Exception:
            return None
        return self.projetos.get(sel[0]) if sel else None

    def atualizar_passo(self):
        info = self.selecionado()
        self.lbl_passo.config(text=self.texto_passo(info) if info else self.TEXTO_VAZIO)

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

    def limpar_projeto(self):
        """Depois de postar: manda a midia pesada para a Lixeira e guarda o resumo do projeto."""
        info = self.exigir()
        if not info:
            return
        pasta = info["pasta"]
        itens = midia_do_projeto(pasta)
        total = sum(t for _, t in itens)
        avisos = []
        if info["n_shorts"] and info["postados"] < info["n_shorts"]:
            avisos.append(f"⚠ {info['n_shorts'] - info['postados']} Short(s) ainda NÃO estão marcados como postados.")
        if info["episodio"] == "ok":
            avisos.append("⚠ O episódio do vídeo longo vai junto. Confira se você já postou.")
        texto = (
            f"Limpar o projeto \"{info['nome']}\"?\n\n"
            + ("\n".join(avisos) + "\n\n" if avisos else "")
            + (
                f"Vai para a Lixeira: {len(itens)} item(ns), {tamanho_txt(total)} "
                "(Shorts, episódio, versões antigas e temporários).\n"
                if itens
                else "Esse projeto não tem mídia para limpar.\n"
            )
            + "Fica guardado o resumo: cortes, edição, textos para postar e o que já foi postado.\n\n"
            "SIM = limpar só a mídia (recomendado)\n"
            "NÃO = mandar o projeto INTEIRO para a Lixeira (inclusive o resumo)\n"
            "CANCELAR = não fazer nada\n\n"
            "O vídeo original não é tocado. Dá para restaurar pela Lixeira do Windows."
        )
        resposta = messagebox.askyesnocancel("Limpar projeto", texto, icon="warning" if avisos else "question")
        if resposta is None:
            return
        try:
            if resposta:
                liberado = limpar_midia(pasta)
                mensagem = (
                    f"Pronto! {tamanho_txt(liberado)} foram para a Lixeira.\nO resumo do projeto continua na lista."
                )
            else:
                apagar_projeto(pasta)
                mensagem = "Pronto! O projeto inteiro foi para a Lixeira."
        except Exception as e:
            messagebox.showerror("Limpar projeto", f"Não consegui limpar:\n{e}")
            return
        messagebox.showinfo("Limpar projeto", mensagem)
        self.studio.atualizar()
