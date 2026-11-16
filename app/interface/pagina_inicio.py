# Tela "Inicio": o que esta pendente agora. Videos que ainda nao foram transcritos, Shorts para revisar
# e publicar, videos longos esperando edicao, e os proximos agendamentos da fila de publicacao.
# Clicar num item leva direto para a tela certa, com o projeto ja selecionado.
import tkinter as tk
from tkinter import messagebox, ttk

from interface import tema
from interface.menus import ligar_botao_direito, montar_menu
from interface.utilidades import mostrar_na_pasta
from nucleo.comum import EXTENSOES_VIDEO, PASTA_SHORTS, PASTA_VIDEOS, nome_seguro

MAXIMO_POR_CARTAO = 8


def videos_sem_projeto() -> list:
    """Videos da pasta videos\\ que ainda nao viraram projeto transcrito."""
    if not PASTA_VIDEOS.exists():
        return []
    soltos = []
    for v in sorted(PASTA_VIDEOS.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True):
        if v.is_file() and v.suffix.lower() in EXTENSOES_VIDEO and not v.name.startswith(("_", ".")):
            if not (PASTA_SHORTS / nome_seguro(v.stem) / "transcricao.json").exists():
                soltos.append(v)
    return soltos


def proximos_agendamentos() -> list:
    """Itens da fila de publicacao que ainda vao sair: [(quando, texto)]."""
    try:
        from publicacao import fila
    except Exception:
        return []
    try:
        return [(item["horario"], item) for item in fila.proximos()]
    except Exception:
        return []


