# Janela de revisao do video longo: o que o Claude marcou para SAIR, numa linha do tempo e numa lista.
# Botao direito num trecho (na lista ou na linha do tempo): ouvir o trecho que sai, ouvir a emenda (como fica),
# "Manter este trecho" ou "Remover". Os capitulos aparecem na linha do tempo e vao para a descricao.
# Embaixo: incluir o outro no final (pasta outro\), gerar previa, gerar o episodio e publicar.
import subprocess
import tkinter as tk
from tkinter import messagebox, ttk

from interface import tema
from interface.menus import ligar_botao_direito, montar_menu
from interface.utilidades import COR_FUNDO, COR_TEXTO, abrir, em_segundo_plano, rodar_script
from nucleo.comum import DADOS_APP, carregar_config, ler_json, ler_tempo, mover_para_antigos, tempo_txt


class JanelaEdicao:
    """Revisao do edicao.json: o que SAI, caixinha para desmarcar, ouvir, outro, previa, gerar e publicar."""

    def __init__(self, studio, info: dict):
        from videos_longos.pedido_edicao import carregar_palavras, fps_fracao, info_video

        self.studio = studio
        self.info = info
        self.pasta = info["pasta"]
        self.arq = self.pasta / "edicao.json"
        self.video, self.dur = info_video(self.pasta)
        self.fps = fps_fracao(self.video) if self.video.exists() else None
        self.palavras = carregar_palavras(self.pasta)
        self.plano = None

        self.jan = tk.Toplevel(studio.raiz)
        self.jan.title(f"Editar vídeo longo - {info['nome']}")
        largura, altura = self.jan.winfo_screenwidth(), self.jan.winfo_screenheight()
        self.jan.geometry(f"{min(1180, largura - 40)}x{min(760, altura - 90)}+20+10")
        self.jan.configure(bg=COR_FUNDO)

        topo = tk.Frame(self.jan, bg=COR_FUNDO)
        topo.pack(fill="x", padx=16, pady=(12, 2))
        tema.rotulo(topo, "Revisar a edição do vídeo longo", "titulo").pack(side="left")
        self.lbl_dur = tk.Label(self.jan, text="", bg=COR_FUNDO, fg=COR_TEXTO, font=(tema.FONTE, 13, "bold"),
                                anchor="w")  # fmt: skip
        self.lbl_dur.pack(fill="x", padx=16)
        self.lbl_info = tk.Label(self.jan, text="", bg=COR_FUNDO, fg=tema.TEXTO_2, font=tema.F_TEXTO, anchor="w",
                                 justify="left", wraplength=1080)  # fmt: skip
        self.lbl_info.pack(fill="x", padx=16, pady=(2, 6))

        # ---- linha do tempo
        self.linha = tk.Canvas(self.jan, height=58, bg=COR_FUNDO, highlightthickness=0)
        self.linha.pack(fill="x", padx=16)
        self.linha.bind("<Configure>", lambda e: self.desenhar_linha())
        self.linha.bind("<Button-1>", self.clique_na_linha)
        ligar_botao_direito(self.linha, self.menu_na_linha)
        tema.rotulo(self.jan, "laranja = sai do episódio   ·   cinza = você mandou manter   ·   | = capítulo   ·   "
                    "clique num trecho para achar na lista; botão direito para mais opções", "pequeno").pack(
            fill="x", padx=16, pady=(2, 6))  # fmt: skip

        meio = tk.Frame(self.jan, bg=COR_FUNDO)
        meio.pack(fill="both", expand=True, padx=16)
        cols = ("sai", "inicio", "fim", "dur", "motivo", "aviso")
        self.tree = ttk.Treeview(meio, columns=cols, show="headings", selectmode="browse", height=6)
        for col, txt, w, anc in [("sai", "Sai?", 50, "center"), ("inicio", "Início", 90, "center"),
                                 ("fim", "Fim", 90, "center"), ("dur", "Duração", 80, "center"),
                                 ("motivo", "Motivo (o que sai)", 600, "w"), ("aviso", "Aviso", 150, "w")]:  # fmt: skip
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
        self.tree.bind("<Double-1>", lambda e: self.ouvir_trecho())
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.desenhar_linha())
        ligar_botao_direito(self.tree, self.menu_do_trecho)
        tema.rotulo(self.jan, "Caixinha (ou Espaço) = manter/remover o trecho. Duplo clique = ouvir o trecho que sai. "
                    "Botão direito = mais opções.", "pequeno").pack(fill="x", padx=16, pady=(4, 0))  # fmt: skip

        # ---- outro
        outro = tk.Frame(self.jan, bg=COR_FUNDO)
        outro.pack(fill="x", padx=16, pady=(8, 0))
        self.incluir_outro = tk.BooleanVar(value=True)
        ttk.Checkbutton(outro, text="Incluir o outro no final", variable=self.incluir_outro,
                        command=self.mudou_outro).pack(side="left")  # fmt: skip
        self.lbl_outro = tk.Label(outro, text="", bg=COR_FUNDO, fg=tema.TEXTO_2, font=tema.F_TEXTO, anchor="w")
        self.lbl_outro.pack(side="left", padx=10)
        ttk.Button(outro, text="Pasta do outro", style="Extra.TButton", command=self.abrir_pasta_outro).pack(
            side="right"
        )
        tema.rotulo(self.jan, "Dica: o outro precisa ter de 5 a 20 segundos para dar para pôr a tela final do YouTube "
                    "(vídeos e botão de inscrever).", "pequeno").pack(fill="x", padx=16)  # fmt: skip

        bot = tk.Frame(self.jan, bg=COR_FUNDO)
        bot.pack(fill="x", padx=16, pady=10)
        ttk.Button(bot, text="Gerar prévia (10 min)", style="Extra.TButton", command=self.previa).pack(side="left")
        self.btn_mais = ttk.Button(bot, text="Mais opções ▾", style="Extra.TButton", command=self.mais_opcoes)
        self.btn_mais.pack(side="left", padx=6)
        ttk.Button(bot, text="Gerar episódio", style="Passo.TButton", command=self.gerar).pack(side="right")
        self.btn_publicar = ttk.Button(bot, text="Publicar", style="Extra.TButton", command=self.publicar)
        self.btn_publicar.pack(side="right", padx=6)
        self.carregar()

    # ------------------------------------------------------ dados
    def carregar(self):
        from videos_longos.pedido_edicao import ler_edicao

        self.dados, self.erros, self.avisos = ler_edicao(self.pasta, self.dur)
        if self.dados:
            self.incluir_outro.set(self.dados.get("incluir_outro", True) is not False)
        self.mostrar()

    def mostrar(self):
        from videos_longos.pedido_edicao import CORTE_CURTO, capitulos_editados, montar_plano

        self.tree.delete(*self.tree.get_children())
        self.mostrar_outro()
        self.btn_publicar.config(state="normal" if self.episodio() else "disabled")
        if self.erros or not self.dados:
            self.plano = None
            self.lbl_dur.config(text="O edicao.json tem problemas")
            self.lbl_info.config(text="- " + "\n- ".join(self.erros[:8]) + '\nPeça pro Claude corrigir (Mais opções > '
                                 "Pedir de novo ao Claude).", fg=tema.VERMELHO)  # fmt: skip
            self.desenhar_linha()
            return
        if not self.video.exists():
            self.plano = None
            self.lbl_dur.config(text="Não achei o vídeo original")
            self.lbl_info.config(text=str(self.video), fg=tema.VERMELHO)
            self.desenhar_linha()
            return
        self.plano = montar_plano(self.dados, self.dur, self.fps, self.palavras, carregar_config())
        for c in self.plano["cortes"]:
            curto = c["dur"] < CORTE_CURTO
            tags = ("off",) if not c["ativo"] else (("curto",) if curto else ())
            self.tree.insert("", "end", iid=str(c["n"]), tags=tags, values=(
                "☑" if c["ativo"] else "☐", tempo_txt(c["ini_aj"]), tempo_txt(c["fim_aj"]),
                f"{c['dur'] / 60:.0f} min" if c["dur"] >= 120 else f"{c['dur']:.0f} s", c["motivo"],
                "⚠ menos de 30 s" if curto else ""))  # fmt: skip
        sai = self.plano["dur_original"] - self.plano["dur_final"]
        ativos = sum(1 for c in self.plano["cortes"] if c["ativo"])
        self.lbl_dur.config(text=f"Duração: {tempo_txt(self.plano['dur_original'])}  →  "
                            f"{tempo_txt(self.plano['dur_final'])}      (sai {tempo_txt(sai)} em "
                            f"{ativos} de {len(self.plano['cortes'])} trechos)")  # fmt: skip
        caps, av_caps = capitulos_editados(self.dados, self.plano)
        linhas = ["Sem gancho: o episódio começa do começo, com a intro. Cada emenda tem uma transição curta.",
                  f"Capítulos: {len(caps)} (vão para a descrição).  Título: {self.dados.get('titulo') or '(sem título)'}"]  # fmt: skip
        for a in (self.avisos + av_caps)[:4]:
            linhas.append(f"⚠ {a}")
        self.lbl_info.config(text="\n".join(linhas), fg=tema.TEXTO_2)
        self.desenhar_linha()

    def salvar(self):
        from videos_longos.pedido_edicao import gravar_edicao

        gravar_edicao(self.arq, self.dados)

    def episodio(self):
        """O episodio ja gerado (arquivo .mp4), ou None."""
        ep = self.pasta / "episodio"
        nome = (ler_json(ep / "episodio.json", {}) or {}).get("arquivo")
        arq = ep / nome if nome else None
        return arq if arq and arq.exists() else None

    # ------------------------------------------------------ linha do tempo
    def desenhar_linha(self):
        cv = self.linha
        cv.delete("all")
        largura = max(10, cv.winfo_width() - 2)
        cv.create_rectangle(1, 14, largura, 46, fill=tema.PAINEL, outline=tema.BORDA)
        if not self.plano or not self.dur:
            return
        x = lambda t: 1 + (largura - 1) * max(0.0, min(1.0, t / self.dur))  # noqa: E731
        sel = self.sel()
        for c in self.plano["cortes"]:
            cor = tema.LARANJA if c["ativo"] else tema.BOTAO_HOVER
            borda = tema.TEXTO if c["n"] == sel else cor
            cv.create_rectangle(x(c["ini_aj"]), 15, max(x(c["fim_aj"]), x(c["ini_aj"]) + 2), 45, fill=cor,
                                outline=borda, width=2 if c["n"] == sel else 1, tags=(f"trecho{c['n']}",))  # fmt: skip
        for c in self.dados.get("capitulos", []) if self.dados else []:
            try:
                t = ler_tempo(c["inicio"])
            except (KeyError, TypeError, ValueError):
                continue
            cv.create_line(x(t), 6, x(t), 52, fill=tema.TEXTO_2)
            cv.create_text(x(t) + 3, 6, text=str(c.get("titulo", ""))[:18], anchor="nw", fill=tema.TEXTO_2,
                           font=tema.F_PEQUENA)  # fmt: skip
        cv.create_text(2, 56, text="0:00", anchor="sw", fill=tema.TEXTO_2, font=tema.F_PEQUENA)
        cv.create_text(largura, 56, text=tempo_txt(self.dur), anchor="se", fill=tema.TEXTO_2, font=tema.F_PEQUENA)

    def trecho_no_ponto(self, x: int):
        if not self.plano or not self.dur:
            return None
        largura = max(10, self.linha.winfo_width() - 2)
        t = (x - 1) / (largura - 1) * self.dur
        folga = self.dur * 4 / largura  # alguns pixels de folga para trecho fininho
        for c in self.plano["cortes"]:
            if c["ini_aj"] - folga <= t <= c["fim_aj"] + folga:
                return c["n"]
        return None

    def clique_na_linha(self, evento):
        n = self.trecho_no_ponto(evento.x)
        if n:
            self.tree.selection_set(str(n))
            self.tree.see(str(n))

    def menu_na_linha(self, evento):
        n = self.trecho_no_ponto(evento.x)
        if not n:
            return None
        self.tree.selection_set(str(n))
        self.tree.see(str(n))
        return montar_menu(self.jan, self.itens_do_trecho(n))

    # ------------------------------------------------------ botao direito
    def menu_do_trecho(self, evento):
        linha = self.tree.identify_row(evento.y)
        if not linha:
            return None
        self.tree.selection_set(linha)
        return montar_menu(self.jan, self.itens_do_trecho(int(linha)))

    def itens_do_trecho(self, n: int) -> list:
        ativo = self.dados["cortes"][n - 1].get("ativo", True) is not False if self.dados else True
        return [
            ("▶  Ouvir o trecho que sai", self.ouvir_trecho),
            ("▶  Ouvir a emenda (como fica)", self.ouvir),
            None,
            ("✓  Manter este trecho (não sai)", self.alternar if ativo else None),
            ("✂  Remover este trecho", self.alternar if not ativo else None),
        ]

    def mais_opcoes(self):
        menu = montar_menu(self.jan, [
            ("▶  Ouvir a emenda do trecho selecionado", self.ouvir),
            None,
            ("🔁  Pedir de novo ao Claude", self.pedir_de_novo),
            ("📋  Colar edicao.json", self.colar),
            None,
            ("📁  Abrir pasta do episódio", self.abrir_pasta_ep),
        ])  # fmt: skip
        menu.tk_popup(self.btn_mais.winfo_rootx(), self.btn_mais.winfo_rooty() + self.btn_mais.winfo_height())
        menu.grab_release()

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
        return None

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
            messagebox.showinfo("Ouvir emenda", "Selecione um trecho na lista.", parent=self.jan)
            return
        if self.pronto():
            rodar_script("videos_longos.editar_episodio", self.pasta, "--emenda", n)

    def ouvir_trecho(self):
        """Corta o trecho que sai (ate 60 s) do video original e abre no player, sem travar a tela."""
        n = self.sel()
        if not n or not self.plano or not self.pronto():
            return
        from nucleo.video import achar_programa

        c = self.plano["cortes"][n - 1]
        saida = DADOS_APP / "temp" / f"trecho_que_sai_{n:03d}.mp4"
        saida.parent.mkdir(parents=True, exist_ok=True)
        dur = min(60.0, c["dur"])
        comando = [achar_programa("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{c['ini_aj']:.3f}",
                   "-t", f"{dur:.3f}", "-i", str(self.video), "-map", "0:v:0", "-map", "0:a:0?", "-vf", "scale=-2:540",
                   "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28", "-c:a", "aac", str(saida)]  # fmt: skip
        self.studio.notificar("Preparando o trecho" + (" (o primeiro minuto)" if c["dur"] > 60 else "") + "...",
                              "info", 3)  # fmt: skip

        def cortar():
            return subprocess.run(
                comando, capture_output=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )

        def pronto(r):
            if isinstance(r, Exception) or r.returncode != 0 or not saida.exists():
                messagebox.showerror("Ouvir trecho", "Não consegui montar o trecho.", parent=self.jan)
                return
            abrir(saida)

        em_segundo_plano(self.jan, cortar, pronto)

    def previa(self):
        if self.pronto():
            rodar_script("videos_longos.editar_episodio", self.pasta, "--previa", 600)

    def gerar(self):
        if not self.pronto():
            return
        ep = self.pasta / "episodio"
        existentes = [f for f in ep.glob("*.mp4") if not f.name.startswith("_")] if ep.exists() else []
        if existentes:
            if not messagebox.askyesno("Gerar episódio", "Esse vídeo já tem um episódio gerado.\n\n"
                                       "Gerar de novo? (o atual vai para a pasta episodio\\antigos)",
                                       parent=self.jan):  # fmt: skip
                return
            mover_para_antigos(ep, existentes + [ep / "textos_episodio.txt", ep / "episodio.json"])
        rodar_script("videos_longos.editar_episodio", self.pasta)
        self.studio.notificar("Gerando o episódio na janela preta que abriu. Quando terminar, clique em Publicar.",
                              "info", 7)  # fmt: skip
        self.studio.atualizar()

    def publicar(self):
        if not self.episodio():
            messagebox.showinfo("Publicar", "Gere o episódio antes de publicar.", parent=self.jan)
            return
        self.studio.publicar_longo(self.info, parent=self.jan)

    # ------------------------------------------------------ outro
    def mostrar_outro(self):
        from videos_longos.outro import situacao

        _, _, texto, ok = situacao(self.incluir_outro.get())
        self.lbl_outro.config(text=texto, fg=tema.TEXTO_2 if ok else tema.AMARELO)

    def mudou_outro(self):
        if self.dados:
            if self.incluir_outro.get():
                self.dados.pop("incluir_outro", None)
            else:
                self.dados["incluir_outro"] = False
            self.salvar()
        self.mostrar_outro()

    def abrir_pasta_outro(self):
        from nucleo.comum import PASTA_OUTRO, preparar_pasta_outro

        preparar_pasta_outro()
        abrir(PASTA_OUTRO)

    # ------------------------------------------------------ outras
    def pedir_de_novo(self):
        self.jan.destroy()
        self.studio.aba_longos.tree.selection_set(self.info["nome"])
        self.studio.aba_longos.editar_com_claude()

    def colar(self):
        if self.studio.colar_edicao(self.info, self.jan):
            self.carregar()

    def abrir_pasta_ep(self):
        ep = self.pasta / "episodio"
        abrir(ep if ep.exists() else self.pasta)
