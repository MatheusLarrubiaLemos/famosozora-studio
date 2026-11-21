# Janela de revisao do video longo: o que o Claude marcou para SAIR, numa linha do tempo e numa lista.
# Em cima, o player embutido (interface/player.py) com o video original: com "Pular o que sai" ligado, ele toca
# como o episodio vai ficar (pula os trechos do Claude e as pausas). Clicar num trecho leva o video para logo
# antes dele; clicar na linha do tempo leva para aquele ponto. Botoes do player: "Inicio aqui" / "Fim aqui"
# ajustam o trecho selecionado no ponto do video (corte exato, sem procurar silencio); I e O marcam um corte
# novo (de I ate O).
# Botao direito num trecho (na lista ou na linha do tempo): assistir o trecho que sai, ver a emenda (como fica),
# "Manter este trecho" ou "Remover". Os capitulos aparecem na linha do tempo e vao para a descricao.
# Embaixo: incluir o outro no final (pasta outro\), gerar previa, gerar o episodio e publicar.
# Sem o player (falta o mpv), ouvir/assistir corta o trecho com o ffmpeg e abre no player do Windows, como antes.
import subprocess
import tkinter as tk
from tkinter import messagebox, ttk

from interface import tema
from interface.menus import ligar_botao_direito, montar_menu
from interface.player import Player
from interface.utilidades import COR_FUNDO, COR_TEXTO, abrir, em_segundo_plano, rodar_script
from nucleo import reproducao
from nucleo.comum import DADOS_APP, carregar_config, ler_json, ler_tempo, mover_para_antigos, tempo_txt
from videos_longos import pausas


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
        self.mantidos = []  # o que fica no episodio, em segundos do video original (para o player pular o resto)
        self.marca_inicio = None  # tecla I: comeco de um corte novo

        self.jan = tk.Toplevel(studio.raiz)
        self.jan.title(f"Editar vídeo longo - {info['nome']}")
        largura, altura = self.jan.winfo_screenwidth(), self.jan.winfo_screenheight()
        self.jan.geometry(f"{min(1180, largura - 40)}x{min(900, altura - 90)}+20+10")
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

        # ---- player (video original)
        self.player = Player(self.jan, altura=150, ao_tempo=self.no_tempo)
        self.player.pack(fill="both", expand=True, padx=16, pady=(0, 6))
        self._montar_extras_do_player()

        # ---- linha do tempo
        self.linha = tk.Canvas(self.jan, height=58, bg=COR_FUNDO, highlightthickness=0)
        self.linha.pack(fill="x", padx=16)
        self.linha.bind("<Configure>", lambda e: self.desenhar_linha())
        self.linha.bind("<Button-1>", self.clique_na_linha)
        self.linha.bind("<B1-Motion>", self.arrastar_na_linha)
        ligar_botao_direito(self.linha, self.menu_na_linha)
        legenda = tk.Frame(self.jan, bg=COR_FUNDO)
        legenda.pack(fill="x", padx=16, pady=(2, 6))
        tema.rotulo(legenda, "laranja = sai   ·   cinza = você mandou manter   ·   | = capítulo   ·   clique = leva o "
                    "vídeo para lá   ·   botão direito num trecho = mais opções", "pequeno").pack(side="left")  # fmt: skip
        self.lbl_agora = tk.Label(legenda, text="", bg=COR_FUNDO, fg=tema.TEXTO_2, font=tema.F_SECAO, anchor="e")
        self.lbl_agora.pack(side="right")

        meio = tk.Frame(self.jan, bg=COR_FUNDO)
        meio.pack(fill="both", expand=True, padx=16)
        cols = ("sai", "inicio", "fim", "dur", "motivo", "aviso")
        self.tree = ttk.Treeview(meio, columns=cols, show="headings", selectmode="browse", height=3)
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
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.selecionou())
        ligar_botao_direito(self.tree, self.menu_do_trecho)
        tema.rotulo(self.jan, "Caixinha (ou Espaço) = manter/remover o trecho. Duplo clique = assistir o trecho que sai. "
                    "Player: K = tocar/pausar · J/L = 5 s · vírgula/ponto = quadro · I/O = novo corte",
                    "pequeno").pack(fill="x", padx=16, pady=(4, 0))  # fmt: skip

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
        pausas_linha = tk.Frame(self.jan, bg=COR_FUNDO)
        pausas_linha.pack(fill="x", padx=16, pady=(6, 0))
        self.cortar_pausas = tk.BooleanVar(value=True)
        ttk.Checkbutton(pausas_linha, text="Cortar as pausas sem fala (fica 3 s antes de você voltar a falar e os "
                        "momentos de ação do jogo)", variable=self.cortar_pausas,
                        command=self.mudou_pausas).pack(side="left")  # fmt: skip
        self.lbl_pausas = tk.Label(pausas_linha, text="", bg=COR_FUNDO, fg=tema.TEXTO_2, font=tema.F_TEXTO)
        self.lbl_pausas.pack(side="left", padx=10)

        bot = tk.Frame(self.jan, bg=COR_FUNDO)
        bot.pack(fill="x", padx=16, pady=10)
        ttk.Button(bot, text="Gerar prévia (10 min)", style="Extra.TButton", command=self.previa).pack(side="left")
        self.btn_mais = ttk.Button(bot, text="Mais opções ▾", style="Extra.TButton", command=self.mais_opcoes)
        self.btn_mais.pack(side="left", padx=6)
        ttk.Button(bot, text="Gerar episódio", style="Passo.TButton", command=self.gerar).pack(side="right")
        self.btn_publicar = ttk.Button(bot, text="Publicar", style="Extra.TButton", command=self.publicar)
        self.btn_publicar.pack(side="right", padx=6)
        self.player.ligar_atalhos(self.jan)
        for tecla in ("<i>", "<I>"):
            self.jan.bind(tecla, self._tecla(self.marcar_inicio_novo), add="+")
        for tecla in ("<o>", "<O>"):
            self.jan.bind(tecla, self._tecla(self.marcar_fim_novo), add="+")
        self.carregar()
        if self.video.exists():
            self.player.abrir(self.video)

    def _montar_extras_do_player(self):
        """Botoes desta tela na linha de controles do player."""
        ex = self.player.extras
        self.pular_o_que_sai = tk.BooleanVar(value=True)
        ttk.Checkbutton(ex, text="Pular o que sai (ver como fica)", variable=self.pular_o_que_sai,
                        command=self.mudou_pular).pack(side="left")  # fmt: skip
        for texto, comando in (("[ Início aqui", lambda: self.ajustar_trecho("inicio")),
                               ("Fim aqui ]", lambda: self.ajustar_trecho("fim")),
                               ("✂ Novo corte (I/O)", self.marcar_inicio_novo)):  # fmt: skip
            ttk.Button(ex, text=texto, style="Player.TButton", command=comando).pack(side="left", padx=(6, 0))

    def _tecla(self, funcao):
        def rodar(evento):
            if isinstance(evento.widget, (tk.Entry, ttk.Entry, tk.Text, ttk.Combobox)) or not self.player.pronto:
                return None
            funcao()
            return "break"

        return rodar

    # ------------------------------------------------------ dados
    def carregar(self):
        from videos_longos.pedido_edicao import ler_edicao

        self.dados, self.erros, self.avisos = ler_edicao(self.pasta, self.dur)
        if self.dados:
            self.incluir_outro.set(self.dados.get("incluir_outro", True) is not False)
            self.cortar_pausas.set(pausas.ligado(carregar_config(), self.dados))
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
        cfg = carregar_config()
        self.plano = montar_plano(self.dados, self.dur, self.fps, self.palavras, cfg, acao=self.momentos_de_acao(cfg))
        self.mantidos = reproducao.mantidos_do_plano(self.plano)
        self.mudou_pular()
        p = self.plano["pausas"]
        self.lbl_pausas.config(text=(f"{p['n']} pausas, {tempo_txt(p['segundos'])} a menos" if p["n"] else
                                     ("nenhuma pausa longa" if self.cortar_pausas.get() else "")))  # fmt: skip
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

    def momentos_de_acao(self, cfg):
        """Momentos de acao do jogo, se o som ja foi medido (o "Gerar" mede; aqui nao trava a tela medindo)."""
        from nucleo.comum import ler_json as ler

        atividade = ler(self.pasta / "atividade.json", None)
        if not isinstance(atividade, dict) or atividade.get("video") != str(self.video):
            return None
        return pausas.momentos_de_acao(atividade, pausas.ajuste(cfg, "episodio_acao_sensibilidade"))

    def mudou_pausas(self):
        """Liga/desliga o corte das pausas so neste video (fica no edicao.json)."""
        if not self.dados:
            return
        if self.cortar_pausas.get():
            self.dados.pop("cortar_pausas", None)
        else:
            self.dados["cortar_pausas"] = False
        self.salvar()
        self.mostrar()

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
        if self.marca_inicio is not None:
            cv.create_line(x(self.marca_inicio), 10, x(self.marca_inicio), 50, fill=tema.AMARELO, width=2)
            cv.create_text(x(self.marca_inicio) + 3, 46, text="I", anchor="sw", fill=tema.AMARELO, font=tema.F_SECAO)
        cv.create_line(0, 10, 0, 50, fill=tema.TEXTO, width=2, tags=("cabeca",))
        self.mover_cabeca(self.player.tempo())

    def mover_cabeca(self, t: float):
        """Risco branco na linha do tempo: onde o player esta."""
        if not self.dur:
            return
        largura = max(10, self.linha.winfo_width() - 2)
        xx = 1 + (largura - 1) * max(0.0, min(1.0, t / self.dur))
        self.linha.coords("cabeca", xx, 10, xx, 50)

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

    def tempo_no_ponto(self, x: int) -> float:
        largura = max(10, self.linha.winfo_width() - 2)
        return max(0.0, min(1.0, (x - 1) / (largura - 1))) * (self.dur or 0)

    def clique_na_linha(self, evento):
        """Clique num trecho: seleciona e leva o video para logo antes dele. Fora dos trechos: leva para o ponto."""
        n = self.trecho_no_ponto(evento.x)
        if n:
            self.tree.selection_set(str(n))
            self.tree.see(str(n))
        else:
            self.player.ir(self.tempo_no_ponto(evento.x), exato=False)

    def arrastar_na_linha(self, evento):
        self.player.ir(self.tempo_no_ponto(evento.x), exato=False)

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
            ("▶  Assistir o trecho que sai", self.ouvir_trecho),
            ("▶  Ver a emenda (como fica)", self.ouvir),
            None,
            ("✓  Manter este trecho (não sai)", self.alternar if ativo else None),
            ("✂  Remover este trecho", self.alternar if not ativo else None),
            None,
            ("[  Início deste trecho = onde o vídeo está", lambda: self.ajustar_trecho("inicio")),
            ("]  Fim deste trecho = onde o vídeo está", lambda: self.ajustar_trecho("fim")),
            ("🗑  Apagar este trecho da lista", self.apagar_trecho),
        ]

    def mais_opcoes(self):
        menu = montar_menu(self.jan, [
            ("▶  Ver a emenda do trecho selecionado", self.ouvir),
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
        """Ver a emenda: no player, 5 s antes do trecho ate 5 s depois, pulando o que sai (como fica no episodio).
        Sem o player: monta a emenda com o editar_episodio (janela preta) como antes."""
        n = self.sel()
        if not n:
            messagebox.showinfo("Ver emenda", "Selecione um trecho na lista.", parent=self.jan)
            return
        if not self.pronto():
            return
        if self.player.pronto and self.plano:
            c = self.plano["cortes"][n - 1]
            self.pular_o_que_sai.set(True)
            self.mudou_pular()
            self.player.tocar(max(0.0, c["ini_aj"] - 5), c["fim_aj"] + 5)
            return
        rodar_script("videos_longos.editar_episodio", self.pasta, "--emenda", n)

    def ouvir_trecho(self):
        """Assistir o trecho que sai: no player, do comeco ao fim do trecho (sem pular nada).
        Sem o player: corta o trecho (ate 60 s) com o ffmpeg e abre no player do Windows, sem travar a tela."""
        n = self.sel()
        if not n or not self.plano or not self.pronto():
            return
        c = self.plano["cortes"][n - 1]
        if self.player.pronto:
            self.player.tocar(c["ini_aj"], c["fim_aj"], pulando=False)
            return
        from nucleo.video import achar_programa

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

    # ------------------------------------------------------ player
    def selecionou(self):
        """Trecho escolhido na lista (ou na linha do tempo): o video vai para 3 s antes dele."""
        self.desenhar_linha()
        n = self.sel()
        if n and self.plano and not self.player.tocando:
            self.player.ir(max(0.0, self.plano["cortes"][n - 1]["ini_aj"] - 3))

    def mudou_pular(self):
        """Liga/desliga o "pular o que sai" do player e pinta na barra do player o que sai."""
        ligado = self.pular_o_que_sai.get() and bool(self.mantidos)
        self.player.pular = (lambda t: reproducao.pulo(t, self.mantidos)) if ligado else None
        faixas = []
        if self.plano:
            fim_anterior = 0.0
            for a, b in self.mantidos:  # o que nao fica: pausas (cinza) e trechos do Claude (laranja, por cima)
                if a > fim_anterior:
                    faixas.append((fim_anterior, a, tema.BOTAO_HOVER))
                fim_anterior = b
            faixas += [(c["ini_aj"], c["fim_aj"], tema.LARANJA) for c in self.plano["cortes"] if c["ativo"]]
        self.player.faixas = faixas
        self.player.desenhar_barra()

    def no_tempo(self, t: float):
        """Chamado pelo player varias vezes por segundo: move o risco da linha do tempo e diz o que acontece ali."""
        self.mover_cabeca(t)
        if not self.plano:
            return
        estado, n = reproducao.situacao(t, self.plano["cortes"], self.mantidos)
        texto, cor = {"sai": (f"✂ aqui SAI (trecho {n})", tema.LARANJA), "pausa": ("pausa cortada", tema.TEXTO_2),
                      "fica": ("● fica no episódio", tema.VERDE)}[estado]  # fmt: skip
        if self.marca_inicio is not None:
            texto = f"I = {reproducao.texto_do_tempo(self.marca_inicio)} (aperte O no fim)   " + texto
        if self.lbl_agora.cget("text") != texto:
            self.lbl_agora.config(text=texto, fg=cor)

    def _sem_player(self) -> bool:
        if self.player.pronto and self.dados and not self.erros:
            return False
        messagebox.showinfo("Player", "Precisa do player embutido e de um edicao.json sem problemas.", parent=self.jan)
        return True

    def ajustar_trecho(self, borda: str):
        """Inicio (ou fim) do trecho selecionado = onde o video esta. O trecho fica "exato": o programa nao muda
        mais a borda para o silencio mais perto (voce escolheu o ponto vendo o video)."""
        from videos_longos.pedido_edicao import fmt_tempo

        n = self.sel()
        if self._sem_player():
            return
        if not n:
            messagebox.showinfo("Ajustar trecho", "Selecione um trecho na lista primeiro.", parent=self.jan)
            return
        t = self.player.tempo()
        c, p = self.dados["cortes"][n - 1], self.plano["cortes"][n - 1]
        ini, fim = (t, p["fim_aj"]) if borda == "inicio" else (p["ini_aj"], t)
        if fim - ini < 0.2:
            messagebox.showinfo("Ajustar trecho", "O início precisa ficar antes do fim. Leve o vídeo para outro ponto.",
                                parent=self.jan)  # fmt: skip
            return
        c["inicio"], c["fim"], c["exato"] = fmt_tempo(ini), fmt_tempo(fim), True
        self._gravar_e_selecionar(ini)
        self.studio.notificar(f"Trecho ajustado: {fmt_tempo(ini)} → {fmt_tempo(fim)}", "ok", 3)

    def marcar_inicio_novo(self):
        """Tecla I: o corte novo comeca onde o video esta."""
        if self._sem_player():
            return
        self.marca_inicio = self.player.tempo()
        self.player.marcas = [(self.marca_inicio, tema.AMARELO)]
        self.player.desenhar_barra()
        self.desenhar_linha()
        self.no_tempo(self.marca_inicio)

    def marcar_fim_novo(self):
        """Tecla O: cria o corte de I ate onde o video esta (motivo "cortado à mão")."""
        from videos_longos.pedido_edicao import fmt_tempo

        if self._sem_player():
            return
        if self.marca_inicio is None:
            messagebox.showinfo("Novo corte", "Primeiro aperte I (ou o botão ✂ Novo corte) no começo do que sai.",
                                parent=self.jan)  # fmt: skip
            return
        ini, fim = sorted((self.marca_inicio, self.player.tempo()))
        if fim - ini < 0.2:
            messagebox.showinfo("Novo corte", "Leve o vídeo até o FIM do que sai e aperte O.", parent=self.jan)
            return
        self.marca_inicio = None
        self.player.marcas = []
        self.dados["cortes"].append({"inicio": fmt_tempo(ini), "fim": fmt_tempo(fim), "motivo": "cortado à mão",
                                     "exato": True})  # fmt: skip
        self._gravar_e_selecionar(ini)
        self.studio.notificar(f"Corte novo: {fmt_tempo(ini)} → {fmt_tempo(fim)}", "ok", 3)

    def apagar_trecho(self):
        """Tira o trecho da lista de vez (diferente de "Manter", que deixa ele na lista desmarcado)."""
        n = self.sel()
        if not n or not self.dados:
            return
        c = self.dados["cortes"][n - 1]
        if not messagebox.askyesno("Apagar trecho", f"Apagar da lista o trecho {c['inicio']} → {c['fim']}?\n\n"
                                   "Ele deixa de sair do episódio.", parent=self.jan):  # fmt: skip
            return
        self.dados["cortes"].pop(n - 1)
        self.salvar()
        self.carregar()

    def _gravar_e_selecionar(self, inicio: float):
        """Grava o edicao.json, rele (a lista volta em ordem) e seleciona o trecho que comeca em 'inicio'."""
        self.salvar()
        self.carregar()
        if self.plano:
            perto = min(self.plano["cortes"], key=lambda c: abs(c["inicio"] - inicio), default=None)
            if perto:
                self.tree.selection_set(str(perto["n"]))
                self.tree.see(str(perto["n"]))

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
