# Tela do LOTE: mostra os videos e a etapa de cada um (na fila, transcrevendo, cortando, renderizando, pronto,
# erro), a barra geral com o tempo estimado e os botoes Pausar, Continuar e Cancelar. O lote roda em segundo
# plano (shorts/lote.py): esta janela so le o estado de tempos em tempos, entao pode ser fechada e aberta de
# novo sem parar nada. No fim vira o RESUMO: Shorts de cada video, tempo, erros, "Revisar" e "Tentar de novo".
import tkinter as tk
from tkinter import messagebox, ttk

from interface import tema
from shorts import lote as motor


def texto_duracao(segundos: float) -> str:
    segundos = int(segundos or 0)
    if segundos < 60:
        return f"{segundos} s"
    if segundos < 3600:
        return f"{segundos // 60} min {segundos % 60:02d} s"
    return f"{segundos // 3600} h {segundos % 3600 // 60:02d} min"


class JanelaLote:
    def __init__(self, studio, rodar: motor.RodarLote):
        self.studio = studio
        self.rodar = rodar
        self.terminado_mostrado = False

        self.jan = tk.Toplevel(studio.raiz)
        self.jan.title("Lote de Shorts")
        self.jan.configure(bg=tema.FUNDO)
        self.jan.minsize(900, 440)
        self.jan.protocol("WM_DELETE_WINDOW", self.fechar)
        q = tk.Frame(self.jan, bg=tema.FUNDO, padx=22, pady=16)
        q.pack(fill="both", expand=True)
        self.lbl_titulo = tema.rotulo(q, "Gerando os Shorts dos vídeos selecionados", "subtitulo")
        self.lbl_titulo.pack(fill="x")
        self.lbl_explica = tema.rotulo(q, "Pode continuar usando o Studio ou fechar esta janela: o lote continua. "
                                       "Para ver de novo, clique no botão laranja da tela Shorts.", "secundario",
                                       wraplength=840)  # fmt: skip
        self.lbl_explica.pack(fill="x", pady=(2, 10))

        meio = tk.Frame(q, bg=tema.FUNDO)
        meio.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(meio, columns=("etapa", "detalhe", "shorts", "tempo"), show="tree headings",
                                 height=8, selectmode="browse")  # fmt: skip
        for col, titulo, largura, ancora in (("#0", "Vídeo", 220, "w"), ("etapa", "Etapa", 140, "w"),
                                              ("detalhe", "Detalhe", 330, "w"), ("shorts", "Shorts", 60, "center"),
                                              ("tempo", "Tempo", 80, "center")):  # fmt: skip
            self.tree.heading(col, text=titulo, anchor=ancora)
            self.tree.column(col, width=largura, anchor=ancora, stretch=col in ("#0", "detalhe"))
        barra = ttk.Scrollbar(meio, command=self.tree.yview)
        self.tree.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.atualizar_botoes())
        self.tree.bind("<Double-1>", lambda e: self.revisar())

        self.lbl_erro = tk.Label(q, text="", bg=tema.FUNDO, fg=tema.VERMELHO, font=tema.F_PEQUENA, anchor="w",
                                 justify="left", wraplength=700)  # fmt: skip
        self.lbl_erro.pack(fill="x", pady=(6, 0))
        self.barra = ttk.Progressbar(q, mode="determinate", maximum=1.0)
        self.barra.pack(fill="x", pady=(8, 2))
        self.lbl_progresso = tema.rotulo(q, "", "pequeno")
        self.lbl_progresso.pack(fill="x")

        baixo = tk.Frame(q, bg=tema.FUNDO)
        baixo.pack(fill="x", pady=(12, 0))
        self.btn_revisar = ttk.Button(baixo, text="✏ Revisar", style="Extra.TButton", command=self.revisar)
        self.btn_revisar.pack(side="left")
        self.btn_tentar = ttk.Button(baixo, text="⟳ Tentar de novo só este", style="Extra.TButton",
                                     command=self.tentar_de_novo)  # fmt: skip
        self.btn_tentar.pack(side="left", padx=(4, 0))
        self.btn_fechar = ttk.Button(baixo, text="Fechar", style="Extra.TButton", command=self.fechar)
        self.btn_fechar.pack(side="right")
        self.btn_cancelar = ttk.Button(baixo, text="Cancelar", style="Extra.TButton", command=self.cancelar)
        self.btn_cancelar.pack(side="right", padx=(0, 8))
        self.btn_pausa = ttk.Button(baixo, text="⏸ Pausar", style="Passo.TButton", command=self.pausar_continuar)
        self.btn_pausa.pack(side="right", padx=(0, 8))
        self.conferir()

    # ---------------------------------------------------------- atualizar a tela
    def conferir(self):
        if not self.jan.winfo_exists():
            return
        lote = self.rodar.retrato()
        self.mostrar(lote)
        if self.rodar.terminou.is_set():
            self.terminou(lote)
            return
        self.jan.after(500, self.conferir)

    def mostrar(self, lote: dict):
        nomes = [v["nome"] for v in lote["videos"]]
        if list(self.tree.get_children()) != nomes:
            self.tree.delete(*self.tree.get_children())
            for n in nomes:
                self.tree.insert("", "end", iid=n, text="  " + n)
        for v in lote["videos"]:
            simbolo, texto = motor.ETAPAS.get(v["etapa"], ("", v["etapa"]))
            detalhe = v.get("erro") or v.get("detalhe") or "; ".join(v.get("avisos") or [])
            shorts = v.get("n_shorts") if v["etapa"] in ("pronto", "pulado") else ""
            tempo = texto_duracao(v.get("segundos")) if v.get("segundos") else ""
            self.tree.item(v["nome"], values=(f"{simbolo}  {texto}", detalhe, shorts, tempo))
        feito = motor.progresso_geral(lote)
        self.barra["value"] = feito
        situacao = lote.get("situacao")
        if situacao == "pausado":
            estado = "⏸ Pausado: termina a etapa que está rodando e espera você clicar em Continuar."
        else:
            resta = motor.tempo_restante(lote)
            estado = "calculando o tempo que falta..." if resta is None else f"falta ~{motor.texto_tempo(resta)}"
        self.lbl_progresso.config(text=f"{feito * 100:.0f}%  ·  {estado}  ·  {texto_duracao(lote.get('segundos'))} "
                                  "passados")  # fmt: skip
        self.btn_pausa.config(text="▶ Continuar" if situacao == "pausado" else "⏸ Pausar")
        self.atualizar_botoes(lote)

    def selecionado(self, lote=None):
        lote = lote or self.rodar.retrato()
        sel = self.tree.selection()
        return next((v for v in lote["videos"] if sel and v["nome"] == sel[0]), None)

    def atualizar_botoes(self, lote=None):
        v = self.selecionado(lote)
        terminou = self.rodar.terminou.is_set()
        self.btn_revisar.config(state="normal" if v and v.get("n_shorts") and v["etapa"] in ("pronto", "pulado")
                                else "disabled")  # fmt: skip
        self.btn_tentar.config(state="normal" if terminou and v and v["etapa"] == "erro" else "disabled")
        self.lbl_erro.config(text=f"❌ {v['nome']}: {v['erro']}" if v and v.get("erro") else "")

    # ---------------------------------------------------------- botoes
    def pausar_continuar(self):
        if self.rodar.terminou.is_set():
            return
        if self.rodar.retrato().get("situacao") == "pausado":
            self.rodar.continuar()
        else:
            self.rodar.pausar()
            self.studio.notificar("O lote vai pausar depois da etapa que está rodando.", "info")
        self.mostrar(self.rodar.retrato())

    def cancelar(self):
        if self.rodar.terminou.is_set():
            return
        if not messagebox.askyesno("Cancelar o lote",
                                   "Cancelar o lote?\n\nA etapa que está rodando para agora (sem deixar arquivo "
                                   "quebrado). Os Shorts que já ficaram prontos continuam na pasta de cada vídeo.",
                                   parent=self.jan):  # fmt: skip
            return
        self.rodar.cancelar()
        self.btn_cancelar.config(state="disabled", text="Cancelando...")
        self.btn_pausa.config(state="disabled")

    def revisar(self):
        """Abre o editor de Shorts do projeto selecionado."""
        v = self.selecionado()
        if not v or not v.get("n_shorts"):
            return
        self.studio.atualizar()
        info = self.studio.projetos.get(v["nome"])
        if not info:
            messagebox.showinfo("Revisar", "Não achei esse projeto (foi excluído?).", parent=self.jan)
            return
        from interface.editor_legendas import EditorLegendas

        EditorLegendas.abrir(self.studio, info)

    def tentar_de_novo(self):
        v = self.selecionado()
        if not v or v["etapa"] != "erro":
            return
        lote = motor.tentar_de_novo(self.rodar.retrato(), v["nome"])
        novo = self.studio.comecar_lote(lote, janela=self)
        if novo:
            self.rodar = novo
            self.terminado_mostrado = False
            self.lbl_titulo.config(text=f"Tentando de novo: {v['nome']}")
            self.btn_pausa.config(state="normal")
            self.btn_cancelar.config(state="normal", text="Cancelar")
            self.conferir()

    def fechar(self):
        """Fechar so esconde a tela: o lote continua em segundo plano."""
        if not self.rodar.terminou.is_set():
            self.studio.notificar("O lote continua rodando. Para ver de novo: botão laranja da tela Shorts.", "info")
        self.jan.destroy()

    # ---------------------------------------------------------- resumo do fim
    def terminou(self, lote: dict):
        self.btn_pausa.config(state="disabled")
        self.btn_cancelar.config(state="disabled", text="Cancelar")
        self.atualizar_botoes(lote)
        if self.terminado_mostrado:
            return
        self.terminado_mostrado = True
        r = motor.resumo(lote)
        if lote.get("situacao") == "cancelado":
            self.lbl_titulo.config(text="Lote cancelado")
            self.lbl_explica.config(text=f"{r['n_shorts']} Shorts ficaram prontos antes de cancelar. Os vídeos que "
                                    "faltaram ficaram como estavam.")  # fmt: skip
            return
        self.lbl_titulo.config(text=f"Lote pronto: {r['n_shorts']} Shorts de {r['n_videos']} vídeo(s)")
        partes = [f"Levou {texto_duracao(r['segundos'])}."]
        if r["erros"]:
            partes.append(f"{len(r['erros'])} vídeo(s) com erro: selecione e clique em \"Tentar de novo só este\".")
        partes.append("Nada foi publicado: selecione um vídeo e clique em Revisar para conferir os Shorts.")
        self.lbl_explica.config(text=" ".join(partes))
        primeiro_erro = next((v["nome"] for v in r["erros"]), None)
        if primeiro_erro:
            self.tree.selection_set(primeiro_erro)