class PaginaInicio(tk.Frame):
    def __init__(self, studio, pai):
        super().__init__(pai, bg=tema.FUNDO)
        self.studio = studio
        topo = tema.quadro(self)
        topo.pack(fill="x", padx=tema.ESPACO * 2, pady=(tema.ESPACO * 1.5, tema.ESPACO))
        tema.rotulo(topo, "Início", "titulo").pack(side="left")
        self.lbl_resumo = tema.rotulo(topo, "", "secundario")
        self.lbl_resumo.pack(side="left", pady=(8, 0), padx=(12, 0))
        ttk.Button(topo, text="+  Adicionar vídeo", style="Passo.TButton", command=studio.adicionar_video).pack(
            side="right"
        )
        dica = tema.rotulo(self, "Dica: arraste um vídeo para esta janela para criar um projeto.", "secundario")
        dica.pack(fill="x", padx=tema.ESPACO * 2)
        self.grade = tema.quadro(self)
        self.grade.pack(fill="both", expand=True, padx=tema.ESPACO * 2, pady=tema.ESPACO)
        for k in range(2):
            self.grade.columnconfigure(k, weight=1, uniform="col")
            self.grade.rowconfigure(k, weight=1, uniform="lin")
        self.cartoes = {}
        for k, (codigo, titulo) in enumerate([("transcrever", "Vídeos para transcrever"),
                                              ("shorts", "Shorts para fazer, revisar e publicar"),
                                              ("longos", "Vídeos longos em andamento"),
                                              ("agenda", "Próximos agendamentos")]):  # fmt: skip
            c = tema.cartao(self.grade, padx=16, pady=14)
            c.grid(
                row=k // 2,
                column=k % 2,
                sticky="nsew",
                padx=(0, tema.ESPACO if k % 2 == 0 else 0),
                pady=(0, tema.ESPACO),
            )
            cab = tk.Frame(c, bg=tema.PAINEL)
            cab.pack(fill="x")
            tema.rotulo(cab, titulo, "subtitulo", fundo=tema.PAINEL).pack(side="left")
            contador = tk.Label(cab, text="0", bg=tema.BORDA, fg=tema.TEXTO, font=tema.F_TEXTO_NEGRITO, padx=8)
            contador.pack(side="right")
            corpo = tk.Frame(c, bg=tema.PAINEL)
            corpo.pack(fill="both", expand=True, pady=(10, 0))
            self.cartoes[codigo] = (contador, corpo)

    # ---------------------------------------------------------- preencher
    def preencher(self, projetos: dict):
        soltos = videos_sem_projeto()
        sem_transcricao = [i for i in projetos.values() if not i["transcrito"]]
        itens_t = [(f"{v.name}", "videos de", lambda v=v: self.studio.criar_projetos([v]),
                    [("▶  Transcrever", lambda v=v: self.studio.criar_projetos([v])),
                     ("📁  Mostrar na pasta", lambda v=v: mostrar_na_pasta(v)), None,
                     ("🗑  Excluir vídeo (Lixeira)...", lambda v=v: self.excluir_video(v))]) for v in soltos]  # fmt: skip
        itens_t += [(i["nome"], "transcrever", lambda n=i["nome"]: self.studio.mostrar("shorts", n))
                    for i in sem_transcricao]  # fmt: skip
        self._cartao("transcrever", itens_t, "Nada para transcrever. Arraste um vídeo para cá ou clique em "
                     "Adicionar vídeo.", "clique para transcrever")  # fmt: skip

        textos = {"cortes": "escolher os cortes", "gerar": "gerar os Shorts", "revisar": "revisar e publicar"}
        shorts = [i for i in projetos.values() if i["transcrito"] and i.get("proximo") in textos]
        self._cartao("shorts", [(i["nome"], textos[i["proximo"]], lambda n=i["nome"]: self.studio.mostrar("shorts", n))
                                for i in shorts], "Nenhum Short pendente.")  # fmt: skip

        textos_l = {"revisar": "revisar e gerar o episódio"}
        longos = [i for i in projetos.values() if i.get("proximo_longo") in textos_l]
        self._cartao("longos", [(i["nome"], textos_l[i["proximo_longo"]],
                                 lambda n=i["nome"]: self.studio.mostrar("longos", n)) for i in longos],
                     "Nenhum vídeo longo esperando revisão.")  # fmt: skip

        agenda = proximos_agendamentos()
        self._cartao("agenda", [(item.get("titulo") or item.get("nome", ""), _quando(quando),
                                 lambda: self.studio.mostrar("publicacao")) for quando, item in agenda],
                     "Nada agendado. Revise um Short e clique em Publicar.")  # fmt: skip
        pendentes = len(itens_t) + len(shorts) + len(longos)
        self.lbl_resumo.config(text=f"{pendentes} coisa(s) pendente(s)" if pendentes else "Tudo em dia!")

    def excluir_video(self, video):
        if _excluir_video_confirmado(self, video):
            self.studio.atualizar()
            self.studio.notificar(f"{video.name} foi para a Lixeira.")

    def _cartao(self, codigo: str, itens: list, vazio: str, dica_padrao: str = ""):
        contador, corpo = self.cartoes[codigo]
        for w in corpo.winfo_children():
            w.destroy()
        contador.config(text=str(len(itens)), bg=tema.LARANJA if itens else tema.BORDA,
                        fg=tema.TEXTO_ESCURO if itens else tema.TEXTO)  # fmt: skip
        if not itens:
            tema.rotulo(corpo, vazio, "secundario", fundo=tema.PAINEL, wraplength=420).pack(fill="x", pady=8)
            return
        for nome, detalhe, acao, *extra in itens[:MAXIMO_POR_CARTAO]:
            linha = tk.Frame(corpo, bg=tema.PAINEL, cursor="hand2")
            linha.pack(fill="x", pady=1)
            a = tk.Label(linha, text=nome, bg=tema.PAINEL, fg=tema.TEXTO, font=tema.F_TEXTO, anchor="w", cursor="hand2")
            a.pack(side="left", fill="x", expand=True)
            b = tk.Label(linha, text=(dica_padrao if detalhe == "videos de" else detalhe) + "  ›", bg=tema.PAINEL,
                         fg=tema.TEXTO_2, font=tema.F_PEQUENA, cursor="hand2")  # fmt: skip
            b.pack(side="right")
            for w in (linha, a, b):
                w.bind("<Button-1>", lambda e, f=acao: f())
                if extra:
                    ligar_botao_direito(w, lambda e, it=extra[0]: montar_menu(self, it))
                w.bind("<Enter>", lambda e, ws=(linha, a, b): [x.config(bg=tema.BORDA) for x in ws])
                w.bind("<Leave>", lambda e, ws=(linha, a, b): [x.config(bg=tema.PAINEL) for x in ws])
        if len(itens) > MAXIMO_POR_CARTAO:
            tema.rotulo(corpo, f"... e mais {len(itens) - MAXIMO_POR_CARTAO}", "pequeno", fundo=tema.PAINEL).pack(
                fill="x", pady=(4, 0)
            )


def _excluir_video_confirmado(pai, video) -> bool:
    from nucleo.limpeza import mandar_para_lixeira, tamanho_dos_itens, tamanho_txt

    if not messagebox.askyesno(
        "Excluir vídeo",
        f"Mandar o vídeo para a Lixeira?\n\n{video}\n\n{tamanho_txt(tamanho_dos_itens([video]))} vão ser liberados. "
        "Dá para restaurar pela Lixeira do Windows.",
        icon="warning", parent=pai,
    ):  # fmt: skip
        return False
    if not mandar_para_lixeira([video]):
        messagebox.showerror("Excluir vídeo", "Não consegui mandar para a Lixeira. O vídeo está aberto no player?",
                             parent=pai)  # fmt: skip
        return False
    return True


def _quando(horario) -> str:
    try:
        from publicacao.horario import texto_horario

        return texto_horario(horario)
    except Exception:
        return str(horario)
