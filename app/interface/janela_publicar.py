# Janela "Publicar": revisar o titulo, a descricao, as tags, a playlist e o horario de cada video ANTES de
# publicar. Nada vai para o YouTube sem o clique em "Confirmar e publicar".
# Depois do clique: o video entra na fila, o Studio monta o pacote (video, thumb, dados) e manda o pedido para
# o Claude no seu computador (Claude Code + Chrome, ou Cowork), que agenda pelo YouTube Studio.
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from interface import tema
from interface.telas import nova_janela
from interface.utilidades import em_segundo_plano
from nucleo.comum import salvar_ajustes
from publicacao import claude_pc, fila
from publicacao.horario import agora, iso, ler_caixa, para_caixa, texto_horario
from publicacao.pacote import LIMITE_TITULO, problemas_do_item


class JanelaPublicar:
    def __init__(self, studio, itens: list, parent=None):
        """itens: rascunhos (publicacao.rascunhos) ainda nao gravados na fila."""
        self.studio = studio
        self.itens = itens
        self.atual = None
        self.enviando = False
        pai = parent or studio.raiz
        self.jan = nova_janela(pai)
        self.jan.title("Publicar no YouTube")
        self.jan.configure(bg=tema.FUNDO)
        largura, altura = self.jan.winfo_screenwidth(), self.jan.winfo_screenheight()
        self.jan.geometry(f"{min(1100, largura - 60)}x{min(700, altura - 90)}+30+20")
        self.jan.protocol("WM_DELETE_WINDOW", self.cancelar)

        topo = tk.Frame(self.jan, bg=tema.FUNDO)
        topo.pack(fill="x", padx=20, pady=(16, 4))
        n = len(itens)
        tema.rotulo(topo, "Revisar antes de publicar" + (f"  ({n} vídeos)" if n > 1 else ""), "titulo").pack(
            side="left"
        )
        modo = claude_pc.modo_efetivo()
        tema.rotulo(
            self.jan,
            "Nada vai para o YouTube antes de você clicar em Confirmar.   Vai por: "
            + ("Claude Code + Claude in Chrome (agenda sozinho)" if modo == "claude_code"
               else "Cowork / app do Claude (você cola o pedido)")
            + "  (mude em Configurações > Claude)",
            "secundario", wraplength=1000,
        ).pack(fill="x", padx=20)  # fmt: skip

        corpo = tk.Frame(self.jan, bg=tema.FUNDO)
        corpo.pack(fill="both", expand=True, padx=20, pady=12)
        self.lista = tk.Listbox(corpo, width=42, activestyle="none", bg=tema.PAINEL, fg=tema.TEXTO,
                                selectbackground=tema.LARANJA_ESCURO, selectforeground=tema.TEXTO,
                                highlightthickness=0, borderwidth=0, exportselection=False, font=tema.F_TEXTO)  # fmt: skip
        if n > 1:
            self.lista.pack(side="left", fill="y", padx=(0, 16))
        self.lista.bind("<<ListboxSelect>>", lambda e: self.escolher())
        self._montar_formulario(corpo)

        baixo = tk.Frame(self.jan, bg=tema.FUNDO)
        baixo.pack(fill="x", padx=20, pady=(0, 16))
        self.progresso = ttk.Progressbar(baixo, mode="determinate", maximum=1.0, length=260)
        self.lbl_progresso = tema.rotulo(baixo, "", "secundario")
        self.btn_ok = ttk.Button(baixo, text="Confirmar e publicar", style="Passo.TButton", command=self.confirmar)
        self.btn_ok.pack(side="right")
        ttk.Button(baixo, text="Cancelar", style="Extra.TButton", command=self.cancelar).pack(side="right", padx=8)
        self.jan.bind("<Escape>", lambda e: self.cancelar())
        self.preencher_lista()
        self.lista.selection_set(0)
        self.escolher()

    # ---------------------------------------------------------- formulario
    def _montar_formulario(self, pai):
        f = tk.Frame(pai, bg=tema.FUNDO)
        f.pack(side="left", fill="both", expand=True)
        self.lbl_tipo = tema.rotulo(f, "", "secao", cor=tema.LARANJA)
        self.lbl_tipo.pack(fill="x")

        def campo(titulo):
            tema.rotulo(f, titulo, "secao").pack(fill="x", pady=(10, 2))

        campo("TÍTULO")
        linha = tk.Frame(f, bg=tema.FUNDO)
        linha.pack(fill="x")
        self.titulo = ttk.Entry(linha, font=tema.F_GRANDE)
        self.titulo.pack(side="left", fill="x", expand=True)
        self.lbl_conta = tema.rotulo(linha, "", "pequeno", width=8, anchor="e")
        self.lbl_conta.pack(side="left", padx=(8, 0))
        self.titulo.bind("<KeyRelease>", lambda e: self.contar())

        campo("DATA E HORA  (horário de Brasília)")
        linha = tk.Frame(f, bg=tema.FUNDO)
        linha.pack(fill="x")
        self.horario = ttk.Entry(linha, width=18, font=tema.F_GRANDE)
        self.horario.pack(side="left")
        self.lbl_dia = tema.rotulo(linha, "", "secundario")
        self.lbl_dia.pack(side="left", padx=10)
        self.horario.bind("<KeyRelease>", lambda e: self.mostrar_dia())

        campo("DESCRIÇÃO")
        self.descricao = tk.Text(f, height=9, wrap="word", font=tema.F_TEXTO, bg=tema.CAMPO, fg=tema.TEXTO,
                                 insertbackground=tema.TEXTO, relief="flat", padx=8, pady=6)  # fmt: skip
        self.descricao.pack(fill="both", expand=True)

        duas = tk.Frame(f, bg=tema.FUNDO)
        duas.pack(fill="x")
        esq, dir_ = tk.Frame(duas, bg=tema.FUNDO), tk.Frame(duas, bg=tema.FUNDO)
        esq.pack(side="left", fill="x", expand=True, padx=(0, 10))
        dir_.pack(side="left", fill="x", expand=True)
        tema.rotulo(esq, "TAGS  (separadas por vírgula)", "secao").pack(fill="x", pady=(10, 2))
        self.tags = ttk.Entry(esq)
        self.tags.pack(fill="x")
        tema.rotulo(dir_, "PLAYLIST  (opcional)", "secao").pack(fill="x", pady=(10, 2))
        self.playlist = ttk.Entry(dir_)
        self.playlist.pack(fill="x")

        self.linha_thumb = tk.Frame(f, bg=tema.FUNDO)
        self.linha_thumb.pack(fill="x", pady=(10, 0))
        self.lbl_thumb = tema.rotulo(self.linha_thumb, "", "secundario")
        self.lbl_thumb.pack(side="left")
        self.btn_thumb = ttk.Button(self.linha_thumb, text="Escolher thumb...", style="Extra.TButton",
                                    command=self.escolher_thumb)  # fmt: skip
        self.lbl_aviso = tk.Label(f, text="", bg=tema.FUNDO, fg=tema.AMARELO, font=tema.F_PEQUENA, anchor="w",
                                  justify="left", wraplength=640)  # fmt: skip
        self.lbl_aviso.pack(fill="x", pady=(6, 0))

    def preencher_lista(self):
        sel = self.lista.curselection()
        self.lista.delete(0, "end")
        for item in self.itens:
            self.lista.insert("end", f"{texto_horario(item['horario'])}   {item['titulo'][:40]}")
        if sel:
            self.lista.selection_set(sel[0])

    def escolher(self):
        sel = self.lista.curselection()
        if not sel:
            return
        if self.atual is not None and not self.guardar():
            self.lista.selection_clear(0, "end")
            self.lista.selection_set(self.itens.index(self.atual))
            return
        self.atual = self.itens[sel[0]]
        it = self.atual
        self.lbl_tipo.config(text=("SHORT" if it["tipo"] == "short" else "VÍDEO LONGO") + f"  ·  {it['projeto']}")
        for caixa, valor in ((self.titulo, it["titulo"]), (self.horario, para_caixa(it["horario"])),
                             (self.tags, ", ".join(it.get("tags") or [])), (self.playlist, it.get("playlist", ""))):  # fmt: skip
            caixa.delete(0, "end")
            caixa.insert(0, valor)
        self.descricao.delete("1.0", "end")
        self.descricao.insert("1.0", it.get("descricao") or "")
        if it["tipo"] == "short":
            self.lbl_thumb.config(text="Thumb: o YouTube não deixa trocar a thumb de Short pelo computador "
                                  "(fica um quadro do vídeo).")  # fmt: skip
            self.btn_thumb.pack_forget()
        else:
            self.lbl_thumb.config(text=f"Thumb: {it.get('thumb') or 'um quadro do vídeo (thumb.png)'}")
            self.btn_thumb.pack(side="left", padx=10)
        self.contar()
        self.mostrar_dia()

    def contar(self):
        n = len(self.titulo.get())
        self.lbl_conta.config(text=f"{n}/{LIMITE_TITULO}", fg=tema.VERMELHO if n > LIMITE_TITULO else tema.TEXTO_2)

    def mostrar_dia(self):
        try:
            quando = ler_caixa(self.horario.get())
        except ValueError:
            self.lbl_dia.config(text="use dia/mês/ano hora:minuto", fg=tema.AMARELO)
            return
        passou = quando <= agora()
        self.lbl_dia.config(text=texto_horario(quando) + ("  ⚠ já passou" if passou else ""),
                            fg=tema.AMARELO if passou else tema.TEXTO_2)  # fmt: skip

    def escolher_thumb(self):
        arq = filedialog.askopenfilename(title="Escolha a thumb (1280x720)", parent=self.jan,
                                         filetypes=[("Imagens", "*.png *.jpg *.jpeg"), ("Todos", "*.*")])  # fmt: skip
        if arq and self.atual:
            self.atual["thumb"] = arq
            self.lbl_thumb.config(text=f"Thumb: {arq}")

    def guardar(self) -> bool:
        """Passa o que esta nas caixas para o item atual. False se a data estiver errada."""
        it = self.atual
        if it is None:
            return True
        try:
            quando = ler_caixa(self.horario.get())
        except ValueError as e:
            messagebox.showinfo("Data e hora", str(e), parent=self.jan)
            return False
        it.update(titulo=" ".join(self.titulo.get().split()), horario=iso(quando),
                  descricao=self.descricao.get("1.0", "end-1c").strip(), playlist=self.playlist.get().strip(),
                  tags=[t.strip().lstrip("#") for t in self.tags.get().split(",") if t.strip()])  # fmt: skip
        self.preencher_lista()
        return True

    # ---------------------------------------------------------- confirmar
    def problemas(self) -> list:
        erros = []
        horarios = {}
        for it in self.itens:
            nome = it["titulo"][:40] or it["video"]
            erros += [f"{nome}: {p}" for p in problemas_do_item(it)]
            if fila.na_fila(Path(it["video"])):  # outra revisao (ou o lote) ja mandou este video para a fila
                erros.append(f"{nome}: já está na fila de publicação (veja a tela Publicação)")
            if it["horario"] <= iso(agora()):
                erros.append(f"{nome}: a data e hora já passou")
            if it["tipo"] == "short":
                dia = it["horario"][:10]
                if dia in horarios:
                    erros.append(f"{nome}: dois Shorts no mesmo dia ({dia[8:10]}/{dia[5:7]}). Um por dia.")
                horarios[dia] = True
        return erros

    def confirmar(self):
        if self.enviando or not self.guardar():
            return
        erros = self.problemas()
        if erros:
            messagebox.showinfo("Antes de publicar, arrume:", "\n".join(f"• {e}" for e in erros[:12]), parent=self.jan)
            return
        for it in self.itens:  # lembra a ultima playlist usada (de Short e de video longo)
            if it.get("playlist"):
                salvar_ajustes({f"ultima_playlist_{it['tipo']}": it["playlist"]})
        self.enviando = True
        self.btn_ok.config(state="disabled", text="Preparando...")
        self.progresso.pack(side="left")
        self.lbl_progresso.pack(side="left", padx=10)
        fila.adicionar(self.itens)
        estado = {"k": 0, "f": 0.0}

        def progresso(k, total, fracao):
            estado.update(k=k, f=fracao, total=total)

        def trabalho():
            return claude_pc.preparar(self.itens, progresso)

        def mostrar_progresso():
            if not self.enviando or not self.jan.winfo_exists():
                return
            total = max(1, len(self.itens))
            self.progresso["value"] = (estado["k"] + estado["f"]) / total
            self.lbl_progresso.config(text=f"Montando o pacote {estado['k'] + 1} de {total}...")
            self.jan.after(200, mostrar_progresso)

        mostrar_progresso()
        em_segundo_plano(self.jan, trabalho, self.pacotes_prontos)

    def pacotes_prontos(self, resultado):
        if isinstance(resultado, Exception):
            for it in self.itens:
                fila.atualizar(it["id"], status="erro", erro=f"não consegui montar o pacote: {resultado}")
            self.terminar()
            messagebox.showerror("Publicar", f"Não consegui montar o pacote de postagem:\n{resultado}\n\n"
                                 "Os vídeos ficaram na fila com erro. Confira o espaço no disco e tente de novo pela "
                                 "tela Publicação.", parent=self.studio.raiz)  # fmt: skip
            return
        try:
            r = claude_pc.enviar(self.itens, copiar=self.studio.copiar)
        except (RuntimeError, OSError) as e:
            for it in self.itens:
                fila.atualizar(it["id"], status="erro", erro=str(e))
            self.terminar()
            messagebox.showerror("Publicar", str(e), parent=self.studio.raiz)
            return
        self.terminar()
        if r["modo"] == "cowork":
            messagebox.showinfo("Publicar", r["aviso"], parent=self.studio.raiz)
        else:
            self.studio.notificar(r["aviso"], "info", 9)

    def terminar(self):
        self.enviando = False
        if self.jan.winfo_exists():
            self.jan.destroy()
        self.studio.atualizar()
        self.studio.mostrar("publicacao")

    def cancelar(self):
        if self.enviando:
            return  # ja confirmou: deixa terminar de montar os pacotes
        self.jan.destroy()
