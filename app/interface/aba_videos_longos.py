# Aba "Videos longos / Lives": juntar as partes, transcrever a live e editar o video longo
# (o Claude escolhe o que sai, voce revisa e o Studio gera o episodio).
import os
import subprocess
from tkinter import messagebox

from interface.aba_base import AbaProjetos
from interface.janela_edicao import JanelaEdicao
from interface.utilidades import rodar_script
from nucleo.comum import FERRAMENTAS, PASTA_VIDEOS

STATUS = {"transcrever": "Falta transcrever", "editar": "Falta a edição do Claude", "revisar": "Revisar e gerar",
          "publicar": "✓ Episódio gerado"}  # fmt: skip


class AbaVideosLongos(AbaProjetos):
    TITULO = "Vídeos longos"
    TELA = "longos"
    SUBTITULO = "a live vira episódio: juntar as partes, transcrever, editar com o Claude e gerar"
    COLUNAS = [("edicao", "Edição do Claude", 130), ("status", "Status", 170)]
    TEXTO_VAZIO = "Nenhuma live ainda.\nJunte as partes da live ou arraste um vídeo para esta janela."
    PASSOS = {"transcrever": ("Transcrever a live", "transcrever"),
              "editar": ("Editar com o Claude", "editar_longo"),
              "revisar": ("Revisar e gerar o episódio", "editar_longo"),
              "publicar": ("Abrir a pasta do episódio", "abrir_pasta")}  # fmt: skip

    def montar_botoes(self):
        self.secao("PASSO A PASSO")
        self.botao("1   Juntar vídeos (partes da live)", self.juntar)
        self.botao("2   Transcrever a live", self.transcrever)
        self.botao("3   Editar vídeo longo", self.editar_longo)
        self.secao("PROJETO SELECIONADO")
        self.botao("Colar edicao.json", lambda: self.studio.colar_edicao(self.exigir()))
        self.botao("Abrir pasta do episódio", self.abrir_pasta)
        self.botao("Excluir...  (ou botão direito / Delete)", self.excluir)

    def itens_do_menu(self, i: dict) -> list:
        return [
            ("▶  Transcrever a live", self.transcrever),
            ("✂  Editar com o Claude / revisar", self.editar_longo),
            ("🔁  Pedir a edição de novo ao Claude", self.editar_com_claude),
            ("📋  Copiar pedido de edição (colar no Claude)", lambda: self.studio.pedir_edicao(self.exigir())),
            ("📋  Colar edicao.json", lambda: self.studio.colar_edicao(self.exigir())),
            None,
            ("📁  Abrir pasta do episódio", self.abrir_pasta),
        ]

    def codigo_passo(self, info: dict) -> str:
        return info.get("proximo_longo", "")

    def valores(self, i: dict) -> tuple:
        tem_edicao = (i["pasta"] / "edicao.json").exists()
        return ("ok" if tem_edicao else "-", STATUS.get(i.get("proximo_longo", ""), ""))

    def texto_passo(self, i: dict) -> str:
        return (
            f"Próximo passo: {i['passo_longo']}\n\n"
            "O Claude só vê a transcrição, não a tela: revise os cortes antes de gerar."
        )

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
        subprocess.Popen(comando + ["-File", str(ps1)], env=dict(os.environ, FAMOSOZORA_VIDEOS=str(PASTA_VIDEOS)))

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
        JanelaEdicao(self.studio, i)

    def editar_com_claude(self, parent=None):
        """Editar com o Claude: com o Claude Code no PC, manda a transcricao e recebe o edicao.json sozinho."""
        from nucleo import claude_local

        i = self.exigir()
        if not i:
            return
        if not claude_local.disponivel():
            self.studio.pedir_edicao(i, parent)
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

        JanelaClaude(self.studio, "Editar com o Claude",
                     f'O Claude está lendo a transcrição de "{i["nome"]}" e marcando as partes sem jogo, no estilo '
                     "programa de TV. Você revisa tudo antes de gerar.", trabalho,
                     lambda r: self.edicao_chegou(i, r), parent)  # fmt: skip

    def edicao_chegou(self, i: dict, resultado):
        from videos_longos.edicao_com_claude import salvar_edicao

        dados, avisos = resultado
        salvar_edicao(i["pasta"], dados)
        self.studio.atualizar()
        self.studio.notificar(f"Edição pronta: {len(dados.get('cortes') or [])} trecho(s) para remover e "
                              f"{len(dados.get('capitulos') or [])} capítulo(s). Revise antes de gerar.", "ok", 7)  # fmt: skip
        JanelaEdicao(self.studio, i)
