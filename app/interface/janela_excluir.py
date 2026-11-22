# Janela "Excluir": confirma antes de mandar projetos (um ou varios) para a Lixeira do Windows.
# Opcoes: so os Shorts (ou so o episodio, na tela de videos longos), o projeto inteiro, ou o projeto junto com
# o video original (aviso em vermelho). Mostra quanto espaco vai liberar e avisa se algum item ainda esta na
# fila de publicacao. Nada e apagado de vez: tudo vai para a Lixeira.
# Leva junto os pacotes de publicacao (pasta publicar\) dos videos daqui que JA estao no ar: o video do pacote e
# uma ligacao do mesmo arquivo, entao sem eles o espaco nao era liberado.
import tkinter as tk
from tkinter import messagebox, ttk

from interface import tema
from interface.telas import nova_janela
from nucleo.limpeza import MODOS, excluir_projeto, itens_para_excluir, tamanho_dos_itens, tamanho_txt, video_original
from publicacao import fila
from publicacao.pacote import mandar_pacotes_para_lixeira, marcar_pacotes_limpos, pacotes_dos_videos


class JanelaExcluir:
    def __init__(self, studio, projetos: list, tela: str = "shorts"):
        """projetos: lista de 'info' (a mesma da lista de projetos). tela: 'shorts' ou 'longos'."""
        self.studio = studio
        self.projetos = projetos
        self.resultado = None
        primeiro = "episodio" if tela == "longos" else "shorts"
        self.modos = [primeiro, "projeto", "tudo"]
        itens_da_fila = fila.itens()
        self.pacotes, self.tamanhos = {}, {}
        for m in self.modos:
            itens = [f for i in projetos for f in itens_para_excluir(i["pasta"], m)]
            self.pacotes[m] = pacotes_dos_videos(itens_da_fila, itens) if itens else []
            # (o video do pacote e o mesmo arquivo do Short: o tamanho conta ele uma vez so)
            self.tamanhos[m] = tamanho_dos_itens(itens + [pasta for _, pasta in self.pacotes[m]])

        self.jan = nova_janela(studio.raiz)
        self.jan.title("Excluir")
        self.jan.configure(bg=tema.FUNDO)
        self.jan.resizable(False, False)
        q = tk.Frame(self.jan, bg=tema.FUNDO, padx=24, pady=20)
        q.pack(fill="both", expand=True)
        nomes = projetos[0]["nome"] if len(projetos) == 1 else f"{len(projetos)} projetos"
        tema.rotulo(q, f"Excluir {nomes}?", "subtitulo", wraplength=520).pack(fill="x")
        if len(projetos) > 1:
            lista = ", ".join(i["nome"] for i in projetos[:6]) + (" ..." if len(projetos) > 6 else "")
            tema.rotulo(q, lista, "secundario", wraplength=520).pack(fill="x", pady=(2, 0))
        tema.rotulo(q, "Tudo vai para a Lixeira do Windows: dá para restaurar depois.", "secundario").pack(
            fill="x", pady=(4, 12)
        )

        self.modo = tk.StringVar(value=self.modos[0])
        explicacoes = {
            "shorts": "mantém a transcrição, os cortes e as edições (dá para gerar de novo)",
            "episodio": "mantém a transcrição e a edição do Claude (dá para gerar de novo)",
            "projeto": "Shorts, episódio, transcrição, cortes e edições. O vídeo original fica.",
            "tudo": "",
        }
        for m in self.modos:
            linha = tk.Frame(q, bg=tema.FUNDO)
            linha.pack(fill="x", pady=3)
            ttk.Radiobutton(linha, text=f"{MODOS[m]}  ({tamanho_txt(self.tamanhos[m])})", value=m,
                            variable=self.modo, command=self.mudou).pack(anchor="w")  # fmt: skip
            if m == "tudo":
                videos = [v for v in (video_original(i["pasta"]) for i in projetos) if v]
                texto = ("⚠ O VÍDEO ORIGINAL (a live gravada) também vai para a Lixeira:\n"
                         + "\n".join(str(v) for v in videos[:3]) + ("\n..." if len(videos) > 3 else "")
                         if videos else "⚠ O vídeo original não foi encontrado: só o projeto vai.")  # fmt: skip
                tk.Label(linha, text=texto, bg=tema.FUNDO, fg=tema.VERMELHO, font=tema.F_PEQUENA, justify="left",
                         anchor="w", wraplength=500).pack(fill="x", padx=(24, 0))  # fmt: skip
            else:
                dentro = m == "projeto" and any(
                    v and i["pasta"] in v.parents for i in projetos for v in [video_original(i["pasta"])]
                )
                texto = ("⚠ O vídeo original está DENTRO da pasta do projeto: ele vai junto."
                         if dentro else explicacoes[m])  # fmt: skip
                tk.Label(
                    linha,
                    text=texto,
                    bg=tema.FUNDO,
                    fg=tema.AMARELO if dentro else tema.TEXTO_2,
                    font=tema.F_PEQUENA,
                    justify="left",
                    anchor="w",
                    wraplength=500,
                ).pack(fill="x", padx=(24, 0))

        self.lbl_fila = tk.Label(q, text="", bg=tema.FUNDO, fg=tema.AMARELO, font=tema.F_TEXTO, justify="left",
                                 anchor="w", wraplength=520)  # fmt: skip
        self.lbl_fila.pack(fill="x", pady=(10, 0))
        self.lbl_total = tema.rotulo(q, "", "texto")
        self.lbl_total.pack(fill="x", pady=(10, 0))

        botoes = tk.Frame(q, bg=tema.FUNDO)
        botoes.pack(fill="x", pady=(16, 0))
        self.btn = ttk.Button(botoes, text="Mandar para a Lixeira", style="Perigo.TButton", command=self.confirmar)
        self.btn.pack(side="right")
        ttk.Button(botoes, text="Cancelar", style="Extra.TButton", command=self.jan.destroy).pack(side="right", padx=8)
        self.jan.bind("<Escape>", lambda e: self.jan.destroy())
        self.mudou()
        self.jan.transient(studio.raiz)
        self.jan.update_idletasks()
        x = studio.raiz.winfo_rootx() + (studio.raiz.winfo_width() - self.jan.winfo_reqwidth()) // 2
        y = studio.raiz.winfo_rooty() + (studio.raiz.winfo_height() - self.jan.winfo_reqheight()) // 3
        self.jan.geometry(f"+{max(0, x)}+{max(0, y)}")

    def mudou(self):
        m = self.modo.get()
        pacotes = len(self.pacotes.get(m) or [])
        self.lbl_total.config(text=f"Vai liberar {tamanho_txt(self.tamanhos[m])} no disco."
                              + (f"\nTambém vão {pacotes} pacote(s) de publicação de vídeos daqui que já estão "
                                 "no ar (pasta publicar)." if pacotes else ""))  # fmt: skip
        itens = [f for i in self.projetos for f in itens_para_excluir(i["pasta"], m)]
        aviso = self.studio.aviso_da_fila(itens) if itens else ""
        self.lbl_fila.config(text=aviso)
        self.btn.config(state="normal" if itens else "disabled")
        if not itens:
            self.lbl_total.config(text="Não tem nada para excluir com essa opção.")

    def confirmar(self):
        m = self.modo.get()
        if m == "tudo" and not messagebox.askyesno(
            "Excluir o vídeo original",
            "Tem certeza? O vídeo original da live também vai para a Lixeira.\n\n"
            "Ele ainda dá para restaurar pela Lixeira, mas só até ela ser esvaziada.",
            icon="warning", parent=self.jan,
        ):  # fmt: skip
            return
        liberado, erros = 0, []
        for i in self.projetos:
            try:
                liberado += excluir_projeto(i["pasta"], m)
            except OSError as e:
                erros.append(str(e))
        if self.pacotes.get(m):  # os pacotes de publicacao dos videos daqui que ja estao no ar
            resultado = mandar_pacotes_para_lixeira(self.pacotes[m])
            marcar_pacotes_limpos([id_ for id_, ok, _ in resultado if ok])
            liberado += sum(livre for _, ok, livre in resultado if ok)
            erros += ["Não consegui mandar um pacote de publicação para a Lixeira (algum arquivo aberto?)."
                      for _, ok, _ in resultado if not ok]  # fmt: skip
        self.resultado = (m, liberado, erros)
        self.jan.destroy()
        self.studio.atualizar()
        if erros:
            messagebox.showerror("Excluir", "\n\n".join(erros[:5]), parent=self.studio.raiz)
        if liberado or not erros:
            self.studio.notificar(f"{MODOS[m]}: {tamanho_txt(liberado)} foram para a Lixeira.")
