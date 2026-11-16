# Janela de progresso enquanto o Claude trabalha (gerar cortes, editar video longo): barra de progresso,
# o que esta acontecendo agora, o tempo passando e o botao Cancelar. O trabalho roda em segundo plano
# (a tela nao trava) e, no fim, a funcao ao_terminar recebe o resultado (ou o erro).
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

from interface import tema
from nucleo.claude_local import Cancelado, ErroClaude


class JanelaClaude:
    def __init__(self, studio, titulo: str, explicacao: str, trabalho, ao_terminar, parent=None):
        """trabalho(cancelar, progresso, avisar) -> resultado.  ao_terminar(resultado) roda na tela, so se deu certo."""
        self.studio = studio
        self.ao_terminar = ao_terminar
        self.cancelar_evento = threading.Event()
        self.estado = {"parte": 0, "total": 1, "texto": "Começando...", "aviso": "", "fim": None}
        self.inicio = time.monotonic()
        self.jan = tk.Toplevel(parent or studio.raiz)
        self.jan.title(titulo)
        self.jan.configure(bg=tema.FUNDO)
        self.jan.resizable(False, False)
        self.jan.protocol("WM_DELETE_WINDOW", self.cancelar)
        q = tk.Frame(self.jan, bg=tema.FUNDO, padx=24, pady=20)
        q.pack(fill="both", expand=True)
        tema.rotulo(q, titulo, "subtitulo").pack(fill="x")
        tema.rotulo(q, explicacao, "secundario", wraplength=480).pack(fill="x", pady=(4, 14))
        self.lbl_texto = tema.rotulo(q, "", "texto", wraplength=480)
        self.lbl_texto.pack(fill="x")
        self.barra = ttk.Progressbar(q, mode="determinate", maximum=1.0, length=480)
        self.barra.pack(fill="x", pady=(8, 4))
        self.lbl_tempo = tema.rotulo(q, "", "pequeno")
        self.lbl_tempo.pack(fill="x")
        self.lbl_aviso = tk.Label(q, text="", bg=tema.FUNDO, fg=tema.AMARELO, font=tema.F_PEQUENA, anchor="w",
                                  justify="left", wraplength=480)  # fmt: skip
        self.lbl_aviso.pack(fill="x", pady=(6, 0))
        self.btn = ttk.Button(q, text="Cancelar", style="Extra.TButton", command=self.cancelar)
        self.btn.pack(anchor="e", pady=(14, 0))
        self.jan.transient(parent or studio.raiz)

        def progresso(parte, total, texto):
            self.estado.update(parte=parte, total=max(1, total), texto=texto)

        def avisar(texto):
            self.estado["aviso"] = texto

        def rodar():
            try:
                self.estado["fim"] = ("ok", trabalho(self.cancelar_evento, progresso, avisar))
            except Cancelado:
                self.estado["fim"] = ("cancelado", None)
            except ErroClaude as e:
                self.estado["fim"] = ("erro", str(e))
            except Exception as e:  # erro inesperado: mostra em portugues e registra
                from nucleo.registro import registrar

                registrar("erro pedindo ao Claude", e)
                self.estado["fim"] = ("erro", f"Erro inesperado: {e}")

        threading.Thread(target=rodar, daemon=True).start()
        self.conferir()

    def conferir(self):
        if not self.jan.winfo_exists():
            return
        e = self.estado
        segundos = int(time.monotonic() - self.inicio)
        self.lbl_texto.config(text=e["texto"])
        pulso = (segundos % 20) / 20 * 0.9  # anda devagar dentro da parte (o Claude nao diz quanto falta)
        self.barra["value"] = min(1.0, (e["parte"] + pulso) / e["total"])
        self.lbl_tempo.config(text=f"{segundos // 60}:{segundos % 60:02d}  ·  costuma levar de 1 a 5 minutos")
        self.lbl_aviso.config(text=e["aviso"])
        if e["fim"] is None:
            self.jan.after(300, self.conferir)
            return
        resultado, valor = e["fim"]
        self.jan.destroy()
        if resultado == "ok":
            self.ao_terminar(valor)
        elif resultado == "erro":
            messagebox.showerror("Claude", f"{valor}\n\nNada foi mudado no projeto. Tente de novo daqui a pouco.",
                                 parent=self.studio.raiz)  # fmt: skip
        else:
            self.studio.notificar("Cancelado. Nada foi mudado no projeto.", "info")

    def cancelar(self):
        if self.estado["fim"] is not None:
            return
        self.cancelar_evento.set()
        self.btn.config(state="disabled", text="Cancelando...")
