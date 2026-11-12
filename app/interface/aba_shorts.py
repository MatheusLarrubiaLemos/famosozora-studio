# Aba "Shorts": transcrever, marcar camera, pedir os cortes ao Claude, gerar os Shorts e publicar.
from tkinter import messagebox, simpledialog

from interface.aba_base import AbaProjetos
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
        self.botao("4   Publicar (Buffer)", self.publicar, "Passo.TButton")
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
        texto = (
            f'Claude, escolhe os cortes do projeto "{i["nome"]}".\n'
            f'Pasta: {i["pasta"]}\n'
            f"Siga as DIRETRIZES DO CANAL ({ARQ_DIRETRIZES}). Resumo:\n"
            "- O vídeo é a versão bruta da live: escolha momentos em que estou JOGANDO "
            "(nada de espera, menu, intro ou papo fora do jogo).\n"
            "- O Short apresenta, o vídeo longo aprofunda: cada corte se entende sozinho, com começo, "
            "meio e fim, sem picotar, e deixa vontade de ver o vídeo completo.\n"
            "- Título honesto e chamativo, alinhado ao que acontece no corte (sem mentir). "
            "Se for série, cite o episódio.\n"
            "- Falas naturais, palavrão pode ficar. Pouca hashtag; o conteúdo é que vende.\n"
            "- Inclua também título e descrição em inglês (youtube_titulo_en, youtube_descricao_en).\n"
            "Legenda corrigida e textos pra YouTube, TikTok e Instagram. Salva o cortes.json na pasta."
        )
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
