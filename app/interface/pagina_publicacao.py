# Tela "Publicacao": a fila de publicacao (o que vai sair, quando, e se ja foi agendado).
import tkinter as tk

from interface import tema


class PaginaPublicacao(tk.Frame):
    def __init__(self, studio, pai):
        super().__init__(pai, bg=tema.FUNDO)
        self.studio = studio
        topo = tema.quadro(self)
        topo.pack(fill="x", padx=tema.ESPACO * 2, pady=(tema.ESPACO * 1.5, tema.ESPACO))
        tema.rotulo(topo, "Publicação", "titulo").pack(side="left")
        tema.rotulo(self, "A fila de publicação aparece aqui.", "secundario").pack(padx=tema.ESPACO * 2, anchor="w")
