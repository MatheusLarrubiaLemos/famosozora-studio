# Aba "Videos longos / Lives": juntar as partes, transcrever a live e editar o video longo
# (o Claude escolhe o que sai, voce revisa e o Studio gera o episodio). Desde a 1.9.0: "Editar" abre o editor de
# video do Studio (Auto-Edit: sugere sozinho o que cortar), e "Analisar os selecionados" analisa varias lives.
import os
import subprocess
from tkinter import messagebox

from interface.aba_base import AbaProjetos
from interface.janela_edicao import JanelaEdicao
from interface.utilidades import rodar_script
from nucleo.comum import ARQ_ULTIMO_JUNTADO, FERRAMENTAS, PASTA_VIDEOS

STATUS = {"transcrever": "Falta transcrever", "editar": "Falta a edição do Claude", "revisar": "Revisar e gerar",
          "publicar": "Episódio pronto: publicar", "pronto": "✓ Publicado"}  # fmt: skip


class AbaVideosLongos(AbaProjetos):
    TITULO = "Vídeos longos"
    TELA = "longos"
    SUBTITULO = "a live vira episódio: juntar as partes, transcrever, editar com o Claude e gerar"
    COLUNAS = [("edicao", "Edição do Claude", 130), ("status", "Status", 170)]
    TEXTO_VAZIO = "Nenhuma live ainda.\nJunte as partes da live ou arraste um vídeo para esta janela."
    PASSOS = {"transcrever": ("Transcrever a live", "transcrever"),
              "editar": ("Editar com o Claude", "editar_longo"),
              "revisar": ("Editar (vídeo e cortes)", "editor"),
              "publicar": ("Publicar o episódio", "publicar"),
              "pronto": ("Abrir a pasta do episódio", "abrir_pasta")}  # fmt: skip

    def montar_botoes(self):
        self.secao("PASSO A PASSO")
        self.botao("1   Juntar vídeos (partes da live)", self.juntar)
        self.botao("2   Transcrever a live", self.transcrever)
        self.botao("3   Editar (editor de vídeo + Auto-Edit)", self.editor)
        self.botao("     Edição do Claude (título, capítulos, cortes grandes)", self.editar_longo)
        self.botao("4   Publicar o episódio", self.publicar)
        self.secao("PROJETO SELECIONADO  (mais no botão direito)")
        self.linha_de_botoes([("▶ Assistir", self.assistir), ("📁 Abrir pasta", self.abrir_pasta),
                              ("🗑 Excluir...", self.excluir)])  # fmt: skip

    def itens_do_menu(self, i: dict) -> list:
        return [
            ("▶  Transcrever a live", self.transcrever),
            ("🎬  Editar (editor de vídeo + Auto-Edit)", self.editor),
            ("✂  Edição do Claude / revisar a lista", self.editar_longo),
            ("🔁  Pedir a edição de novo ao Claude", self.editar_com_claude),
            ("📋  Copiar pedido de edição (colar no Claude)", lambda: self.studio.pedir_edicao(self.exigir())),
            ("📋  Colar edicao.json", lambda: self.studio.colar_edicao(self.exigir())),
            ("▶  Assistir o episódio editado", self.assistir),
            ("📅  Publicar o episódio", self.publicar),
            None,
            ("📁  Abrir pasta do episódio", self.abrir_pasta),
        ]

    def itens_do_menu_varios(self, selecionados: list) -> list:
        return [(f"🔎  Analisar as {len(selecionados)} lives (Auto-Edit)", lambda: self.analisar_varios(selecionados)),
                (f"🔎  Analisar as {len(selecionados)} sem o Claude (mais rápido)",
                 lambda: self.analisar_varios(selecionados, False))]  # fmt: skip

    def acao_varios(self, selecionados: list):
        return (f"Analisar as {len(selecionados)} lives (Auto-Edit)", lambda: self.analisar_varios(selecionados))

    def codigo_passo(self, info: dict) -> str:
        return info.get("proximo_longo", "")

    def valores(self, i: dict) -> tuple:
        tem_edicao = (i["pasta"] / "edicao.json").exists()
        return ("ok" if tem_edicao else "-", STATUS.get(i.get("proximo_longo", ""), ""))

    def texto_passo(self, i: dict) -> str:
        return f"Próximo passo: {i['passo_longo']}"

    def texto_extra(self, i: dict) -> str:
        return "O Claude só vê a transcrição, não a tela: revise os trechos antes de gerar."

    def pasta_para_abrir(self, i: dict):
        return i["pasta"] / "episodio" if (i["pasta"] / "episodio").exists() else i["pasta"]

    # ---------------------------------------------------------- passos
    def juntar(self):
        ps1 = FERRAMENTAS / "videos_longos" / "juntar_videos_gui.ps1"
        if not ps1.exists():
            messagebox.showinfo("Juntar vídeos", f"Não achei {ps1}.")
            return
        PASTA_VIDEOS.mkdir(parents=True, exist_ok=True)
        comando = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-STA", "-WindowStyle", "Hidden"]
        # FAMOSOZORA_ULTIMO_JUNTADO: onde anotar o video criado (o "Transcrever" abre na pasta dele)
        env = dict(os.environ, FAMOSOZORA_VIDEOS=str(PASTA_VIDEOS), FAMOSOZORA_ULTIMO_JUNTADO=str(ARQ_ULTIMO_JUNTADO))
        subprocess.Popen(comando + ["-File", str(ps1)], env=env)

    def transcrever(self):
        rodar_script("nucleo.transcrever")

    def editar_longo(self):
        i = self.exigir()
        if not i:
            return
        if not i["transcrito"]:
            messagebox.showinfo("Editar vídeo longo", "Essa live ainda não foi transcrita. Faça o passo 2 antes.")
            return
        if not (i["pasta"] / "edicao.json").exists():
            self.editar_com_claude()
            return
        self.abrir_revisao(i)

    def editor(self):
        """O editor de video do Studio (Auto-Edit): sugere os cortes, voce revisa em ate 4x e gera o episodio."""
        i = self.exigir()
        if not i:
            return
        if not i["transcrito"] and not messagebox.askyesno(
            "Editar", "Essa live ainda não foi transcrita. Sem a transcrição, o Studio não sabe onde você fala e "
            "corta pior.\n\nAbrir o editor assim mesmo?"):  # fmt: skip
            return
        from editor.janela_editor import JanelaEditor

        return JanelaEditor.abrir_longo(self.studio, i)

    def analisar_varios(self, selecionados: list, usar_claude: bool = True):
        from editor.janela_analise_lote import JanelaAnaliseLote

        sem = [i["nome"] for i in selecionados if not i["transcrito"]]
        if sem and not messagebox.askyesno("Analisar", f"{len(sem)} live(s) ainda sem transcrição (o corte fica "
                                           "pior):\n" + "\n".join(sem[:5]) + "\n\nAnalisar assim mesmo?"):  # fmt: skip
            return
        JanelaAnaliseLote(self.studio, selecionados, usar_claude)

    def abrir_revisao(self, i: dict):
        """A revisao do video longo (uma por projeto: clicar de novo traz a que ja esta aberta)."""
        from interface.utilidades import janela_ja_aberta, lembrar_janela

        chave = ("edicao", str(i["pasta"]))
        return janela_ja_aberta(chave) or lembrar_janela(chave, JanelaEdicao(self.studio, i))

    def assistir(self):
        """Abre o episodio ja editado (o .mp4 gerado) no player do PC."""
        from interface.utilidades import abrir
        from publicacao.rascunhos import episodio_do_projeto

        i = self.exigir()
        if not i:
            return
        arq = episodio_do_projeto(i["pasta"])
        if not arq:
            messagebox.showinfo("Assistir", "Esse vídeo ainda não tem episódio gerado. Gere o episódio antes.")
            return
        abrir(arq)

    def publicar(self):
        i = self.exigir()
        if i:
            self.studio.publicar_longo(i)

    def editar_com_claude(self, parent=None):
        """Editar com o Claude: com o Claude Code no PC, manda a transcricao e recebe o edicao.json sozinho."""
        from nucleo import claude_local

        i = self.exigir()
        if not i:
            return
        if not claude_local.disponivel():
            self.studio.pedir_edicao(i, parent)
            return
        from interface.utilidades import janela_ja_aberta, lembrar_janela

        chave = ("claude", "edicao", str(i["pasta"]))
        if janela_ja_aberta(chave):  # o Claude ja esta editando esta live: nao pede duas vezes
            self.studio.notificar("O Claude já está editando esse vídeo. Acompanhe na janela dele.", "info")
            return
        if (i["pasta"] / "edicao.json").exists() and not messagebox.askyesno(
            "Editar com o Claude", "Essa live já tem uma edição.\n\nPedir de novo ao Claude? A atual vai para "
            "edicao_anterior.json.", parent=parent or self.studio.raiz):  # fmt: skip
            return
        from interface.janela_claude import JanelaClaude
        from interface.utilidades import ARQ_DIRETRIZES
        from nucleo.comum import carregar_config
        from videos_longos.edicao_com_claude import editar_longo

        cfg = carregar_config()

        def trabalho(cancelar, progresso, avisar):
            return editar_longo(i["pasta"], i["nome"], cfg, ARQ_DIRETRIZES, cancelar, progresso, avisar)

        lembrar_janela(
            chave,
            JanelaClaude(
                self.studio,
                "Editar com o Claude",
                f'O Claude está lendo a transcrição de "{i["nome"]}" e marcando as partes sem jogo, no estilo '
                "programa de TV. Você revisa tudo antes de gerar.",
                trabalho,
                lambda r: self.edicao_chegou(i, r),
                parent,
            ),
        )

    def edicao_chegou(self, i: dict, resultado):
        from videos_longos.edicao_com_claude import salvar_edicao

        dados, avisos = resultado
        salvar_edicao(i["pasta"], dados)
        self.studio.atualizar()
        self.studio.notificar(f"Edição pronta: {len(dados.get('cortes') or [])} trecho(s) para remover e "
                              f"{len(dados.get('capitulos') or [])} capítulo(s). Revise antes de gerar.", "ok", 7)  # fmt: skip
        self.abrir_revisao(i)
