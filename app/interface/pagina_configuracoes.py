# Tela "Configuracoes": tudo o que vale para o programa inteiro (pasta de trabalho, atualizacoes, legenda,
# musicas, efeitos, o Claude e a publicacao). Antes ficava no botao "Menu" do topo.
import tkinter as tk
from tkinter import ttk

from interface import tema
from interface.utilidades import ARQ_DIRETRIZES, ARQ_GUIA, abrir, abrir_texto, rodar_script
from nucleo.comum import (
    APP_INSTALADO,
    PASTA_CANAL,
    PASTA_CONFIG,
    PASTA_EFEITOS,
    PASTA_MUSICAS,
    ler_ajustes,
    salvar_ajustes,
)
from versao import VERSAO


class PaginaConfiguracoes(tk.Frame):
    def __init__(self, studio, pai):
        super().__init__(pai, bg=tema.FUNDO)
        self.studio = studio
        topo = tema.quadro(self)
        topo.pack(fill="x", padx=tema.ESPACO * 2, pady=(tema.ESPACO * 1.5, tema.ESPACO))
        tema.rotulo(topo, "Configurações", "titulo").pack(side="left")
        tema.rotulo(topo, "   tudo o que vale para o programa inteiro", "secundario").pack(side="left", pady=(8, 0))

        # rolagem: em telas pequenas (1366x768) as secoes nao cabem todas de uma vez
        fundo = tk.Canvas(self, bg=tema.FUNDO, highlightthickness=0)
        barra = ttk.Scrollbar(self, command=fundo.yview)
        fundo.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        fundo.pack(fill="both", expand=True, padx=(tema.ESPACO * 2, 0))
        self.corpo = tema.quadro(fundo)
        janela = fundo.create_window(0, 0, window=self.corpo, anchor="nw")
        self.corpo.bind("<Configure>", lambda e: fundo.configure(scrollregion=fundo.bbox("all")))
        fundo.bind("<Configure>", lambda e: fundo.itemconfigure(janela, width=e.width - tema.ESPACO * 2))
        fundo.bind("<Enter>", lambda e: fundo.bind_all("<MouseWheel>", lambda ev: fundo.yview_scroll(
            int(-ev.delta / 120), "units")))  # fmt: skip
        fundo.bind("<Leave>", lambda e: fundo.unbind_all("<MouseWheel>"))
        self.colunas = tema.quadro(self.corpo)
        self.colunas.pack(fill="both", expand=True)
        self.col_esq = tema.quadro(self.colunas)
        self.col_dir = tema.quadro(self.colunas)
        self.col_esq.pack(side="left", fill="both", expand=True, padx=(0, tema.ESPACO))
        self.col_dir.pack(side="left", fill="both", expand=True)
        self.montar()

    # ---------------------------------------------------------- ajudantes
    def secao(self, coluna, titulo: str, explicacao: str = "") -> tk.Frame:
        c = tema.cartao(coluna, padx=16, pady=14)
        c.pack(fill="x", pady=(0, tema.ESPACO))
        tema.rotulo(c, titulo, "subtitulo", fundo=tema.PAINEL).pack(fill="x")
        if explicacao:
            tema.rotulo(c, explicacao, "secundario", fundo=tema.PAINEL, wraplength=440).pack(fill="x", pady=(2, 8))
        return c

    def botao(self, pai, texto: str, comando, estilo="Extra.TButton"):
        b = ttk.Button(pai, text=texto, command=comando, style=estilo)
        b.pack(fill="x", pady=2)
        return b

    # ---------------------------------------------------------- secoes
    def montar(self):
        st = self.studio
        s = self.secao(self.col_esq, "Pasta de trabalho", f"Vídeos e projetos em produção ficam em:\n{PASTA_CANAL}")
        self.botao(s, "Abrir pasta de trabalho", lambda: st.abrir_pasta_segura(PASTA_CANAL))
        self.botao(s, "Mudar pasta de trabalho...", st.mudar_pasta_trabalho)
        self.botao(s, "Pasta do outro (final dos vídeos longos)", self.abrir_pasta_outro)

        s = self.secao(self.col_esq, "Legenda e Shorts")
        self.botao(s, "Pessoas e cores da legenda", st.pessoas_e_cores)
        self.botao(s, "Máximo de Shorts por vídeo...", st.maximo_de_shorts)
        self.botao(s, "Vocabulário (nomes do canal)", lambda: abrir_texto(PASTA_CONFIG / "vocabulario.txt"))
        self.botao(s, "Correções automáticas", lambda: abrir_texto(PASTA_CONFIG / "correcoes.txt"))
        self.botao(
            s,
            "Marcar câmera e gameplay (formato do Short)",
            lambda: rodar_script("interface.marcar_camera", console=False),
        )
        self.botao(s, "Configurações avançadas (config.json)", lambda: abrir_texto(PASTA_CONFIG / "config.json"))

        s = self.secao(self.col_esq, "Músicas e efeitos sonoros")
        self.botao(s, "Músicas de fundo (por clima)", lambda: st.abrir_pasta_segura(PASTA_MUSICAS))
        self.botao(s, "Efeitos sonoros", lambda: st.abrir_pasta_segura(PASTA_EFEITOS))

        self.montar_claude(self.col_dir)

        s = self.secao(self.col_dir, "Atualizações", f"Você está na versão {VERSAO}.")
        self.botao(s, f"Novidades da versão {VERSAO}", st.novidades)
        self.botao(s, "Procurar atualização", st.atualizar_github)
        self.verificar_ao_abrir = tk.BooleanVar(value=ler_ajustes().get("verificar_atualizacoes", True))
        ttk.Checkbutton(s, text="Verificar atualizações ao abrir", variable=self.verificar_ao_abrir,
                        style="Cartao.TCheckbutton",
                        command=lambda: salvar_ajustes({"verificar_atualizacoes": bool(self.verificar_ao_abrir.get())})
                        ).pack(anchor="w", pady=(4, 0))  # fmt: skip

        s = self.secao(self.col_dir, "Ajuda")
        self.botao(s, "Guia: COMO USAR", lambda: abrir(ARQ_GUIA))
        self.botao(s, "Diretrizes do canal (o que o Claude segue)", lambda: abrir(ARQ_DIRETRIZES))
        if APP_INSTALADO:
            self.botao(s, "Ativar placa de vídeo NVIDIA", st.instalar)
        else:
            self.botao(s, "Atualizar dependências (modo desenvolvedor)", st.instalar)
        ttk.Style(self).configure("Cartao.TCheckbutton", background=tema.PAINEL, foreground=tema.TEXTO)
        ttk.Style(self).map("Cartao.TCheckbutton", background=[("active", tema.PAINEL)])

    def montar_claude(self, coluna):
        """Como o Studio conversa com o Claude no seu computador (publicar e pedir cortes/edicao)."""
        from publicacao import claude_pc

        s = self.secao(coluna, "Claude", "Publicar no YouTube: o Claude agenda pelo YouTube Studio no seu Chrome. "
                       "Nada é publicado sem você revisar e clicar em Confirmar.")  # fmt: skip
        self.modo_claude = tk.StringVar(value=claude_pc.modo_escolhido())
        for codigo, texto in claude_pc.MODOS.items():
            ttk.Radiobutton(s, text=texto, value=codigo, variable=self.modo_claude, style="Cartao.TRadiobutton",
                            command=self.mudou_modo_claude).pack(anchor="w", pady=1)  # fmt: skip
        self.lbl_claude = tk.Label(s, text="", bg=tema.PAINEL, fg=tema.TEXTO_2, font=tema.F_PEQUENA, justify="left",
                                   anchor="w", wraplength=440)  # fmt: skip
        self.lbl_claude.pack(fill="x", pady=(6, 4))
        self.botao(s, "Testar: achar o Claude neste computador", self.testar_claude)
        self.botao(s, "Abrir a pasta dos pacotes de postagem", self.abrir_pasta_publicar)
        estilo = ttk.Style(self)
        estilo.configure("Cartao.TRadiobutton", background=tema.PAINEL, foreground=tema.TEXTO)
        estilo.map("Cartao.TRadiobutton", background=[("active", tema.PAINEL)])

    def mudou_modo_claude(self):
        salvar_ajustes({"publicar_modo": self.modo_claude.get()})
        self.lbl_claude.config(text="")
        if hasattr(self.studio, "pagina_publicacao"):
            self.studio.pagina_publicacao.atualizar_lista()

    def testar_claude(self):
        """Procura o Claude Code e o app do Claude, sem travar a tela, e diz o que achou em portugues."""
        from interface.utilidades import em_segundo_plano
        from publicacao import claude_pc

        self.lbl_claude.config(text="Procurando...", fg=tema.TEXTO_2)

        def procurar():
            caminho = claude_pc.achar_claude_code()
            return caminho, claude_pc.versao_claude_code(caminho) if caminho else None, claude_pc.achar_app_claude()

        def mostrar(r):
            if isinstance(r, Exception):
                self.lbl_claude.config(text=f"Não consegui testar: {r}", fg=tema.VERMELHO)
                return
            caminho, versao, app = r
            linhas = [f"✓ Claude Code: {versao}" if versao else
                      (f"⚠ Achei o Claude Code em {caminho}, mas ele não respondeu." if caminho else
                       "✗ Claude Code não encontrado (instale em claude.com/code, ou use o Cowork)."),
                      "✓ App do Claude (Cowork) encontrado." if app else
                      "✗ App do Claude não encontrado (o Studio abre o Claude no navegador)."]  # fmt: skip
            linhas.append("Lembre: o Claude Code precisa do Claude in Chrome instalado no Chrome para publicar.")
            ok = bool(versao) or bool(app)
            self.lbl_claude.config(text="\n".join(linhas), fg=tema.VERDE if ok else tema.AMARELO)

        em_segundo_plano(self, procurar, mostrar)

    def abrir_pasta_publicar(self):
        from nucleo.comum import PASTA_PUBLICAR

        self.studio.abrir_pasta_segura(PASTA_PUBLICAR)

    def abrir_pasta_outro(self):
        from nucleo.comum import PASTA_OUTRO, preparar_pasta_outro

        preparar_pasta_outro()
        self.studio.abrir_pasta_segura(PASTA_OUTRO)
