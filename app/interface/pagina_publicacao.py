# Tela "Publicacao": a fila de publicacao. Mostra o que vai sair, quando, e a situacao de cada video
# (na fila, enviando para o Claude, agendado, publicado ou erro), com o link do YouTube.
# Botao direito num item: abrir o pacote, assistir, copiar o pedido para o Claude, mandar de novo,
# marcar como agendado/publicado a mao, abrir o link, tirar da fila.
# A cada poucos segundos confere se o Claude terminou (resultado.json no pacote) e avisa no canto da tela.
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

from interface import tema
from interface.menus import ligar_botao_direito, montar_menu
from interface.utilidades import abrir, em_segundo_plano, mostrar_na_pasta
from publicacao import claude_pc, fila
from publicacao.horario import texto_horario
from publicacao.pacote import texto_pedido

CORES = {"na fila": tema.TEXTO, "enviando": tema.LARANJA, "agendado": tema.VERDE, "publicado": tema.TEXTO_2,
         "erro": tema.VERMELHO}  # fmt: skip
TEXTO_STATUS = {"na fila": "na fila", "enviando": "com o Claude...", "agendado": "✓ agendado",
                "publicado": "✓ no ar", "erro": "⚠ erro"}  # fmt: skip


class PaginaPublicacao(tk.Frame):
    def __init__(self, studio, pai):
        super().__init__(pai, bg=tema.FUNDO)
        self.studio = studio
        topo = tema.quadro(self)
        topo.pack(fill="x", padx=tema.ESPACO * 2, pady=(tema.ESPACO * 1.5, tema.ESPACO / 2))
        tema.rotulo(topo, "Publicação", "titulo").pack(side="left")
        tema.rotulo(topo, "   a fila do YouTube", "secundario").pack(side="left", pady=(8, 0))
        ttk.Button(topo, text="Publicar todos os Shorts prontos", style="Passo.TButton",
                   command=studio.publicar_todos_os_shorts).pack(side="right")  # fmt: skip
        self.lbl_modo = tema.rotulo(self, "", "secundario")
        self.lbl_modo.pack(fill="x", padx=tema.ESPACO * 2)

        quadro = tema.quadro(self)
        quadro.pack(fill="both", expand=True, padx=tema.ESPACO * 2, pady=tema.ESPACO)
        colunas = (("quando", "Quando (Brasília)", 170), ("tipo", "Tipo", 70), ("titulo", "Título", 380),
                   ("status", "Situação", 130), ("link", "Link", 200))  # fmt: skip
        self.tree = ttk.Treeview(quadro, columns=[c[0] for c in colunas], show="headings", selectmode="browse")
        for col, titulo, largura in colunas:
            self.tree.heading(col, text=titulo, anchor="w")
            self.tree.column(col, width=largura, anchor="w", stretch=(col == "titulo"))
        for status, cor in CORES.items():
            self.tree.tag_configure(status, foreground=cor)
        barra = ttk.Scrollbar(quadro, command=self.tree.yview)
        self.tree.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda e: self.abrir_item())
        self.tree.bind("<Delete>", lambda e: self.tirar_da_fila())
        ligar_botao_direito(self.tree, self.menu_do_item)
        self.lbl_vazio = tk.Label(quadro, bg=tema.PAINEL, fg=tema.TEXTO_2, font=tema.F_GRANDE, justify="center",
                                  text="Nada na fila ainda.\nRevise um Short e clique em Publicar, ou use "
                                  '"Publicar todos os Shorts prontos".')  # fmt: skip
        self.lbl_erro = tk.Label(self, text="", bg=tema.FUNDO, fg=tema.VERMELHO, font=tema.F_TEXTO, anchor="w",
                                 justify="left", wraplength=900)  # fmt: skip
        self.lbl_erro.pack(fill="x", padx=tema.ESPACO * 2, pady=(0, tema.ESPACO))
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.mostrar_erro())
        self.atualizar_lista()

    # ---------------------------------------------------------- lista
    def preencher(self, _projetos=None):
        self.atualizar_lista()

    def ao_mostrar(self):
        self.conferir()
        self.atualizar_lista()

    def atualizar_lista(self):
        modo = claude_pc.modo_efetivo()
        self.lbl_modo.config(text="Shorts às 12:00 (Brasília), um por dia.   Vai por: "
                             + ("Claude Code + Claude in Chrome" if modo == "claude_code" else "Cowork / app do Claude")
                             + ".   Botão direito num vídeo: mais opções.")  # fmt: skip
        sel = self.tree.selection()
        self.tree.delete(*self.tree.get_children())
        itens = fila.ordenados()
        ativos = [i for i in itens if i["status"] != "publicado"]
        no_ar = [i for i in itens if i["status"] == "publicado"][::-1]  # os mais recentes primeiro
        for i in ativos + no_ar:
            self.tree.insert("", "end", iid=i["id"], tags=(i["status"],), values=(
                texto_horario(i["horario"]), "Short" if i["tipo"] == "short" else "Longo", i["titulo"],
                TEXTO_STATUS.get(i["status"], i["status"]), i.get("link") or ""))  # fmt: skip
        if sel and self.tree.exists(sel[0]):
            self.tree.selection_set(sel[0])
        if itens:
            self.lbl_vazio.place_forget()
        else:
            self.lbl_vazio.place(relx=0.5, rely=0.4, anchor="center")
        self.mostrar_erro()

    def selecionado(self):
        sel = self.tree.selection()
        return fila.pegar(sel[0]) if sel else None

    def mostrar_erro(self):
        it = self.selecionado()
        self.lbl_erro.config(text=f"Erro em \"{it['titulo']}\": {it['erro']}" if it and it.get("erro") else "")

    def conferir(self):
        """Ve se o Claude terminou algum (resultado.json) e se algum ja entrou no ar. Avisa no canto."""
        from publicacao.rascunhos import marcar_no_projeto

        try:
            mudados = fila.conferir()
        except Exception:
            return
        for item, _antes in mudados:
            if item["status"] in ("agendado", "publicado"):
                marcar_no_projeto(item)
            if item["status"] == "agendado":
                self.studio.notificar(f"Agendado: {item['titulo'][:50]}\n{texto_horario(item['horario'])}", "ok", 7)
            elif item["status"] == "erro":
                self.studio.notificar(f"Erro ao publicar: {item['titulo'][:50]}\n{item['erro'][:120]}", "erro", 9)
        if mudados:
            self.atualizar_lista()
            self.studio.pedir_atualizacao()

    # ---------------------------------------------------------- botao direito
    def menu_do_item(self, evento):
        linha = self.tree.identify_row(evento.y)
        if not linha:
            return None
        self.tree.selection_set(linha)
        it = fila.pegar(linha)
        if not it:
            return None
        pode_mandar = it["status"] in ("na fila", "enviando", "erro")
        return montar_menu(self, [
            ("🔗  Abrir no YouTube", (lambda: webbrowser.open(it["link"])) if it.get("link") else None),
            ("📁  Abrir o pacote", (lambda: abrir(it["pacote"])) if it.get("pacote") else None),
            ("▶  Assistir o vídeo", lambda: abrir(it.get("video_pacote") or it["video"])),
            ("📁  Mostrar o vídeo na pasta", lambda: mostrar_na_pasta(Path(it["video"]))),
            None,
            ("📋  Copiar pedido para o Claude", self.copiar_pedido if it.get("pacote") else None),
            ("📤  Mandar para o Claude de novo", self.mandar_de_novo if pode_mandar else None),
            ("📤  Mandar de novo todos os com erro ou parados", self.mandar_de_novo_todos),
            None,
            ("✓  Marcar como agendado (já fiz)", self.marcar_agendado if it["status"] != "publicado" else None),
            ("✓  Marcar como publicado", self.marcar_publicado if it["status"] != "publicado" else None),
            None,
            ("🗑  Tirar da fila", self.tirar_da_fila, "Delete"),
        ])  # fmt: skip

    def abrir_item(self):
        it = self.selecionado()
        if not it:
            return
        if it.get("link"):
            webbrowser.open(it["link"])
        elif it.get("pacote"):
            abrir(it["pacote"])

    def copiar_pedido(self):
        it = self.selecionado()
        if it:
            self.studio.copiar(texto_pedido([it]))
            self.studio.notificar("Pedido copiado. Cole (Ctrl+V) na conversa com o Claude.", "info")

    def mandar_de_novo(self):
        it = self.selecionado()
        if not it:
            return
        if it["status"] == "enviando" and not messagebox.askyesno(
            "Mandar de novo", "Esse vídeo já foi mandado para o Claude e ele pode estar trabalhando nele agora.\n\n"
            "Mandar de novo mesmo assim? (Confira no YouTube Studio se ele já não foi agendado, para não "
            "subir duas vezes.)", parent=self):  # fmt: skip
            return
        self._mandar([it])

    def mandar_de_novo_todos(self):
        """Todos os que deram erro ou ficaram parados "com o Claude..." de uma vez: os videos vao juntos para a
        pasta _para_enviar (voce arrasta todos de uma vez para o YouTube Studio)."""
        itens = [i for i in fila.ordenados() if i["status"] in ("erro", "enviando")]
        if not itens:
            self.studio.notificar("Nenhum vídeo com erro ou parado com o Claude.", "info")
            return
        if not messagebox.askyesno(
            "Mandar de novo", f"Mandar de novo os {len(itens)} vídeo(s) com erro ou parados \"com o Claude...\"?\n\n"
            "Antes, confira no YouTube Studio se algum já não foi agendado, para não subir duas vezes.", parent=self):  # fmt: skip
            return
        self._mandar(itens)

    def _mandar(self, itens: list):
        self.studio.notificar("Montando os pacotes de novo...", "info", 3)

        def pacotes_prontos(resultado):
            """Montar o pacote pode copiar o video inteiro (outro disco): por isso roda em segundo plano."""
            try:
                if isinstance(resultado, Exception):
                    raise resultado
                r = claude_pc.enviar(itens, copiar=self.studio.copiar)
            except (RuntimeError, OSError) as e:
                for it in itens:
                    fila.atualizar(it["id"], status="erro", erro=str(e))
                messagebox.showerror("Mandar de novo", str(e), parent=self)
                self.atualizar_lista()
                return
            self.atualizar_lista()
            if r["modo"] == "cowork":
                messagebox.showinfo("Mandar de novo", r["aviso"], parent=self)
            else:
                self.studio.notificar(r["aviso"], "info", 10)

        em_segundo_plano(self.studio.raiz, lambda: claude_pc.preparar(itens), pacotes_prontos)

    def marcar_agendado(self):
        from publicacao.rascunhos import marcar_no_projeto

        it = self.selecionado()
        if not it:
            return
        link = simpledialog.askstring("Marcar como agendado", "Link do vídeo no YouTube (pode deixar vazio):",
                                      initialvalue=it.get("link", ""), parent=self)  # fmt: skip
        if link is None:
            return
        it = fila.atualizar(it["id"], status="agendado", link=link.strip(), erro="")
        marcar_no_projeto(it)
        self.atualizar_lista()
        self.studio.pedir_atualizacao()

    def marcar_publicado(self):
        from publicacao.rascunhos import marcar_no_projeto

        it = self.selecionado()
        if it:
            marcar_no_projeto(fila.atualizar(it["id"], status="publicado", erro=""))
            self.atualizar_lista()
            self.studio.pedir_atualizacao()

    def tirar_da_fila(self):
        it = self.selecionado()
        if not it:
            return
        aviso = ""
        if it["status"] in ("enviando", "agendado"):
            aviso = ("\n\n⚠ Ele já foi para o Claude / YouTube. Tirar da fila NÃO cancela no YouTube: "
                     "se precisar, apague o agendamento no YouTube Studio.")  # fmt: skip
        if not messagebox.askyesno("Tirar da fila", f"Tirar \"{it['titulo']}\" da fila?{aviso}\n\n"
                                   "O vídeo e o pacote continuam na pasta.", parent=self):  # fmt: skip
            return
        fila.remover(it["id"])
        self.atualizar_lista()
        self.studio.pedir_atualizacao()
