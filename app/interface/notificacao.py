# Notificacoes discretas no canto de baixo da janela ("Short renderizado", "Agendado para 18/11 as 12:00").
# Aparecem por alguns segundos e somem sozinhas, sem travar a tela como as janelas de aviso.
import tkinter as tk

from interface import tema

CORES = {"ok": tema.VERDE, "info": tema.LARANJA, "aviso": tema.AMARELO, "erro": tema.VERMELHO}
_abertas = {}  # janela -> lista de notificacoes visiveis (para empilhar uma em cima da outra)


def notificar(janela: tk.Misc, texto: str, tipo: str = "ok", segundos: float = 4.5):
    """Mostra uma notificacao no canto de baixo, a direita, da janela (a principal ou outra)."""
    try:
        raiz = janela.winfo_toplevel()
    except tk.TclError:
        return None
    lista = _abertas.setdefault(str(raiz), [])
    caixa = tk.Frame(raiz, bg=tema.PAINEL, highlightbackground=CORES.get(tipo, tema.LARANJA), highlightthickness=1)
    tk.Frame(caixa, bg=CORES.get(tipo, tema.LARANJA), width=4).pack(side="left", fill="y")
    tk.Label(caixa, text=texto, bg=tema.PAINEL, fg=tema.TEXTO, font=tema.F_TEXTO, justify="left", anchor="w",
             wraplength=360, padx=12, pady=10).pack(side="left")  # fmt: skip
    fechar = tk.Label(caixa, text="✕", bg=tema.PAINEL, fg=tema.TEXTO_2, font=tema.F_PEQUENA, padx=8, cursor="hand2")
    fechar.pack(side="right", anchor="n", pady=4)
    lista.append(caixa)

    def arrumar():
        y = -16
        for c in reversed([c for c in lista if c.winfo_exists()]):
            c.update_idletasks()
            c.place(relx=1.0, rely=1.0, x=-16, y=y, anchor="se")
            c.lift()
            y -= c.winfo_reqheight() + 8

    def sumir(_evento=None):
        if caixa in lista:
            lista.remove(caixa)
        if caixa.winfo_exists():
            caixa.destroy()
        arrumar()

    fechar.bind("<Button-1>", sumir)
    arrumar()
    raiz.after(int(segundos * 1000), sumir)
    return caixa
