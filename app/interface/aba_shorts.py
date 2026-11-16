# Aba "Shorts": transcrever, marcar camera, pedir os cortes ao Claude, gerar os Shorts,
# revisar as legendas e publicar.
from tkinter import messagebox, simpledialog

from interface.aba_base import AbaProjetos
from interface.editor_legendas import EditorLegendas
from interface.janela_publicar import JanelaPublicar
from interface.utilidades import ARQ_DIRETRIZES, rodar_script
from nucleo.comum import carregar_config, gravar_json, ler_json, mover_para_antigos


class AbaShorts(AbaProjetos):
    COLUNAS = [("transcricao", "Transcrição", 100), ("cortes", "Cortes", 80), ("shorts", "Shorts", 80),
               ("postados", "Postados", 90)]  # fmt: skip
    TEXTO_VAZIO = "Nenhum vídeo ainda. Comece pelo passo 1: Transcrever vídeo novo."

    def montar_botoes(self):
        self.secao("PASSO A PASSO")
        self.botao("1   Transcrever vídeo novo", self.transcrever, "Passo.TButton")
        self.botao("2   Pedir cortes ao Claude", self.pedir_cortes, "Passo.TButton")
        self.botao("3   Gerar Shorts", self.gerar, "Passo.TButton")
        self.botao("4   Revisar legendas", self.revisar_legendas, "Passo.TButton")
        self.botao("5   Publicar (Buffer)", self.publicar, "Passo.TButton")
        self.secao("PROJETO SELECIONADO")
        self.botao("Link do vídeo completo...", self.definir_link)
        self.botao("Abrir pasta dos Shorts", self.abrir_pasta)
        self.botao("Limpar projeto (depois de postar)", self.limpar_projeto)
        self.secao("FERRAMENTAS")
        self.botao("Marcar câmera e gameplay", lambda: rodar_script("interface.marcar_camera", console=False))

    def valores(self, i: dict) -> tuple:
        return (
            "ok" if i["transcrito"] else "-",
            i["n_cortes"] if i["tem_cortes"] else "-",
            f"{i['n_shorts']}/{i['n_cortes']}" if i["tem_cortes"] else "-",
            f"{i['postados']}/{i['n_pub']}" if i["n_pub"] else "-",
        )

    def texto_passo(self, i: dict) -> str:
        link = i["projeto"].get("link_video_completo") or "(ainda não definido: usa o link do canal)"
        return f"{i['nome']}\nPróximo passo: {i['passo']}\nLink do vídeo completo: {link}"

    def pasta_para_abrir(self, i: dict):
        return i["pasta"] / "prontos" if (i["pasta"] / "prontos").exists() else i["pasta"]

    # ---------------------------------------------------------- passos
    def transcrever(self):
        rodar_script("nucleo.transcrever")

    def pedir_cortes(self):
        i = self.exigir()
        if not i:
            return
        if not i["transcrito"]:
            messagebox.showinfo("Pedir cortes", "Esse vídeo ainda não foi transcrito. Faça o passo 1 antes.")
            return
        from shorts.pedido_cortes import texto_pedido

        texto = texto_pedido(i["nome"], i["pasta"], ARQ_DIRETRIZES, carregar_config())
        self.studio.copiar(texto)
        messagebox.showinfo(
            "Pedir cortes ao Claude",
            "Pedido copiado!\n\nAgora cole (Ctrl+V) na conversa com o Claude e envie.\n"
            "Quando ele avisar que salvou o cortes.json, volte aqui e clique em 3 - Gerar Shorts.",
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
        i = self.exigir()
        if not i:
            return
        pub = ler_json(i["pasta"] / "prontos" / "publicacao.json", None)
        if not pub or not pub.get("shorts"):
            messagebox.showinfo("Publicar", "Esse vídeo ainda não tem Shorts gerados. Faça o passo 3 antes.")
            return
        JanelaPublicar(self.studio, i)

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
