# Janela que mostra um arquivo de texto formatado (usada nas novidades da versao).
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from interface import tema
from interface.telas import nova_janela
from interface.utilidades import COR_DESTAQUE, COR_FUNDO, COR_TEXTO


class JanelaTexto:
    def __init__(self, raiz, titulo: str, arquivo: Path):
        jan = nova_janela(raiz)
        jan.title(titulo)
        jan.geometry("760x620")
        jan.configure(bg=COR_FUNDO)
        txt = tk.Text(
            jan,
            wrap="word",
            bg=tema.CAMPO,
            fg=COR_TEXTO,
            insertbackground=COR_TEXTO,
            font=("Segoe UI", 11),
            padx=16,
            pady=12,
            relief="flat",
        )
        barra = ttk.Scrollbar(jan, command=txt.yview)
        txt.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        txt.pack(fill="both", expand=True)
        txt.tag_configure("h1", font=("Segoe UI", 16, "bold"), foreground=COR_DESTAQUE, spacing1=8, spacing3=6)
        txt.tag_configure("h2", font=("Segoe UI", 13, "bold"), foreground=COR_DESTAQUE, spacing1=10, spacing3=4)
        txt.tag_configure("h3", font=("Segoe UI", 11, "bold"), foreground=tema.LARANJA, spacing1=6)
        try:
            linhas = arquivo.read_text(encoding="utf-8").splitlines()
        except Exception:
            linhas = [f"Não achei o arquivo {arquivo}."]
        for linha in linhas:
            limpa = linha.replace("**", "").replace("`", "")
            if limpa.startswith("### "):
                txt.insert("end", limpa[4:] + "\n", "h3")
            elif limpa.startswith("## "):
                txt.insert("end", limpa[3:] + "\n", "h2")
            elif limpa.startswith("# "):
                txt.insert("end", limpa[2:] + "\n", "h1")
            else:
                txt.insert("end", (("  •" + limpa[1:]) if limpa.startswith("- ") else limpa) + "\n")
        txt.configure(state="disabled")
