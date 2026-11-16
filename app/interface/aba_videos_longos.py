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
        self.botao("Limpar projeto (depois de postar)", self.limpar_projeto)

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
            self.studio.pedir_edicao(i)
            return
        JanelaEdicao(self.studio, i)
