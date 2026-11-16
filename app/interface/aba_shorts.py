# Aba "Shorts": transcrever, marcar camera, pedir os cortes ao Claude, gerar os Shorts,
# revisar as legendas e publicar.
from tkinter import messagebox, simpledialog

from interface.aba_base import AbaProjetos
from interface.editor_legendas import EditorLegendas
from interface.utilidades import ARQ_DIRETRIZES, rodar_script
from nucleo.comum import carregar_config, gravar_json, ler_json, mover_para_antigos

STATUS = {"transcrever": "Falta transcrever", "cortes": "Falta escolher os cortes", "gerar": "Falta gerar os Shorts",
          "revisar": "Revisar e publicar", "pronto": "✓ Tudo publicado"}  # fmt: skip


class AbaShorts(AbaProjetos):
    TITULO = "Shorts"
    SUBTITULO = "da live aos Shorts: transcrever, escolher os cortes, gerar, revisar e publicar"
    COLUNAS = [("shorts", "Shorts", 70), ("postados", "Publicados", 90), ("status", "Status", 170)]
    PASSOS = {"transcrever": ("Transcrever o vídeo", "transcrever_selecionado"),
              "cortes": ("Gerar cortes com o Claude", "pedir_cortes"),
              "gerar": ("Gerar os Shorts", "gerar"),
              "revisar": ("Revisar os Shorts", "revisar_legendas"),
              "pronto": ("Abrir a pasta dos Shorts", "abrir_pasta")}  # fmt: skip

    def montar_botoes(self):
        self.secao("PASSO A PASSO")
        self.botao("1   Transcrever vídeo novo", self.transcrever)
        self.botao("2   Gerar cortes com o Claude", self.pedir_cortes)
        self.botao("3   Gerar Shorts", self.gerar)
        self.botao("4   Revisar legendas", self.revisar_legendas)
        self.botao("5   Publicar os Shorts prontos", self.publicar)
        self.secao("PROJETO SELECIONADO  (mais no botão direito)")
        self.linha_de_botoes([("📁 Abrir pasta", self.abrir_pasta), ("🗑 Excluir...", self.excluir)])

    def itens_do_menu(self, i: dict) -> list:
        return [
            ("▶  Transcrever o vídeo", self.transcrever_selecionado),
            ("✂  Gerar cortes com o Claude", self.pedir_cortes),
            ("📋  Copiar pedido de cortes (colar no Claude)", self.copiar_pedido_cortes),
            ("⚙  Gerar os Shorts", self.gerar),
            ("✏  Revisar os Shorts", self.revisar_legendas),
            ("📅  Publicar", self.publicar),
            None,
            ("🔗  Link do vídeo completo...", self.definir_link),
            ("📁  Abrir pasta dos Shorts", self.abrir_pasta),
        ]

    def valores(self, i: dict) -> tuple:
        return (
            f"{i['n_shorts']}/{i['n_cortes']}" if i["tem_cortes"] else "-",
            f"{i['postados']}/{i['n_pub']}" if i["n_pub"] else "-",
            STATUS.get(i.get("proximo", ""), ""),
        )

    def texto_passo(self, i: dict) -> str:
        return f"Próximo passo: {i['passo']}"

    def texto_extra(self, i: dict) -> str:
        link = i["projeto"].get("link_video_completo") or "ainda não definido (usa o link do canal)"
        return f"🔗 Link do vídeo completo: {link}  (clique para mudar)"

    def clique_extra(self):
        self.definir_link()

    def transcrever_selecionado(self):
        """Transcreve o video do projeto selecionado (ou pede para escolher, se o video sumiu)."""
        from nucleo.miniatura import video_do_projeto

        i = self.selecionado()
        video = video_do_projeto(i["pasta"]) if i else None
        rodar_script("nucleo.transcrever", *([video] if video else []))

    def pasta_para_abrir(self, i: dict):
        return i["pasta"] / "prontos" if (i["pasta"] / "prontos").exists() else i["pasta"]

    # ---------------------------------------------------------- passos
    def transcrever(self):
        rodar_script("nucleo.transcrever")

    def pedir_cortes(self):
        """Gerar cortes com o Claude: com o Claude Code no PC, manda e recebe sozinho; sem ele, copia o pedido."""
        from nucleo import claude_local

        i = self.exigir()
        if not i:
            return
        if not i["transcrito"]:
            messagebox.showinfo("Gerar cortes", "Esse vídeo ainda não foi transcrito. Faça o passo 1 antes.")
            return
        if not claude_local.disponivel():
            self.copiar_pedido_cortes(sem_claude_code=True)
            return
        if i["tem_cortes"] and not messagebox.askyesno(
            "Gerar cortes com o Claude",
            "Esse vídeo já tem cortes escolhidos.\n\nPedir de novo ao Claude? Os cortes atuais vão para "
            "cortes_anterior.json (os Shorts já gerados continuam na pasta).",
        ):
            return
        from interface.janela_claude import JanelaClaude
        from shorts.biblioteca import categorias_com_arquivos
        from shorts.cortes_com_claude import gerar_cortes

        cfg, categorias = carregar_config(), categorias_com_arquivos("efeito")

        def trabalho(cancelar, progresso, avisar):
            return gerar_cortes(i["pasta"], i["nome"], cfg, categorias, ARQ_DIRETRIZES, cancelar, progresso, avisar)

        JanelaClaude(self.studio, "Gerar cortes com o Claude",
                     f'O Claude está lendo a transcrição de "{i["nome"]}" e escolhendo os trechos que viram Short. '
                     "Pode continuar usando o Studio.", trabalho, lambda dados: self.cortes_chegaram(i, dados))  # fmt: skip

    def cortes_chegaram(self, i: dict, dados: dict):
        from shorts.cortes import MENSAGEM_ZERO
        from shorts.cortes_com_claude import salvar_cortes

        salvar_cortes(i["pasta"], dados)
        self.studio.atualizar()
        n = len(dados.get("cortes") or [])
        if n:
            self.studio.notificar(f"O Claude escolheu {n} corte(s) de \"{i['nome']}\".\n"
                                  "Próximo passo: Gerar os Shorts (botão laranja).", "ok", 7)  # fmt: skip
        else:
            self.studio.notificar(f"{MENSAGEM_ZERO} O Claude não achou nenhum corte bom.", "aviso", 7)

    def copiar_pedido_cortes(self, sem_claude_code: bool = False):
        """O jeito antigo: copia o pedido para colar na conversa com o Claude."""
        i = self.exigir()
        if not i:
            return
        from shorts.biblioteca import categorias_com_arquivos
        from shorts.pedido_cortes import texto_pedido

        texto = texto_pedido(i["nome"], i["pasta"], ARQ_DIRETRIZES, carregar_config(),
                             categorias_com_arquivos("efeito"))  # fmt: skip
        self.studio.copiar(texto)
        messagebox.showinfo(
            "Pedir cortes ao Claude",
            ("Não achei o Claude Code neste computador, então fiz do jeito antigo:\n\n" if sem_claude_code else "")
            + "Pedido copiado! Cole (Ctrl+V) na conversa com o Claude e envie.\n"
            "Quando ele avisar que salvou o cortes.json, volte aqui e clique em Gerar os Shorts.",
        )

    def gerar(self):
        i = self.exigir()
        if not i:
            return
        if not i["tem_cortes"]:
            messagebox.showinfo("Gerar Shorts", "Esse vídeo ainda não tem cortes. Faça o passo 2 antes.")
            return
        if i["n_cortes"] == 0:
            from shorts.cortes import MENSAGEM_ZERO

            messagebox.showinfo(
                "Gerar Shorts",
                f"{MENSAGEM_ZERO}\n\nO Claude não achou nenhum corte chamativo ou engraçado o bastante.\n"
                "Se discordar, peça de novo (passo 2) dizendo qual momento você queria.",
            )
            return
        cfg = carregar_config()
        if cfg.get("layout") == "camera" and not cfg.get("camera_area"):
            if not messagebox.askyesno(
                "Câmera não marcada",
                "O formato com câmera em cima ainda não foi marcado.\nQuer gerar assim mesmo (com fundo desfocado)?",
            ):
                return
        prontos = i["pasta"] / "prontos"
        existentes = [f for f in prontos.glob("*.mp4") if not f.name.startswith("_")] if prontos.exists() else []
        if existentes:
            r = messagebox.askyesnocancel(
                "Gerar Shorts",
                f"Já existem {len(existentes)} Shorts desse vídeo.\n\n"
                "SIM = refazer TODOS (os atuais vão para a pasta 'antigos')\n"
                "NÃO = gerar só os que faltam\n"
                "CANCELAR = não fazer nada",
            )
            if r is None:
                return
            if r:
                mover_para_antigos(prontos, existentes)
        rodar_script("shorts.gerar_shorts", i["pasta"])

    def revisar_legendas(self):
        i = self.exigir()
        if not i:
            return
        pub = ler_json(i["pasta"] / "prontos" / "publicacao.json", None)
        if not pub or not pub.get("shorts"):
            messagebox.showinfo("Revisar legendas", "Esse vídeo ainda não tem Shorts gerados. Faça o passo 3 antes.")
            return
        EditorLegendas(self.studio, i)

    def publicar(self):
        """Publica os Shorts prontos deste projeto (um por dia, as 12:00), depois de voce revisar."""
        i = self.exigir()
        if not i:
            return
        pub = ler_json(i["pasta"] / "prontos" / "publicacao.json", None)
        if not pub or not pub.get("shorts"):
            messagebox.showinfo("Publicar", "Esse vídeo ainda não tem Shorts gerados. Faça o passo 3 antes.")
            return
        self.studio.publicar_shorts(i)

    def definir_link(self):
        i = self.exigir()
        if not i:
            return
        atual = i["projeto"].get("link_video_completo", "")
        link = simpledialog.askstring(
            "Link do vídeo completo",
            "Cole o link do vídeo longo no YouTube\n(vai na descrição dos Shorts):",
            initialvalue=atual,
            parent=self.studio.raiz,
        )
        if link is None:
            return
        link = link.strip()
        if link and not link.startswith("http"):
            link = "https://" + link
        projeto = ler_json(i["pasta"] / "projeto.json", {}) or {}
        projeto["link_video_completo"] = link
        gravar_json(i["pasta"] / "projeto.json", projeto)
        self.studio.atualizar()
