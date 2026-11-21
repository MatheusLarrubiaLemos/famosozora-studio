# Dica que aparece ao passar o mouse em cima de um botao (o "tooltip"): uma frase curta dizendo o que ele faz.
# Uso: dica(widget, "Toca o video (Espaco)"). Some sozinha ao tirar o mouse ou clicar.
import tkinter as tk

from interface import tema

ESPERA_MS = 450


class _Dica:
    def __init__(self, widget, texto: str):
        self.widget, self.texto = widget, texto
        self.janela = None
        self._id = None
        widget.bind("<Enter>", self._agendar, add="+")
        widget.bind("<Leave>", self._esconder, add="+")
        widget.bind("<ButtonPress>", self._esconder, add="+")

    def _agendar(self, _e=None):
        self._cancelar()
        self._id = self.widget.after(ESPERA_MS, self._mostrar)

    def _cancelar(self):
        if self._id:
            try:
                self.widget.after_cancel(self._id)
            except tk.TclError:
                pass
            self._id = None

    def _mostrar(self):
        self._id = None
        if self.janela or not self.texto:
            return
        try:
            x = self.widget.winfo_rootx() + 8
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
            self.janela = tk.Toplevel(self.widget)
            self.janela.wm_overrideredirect(True)
            self.janela.wm_geometry(f"+{x}+{y}")
            tk.Label(self.janela, text=self.texto, bg=tema.PAINEL, fg=tema.TEXTO, font=tema.F_PEQUENA, padx=8, pady=4,
                     relief="solid", borderwidth=1, justify="left", wraplength=320).pack()  # fmt: skip
        except tk.TclError:
            self.janela = None

    def _esconder(self, _e=None):
        self._cancelar()
        if self.janela is not None:
            try:
                self.janela.destroy()
            except tk.TclError:
                pass
            self.janela = None


def dica(widget, texto: str):
    """Liga a dica no widget e devolve o proprio widget (para usar em cadeia)."""
    _Dica(widget, texto)
    return widget
