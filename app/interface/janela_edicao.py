# Janela de revisao do video longo (passo 3 da aba Videos longos): o que sai, ouvir emenda, previa e gerar o episodio.
import tkinter as tk
from tkinter import messagebox, ttk

from interface import tema
from interface.utilidades import COR_DESTAQUE, COR_FUNDO, COR_TEXTO, abrir, rodar_script
from nucleo.comum import carregar_config, gravar_json, mover_para_antigos, tempo_txt


class JanelaEdicao:
    """Revisao do edicao.json: o que SAI, caixinha para desmarcar, ouvir emenda, previa e gerar."""

    def __init__(self, studio, info: dict):
        from videos_longos.pedido_edicao import carregar_palavras, fps_fracao, info_video

        self.studio = studio
        self.info = info
        self.pasta = info["pasta"]
        self.arq = self.pasta / "edicao.json"
        self.video, self.dur = info_video(self.pasta)
        self.fps = fps_fracao(self.video) if self.video.exists() else None
        self.palavras = carregar_palavras(self.pasta)

        self.jan = tk.Toplevel(studio.raiz)
        self.jan.title(f"Editar vídeo longo - {info['nome']}")
        self.jan.geometry("1120x680")
        self.jan.configure(bg=COR_FUNDO)

        topo = tk.Frame(self.jan, bg=COR_FUNDO)
        topo.pack(fill="x", padx=16, pady=(12, 2))
        tk.Label(
            topo, text="Revisar a edição do vídeo longo", bg=COR_FUNDO, fg=COR_DESTAQUE, font=("Segoe UI", 15, "bold")
        ).pack(side="left")
        self.lbl_dur = tk.Label(
            self.jan, text="", bg=COR_FUNDO, fg=COR_TEXTO, font=("Segoe UI", 13, "bold"), anchor="w"
        )
        self.lbl_dur.pack(fill="x", padx=16)
        self.lbl_info = tk.Label(
            self.jan,
            text="",
            bg=COR_FUNDO,
            fg=tema.TEXTO_2,
            font=("Segoe UI", 10),
            anchor="w",
            justify="left",
            wraplength=1080,
        )
        self.lbl_info.pack(fill="x", padx=16, pady=(2, 6))

        meio = tk.Frame(self.jan, bg=COR_FUNDO)
        meio.pack(fill="both", expand=True, padx=16)
        cols = ("sai", "inicio", "fim", "dur", "motivo", "aviso")
        self.tree = ttk.Treeview(meio, columns=cols, show="headings", selectmode="browse")
        for col, txt, w, anc in [
            ("sai", "Sai?", 50, "center"),
            ("inicio", "Início", 90, "center"),
            ("fim", "Fim", 90, "center"),
            ("dur", "Duração", 80, "center"),
            ("motivo", "Motivo (o que sai)", 600, "w"),
            ("aviso", "Aviso", 150, "w"),
        ]:
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w, anchor=anc, stretch=(col == "motivo"))
        barra = ttk.Scrollbar(meio, command=self.tree.yview)
        self.tree.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.tag_configure("off", foreground=tema.TEXTO_2)
        self.tree.tag_configure("curto", foreground=tema.AMARELO)
        self.tree.bind("<Button-1>", self.clique)
        self.tree.bind("<space>", lambda e: self.alternar())
        self.tree.bind("<Double-1>", lambda e: self.ouvir())
        tk.Label(
            self.jan,
            text="Clique na caixinha (ou aperte Espaço) para desmarcar um corte: o trecho desmarcado "
            "FICA no episódio. Duplo clique = Ouvir emenda.",
            bg=COR_FUNDO,
            fg=tema.TEXTO_2,
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(fill="x", padx=16, pady=(4, 0))

        bot = tk.Frame(self.jan, bg=COR_FUNDO)
        bot.pack(fill="x", padx=16, pady=10)
        ttk.Button(bot, text="Ouvir emenda", style="Extra.TButton", command=self.ouvir).pack(side="left")
        ttk.Button(bot, text="Gerar prévia (10 min)", style="Extra.TButton", command=self.previa).pack(
            side="left", padx=6
        )
        ttk.Button(bot, text="Gerar episódio", style="Passo.TButton", command=self.gerar).pack(side="left", padx=6)
        ttk.Button(bot, text="Abrir pasta do episódio", style="Extra.TButton", command=self.abrir_pasta_ep).pack(
            side="right"
        )
        ttk.Button(bot, text="Colar edicao.json", style="Extra.TButton", command=self.colar).pack(side="right", padx=6)
        ttk.Button(
            bot,
            text="Copiar pedido de novo",
            style="Extra.TButton",
            command=lambda: self.studio.pedir_edicao(self.info, self.jan),
        ).pack(side="right")

        self.carregar()

    # ------------------------------------------------------ dados
    def carregar(self):
        from videos_longos.pedido_edicao import ler_edicao

        self.dados, self.erros, self.avisos = ler_edicao(self.pasta, self.dur)
        self.mostrar()

    def mostrar(self):
        from videos_longos.pedido_edicao import CORTE_CURTO, capitulos_editados, montar_plano

        self.tree.delete(*self.tree.get_children())
        if self.erros or not self.dados:
            self.lbl_dur.config(text="O edicao.json tem problemas")
            self.lbl_info.config(
                text="- " + "\n- ".join(self.erros[:8]) + "\nPeça pro Claude corrigir " '(ou use "Colar edicao.json").',
                fg=tema.VERMELHO,
            )
            return
        if not self.video.exists():
            self.lbl_dur.config(text="Não achei o vídeo original")
            self.lbl_info.config(text=str(self.video), fg=tema.VERMELHO)
            return
        self.plano = montar_plano(self.dados, self.dur, self.fps, self.palavras, carregar_config())
        for c in self.plano["cortes"]:
            curto = c["dur"] < CORTE_CURTO
            tags = ("off",) if not c["ativo"] else (("curto",) if curto else ())
            self.tree.insert(
                "",
                "end",
                iid=str(c["n"]),
                tags=tags,
                values=(
                    "☑" if c["ativo"] else "☐",
                    tempo_txt(c["ini_aj"]),
                    tempo_txt(c["fim_aj"]),
                    f"{c['dur'] / 60:.0f} min" if c["dur"] >= 120 else f"{c['dur']:.0f} s",
                    c["motivo"],
                    "⚠ menos de 30 s" if curto else "",
                ),
            )
        sai = (
            self.plano["dur_original"]
            - self.plano["dur_final"]
            + (self.plano["abertura"][1] / float(self.fps) if self.plano["abertura"] else 0)
        )
        ativos = sum(1 for c in self.plano["cortes"] if c["ativo"])
        self.lbl_dur.config(
            text=f"Duração: {tempo_txt(self.plano['dur_original'])}  →  "
            f"{tempo_txt(self.plano['dur_final'])}      (sai {tempo_txt(sai)} em "
            f"{ativos} de {len(self.plano['cortes'])} cortes)"
        )
        ab = self.plano["abertura"]
        linhas = []
        if ab:
            linhas.append(
                f"Abertura: {tempo_txt(ab[0] / float(self.fps))} → "
                f"{tempo_txt((ab[0] + ab[1]) / float(self.fps))} ({ab[1] / float(self.fps):.0f} s), "
                "com fade para preto antes do episódio."
            )
        else:
            linhas.append("Sem abertura.")
        caps, av_caps = capitulos_editados(self.dados, self.plano)
        linhas.append(f"Capítulos: {len(caps)}.  Título: {self.dados.get('titulo') or '(sem título)'}")
        for a in (self.avisos + av_caps)[:4]:
            linhas.append(f"⚠ {a}")
        self.lbl_info.config(text="\n".join(linhas), fg=tema.TEXTO_2)

    def salvar(self):
        gravar_json(self.arq, self.dados)

    # ------------------------------------------------------ acoes
    def sel(self):
        s = self.tree.selection()
        return int(s[0]) if s else None

    def clique(self, ev):
        if self.tree.identify("region", ev.x, ev.y) == "cell" and self.tree.identify_column(ev.x) == "#1":
            linha = self.tree.identify_row(ev.y)
            if linha:
                self.tree.selection_set(linha)
                self.alternar()
                return "break"

    def alternar(self):
        n = self.sel()
        if not n or not self.dados:
            return
        c = self.dados["cortes"][n - 1]
        if c.get("ativo", True) is False:
            c.pop("ativo", None)
        else:
            c["ativo"] = False
        self.salvar()
        self.mostrar()
        self.tree.selection_set(str(n))
        self.tree.see(str(n))

    def pronto(self) -> bool:
        if self.erros or not self.dados or not self.video.exists():
            messagebox.showinfo("Editar vídeo longo", "Corrija o edicao.json primeiro.", parent=self.jan)
            return False
        return True

    def ouvir(self):
        n = self.sel()
        if not n:
            messagebox.showinfo("Ouvir emenda", "Selecione um corte na lista.", parent=self.jan)
            return
        if self.pronto():
            rodar_script("videos_longos.editar_episodio", self.pasta, "--emenda", n)

    def previa(self):
        if self.pronto():
            rodar_script("videos_longos.editar_episodio", self.pasta, "--previa", 600)

    def gerar(self):
        if not self.pronto():
            return
        ep = self.pasta / "episodio"
        existentes = [f for f in ep.glob("*.mp4") if not f.name.startswith("_")] if ep.exists() else []
        if existentes:
            if not messagebox.askyesno(
                "Gerar episódio",
                "Esse vídeo já tem um episódio gerado.\n\n"
                "Gerar de novo? (o atual vai para a pasta episodio\\antigos)",
                parent=self.jan,
            ):
                return
            mover_para_antigos(ep, existentes + [ep / "textos_episodio.txt", ep / "episodio.json"])
        rodar_script("videos_longos.editar_episodio", self.pasta)
        self.studio.atualizar()

    def colar(self):
        if self.studio.colar_edicao(self.info, self.jan):
            self.carregar()

    def abrir_pasta_ep(self):
        ep = self.pasta / "episodio"
        abrir(ep if ep.exists() else self.pasta)
